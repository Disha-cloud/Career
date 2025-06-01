from flask import Blueprint, render_template
from models import Event
from datetime import datetime

# Create Blueprint without a URL prefix
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/events')
def events():
    # Get all upcoming events ordered by date and time
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.now().date()
    ).order_by(Event.event_date, Event.start_time).all()
    
    return render_template('events.html', 
                         events=upcoming_events,
                         now=datetime.now()) 