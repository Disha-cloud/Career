from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Student, CareerCounsellor, Administrator, Appointment, Event, Grievance, Notification, AppointmentRequest, EventRegistration, CareerGoal, GoalMilestone, StudentDocument, Feedback, CounsellingSession, Message
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import desc

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin-only decorator
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
        return redirect(url_for('auth.login'))

    # Get statistics
    stats = {
        'total_students': Student.query.count(),
        'active_students': Student.query.filter_by(is_active=True).count(),
        'inactive_students': Student.query.filter_by(is_active=False).count(),
        'total_counsellors': CareerCounsellor.query.count(),
        'active_counsellors': CareerCounsellor.query.filter_by(availability_status=True).count(),
        'inactive_counsellors': CareerCounsellor.query.filter_by(availability_status=False).count(),
        'active_sessions': Appointment.query.filter_by(status='scheduled').count(),
        'pending_grievances': Grievance.query.filter_by(status='Pending').count()
    }

    # Get all students with their counsellors
    all_students = Student.query.options(db.joinedload(Student.counsellor)).order_by(Student.date_registered.desc()).all()

    # Get all counsellors
    all_counsellors = CareerCounsellor.query.order_by(CareerCounsellor.date_registered.desc()).all()

    # Get active counsellors for replacement selection
    active_counsellors = CareerCounsellor.query.filter_by(availability_status=True).all()

    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date, Appointment.start_time).all()

    # Get pending appointment requests
    pending_requests = AppointmentRequest.query.filter_by(status='pending').all()

    # Get recent grievances
    recent_grievances = Grievance.query.order_by(Grievance.created_at.desc()).limit(5).all()

    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.now().date()
    ).order_by(Event.event_date, Event.start_time).all()

    return render_template('admin/dashboard.html',
                         stats=stats,
                         all_students=all_students,
                         all_counsellors=all_counsellors,
                         active_counsellors=active_counsellors,
                         upcoming_appointments=upcoming_appointments,
                         pending_requests=pending_requests,
                         recent_grievances=recent_grievances,
                         upcoming_events=upcoming_events)

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
    # Get counsellor's students
    assigned_students = Student.query.filter_by(counsellor_id=counsellor_id).all()
    # Get counsellor's upcoming appointments
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

        # Store old counsellor ID for notification
        old_counsellor_id = student.counsellor_id

        # Update student's counsellor
        student.counsellor_id = counsellor_id
        db.session.commit()

        # Create notifications
        # For new counsellor
        new_counsellor_notification = Notification(
            user_id=counsellor_id,
            message=f'New student {student.first_name} {student.last_name} has been assigned to you.',
            notification_type='assignment',
            related_entity_id=student.id
        )
        db.session.add(new_counsellor_notification)

        # For old counsellor
        if old_counsellor_id:
            old_counsellor_notification = Notification(
                user_id=old_counsellor_id,
                message=f'Student {student.first_name} {student.last_name} has been reassigned to another counsellor.',
                notification_type='assignment',
                related_entity_id=student.id
            )
            db.session.add(old_counsellor_notification)

        # For student
        student_notification = Notification(
            user_id=student.id,
            message=f'You have been assigned to a new counsellor: {counsellor.first_name} {counsellor.last_name}.',
            notification_type='assignment',
            related_entity_id=counsellor.id
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
    
    # Get unread notifications count
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
        # Mark specific notification as read
        notification = Notification.query.filter_by(
            notification_id=notification_id,
            user_id=current_user.id
        ).first_or_404()
        notification.read_status = True
    else:
        # Mark all notifications as read
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
    
    # Update the grievance status
    grievance.status = new_status
    
    # Create notification for student
    notification = Notification(
        user_id=grievance.student_id,
        message=f'Your grievance has been marked as {new_status}.',
        notification_type='grievance',
        related_entity_id=grievance.id
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
        # Find and delete the registration
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
        
        # Delete related records first
        # Delete event registrations
        EventRegistration.query.filter_by(student_id=student_id).delete()
        
        # Delete appointments
        Appointment.query.filter_by(student_id=student_id).delete()
        
        # Delete appointment requests
        AppointmentRequest.query.filter_by(student_id=student_id).delete()
        
        # Delete grievances
        Grievance.query.filter_by(student_id=student_id).delete()
        
        # Delete notifications
        Notification.query.filter_by(user_id=student_id).delete()
        
        # Delete career goals and their milestones
        goals = CareerGoal.query.filter_by(student_id=student_id).all()
        for goal in goals:
            GoalMilestone.query.filter_by(goal_id=goal.goal_id).delete()
        CareerGoal.query.filter_by(student_id=student_id).delete()
        
        # Finally, delete the student
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
    print(f"[DEBUG] Starting student status toggle for student_id: {student_id}")
    
    if not isinstance(current_user, Administrator):
        print("[DEBUG] Unauthorized access attempt - not an administrator")
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    student = Student.query.get_or_404(student_id)
    print(f"[DEBUG] Found student: {student.first_name} {student.last_name}, current status: {student.is_active}")
    
    try:
        # Begin transaction
        print("[DEBUG] Starting nested transaction")
        db.session.begin_nested()
        
        # Toggle student status
        student.is_active = not student.is_active
        print(f"[DEBUG] Toggled student status to: {student.is_active}")
        
        if not student.is_active:
            print("[DEBUG] Deactivating student - starting cleanup process")
            
            try:
                # Delete appointment requests first (no dependencies)
                requests_deleted = AppointmentRequest.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {requests_deleted} appointment requests")
                
                # Get all appointments for this student
                appointments = Appointment.query.filter_by(student_id=student_id).all()
                appointment_ids = [appointment.id for appointment in appointments]
                print(f"[DEBUG] Found {len(appointment_ids)} appointments to process")
                
                # Get all counselling sessions for these appointments
                if appointment_ids:
                    sessions = CounsellingSession.query.filter(
                        CounsellingSession.appointment_id.in_(appointment_ids)
                    ).all()
                    session_ids = [session.session_id for session in sessions]
                    print(f"[DEBUG] Found {len(session_ids)} counselling sessions to process")
                    
                    # Delete feedback first (depends on counselling sessions)
                    if session_ids:
                        feedback_deleted = Feedback.query.filter(
                            Feedback.session_id.in_(session_ids)
                        ).delete(synchronize_session='fetch')
                        print(f"[DEBUG] Deleted {feedback_deleted} feedback records linked to sessions")
                    
                    # Now safe to delete counselling sessions
                    sessions_deleted = CounsellingSession.query.filter(
                        CounsellingSession.appointment_id.in_(appointment_ids)
                    ).delete(synchronize_session='fetch')
                    print(f"[DEBUG] Deleted {sessions_deleted} counselling sessions")
                
                # Now safe to delete appointments
                appointments_deleted = Appointment.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {appointments_deleted} appointments")
                
                # Delete grievances
                grievances_deleted = Grievance.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {grievances_deleted} grievances")
                
                # Delete event registrations
                registrations_deleted = EventRegistration.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {registrations_deleted} event registrations")
                
                # Delete remaining feedback not linked to sessions
                remaining_feedback_deleted = Feedback.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {remaining_feedback_deleted} remaining feedback records")
                
                # Delete career goals and milestones
                goals = CareerGoal.query.filter_by(student_id=student_id).all()
                milestones_deleted = 0
                for goal in goals:
                    print(f"[DEBUG] Processing goal_id: {goal.goal_id}")
                    milestones_count = GoalMilestone.query.filter_by(goal_id=goal.goal_id).delete()
                    milestones_deleted += milestones_count
                goals_deleted = CareerGoal.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {goals_deleted} career goals and {milestones_deleted} milestones")
                
                # Delete documents
                documents_deleted = StudentDocument.query.filter_by(student_id=student_id).delete()
                print(f"[DEBUG] Deleted {documents_deleted} student documents")
                
                # Delete notifications
                notifications_deleted = Notification.query.filter_by(user_id=student_id).delete()
                print(f"[DEBUG] Deleted {notifications_deleted} notifications")
                
                # Delete messages
                messages_deleted = Message.query.filter(
                    (Message.sender_id == student_id) | 
                    (Message.recipient_id == student_id)
                ).delete()
                print(f"[DEBUG] Deleted {messages_deleted} messages")
                
                print("[DEBUG] Successfully completed all cleanup operations")
                
            except Exception as cleanup_error:
                print(f"[DEBUG] Error during cleanup: {str(cleanup_error)}")
                raise
            
            flash(f'Student {student.first_name} {student.last_name} has been deactivated and all related records have been removed.', 'success')
        else:
            print(f"[DEBUG] Activating student {student.first_name} {student.last_name}")
            flash(f'Student {student.first_name} {student.last_name} has been activated.', 'success')
        
        # Commit all changes
        print("[DEBUG] Committing all changes")
        db.session.commit()
        print("[DEBUG] Successfully committed all changes")
        
    except Exception as e:
        print(f"[DEBUG] Error occurred: {str(e)}")
        print("[DEBUG] Rolling back transaction")
        db.session.rollback()
        flash(f'Error updating student status: {str(e)}', 'danger')
    
    print("[DEBUG] Redirecting to dashboard")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/counsellor/<int:counsellor_id>/toggle-status', methods=['POST'])
@login_required
def toggle_counsellor_status(counsellor_id):
    if not isinstance(current_user, Administrator):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    counsellor = CareerCounsellor.query.get_or_404(counsellor_id)
    
    try:
        # Begin transaction
        db.session.begin_nested()
        
        # Toggle counsellor status
        new_status = not counsellor.availability_status
        counsellor.availability_status = new_status
        
        if not new_status:  # Deactivating counsellor
            # Get the replacement counsellor ID from form
            new_counsellor_id = request.form.get('new_counsellor_id')
            
            if not new_counsellor_id:
                flash('Please select a replacement counsellor', 'danger')
                return redirect(url_for('admin.dashboard'))
            
            new_counsellor = CareerCounsellor.query.get(new_counsellor_id)
            if not new_counsellor or not new_counsellor.availability_status:
                flash('Invalid replacement counsellor selected', 'danger')
                return redirect(url_for('admin.dashboard'))
            
            # Count students before reassignment
            students_count = Student.query.filter_by(counsellor_id=counsellor_id).count()
            
            # Reassign all students to the new counsellor
            update_result = Student.query.filter_by(counsellor_id=counsellor_id).update({'counsellor_id': new_counsellor_id})
            
            # Get and reassign future appointments
            future_appointments = Appointment.query.filter(
                Appointment.counsellor_id == counsellor_id,
                Appointment.appointment_date >= datetime.now().date(),
                Appointment.status == 'scheduled'
            ).all()
            
            for appointment in future_appointments:
                # Create notification for student
                notification = Notification(
                    user_id=appointment.student_id,
                    message=f'Your appointment on {appointment.appointment_date} has been reassigned to {new_counsellor.first_name} {new_counsellor.last_name} due to counsellor unavailability.',
                    notification_type='appointment',
                    related_entity_id=appointment.id
                )
                db.session.add(notification)
                
                # Update appointment
                appointment.counsellor_id = new_counsellor_id
            
            # Reassign pending appointment requests
            pending_requests_count = AppointmentRequest.query.filter_by(
                counsellor_id=counsellor_id,
                status='pending'
            ).update({'counsellor_id': new_counsellor_id})
            
            # Create notifications
            # For new counsellor
            new_counsellor_notification = Notification(
                user_id=new_counsellor_id,
                message=f'You have been assigned {students_count} students and {len(future_appointments)} appointments from {counsellor.first_name} {counsellor.last_name} who is now unavailable.',
                notification_type='general',
                related_entity_id=counsellor_id
            )
            db.session.add(new_counsellor_notification)
            
            # For reassigned students
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
        
        # Commit all changes
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating counsellor status: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/student/<int:student_id>/reassign-counsellor', methods=['POST'])
@login_required
def reassign_student_counsellor(student_id):
    print(f"[DEBUG] Starting counsellor reassignment for student_id: {student_id}")
    
    if not isinstance(current_user, Administrator):
        print("[DEBUG] Unauthorized access attempt - not an administrator")
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    student = Student.query.get_or_404(student_id)
    print(f"[DEBUG] Found student: {student.first_name} {student.last_name}")
    
    new_counsellor_id = request.form.get('new_counsellor_id')
    print(f"[DEBUG] Requested new counsellor_id: {new_counsellor_id}")
    
    if not new_counsellor_id:
        print("[DEBUG] Error: No new counsellor selected")
        flash('Please select a new counsellor', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Begin transaction
        print("[DEBUG] Starting nested transaction")
        db.session.begin_nested()
        
        # Get the new counsellor
        new_counsellor = CareerCounsellor.query.get(new_counsellor_id)
        if not new_counsellor or not new_counsellor.availability_status:
            print(f"[DEBUG] Error: Invalid counsellor or unavailable. Found: {new_counsellor}, Status: {new_counsellor.availability_status if new_counsellor else 'None'}")
            flash('Invalid counsellor selected', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        print(f"[DEBUG] New counsellor found: {new_counsellor.first_name} {new_counsellor.last_name}")
        
        # Store old counsellor info for reference
        old_counsellor = student.counsellor
        print(f"[DEBUG] Current counsellor: {old_counsellor.first_name} {old_counsellor.last_name if old_counsellor else 'None'}")
        
        # Update student's counsellor
        student.counsellor_id = new_counsellor_id
        print("[DEBUG] Updated student's counsellor_id")
        
        try:
            # Create notifications - only for student since notifications table is linked to students
            print("[DEBUG] Creating notifications")
            
            # For student - notifying about new counsellor
            print(f"[DEBUG] Creating notification for student with ID: {student.id}")
            student_notification = Notification(
                user_id=int(student.id),
                message=f'You have been assigned to a new counsellor: {new_counsellor.first_name} {new_counsellor.last_name}.',
                notification_type='general',
                related_entity_id=new_counsellor.id
            )
            db.session.add(student_notification)
            print("[DEBUG] Added notification for student about new counsellor")
            
            # Note: We'll handle counsellor notifications through a different mechanism
            print("[DEBUG] Note: Counsellor notifications will be handled through email/dashboard updates")
            
        except Exception as notification_error:
            print(f"[DEBUG] Error creating notifications: {str(notification_error)}")
            raise
        
        try:
            # Reassign future appointments
            print("[DEBUG] Processing future appointments")
            future_appointments = Appointment.query.filter(
                Appointment.student_id == student_id,
                Appointment.appointment_date >= datetime.now().date(),
                Appointment.status == 'scheduled'
            ).all()
            
            print(f"[DEBUG] Found {len(future_appointments)} future appointments to reassign")
            
            for appointment in future_appointments:
                print(f"[DEBUG] Processing appointment ID: {appointment.id} on {appointment.appointment_date}")
                # Create notification for student about appointment reassignment
                appointment_notification = Notification(
                    user_id=int(student.id),
                    message=f'Your appointment on {appointment.appointment_date} has been reassigned to {new_counsellor.first_name} {new_counsellor.last_name}.',
                    notification_type='appointment',
                    related_entity_id=appointment.id
                )
                db.session.add(appointment_notification)
                
                # Update appointment
                appointment.counsellor_id = new_counsellor_id
                print(f"[DEBUG] Updated appointment ID: {appointment.id} to new counsellor")
            
        except Exception as appointment_error:
            print(f"[DEBUG] Error processing appointments: {str(appointment_error)}")
            raise
        
        try:
            # Reassign pending appointment requests
            print("[DEBUG] Processing pending appointment requests")
            pending_requests = AppointmentRequest.query.filter_by(
                student_id=student_id,
                status='pending'
            ).update({'counsellor_id': new_counsellor_id})
            print(f"[DEBUG] Updated {pending_requests} pending appointment requests")
            
        except Exception as request_error:
            print(f"[DEBUG] Error updating appointment requests: {str(request_error)}")
            raise
        
        print("[DEBUG] Committing all changes")
        db.session.commit()
        print("[DEBUG] Successfully committed all changes")
        
        flash(f'Successfully reassigned {student.first_name} {student.last_name} to counsellor {new_counsellor.first_name} {new_counsellor.last_name}', 'success')
        
        # TODO: Implement counsellor notification through a different mechanism
        # This could be through email, a separate counsellor_notifications table,
        # or by modifying the notifications table to support both user types
        
    except Exception as e:
        print(f"[DEBUG] Error occurred: {str(e)}")
        print("[DEBUG] Rolling back transaction")
        db.session.rollback()
        flash(f'Error reassigning counsellor: {str(e)}', 'danger')
    
    print("[DEBUG] Redirecting to dashboard")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    print(f"[DEBUG] Starting event deletion for event_id: {event_id}")
    
    if not isinstance(current_user, Administrator):
        print("[DEBUG] Unauthorized access attempt - not an administrator")
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Begin transaction
        print("[DEBUG] Starting nested transaction")
        db.session.begin_nested()
        
        # Get the event
        event = Event.query.get_or_404(event_id)
        print(f"[DEBUG] Found event: {event.title} on {event.event_date}")
        
        # Get all registrations for this event
        registrations = EventRegistration.query.filter_by(event_id=event_id).all()
        registered_students = [reg.student_id for reg in registrations]
        print(f"[DEBUG] Found {len(registrations)} registrations to process")
        
        try:
            # Delete all registrations first
            if registered_students:
                # Create notifications for registered students
                for student_id in registered_students:
                    notification = Notification(
                        user_id=int(student_id),
                        message=f'The event "{event.title}" scheduled for {event.event_date.strftime("%B %d, %Y")} has been cancelled.',
                        notification_type='general',
                        related_entity_id=event_id
                    )
                    db.session.add(notification)
                print(f"[DEBUG] Created notifications for {len(registered_students)} students")
                
                # Delete registrations
                deleted_registrations = EventRegistration.query.filter_by(event_id=event_id).delete()
                print(f"[DEBUG] Deleted {deleted_registrations} event registrations")
        
        except Exception as reg_error:
            print(f"[DEBUG] Error processing registrations: {str(reg_error)}")
            raise
        
        try:
            # Delete the event
            db.session.delete(event)
            print("[DEBUG] Deleted event")
            
        except Exception as event_error:
            print(f"[DEBUG] Error deleting event: {str(event_error)}")
            raise
        
        # Commit all changes
        print("[DEBUG] Committing all changes")
        db.session.commit()
        print("[DEBUG] Successfully committed all changes")
        
        flash(f'Successfully deleted event "{event.title}" and all related registrations.', 'success')
        
    except Exception as e:
        print(f"[DEBUG] Error occurred: {str(e)}")
        print("[DEBUG] Rolling back transaction")
        db.session.rollback()
        flash(f'Error deleting event: {str(e)}', 'danger')
    
    print("[DEBUG] Redirecting to dashboard")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    print("[DEBUG] Starting create_event route")
    print(f"[DEBUG] Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            # Log form data
            print("[DEBUG] Form data received:")
            for key, value in request.form.items():
                print(f"[DEBUG] {key}: {value}")
            
            # Get form data
            title = request.form.get('title')
            description = request.form.get('description')
            event_date_str = request.form.get('event_date')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            location = request.form.get('location')
            event_type = request.form.get('event_type')
            max_participants = request.form.get('max_participants')
            
            print(f"[DEBUG] Parsed values:")
            print(f"[DEBUG] Title: {title}")
            print(f"[DEBUG] Event date string: {event_date_str}")
            print(f"[DEBUG] Start time string: {start_time_str}")
            print(f"[DEBUG] End time string: {end_time_str}")
            
            # Parse date and times
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                
                print(f"[DEBUG] Parsed date/times:")
                print(f"[DEBUG] Event date: {event_date}")
                print(f"[DEBUG] Start time: {start_time}")
                print(f"[DEBUG] End time: {end_time}")
            except ValueError as e:
                print(f"[DEBUG] Error parsing date/time: {str(e)}")
                raise
            
            # Convert max_participants to int if provided
            capacity = None
            if max_participants:
                try:
                    capacity = int(max_participants)
                    print(f"[DEBUG] Capacity: {capacity}")
                except ValueError:
                    print("[DEBUG] Error converting max_participants to int")
            
            print("[DEBUG] Creating new event object")
            # Create new event
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
                counsellor_id=None  # Optional: Set this if you want to assign a counsellor
            )
            
            print("[DEBUG] Adding event to session")
            db.session.add(new_event)
            
            print("[DEBUG] Committing to database")
            db.session.commit()
            
            print("[DEBUG] Event created successfully")
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"[DEBUG] Error creating event: {str(e)}")
            print(f"[DEBUG] Error type: {type(e)}")
            import traceback
            print("[DEBUG] Full traceback:")
            print(traceback.format_exc())
            
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
            return redirect(url_for('admin.create_event'))
    
    # GET request - render the create event form
    print("[DEBUG] GET request - rendering form")
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('admin/create_event.html', today=today)

@admin_bp.route('/appointment-request/<int:request_id>/<action>', methods=['POST'])
@login_required
@admin_required
def handle_appointment_request(request_id, action):
    print(f"[DEBUG] Handling appointment request {request_id} with action {action}")
    
    if action not in ['approve', 'reject']:
        print(f"[DEBUG] Invalid action: {action}")
        flash('Invalid action', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        request = AppointmentRequest.query.get_or_404(request_id)
        print(f"[DEBUG] Found request: {request}")
        
        if action == 'approve':
            print("[DEBUG] Approving request")
            # Create new appointment
            appointment = Appointment(
                student_id=request.student_id,
                counsellor_id=request.counsellor_id,
                appointment_date=request.preferred_date,
                start_time=request.preferred_time,
                end_time=(datetime.combine(request.preferred_date, request.preferred_time) + timedelta(hours=1)).time(),
                appointment_type=request.appointment_type,
                status='scheduled'
            )
            db.session.add(appointment)
            
            # Create notification for student
            student_notification = Notification(
                user_id=request.student_id,
                message=f'Your appointment request has been approved for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")}',
                notification_type='appointment',
                related_entity_id=appointment.id
            )
            db.session.add(student_notification)
            
            # Create notification for counsellor
            counsellor_notification = Notification(
                user_id=request.counsellor_id,
                message=f'New appointment scheduled for {request.preferred_date.strftime("%B %d, %Y")} at {request.preferred_time.strftime("%I:%M %p")}',
                notification_type='appointment',
                related_entity_id=appointment.id
            )
            db.session.add(counsellor_notification)
            
            flash('Appointment request approved and scheduled', 'success')
        else:
            print("[DEBUG] Rejecting request")
            # Create rejection notification for student
            student_notification = Notification(
                user_id=request.student_id,
                message=f'Your appointment request for {request.preferred_date.strftime("%B %d, %Y")} has been rejected',
                notification_type='appointment',
                related_entity_id=request.id
            )
            db.session.add(student_notification)
            
            flash('Appointment request rejected', 'info')
        
        # Delete the request
        db.session.delete(request)
        db.session.commit()
        print("[DEBUG] Successfully processed request")
        
    except Exception as e:
        print(f"[DEBUG] Error processing request: {str(e)}")
        db.session.rollback()
        flash(f'Error processing request: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))