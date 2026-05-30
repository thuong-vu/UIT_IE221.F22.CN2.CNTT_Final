from flask import Flask, jsonify, request, render_template
from datetime import date, datetime
import json
from db import get_connection

app = Flask(__name__)

# ── Serialise date/datetime objects for JSON ──────────────────────────────────
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = DateEncoder


# ── Frontend ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── Categories ────────────────────────────────────────────────────────────────
@app.route('/api/categories')
def get_categories():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY type, id")
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.get_json()
    name     = (data.get('name') or '').strip()
    icon     = (data.get('icon') or '').strip()
    cat_type = data.get('type', '')

    if not name:
        return jsonify({'error': 'Tên danh mục không được để trống'}), 400
    if not icon:
        return jsonify({'error': 'Vui lòng chọn biểu tượng'}), 400
    if cat_type not in ('expense', 'income'):
        return jsonify({'error': 'Loại danh mục không hợp lệ'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO categories (name, icon, type) VALUES (%s, %s, %s)",
                (name, icon, cat_type)
            )
            new_id = cursor.lastrowid
        conn.commit()
        return jsonify({'id': new_id, 'name': name, 'icon': icon, 'type': cat_type}), 201
    finally:
        conn.close()


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM transactions WHERE category_id = %s",
                (cat_id,)
            )
            row = cursor.fetchone()
            if row['cnt'] > 0:
                return jsonify({
                    'error': f'Danh mục đang có {row["cnt"]} giao dịch, không thể xoá'
                }), 400
            cursor.execute("DELETE FROM categories WHERE id = %s", (cat_id,))
        conn.commit()
        return jsonify({'message': 'Đã xoá danh mục'})
    finally:
        conn.close()


# ── Transactions ──────────────────────────────────────────────────────────────
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    month       = request.args.get('month')        # YYYY-MM
    category_id = request.args.get('category_id')
    limit       = request.args.get('limit')        # for recent-5

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            conditions = []
            params     = []

            if month:
                conditions.append("DATE_FORMAT(t.date, '%%Y-%%m') = %s")
                params.append(month)
            if category_id:
                conditions.append("t.category_id = %s")
                params.append(category_id)

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            order = "ORDER BY t.date DESC, t.created_at DESC"
            lim   = f"LIMIT {int(limit)}" if limit else ""

            sql = f"""
                SELECT t.id, t.amount, t.type, t.note, t.date, t.created_at,
                       c.name AS category_name, c.icon
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                {where}
                {order}
                {lim}
            """
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.get_json()
    tx_type     = data.get('type')
    amount      = data.get('amount')
    category_id = data.get('category_id')
    tx_date     = data.get('date')
    note        = data.get('note', '')

    if not all([tx_type, amount, category_id, tx_date]):
        return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400
    if tx_type not in ('expense', 'income'):
        return jsonify({'error': 'Loại giao dịch không hợp lệ'}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO transactions (category_id, amount, type, note, date)
                   VALUES (%s, %s, %s, %s, %s)""",
                (category_id, int(amount), tx_type, note, tx_date)
            )
            new_id = cursor.lastrowid
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Đã lưu giao dịch'}), 201
    finally:
        conn.close()


@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM transactions WHERE id = %s", (tx_id,))
        conn.commit()
        return jsonify({'message': 'Đã xoá giao dịch'})
    finally:
        conn.close()


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
def get_stats():
    period = request.args.get('period', 'month')  # week | month | year

    if period == 'week':
        date_cond = "t.date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
    elif period == 'year':
        date_cond = "YEAR(t.date) = YEAR(CURDATE())"
    else:
        date_cond = "DATE_FORMAT(t.date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Totals
            cursor.execute(f"""
                SELECT
                    COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS total_income,
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS total_expense
                FROM transactions t
                WHERE {date_cond}
            """)
            totals = cursor.fetchone()

            # Category breakdown for expense
            cursor.execute(f"""
                SELECT c.name, c.icon,
                       SUM(t.amount) AS total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND {date_cond}
                GROUP BY t.category_id, c.name, c.icon
                ORDER BY total DESC
            """)
            breakdown = cursor.fetchall()

        return jsonify({
            'total_income':  totals['total_income'],
            'total_expense': totals['total_expense'],
            'balance':       totals['total_income'] - totals['total_expense'],
            'breakdown':     breakdown
        })
    finally:
        conn.close()


# ── Overview (home tab summary) ───────────────────────────────────────────────
@app.route('/api/overview')
def get_overview():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS total_income,
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS total_expense
                FROM transactions
                WHERE DATE_FORMAT(date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
            """)
            totals = cursor.fetchone()

            cursor.execute("""
                SELECT t.id, t.amount, t.type, t.note, t.date,
                       c.name AS category_name, c.icon
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                ORDER BY t.date DESC, t.created_at DESC
                LIMIT 5
            """)
            recent = cursor.fetchall()

        return jsonify({
            'total_income':  totals['total_income'],
            'total_expense': totals['total_expense'],
            'balance':       totals['total_income'] - totals['total_expense'],
            'recent':        recent
        })
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
