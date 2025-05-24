from .student import student_bp
from .admin import admin_bp
from .counsellor import counsellor_bp

def register_blueprints(app):
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(counsellor_bp)