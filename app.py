from flask import Flask, jsonify, request, render_template, session, redirect
from datetime import date, datetime
from flask.json.provider import DefaultJSONProvider
from db import get_connection
from auth import auth_bp

app = Flask(__name__)
# BẮT BUỘC: Thêm secret key để sử dụng session cho đăng nhập
app.secret_key = 'super_secret_key_thu_chi'

# ── Đăng ký auth blueprint ────────────────────────────────────────────────────
app.register_blueprint(auth_bp)


# ── Serialise date/datetime objects for JSON (Cách chuẩn của Flask 2.3+) ──────
class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


app.json = CustomJSONProvider(app)


# ── Middleware kiểm tra đăng nhập ─────────────────────────────────────────────
@app.before_request
def require_login():
    # Các route được phép truy cập không cần đăng nhập
    allowed_routes = ['auth.login_page', 'auth.login', 'auth.register', 'static']
    if request.endpoint not in allowed_routes and not session.get('user_id'):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Vui lòng đăng nhập'}), 401
        return redirect('/login')


# ── Frontend ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── Categories ────────────────────────────────────────────────────────────────
@app.route('/api/categories')
def get_categories():
    user_id = session['user_id']
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories WHERE user_id = %s ORDER BY type, id", (user_id,))
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.route('/api/categories', methods=['POST'])
def add_category():
    user_id = session['user_id']
    data = request.get_json()
    name = (data.get('name') or '').strip()
    icon = (data.get('icon') or '').strip()
    cat_type = data.get('type', '')

    if not name or not icon or cat_type not in ('expense', 'income'):
        return jsonify({'error': 'Dữ liệu không hợp lệ'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO categories (name, icon, type, user_id) VALUES (%s, %s, %s, %s)",
                (name, icon, cat_type, user_id)
            )
            new_id = cursor.lastrowid
        conn.commit()
        return jsonify({'id': new_id, 'name': name, 'icon': icon, 'type': cat_type}), 201
    finally:
        conn.close()


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    user_id = session['user_id']
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM transactions WHERE category_id = %s AND user_id = %s",
                           (cat_id, user_id))
            row = cursor.fetchone()
            if row['cnt'] > 0:
                return jsonify({'error': f'Danh mục đang có {row["cnt"]} giao dịch, không thể xoá'}), 400
            cursor.execute("DELETE FROM categories WHERE id = %s AND user_id = %s", (cat_id, user_id))
        conn.commit()
        return jsonify({'message': 'Đã xoá danh mục'})
    finally:
        conn.close()


# ── Transactions ──────────────────────────────────────────────────────────────
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    user_id = session['user_id']
    month = request.args.get('month')
    category_id = request.args.get('category_id')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            conditions = ["t.user_id = %s"]
            params = [user_id]

            if month:
                # CÁCH CHUẨN: Tách chuỗi 'YYYY-MM' thành Năm và Tháng
                y, m = month.split('-')
                conditions.append("YEAR(t.date) = %s AND MONTH(t.date) = %s")
                params.extend([y, m])
            if category_id:
                conditions.append("t.category_id = %s")
                params.append(category_id)

            where = "WHERE " + " AND ".join(conditions)
            sql = f"""
                SELECT t.id, t.amount, t.type, t.note, t.date, t.created_at,
                       c.name AS category_name, c.icon
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                {where}
                ORDER BY t.date DESC, t.created_at DESC
            """
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    user_id = session['user_id']
    data = request.get_json()
    tx_type = data.get('type')
    amount = data.get('amount')
    category_id = data.get('category_id')
    tx_date = data.get('date')
    note = data.get('note', '')

    if not all([tx_type, amount, category_id, tx_date]):
        return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Kiểm tra xem category_id có thuộc về user này không
            cursor.execute("SELECT id FROM categories WHERE id = %s AND user_id = %s", (category_id, user_id))
            if not cursor.fetchone():
                return jsonify({'error': 'Danh mục không hợp lệ'}), 403

            cursor.execute(
                """INSERT INTO transactions (category_id, amount, type, note, date, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (category_id, int(amount), tx_type, note, tx_date, user_id)
            )
            new_id = cursor.lastrowid
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Đã lưu giao dịch'}), 201
    finally:
        conn.close()


@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    user_id = session['user_id']
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (tx_id, user_id))
        conn.commit()
        return jsonify({'message': 'Đã xoá giao dịch'})
    finally:
        conn.close()


# ── Stats & Overview ──────────────────────────────────────────────────────────
@app.route('/api/stats')
def get_stats():
    user_id = session['user_id']
    period = request.args.get('period', 'month')

    if period == 'week':
        date_cond = "t.date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
    elif period == 'year':
        date_cond = "YEAR(t.date) = YEAR(CURDATE())"
    else:
        # SỬA LỖI: Dùng YEAR() và MONTH() thay vì DATE_FORMAT() để né hoàn toàn dấu %
        date_cond = "YEAR(t.date) = YEAR(CURDATE()) AND MONTH(t.date) = MONTH(CURDATE())"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) AS total_income,
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS total_expense
                FROM transactions t
                WHERE t.user_id = %s AND {date_cond}
            """, (user_id,))
            totals = cursor.fetchone()

            cursor.execute(f"""
                SELECT c.name, c.icon, SUM(t.amount) AS total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = %s AND t.type = 'expense' AND {date_cond}
                GROUP BY t.category_id, c.name, c.icon
                ORDER BY total DESC
            """, (user_id,))
            breakdown = cursor.fetchall()

        return jsonify({
            'total_income': totals['total_income'],
            'total_expense': totals['total_expense'],
            'balance': totals['total_income'] - totals['total_expense'],
            'breakdown': breakdown
        })
    finally:
        conn.close()

@app.route('/api/overview')
def get_overview():
    user_id = session['user_id']
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # SỬA LỖI: Dùng YEAR() và MONTH() thay vì DATE_FORMAT()
            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) AS total_income,
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS total_expense
                FROM transactions
                WHERE user_id = %s AND YEAR(date) = YEAR(CURDATE()) AND MONTH(date) = MONTH(CURDATE())
            """, (user_id,))
            totals = cursor.fetchone()

            cursor.execute("""
                SELECT t.id, t.amount, t.type, t.note, t.date, c.name AS category_name, c.icon
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = %s
                ORDER BY t.date DESC, t.created_at DESC
                LIMIT 5
            """, (user_id,))
            recent = cursor.fetchall()

        return jsonify({
            'total_income': totals['total_income'],
            'total_expense': totals['total_expense'],
            'balance': totals['total_income'] - totals['total_expense'],
            'recent': recent
        })
    finally:
        conn.close()


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': f'Lỗi server: {str(e)}'}), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    return jsonify({'error': f'Lỗi không xác định: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)