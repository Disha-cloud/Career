from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required
from models import Student, CareerCounsellor, Administrator
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

auth_bp = Blueprint('auth', __name__)
db = SQLAlchemy()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Check if request is JSON
        if request.is_json:
            data = request.get_json()
            email = data.get('email', '').strip()
            password = data.get('password', '')
        else:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

        # Check if it's the admin email
        if Administrator.is_admin_email(email):
            user = Administrator.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('admin.dashboard')})
                return redirect(url_for('admin.dashboard'))
            else:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Invalid admin credentials.'}), 401
                flash('Invalid admin credentials.', 'danger')
                return render_template('auth/login.html')

        # Try to find user in student or counsellor tables
        user = Student.query.filter_by(email=email).first()
        user_type = 'student'
        
        if not user:
            user = CareerCounsellor.query.filter_by(email=email).first()
            user_type = 'counsellor'

        if user is None:
            if request.is_json:
                return jsonify({'success': False, 'message': 'No account found with that email.'}), 401
            flash('No account found with that email.', 'danger')
        elif not user.check_password(password):
            if request.is_json:
                return jsonify({'success': False, 'message': 'Incorrect password.'}), 401
            flash('Incorrect password.', 'danger')
        elif not user.is_active:  # Check if user is active
            if request.is_json:
                return jsonify({'success': False, 'message': 'Your account has been deactivated. Please contact the administrator.'}), 401
            flash('Your account has been deactivated. Please contact the administrator.', 'danger')
        else:
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            if user_type == 'student':
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('student.dashboard')})
                return redirect(url_for('student.dashboard'))
            elif user_type == 'counsellor':
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('counsellor.dashboard')})
                return redirect(url_for('counsellor.dashboard'))

        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid credentials.'}), 401

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index')) 