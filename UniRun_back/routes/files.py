from flask import Blueprint, request, jsonify, current_app, send_from_directory
import os
from werkzeug.utils import secure_filename
from .orders import token_required

bp = Blueprint('files', __name__, url_prefix='/api/files')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@bp.route('/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    try:
        if 'file' not in request.files:
            return jsonify({'message': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # 添加用户ID前缀避免文件名冲突
            filename = f"{current_user.user_id}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 返回文件URL
            file_url = f"/{current_app.config['UPLOAD_FOLDER']}/{filename}"
            
            return jsonify({
                'message': '文件上传成功',
                'file_url': file_url,
                'file_name': filename
            }), 200
        
        return jsonify({'message': '不支持的文件类型'}), 400
        
    except Exception as e:
        return jsonify({'message': f'文件上传失败: {str(e)}'}), 500

@bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return jsonify({'message': f'文件下载失败: {str(e)}'}), 404