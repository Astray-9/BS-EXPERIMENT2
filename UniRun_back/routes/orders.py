from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models import Order, User, PointRecord, Message
from datetime import datetime
import json
from functools import wraps

bp = Blueprint('orders', __name__, url_prefix='/api/orders')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from extensions import JWTManager
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = JWTManager.decode_token(token)
        if not user_id:
            return jsonify({'message': 'Token is invalid or expired'}), 401
        
        current_user = User.query.get(int(user_id))
        if not current_user:
            return jsonify({'message': 'User not found'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# 发布订单接口
@bp.route('/create', methods=['POST'])
@token_required
def create_order(current_user):
    try:
        data = request.get_json()

        # 强制赏金为20
        reward_points = 20
        if current_user.points < reward_points:
            return jsonify({'message': '积分不足（需20积分）'}), 400

        # 校验前端必填字段
        required_fields = ['category', 'location_deliver']  
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'缺少必填字段：{field}'}), 400
        
        # 快递类订单默认description，避免前端未传报错
        description = data.get('description')
        if data.get('category') == 'package' and not description:
            description = f"快递代拿（{data.get('tags', ['小件'])[0]}）"

        # 创建订单
        new_order = Order(
            requester_id=current_user.user_id,
            category=data.get('category'),
            reward_points=reward_points,
            pickup_code=data.get('pickup_code', ''),
            location_pickup=data.get('location_pickup', '未知取件点'),  # 默认值避免为空
            location_deliver=data.get('location_deliver'),
            description=description,  # 使用默认值或前端传的值
            tags=json.dumps(data.get('tags', [])),
            status=0  # 待接单
        )

        # 打印类订单补充file_name
        if new_order.category == 'print':
            new_order.file_name = data.get('file_name', '用户上传文件.pdf')

        db.session.add(new_order)
        db.session.flush()

        # 扣减用户积分
        current_user.points -= reward_points

        # 记录积分变动
        payment_record = PointRecord(
            user_id=current_user.user_id,
            order_id=new_order.order_id,
            change=-reward_points,
            source='order_payment',
            balance_after=current_user.points,
            remark=f'发布{new_order.category}订单 #{new_order.order_id}'
        )
        db.session.add(payment_record)

        db.session.commit()

        return jsonify({
            'message': '订单创建成功（扣除20积分）',
            'order_id': new_order.order_id,
            'data': new_order.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'创建订单失败: {str(e)}'}), 500

# 订单列表接口
@bp.route('/list', methods=['GET'])
@token_required
def list_orders(current_user):
    try:
        # 获取查询参数
        status = request.args.get('status', '0')
        category = request.args.get('category', '')
        
        # 构建查询
        query = Order.query
        
        # 状态筛选
        if status:
            try:
                status_int = int(status)
                query = query.filter(Order.status == status_int)
            except ValueError:
                pass
        
        # 类别筛选
        if category and category != 'all':
            query = query.filter(Order.category == category)
        
        # 按创建时间倒序
        orders = query.order_by(Order.create_time.desc()).all()
        
        return jsonify({
            'message': 'success',
            'data': [order.to_dict() for order in orders]
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'获取订单列表失败: {str(e)}'}), 500

# 全局缓存：存储 (user_id, order_id) -> 第一次提示“无权查看”的时间
no_perm_cache = {}
CACHE_EXPIRE = 300  # 缓存过期时间：5分钟

# 订单详情接口 “无权查看”弹窗仅触发1次
@bp.route('/<int:order_id>', methods=['GET'])
@token_required
def get_order(current_user, order_id):
    try:
        order = Order.query.get_or_404(order_id)
        cache_key = (current_user.user_id, order_id)  # 缓存键：用户-订单组合

        # 1. 权限检查：仅发单人、接单人、待接单订单可查看
        if (order.requester_id != current_user.user_id and 
            order.runner_id != current_user.user_id and 
            order.status != 0):
            # 第一次请求：返回403（触发1次弹窗），记录缓存
            if cache_key not in no_perm_cache:
                no_perm_cache[cache_key] = datetime.utcnow()
                return jsonify({'message': '无权查看此订单'}), 403
            # 后续请求：返回200（不触发弹窗），空数据
            else:
                # 缓存过期则清除，下次刷新页面仍能提示1次
                elapsed = (datetime.utcnow() - no_perm_cache[cache_key]).total_seconds()
                if elapsed > CACHE_EXPIRE:
                    del no_perm_cache[cache_key]
                # 返回200+空数据，前端不alert且不显示详情
                return jsonify({'message': '无权查看此订单', 'data': None}), 200

        # 2. 有权限：正常返回订单+消息数据
        messages = Message.query.filter_by(order_id=order_id).order_by(Message.create_time).all()
        order_data = order.to_dict()
        order_data['messages'] = []
        for msg in messages:
            msg_dict = msg.to_dict()
            sender = User.query.get(msg.sender_id)
            msg_dict['sender_name'] = sender.name if sender else '未知用户'
            order_data['messages'].append(msg_dict)

        return jsonify({'message': 'success', 'data': order_data}), 200

    except Exception as e:
        return jsonify({'message': f'获取订单失败: {str(e)}'}), 500
# 接单接口
@bp.route('/<int:order_id>/take', methods=['POST'])
@token_required
def take_order(current_user, order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # 校验1：订单是否为“待接单”状态
        if order.status != 0:
            return jsonify({'message': '手慢了，订单已被抢或状态异常'}), 400
        
        # 校验2：禁止自己接自己的单
        # 双重确认：current_user.user_id（当前登录用户ID） vs order.requester_id（订单发布者ID）
        if order.requester_id == current_user.user_id:
            # 返回明确错误提示，前端会通过 api.js 自动弹窗
            return jsonify({'message': '不能接自己发布的订单哦～请选择他人订单接单'}), 403
        
        # 校验3：防止重复接单
        if order.runner_id is not None:
            return jsonify({'message': '订单已被其他用户接单，请勿重复操作'}), 400
        
        # 正常接单逻辑
        order.runner_id = current_user.user_id
        order.status = 1  # 改为“配送中”状态
        order.take_time = datetime.utcnow()
        
        # 创建系统消息
        system_msg = Message(
            order_id=order.order_id,
            sender_id=0,  # 0 代表系统用户
            receiver_id=order.requester_id,
            type='text',
            content=f'您的订单已被用户【{current_user.name}】接单，正在配送中～'
        )
        db.session.add(system_msg)
        
        db.session.commit()
        
        return jsonify({
            'message': '抢单成功！请尽快前往取件配送',
            'data': order.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'接单失败：{str(e)}'}), 500

# 确认送达接口
@bp.route('/<int:order_id>/deliver', methods=['POST'])
@token_required
def deliver_order(current_user, order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # 检查权限：必须是接单人
        if order.runner_id != current_user.user_id:
            return jsonify({'message': '无权操作'}), 403
        
        # 检查订单状态
        if order.status != 1:
            return jsonify({'message': '订单状态不正确'}), 400
        
        # 更新订单状态
        order.status = 2  # 待收货
        order.deliver_time = datetime.utcnow()
        
        # 创建系统消息
        system_msg = Message(
            order_id=order.order_id,
            sender_id=0,  # 系统用户
            receiver_id=order.requester_id,
            type='text',
            content=f'您的订单已送达，请确认收货'
        )
        db.session.add(system_msg)
        
        db.session.commit()
        
        return jsonify({
            'message': '送达确认成功',
            'data': order.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'确认送达失败: {str(e)}'}), 500

@bp.route('/<int:order_id>/finish', methods=['POST'])
@token_required
def confirm_order(current_user, order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # 权限检查：必须是发单人
        if order.requester_id != current_user.user_id:
            return jsonify({'message': '只有发单人才能确认收货'}), 403
        
        # 状态检查：必须是“待收货”状态
        if order.status != 2:
            return jsonify({'message': '订单未处于待收货状态，无法确认'}), 400
        
        # 查找跑腿侠
        runner = User.query.get(order.runner_id)
        if not runner:
            return jsonify({'message': '接单用户不存在，无法发放积分'}), 404
        
        # 核心：给跑腿侠加积分
        reward_points = order.reward_points
        runner.points += reward_points
        
        # 记录积分变动
        reward_record = PointRecord(
            user_id=runner.user_id,
            order_id=order.order_id,
            change=reward_points,  # 正数表示增加
            source='order_reward',
            balance_after=runner.points,
            remark=f'完成订单 #{order.order_id} 获得赏金'
        )
        db.session.add(reward_record)
        
        # 更新订单状态为“已完成”
        order.status = 3
        order.confirm_time = datetime.utcnow()
        
        # 创建系统消息
        system_msg = Message(
            order_id=order.order_id,
            sender_id=0,  # 0 代表系统用户
            receiver_id=runner.user_id,
            type='text',
            content=f'您完成的订单 #{order.order_id} 已被确认收货，{reward_points} 积分已到账！'
        )
        db.session.add(system_msg)
        
        # 提交事务
        db.session.commit()
        
        return jsonify({
            'message': '收货确认成功，跑腿侠已获得积分奖励',
            'data': {
                'order': order.to_dict(),
                'runner_points': runner.points  # 返回骑手当前积分，方便前端展示
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'确认收货失败: {str(e)}'}), 500

# 取消订单接口
@bp.route('/<int:order_id>/cancel', methods=['POST'])
@token_required
def cancel_order(current_user, order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # 检查权限：必须是发单人
        if order.requester_id != current_user.user_id:
            return jsonify({'message': '无权操作'}), 403
        
        # 检查订单状态
        if order.status != 0:
            return jsonify({'message': '订单已被接单，无法取消'}), 400
        
        # 更新订单状态
        order.status = 4  # 已取消
        order.cancel_time = datetime.utcnow()
        
        # 退还积分给发单人
        current_user.points += order.reward_points
        
        # 记录积分变动
        refund_record = PointRecord(
            user_id=current_user.user_id,
            order_id=order.order_id,
            change=order.reward_points,
            source='order_refund',
            balance_after=current_user.points,
            remark=f'取消订单 #{order.order_id}'
        )
        db.session.add(refund_record)
        
        db.session.commit()
        
        return jsonify({
            'message': '已取消（积分已退回）',
            'data': order.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'取消订单失败: {str(e)}'}), 500

# 聊天消息发送接口（适配前端）
@bp.route('/<int:order_id>/chat', methods=['POST'])
@token_required
def send_message(current_user, order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # 权限校验：仅订单相关方（发单人/接单人）可聊天
        if current_user.user_id not in [order.requester_id, order.runner_id] and order.runner_id:
            return jsonify({'message': '无权发送消息'}), 403
        
        data = request.get_json()
        msg_type = data.get('type', 'text')  # 支持 text/image
        content = data.get('content', '')
        
        # 确定接收者（发单人→接单人，接单人→发单人）
        receiver_id = order.runner_id if current_user.user_id == order.requester_id else order.requester_id
        
        # 创建消息
        new_message = Message(
            order_id=order_id,
            sender_id=current_user.user_id,
            receiver_id=receiver_id,
            type=msg_type,
            content=content,
            create_time=datetime.utcnow()
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        # 补充sender_name
        msg_dict = new_message.to_dict()
        msg_dict['sender_name'] = current_user.name
        
        return jsonify({
            'message': '消息发送成功',
            'data': msg_dict
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'发送消息失败: {str(e)}'}), 500

# 评价接口
@bp.route('/<int:order_id>/rate', methods=['POST'])
@token_required
def rate_order(current_user, order_id):
    try:
        from models import Review
        order = Order.query.get_or_404(order_id)
        
        # 检查订单状态
        if order.status != 3:
            return jsonify({'message': '订单未完成，无法评价'}), 400
        
        data = request.get_json()
        rating = data.get('rating', 5)
        
        # 验证评分范围
        if rating < 1 or rating > 5:
            return jsonify({'message': '评分必须在1-5之间'}), 400
        
        # 确定评价关系
        if current_user.user_id == order.requester_id:
            reviewer_id = current_user.user_id
            reviewee_id = order.runner_id
        elif current_user.user_id == order.runner_id:
            reviewer_id = current_user.user_id
            reviewee_id = order.requester_id
        else:
            return jsonify({'message': '无权评价此订单'}), 403
        
        # 检查是否已评价
        existing_review = Review.query.filter_by(
            order_id=order_id,
            reviewer_id=reviewer_id
        ).first()
        
        if existing_review:
            return jsonify({'message': '已评价过此订单'}), 400
        
        # 创建评价
        new_review = Review(
            order_id=order_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=data.get('comment', '')
        )
        
        # 更新被评价用户的信誉分
        reviewee = User.query.get(reviewee_id)
        if reviewee:
            # 根据评分调整信誉分（1-5星对应-2~+2分）
            if rating >= 4:
                reviewee.credit_score = min(reviewee.credit_score + 2, 100)
            elif rating == 3:
                reviewee.credit_score = max(reviewee.credit_score - 1, 0)
            else:
                reviewee.credit_score = max(reviewee.credit_score - 2, 0)
        
        db.session.add(new_review)
        db.session.commit()
        
        return jsonify({
            'message': '评价成功！',
            'data': new_review.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'评价失败: {str(e)}'}), 500