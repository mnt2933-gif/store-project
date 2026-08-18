-- جدول المنتجات (الهواتف واللابتوبات)
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- اسم الجهاز، مثلاً: iPhone 13 Pro
    brand TEXT NOT NULL,          -- الماركة: Apple, Samsung, HP, ...
    category TEXT NOT NULL,       -- phone أو laptop
    price REAL NOT NULL,          -- السعر بالدينار الليبي
    specs TEXT,                   -- المواصفات (رام، تخزين، معالج...)
    available INTEGER DEFAULT 1,  -- 1 = متوفر, 0 = غير متوفر
    image_url TEXT                -- رابط صورة (اختياري)
);

-- إعدادات عامة (تخزن كلمة مرور الأدمن بشكل قابل للتغيير)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
