import os
from datetime import timedelta

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'unirun-dev-secret-key-2025'
    
    # 数据库配置
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # 获取当前config.py所在的UniRun_back目录
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "campus_runner.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 关闭不必要的跟踪，提升性能
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-2025'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')  # 绝对路径
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # 积分配置
    INITIAL_POINTS = 100  # 新用户初始积分
    ORDER_MIN_POINTS = 1  # 最小赏金积分
    ORDER_MAX_POINTS = 100  # 最大赏金积分
    
    @staticmethod
    def init_app(app):
        # 自动创建上传文件夹
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
        pass