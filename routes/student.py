from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import Student, db, Notification, CareerGoal, GoalMilestone, Task, StudentDocument, Grievance, Event, EventRegistration, Message, Appointment, CounsellorSchedule, CareerCounsellor, AppointmentRequest
from datetime import datetime, timedelta, time
from sqlalchemy import desc, func
from werkzeug.utils import secure_filename
import os
import uuid

student_bp = Blueprint('student', __name__)

def assign_counsellor(student_interests):
    """
    Assigns a counsellor to a student based on matching specializations with student interests.
    Args:
        student_interests: Comma-separated string of student interests
    Returns:
        The counsellor_id of the best matching counsellor, or None if no match found
    """
    # Get all active counsellors
    available_counsellors = CareerCounsellor.query.filter_by(availability_status=True).all()
    
    if not available_counsellors:
        return None
        
    # Convert student interests to a list and clean them
    interests = [interest.strip().lower() for interest in student_interests.split(',')]
    
    # Find best matching counsellor based on specialization
    best_match_score = 0
    selected_counsellor = None
    
    # Define specialization categories and related keywords
    specialization_keywords = {
        'Technology': ['technology', 'computer', 'it', 'software', 'programming', 'tech'],
        'Healthcare': ['healthcare', 'medical', 'medicine', 'health', 'nursing'],
        'Business': ['business', 'finance', 'management', 'entrepreneurship', 'marketing'],
        'Engineering': ['engineering', 'mechanical', 'civil', 'electrical', 'electronics'],
        'Arts': ['arts', 'creative', 'design', 'music', 'fine arts', 'media'],
        'Science': ['science', 'physics', 'chemistry', 'biology', 'research'],
        'Education': ['education', 'teaching', 'training', 'academic'],
        'Law': ['law', 'legal', 'justice', 'advocacy']
    }
    
    for counsellor in available_counsellors:
        match_score = 0
        counsellor_specialization = counsellor.specialization.lower()
        
        # Check each student interest against counsellor's specialization and related keywords
        for interest in interests:
            # Direct match with specialization
            if interest in counsellor_specialization:
                match_score += 2  # Give higher weight to direct matches
                continue
            
            # Check against specialization keywords
            for spec, keywords in specialization_keywords.items():
                if spec.lower() == counsellor_specialization:
                    if any(keyword in interest for keyword in keywords):
                        match_score += 1
                        break
        
        # Update best match if this counsellor has a better score
        if match_score > best_match_score:
            best_match_score = match_score
            selected_counsellor = counsellor
    
    # If no matches found, assign the counsellor with highest rating
    if not selected_counsellor and available_counsellors:
        selected_counsellor = max(available_counsellors, key=lambda c: c.rating)
    
    return selected_counsellor.id if selected_counsellor else None

@student_bp.route('/student/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data with debug prints
            print("Starting registration process...")
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            dob_str = request.form.get('dob')
            address = request.form.get('address')
            education_level = request.form.get('education_level')
            interests = request.form.getlist('interests')
            password = request.form.get('password')

            print(f"Received data: {first_name=}, {last_name=}, {email=}, {interests=}")

            # Validate required fields
            if not all([first_name, last_name, email, password, dob_str]):
                flash('Please fill in all required fields', 'danger')
                return render_template('student/register.html')

            # Parse date of birth
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError as e:
                print(f"DOB parsing error: {e}")
                flash('Invalid date format for date of birth', 'danger')
                return render_template('student/register.html')

            # Check if email already exists
            existing_student = Student.query.filter_by(email=email).first()
            if existing_student:
                flash('Email already registered', 'danger')
                return render_template('student/register.html')

            # Convert interests list to comma-separated string
            interests_str = ','.join(interests) if interests else ''
            print(f"Interests string: {interests_str}")
            
            # Assign a counsellor based on interests
            counsellor_id = assign_counsellor(interests_str)
            print(f"Assigned counsellor ID: {counsellor_id}")

            # Create new student
            student = Student(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                dob=dob,
                address=address,
                education_level=education_level,
                interests=interests_str,
                counsellor_id=counsellor_id,
                is_active=True
            )
            
            # Set password
            student.set_password(password)
            print("Student object created, attempting database save...")

            # Add to database
            db.session.add(student)
            db.session.commit()
            print(f"Student saved to database with ID: {student.id}")

            # Create notification for assigned counsellor
            if counsellor_id:
                try:
                    notification = Notification(
                        user_id=counsellor_id,
                        message=f"New student {first_name} {last_name} has been assigned to you based on matching interests.",
                        notification_type='assignment',
                        related_entity_id=student.id
                    )
                    db.session.add(notification)
                    db.session.commit()
                    print("Counsellor notification created")
                except Exception as notif_error:
                    print(f"Notification creation error: {notif_error}")
                    # Continue even if notification fails
                    pass

                flash('Registration successful! A counsellor matching your interests has been assigned to you.', 'success')
            else:
                flash('Registration successful! A counsellor will be assigned to you soon.', 'success')

            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('student/register.html')

    # GET request - show registration form
    return render_template('student/register.html')

@student_bp.route('/goals', methods=['GET', 'POST'])
@login_required
def manage_goals():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_date_str = request.form.get('start_date')
        target_date_str = request.form.get('target_date')
        
        if not title:
            flash('Goal title is required', 'error')
            return redirect(url_for('student.manage_goals'))
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else None
            
            goal = CareerGoal(
                student_id=current_user.id,
                title=title,
                description=description,
                start_date=start_date,
                target_date=target_date,
                status='not_started'
            )
            db.session.add(goal)
            db.session.commit()
            flash('Career goal added successfully!', 'success')
            return redirect(url_for('student.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding career goal: ' + str(e), 'error')
            return redirect(url_for('student.manage_goals'))
    
    career_goals = CareerGoal.query.filter_by(student_id=current_user.id).all()
    return render_template('student/dashboard.html', career_goals=career_goals)

@student_bp.route('/goals/<int:goal_id>/milestones', methods=['GET', 'POST'])
@login_required
def manage_milestones(goal_id):
    goal = CareerGoal.query.filter_by(goal_id=goal_id, student_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        milestone_title = request.form.get('milestone_title')
        due_date_str = request.form.get('due_date')
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
            milestone = GoalMilestone(
                goal_id=goal_id,
                milestone_title=milestone_title,
                due_date=due_date,
                status='pending'
            )
            db.session.add(milestone)
            db.session.commit()
            flash('Milestone added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding milestone', 'danger')
        
        return redirect(url_for('student.manage_milestones', goal_id=goal_id))
    
    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read_status=False
    ).count()
    
    milestones = GoalMilestone.query.filter_by(goal_id=goal_id).order_by(GoalMilestone.due_date.asc()).all()
    return render_template('student/milestones.html', 
                         goal=goal, 
                         milestones=milestones,
                         unread_notifications=unread_notifications)

@student_bp.route('/goals/<int:goal_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_goal(goal_id):
    goal = CareerGoal.query.filter_by(goal_id=goal_id, student_id=current_user.id).first_or_404()
    
    if request.method == 'PUT':
        data = request.get_json()
        goal.status = data.get('status', goal.status)
        goal.title = data.get('title', goal.title)
        goal.description = data.get('description', goal.description)
        if 'target_date' in data:
            goal.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
        
        try:
            db.session.commit()
            return jsonify({
                'id': goal.goal_id,
                'title': goal.title,
                'description': goal.description,
                'status': goal.status,
                'target_date': goal.target_date.isoformat() if goal.target_date else None
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update goal'}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(goal)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete goal'}), 500

@student_bp.route('/milestones/<int:milestone_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_milestone(milestone_id):
    milestone = GoalMilestone.query.join(CareerGoal).filter(
        GoalMilestone.milestone_id == milestone_id,
        CareerGoal.student_id == current_user.id
    ).first_or_404()
    
    if request.method == 'PUT':
        data = request.get_json()
        milestone.status = data.get('status', milestone.status)
        milestone.milestone_title = data.get('title', milestone.milestone_title)
        if 'due_date' in data:
            milestone.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        
        try:
            db.session.commit()
            return jsonify({
                'id': milestone.milestone_id,
                'title': milestone.milestone_title,
                'status': milestone.status,
                'due_date': milestone.due_date.isoformat() if milestone.due_date else None
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update milestone'}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(milestone)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete milestone'}), 500

@student_bp.route('/student/tasks', methods=['GET', 'POST'])
@login_required
def manage_tasks():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        priority = request.form.get('priority')
        category = request.form.get('category')
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
            
            task = Task(
                student_id=current_user.id,
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                category=category,
                status='Pending'
            )
            db.session.add(task)
            db.session.commit()
            return jsonify({'message': 'Task added successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to add task'}), 500
    
    # GET request - return tasks with filters
    status = request.args.get('status')
    priority = request.args.get('priority')
    category = request.args.get('category')
    sort_by = request.args.get('sort_by', 'due_date')

    query = Task.query.filter_by(student_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if category:
        query = query.filter_by(category=category)
    
    if sort_by == 'due_date':
        query = query.order_by(Task.due_date.asc())
    elif sort_by == 'priority':
        priority_order = {'High': 1, 'Medium': 2, 'Low': 3}
        query = query.order_by(Task.priority.asc())
    elif sort_by == 'created_at':
        query = query.order_by(desc(Task.created_at))
    
    tasks = query.all()
    
    # Calculate statistics
    total_tasks = len(tasks)
    pending_tasks = sum(1 for task in tasks if task.status == 'Pending')
    completed_tasks = sum(1 for task in tasks if task.status == 'Completed')
    due_soon = sum(1 for task in tasks 
                  if task.status == 'Pending' 
                  and task.due_date 
                  and task.due_date <= datetime.now().date() + timedelta(days=3))

    stats = {
        'total': total_tasks,
        'pending': pending_tasks,
        'completed': completed_tasks,
        'due_soon': due_soon
    }

    return jsonify({
        'tasks': [task.to_dict() for task in tasks],
        'stats': stats
    })

@student_bp.route('/student/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_task(task_id):
    task = Task.query.filter_by(task_id=task_id, student_id=current_user.id).first_or_404()
    
    if request.method == 'PUT':
        data = request.get_json()
        task.status = data.get('status', task.status)
        task.title = data.get('title', task.title)
        task.description = data.get('description', task.description)
        task.priority = data.get('priority', task.priority)
        task.category = data.get('category', task.category)
        if 'due_date' in data:
            task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        
        try:
            db.session.commit()
            return jsonify(task.to_dict()), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update task'}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(task)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete task'}), 500

@student_bp.route('/student/documents', methods=['GET', 'POST'])
@login_required
def manage_documents():
    if request.method == 'POST':
        title = request.form.get('title')
        document_type = request.form.get('document_type')
        file = request.files.get('file')
        
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        try:
            # Save file to appropriate location
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            document = StudentDocument(
                student_id=current_user.id,
                title=title,
                document_type=document_type,
                file_path=file_path
            )
            db.session.add(document)
            db.session.commit()
            
            return jsonify({'message': 'Document uploaded successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to upload document'}), 500
    
    # GET request - return student's documents
    documents = StudentDocument.query.filter_by(student_id=current_user.id).all()
    return jsonify({
        'documents': [{
            'title': doc.title,
            'document_type': doc.document_type,
            'upload_date': doc.upload_date.isoformat(),
            'file_path': doc.file_path
        } for doc in documents]
    })

@student_bp.route('/student/grievances', methods=['GET', 'POST'])
@login_required
def manage_grievances():
    if request.method == 'POST':
        data = request.get_json()
        subject = data.get('subject')
        description = data.get('description')
        
        try:
            grievance = Grievance(
                student_id=current_user.id,
                subject=subject,
                description=description,
                status='Pending'
            )
            db.session.add(grievance)
            db.session.commit()
            
            return jsonify({'message': 'Grievance submitted successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to submit grievance'}), 500
    
    # GET request - return student's grievances
    grievances = Grievance.query.filter_by(student_id=current_user.id).order_by(Grievance.created_at.desc()).all()
    return jsonify({
        'grievances': [{
            'id': g.id,
            'subject': g.subject,
            'description': g.description,
            'status': g.status,
            'response': g.response,
            'created_at': g.created_at.isoformat()
        } for g in grievances]
    })

@student_bp.route('/student/events', methods=['GET'])
@login_required
def view_events():
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.now().date()
    ).order_by(Event.event_date.asc()).all()
    
    # Get student's registrations
    registrations = {r.event_id: r for r in EventRegistration.query.filter_by(student_id=current_user.id).all()}
    
    return jsonify({
        'events': [{
            'event_id': event.event_id,
            'title': event.title,
            'description': event.description,
            'event_type': event.event_type,
            'event_date': event.event_date.isoformat(),
            'start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
            'end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
            'location': event.location,
            'is_online': event.is_online,
            'capacity': event.capacity,
            'registration': bool(registrations.get(event.event_id))
        } for event in upcoming_events]
    })

@student_bp.route('/student/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_for_event(event_id):
    print("\n=== Debug: Processing Event Registration ===")
    print(f"Event ID: {event_id}")
    print(f"Student ID: {current_user.id}")
    
    event = Event.query.get_or_404(event_id)
    print(f"Event found: {event.title}")
    print(f"Event capacity: {event.capacity}")
    
    # Check if event date has passed
    if event.event_date < datetime.now().date():
        print("Error: Cannot register for past events")
        return jsonify({'error': 'Cannot register for past events'}), 400
    
    # Check if already registered
    existing_registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=current_user.id
    ).first()
    
    if existing_registration:
        print("Error: Already registered for this event")
        return jsonify({'error': 'Already registered for this event'}), 400
    
    # Check event capacity if it's set
    if event.capacity is not None:
        current_registrations = EventRegistration.query.filter_by(event_id=event_id).count()
        print(f"Current registrations: {current_registrations}")
        print(f"Event capacity: {event.capacity}")
        
        if current_registrations >= event.capacity:
            print("Error: Event is at full capacity")
            return jsonify({'error': 'Event is at full capacity'}), 400
    else:
        print("Note: Event has no capacity limit")
    
    try:
        # Create registration
        registration = EventRegistration(
            event_id=event_id,
            student_id=current_user.id,
            registered_at=datetime.now(),
            attendance_status='registered'
        )
        db.session.add(registration)
        
        # Create notification for student
        notification = Notification(
            user_id=current_user.id,
            message=f'You have successfully registered for {event.title} on {event.event_date.strftime("%B %d, %Y")}.',
            notification_type='general',
            related_entity_id=event.event_id,
            created_at=datetime.now()
        )
        db.session.add(notification)
        
        print("Committing to database...")
        db.session.commit()
        print("Successfully registered for event")
        
        return jsonify({
            'message': 'Successfully registered for event',
            'event': {
                'event_id': event.event_id,
                'title': event.title,
                'event_date': event.event_date.isoformat(),
                'start_time': event.start_time.strftime('%H:%M') if event.start_time else None
            }
        }), 201
        
    except Exception as e:
        print(f"Error during registration: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to register for event'}), 500

@student_bp.route('/student/messages', methods=['GET', 'POST'])
@login_required
def messages():
    if request.method == 'POST':
        data = request.get_json()
        recipient_id = data.get('recipient_id')
        message_text = data.get('message_text')
        
        try:
            message = Message(
                sender_id=current_user.id,
                recipient_id=recipient_id,
                message_text=message_text
            )
            db.session.add(message)
            db.session.commit()
            
            return jsonify({'message': 'Message sent successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to send message'}), 500
    
    # GET request - return student's messages
    sent_messages = Message.query.filter_by(sender_id=current_user.id).all()
    received_messages = Message.query.filter_by(recipient_id=current_user.id).all()
    
    return jsonify({
        'messages': [{
            'id': msg.message_id,
            'sender_id': msg.sender_id,
            'recipient_id': msg.recipient_id,
            'message_text': msg.message_text,
            'sent_at': msg.sent_at.isoformat(),
            'is_read': msg.is_read
        } for msg in sorted(sent_messages + received_messages, key=lambda x: x.sent_at, reverse=True)]
    })

@student_bp.route('/student/submit_grievance', methods=['POST'])
@login_required
def submit_grievance():
    subject = request.form.get('subject')
    description = request.form.get('description')
    
    if not subject or not description:
        flash('Please fill in all required fields', 'danger')
        return redirect(url_for('student.dashboard'))
    
    try:
        # Create new grievance
        grievance = Grievance(
            student_id=current_user.id,
            subject=subject,
            description=description,
            status='Pending'
        )
        db.session.add(grievance)
        db.session.commit()
        
        # Create notification for the student
        notification = Notification(
            user_id=current_user.id,
            message=f'Your grievance "{subject}" has been submitted successfully.',
            notification_type='grievance',
            related_entity_id=grievance.id
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Grievance submitted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to submit grievance. Please try again.', 'danger')
    
    return redirect(url_for('student.dashboard'))

def setup_counselor_schedule(counselor_id):
    """Set up default schedule for counselor if none exists"""
    # Check if schedule exists
    existing_schedule = CounsellorSchedule.query.filter_by(counselor_id=counselor_id).first()
    if existing_schedule:
        return

    # Extended working hours
    start_time = time(9, 0)   # 9:00 AM
    end_time = time(20, 0)    # 8:00 PM
    
    # Create schedule for Monday through Friday
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in weekdays:
        schedule = CounsellorSchedule(
            counselor_id=counselor_id,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time,
            is_recurring=True
        )
        db.session.add(schedule)
    
    try:
        db.session.commit()
        print(f"Created default schedule for counselor {counselor_id}")
    except Exception as e:
        print(f"Error creating schedule: {str(e)}")
        db.session.rollback()

    # Delete existing schedule and create new one if needed
    CounsellorSchedule.query.filter_by(counselor_id=counselor_id).delete()
    db.session.commit()

    # Create new schedule
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in weekdays:
        schedule = CounsellorSchedule(
            counselor_id=counselor_id,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time,
            is_recurring=True
        )
        db.session.add(schedule)
    
    try:
        db.session.commit()
        print(f"Updated schedule for counselor {counselor_id}")
    except Exception as e:
        print(f"Error updating schedule: {str(e)}")
        db.session.rollback()

@student_bp.route('/student/request_appointment', methods=['POST'])
@login_required
def request_appointment():
    # Get student ID from current_user
    student_id = current_user.id
    counsellor_id = current_user.counsellor_id
    
    if not counsellor_id:
        flash('You need to be assigned a counsellor first.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Get form data
    appointment_type = request.form.get('appointment_type')
    appointment_date = request.form.get('appointment_date')
    start_time = request.form.get('start_time')
    mode = request.form.get('mode')
    notes = request.form.get('notes')
    
    # Validate required fields
    if not all([appointment_type, appointment_date, start_time, mode]):
        flash('Please fill in all required fields', 'danger')
        return redirect(url_for('student.dashboard'))
    
    try:
        # Convert string inputs to proper datetime objects
        preferred_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        preferred_time = datetime.strptime(start_time, '%H:%M').time()
        
        # Validate appointment date is not in the past
        if preferred_date < datetime.now().date():
            flash('Cannot schedule appointments in the past', 'danger')
            return redirect(url_for('student.dashboard'))
        
        # Create appointment request
        appointment_request = AppointmentRequest(
            student_id=student_id,
            counsellor_id=counsellor_id,
            appointment_type=appointment_type,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            mode=mode,
            notes=notes,
            status='pending'
        )
        
        db.session.add(appointment_request)
        db.session.commit()  # Commit first to get the ID
        
        # For counsellor
        counsellor_notification = Notification(
            user_id=counsellor_id,
            message=f'New appointment request from {current_user.first_name} {current_user.last_name} for {preferred_date.strftime("%B %d, %Y")} at {preferred_time.strftime("%I:%M %p")}',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(counsellor_notification)
        
        # For student
        student_notification = Notification(
            user_id=student_id,
            message=f'Your appointment request for {preferred_date.strftime("%B %d, %Y")} at {preferred_time.strftime("%I:%M %p")} has been submitted and is pending approval.',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(student_notification)
        
        db.session.commit()
        
        flash('Appointment request submitted successfully! Waiting for counsellor approval.', 'success')
        
    except ValueError as e:
        flash('Invalid date or time format.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash('Failed to submit appointment request. Please try again.', 'danger')
    
    return redirect(url_for('student.dashboard'))

@student_bp.route('/student/appointment_requests', methods=['GET'])
@login_required
def view_appointment_requests():
    appointment_requests = AppointmentRequest.query.filter_by(
        student_id=current_user.id
    ).order_by(AppointmentRequest.created_at.desc()).all()

    return jsonify({
        'appointment_requests': [request.to_dict() for request in appointment_requests]
    })

@student_bp.route('/student/dashboard')
@login_required
def dashboard():
    if not current_user.get_id().startswith('student-'):
        flash('Access denied. This dashboard is for students only.', 'danger')
        return redirect(url_for('index'))
    
    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read_status=False
    ).count()
    
    # Get career goals and their milestones
    career_goals = CareerGoal.query.filter_by(
        student_id=current_user.id
    ).all()
    
    # Get upcoming milestones
    upcoming_milestones = GoalMilestone.query.join(CareerGoal).filter(
        CareerGoal.student_id == current_user.id,
        GoalMilestone.status == 'pending'
    ).order_by(GoalMilestone.due_date.asc()).limit(5).all()
    
    # Get recent grievances
    recent_grievances = Grievance.query.filter_by(
        student_id=current_user.id
    ).order_by(Grievance.created_at.desc()).limit(5).all()
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.student_id == current_user.id,
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc()).all()
    
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.now().date()
    ).order_by(Event.event_date.asc()).limit(5).all()
    
    # Get event registrations
    event_registrations = {}
    if upcoming_events:
        event_ids = [event.event_id for event in upcoming_events]
        registrations = EventRegistration.query.filter(
            EventRegistration.student_id == current_user.id,
            EventRegistration.event_id.in_(event_ids)
        ).all()
        event_registrations = {r.event_id: r for r in registrations}
    
    # Get student's appointment requests
    appointment_requests = AppointmentRequest.query.filter_by(
        student_id=current_user.id
    ).order_by(AppointmentRequest.created_at.desc()).all()
    
    # Get student's counselor
    counselor = None
    if current_user.counsellor_id:
        counselor = CareerCounsellor.query.get(current_user.counsellor_id)

    return render_template('student/dashboard.html',
                         student=current_user,
                         unread_notifications=unread_notifications,
                         career_goals=career_goals,
                         upcoming_milestones=upcoming_milestones,
                         recent_grievances=recent_grievances,
                         upcoming_appointments=upcoming_appointments,
                         upcoming_events=upcoming_events,
                         event_registrations=event_registrations,
                         appointment_requests=appointment_requests,
                         counselor=counselor,
                         today=datetime.now())

@student_bp.route('/student/notifications')
@login_required
def get_notifications():
    # Get recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    return jsonify({
        'notifications': [notification.to_dict() for notification in notifications]
    })

@student_bp.route('/student/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        notification_id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    notification.read_status = True
    db.session.commit()
    
    return jsonify({'success': True})

@student_bp.route('/student/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(
        user_id=current_user.id,
        read_status=False
    ).update({'read_status': True})
    
    db.session.commit()
    
    return jsonify({'success': True})

@student_bp.route('/student/notifications/all')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    notification_icons = {
        'appointment': 'fa-calendar-check',
        'resource': 'fa-book',
        'grievance': 'fa-exclamation-circle',
        'payment': 'fa-credit-card',
        'general': 'fa-bell'
    }
    
    return render_template('student/notifications.html',
                         notifications=notifications,
                         notification_icons=notification_icons)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return 'pdf'
    elif ext in ['doc', 'docx']:
        return 'doc'
    elif ext in ['jpg', 'jpeg', 'png']:
        return 'image'
    return 'other'

@student_bp.route('/student/documents/upload', methods=['POST'])
@login_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed'}), 400
    
    try:
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create upload folder if it doesn't exist
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Create document record
        document = StudentDocument(
            student_id=current_user.id,
            title=request.form.get('title'),
            document_type=request.form.get('document_type'),
            file_path=file_path,
            file_type=get_file_type(file.filename)
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document': {
                'id': document.document_id,
                'title': document.title,
                'document_type': document.document_type,
                'file_type': document.file_type,
                'upload_date': document.upload_date.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@student_bp.route('/student/documents/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    document = StudentDocument.query.filter_by(
        document_id=doc_id,
        student_id=current_user.id
    ).first_or_404()
    
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        document.file_path,
        as_attachment=True,
        download_name=f"{document.title}.{document.file_path.rsplit('.', 1)[1]}"
    )

@student_bp.route('/student/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    document = StudentDocument.query.filter_by(
        document_id=doc_id,
        student_id=current_user.id
    ).first_or_404()
    
    try:
        # Delete file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete record
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@student_bp.route('/student/appointments/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@login_required
def reschedule_appointment(appointment_id):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        student_id=current_user.id,
        status='scheduled'
    ).first_or_404()
    
    if request.method == 'POST':
        new_date = request.form.get('appointment_date')
        new_time = request.form.get('start_time')
        
        try:
            # Convert string inputs to proper datetime objects
            new_date = datetime.strptime(new_date, '%Y-%m-%d').date()
            new_time = datetime.strptime(new_time, '%H:%M').time()
            
            # Validate new date is not in the past
            if new_date < datetime.now().date():
                flash('Cannot schedule appointments in the past', 'danger')
                return redirect(url_for('student.dashboard'))
            
            # Calculate end time (1 hour duration)
            new_end_time = (datetime.combine(datetime.min, new_time) + timedelta(hours=1)).time()
            
            # Check counselor availability
            day_of_week = new_date.strftime('%A')
            counselor_schedule = CounsellorSchedule.query.filter_by(
                counselor_id=appointment.counselor_id,
                day_of_week=day_of_week
            ).first()
            
            if not counselor_schedule:
                flash('Counselor is not available on this day.', 'danger')
                return redirect(url_for('student.dashboard'))
            
            if (new_time < counselor_schedule.start_time or 
                new_end_time > counselor_schedule.end_time):
                flash('Selected time is outside counselor\'s working hours.', 'danger')
                return redirect(url_for('student.dashboard'))
            
            # Check for existing appointments at the new time
            existing_appointment = Appointment.query.filter_by(
                counselor_id=appointment.counselor_id,
                appointment_date=new_date,
                start_time=new_time,
                status='scheduled'
            ).first()
            
            if existing_appointment and existing_appointment.id != appointment_id:
                flash('This time slot is already booked. Please choose another time.', 'danger')
                return redirect(url_for('student.dashboard'))
            
            # Update appointment
            appointment.appointment_date = new_date
            appointment.start_time = new_time
            appointment.end_time = new_end_time
            appointment.status = 'rescheduled'
            
            # Create notifications
            student_notification = Notification(
                user_id=current_user.id,
                message=f'Your appointment has been rescheduled to {new_date.strftime("%B %d, %Y")} at {new_time.strftime("%I:%M %p")}',
                notification_type='appointment',
                related_entity_id=appointment.id
            )
            
            counselor_notification = Notification(
                user_id=appointment.counselor_id,
                message=f'Appointment with {current_user.first_name} {current_user.last_name} has been rescheduled to {new_date.strftime("%B %d, %Y")} at {new_time.strftime("%I:%M %p")}',
                notification_type='appointment',
                related_entity_id=appointment.id
            )
            
            db.session.add(student_notification)
            db.session.add(counselor_notification)
            db.session.commit()
            
            flash('Appointment rescheduled successfully!', 'success')
            return redirect(url_for('student.dashboard'))
            
        except ValueError as e:
            flash('Invalid date or time format.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash('Failed to reschedule appointment. Please try again.', 'danger')
        
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/reschedule_appointment.html', 
                         appointment=appointment,
                         today=datetime.now())

@student_bp.route('/student/appointment_requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment_request(request_id):
    print(f"\n=== Debug: Canceling Appointment Request {request_id} ===")
    try:
        # Find the appointment request
        appointment_request = AppointmentRequest.query.filter_by(
            id=request_id,
            student_id=current_user.id,
            status='pending'
        ).first()

        if not appointment_request:
            print("Error: Appointment request not found or not pending")
            return jsonify({
                'status': 'error',
                'message': 'Appointment request not found or already processed'
            }), 404
        
        print(f"Found appointment request: {appointment_request.id}")
        print(f"Current status: {appointment_request.status}")
        
        # Update the request status
        appointment_request.status = 'cancelled'
        
        # Create notification for counselor
        counselor_notification = Notification(
            user_id=appointment_request.counselor_id,
            message=f'Appointment request for {appointment_request.preferred_date.strftime("%B %d, %Y")} at {appointment_request.preferred_time.strftime("%I:%M %p")} has been cancelled by the student.',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(counselor_notification)
        
        # Create notification for student
        student_notification = Notification(
            user_id=current_user.id,
            message=f'You have cancelled your appointment request for {appointment_request.preferred_date.strftime("%B %d, %Y")} at {appointment_request.preferred_time.strftime("%I:%M %p")}.',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(student_notification)
        
        print("Committing changes to database...")
        db.session.commit()
        print("Successfully cancelled appointment request")
        
        return jsonify({
            'status': 'success',
            'message': 'Appointment request cancelled successfully'
        })
        
    except Exception as e:
        print(f"Error cancelling appointment request: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to cancel appointment request. Please try again.'
        }), 500