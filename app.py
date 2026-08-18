import sqlite3
import os
import csv
import io
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, g, session, flash

app = Flask(__name__)
app.secret_key = "change-this-secret-key-later"  # أي نص عشوائي، غيريه قبل التسليم النهائي

DATABASE = os.path.join(os.path.dirname(__file__), "store.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# قيم افتراضية أول مرة يشتغل فيها الموقع
DEFAULT_STORE_WHATSAPP = "218900000000"
DEFAULT_STORE_NAME = "متجر تجريبي - Demo Store"

# كلمة مرور لوحة التحكم
ADMIN_PASSWORD = "admin123"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ---------- إدارة قاعدة البيانات ----------

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
            db.executescript(f.read())
        db.commit()

        # نضيف بيانات تجريبية فقط إذا كان الجدول فاضي
        count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            sample_products = [
                ("iPhone 13", "Apple", "phone", 3200, "128GB - رام 4GB - كاميرا 12MP", 1, "https://placehold.co/300x300?text=iPhone+13"),
                ("iPhone 15 Pro", "Apple", "phone", 6500, "256GB - رام 8GB - كاميرا 48MP", 1, "https://placehold.co/300x300?text=iPhone+15+Pro"),
                ("Samsung Galaxy S23", "Samsung", "phone", 4200, "256GB - رام 8GB - شاشة AMOLED", 1, "https://placehold.co/300x300?text=Galaxy+S23"),
                ("Samsung Galaxy A54", "Samsung", "phone", 1800, "128GB - رام 6GB", 0, "https://placehold.co/300x300?text=Galaxy+A54"),
                ("HP Pavilion 15", "HP", "laptop", 2900, "Core i5 - رام 8GB - تخزين 512GB SSD", 1, "https://placehold.co/300x300?text=HP+Pavilion"),
                ("Lenovo IdeaPad 3", "Lenovo", "laptop", 2100, "Core i3 - رام 8GB - تخزين 256GB SSD", 1, "https://placehold.co/300x300?text=IdeaPad+3"),
                ("MacBook Air M2", "Apple", "laptop", 8900, "رام 8GB - تخزين 256GB SSD", 1, "https://placehold.co/300x300?text=MacBook+Air"),
                ("Dell Inspiron 15", "Dell", "laptop", 2500, "Core i5 - رام 8GB - تخزين 512GB SSD", 0, "https://placehold.co/300x300?text=Dell+Inspiron"),
            ]
            db.executemany(
                "INSERT INTO products (name, brand, category, price, specs, available, image_url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                sample_products,
            )
            db.commit()

        # نضيف كلمة مرور افتراضية في جدول settings إذا ما كانت موجودة
        existing = db.execute("SELECT value FROM settings WHERE key = 'admin_password_hash'").fetchone()
        if existing is None:
            db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ("admin_password_hash", generate_password_hash(ADMIN_PASSWORD)),
            )
            db.commit()

        # نضيف رقم الواتساب واسم المحل الافتراضيين
        for key, default_value in [
            ("store_whatsapp", DEFAULT_STORE_WHATSAPP),
            ("store_name", DEFAULT_STORE_NAME),
        ]:
            existing = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if existing is None:
                db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, default_value))
                db.commit()


def get_admin_password_hash():
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = 'admin_password_hash'").fetchone()
    return row["value"] if row else None


def get_setting(key, default=""):
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    db.commit()


# ---------- الصفحات الرئيسية (للزبون) ----------

@app.route("/")
def index():
    db = get_db()

    q = request.args.get("q", "").strip()
    brand = request.args.get("brand", "")
    category = request.args.get("category", "")
    max_price = request.args.get("max_price", "")

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if q:
        query += " AND name LIKE ?"
        params.append(f"%{q}%")
    if brand:
        query += " AND brand = ?"
        params.append(brand)
    if category:
        query += " AND category = ?"
        params.append(category)
    if max_price:
        query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY available DESC, price ASC"
    products = db.execute(query, params).fetchall()

    brands = db.execute("SELECT DISTINCT brand FROM products ORDER BY brand").fetchall()

    return render_template(
        "index.html",
        products=products,
        brands=brands,
        store_name=get_setting("store_name", DEFAULT_STORE_NAME),
        selected_brand=brand,
        selected_category=category,
        selected_q=q,
        selected_max_price=max_price,
    )


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        return "المنتج غير موجود", 404

    whatsapp_text = f"مرحباً، أنا مهتم بجهاز {product['name']} بسعر {product['price']} د.ل، هل هو متوفر؟"
    store_whatsapp = get_setting("store_whatsapp", DEFAULT_STORE_WHATSAPP)
    whatsapp_link = f"https://wa.me/{store_whatsapp}?text={whatsapp_text}"

    return render_template(
        "product.html",
        product=product,
        store_name=get_setting("store_name", DEFAULT_STORE_NAME),
        whatsapp_link=whatsapp_link,
    )


# ---------- لوحة التحكم (لصاحب المحل) ----------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        entered = request.form.get("password", "")
        stored_hash = get_admin_password_hash()
        if stored_hash and check_password_hash(stored_hash, entered):
            session["logged_in"] = True
            return redirect(url_for("admin"))
        error = "كلمة المرور غلط، حاولي مرة ثانية"
    return render_template("admin_login.html", store_name=get_setting("store_name", DEFAULT_STORE_NAME), error=error)


@app.route("/admin/change-password", methods=["GET", "POST"])
@login_required
def admin_change_password():
    error = None
    success = None
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new1 = request.form.get("new_password", "")
        new2 = request.form.get("new_password_confirm", "")
        stored_hash = get_admin_password_hash()

        if not check_password_hash(stored_hash, current):
            error = "كلمة المرور الحالية غلط"
        elif len(new1) < 4:
            error = "كلمة المرور الجديدة قصيرة جداً"
        elif new1 != new2:
            error = "كلمة المرور الجديدة غير متطابقة"
        else:
            db = get_db()
            db.execute(
                "UPDATE settings SET value = ? WHERE key = 'admin_password_hash'",
                (generate_password_hash(new1),),
            )
            db.commit()
            success = "تم تغيير كلمة المرور بنجاح"

    return render_template(
        "admin_change_password.html", store_name=get_setting("store_name", DEFAULT_STORE_NAME), error=error, success=success
    )


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    error = None
    success = None
    if request.method == "POST":
        new_name = request.form.get("store_name", "").strip()
        new_whatsapp = request.form.get("store_whatsapp", "").strip()

        if not new_name or not new_whatsapp:
            error = "الاسم والرقم مطلوبين"
        elif not new_whatsapp.isdigit():
            error = "رقم الواتساب لازم يكون أرقام بس (مع كود الدولة، مثلاً 218912345678)"
        else:
            set_setting("store_name", new_name)
            set_setting("store_whatsapp", new_whatsapp)
            success = "تم حفظ الإعدادات بنجاح"

    return render_template(
        "admin_settings.html",
        store_name=get_setting("store_name", DEFAULT_STORE_NAME),
        current_whatsapp=get_setting("store_whatsapp", DEFAULT_STORE_WHATSAPP),
        error=error,
        success=success,
    )


@app.route("/admin/upload-csv", methods=["POST"])
@login_required
def upload_csv():
    file = request.files.get("file")
    if not file:
        return redirect(url_for("admin_settings"))

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        db = get_db()

        for row in csv_input:
            db.execute(
                "INSERT INTO products (name, brand, category, price, specs, available, image_url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    row.get("name", "منتج جديد"),
                    row.get("brand", "عام"),
                    row.get("category", "phone"),
                    row.get("price", 0),
                    row.get("specs", ""),
                    1,
                    row.get("image_url", "https://placehold.co/300x300?text=Product"),
                ),
            )
        db.commit()
        return redirect(url_for("admin_settings"))
    except Exception as e:
        return redirect(url_for("admin_settings"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("admin.html", products=products, store_name=get_setting("store_name", DEFAULT_STORE_NAME))


@app.route("/admin/add", methods=["POST"])
@login_required
def admin_add():
    db = get_db()

    image_url = request.form.get("image_url", "")

    file = request.files.get("image_file")
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        filename = f"{db.execute('SELECT COUNT(*) FROM products').fetchone()[0] + 1}_{filename}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        image_url = url_for("static", filename=f"uploads/{filename}")

    db.execute(
        "INSERT INTO products (name, brand, category, price, specs, available, image_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            request.form["name"],
            request.form["brand"],
            request.form["category"],
            request.form["price"],
            request.form["specs"],
            1 if request.form.get("available") == "on" else 0,
            image_url,
        ),
    )
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/toggle/<int:product_id>", methods=["POST"])
@login_required
def admin_toggle(product_id):
    db = get_db()
    db.execute(
        "UPDATE products SET available = 1 - available WHERE id = ?", (product_id,)
    )
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:product_id>", methods=["POST"])
@login_required
def admin_delete(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    else:
        init_db()
    app.run(debug=True)
