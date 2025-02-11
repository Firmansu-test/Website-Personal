from flask import Flask, request, jsonify, render_template, send_file
from file_processor import FileProcessor
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time

#获取OPEN AI API密钥和端点
openai_api_key = os.getenv('OPENAI_API_KEY')
translation_api_endpoint = os.getenv('TRANSLATION_API_ENDPOINT')

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

processor = FileProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=False) 
