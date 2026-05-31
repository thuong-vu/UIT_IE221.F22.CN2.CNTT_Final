# Sổ Thu Chi — Ứng dụng quản lý thu chi cá nhân

Flask + MySQL (XAMPP) + HTML/CSS/JS thuần · Mobile-first SPA

## Cài đặt & Chạy

### 1. Khởi động XAMPP
- Mở XAMPP Control Panel
- Bật **Apache** và **MySQL**

### 2. Tạo database
- Vào `http://localhost/phpmyadmin`
- Chọn tab **SQL**, dán nội dung file `database/init.sql` và bấm **Go**
- Hoặc dùng MySQL CLI: `mysql -u root < database/init.sql`

### 3. Cấu hình môi trường (tuỳ chọn)
```bash
cp .env.example .env
# Chỉnh sửa .env nếu MySQL có password khác mặc định XAMPP
```

### 4. Cài Python dependencies
```bash
pip install -r requirements.txt
```

### 5. Chạy ứng dụng
```bash
python app.py
```

### 6. Mở trình duyệt
```
http://localhost:5000
```

---

## Cấu trúc dự án

```
thu-chi-app/
├── app.py              Flask app + tất cả API routes
├── db.py               Hàm get_connection() dùng PyMySQL
├── requirements.txt
├── .env.example        Mẫu biến môi trường
├── database/
│   └── init.sql        Tạo bảng + seed danh mục (chạy 1 lần)
└── templates/
    └── index.html      Toàn bộ UI single-page
```

## API Endpoints

| Method | URL | Mô tả |
|--------|-----|-------|
| GET | `/api/overview` | Tổng quan tháng này + 5 giao dịch gần nhất |
| GET | `/api/transactions?month=YYYY-MM&category_id=N` | Danh sách giao dịch |
| POST | `/api/transactions` | Thêm giao dịch mới |
| DELETE | `/api/transactions/:id` | Xoá giao dịch |
| GET | `/api/stats?period=week\|month\|year` | Thống kê tổng thu/chi + phân tích danh mục |
| GET | `/api/categories` | Danh sách danh mục |

## Yêu cầu hệ thống

- Python 3.9+
- XAMPP với MySQL 5.7+ / MariaDB 10.4+
- Trình duyệt hiện đại (Chrome, Firefox, Safari, Edge)
