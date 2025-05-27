from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import CareerCounsellor, db, CounsellorSchedule, Student, Appointment, AppointmentRequest, CounsellingSession, Administrator, Notification
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os

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
        'total_students': len(current_user.students),
        'upcoming_appointments': Appointment.query.filter(
            Appointment.counsellor_id == counsellor_id,
            Appointment.appointment_date >= datetime.now().date(),
            Appointment.status == 'scheduled'
        ).count(),
        'pending_requests': AppointmentRequest.query.filter_by(
            counsellor_id=counsellor_id,
            status='pending'
        ).count(),
        'completed_sessions': CounsellingSession.query.join(Appointment).filter(
            Appointment.counsellor_id == counsellor_id
        ).count()
    }
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.counsellor_id == counsellor_id,
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc()).all()
    
    # Get pending appointment requests
    appointment_requests = AppointmentRequest.query.filter_by(
        counsellor_id=counsellor_id,
        status='pending'
    ).order_by(AppointmentRequest.created_at.desc()).all()
    
    # Get assigned students
    assigned_students = Student.query.filter_by(counsellor_id=counsellor_id).all()
    
    # Get counsellor's schedule
    schedule = CounsellorSchedule.query.filter_by(counsellor_id=counsellor_id).all()
    
    return render_template('counsellor/dashboard.html',
                         counsellor=current_user,
                         stats=stats,
                         upcoming_appointments=upcoming_appointments,
                         appointment_requests=appointment_requests,
                         assigned_students=assigned_students,
                         schedule=schedule)

@counsellor_bp.route('/appointments/schedule', methods=['POST'])
@login_required
@counsellor_required
def schedule_appointment():
    try:
        student_id = request.form.get('student_id')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        time = datetime.strptime(request.form.get('time'), '%H:%M').time()
        mode = request.form.get('mode')
        location = request.form.get('location')
        
        # Create new appointment
        appointment = Appointment(
            student_id=student_id,
            counsellor_id=int(current_user.get_id().split('-')[1]),
            appointment_date=date,
            start_time=time,
            mode=mode,
            status='scheduled'
        )
        
        if mode == 'online':
            appointment.meeting_link = location
        else:
            appointment.location = location
            
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@counsellor_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@counsellor_required
def cancel_appointment(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        appointment.status = 'cancelled'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@counsellor_bp.route('/appointment-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@counsellor_required
def approve_request(request_id):
    try:
        request = AppointmentRequest.query.get_or_404(request_id)
        
        # Create new appointment from request
        appointment = Appointment(
            student_id=request.student_id,
            counsellor_id=request.counsellor_id,
            appointment_date=request.preferred_date,
            start_time=request.preferred_time,
            mode=request.mode,
            status='scheduled'
        )
        
        db.session.add(appointment)
        request.status = 'approved'
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@counsellor_bp.route('/appointment-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@counsellor_required
def reject_request(request_id):
    try:
        request = AppointmentRequest.query.get_or_404(request_id)
        request.status = 'rejected'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
        
        # Create counselling session record
        session = CounsellingSession(
            appointment_id=appointment.id,
            session_duration=60  # Default 1 hour duration
        )
        db.session.add(session)
        
        # Create notification for student
        notification = Notification(
            user_id=appointment.student_id,
            message=f'Your appointment on {appointment.appointment_date.strftime("%B %d, %Y")} at {appointment.start_time.strftime("%I:%M %p")} has been marked as completed.',
            notification_type='appointment',
            related_entity_id=appointment.id
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
        counsellor_id = int(current_user.get_id().split('-')[1])
        
        # Delete existing schedule
        CounsellorSchedule.query.filter_by(counsellor_id=counsellor_id).delete()
        
        # Create new schedule entries
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for day in weekdays:
            start_time = datetime.strptime(request.form.get(f'{day}_start'), '%H:%M').time()
            end_time = datetime.strptime(request.form.get(f'{day}_end'), '%H:%M').time()
            
            schedule = CounsellorSchedule(
                counsellor_id=counsellor_id,
                day_of_week=day.capitalize(),
                start_time=start_time,
                end_time=end_time,
                is_recurring=True
            )
            db.session.add(schedule)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})