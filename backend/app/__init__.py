from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.config import Config
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Custom CORS to allow custom header for AuthGate
    CORS(app, resources={r"/*": {"origins": "*"}}, 
         supports_credentials=True, 
         allow_headers=["Content-Type", "X-Access-Token"])
    
    # Register Blueprints
    from backend.app.api.chat import chat_bp
    from backend.app.api.lesson import lesson_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(lesson_bp, url_prefix='/api/lesson')
    
    # Health Check
    @app.route('/health')
    def health_check():
        return {"status": "ok", "service": "sizheng-backend"}
    
    # ✅ NEW: Verification Route for Frontend AuthGate
    @app.route('/api/verify', methods=['POST'])
    def verify_token():
        # If execution reaches here, the middleware has already validated the password.
        return jsonify({"valid": True})

    # 🔒 Security Middleware
    @app.before_request
    def check_access_password():
        # Allow preflight CORS checks to pass
        if request.method == "OPTIONS":
            return
        
        # Skip password check for health check (optional, but good practice)
        if request.path == '/health':
            return

        # Define your password
        CORRECT_PASSWORD = os.getenv("ACCESS_PASSWORD", "sizheng2025")
        
        # Check the header
        user_password = request.headers.get("X-Access-Token")
        
        if user_password != CORRECT_PASSWORD:
            print(f"🛑 Blocked unauthorized access from {request.remote_addr}")
            return jsonify({"error": "Unauthorized: Access Denied"}), 401
        
    return app