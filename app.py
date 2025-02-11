from flask import Flask, request, jsonify, render_template, send_file
from file_processor import FileProcessor
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time
import logging
import traceback

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

processor = FileProcessor()

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    logger.error(traceback.format_exc())
    return jsonify({'error': 'Internal Server Error', 'details': str(error)}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    try:
        logger.debug(f"Template folder: {app.template_folder}")
        logger.debug(f"Templates available: {os.listdir(app.template_folder)}")
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.debug(f"Directory contents: {os.listdir('.')}")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.debug("Upload endpoint called")
    text = request.form.get('text', '').strip()
    
    if text:
        try:
            source_lang = request.form.get('source_lang', 'auto')
            target_lang = request.form.get('target_lang', 'zh')
            translated_text = processor.translate_text(text, source_lang, target_lang)
            
            return jsonify({
                'original_text': text,
                'translated_text': translated_text
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    # 处理中文文件名
    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1]
    safe_filename = secure_filename(f"upload_{int(time.time())}{file_ext}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    try:
        # 保存文件
        file.save(file_path)
        
        # 验证文件
        processor.validate_file(file_path)
        
        # 提取文本
        text = processor.extract_text(file_path)
        
        # 翻译文本
        source_lang = request.form.get('source_lang', 'auto')
        target_lang = request.form.get('target_lang', 'zh')
        translated_text = processor.translate_text(text, source_lang, target_lang)
        
        return jsonify({
            'original_text': text,
            'translated_text': translated_text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        # 清理上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route('/health')
def health_check():
    try:
        return jsonify({
            'status': 'healthy',
            'upload_dir': os.path.exists(app.config['UPLOAD_FOLDER']),
            'api_key_configured': bool(os.getenv('OPENAI_API_KEY'))
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port, debug=False) 
