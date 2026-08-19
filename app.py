import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from functools import wraps

app = Flask(__name__)

# --- إعدادات الحماية ---
def check_auth(username, password):
    # غيّري كلمة السر هنا بكلمة قوية!
    return username == 'admin' and password == '123456' 

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
# ----------------------

# إعداد قاعدة البيانات
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
    conn.commit()
    conn.close()

init_db()

def get_settings():
    conn = get_db_connection()
    settings = dict(conn.execute("SELECT key, value FROM settings").fetchall())
    conn.close()
    return settings

# الصفحة الرئيسية (لا تحتاج حماية)
@app.route('/')
def index():
    settings = get_settings()
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products WHERE available = 1").fetchall()
    conn.close()
    return render_template('index.html', products=products, store_name=settings.get('store_name'), whatsapp=settings.get('store_whatsapp'))

# لوحة التحكم الرئيسية (محمية)
@app.route('/admin')
@requires_auth
def admin():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    total_products = len(products)
    available_products = sum(1 for p in products if p['available'] == 1)
    unavailable_products = total_products - available_products
    conn.close()
    return render_template('admin.html', products=products, total_products=total_products, 
                           available_products=available_products, unavailable_products=unavailable_products)

# إضافة منتج (محمية)
@app.route('/admin/add', methods=['GET', 'POST'])
@requires_auth
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        category = request.form['category']
        image = request.form['image']
        condition = request.form.get('condition', 'جديد')
        storage = request.form.get('storage', '')
        ram = request.form.get('ram', '')
        conn = get_db_connection()
        conn.execute("INSERT INTO products (name, price, category, image, condition, storage, ram) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (name, price, category, image, condition, storage, ram))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('add_product.html')

# تعديل منتج (محمية)
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@requires_auth
def edit_product(id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        category = request.form['category']
        image = request.form['image']
        available = 1 if 'available' in request.form else 0
        condition = request.form.get('condition', 'جديد')
        storage = request.form.get('storage', '')
        ram = request.form.get('ram', '')
        conn.execute("UPDATE products SET name=?, price=?, category=?, image=?, available=?, condition=?, storage=?, ram=? WHERE id=?",
                     (name, price, category, image, available, condition, storage, ram, id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    conn.close()
    return render_template('edit_product.html', product=product)

# حذف منتج (محمية)
@app.route('/admin/delete/<int:id>')
@requires_auth
def delete_product(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# إعدادات المحل (محمية)
@app.route('/admin/settings', methods=['GET', 'POST'])
@requires_auth
def admin_settings():
    settings = get_settings()
    if request.method == 'POST':
        store_name = request.form.get('store_name')
        store_whatsapp = request.form.get('store_whatsapp')
        api_secret_key = request.form.get('api_secret_key')
        conn = get_db_connection()
        conn.execute("UPDATE settings SET value = ? WHERE key = 'store_name'", (store_name,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'store_whatsapp'", (store_whatsapp,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'api_secret_key'", (api_secret_key,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_settings'))
    return render_template('admin_settings.html', store_name=settings.get('store_name'), 
                           current_whatsapp=settings.get('store_whatsapp'), api_secret_key=settings.get('api_secret_key'))

# باقي الدوال (API وما شابه) تبقى كما هي بدون requires_auth إذا لم تكن تتطلب دخولاً بشرياً
@app.route('/api/v1/update-stock', methods=['POST'])
def api_update_stock():
    # ... كود الـ API ...
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
