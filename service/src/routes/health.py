"""
Health check routes for monitoring application status
"""
from flask import Blueprint, jsonify
import datetime
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
        'service': 'Radio Host Service',
        'version': os.getenv('VERSION', '0.0.0')
    })

@health_bp.route('/service', methods=['GET'])
def status_check():
    """Detailed status endpoint"""
    try:
        import requests
        response = requests.get('http://localhost:11434/api/version')
        if response.status_code == 200:
            ollama_status = 'running'
        else:
            ollama_status = 'error'
    except Exception:
        ollama_status = 'error'
        
    pg_model_status = 'down' # TODO: Add actual check
    
    return jsonify({
        'status': 'healthy',
        'subsystems': {
            'ollama': ollama_status,  # Add actual DB check when implemented
            'pg_model': pg_model_status, # TODO: Add actual check
        },
        'uptime': 'running',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })
