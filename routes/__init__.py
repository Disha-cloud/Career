from .student import student_bp
from .admin import admin_bp
from .counsellor import counsellor_bp
from .main import main_bp
from .messages import messages_bp

def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(counsellor_bp)
    app.register_blueprint(messages_bp)
