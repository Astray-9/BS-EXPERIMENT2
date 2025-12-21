from app import app, db
from models import User, Order, Message, Review, PointRecord
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import json
import os

def init_database():
    with app.app_context():
        # 删除所有表并重新创建
        db.drop_all()
        db.create_all()
        
        print("数据库表创建成功！")
        
        # 创建测试用户
        users = [
            User(
                student_id='2023001',
                name='同学 2023001',
                password_hash=generate_password_hash('123'),
                points=120,
                credit_score=780
            ),
            User(
                student_id='2023002',
                name='跑腿侠B',
                password_hash=generate_password_hash('123'),
                points=50,
                credit_score=98
            ),
            User(
                student_id='2023003',
                name='李同学',
                password_hash=generate_password_hash('123'),
                points=200,
                credit_score=600
            )
        ]
        
        for user in users:
            db.session.add(user)
        
        db.session.commit()
        print("测试用户创建成功！")
        
        # 创建测试订单
        orders = [
            Order(
                requester_id=2,
                runner_id=None,
                status=0,
                category='food',
                reward_points=20,
                location_pickup='二食堂一楼',
                location_deliver='西区宿舍 5栋 201',
                description='急！求带麦当劳双层吉士堡套餐',
                tags=json.dumps(["急单"]),
                create_time=datetime.utcnow() - timedelta(minutes=5)
            ),
            Order(
                requester_id=3,
                runner_id=None,
                status=0,
                category='package',
                reward_points=20,
                pickup_code='5-2-2011',
                location_pickup='菜鸟驿站 B区',
                location_deliver='东区 12栋',
                description='中通快递，小盒子',
                tags=json.dumps(["小件"]),
                create_time=datetime.utcnow() - timedelta(minutes=10)
            ),
            Order(
                requester_id=3,
                runner_id=None,
                status=0,
                category='print',
                reward_points=20,
                location_pickup='图书馆打印店',
                location_deliver='教学楼 C101',
                description='打印复习资料，单面，20页',
                tags=json.dumps([]),
                file_name='复习资料.pdf',
                create_time=datetime.utcnow() - timedelta(minutes=25)
            ),
        ]
        
        for order in orders:
            db.session.add(order)
        
        db.session.commit()
        print("测试订单创建成功！")
        
        # 创建积分记录
        for user in users:
            record = PointRecord(
                user_id=user.user_id,
                change=user.points,
                source='initial',
                balance_after=user.points,
                remark='初始积分'
            )
            db.session.add(record)
        
        db.session.commit()
        print("数据库初始化完成！")

if __name__ == '__main__':
    init_database()