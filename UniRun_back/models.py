from extensions import db
from datetime import datetime
import json

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    points = db.Column(db.Integer, default=100)
    credit_score = db.Column(db.Integer, default=100)
    avatar_url = db.Column(db.String(255), default='/static/assets/avatar_default.png')
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    orders_requester = db.relationship('Order', foreign_keys='Order.requester_id', backref='requester', lazy=True)
    orders_runner = db.relationship('Order', foreign_keys='Order.runner_id', backref='runner', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='reviewer', lazy=True)
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewee_id', backref='reviewee', lazy=True)
    point_records = db.relationship('PointRecord', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'student_id': self.student_id,
            'name': self.name,
            'points': self.points,
            'credit_score': self.credit_score,
            'avatar_url': self.avatar_url,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    order_id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    runner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    
    status = db.Column(db.Integer, default=0)  # 0:待接单, 1:配送中, 2:待收货, 3:已完成, 4:已取消
    category = db.Column(db.String(20), nullable=False)  # food, package, print
    reward_points = db.Column(db.Integer, nullable=False)
    
    # 快递相关
    pickup_code = db.Column(db.String(20), nullable=True)
    
    # 打印相关
    file_url = db.Column(db.String(255), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_pages = db.Column(db.Integer, nullable=True)
    print_type = db.Column(db.String(20), nullable=True)  # single, double
    
    # 位置信息
    location_pickup = db.Column(db.String(100), nullable=True)
    location_deliver = db.Column(db.String(100), nullable=False)
    
    # 订单详情
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON字符串存储
    
    # 时间戳
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    take_time = db.Column(db.DateTime, nullable=True)
    deliver_time = db.Column(db.DateTime, nullable=True)
    confirm_time = db.Column(db.DateTime, nullable=True)
    cancel_time = db.Column(db.DateTime, nullable=True)
    
    # 关系
    messages = db.relationship('Message', backref='order', lazy=True)
    reviews = db.relationship('Review', backref='order', lazy=True)
    point_records = db.relationship('PointRecord', backref='order', lazy=True)
    
    def to_dict(self):
        return {
            'order_id': self.order_id,
            'requester_id': self.requester_id,
            'runner_id': self.runner_id,
            'status': self.status,
            'category': self.category,
            'reward_points': self.reward_points,
            'pickup_code': self.pickup_code,
            'file_url': self.file_url,
            'file_name': self.file_name,
            'file_pages': self.file_pages,
            'print_type': self.print_type,
            'location_pickup': self.location_pickup,
            'location_deliver': self.location_deliver,
            'description': self.description,
            'tags': json.loads(self.tags) if self.tags else [],
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'take_time': self.take_time.isoformat() if self.take_time else None,
            'deliver_time': self.deliver_time.isoformat() if self.deliver_time else None,
            'confirm_time': self.confirm_time.isoformat() if self.confirm_time else None,
            'cancel_time': self.cancel_time.isoformat() if self.cancel_time else None,
            'requester': self.requester.to_dict() if self.requester else None,
            'runner': self.runner.to_dict() if self.runner else None
        }

class Message(db.Model):
    __tablename__ = 'messages'
    
    message_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    type = db.Column(db.String(10), default='text')  # text, image
    content = db.Column(db.Text, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'message_id': self.message_id,
            'order_id': self.order_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'type': self.type,
            'content': self.content,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }

class Review(db.Model):
    __tablename__ = 'reviews'
    
    review_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'review_id': self.review_id,
            'order_id': self.order_id,
            'reviewer_id': self.reviewer_id,
            'reviewee_id': self.reviewee_id,
            'rating': self.rating,
            'comment': self.comment,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }

class PointRecord(db.Model):
    __tablename__ = 'point_records'
    
    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=True)
    change = db.Column(db.Integer, nullable=False)  # 正数为增加，负数为减少
    source = db.Column(db.String(50), nullable=False)  # 来源order_payment, order_reward, initial, etc.
    balance_after = db.Column(db.Integer, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    remark = db.Column(db.String(255), nullable=True)
    
    def to_dict(self):
        return {
            'record_id': self.record_id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'change': self.change,
            'source': self.source,
            'balance_after': self.balance_after,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'remark': self.remark
        }