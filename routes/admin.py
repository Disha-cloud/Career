from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import (
    db, Student, CareerCounsellor, Administrator, Appointment, Event, 
    Grievance, Notification, AppointmentRequest, EventRegistration, 
    CareerGoal, GoalMilestone, StudentDocument, Feedback, Message, StudentResourceAccess
)
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import desc
import os
from flask import current_app

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_id().startswith('admin-'):
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard')
@login_required
def dashboard():
    if not isinstance(current_user, Administrator):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('main.index'))

    
    counsellors = CareerCounsellor.query.all()
    
    
    students = Student.query.all()
    
    
    recent_grievances = Grievance.query.order_by(Grievance.created_at.desc()).limit(10).all()
    
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.now().date()
    ).order_by(Appointment.appointment_date, Appointment.start_time).all()
    
    
    pending_requests = AppointmentRequest.query.filter_by(status='pending').all()
    
    
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.now().date()
    ).options(
        db.joinedload(Event.registrations).joinedload(EventRegistration.student)
    ).order_by(Event.event_date, Event.start_time).all()

    
    stats = {
        'total_students': Student.query.count(),
        'total_counsellors': CareerCounsellor.query.count()
    }

    
    all_students = Student.query.all()
    active_counsellors = CareerCounsellor.query.filter_by(availability_status=True).all()

    return render_template('admin/dashboard.html',
                         counsellors=counsellors,
                         students=students,
                         recent_grievances=recent_grievances,
                         upcoming_appointments=upcoming_appointments,
                         pending_requests=pending_requests,
                         upcoming_events=upcoming_events,
                         stats=stats,
                         all_students=all_students,
                         active_counsellors=active_counsellors)

@admin_bp.route('/manage-users')
@login_required
@admin_required
def manage_users():
    students = Student.query.all()
    counsellors = CareerCounsellor.query.all()
    return render_template('admin/manage_users.html',
                         students=students,
                         counsellors=counsellors)

@admin_bp.route('/manage-counsellor/<int:counsellor_id>')
@login_required
@admin_required
def manage_counsellor(counsellor_id):
    counsellor = CareerCounsellor.query.get_or_404(counsellor_id)
    
    assigned_students = Student.query.filter_by(counsellor_id=counsellor_id).all()
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.counsellor_id == counsellor_id,
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date.asc()).all()
    return render_template('admin/manage_counsellor.html',
                         counsellor=counsellor,
                         assigned_students=assigned_students,
                         upcoming_appointments=upcoming_appointments)

@admin_bp.route('/api/admin/reassign-counsellor', methods=['POST'])
@login_required
@admin_required
def reassign_counsellor():
    data = request.get_json()
    student_id = data.get('student_id')
    counsellor_id = data.get('counsellor_id')

    if not student_id or not counsellor_id:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    try:
        student = Student.query.get(student_id)
        counsellor = CareerCounsellor.query.get(counsellor_id)

        if not student or not counsellor:
            return jsonify({'success': False, 'message': 'Student or counsellor not found'}), 404

        
        old_counsellor_id = student.counsellor_id

        
        student.counsellor_id = counsellor_id
        db.session.commit()


        new_counsellor_notification = Notification(
            user_id=counsellor_id,
            user_type='counsellor',
            message=f'New student {student.first_name} {student.last_name} has been assigned to you.',
            notification_type='assignment',
            related_entity_id=student.id,
            created_at=datetime.now()
        )
        db.session.add(new_counsellor_notification)

        
        if old_counsellor_id:
            old_counsellor_notification = Notification(
                user_id=old_counsellor_id,
                user_type='counsellor',
                message=f'Student {student.first_name} {student.last_name} has been reassigned to another counsellor.',
                notification_type='assignment',
                related_entity_id=student.id,
                created_at=datetime.now()
            )
            db.session.add(old_counsellor_notification)

        
        student_notification = Notification(
            user_id=student.id,
            user_type='student',
            message=f'You have been assigned to a new counsellor: {counsellor.first_name} {counsellor.last_name}.',
            notification_type='assignment',
            related_entity_id=counsellor.id,
            created_at=datetime.now()
        )
        db.session.add(student_notification)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Counsellor reassigned successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/notifications')
@login_required
@admin_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read_status=False
    ).count()
    
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
        'assignment': 'fa-user-plus',
        'general': 'fa-bell'
    }
    
    return render_template('admin/notifications.html',
                         notifications=notifications,
                         notification_icons=notification_icons,
                         unread_notifications=unread_notifications)

@admin_bp.route('/admin/notifications/mark-read', methods=['POST'])
@login_required
@admin_required
def mark_notifications_read():
    notification_id = request.json.get('notification_id')
    
    if notification_id:
        
        notification = Notification.query.filter_by(
            notification_id=notification_id,
            user_id=current_user.id
        ).first_or_404()
        notification.read_status = True
    else:
        
        Notification.query.filter_by(
            user_id=current_user.id,
            read_status=False
        ).update({'read_status': True})
    
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/grievance/<int:grievance_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_grievance_status(grievance_id):
    grievance = Grievance.query.get_or_404(grievance_id)
    new_status = request.form.get('new_status')
    
    if new_status not in ['In Progress', 'Resolved']:
        flash('Invalid status value.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    
    grievance.status = new_status
    
   
    notification = Notification(
        user_id=grievance.student_id,
        user_type='student',
        message=f'Your grievance has been marked as {new_status}.',
        notification_type='grievance',
        related_entity_id=grievance.id,
        created_at=datetime.now()
    )
    
    db.session.add(notification)
    
    try:
        db.session.commit()
        flash(f'Grievance status updated to {new_status}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating grievance status', 'danger')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/events/<int:event_id>/registrations/<int:student_id>', methods=['DELETE'])
@login_required
@admin_required
def remove_event_registration(event_id, student_id):
    try:
        
        registration = EventRegistration.query.filter_by(
            event_id=event_id,
            student_id=student_id
        ).first_or_404()
        
        db.session.delete(registration)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration removed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/delete', methods=['DELETE'])
@login_required
@admin_required
def delete_student(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        
        
        
        EventRegistration.query.filter_by(student_id=student_id).delete()
        
        
        Appointment.query.filter_by(student_id=student_id).delete()
        
        
        AppointmentRequest.query.filter_by(student_id=student_id).delete()
        
        
        Grievance.query.filter_by(student_id=student_id).delete()
        
        
        Notification.query.filter_by(user_id=student_id).delete()
        
        
        goals = CareerGoal.query.filter_by(student_id=student_id).all()
        for goal in goals:
            GoalMilestone.query.filter_by(goal_id=goal.goal_id).delete()
        CareerGoal.query.filter_by(student_id=student_id).delete()
        
        
        db.session.delete(student)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Student {student.first_name} {student.last_name} and all related records have been deleted'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': f'Error deleting student: {str(e)}'
        }), 500

@admin_bp.route('/admin/student/<int:student_id>/toggle-status', methods=['POST'])
@login_required
def toggle_student_status(student_id):
    if not isinstance(current_user, Administrator):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    student = Student.query.get_or_404(student_id)
    
    try:
        
        db.session.begin_nested()
        
        
        student.is_active = not student.is_active
        
        if not student.is_active:
            
            messages_deleted = Message.query.filter(
                (Message.sender_id == student.id) | 
                (Message.recipient_id == student.id)
            ).delete()
            
            
            notifications_deleted = Notification.query.filter_by(
                user_id=student.id
            ).delete()
            
            
            feedback_deleted = Feedback.query.filter_by(
                student_id=student.id
            ).delete()
            
            
            requests_deleted = AppointmentRequest.query.filter_by(
                student_id=student.id
            ).delete()
            
            
            appointments_deleted = Appointment.query.filter_by(
                student_id=student.id
            ).delete()
            
            
            grievances_deleted = Grievance.query.filter_by(
                student_id=student.id
            ).delete()
            
            
            registrations_deleted = EventRegistration.query.filter_by(
                student_id=student.id
            ).delete()
            
            
            goals_deleted = 0
            milestones_deleted = 0
            for goal in CareerGoal.query.filter_by(student_id=student.id).all():
                milestones_deleted += GoalMilestone.query.filter_by(goal_id=goal.goal_id).delete()
                goals_deleted += 1
            CareerGoal.query.filter_by(student_id=student.id).delete()
            
            
            documents_deleted = 0
            for doc in StudentDocument.query.filter_by(student_id=student.id).all():
                try:
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.file_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                documents_deleted += 1
            StudentDocument.query.filter_by(student_id=student.id).delete()
            
            
            resource_access_deleted = StudentResourceAccess.query.filter_by(
                student_id=student.id
            ).delete()
        
        db.session.commit()
        flash('Student status updated successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to update student status', 'danger')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/counsellor/<int:counsellor_id>/toggle-status', methods=['POST'])
@login_required
def toggle_counsellor_status(counsellor_id):
    if not isinstance(current_user, Administrator):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    counsellor = CareerCounsellor.query.get_or_404(counsellor_id)
    
    try:
        
        db.session.begin_nested()
        
        
        new_status = not counsellor.availability_status
        counsellor.availability_status = new_status
        
        if not new_status:  
            
            new_counsellor_id = request.form.get('new_counsellor_id')
            
            if not new_counsellor_id:
                flash('Please select a replacement counsellor', 'danger')
                return redirect(url_for('admin.dashboard'))
            
            new_counsellor = CareerCounsellor.query.get(new_counsellor_id)
            if not new_counsellor or not new_counsellor.availability_status:
                flash('Invalid replacement counsellor selected', 'danger')
                return redirect(url_for('admin.dashboard'))
            
            
            students_count = Student.query.filter_by(counsellor_id=counsellor_id).count()
            
            
            update_result = Student.query.filter_by(counsellor_id=counsellor_id).update({'counsellor_id': new_counsellor_id})
            
            
            future_appointments = Appointment.query.filter(
                Appointment.counsellor_id == counsellor_id,
                Appointment.appointment_date >= datetime.now().date(),
                Appointment.status == 'scheduled'
            ).all()
            
            for appointment in future_appointments:
                
                notification = Notification(
                    user_id=appointment.student_id,
                    message=f'Your appointment on {appointment.appointment_date} has been reassigned to {new_counsellor.first_name} {new_counsellor.last_name} due to counsellor unavailability.',
                    notification_type='appointment',
                    related_entity_id=appointment.id
                )
                db.session.add(notification)
                
                
                appointment.counsellor_id = new_counsellor_id
            
            
            pending_requests_count = AppointmentRequest.query.filter_by(
                counsellor_id=counsellor_id,
                status='pending'
            ).update({'counsellor_id': new_counsellor_id})
            
            
            
            new_counsellor_notification = Notification(
                user_id=new_counsellor_id,
                message=f'You have been assigned {students_count} students and {len(future_appointments)} appointments from {counsellor.first_name} {counsellor.last_name} who is now unavailable.',
                notification_type='general',
                related_entity_id=counsellor_id
            )
            db.session.add(new_counsellor_notification)
            
            
            reassigned_students = Student.query.filter_by(counsellor_id=new_counsellor_id).all()
            for student in reassigned_students:
                student_notification = Notification(
                    user_id=student.id,
                    message=f'Your counsellor has been changed to {new_counsellor.first_name} {new_counsellor.last_name} as your previous counsellor is no longer available.',
                    notification_type='general',
                    related_entity_id=new_counsellor_id
                )
                db.session.add(student_notification)
            
            success_message = f'Counsellor {counsellor.first_name} {counsellor.last_name} has been deactivated. '
            success_message += f'Transferred {students_count} students, {len(future_appointments)} appointments, '
            success_message += f'and {pending_requests_count} pending requests to {new_counsellor.first_name} {new_counsellor.last_name}.'
            flash(success_message, 'success')
        else:
            flash(f'Counsellor {counsellor.first_name} {counsellor.last_name} has been activated.', 'success')
        
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating counsellor status: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/student/<int:student_id>/reassign-counsellor', methods=['POST'])
@login_required
def reassign_student_counsellor(student_id):
    print(f"Reassignment request received for student {student_id}")
    print(f"Current user: {current_user}")
    
    if not isinstance(current_user, Administrator):
        print("Access denied: User is not an administrator")
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    
    student = Student.query.get_or_404(student_id)
    print(f"Found student: {student.first_name} {student.last_name}")
    
    
    new_counsellor_id = request.form.get('new_counsellor_id')
    reason = request.form.get('reason')
    print(f"New counsellor ID: {new_counsellor_id}")
    print(f"Form data: {request.form}")
    
    if not new_counsellor_id:
        print("Error: No counsellor ID provided")
        flash('New counsellor ID is required', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        
        db.session.begin_nested()
        print("Transaction started")
        
        
        new_counsellor = CareerCounsellor.query.get(new_counsellor_id)
        if not new_counsellor or not new_counsellor.availability_status:
            print(f"Error: Invalid counsellor or counsellor not available. Counsellor found: {new_counsellor}")
            flash('Invalid counsellor selected or counsellor is not available', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        print(f"Found new counsellor: {new_counsellor.first_name} {new_counsellor.last_name}")
        
        
        old_counsellor = CareerCounsellor.query.get(student.counsellor_id) if student.counsellor_id else None
        print(f"Old counsellor: {old_counsellor.first_name if old_counsellor else 'None'} {old_counsellor.last_name if old_counsellor else ''}")
        
        
        student.counsellor_id = new_counsellor_id
        print("Updated student's counsellor ID")
        
        try:
            
            student_notification = Notification(
                user_id=student.id,
                user_type='student',
                message=f'You have been assigned to a new counsellor: {new_counsellor.first_name} {new_counsellor.last_name}',
                notification_type='general',
                related_entity_id=new_counsellor_id
            )
            db.session.add(student_notification)
            print("Added student notification")
            
            
            new_counsellor_notification = Notification(
                user_id=new_counsellor_id,
                user_type='counsellor',
                message=f'New student assigned: {student.first_name} {student.last_name}',
                notification_type='general',
                related_entity_id=student.id
            )
            db.session.add(new_counsellor_notification)
            print("Added new counsellor notification")
            
            
            if old_counsellor:
                old_counsellor_notification = Notification(
                    user_id=old_counsellor.id,
                    user_type='counsellor',
                    message=f'Student {student.first_name} {student.last_name} has been reassigned to another counsellor',
                    notification_type='general',
                    related_entity_id=student.id
                )
                db.session.add(old_counsellor_notification)
                print("Added old counsellor notification")
            
            db.session.commit()
            print("Committed all changes successfully")
            flash('Counsellor reassigned successfully', 'success')
            
        except Exception as notification_error:
            print(f"Notification error: {str(notification_error)}")
            db.session.rollback()
            flash('Failed to create notifications', 'warning')
        
    except Exception as e:
        print(f"Error during reassignment: {str(e)}")
        db.session.rollback()
        flash('Failed to reassign counsellor', 'danger')
    
    print("Redirecting to dashboard")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if not isinstance(current_user, Administrator):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        
        db.session.begin_nested()
        
        event = Event.query.get_or_404(event_id)
        
        try:
            
            registrations = EventRegistration.query.filter_by(event_id=event_id).all()
            
            
            registered_students = []
            for registration in registrations:
                notification = Notification(
                    user_id=registration.student_id,
                    user_type='student',
                    message=f'Event "{event.title}" scheduled for {event.event_date.strftime("%B %d, %Y")} has been cancelled.',
                    notification_type='event',
                    related_entity_id=event_id
                )
                db.session.add(notification)
                registered_students.append(registration.student_id)
            
            
            deleted_registrations = EventRegistration.query.filter_by(event_id=event_id).delete()
            
        except Exception as reg_error:
            db.session.rollback()
            flash('Failed to process event registrations', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        try:
            
            db.session.delete(event)
            db.session.commit()
            flash('Event deleted successfully', 'success')
            
        except Exception as event_error:
            db.session.rollback()
            flash('Failed to delete event', 'danger')
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete event', 'danger')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    if request.method == 'POST':
        try:
            
            title = request.form.get('title')
            description = request.form.get('description')
            event_date_str = request.form.get('event_date')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            location = request.form.get('location')
            event_type = request.form.get('event_type')
            max_participants = request.form.get('max_participants')
            
            
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError as e:
                raise
            
            
            capacity = None
            if max_participants:
                try:
                    capacity = int(max_participants)
                except ValueError:
                    pass
            
            
            new_event = Event(
                title=title,
                description=description,
                event_type=event_type,
                event_date=event_date,
                start_time=start_time,
                end_time=end_time,
                location=location,
                capacity=capacity,
                is_online=False if location else True,
                counsellor_id=None  
            )
            
            db.session.add(new_event)
            
            db.session.commit()
            
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
            return redirect(url_for('admin.create_event'))
    
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('admin/create_event.html', today=today)

@admin_bp.route('/appointment-requests/<int:request_id>/<action>', methods=['POST'])
@login_required
@admin_required
def handle_appointment_request(request_id, action):
    if action not in ['approve', 'reject']:
        flash('Invalid action', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        request = AppointmentRequest.query.get_or_404(request_id)
        
        if action == 'approve':
           
            request.status = 'approved'
            
            
            appointment = Appointment(
                student_id=request.student_id,
                counsellor_id=request.counsellor_id,
                appointment_date=request.preferred_date,
                start_time=request.preferred_time,
                end_time=(datetime.combine(request.preferred_date, request.preferred_time) + timedelta(hours=1)).time(),
                appointment_type=request.appointment_type,
                mode=request.mode,
                status='scheduled'
            )
            
            
            if request.mode == 'online':
                appointment.meeting_link = 'https://meet.link/appointment'  
            elif request.mode == 'offline':
                appointment.location = 'Counselling Room'  
            
            db.session.add(appointment)
            
           
            student_notification = Notification(
                user_id=request.student_id,
                user_type='student',
                message=f'Your appointment request has been approved for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")}',
                notification_type='appointment',
                related_entity_id=appointment.id
            )
            db.session.add(student_notification)
            
            
            counsellor_notification = Notification(
                user_id=request.counsellor_id,
                user_type='counsellor',
                message=f'New appointment scheduled for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")}',
                notification_type='appointment',
                related_entity_id=appointment.id
            )
            db.session.add(counsellor_notification)
            
            flash('Appointment request approved and scheduled', 'success')
        else:
            
            request.status = 'rejected'
            
            
            student_notification = Notification(
                user_id=request.student_id,
                user_type='student',
                message=f'Your appointment request for {request.preferred_date.strftime("%B %d, %Y")} has been rejected',
                notification_type='appointment',
                related_entity_id=request.id
            )
            db.session.add(student_notification)
            
            flash('Appointment request rejected', 'info')
        
        
        db.session.commit()
        db.session.delete(request)
        db.session.commit()
        
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing request: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))
