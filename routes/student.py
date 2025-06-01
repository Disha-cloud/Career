from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import Student, db, Notification, CareerGoal, GoalMilestone, Task, StudentDocument, Grievance, Event, EventRegistration, Message, Appointment, CounsellorSchedule, CareerCounsellor, AppointmentRequest, Feedback
from datetime import datetime, timedelta, time
from sqlalchemy import desc, func
from werkzeug.utils import secure_filename
import os
import uuid
from functools import wraps

# Create the blueprint
student_bp = Blueprint('student', __name__)

# Student-only decorator
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_id().startswith('student-'):
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/student/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            dob_str = request.form.get('dob')
            address = request.form.get('address')
            education_level = request.form.get('education_level')
            interests = request.form.getlist('interests')
            password = request.form.get('password')

            # Validate required fields
            if not all([first_name, last_name, email, password, dob_str]):
                flash('Please fill in all required fields', 'danger')
                return render_template('student/register.html')

            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for date of birth', 'danger')
                return render_template('student/register.html')

            # Check if email exists in any user table
            email_exists, user_type = Student.check_email_exists(email)
            if email_exists:
                flash(f'This email is already registered as a {user_type}. Please use a different email address.', 'danger')
                return render_template('student/register.html')

            interests_str = ','.join(interests) if interests else ''
            counsellor_id = assign_counsellor(interests_str)

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
            
            student.set_password(password)

            try:
                db.session.add(student)
                db.session.commit()

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
                    except Exception:
                        pass

                    flash('Registration successful! A counsellor matching your interests has been assigned to you.', 'success')
                else:
                    flash('Registration successful! A counsellor will be assigned to you soon.', 'success')

                return redirect(url_for('auth.login'))

            except Exception as e:
                db.session.rollback()
                flash('An error occurred during registration. Please try again.', 'danger')
                return render_template('student/register.html')

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('student/register.html')

    return render_template('student/register.html')

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

@student_bp.route('/student/goals', methods=['GET'])
@login_required
@student_required
def get_career_goals():
    try:
        # Get all career goals for the current student
        goals = CareerGoal.query.filter_by(student_id=current_user.id).all()
        
        # Convert goals to dictionary format
        goals_data = []
        for goal in goals:
            goal_dict = {
                'id': goal.goal_id,
                'title': goal.title,
                'description': goal.description,
                'target_date': goal.target_date.strftime('%Y-%m-%d') if goal.target_date else None,
                'status': goal.status,
                'priority': goal.priority,
                'created_at': goal.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'milestones': []
            }
            
            # Add milestones for each goal
            milestones = GoalMilestone.query.filter_by(goal_id=goal.goal_id).all()
            for milestone in milestones:
                milestone_dict = {
                    'id': milestone.milestone_id,
                    'title': milestone.title,
                    'description': milestone.description,
                    'due_date': milestone.due_date.strftime('%Y-%m-%d') if milestone.due_date else None,
                    'status': milestone.status,
                    'created_at': milestone.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                goal_dict['milestones'].append(milestone_dict)
            
            goals_data.append(goal_dict)
        
        return jsonify({
            'success': True,
            'goals': goals_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch career goals'
        }), 500

@student_bp.route('/student/goals', methods=['POST'])
@login_required
@student_required
def manage_goals():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        start_date_str = request.form.get('start_date')
        target_date_str = request.form.get('target_date')
        
        # Convert date strings to date objects if provided
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else None
        
        # Create new goal
        goal = CareerGoal(
            student_id=current_user.id,
            title=title,
            description=description,
            start_date=start_date,
            target_date=target_date,
            status='in_progress'
        )
        
        db.session.add(goal)
        db.session.commit()
        
        flash('Career goal added successfully!', 'success')
        return redirect(url_for('student.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to add career goal. Please try again.', 'danger')
        return redirect(url_for('student.dashboard'))

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
    event = Event.query.get_or_404(event_id)
    
    if event.event_date < datetime.now().date():
        return jsonify({'error': 'Cannot register for past events'}), 400
    
    # Check if already registered
    existing_registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=current_user.id
    ).first()
    
    if existing_registration:
        return jsonify({'error': 'Already registered for this event'}), 400
    
    # Check event capacity if it's set
    if event.capacity is not None:
        current_registrations = EventRegistration.query.filter_by(event_id=event_id).count()
        
        if current_registrations >= event.capacity:
            return jsonify({'error': 'Event is at full capacity'}), 400
    else:
        pass
    
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
            user_type='student',
            message=f'You have successfully registered for {event.title} on {event.event_date.strftime("%B %d, %Y")}.',
            notification_type='event',
            related_entity_id=event.event_id,
            created_at=datetime.now()
        )
        db.session.add(notification)
        
        db.session.commit()
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
        db.session.rollback()
        return jsonify({'error': 'Failed to register for event'}), 500

@student_bp.route('/student/messages', methods=['GET', 'POST'])
@login_required
def messages():
    if not current_user.counsellor_id:
        return jsonify({
            'error': 'You need to be assigned a counsellor first to use the messaging feature.'
        }), 400

    if request.method == 'POST':
        data = request.get_json()
        message_text = data.get('message_text')
        
        if not message_text:
            return jsonify({'error': 'Message text is required'}), 400
        
        try:
            # Create message to counsellor
            message = Message(
                sender_id=current_user.id,
                recipient_id=current_user.counsellor_id,
                sender_type='student',
                recipient_type='counsellor',
                message_text=message_text,
                sent_at=datetime.now()
            )
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                'message': 'Message sent successfully',
                'data': {
                    'id': message.message_id,
                    'sender_id': message.sender_id,
                    'recipient_id': message.recipient_id,
                    'message_text': message.message_text,
                    'sent_at': message.sent_at.isoformat(),
                    'is_read': message.is_read
                }
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to send message'}), 500
    
    # GET request - return conversation with assigned counsellor
    conversation = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == current_user.counsellor_id)) |
        ((Message.sender_id == current_user.counsellor_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.sent_at.desc()).all()
    
    # Mark received messages as read
    unread_messages = [msg for msg in conversation if not msg.is_read and msg.recipient_id == current_user.id]
    for msg in unread_messages:
        msg.is_read = True
    if unread_messages:
        db.session.commit()
    
    return jsonify({
        'counsellor_id': current_user.counsellor_id,
        'messages': [{
            'id': msg.message_id,
            'sender_id': msg.sender_id,
            'recipient_id': msg.recipient_id,
            'message_text': msg.message_text,
            'sent_at': msg.sent_at.isoformat(),
            'is_read': msg.is_read,
            'is_sent_by_me': msg.sender_id == current_user.id
        } for msg in conversation]
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
            user_type='student',
            message=f'Your grievance "{subject}" has been submitted successfully.',
            notification_type='grievance',
            related_entity_id=grievance.id,
            created_at=datetime.now()
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Grievance submitted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to submit grievance. Please try again.', 'danger')
    
    return redirect(url_for('student.dashboard'))

@student_bp.route('/student/request_appointment', methods=['POST'])
@login_required
def request_appointment():
    # Get student ID from current_user
    student_id = current_user.id
    counsellor_id = current_user.counsellor_id
    
    if not counsellor_id:
        return jsonify({
            'status': 'error',
            'message': 'You need to be assigned a counsellor first.'
        }), 400
    
    # Get form data
    appointment_type = request.form.get('appointment_type')
    appointment_date = request.form.get('appointment_date')
    start_time = request.form.get('start_time')
    mode = request.form.get('mode')
    notes = request.form.get('notes')
    
    # Validate required fields
    if not all([appointment_type, appointment_date, start_time, mode]):
        return jsonify({
            'status': 'error',
            'message': 'Please fill in all required fields'
        }), 400
    
    try:
        # Convert string inputs to proper datetime objects
        preferred_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        preferred_time = datetime.strptime(start_time, '%H:%M').time()
        
        # Calculate end time (1 hour duration)
        end_time = (datetime.combine(datetime.min, preferred_time) + timedelta(hours=1)).time()
        
        # Validate appointment date is not in the past
        if preferred_date < datetime.now().date():
            return jsonify({
                'status': 'error',
                'message': 'Cannot schedule appointments in the past'
            }), 400
            
        # Check counsellor's schedule for the requested day
        day_of_week = preferred_date.strftime('%A')
        
        counsellor_schedule = CounsellorSchedule.query.filter_by(
            counsellor_id=counsellor_id,
            day_of_week=day_of_week
        ).first()
        
        if not counsellor_schedule:
            return jsonify({
                'status': 'error',
                'message': f'Counsellor is not available on {day_of_week}'
            }), 400
            
        # Check if time is within counsellor's working hours
        if (preferred_time < counsellor_schedule.start_time or 
            end_time > counsellor_schedule.end_time):
            return jsonify({
                'status': 'error',
                'message': 'Selected time is outside counsellor\'s working hours'
            }), 400
            
        # Check for existing appointments at the same time
        existing_appointment = Appointment.query.filter_by(
            counsellor_id=counsellor_id,
            appointment_date=preferred_date,
            start_time=preferred_time,
            status='scheduled'
        ).first()
        
        if existing_appointment:
            return jsonify({
                'status': 'error',
                'message': 'This time slot is already booked. Please choose another time.'
            }), 400
        
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
            user_type='counsellor',
            message=f'New appointment request from {current_user.first_name} {current_user.last_name} for {preferred_date.strftime("%B %d, %Y")} at {preferred_time.strftime("%I:%M %p")}',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(counsellor_notification)
        
        # For student
        student_notification = Notification(
            user_id=student_id,
            user_type='student',
            message=f'Your appointment request for {preferred_date.strftime("%B %d, %Y")} at {preferred_time.strftime("%I:%M %p")} has been submitted.',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(student_notification)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Appointment request submitted successfully'
        })
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': 'Invalid date or time format'
        }), 400
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': 'Failed to submit appointment request. Please try again.'
        }), 500

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
    if not isinstance(current_user, Student):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('auth.login'))

    # Get career goals for the student
    career_goals = CareerGoal.query.filter_by(student_id=current_user.id).all()
    
    # Get assigned counsellor's schedule
    counsellor_schedule = None
    if current_user.counsellor_id:
        counsellor_schedule = CounsellorSchedule.query.filter_by(
            counsellor_id=current_user.counsellor_id
        ).order_by(CounsellorSchedule.day_of_week).all()

    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.student_id == current_user.id,
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date, Appointment.start_time).all()

    # Get pending appointment requests
    pending_requests = AppointmentRequest.query.filter_by(
        student_id=current_user.id,
        status='pending'
    ).all()

    # Get recent grievances
    recent_grievances = Grievance.query.filter_by(
        student_id=current_user.id
    ).order_by(Grievance.created_at.desc()).limit(5).all()

    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.now().date()
    ).order_by(Event.event_date, Event.start_time).all()

    # Get student's event registrations
    student_registrations = EventRegistration.query.filter_by(
        student_id=current_user.id
    ).all()
    
    # Create a dictionary of event registrations for easy lookup
    event_registrations = {reg.event_id: reg for reg in student_registrations}

    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read_status=False
    ).count()

    # Get recent feedback history
    recent_feedback = Feedback.query.filter_by(
        student_id=current_user.id
    ).order_by(Feedback.created_at.desc()).limit(5).all()

    # Get assigned tasks
    assigned_tasks = Task.query.filter_by(
        student_id=current_user.id
    ).order_by(Task.due_date.asc()).all()

    return render_template('student/dashboard.html',
                         student=current_user,
                         career_goals=career_goals,
                         counsellor_schedule=counsellor_schedule,
                         upcoming_appointments=upcoming_appointments,
                         pending_requests=pending_requests,
                         recent_grievances=recent_grievances,
                         upcoming_events=upcoming_events,
                         event_registrations=event_registrations,
                         unread_notifications=unread_notifications,
                         recent_feedback=recent_feedback,
                         assigned_tasks=assigned_tasks)

@student_bp.route('/student/notifications')
@login_required
def notifications():
    # Get page number from request args, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of notifications per page
    
    # Get paginated notifications for this student
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get unread notifications count for the navbar
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        read_status=False
    ).count()
    
    return render_template('student/notifications.html', 
                         notifications=notifications,
                         unread_notifications=unread_count)

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

@student_bp.route('/student/notifications/load', methods=['GET'])
@login_required
def load_notifications():
    # Get the most recent 5 notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    return jsonify({
        'notifications': [{
            'id': notification.notification_id,
            'message': notification.message,
            'type': notification.notification_type,
            'related_entity_id': notification.related_entity_id,
            'created_at': notification.created_at.isoformat(),
            'read': notification.read_status
        } for notification in notifications]
    })

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
    try:
        # Find the appointment request
        appointment_request = AppointmentRequest.query.filter_by(
            id=request_id,
            student_id=current_user.id,
            status='pending'
        ).first()

        if not appointment_request:
            return jsonify({
                'status': 'error',
                'message': 'Appointment request not found or not pending'
            }), 404
        
        # Update the request status
        appointment_request.status = 'cancelled'
        
        # Create notification for counselor
        counselor_notification = Notification(
            user_id=appointment_request.counselor_id,
            user_type='counsellor',
            message=f'Appointment request for {appointment_request.preferred_date.strftime("%B %d, %Y")} at {appointment_request.preferred_time.strftime("%I:%M %p")} has been cancelled by the student.',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(counselor_notification)
        
        # Create notification for student
        student_notification = Notification(
            user_id=current_user.id,
            user_type='student',
            message=f'You have cancelled your appointment request for {appointment_request.preferred_date.strftime("%B %d, %Y")} at {appointment_request.preferred_time.strftime("%I:%M %p")}.',
            notification_type='appointment',
            related_entity_id=appointment_request.id,
            created_at=datetime.now()
        )
        db.session.add(student_notification)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Appointment request cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to cancel appointment request. Please try again.'
        }), 500

@student_bp.route('/feedback/check-weekly', methods=['GET'])
@login_required
@student_required
def check_weekly_feedback():
    # Get the student's ID
    student_id = int(current_user.get_id().split('-')[1])
    
    # Get the last feedback submission
    last_feedback = Feedback.query.filter_by(
        student_id=student_id
    ).order_by(Feedback.created_at.desc()).first()
    
    # Check if feedback is due
    feedback_due = False
    if not last_feedback:
        feedback_due = True
    else:
        # Check if it's been a week since last feedback
        week_ago = datetime.now() - timedelta(days=7)
        if last_feedback.created_at < week_ago:
            feedback_due = True
    
    # Get the most recent feedback for display
    recent_feedback = None
    if last_feedback:
        recent_feedback = {
            'rating': last_feedback.rating,
            'comments': last_feedback.comments,
            'created_at': last_feedback.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    return jsonify({
        'feedback_due': feedback_due,
        'recent_feedback': recent_feedback,
        'next_feedback_date': (last_feedback.created_at + timedelta(days=7)).strftime('%Y-%m-%d') if last_feedback else None
    })

@student_bp.route('/feedback/submit-weekly', methods=['POST'])
@login_required
@student_required
def submit_weekly_feedback():
    try:
        # Get the student's ID and counsellor ID
        student_id = int(current_user.get_id().split('-')[1])
        counsellor_id = current_user.counsellor_id
        
        if not counsellor_id:
            return jsonify({
                'status': 'error',
                'message': 'No counsellor assigned'
            }), 400
        
        # Check if a feedback was already submitted in the last 7 days
        last_feedback = Feedback.query.filter_by(
            student_id=student_id
        ).order_by(Feedback.created_at.desc()).first()
        
        if last_feedback:
            week_ago = datetime.now() - timedelta(days=7)
            if last_feedback.created_at > week_ago:
                next_feedback_date = (last_feedback.created_at + timedelta(days=7)).strftime('%Y-%m-%d')
                return jsonify({
                    'status': 'error',
                    'message': f'You can submit your next feedback on {next_feedback_date}'
                }), 400
        
        # Get form data
        rating = request.form.get('rating')
        comments = request.form.get('comments')
        
        if not rating or not comments:
            return jsonify({
                'status': 'error',
                'message': 'Rating and comments are required'
            }), 400
        
        # Create new feedback
        feedback = Feedback(
            student_id=student_id,
            counsellor_id=counsellor_id,
            rating=int(rating),
            comments=comments,
            created_at=datetime.now()
        )
        
        db.session.add(feedback)
        
        # Create notification for counsellor
        notification = Notification(
            user_id=counsellor_id,
            user_type='counsellor',
            message=f'New weekly feedback received from {current_user.first_name} {current_user.last_name}',
            notification_type='feedback',
            related_entity_id=feedback.feedback_id,
            created_at=datetime.now()
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback submitted successfully',
            'next_feedback_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@student_bp.route('/student/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
@student_required
def complete_task(task_id):
    task = Task.query.filter_by(
        task_id=task_id,
        student_id=current_user.id
    ).first_or_404()
    
    try:
        task.status = 'Completed'
        task.completed_at = datetime.now()
        
        notification = Notification(
            user_id=current_user.counsellor_id,
            user_type='counsellor',
            message=f'Student {current_user.first_name} {current_user.last_name} completed task: {task.title}',
            notification_type='general',
            related_entity_id=task.task_id,
            read_status=False,
            created_at=datetime.now()
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task marked as completed'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500