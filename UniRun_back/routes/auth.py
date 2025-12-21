from flask import Blueprint, request, jsonify, current_app
from extensions import db, JWTManager
from models import User, PointRecord
from werkzeug.security import generate_password_hash, check_password_hash
import re

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        student_id = data.get('student_id', '').strip()
        name = data.get('name', '').strip()
        password = data.get('password', '').strip()
        
        # 验证学号格式（10或11位）
        if not re.match(r'^\d{10,11}$', student_id):
            return jsonify({'message': '学号必须是10或11位数字'}), 400
        
        # 检查学号是否已存在
        if User.query.filter_by(student_id=student_id).first():
            return jsonify({'message': '该学号已注册'}), 400
        
        # 检查密码长度
        if len(password) < 6:
            return jsonify({'message': '密码长度至少6位'}), 400
        
        # 创建新用户
        new_user = User(
            student_id=student_id,
            name=name,
            password_hash=generate_password_hash(password),
            points=current_app.config['INITIAL_POINTS']
        )
        
        db.session.add(new_user)
        db.session.flush()  # 获取user_id
        
        # 创建初始积分记录
        init_record = PointRecord(
            user_id=new_user.user_id,
            change=current_app.config['INITIAL_POINTS'],
            source='initial',
            balance_after=current_app.config['INITIAL_POINTS'],
            remark='初始积分'
        )
        db.session.add(init_record)
        db.session.commit()
        
        return jsonify({'message': '注册成功'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'注册失败: {str(e)}'}), 500

@bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        student_id = data.get('student_id', '').strip()
        password = data.get('password', '').strip()
        
        # 查找用户
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            return jsonify({'message': '账号或密码错误'}), 401
        
        # 验证密码
        if not check_password_hash(user.password_hash, password):
            return jsonify({'message': '账号或密码错误'}), 401
        
        # 生成token
        token = JWTManager.encode_token(user.user_id)
        
        # 更新用户信息
        from datetime import datetime
        user.update_time = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '登录成功',
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'登录失败: {str(e)}'}), 500