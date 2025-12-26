from flask import Flask, request, jsonify, send_from_directory, abort # <--- 1. Add imports
from flask_cors import CORS
from backend.config import Config
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FOLDER = os.path.join(BASE_DIR, '..', '..', 'data')
    
    # Custom CORS to allow custom header for AuthGate
    CORS(app, resources={r"/*": {"origins": "*"}}, 
         supports_credentials=True, 
         allow_headers=["Content-Type", "X-Access-Token"])
    
    # Register Blueprints
    from backend.app.api.chat import chat_bp
    from backend.app.api.lesson import lesson_bp
    from backend.app.api.files import files_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(lesson_bp, url_prefix='/api/lesson')
    app.register_blueprint(files_bp, url_prefix='/api')
    
    # Health Check
    @app.route('/health')
    def health_check():
        return {"status": "ok", "service": "sizheng-backend"}
    
    @app.route('/api/source/<path:filename>')
    def serve_source(filename):
        # Path to your existing placeholder
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        PLACEHOLDER_PATH = os.path.join(BASE_DIR, 'static', 'placeholder.html')

        try:
            if os.path.exists(PLACEHOLDER_PATH):
                return send_file(
                    PLACEHOLDER_PATH,
                    as_attachment=True,
                    download_name="文档受限说明.html", # This sets the filename in Chinese
                    mimetype='text/html'
                )
            else:
                return jsonify({"error": "Placeholder not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    # ✅ NEW: Verification Route for Frontend AuthGate
    @app.route('/api/verify', methods=['POST'])
    def verify_token():
        # If execution reaches here, the middleware has already validated the password.
        return jsonify({"valid": True})

    @app.before_request
    def check_access_password():
        if request.method == "OPTIONS" or request.path == '/health':
            return

        # 1. Fallback to your known test password if .env isn't loaded
        CORRECT_PASSWORD = os.getenv("ACCESS_PASSWORD") or "sizheng2025"
        
        # 2. Check the header
        user_password = request.headers.get("X-Access-Token")
        
        # DEBUG: This is vital for local testing. 
        # Check your terminal/Docker logs to see these values.
        print(f"--- AUTH CHECK ---")
        print(f"Path: {request.path}")
        print(f"Received Token: '{user_password}'")
        print(f"Expected Token: '{CORRECT_PASSWORD}'")
        
        if user_password != CORRECT_PASSWORD:
            return jsonify({"error": "Unauthorized: Access Denied"}), 401
        
    return app