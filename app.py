import os
import uuid
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from werkzeug.utils import secure_filename
from functools import wraps
from supabase import create_client, Client

app = Flask(__name__)

# مجلد حفظ الصور المرفوعة محلياً
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SUPABASE_URL = "https://jghhfdpidostankjghvr.supabase.co"
SUPABASE_KEY = "sb_publishable__4PZ29q-_wsEY9vS-adQKQ_oC_aQdnJ"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# --- إعدادات الحماية لوحة التحكم ---
def check_auth(username, password):
    try:
        res = supabase.table('settings').select("value").eq('key', 'admin_username').execute()
        saved_user = res.data[0]['value'] if res.data else 'admin'
        
        res_pass = supabase.table('settings').select("value").eq('key', 'admin_password').execute()
        saved_pass = res_pass.data[0]['value'] if res_pass.data else '123456'
        
        return username == saved_user and password == saved_pass
    except:
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

def get_settings():
    try:
        res = supabase.table('settings').select("key, value").execute()
        if res.data:
            return {row['key']: row['value'] for row in res.data}
    except:
        pass
    return {
        'store_name': 'ليبيا تك - ليبيا',
        'store_whatsapp': '218910000000',
        'api_secret_key': 'libya-tech-api-secret-key-2026',
        'admin_username': 'admin',
        'admin_password': '123456'
    }

# الصفحة الرئيسية للمتجر
@app.route('/')
def index():
    settings = get_settings()
    try:
        res = supabase.table('products').select("*").eq('available', 1).execute()
        products = res.data if res.data else []
    except:
        products = []
    return render_template('index.html', products=products, store_name=settings.get('store_name'), whatsapp=settings.get('store_whatsapp'))

# لوحة التحكم الرئيسية
@app.route('/admin')
@requires_auth
def admin():
    try:
        res = supabase.table('products').select("*").execute()
        products = res.data if res.data else []
    except:
        products = []
    
    total_products = len(products)
    available_products = sum(1 for p in products if p.get('available') == 1)
    unavailable_products = total_products - available_products

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

            supabase.table('products').insert({
                "name": name,
                "price": price,
                "category": category,
                "image": image_path,
                "available": 1,
                "condition": condition,
                "storage": storage,
                "ram": ram
            }).execute()

            return redirect(url_for('admin'))
        except Exception as e:
            return f"<h3>حدث خطأ أثناء الإضافة:</h3><p>{str(e)}</p>", 500

    return render_template('add_product.html')

# تعديل منتج
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@requires_auth
def edit_product(id):
    try:
        res = supabase.table('products').select("*").eq('id', id).execute()
        if not res.data:
            return "المنتج غير موجود", 404
        product = res.data[0]
    except:
        return "المنتج غير موجود", 404

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

            supabase.table('products').update({
                "name": name,
                "price": price,
                "category": category,
                "image": image_path,
                "available": available,
                "condition": condition,
                "storage": storage,
                "ram": ram
            }).eq('id', id).execute()

            return redirect(url_for('admin'))
        except Exception as e:
            return f"<h3>حدث خطأ أثناء التعديل:</h3><p>{str(e)}</p>", 500

    return render_template('edit_product.html', product=product)

# حذف منتج
@app.route('/admin/delete/<int:id>')
@requires_auth
def delete_product(id):
    try:
        supabase.table('products').delete().eq('id', id).execute()
    except:
        pass
    return redirect(url_for('admin'))

# صفحة طباعة ملصق الـ QR Code
@app.route('/admin/qr')
@requires_auth
def store_qr():
    settings = get_settings()
    store_url = request.host_url
    return render_template('qr.html', store_name=settings.get('store_name'), store_url=store_url)

# إعدادات المحل
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

        try:
            supabase.table('settings').upsert({"key": "store_name", "value": store_name}).execute()
            supabase.table('settings').upsert({"key": "store_whatsapp", "value": store_whatsapp}).execute()
            supabase.table('settings').upsert({"key": "api_secret_key", "value": api_secret_key}).execute()
            supabase.table('settings').upsert({"key": "admin_username", "value": admin_username}).execute()
            if admin_password:
                supabase.table('settings').upsert({"key": "admin_password", "value": admin_password}).execute()
            
            success = "تم حفظ الإعدادات بنجاح!"
            settings = get_settings()
        except Exception as e:
            error = str(e)

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

            for row in reader:
                name = str(row.get('name', '')).strip()
                price = float(row.get('price', 0) or 0)
                category = str(row.get('category', 'عام')).strip()
                image = str(row.get('image', '')).strip()
                condition = str(row.get('condition', 'جديد')).strip()
                storage = str(row.get('storage', '')).strip()
                ram = str(row.get('ram', '')).strip()

                if name:
                    res = supabase.table('products').select("id").eq('name', name).execute()
                    if res.data:
                        prod_id = res.data[0]['id']
                        supabase.table('products').update({
                            "price": price,
                            "category": category,
                            "condition": condition,
                            "storage": storage,
                            "ram": ram
                        }).eq('id', prod_id).execute()
                    else:
                        supabase.table('products').insert({
                            "name": name,
                            "price": price,
                            "category": category,
                            "image": image,
                            "available": 1,
                            "condition": condition,
                            "storage": storage,
                            "ram": ram
                        }).execute()
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

    try:
        query = supabase.table('products').select("*")
        if product_id:
            query = query.eq('id', product_id)
        elif product_name:
            query = query.eq('name', product_name)
        else:
            return jsonify({"status": "error", "message": "Product not found"}), 404

        res = query.execute()
        if not res.data:
            return jsonify({"status": "error", "message": "Product not found"}), 404
        
        product = res.data[0]
        update_data = {}
        
        if data.get('price') is not None:
            update_data['price'] = data.get('price')
        if data.get('available') is not None:
            update_data['available'] = data.get('available')
        if data.get('condition') is not None:
            update_data['condition'] = data.get('condition')
        if data.get('storage') is not None:
            update_data['storage'] = data.get('storage')
        if data.get('ram') is not None:
            update_data['ram'] = data.get('ram')

        if update_data:
            supabase.table('products').update(update_data).eq('id', product['id']).execute()

        return jsonify({"status": "success", "message": "Stock/Price updated successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
