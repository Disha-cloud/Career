from flask import Flask, render_template, request
from flask_login import LoginManager
from models import db, Student, CareerCounsellor, Administrator
from config import Config
from routes import register_blueprints
from routes.auth import auth_bp
import logging
import sys
import os


if not os.path.exists('logs'):
    os.makedirs('logs')


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', mode='a')
    ]
)


logger = logging.getLogger(__name__)


logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
logging.getLogger('student_blueprint').setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object(Config)
app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
db.init_app(app)

logger.debug("=== Starting Flask Application ===")


logger.debug("Registering blueprints...")
register_blueprints(app)
app.register_blueprint(auth_bp)
logger.debug("Blueprints registered successfully")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    logger.debug(f"Loading user: {user_id}")
    if not user_id or '-' not in user_id:
        return None
    user_type, id = user_id.split('-', 1)
    if not id.isdigit():
        return None
    id = int(id)
    
    if user_type == 'student':
        return db.session.get(Student, id)
    elif user_type == 'counsellor':
        return db.session.get(CareerCounsellor, id)
    elif user_type == 'admin':
        return db.session.get(Administrator, id)
    return None

@app.before_request
def log_request_info():
    try:
        logger.debug('=== Request Information ===')
        logger.debug(f'Method: {request.method}')
        logger.debug(f'Path: {request.path}')
        logger.debug(f'Headers: {dict(request.headers)}')
        if request.is_json:
            logger.debug(f'JSON Body: {request.get_json()}')
        elif request.form:
            logger.debug(f'Form Data: {dict(request.form)}')
        elif request.data:
            logger.debug(f'Raw Data: {request.data}')
    except Exception as e:
        logger.error(f'Error logging request: {str(e)}')

@app.after_request
def log_response_info(response):
    try:
        logger.debug('=== Response Information ===')
        logger.debug(f'Status: {response.status}')
        logger.debug(f'Headers: {dict(response.headers)}')
    except Exception as e:
        logger.error(f'Error logging response: {str(e)}')
    return response

@app.route('/')
def index():
    logger.debug("Accessing index route")
    return render_template('index.html')

if __name__ == '__main__':
    logger.info("=== Starting Development Server ===")
    app.run(debug=True, host='0.0.0.0', port=5001)
