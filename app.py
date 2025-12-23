import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from werkzeug.utils import secure_filename
import eventlet

from config import Config
from modules.video_to_text import VideoToText
from modules.audio_to_text import AudioToText
from modules.text_to_speech import TextToSpeech
from modules.document_analysis import DocumentAnalyzer
from modules.ai_tools import AITools
from modules.steganography import Steganography
from modules.uz_llm import UzbekLLM

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Create upload directories
os.makedirs('uploads/audio', exist_ok=True)
os.makedirs('uploads/video', exist_ok=True)
os.makedirs('uploads/documents', exist_ok=True)
os.makedirs('uploads/images', exist_ok=True)

# Initialize modules
video_processor = VideoToText()
audio_processor = AudioToText()
tts_processor = TextToSpeech()
doc_analyzer = DocumentAnalyzer()
ai_tools = AITools()
stego = Steganography()
uz_llm = UzbekLLM()

def allowed_file(filename, file_type):
    """Check if file extension is allowed"""
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in app.config['ALLOWED_EXTENSIONS'].get(file_type, [])
    return False

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

# WebSocket for real-time progress
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('progress', {'data': 'Connected', 'progress': 0})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

# 🎥 Video → Text endpoint
@app.route('/api/video-to-text', methods=['POST'])
def video_to_text():
    """Convert video to text with translation"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        source_lang = request.form.get('source_lang', 'auto')
        target_langs = request.form.get('target_langs', 'en,ru,uz').split(',')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'video'):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads/video', filename)
        file.save(filepath)
        
        # Process video through WebSocket
        def progress_callback(progress, message):
            socketio.emit('progress', {
                'progress': progress,
                'message': message,
                'task': 'video_to_text'
            })
        
        result = video_processor.process(
            filepath, 
            source_lang, 
            target_langs,
            progress_callback
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Video to text error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 🎧 Audio → Text endpoint
@app.route('/api/audio-to-text', methods=['POST'])
def audio_to_text():
    """Convert audio to text with high accuracy"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'audio'):
            return jsonify({'error': 'File type not allowed'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads/audio', filename)
        file.save(filepath)
        
        def progress_callback(progress, message):
            socketio.emit('progress', {
                'progress': progress,
                'message': message,
                'task': 'audio_to_text'
            })
        
        result = audio_processor.process(filepath, progress_callback)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Audio to text error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 🗣 Text → Speech endpoint
@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech in multiple languages"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'uz')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        audio_file = tts_processor.convert(text, language)
        
        return send_file(
            audio_file,
            mimetype='audio/mp3',
            as_attachment=True,
            download_name=f'tts_{language}.mp3'
        )
        
    except Exception as e:
        logger.error(f"Text to speech error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 📄 Document Analysis endpoint
@app.route('/api/analyze-document', methods=['POST'])
def analyze_document():
    """Analyze PDF, DOCX, TXT files"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        analysis_type = request.form.get('type', 'summary')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'document'):
            return jsonify({'error': 'File type not allowed'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads/documents', filename)
        file.save(filepath)
        
        def progress_callback(progress, message):
            socketio.emit('progress', {
                'progress': progress,
                'message': message,
                'task': 'document_analysis'
            })
        
        result = doc_analyzer.analyze(filepath, analysis_type, progress_callback)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Document analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 🧠 AI Tools endpoint
@app.route('/api/ai-tools', methods=['POST'])
def ai_tools_endpoint():
    """Various AI tools: summarization, sentiment, keywords"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        tool = data.get('tool', 'summarize')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        result = {}
        if tool == 'summarize':
            result = ai_tools.summarize(text)
        elif tool == 'sentiment':
            result = ai_tools.analyze_sentiment(text)
        elif tool == 'keywords':
            result = ai_tools.extract_keywords(text)
        else:
            return jsonify({'error': 'Invalid tool specified'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"AI tools error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 🕵️ Steganography endpoint
@app.route('/api/steganography', methods=['POST'])
def steganography():
    """Hide and extract text from images"""
    try:
        operation = request.form.get('operation', 'encode')
        
        if operation == 'encode':
            if 'image' not in request.files or 'text' not in request.form:
                return jsonify({'error': 'Image and text required'}), 400
            
            image_file = request.files['image']
            text = request.form['text']
            
            if not allowed_file(image_file.filename, 'image'):
                return jsonify({'error': 'Invalid image format'}), 400
            
            filename = secure_filename(image_file.filename)
            filepath = os.path.join('uploads/images', filename)
            image_file.save(filepath)
            
            result_image = stego.encode_text(filepath, text)
            
            return send_file(
                result_image,
                mimetype='image/png',
                as_attachment=True,
                download_name='encoded_image.png'
            )
            
        elif operation == 'decode':
            if 'image' not in request.files:
                return jsonify({'error': 'Image required'}), 400
            
            image_file = request.files['image']
            
            if not allowed_file(image_file.filename, 'image'):
                return jsonify({'error': 'Invalid image format'}), 400
            
            filename = secure_filename(image_file.filename)
            filepath = os.path.join('uploads/images', filename)
            image_file.save(filepath)
            
            text = stego.decode_text(filepath)
            
            return jsonify({'text': text})
        
    except Exception as e:
        logger.error(f"Steganography error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 🇺🇿 Uzbek LLM endpoint
@app.route('/api/uzbek-llm', methods=['POST'])
def uzbek_llm():
    """Uzbek language text generation"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        max_length = data.get('max_length', 100)
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        def progress_callback(progress, message):
            socketio.emit('progress', {
                'progress': progress,
                'message': message,
                'task': 'uzbek_llm'
            })
        
        response = uz_llm.generate(
            prompt, 
            max_length=max_length,
            progress_callback=progress_callback
        )
        
        return jsonify({'response': response})
        
    except Exception as e:
        logger.error(f"Uzbek LLM error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')