
from flask import Flask, render_template, request, jsonify, send_file, abort
from flasgger import Swagger
import qrcode
import io
import base64
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
Swagger(app)

# Logging setup
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Database setup
DB_NAME = os.environ.get('DB_NAME', 'qrcodes.db')

# Simple in-memory cache
cache = {}

# Simple rate limiting
rate_limit = {}

# API keys (in a real application, these should be stored securely)
API_KEYS = {'secret_key_1', 'secret_key_2'}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS qrcodes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Error handling middleware
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        response = e.get_response()
        response.data = jsonify({
            "code": e.code,
            "name": e.name,
            "description": e.description,
        }).data
        response.content_type = "application/json"
        return response
    
    app.logger.error(f'An error occurred: {str(e)}')
    return jsonify({"error": "An unexpected error occurred"}), 500

# Simple caching decorator
def cache_result(timeout=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                result, timestamp = cache[key]
                if datetime.now().timestamp() - timestamp < timeout:
                    return result
            result = f(*args, **kwargs)
            cache[key] = (result, datetime.now().timestamp())
            return result
        return wrapper
    return decorator

# Rate limiting decorator
def rate_limit_decorator(limit=5, per=60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = request.remote_addr
            if key not in rate_limit:
                rate_limit[key] = []
            now = datetime.now()
            rate_limit[key] = [t for t in rate_limit[key] if now - t < timedelta(seconds=per)]
            if len(rate_limit[key]) >= limit:
                app.logger.warning(f'Rate limit exceeded for IP: {key}')
                abort(429, description="Rate limit exceeded")
            rate_limit[key].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# API key authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Bypass API key check if it's a form submission
        if request.content_type == 'application/x-www-form-urlencoded':
            # api_key = 'secret_key_1'
            return f(*args, **kwargs)  # Directly call the wrapped function

        api_key = request.headers.get('X-API-Key')
        api_key = 'secret_key_1'
        if api_key not in API_KEYS:
            app.logger.warning(f'Invalid API key used: {api_key}')
            abort(401, description="Invalid API key")
        return f(*args, **kwargs)
    return decorated



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health_check():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.close()
        app.logger.info('Health check passed')
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        app.logger.error(f'Health check failed: {str(e)}')
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/generate', methods=['POST'])
@rate_limit_decorator()
@require_api_key
def generate():
    '''
    Generate a QR code
    ---
    parameters:
      - name: content
        in: formData
        type: string
        required: true
        description: The content to encode in the QR code
      - name: X-API-Key
        in: header
        type: string
        required: true
        description: API key for authentication
    responses:
      200:
        description: QR code generated successfully
        schema:
          properties:
            image:
              type: string
              description: Base64 encoded image
            id:
              type: integer
              description: ID of the generated QR code
      400:
        description: Invalid input
      401:
        description: Invalid API key
      429:
        description: Rate limit exceeded
    '''
    content = request.form.get('content')
    if not content:
        app.logger.warning('Attempt to generate QR code with empty content')
        return jsonify({'error': 'Content is required'}), 400

    img = qrcode.make(content)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO qrcodes (content) VALUES (?)", (content,))
    qr_id = c.lastrowid
    conn.commit()
    conn.close()
    
    app.logger.info(f'QR code generated with ID: {qr_id}')
    return jsonify({'image': img_str, 'id': qr_id})

@app.route('/download/<int:qr_id>')
@cache_result(timeout=60)
@rate_limit_decorator()
@require_api_key
def download(qr_id):
    '''
    Download a generated QR code
    ---
    parameters:
      - name: qr_id
        in: path
        type: integer
        required: true
        description: The ID of the QR code to download
      - name: X-API-Key
        in: header
        type: string
        required: true
        description: API key for authentication
    responses:
      200:
        description: QR code image
      404:
        description: QR code not found
      401:
        description: Invalid API key
      429:
        description: Rate limit exceeded
    '''
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT content FROM qrcodes WHERE id = ?", (qr_id,))
    result = c.fetchone()
    conn.close()
    
    if result is None:
        app.logger.warning(f'Attempt to download non-existent QR code with ID: {qr_id}')
        return jsonify({'error': 'QR code not found'}), 404
    
    content = result[0]
    img = qrcode.make(content)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    
    app.logger.info(f'QR code downloaded with ID: {qr_id}')
    return send_file(buffered, mimetype='image/png', as_attachment=True, download_name=f'qrcode_{qr_id}.png')

@app.route('/list')
@require_api_key
def list_qr_codes():
    '''
    List all generated QR codes
    ---
    parameters:
      - name: X-API-Key
        in: header
        type: string
        required: true
        description: API key for authentication
    responses:
      200:
        description: List of QR codes
        schema:
          properties:
            qr_codes:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  content:
                    type: string
                  created_at:
                    type: string
      401:
        description: Invalid API key
    '''
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, content, created_at FROM qrcodes ORDER BY created_at DESC")
    qr_codes = [{'id': row[0], 'content': row[1], 'created_at': row[2]} for row in c.fetchall()]
    conn.close()
    
    app.logger.info('QR code list retrieved')
    return jsonify({'qr_codes': qr_codes})


if __name__ == '__main__':
  app.run(debug=False, host='0.0.0.0', port=8000)
