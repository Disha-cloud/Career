from flask import request, jsonify
from flask_login import login_required, current_user
from models.message import Message
from models.student import Student

@api_bp.route('/messages/conversation/<string:partner_type>/<int:partner_id>/new')
@login_required
def check_new_messages(partner_type, partner_id):
    try:
        after_id = request.args.get('after', 0, type=int)
        
        
        user_type = 'student' if isinstance(current_user, Student) else 'counsellor'
        user_id = int(current_user.get_id().split('-')[1])
        
        
        new_messages = Message.query.filter(
            Message.id > after_id,
            ((Message.sender_type == partner_type) & (Message.sender_id == partner_id) &
             (Message.recipient_type == user_type) & (Message.recipient_id == user_id)) |
            ((Message.sender_type == user_type) & (Message.sender_id == user_id) &
             (Message.recipient_type == partner_type) & (Message.recipient_id == partner_id))
        ).order_by(Message.sent_at.asc()).all()
        
        return jsonify({
            'hasNew': len(new_messages) > 0,
            'messages': [message.to_dict() for message in new_messages]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to check for new messages'
        }), 500

@api_bp.route('/check-all-new-messages')
@login_required
def check_all_new_messages():
    try:
        
        last_message = Message.query.filter(
            (Message.sender_id == current_user.id) | 
            (Message.recipient_id == current_user.id)
        ).order_by(Message.timestamp.desc()).first()
        
        
        unread_count = Message.query.filter_by(
            recipient_id=current_user.id,
            read_status=False
        ).count()
        
        return jsonify({
            'success': True,
            'last_message_time': last_message.timestamp.isoformat() if last_message else None,
            'unread_count': unread_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to check new messages'
        }), 500 