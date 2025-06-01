from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Message, Student, CareerCounsellor
from datetime import datetime

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/api/messages/conversation/<recipient_type>/<int:recipient_id>', methods=['GET'])
@login_required
def get_conversation(recipient_type, recipient_id):
    # Determine sender type based on current user
    sender_type = 'student' if current_user.get_id().startswith('student-') else 'counsellor'
    sender_id = int(current_user.get_id().split('-')[1])
    
    # Verify the relationship between student and counsellor
    if sender_type == 'student':
        if not current_user.counsellor_id or current_user.counsellor_id != recipient_id:
            return jsonify({'error': 'You can only message your assigned counsellor'}), 403
    else:  # sender is counsellor
        student = Student.query.get(recipient_id)
        if not student or student.counsellor_id != sender_id:
            return jsonify({'error': 'You can only message your assigned students'}), 403
    
    # Get messages between the two users
    messages = Message.query.filter(
        (
            (Message.sender_id == sender_id) & 
            (Message.sender_type == sender_type) & 
            (Message.recipient_id == recipient_id) & 
            (Message.recipient_type == recipient_type)
        ) |
        (
            (Message.sender_id == recipient_id) & 
            (Message.sender_type == recipient_type) & 
            (Message.recipient_id == sender_id) & 
            (Message.recipient_type == sender_type)
        )
    ).order_by(Message.sent_at.asc()).all()
    
    # Mark unread messages as read
    unread_messages = [m for m in messages if not m.is_read and m.recipient_id == sender_id]
    for message in unread_messages:
        message.is_read = True
    if unread_messages:
        db.session.commit()
    
    return jsonify([message.to_dict() for message in messages])

@messages_bp.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    
    # Determine sender type based on current user
    sender_type = 'student' if current_user.get_id().startswith('student-') else 'counsellor'
    sender_id = int(current_user.get_id().split('-')[1])
    recipient_id = data.get('recipient_id')
    recipient_type = data.get('recipient_type')
    
    # Prevent users from messaging themselves
    if sender_id == recipient_id and sender_type == recipient_type:
        return jsonify({'error': 'You cannot send messages to yourself'}), 400
    
    # Verify the relationship between student and counsellor
    if sender_type == 'student':
        if not current_user.counsellor_id or current_user.counsellor_id != recipient_id:
            return jsonify({'error': 'You can only message your assigned counsellor'}), 403
    else:  # sender is counsellor
        student = Student.query.get(recipient_id)
        if not student or student.counsellor_id != sender_id:
            return jsonify({'error': 'You can only message your assigned students'}), 403
    
    # Create new message
    message = Message(
        sender_id=sender_id,
        sender_type=sender_type,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        message_text=data.get('message'),
        sent_at=datetime.utcnow(),
        is_read=False
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify(message.to_dict())

@messages_bp.route('/api/messages/conversations', methods=['GET'])
@login_required
def get_conversations():
    # Determine user type based on current user
    user_type = 'student' if current_user.get_id().startswith('student-') else 'counsellor'
    user_id = int(current_user.get_id().split('-')[1])
    
    if user_type == 'student':
        # Students can only see conversations with their assigned counsellor
        if not current_user.counsellor_id:
            return jsonify([])
            
        messages = Message.query.filter(
            (
                (Message.sender_id == user_id) & 
                (Message.sender_type == 'student') & 
                (Message.recipient_id == current_user.counsellor_id) &
                (Message.recipient_type == 'counsellor')
            ) |
            (
                (Message.sender_id == current_user.counsellor_id) & 
                (Message.sender_type == 'counsellor') &
                (Message.recipient_id == user_id) &
                (Message.recipient_type == 'student')
            )
        ).order_by(Message.sent_at.desc()).all()
    else:
        # Counsellors can only see conversations with their assigned students
        assigned_students = Student.query.filter_by(counsellor_id=user_id).with_entities(Student.id).all()
        student_ids = [s.id for s in assigned_students]
        
        if not student_ids:
            return jsonify([])
            
        messages = Message.query.filter(
            (
                (Message.sender_id == user_id) & 
                (Message.sender_type == 'counsellor') & 
                (Message.recipient_id.in_(student_ids)) &
                (Message.recipient_type == 'student')
            ) |
            (
                (Message.sender_id.in_(student_ids)) & 
                (Message.sender_type == 'student') &
                (Message.recipient_id == user_id) &
                (Message.recipient_type == 'counsellor')
            )
        ).order_by(Message.sent_at.desc()).all()
    
    # Get unique conversation partners
    conversations = {}
    for message in messages:
        if message.sender_id == user_id:
            # Only show recipients of the opposite type
            if (user_type == 'student' and message.recipient_type != 'counsellor') or \
               (user_type == 'counsellor' and message.recipient_type != 'student'):
                continue
            partner_id = message.recipient_id
            partner_type = message.recipient_type
        else:
            # Only show senders of the opposite type
            if (user_type == 'student' and message.sender_type != 'counsellor') or \
               (user_type == 'counsellor' and message.sender_type != 'student'):
                continue
            partner_id = message.sender_id
            partner_type = message.sender_type
            
        if (partner_type, partner_id) not in conversations:
            # Get partner details
            if partner_type == 'student':
                partner = Student.query.get(partner_id)
                if partner:
                    conversations[(partner_type, partner_id)] = {
                        'id': partner_id,
                        'type': partner_type,
                        'name': f"{partner.first_name} {partner.last_name}",
                        'last_message': message.to_dict(),
                        'unread_count': Message.query.filter_by(
                            sender_id=partner_id,
                            sender_type=partner_type,
                            recipient_id=user_id,
                            recipient_type=user_type,
                            is_read=False
                        ).count()
                    }
            else:
                partner = CareerCounsellor.query.get(partner_id)
                if partner:
                    conversations[(partner_type, partner_id)] = {
                        'id': partner_id,
                        'type': partner_type,
                        'name': f"{partner.first_name} {partner.last_name}",
                        'last_message': message.to_dict(),
                        'unread_count': Message.query.filter_by(
                            sender_id=partner_id,
                            sender_type=partner_type,
                            recipient_id=user_id,
                            recipient_type=user_type,
                            is_read=False
                        ).count()
                    }
    
    return jsonify(list(conversations.values())) 