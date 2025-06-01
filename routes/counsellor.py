from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import CareerCounsellor, db, CounsellorSchedule, Student, Appointment, AppointmentRequest, Administrator, Notification, Task
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os
import random
import string

counsellor_bp = Blueprint('counsellor', __name__, url_prefix='/counsellor')

def counsellor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_id().startswith('counsellor-'):
            flash('Access denied. Counsellor privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@counsellor_bp.route('/login', methods=['GET'])
def login():
    return render_template('auth/login.html')

@counsellor_bp.route('/registration-success')
def registration_success():
    return render_template('counsellor/regs.html')

@counsellor_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.form.get('full_name', '').split()
            first_name = full_name[0] if full_name else ''
            last_name = ' '.join(full_name[1:]) if len(full_name) > 1 else ''
            email = request.form.get('email')
            password = request.form.get('password')
            qualification = request.form.get('qualifications')
            years_of_experience = request.form.get('experience')
            bio = request.form.get('bio')
            phone = request.form.get('phone')
            languages = request.form.get('languages')
            
            # Get specializations
            specializations = request.form.getlist('specializations')
            specialization = ', '.join(specializations)

            # Check if email already exists
            if CareerCounsellor.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return render_template('counsellor/register.html')

            # Create new counsellor
            counsellor = CareerCounsellor(
                email=email,
                first_name=first_name,
                last_name=last_name,
                specialization=specialization,
                qualification=qualification,
                years_of_experience=int(years_of_experience),
                bio=bio,
                availability_status=True,
                date_registered=datetime.utcnow()
            )
            counsellor.set_password(password)

            # Add to database
            db.session.add(counsellor)
            db.session.commit()

            # Handle availability schedule
            availability = request.form.getlist('availability')
            for day in availability:
                schedule = CounsellorSchedule(
                    counsellor_id=counsellor.id,
                    day_of_week=day,
                    start_time=datetime.strptime('09:00', '%H:%M').time(),  # Default 9 AM
                    end_time=datetime.strptime('17:00', '%H:%M').time(),    # Default 5 PM
                    is_recurring=True
                )
                db.session.add(schedule)
            
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('counsellor.registration_success'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration', 'danger')
            return render_template('counsellor/register.html')

    return render_template('counsellor/register.html')

@counsellor_bp.route('/dashboard')
@login_required
@counsellor_required
def dashboard():
    # Get counsellor's ID from current_user
    counsellor_id = int(current_user.get_id().split('-')[1])
    
    # Get statistics
    stats = {
        'total_students': Student.query.filter_by(counsellor_id=counsellor_id).count(),
        'upcoming_appointments': Appointment.query.filter(
            Appointment.counsellor_id == counsellor_id,
            Appointment.appointment_date >= datetime.now().date(),
            Appointment.status == 'scheduled'
        ).count(),
        'pending_requests': AppointmentRequest.query.filter_by(
            counsellor_id=counsellor_id,
            status='pending'
        ).count()
    }
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.counsellor_id == counsellor_id,
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date, Appointment.start_time).all()
    
    # Get pending appointment requests
    appointment_requests = AppointmentRequest.query.filter_by(
        counsellor_id=counsellor_id,
        status='pending'
    ).order_by(AppointmentRequest.preferred_date).all()
    
    # Get assigned students
    assigned_students = Student.query.filter_by(
        counsellor_id=counsellor_id,
        is_active=True
    ).all()
    
    # Get counsellor's schedule
    schedule = CounsellorSchedule.query.filter_by(
        counsellor_id=counsellor_id
    ).order_by(CounsellorSchedule.day_of_week).all()
    
    # Get assigned tasks
    assigned_tasks = Task.query.join(Student).filter(
        Student.counsellor_id == counsellor_id
    ).order_by(Task.due_date.asc()).all()
    
    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(
        user_id=counsellor_id,
        read_status=False
    ).count()
    
    return render_template('counsellor/dashboard.html',
                         counsellor=current_user,
                         stats=stats,
                         upcoming_appointments=upcoming_appointments,
                         appointment_requests=appointment_requests,
                         assigned_students=assigned_students,
                         schedule=schedule,
                         assigned_tasks=assigned_tasks,
                         unread_notifications=unread_notifications)

@counsellor_bp.route('/appointments/schedule', methods=['POST'])
@login_required
@counsellor_required
def schedule_appointment():
    print("\n=== Starting Appointment Scheduling ===")
    try:
        # Debug: Print all form data
        print("Form data received:", request.form)
        
        # Get form data
        student_id = request.form.get('student_id')
        appointment_type = request.form.get('appointment_type')
        date = request.form.get('date')
        time = request.form.get('time')
        mode = request.form.get('mode')
        location = request.form.get('location', '')

        print("Extracted form data:", {
            'student_id': student_id,
            'appointment_type': appointment_type,
            'date': date,
            'time': time,
            'mode': mode,
            'location': location
        })

        # Validate required fields
        required_fields = {'student_id': student_id, 
                         'appointment_type': appointment_type, 
                         'date': date, 
                         'time': time, 
                         'mode': mode}
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Convert string inputs to proper datetime objects
        try:
            print(f"Converting date '{date}' and time '{time}' to datetime objects")
            appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
            start_time = datetime.strptime(time, '%H:%M').time()
            print(f"Converted to: date={appointment_date}, time={start_time}")
        except ValueError as e:
            print(f"DateTime conversion error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Invalid date or time format'
            }), 400

        # Validate date is not in the past
        if appointment_date < datetime.now().date():
            print(f"Past date validation failed: {appointment_date} < {datetime.now().date()}")
            return jsonify({
                'success': False,
                'message': 'Cannot schedule appointments in the past'
            }), 400

        # Calculate end time (1 hour duration)
        end_time = (datetime.combine(datetime.min, start_time) + timedelta(hours=1)).time()
        print(f"Calculated end time: {end_time}")

        # Check counsellor's schedule for the requested day
        day_of_week = appointment_date.strftime('%A')
        print(f"Checking schedule for {day_of_week}")
        
        counsellor_schedule = CounsellorSchedule.query.filter_by(
            counsellor_id=current_user.id,
            day_of_week=day_of_week
        ).first()

        if not counsellor_schedule:
            print(f"No schedule found for {day_of_week}")
            return jsonify({
                'success': False,
                'message': f'You are not available on {day_of_week}s'
            }), 400

        print("Found counsellor schedule:", {
            'start_time': counsellor_schedule.start_time,
            'end_time': counsellor_schedule.end_time
        })

        # Check if time is within working hours
        if (start_time < counsellor_schedule.start_time or 
            end_time > counsellor_schedule.end_time):
            print(f"Time validation failed: start={start_time}, end={end_time}")
            print(f"Working hours: {counsellor_schedule.start_time} - {counsellor_schedule.end_time}")
            return jsonify({
                'success': False,
                'message': 'Selected time is outside your working hours'
            }), 400

        # Check for existing appointments
        print("Checking for existing appointments")
        existing_appointment = Appointment.query.filter_by(
            counsellor_id=current_user.id,
            appointment_date=appointment_date,
            start_time=start_time,
            status='scheduled'
        ).first()

        if existing_appointment:
            print(f"Found conflicting appointment: {existing_appointment.id}")
            return jsonify({
                'success': False,
                'message': 'This time slot is already booked'
            }), 400

        print("Creating new appointment")
        # Create appointment
        appointment = Appointment(
            student_id=student_id,
            counsellor_id=current_user.id,
            appointment_type=appointment_type,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            mode=mode,
            location=location,
            status='scheduled'
        )
        db.session.add(appointment)

        print("Creating notification")
        # Create notification for student
        notification = Notification(
            user_id=student_id,
            user_type='student',
            message=f'New appointment scheduled with your counsellor for {appointment_date.strftime("%B %d, %Y")} at {start_time.strftime("%I:%M %p")}',
            notification_type='appointment',
            related_entity_id=appointment.id
        )
        db.session.add(notification)
        
        print("Committing to database")
        db.session.commit()

        print("=== Appointment Scheduling Completed Successfully ===\n")
        return jsonify({
            'success': True,
            'message': 'Appointment scheduled successfully'
        })

    except Exception as e:
        db.session.rollback()
        print("\n=== Appointment Scheduling Error ===")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        print("=====================================\n")
        return jsonify({
            'success': False,
            'message': 'Failed to schedule appointment'
        }), 500

@counsellor_bp.route('/approve_request/<int:request_id>', methods=['POST'])
@login_required
@counsellor_required
def approve_request(request_id):
    try:
        # Get counsellor ID from current_user
        counsellor_id = int(current_user.get_id().split('-')[1])
        
        # First check if request exists at all
        request = AppointmentRequest.query.get(request_id)
        if not request:
            print(f"Request {request_id} not found")
            return jsonify({
                'success': False,
                'message': 'Appointment request not found'
            }), 404
            
        # Then check if it belongs to this counsellor
        if request.counsellor_id != counsellor_id:
            print(f"Request {request_id} belongs to counsellor {request.counsellor_id}, not {counsellor_id}")
            return jsonify({
                'success': False,
                'message': 'This request is not assigned to you'
            }), 403
            
        # Finally check if it's still pending
        if request.status != 'pending':
            print(f"Request {request_id} is not pending (status: {request.status})")
            return jsonify({
                'success': False,
                'message': f'This request has already been {request.status}'
            }), 400
        
        print(f"Processing approval for request {request_id}")
        print(f"Request details: date={request.preferred_date}, time={request.preferred_time}, student={request.student_id}")
        
        # Calculate end time (1 hour duration)
        end_time = (datetime.combine(datetime.min, request.preferred_time) + timedelta(hours=1)).time()
        
        # Create appointment
        appointment = Appointment(
            student_id=request.student_id,
            counsellor_id=counsellor_id,
            appointment_type=request.appointment_type,
            appointment_date=request.preferred_date,
            start_time=request.preferred_time,
            end_time=end_time,
            mode=request.mode,
            status='scheduled'
        )
        
        # Set location or meeting link based on mode
        if request.mode == 'online':
            appointment.meeting_link = 'https://meet.google.com/' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        elif request.mode == 'offline':
            appointment.location = 'Counselling Office'
            
        db.session.add(appointment)
        
        # Update request status
        request.status = 'approved'
        request.updated_at = datetime.now()
        
        # Create notification for student
        notification = Notification(
            user_id=request.student_id,
            user_type='student',
            message=f'Your appointment request for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")} has been approved.',
            notification_type='appointment',
            related_entity_id=appointment.id
        )
        db.session.add(notification)
        
        # Create notification for counsellor
        counsellor_notification = Notification(
            user_id=counsellor_id,
            user_type='counsellor',
            message=f'You have approved the appointment request for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")}',
            notification_type='appointment',
            related_entity_id=appointment.id
        )
        db.session.add(counsellor_notification)
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully approved request {request_id} and created appointment")
        
        return jsonify({
            'success': True,
            'message': 'Appointment request approved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in approve_request: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': 'Failed to approve appointment request'
        }), 500

@counsellor_bp.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
@counsellor_required
def reject_request(request_id):
    try:
        # Find the appointment request
        request = AppointmentRequest.query.filter_by(
            id=request_id,
            counsellor_id=current_user.id,
            status='pending'
        ).first_or_404()
        
        # Update request status
        request.status = 'rejected'
        
        # Create notification for student
        notification = Notification(
            user_id=request.student_id,
            message=f'Your appointment request for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")} has been rejected.',
            notification_type='appointment',
            related_entity_id=request.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Appointment request rejected successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to reject appointment request'
        }), 500

@counsellor_bp.route('/students/<int:student_id>')
@login_required
@counsellor_required
def view_student(student_id):
    student = Student.query.get_or_404(student_id)
    if student.counsellor_id != int(current_user.get_id().split('-')[1]):
        flash('Access denied. This student is not assigned to you.', 'danger')
        return redirect(url_for('counsellor.dashboard'))
    return render_template('counsellor/student_profile.html', student=student)

@counsellor_bp.route('/schedule')
@login_required
@counsellor_required
def edit_schedule():
    counsellor_id = int(current_user.get_id().split('-')[1])
    schedule = CounsellorSchedule.query.filter_by(counsellor_id=counsellor_id).all()
    return render_template('counsellor/schedule.html', schedule=schedule)

@counsellor_bp.route('/appointments/<int:appointment_id>/complete', methods=['POST'])
@login_required
@counsellor_required
def complete_appointment(appointment_id):
    try:
        # Get the appointment
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            counsellor_id=int(current_user.get_id().split('-')[1]),
            status='scheduled'
        ).first_or_404()
        
        # Update appointment status
        appointment.status = 'completed'
        
        # Create notification for student
        notification = Notification(
            user_id=appointment.student_id,
            user_type='student',
            message=f'Your appointment on {appointment.appointment_date.strftime("%B %d, %Y")} at {appointment.start_time.strftime("%I:%M %p")} has been marked as completed.',
            notification_type='appointment',
            related_entity_id=appointment.id,
            created_at=datetime.now()
        )
        db.session.add(notification)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@counsellor_bp.route('/schedule/update', methods=['POST'])
@login_required
@counsellor_required
def update_schedule():
    try:
        data = request.get_json()
        print(f"Received schedule update data: {data}")  # Debug log
        
        if not isinstance(data, dict):
            return jsonify({
                'status': 'error',
                'message': 'Invalid data format'
            }), 400
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No schedule data provided'
            }), 400
        
        counsellor_id = int(current_user.get_id().split('-')[1])
        schedules_updated = 0
        
        # Start transaction
        db.session.begin_nested()
        
        # Get the days that are included in the request
        days_in_request = set()
        for key in data.keys():
            if '_start' in key:
                days_in_request.add(key.replace('_start', ''))
        
        print(f"Days included in request: {days_in_request}")  # Debug log
        
        # Process only the days included in the request
        for day in days_in_request:
            start_key = f'{day}_start'
            end_key = f'{day}_end'
            
            # If either time is empty for a day, remove that day's schedule
            if not data.get(start_key) or not data.get(end_key):
                # Remove schedule for this day if it exists
                deleted = CounsellorSchedule.query.filter_by(
                    counsellor_id=counsellor_id,
                    day_of_week=day.capitalize()
                ).delete()
                if deleted:
                    print(f"Removed schedule for {day}")  # Debug log
                    schedules_updated += 1
                continue
                
            try:
                start_time = datetime.strptime(data[start_key], '%H:%M').time()
                end_time = datetime.strptime(data[end_key], '%H:%M').time()
                
                # Validate times
                if start_time >= end_time:
                    raise ValueError(f'End time must be after start time for {day}')
                
                # Find existing schedule for this day
                schedule = CounsellorSchedule.query.filter_by(
                    counsellor_id=counsellor_id,
                    day_of_week=day.capitalize()
                ).first()
                
                if schedule:
                    # Update existing schedule
                    schedule.start_time = start_time
                    schedule.end_time = end_time
                    print(f"Updated schedule for {day}: {start_time} - {end_time}")  # Debug log
                else:
                    # Create new schedule
                    schedule = CounsellorSchedule(
                        counsellor_id=counsellor_id,
                        day_of_week=day.capitalize(),
                        start_time=start_time,
                        end_time=end_time,
                        is_recurring=True
                    )
                    db.session.add(schedule)
                    print(f"Created new schedule for {day}: {start_time} - {end_time}")  # Debug log
                
                schedules_updated += 1
                
            except ValueError as e:
                db.session.rollback()
                print(f"Error updating schedule for {day}: {str(e)}")  # Debug log
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid time format for {day}: {str(e)}'
                }), 400
        
        if schedules_updated == 0:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'No valid schedule days provided'
            }), 400
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully updated {schedules_updated} schedule entries")  # Debug log
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully updated {schedules_updated} schedule entries'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in update_schedule: {str(e)}")  # Debug log
        return jsonify({
            'status': 'error',
            'message': 'Failed to update schedule'
        }), 500

@counsellor_bp.route('/notifications/load')
@login_required
@counsellor_required
def load_notifications():
    try:
        counsellor_id = int(current_user.get_id().split('-')[1])
        
        # Get notifications for this counsellor
        notifications = Notification.query.filter_by(
            user_id=counsellor_id,
            user_type='counsellor'
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        # Format notifications
        formatted_notifications = [{
            'id': n.notification_id,
            'message': n.message,
            'type': n.notification_type,
            'read': n.read_status,
            'created_at': n.created_at.isoformat(),
            'related_entity_id': n.related_entity_id
        } for n in notifications]
        
        return jsonify({'notifications': formatted_notifications})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@counsellor_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
@counsellor_required
def mark_notification_read(notification_id):
    try:
        counsellor_id = int(current_user.get_id().split('-')[1])
        
        # Get and update notification
        notification = Notification.query.filter_by(
            notification_id=notification_id,
            user_id=counsellor_id,
            user_type='counsellor'
        ).first_or_404()
        
        notification.read_status = True
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@counsellor_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
@counsellor_required
def mark_all_notifications_read():
    try:
        counsellor_id = int(current_user.get_id().split('-')[1])
        
        # Update all unread notifications
        Notification.query.filter_by(
            user_id=counsellor_id,
            user_type='counsellor',
            read_status=False
        ).update({'read_status': True})
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@counsellor_bp.route('/assign_task', methods=['POST'])
@login_required
@counsellor_required
def assign_task():
    try:
        print("Starting task assignment...")  # Debug print
        
        # Get form data
        student_id = request.form.get('student_id')
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority')
        category = request.form.get('category')

        print(f"Received form data: student_id={student_id}, title={title}, due_date={due_date}, priority={priority}, category={category}")  # Debug print

        # Validate required fields
        if not all([student_id, title, due_date, priority, category]):
            missing_fields = [field for field, value in {
                'student_id': student_id,
                'title': title,
                'due_date': due_date,
                'priority': priority,
                'category': category
            }.items() if not value]
            print(f"Missing required fields: {missing_fields}")  # Debug print
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        try:
            # Convert due_date string to date object
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            print(f"Converted due_date: {due_date}")  # Debug print
        except ValueError as e:
            print(f"Error parsing due_date: {str(e)}")  # Debug print
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD'
            }), 400

        # Create new task
        task = Task(
            student_id=student_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            category=category,
            status='Pending'
        )

        print("Created task object")  # Debug print

        # Add task to database
        db.session.add(task)
        print("Added task to session")  # Debug print

        # Create notification for student
        notification = Notification(
            user_id=student_id,
            user_type='student',
            message=f'New task assigned: {title}',
            notification_type='general',
            related_entity_id=task.task_id
        )
        db.session.add(notification)
        print("Added notification to session")  # Debug print

        # Commit changes
        db.session.commit()
        print("Committed changes to database")  # Debug print

        return jsonify({
            'success': True,
            'message': 'Task assigned successfully'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error assigning task: {str(e)}")  # Debug print
        print(f"Error type: {type(e)}")  # Debug print
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Debug print
        return jsonify({
            'success': False,
            'message': 'Failed to assign task'
        }), 500

@counsellor_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
@counsellor_required
def delete_task(task_id):
    try:
        # Get task and verify it belongs to a student assigned to this counsellor
        counsellor_id = int(current_user.get_id().split('-')[1])
        task = Task.query.join(Student).filter(
            Task.task_id == task_id,
            Student.counsellor_id == counsellor_id
        ).first_or_404()
        
        # Create notification for student
        notification = Notification(
            user_id=task.student_id,
            user_type='student',
            message=f'Task deleted: {task.title}',
            notification_type='general',
            related_entity_id=None
        )
        db.session.add(notification)
        
        # Delete task
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500