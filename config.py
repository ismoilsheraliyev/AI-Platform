import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    
    # API keys (set these in .env file)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {
        'video': ['mp4', 'avi', 'mov', 'mkv'],
        'audio': ['mp3', 'wav', 'm4a', 'ogg'],
        'document': ['pdf', 'docx', 'txt', 'doc'],
        'image': ['png', 'jpg', 'jpeg', 'bmp']
    }
    
    # Model paths
    WHISPER_MODEL = 'base'
    TTS_MODEL_PATH = 'models/tts'
    
    # WebSocket settings
    SOCKETIO_ASYNC_MODE = 'eventlet'