from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import Order, Evaluation, User
from extensions import db

bp = Blueprint("reviews", __name__)

# 提交评价（对应前端/orders/{id}/rate）
@bp.route("/orders/<int:order_id>/rate", methods=["POST"])
@jwt_required()
def submit_rating(order_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    score = data.get("rating")
    content = data.get("content", "")

    # 校验订单
    order = Order.query.get(order_id)
    if not order or order.status != 3:
        return jsonify({"message": "仅已完成订单可评价"}), 400
    if current_user_id not in [order.requester_id, order.runner_id]:
        return jsonify({"message": "无评价权限"}), 403
    # 避免重复评价
    if Evaluation.query.filter_by(order_id=order_id, reviewer_id=current_user_id).first():
        return jsonify({"message": "已评价过该订单"}), 409

    # 确定被评价人
    reviewee_id = order.runner_id if current_user_id == order.requester_id else order.requester_id
    reviewee = User.query.get(reviewee_id)

    # 计算信誉分影响（1-5星对应-2~+2分）
    credit_impact = score - 3  # 3星无影响，每高1星+1，每低1星-1

    # 保存评价
    evaluation = Evaluation(
        order_id=order_id,
        reviewer_id=current_user_id,
        reviewee_id=reviewee_id,
        score=score,
        content=content,
        credit_impact=credit_impact,
        review_time=datetime.now()
    )

    # 更新信誉分
    reviewee.credit_score = max(0, min(100, reviewee.credit_score + credit_impact))

    db.session.add(evaluation)
    db.session.commit()

    return jsonify({"message": "评价成功"}), 201