from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import Student, CareerCounsellor, Administrator
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

auth_bp = Blueprint('auth', __name__)
db = SQLAlchemy()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Check if it's the admin email
        if Administrator.is_admin_email(email):
            user = Administrator.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Invalid admin credentials.', 'danger')
                return render_template('auth/login.html')

        # Try to find user in student or counsellor tables
        user = Student.query.filter_by(email=email).first()
        user_type = 'student'
        
        if not user:
            user = CareerCounsellor.query.filter_by(email=email).first()
            user_type = 'counsellor'

        if user is None:
            flash('No account found with that email.', 'danger')
        elif not user.check_password(password):
            flash('Incorrect password.', 'danger')
        else:
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            if user_type == 'student':
                return redirect(url_for('student.dashboard'))
            elif user_type == 'counsellor':
                return redirect(url_for('counsellor.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index')) 