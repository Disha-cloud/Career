from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Student, Counsellor, Administrator
from functools import wraps

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

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    if current_user.get_id().startswith('admin-'):
        # Get statistics
        stats = {
            'total_students': Student.query.count(),
            'total_counsellors': Counsellor.query.count(),
            'active_sessions': 0  # You can implement this based on your session tracking
        }

        # Get all students and counsellors for management
        students = Student.query.all()
        counsellors = Counsellor.query.all()

        return render_template('admin/dashboard.html',
                               admin=current_user,
                               stats=stats,
                               students=students,
                               counselors=counsellors)

    flash('Access denied.', 'danger')
    return redirect(url_for('index'))

@admin_bp.route('/manage-users')
@login_required
@admin_required
def manage_users():
    return render_template('admin/manage_users.html')

@admin_bp.route('/manage-counselor/<int:counselor_id>')
@login_required
@admin_required
def manage_counselor(counselor_id):
    counselor = Counsellor.query.get_or_404(counselor_id)
    return render_template('admin/manage_counselor.html', counselor=counselor)

@admin_bp.route('/api/admin/reassign-counselor', methods=['POST'])
@login_required
@admin_required
def reassign_counselor():
    data = request.get_json()
    student_id = data.get('student_id')
    counselor_id = data.get('counselor_id')

    if not student_id or not counselor_id:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    try:
        student = Student.query.get(student_id)
        counselor = Counsellor.query.get(counselor_id)

        if not student or not counselor:
            return jsonify({'success': False, 'message': 'Student or counselor not found'}), 404

        student.counselor_id = counselor_id
        db.session.commit()

        return jsonify({'success': True, 'message': 'Counselor reassigned successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
