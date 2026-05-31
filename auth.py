from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login_page():
    return render_template('auth.html')

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': 'Tài khoản và mật khẩu không được trống'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mật khẩu phải có ít nhất 6 ký tự'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({'error': 'Tài khoản này đã tồn tại'}), 400

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
        conn.commit()
        return jsonify({'message': 'Đăng ký tài khoản thành công'}), 201
    finally:
        conn.close()

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password'], password):
                return jsonify({'error': 'Tài khoản hoặc mật khẩu không chính xác'}), 401

            session['user_id'] = user['id']
            session['username'] = user['username']

        return jsonify({'message': 'Đăng nhập thành công', 'username': user['username']})
    finally:
        conn.close()

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Đã đăng xuất'})

@auth_bp.route('/api/auth/me', methods=['GET'])
def get_me():
    if not session.get('user_id'):
        return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'username': session.get('username')})