from flask import Blueprint, request, jsonify
from extensions import db
from models import Message
from .orders import token_required

bp = Blueprint('messages', __name__, url_prefix='/api/messages')

@bp.route('/', methods=['GET'])
@token_required
def get_messages(current_user):
    try:
        # 获取用户相关的消息
        messages = Message.query.filter(
            (Message.receiver_id == current_user.user_id) |
            (Message.sender_id == current_user.user_id)
        ).order_by(Message.create_time.desc()).all()
        
        # 分组消息按订单
        orders_messages = {}
        for msg in messages:
            if msg.order_id not in orders_messages:
                orders_messages[msg.order_id] = []
            orders_messages[msg.order_id].append(msg.to_dict())
        
        # 计算未读消息数
        unread_count = Message.query.filter_by(
            receiver_id=current_user.user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'message': 'success',
            'data': {
                'messages_by_order': orders_messages,
                'unread_count': unread_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'获取消息失败: {str(e)}'}), 500