import os
import datetime
import base64
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 允许最大16MB上传

# ==========================================
# 1. 模拟数据库 (In-Memory Data)
# ==========================================

MOCK_USERS = [
    {
        "user_id": 1, 
        "student_id": "2023001", 
        "password": "123", 
        "name": "同学 2023001", 
        "points": 120, 
        "credit_score": 780, 
        "avatar_url": "/static/assets/avatar_default.png", 
        "role": "both"
    },
    {
        "user_id": 2, 
        "student_id": "2023002", 
        "password": "123", 
        "name": "跑腿侠B", 
        "points": 50, 
        "credit_score": 98, 
        "avatar_url": "/static/assets/avatar_default.png", 
        "role": "both"
    },
    {
        "user_id": 3, 
        "student_id": "2023003", 
        "password": "123", 
        "name": "李同学", 
        "points": 200, 
        "credit_score": 600, 
        "avatar_url": "/static/assets/avatar_default.png", 
        "role": "demander"
    }
]

# 初始订单数据
MOCK_ORDERS = [
    {
        "order_id": 1001, 
        "requester_id": 2, 
        "runner_id": None, 
        "status": 0, 
        "category": "food", 
        "reward_points": 20, 
        "location_pickup": "二食堂一楼", 
        "location_deliver": "西区宿舍 5栋 201", 
        "description": "急！求带麦当劳双层吉士堡套餐", 
        "tags": ["急单"], 
        "create_time": (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat()
    },
    {
        "order_id": 1005, 
        "requester_id": 3, 
        "runner_id": None, 
        "status": 0, 
        "category": "package", 
        "reward_points": 20, 
        "location_pickup": "菜鸟驿站 B区", 
        "location_deliver": "东区 12栋", 
        "description": "中通快递，小盒子", 
        "pickup_code": "5-2-2011", 
        "tags": ["小件"], 
        "create_time": (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
    },
    {
        "order_id": 1006, 
        "requester_id": 3, 
        "runner_id": None, 
        "status": 0, 
        "category": "print", 
        "reward_points": 20, 
        "location_pickup": "图书馆打印店", 
        "location_deliver": "教学楼 C101", 
        "description": "打印复习资料，单面，20页", 
        "tags": [], 
        "file_name": "复习资料.pdf", 
        "create_time": (datetime.datetime.now() - datetime.timedelta(minutes=25)).isoformat()
    },
    
    # ============================================================
    # [测试用例] ID: 1007
    # 场景：我发布的 (requester_id=1)，已被接单 (runner_id=2)，配送中 (status=1)
    # 用于测试：详情页底部应显示 "联系" + "确认收货"
    # ============================================================
    {
        "order_id": 1007,
        "requester_id": 1,  # 您的ID
        "runner_id": 2,     # 跑腿侠B 接单
        "status": 1,        # 配送中
        "category": "package", 
        "reward_points": 15,
        "location_pickup": "南区菜鸟驿站", 
        "location_deliver": "北区宿舍 1栋 101", 
        "description": "【测试】我的快递单，已被同学接单正在配送中",
        "pickup_code": "1-1-1007", 
        "tags": ["测试"],
        "create_time": (datetime.datetime.now() - datetime.timedelta(minutes=30)).isoformat(),
        "take_time": (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
    }
]

MOCK_MESSAGES = {}
MOCK_POINT_RECORDS = {}

# ==========================================
# 2. 辅助函数
# ==========================================

def get_user_by_token(request):
    """根据请求头获取当前用户"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        # 为了方便浏览器直接访问测试，如果没传 Header 默认返回用户 1
        return MOCK_USERS[0]
    try:
        token = auth_header.split(" ")[1]
        user_id = int(token)
        return next((u for u in MOCK_USERS if u['user_id'] == user_id), None)
    except:
        return None

def add_point_record(user_id, source, change):
    if user_id not in MOCK_POINT_RECORDS:
        MOCK_POINT_RECORDS[user_id] = []
    
    MOCK_POINT_RECORDS[user_id].insert(0, {
        "source": source,
        "change": change,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    })

# ==========================================
# 3. 页面路由 (视图层)
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

# [核心修复] 路由跳转：根据 category 参数返回不同的 create_*.html 页面
@app.route('/orders/create')
def create_order_page():
    category = request.args.get('category', 'food')
    
    if category == 'food':
        return render_template('forms/create_food.html')
    elif category == 'package':
        return render_template('forms/create_package.html')
    elif category == 'print':
        return render_template('forms/create_print.html')
    
    # 默认返回带饭页面或首页
    return render_template('create_food.html')

@app.route('/orders/<int:order_id>')
def order_detail(order_id):
    is_partial = request.args.get('partial') == 'true'
    return render_template('detail.html', partial=is_partial, order_id=order_id)

# ==========================================
# 4. API 接口 (业务逻辑层)
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    student_id = data.get('student_id')
    password = data.get('password')
    user = next((u for u in MOCK_USERS if u['student_id'] == student_id and u['password'] == password), None)
    if user:
        return jsonify({"token": str(user['user_id']), "user": user, "message": "Login successful"})
    return jsonify({"message": "账号或密码错误"}), 401

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.json
    if any(u['student_id'] == data['student_id'] for u in MOCK_USERS):
        return jsonify({"message": "学号已存在"}), 400
    new_user = {
        "user_id": len(MOCK_USERS) + 1,
        "student_id": data['student_id'],
        "password": data['password'],
        "name": data.get('name', f"同学 {data['student_id']}"),
        "points": 100, "credit_score": 100, "avatar_url": "/static/assets/avatar_default.png", "role": "demander"
    }
    MOCK_USERS.append(new_user)
    add_point_record(new_user['user_id'], "新用户注册", 100)
    return jsonify({"message": "注册成功", "user_id": new_user['user_id']}), 201

@app.route('/api/user/profile', methods=['GET'])
def api_profile():
    user = get_user_by_token(request)
    if not user: return jsonify({"message": "未登录"}), 401
    completed_orders = len([o for o in MOCK_ORDERS if o['runner_id'] == user['user_id'] and o['status'] == 3])
    user['completed_orders_count'] = completed_orders
    return jsonify({"data": user})

@app.route('/api/user/points', methods=['GET'])
def api_user_points():
    user = get_user_by_token(request)
    if not user: return jsonify({"message": "未登录"}), 401
    records = MOCK_POINT_RECORDS.get(user['user_id'], [])
    return jsonify({"points": user['points'], "records": records})

@app.route('/api/orders/list', methods=['GET'])
def api_order_list():
    category = request.args.get('category')
    status = request.args.get('status')
    filtered_orders = MOCK_ORDERS
    if category and category != 'all':
        filtered_orders = [o for o in filtered_orders if o['category'] == category]
    if status == 'active':
        filtered_orders = [o for o in filtered_orders if o['status'] in [0, 1, 2]]
    elif status is not None:
        filtered_orders = [o for o in filtered_orders if str(o['status']) == str(status)]
    filtered_orders.sort(key=lambda x: x['create_time'], reverse=True)
    return jsonify({"data": filtered_orders})

@app.route('/api/orders/create', methods=['POST'])
def api_create_order():
    user = get_user_by_token(request)
    if not user: return jsonify({"message": "未登录"}), 401
    COST = 20
    if user['points'] < COST: return jsonify({"message": "积分不足"}), 400
    user['points'] -= COST
    add_point_record(user['user_id'], "发布订单", -COST)
    data = request.json
    new_order = {
        "order_id": len(MOCK_ORDERS) + 1000 + 1,
        "requester_id": user['user_id'],
        "runner_id": None,
        "status": 0, 
        "category": data.get('category'),
        "reward_points": COST,
        "location_pickup": data.get('location_pickup', ''),
        "location_deliver": data.get('location_deliver', ''),
        "description": data.get('description', ''),
        "pickup_code": data.get('pickup_code', ''),
        "file_pages": data.get('file_pages'),
        "print_type": data.get('print_type'),
        "tags": data.get('tags', []),
        "create_time": datetime.datetime.now().isoformat()
    }
    if new_order['category'] == 'print': new_order['file_name'] = "用户上传文件.pdf"
    MOCK_ORDERS.append(new_order)
    MOCK_MESSAGES[new_order['order_id']] = []
    return jsonify({"message": "发布成功", "order_id": new_order['order_id']}), 201

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def api_order_detail_data(order_id):
    order = next((o for o in MOCK_ORDERS if o['order_id'] == order_id), None)
    if not order: return jsonify({"message": "订单不存在"}), 404
    order_with_msgs = order.copy()
    order_with_msgs['messages'] = MOCK_MESSAGES.get(order_id, [])
    return jsonify({"data": order_with_msgs})

@app.route('/api/orders/<int:order_id>/take', methods=['POST'])
def api_take_order(order_id):
    user = get_user_by_token(request)
    order = next((o for o in MOCK_ORDERS if o['order_id'] == order_id), None)
    if order['status'] != 0: return jsonify({"message": "手慢了，订单已被抢"}), 400
    if order['requester_id'] == user['user_id']: return jsonify({"message": "不能抢自己的单"}), 400
    order['status'] = 1
    order['runner_id'] = user['user_id']
    order['take_time'] = datetime.datetime.now().isoformat()
    return jsonify({"message": "抢单成功"})

@app.route('/api/orders/<int:order_id>/deliver', methods=['POST'])
def api_deliver_order(order_id):
    user = get_user_by_token(request)
    order = next((o for o in MOCK_ORDERS if o['order_id'] == order_id), None)
    if order['runner_id'] != user['user_id']: return jsonify({"message": "无权操作"}), 403
    REWARD = 20
    user['points'] += REWARD
    add_point_record(user['user_id'], "完成订单", REWARD)
    order['status'] = 3 
    return jsonify({"message": "订单已完成"})

@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
def api_cancel_order(order_id):
    user = get_user_by_token(request)
    order = next((o for o in MOCK_ORDERS if o['order_id'] == order_id), None)
    if order['requester_id'] != user['user_id']: return jsonify({"message": "无权操作"}), 403
    user['points'] += 20
    add_point_record(user['user_id'], "取消订单退回", 20)
    order['status'] = 4
    return jsonify({"message": "已取消"})

@app.route('/api/orders/<int:order_id>/rate', methods=['POST'])
def api_rate_order(order_id):
    return jsonify({"message": "评价提交成功"})

@app.route('/api/orders/<int:order_id>/chat', methods=['POST'])
def api_send_message(order_id):
    user = get_user_by_token(request)
    data = request.json
    new_msg = {
        "sender_id": user['user_id'], "sender_name": user['name'],
        "type": data.get('type', 'text'), "content": data.get('content'),
        "time": datetime.datetime.now().isoformat()
    }
    if order_id not in MOCK_MESSAGES: MOCK_MESSAGES[order_id] = []
    MOCK_MESSAGES[order_id].append(new_msg)
    return jsonify({"message": "发送成功", "data": new_msg})

if __name__ == '__main__':
    print("Mock Server Started on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)