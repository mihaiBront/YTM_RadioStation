from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
import logging
from dotenv import load_dotenv
from src.models.user_config import UserConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

# FIXME: Placeholder for database initialization
def initialize_database():
    pass

def initialize_config():
    try:
        # See if the file exists
        user_config = UserConfig.from_file("src/config/user_config.json")
        if user_config is None:
            raise Exception("User config file is empty")
        return user_config
    except Exception as e:
        # If the file doesn't exist, create a default instance
        user_config = UserConfig()
        user_config.to_file("src/config/user_config.json")
        return user_config
    
def init_app() -> Flask:
    app: Flask = Flask(__name__)
    
    app.config['DEBUG'] = os.getenv('DEBUG', 'True').lower() == 'true'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Tokens don't expire (for development)
    
    # Initialize JWT
    jwt = JWTManager(app)
    
    # Enable CORS
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:4200,http://127.0.0.1:4200').split(',')
    CORS(app, origins=cors_origins)
    
    # Initialize files and components
    initialize_database()
    user_config = initialize_config()
    
    # Import blueprints
    from src.routes.health import health_bp
    # Register blueprints
    app.register_blueprint(health_bp, url_prefix='/api/health')
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == "__main__":
    app = init_app()
    port = int(os.environ.get('PORT', 3000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Radio Host Service starting on {host}:{port}")
    print(f"Health check: http://{host}:{port}/api/health")
    
    app.run(host=host, port=port, debug=app.config['DEBUG'])

    
    