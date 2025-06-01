from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time

db = SQLAlchemy()

class CareerCounsellor(db.Model, UserMixin):
    __tablename__ = 'counsellors'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    specialization = db.Column(db.String(100))
    qualification = db.Column(db.Text)
    years_of_experience = db.Column(db.Integer)
    bio = db.Column(db.Text)
    availability_status = db.Column(db.Boolean, default=True)
    rating = db.Column(db.Numeric(3, 2))
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def get_id(self):
        return f"counsellor-{self.id}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model, UserMixin):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    dob = db.Column(db.Date)
    address = db.Column(db.Text)
    education_level = db.Column(db.String(100))
    interests = db.Column(db.Text)
    counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellors.id', ondelete='SET NULL'))
    course = db.Column(db.String(100))
    quiz_result = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    counsellor = db.relationship('CareerCounsellor', backref=db.backref('students', lazy=True), foreign_keys=[counsellor_id])

    def get_id(self):
        return f"student-{self.id}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def check_email_exists(email):
        """Check if an email exists in any user table (Student, CareerCounsellor, or Administrator)"""
        if Student.query.filter_by(email=email).first():
            return True, 'student'
        if CareerCounsellor.query.filter_by(email=email).first():
            return True, 'counsellor'
        if Administrator.query.filter_by(email=email).first():
            return True, 'administrator'
        return False, None

class Administrator(db.Model, UserMixin):
    __tablename__ = 'administrators'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    role_description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    @staticmethod
    def is_admin_email(email):
        """Check if an email belongs to an administrator"""
        return Administrator.query.filter_by(email=email).first() is not None

    def get_id(self):
        return f"admin-{self.id}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Grievance(db.Model):
    __tablename__ = 'grievances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('Pending', 'In Progress', 'Resolved'), default='Pending')
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', backref='grievances', foreign_keys=[student_id])

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellors.id', ondelete='CASCADE'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time)
    appointment_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum('scheduled', 'completed', 'cancelled', 'rescheduled'), default='scheduled')
    mode = db.Column(db.Enum('online', 'offline', 'phone'), nullable=False)
    meeting_link = db.Column(db.String(255))
    location = db.Column(db.String(255))

    # Relationships
    student = db.relationship('Student', backref=db.backref('appointments', lazy=True))
    counsellor = db.relationship('CareerCounsellor', backref=db.backref('appointments', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'counsellor_id': self.counsellor_id,
            'appointment_date': self.appointment_date,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'appointment_type': self.appointment_type,
            'status': self.status,
            'mode': self.mode,
            'meeting_link': self.meeting_link,
            'location': self.location
        }


class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellors.id'))
    rating = db.Column(db.Integer)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CounsellorSchedule(db.Model):
    __tablename__ = 'counsellor_schedules'
    schedule_id = db.Column(db.Integer, primary_key=True)
    counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellors.id', ondelete='CASCADE'))
    day_of_week = db.Column(db.Enum('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'))
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    is_recurring = db.Column(db.Boolean, default=True)

class CareerResource(db.Model):
    __tablename__ = 'career_resources'
    resource_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.Enum('document', 'video', 'link', 'other'), nullable=False)
    url = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    added_by = db.Column(db.Integer, db.ForeignKey('administrators.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)

class StudentDocument(db.Model):
    __tablename__ = 'student_documents'
    document_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'))
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.Enum('transcript', 'resume', 'certificate', 'other'), nullable=False)
    file_type = db.Column(db.String(10), nullable=False, default='other')  # pdf, doc, image, other
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_type = db.Column(db.Enum('student', 'counsellor', 'admin'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    read_status = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.Enum('general', 'appointment', 'resource', 'payment', 'grievance', 'appointment_request', 'feedback', 'event'), nullable=False)
    related_entity_id = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.notification_id,
            'message': self.message,
            'type': self.notification_type,
            'read': self.read_status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'related_entity_id': self.related_entity_id
        }

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)
    sender_type = db.Column(db.Enum('student', 'counsellor'), nullable=False)
    recipient_type = db.Column(db.Enum('student', 'counsellor'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'sender_type': self.sender_type,
            'recipient_type': self.recipient_type,
            'message_text': self.message_text,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': self.is_read
        }

class CareerGoal(db.Model):
    __tablename__ = 'career_goals'
    goal_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'))
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    target_date = db.Column(db.Date)
    status = db.Column(db.Enum('not_started', 'in_progress', 'completed'), default='not_started')

class StudentResourceAccess(db.Model):
    __tablename__ = 'student_resource_access'
    access_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'))
    resource_id = db.Column(db.Integer, db.ForeignKey('career_resources.resource_id', ondelete='CASCADE'))
    access_date = db.Column(db.DateTime, default=datetime.utcnow)

class GoalMilestone(db.Model):
    __tablename__ = 'goal_milestones'
    milestone_id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('career_goals.goal_id', ondelete='CASCADE'))
    milestone_title = db.Column(db.String(255))
    due_date = db.Column(db.Date)
    status = db.Column(db.Enum('pending', 'completed'), default='pending')

class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.Enum('webinar', 'workshop', 'qna', 'seminar'), nullable=False)
    counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellors.id'))
    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time)
    location = db.Column(db.String(255))
    meeting_link = db.Column(db.String(255))
    capacity = db.Column(db.Integer)
    is_online = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add relationship to EventRegistration with student information
    registrations = db.relationship('EventRegistration',
                                  backref=db.backref('event', lazy=True),
                                  lazy='joined',
                                  cascade='all, delete-orphan')

class EventRegistration(db.Model):
    __tablename__ = 'event_registrations'
    registration_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id', ondelete='CASCADE'))
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    reminder_sent = db.Column(db.Boolean, default=False)
    attendance_status = db.Column(db.Enum('registered', 'attended', 'missed'), default='registered')
    
    # Add relationship to Student to get student information
    student = db.relationship('Student', backref=db.backref('event_registrations', lazy=True))

class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), nullable=False)  # High, Medium, Low
    category = db.Column(db.String(50), nullable=False)  # Career, Academic, Personal, Other
    status = db.Column(db.String(20), nullable=False, default='Pending')  # Pending, Completed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('tasks', lazy=True))

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class AppointmentRequest(db.Model):
    __tablename__ = 'appointment_requests'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellors.id', ondelete='CASCADE'), nullable=False)
    appointment_type = db.Column(db.String(100), nullable=False)
    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time = db.Column(db.Time, nullable=False)
    mode = db.Column(db.Enum('online', 'offline', 'phone'), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = db.relationship('Student', backref=db.backref('appointment_requests', lazy=True))
    counsellor = db.relationship('CareerCounsellor', backref=db.backref('appointment_requests', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'counsellor_id': self.counsellor_id,
            'appointment_type': self.appointment_type,
            'preferred_date': self.preferred_date,
            'preferred_time': self.preferred_time,
            'mode': self.mode,
            'notes': self.notes,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }