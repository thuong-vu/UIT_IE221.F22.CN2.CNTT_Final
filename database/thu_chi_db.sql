-- 1. Tạo một user mới 
CREATE USER IF NOT EXISTS 'thuchi_admin'@'localhost' IDENTIFIED BY '123';

-- 2. Cấp TOÀN BỘ quyền (Thêm, sửa, xóa, tạo bảng...) nhưng CHỈ trên database thu_chi_db
GRANT ALL PRIVILEGES ON thu_chi_db.* TO 'thuchi_admin'@'localhost';

-- 3. Áp dụng các thay đổi về quyền
FLUSH PRIVILEGES;

CREATE DATABASE IF NOT EXISTS thu_chi_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE thu_chi_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NOT NULL,
    type ENUM('expense', 'income') NOT NULL,
    user_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    amount BIGINT NOT NULL,
    type ENUM('expense', 'income') NOT NULL,
    note TEXT,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

DELIMITER //

CREATE TRIGGER after_user_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO categories (name, icon, type, user_id) VALUES
    ('Ăn uống',    'ti-tools-kitchen-2', 'expense', NEW.id),
    ('Di chuyển',  'ti-car',             'expense', NEW.id),
    ('Mua sắm',    'ti-shopping-bag',    'expense', NEW.id),
    ('Nhà cửa',    'ti-home',            'expense', NEW.id),
    ('Sức khoẻ',   'ti-heart',           'expense', NEW.id),
    ('Giải trí',   'ti-device-tv',       'expense', NEW.id),
    ('Khác',       'ti-clipboard',       'expense', NEW.id),
    ('Lương',      'ti-currency-dollar', 'income',  NEW.id),
    ('Thưởng',     'ti-gift',            'income',  NEW.id),
    ('Đầu tư',     'ti-trending-up',     'income',  NEW.id),
    ('Thu khác',   'ti-wallet',          'income',  NEW.id);
END //

DELIMITER ;
