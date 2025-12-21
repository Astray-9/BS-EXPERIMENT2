from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import jwt
import datetime

db = SQLAlchemy()
cors = CORS()

class JWTManager:
    @staticmethod
    def encode_token(user_id):
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2),
            'iat': datetime.datetime.utcnow(),
            'sub': str(user_id)
        }
        from app import app
        return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def decode_token(token):
        try:
            from app import app
            payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None