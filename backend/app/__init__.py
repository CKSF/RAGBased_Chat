from flask import Flask
from flask_cors import CORS
from backend.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS
    CORS(app)
    
    # Register Blueprints
    from backend.app.api.chat import chat_bp
    from backend.app.api.lesson import lesson_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(lesson_bp, url_prefix='/api/lesson')
    
    @app.route('/health')
    def health_check():
        return {"status": "ok", "service": "sizheng-backend"}
        
    return app
