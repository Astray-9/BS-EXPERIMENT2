from flask import Flask, send_from_directory, render_template, request
from config import Config
from extensions import db, cors
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import json

def create_app(config_class=Config):
    # 1. 计算核心路径（UniRun根目录、静态/模板文件夹）
    current_file_dir = os.path.dirname(os.path.abspath(__file__))  # UniRun_back目录
    project_root_dir = os.path.dirname(current_file_dir)           # UniRun根目录
    static_folder = os.path.join(project_root_dir, 'static')       # UniRun/static
    template_folder = os.path.join(project_root_dir, 'templates') # UniRun/templates
    
    # 验证静态/模板文件夹是否存在，不存在则创建
    for folder in [static_folder, template_folder]:
        if not os.path.exists(folder):
            print(f"警告：文件夹不存在，自动创建 -> {folder}")
            os.makedirs(folder, exist_ok=True)
    
    # 2. 初始化Flask应用
    app = Flask(__name__, 
                static_folder=static_folder,
                template_folder=template_folder)
    app.config.from_object(config_class)
    
    # 3. 初始化扩展（数据库、跨域）
    db.init_app(app)
    cors.init_app(app, resources={
        r"/api/*": {"origins": "*"},
        r"/static/*": {"origins": "*"}  # 允许静态资源跨域
    })
    
    # 4. 自动创建数据库表 + 插入初始数据
    with app.app_context():
        # 导入所有模型
        from models import User, Order, Message, Review, PointRecord
        
        # 创建所有表
        db.create_all()

        # 插入初始用户
        if not User.query.first():  # 无用户时才插入
            initial_users = [
                User(
                    student_id='2023001',
                    name='同学 2023001',
                    password_hash=generate_password_hash('123'),  # 密码123，和mock一致
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
            db.session.add_all(initial_users)
            db.session.commit()
            print("✅ 初始用户插入成功（账号：2023001/2023002/2023003，密码：123）")

        # 插入初始订单
        if not Order.query.first():  # 无订单时才插入
            # 获取初始用户
            user1 = User.query.filter_by(student_id='2023001').first()
            user2 = User.query.filter_by(student_id='2023002').first()
            user3 = User.query.filter_by(student_id='2023003').first()

            initial_orders = [
                # 订单1：food类，待接单（status=0）
                Order(
                    requester_id=user2.user_id,
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
                # 订单2：package类，待接单
                Order(
                    requester_id=user3.user_id,
                    runner_id=None,
                    status=0,
                    category='package',
                    reward_points=20,
                    location_pickup='菜鸟驿站 B区',
                    location_deliver='东区 12栋',
                    description='中通快递，小盒子',
                    pickup_code='5-2-2011',
                    tags=json.dumps(["小件"]),
                    create_time=datetime.utcnow() - timedelta(minutes=10)
                ),
                # 订单3：print类，待接单
                Order(
                    requester_id=user3.user_id,
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
                # 订单4：测试用（已接单，配送中）
                Order(
                    requester_id=user1.user_id,
                    runner_id=user2.user_id,
                    status=1,
                    category='package',
                    reward_points=15,
                    location_pickup='南区菜鸟驿站',
                    location_deliver='北区宿舍 1栋 101',
                    description='【测试】我的快递单，已被同学接单正在配送中',
                    pickup_code='1-1-1007',
                    tags=json.dumps(["测试"]),
                    create_time=datetime.utcnow() - timedelta(minutes=30),
                    take_time=datetime.utcnow() - timedelta(minutes=10)
                )
            ]
            db.session.add_all(initial_orders)
            db.session.commit()
            print(" 初始订单插入成功（4条测试订单）")

        print(f" 数据库表创建完成！数据库文件路径：{app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # 5. 注册蓝图
    try:
        from routes import auth, orders, users, messages, files
        app.register_blueprint(auth.bp)
        app.register_blueprint(orders.bp)
        app.register_blueprint(users.bp)
        app.register_blueprint(messages.bp)
        app.register_blueprint(files.bp)
        print("所有蓝图注册成功")
    except ImportError as e:
        print(f" 蓝图导入失败（不影响基础功能）：{str(e)}")
    
    # 6. 静态文件路由
    @app.route('/static/<path:filename>')
    def static_files(filename):
        try:
            file_path = os.path.join(app.static_folder, filename)
            if not os.path.exists(file_path):
                return f"静态文件不存在: {filename}", 404
            # 自动识别文件类型，确保CSS/JS正常加载
            return send_from_directory(app.static_folder, filename, conditional=True)
        except Exception as e:
            return f"加载静态文件失败: {str(e)}", 500
    
    # 7. 模板页面路由
    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception as e:
            return f"首页渲染失败: {str(e)}，请检查templates/index.html是否存在", 404
    
    @app.route('/login')
    def login_page():
        try:
            return render_template('login.html')
        except Exception as e:
            return f"登录页渲染失败: {str(e)}", 404
    
    @app.route('/register')
    def register_page():
        try:
            return render_template('register.html')
        except Exception as e:
            return f"注册页渲染失败: {str(e)}", 404
    
    @app.route('/profile')
    def profile_page():
        try:
            return render_template('profile.html')
        except Exception as e:
            return f"个人中心渲染失败: {str(e)}", 404
    
    @app.route('/orders/create')
    def create_order_page():
        try:
            category = request.args.get('category', 'food')
            template_map = {
                'food': 'forms/create_food.html',
                'package': 'forms/create_package.html',
                'print': 'forms/create_print.html'
            }
            template_file = template_map.get(category, 'forms/create_food.html')
            return render_template(template_file)
        except Exception as e:
            return f"发布页渲染失败: {str(e)}", 404
    # app.py 的“模板页面路由”部分
    @app.route('/orders/<int:order_id>')
    def order_detail(order_id):
        is_partial = request.args.get('partial') == 'true'
        # 确保detail.html在templates目录下
        return render_template('detail.html', partial=is_partial, order_id=order_id)
    
    # 8. 健康检查接口
    @app.route('/health')
    def health_check():
        return {
            "status": "healthy",
            "project_root_dir": project_root_dir,
            "static_folder": app.static_folder,
            "template_folder": app.template_folder,
            "database_path": app.config['SQLALCHEMY_DATABASE_URI'],
            "static_folder_exists": os.path.exists(app.static_folder)
        }
    
    return app

# 创建app实例
app = create_app()

# 启动程序
if __name__ == '__main__':
    # 打印关键路径，方便排查
    print(f"\n 项目关键路径：")
    print(f"   - UniRun根目录: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"   - 静态文件目录: {app.static_folder}")
    print(f"   - 模板文件目录: {app.template_folder}")
    print(f"   - 数据库文件路径: {app.config['SQLALCHEMY_DATABASE_URI']}\n")
    
    # 启动Flask服务
    app.run(host='0.0.0.0', port=5001, debug=True)