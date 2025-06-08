from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, Student, CareerCounsellor, Administrator
from werkzeug.security import check_password_hash
from config import Config  

app = Flask(__name__)
app.config.from_object(Config)  
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'student_login'

@login_manager.user_loader
def load_user(user_id):
    if not user_id or '-' not in user_id:
        return None
    user_type, id = user_id.split('-', 1)
    if not id.isdigit():
        return None
    id = int(id)
    if user_type == 'student':
        return Student.query.get(id)
    elif user_type == 'counsellor':
        return CareerCounsellor.query.get(id)
    elif user_type == 'admin':
        return Administrator.query.get(id)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        user = None
        if user_type == 'student':
            user = Student.query.filter_by(email=email).first()
        elif user_type == 'counsellor':
            user = CareerCounsellor.query.filter_by(email=email).first()
        elif user_type == 'admin':
            user = Administrator.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user_type == 'student':
                return redirect(url_for('student_dashboard'))
            elif user_type == 'counsellor':
                return redirect(url_for('counsellor_dashboard'))
            elif user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('student/login.html')

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.get_id().startswith('student-'):
        return render_template('student/dashboard.html', student=current_user)
    flash('Access denied.', 'danger')
    return redirect(url_for('index'))

@app.route('/counsellor/dashboard')
@login_required
def counsellor_dashboard():
    if current_user.get_id().startswith('counsellor-'):
        return render_template('counsellor/dashboard.html', counsellor=current_user)
    flash('Access denied.', 'danger')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.get_id().startswith('admin-'):
        return render_template('admin/dashboard.html', admin=current_user)
    flash('Access denied.', 'danger')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
