import os
import sqlite3
import uuid
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# مجلد حفظ الصور المرفوعة محلياً
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- إعدادات الحماية لوحة التحكم (تقرأ من قاعدة البيانات) ---
def check_auth(username, password):
    conn = get_db_connection()
    settings = dict(conn.execute("SELECT key, value FROM settings").fetchall())
    conn.close()
    saved_user = settings.get('admin_username', 'admin')
    saved_pass = settings.get('admin_password', '123456')
    return username == saved_user and password == saved_pass

def authenticate():
    return Response('يرجى إدخال اسم المستخدم وكلمة المرور للدخول إلى لوحة التحكم', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# إعداد قاعدة البيانات وتحديث الأعمدة تلقائياً
DB_NAME = "store.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            image TEXT,
            available INTEGER DEFAULT 1,
            condition TEXT DEFAULT 'جديد',
            storage TEXT,
            ram TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('store_name', 'ليبيا تك - ليبيا')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('store_whatsapp', '218910000000')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('api_secret_key', 'libya-tech-api-secret-key-2026')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_username', 'admin')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', '123456')")
    
    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'image' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN image TEXT")
    if 'condition' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN condition TEXT DEFAULT 'جديد'")
    if 'storage' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN storage TEXT")
    if 'ram' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN ram TEXT")

    conn.commit()
    conn.close()

init_db()

def get_settings():
    conn = get_db_connection()
    settings = dict(conn.execute("SELECT key, value FROM settings").fetchall())
    conn.close()
    return settings

# الصفحة الرئيسية للمتجر
@app.route('/')
def index():
    settings = get_settings()
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products WHERE available = 1").fetchall()
    conn.close()
    return render_template('index.html', products=products, store_name=settings.get('store_name'), whatsapp=settings.get('store_whatsapp'))

# لوحة التحكم الرئيسية
@app.route('/admin')
@requires_auth
def admin():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    
    total_products = len(products)
    available_products = sum(1 for p in products if p['available'] == 1)
    unavailable_products = total_products - available_products

    conn.close()
    return render_template('admin.html', 
                           products=products, 
                           total_products=total_products,
                           available_products=available_products,
                           unavailable_products=unavailable_products)

# إضافة منتج جديد
@app.route('/admin/add', methods=['GET', 'POST'])
@requires_auth
def add_product():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            price = float(request.form.get('price', 0) or 0)
            category = request.form.get('category', '').strip()
            condition = request.form.get('condition', 'جديد')
            storage = request.form.get('storage', '').strip()
            ram = request.form.get('ram', '').strip()

            image_path = ''
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                    image_path = f"uploads/{unique_filename}"

            conn = get_db_connection()
            conn.execute("INSERT INTO products (name, price, category, image, condition, storage, ram) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (name, price, category, image_path, condition, storage, ram))
            conn.commit()
            conn.close()
            return redirect(url_for('admin'))
        except Exception as e:
            return f"<h3>حدث خطأ أثناء الإضافة:</h3><p>{str(e)}</p>", 500

    return render_template('add_product.html')

# تعديل منتج
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@requires_auth
def edit_product(id):
    conn = get_db_connection()
    product_row = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    
    if not product_row:
        conn.close()
        return "المنتج غير موجود", 404

    product = dict(product_row)

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            price = float(request.form.get('price', 0) or 0)
            category = request.form.get('category', '').strip()
            available = 1 if 'available' in request.form else 0
            condition = request.form.get('condition', 'جديد')
            storage = request.form.get('storage', '').strip()
            ram = request.form.get('ram', '').strip()

            image_path = product.get('image', '')
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                    image_path = f"uploads/{unique_filename}"

            conn.execute("""
                UPDATE products 
                SET name=?, price=?, category=?, image=?, available=?, condition=?, storage=?, ram=? 
                WHERE id=?
            """, (name, price, category, image_path, available, condition, storage, ram, id))
            conn.commit()
            conn.close()
            return redirect(url_for('admin'))
        except Exception as e:
            conn.close()
            return f"<h3>حدث خطأ أثناء التعديل:</h3><p>{str(e)}</p>", 500

    conn.close()
    return render_template('edit_product.html', product=product)

# حذف منتج
@app.route('/admin/delete/<int:id>')
@requires_auth
def delete_product(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# صفحة طباعة ملصق الـ QR Code
@app.route('/admin/qr')
@requires_auth
def store_qr():
    settings = get_settings()
    store_url = request.host_url
    return render_template('qr.html', store_name=settings.get('store_name'), store_url=store_url)

# إعدادات المحل (مع تحديث اسم المستخدم وكلمة المرور)
@app.route('/admin/settings', methods=['GET', 'POST'])
@requires_auth
def admin_settings():
    settings = get_settings()
    error = None
    success = None

    if request.method == 'POST':
        store_name = request.form.get('store_name')
        store_whatsapp = request.form.get('store_whatsapp')
        api_secret_key = request.form.get('api_secret_key')
        admin_username = request.form.get('admin_username')
        admin_password = request.form.get('admin_password')

        conn = get_db_connection()
        conn.execute("UPDATE settings SET value = ? WHERE key = 'store_name'", (store_name,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'store_whatsapp'", (store_whatsapp,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'api_secret_key'", (api_secret_key,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'admin_username'", (admin_username,))
        if admin_password:
            conn.execute("UPDATE settings SET value = ? WHERE key = 'admin_password'", (admin_password,))
        conn.commit()
        conn.close()

        success = "تم حفظ الإعدادات بنجاح!"
        settings = get_settings()

    return render_template('admin_settings.html',
                           store_name=settings.get('store_name'),
                           current_whatsapp=settings.get('store_whatsapp'),
                           api_secret_key=settings.get('api_secret_key'),
                           admin_username=settings.get('admin_username', 'admin'),
                           error=error,
                           success=success)

# رفع ملف CSV للمخزون
@app.route('/admin/upload-csv', methods=['POST'])
@requires_auth
def upload_csv():
    if 'file' not in request.files:
        return redirect(url_for('admin_settings'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('admin_settings'))

    if file:
        try:
            stream = io.TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(stream)

            conn = get_db_connection()
            for row in reader:
                name = str(row.get('name', '')).strip()
                price = float(row.get('price', 0) or 0)
                category = str(row.get('category', 'عام')).strip()
                image = str(row.get('image', '')).strip()
                condition = str(row.get('condition', 'جديد')).strip()
                storage = str(row.get('storage', '')).strip()
                ram = str(row.get('ram', '')).strip()

                if name:
                    existing = conn.execute("SELECT id FROM products WHERE name = ?", (name,)).fetchone()
                    if existing:
                        conn.execute("UPDATE products SET price = ?, category = ?, condition = ?, storage = ?, ram = ? WHERE id = ?",
                                     (price, category, condition, storage, ram, existing['id']))
                    else:
                        conn.execute("INSERT INTO products (name, price, category, image, condition, storage, ram) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                     (name, price, category, image, condition, storage, ram))
            conn.commit()
            conn.close()
        except Exception as e:
            print("CSV Error:", e)

    return redirect(url_for('admin'))

# REST API
@app.route('/api/v1/update-stock', methods=['POST'])
def api_update_stock():
    settings = get_settings()
    expected_key = settings.get('api_secret_key')
    provided_key = request.headers.get('X-API-KEY')

    if not provided_key or provided_key != expected_key:
        return jsonify({"status": "error", "message": "Unauthorized: Invalid API Key"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON body"}), 400

    product_id = data.get('product_id')
    product_name = data.get('name')
    new_price = data.get('price')
    available = data.get('available')
    condition = data.get('condition')
    storage = data.get('storage')
    ram = data.get('ram')

    conn = get_db_connection()
    product = None
    if product_id:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    elif product_name:
        product = conn.execute("SELECT * FROM products WHERE name = ?", (product_name,)).fetchone()

    if not product:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found"}), 404

    query = "UPDATE products SET "
    params = []

    if new_price is not None:
        query += "price = ?, "
        params.append(new_price)
    if available is not None:
        query += "available = ?, "
        params.append(available)
    if condition is not None:
        query += "condition = ?, "
        params.append(condition)
    if storage is not None:
        query += "storage = ?, "
        params.append(storage)
    if ram is not None:
        query += "ram = ?, "
        params.append(ram)

    query = query.rstrip(', ') + " WHERE id = ?"
    params.append(product['id'])

    conn.execute(query, params)
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Stock/Price updated successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)
