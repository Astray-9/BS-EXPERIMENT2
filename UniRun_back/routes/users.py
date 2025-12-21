from flask import Blueprint, request, jsonify
from extensions import db
from models import User, PointRecord, Order, Review
from .orders import token_required

bp = Blueprint('users', __name__, url_prefix='/api/user')

@bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    try:
        # 计算完成订单数
        completed_orders_count = Order.query.filter(
            (Order.requester_id == current_user.user_id) | 
            (Order.runner_id == current_user.user_id),
            Order.status == 3
        ).count()
        
        # 计算平均评分
        reviews = Review.query.filter_by(reviewee_id=current_user.user_id).all()
        avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 4.9
        
        return jsonify({
            'message': 'success',
            'data': {
                **current_user.to_dict(),
                'completed_orders_count': completed_orders_count,
                'avg_rating': round(avg_rating, 1)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'获取用户信息失败: {str(e)}'}), 500

@bp.route('/points', methods=['GET'])
@token_required
def get_points(current_user):
    try:
        # 获取积分记录
        records = PointRecord.query.filter_by(user_id=current_user.user_id)\
            .order_by(PointRecord.create_time.desc())\
            .limit(20)\
            .all()
        
        formatted_records = []
        for record in records:
            formatted_records.append({
                'source': record.remark or '积分变动',
                'change': record.change,
                'time': record.create_time.strftime('%Y-%m-%d %H:%M') if record.create_time else '',
                'balance_after': record.balance_after
            })
        
        return jsonify({
            'message': 'success',
            'points': current_user.points,
            'records': formatted_records
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'获取积分记录失败: {str(e)}'}), 500