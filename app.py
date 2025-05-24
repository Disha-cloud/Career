from flask import Flask, render_template
from flask_login import LoginManager
from models import db, Student, CareerCounsellor, Administrator
from config import Config
from routes import register_blueprints
from routes.auth import auth_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Register all blueprints
register_blueprints(app)

app.register_blueprint(auth_bp)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

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

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=5001)
