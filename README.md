# Demo Store

#### Video Demo: <[Https://youtu.be/PVdHy1XxjD4?si=HdBSUCO7c8YasbsI>

#### Description:

**Demo Store** is a lightweight online catalog system I built as my CS50x final project to solve a real problem faced by many small and medium phone/laptop shops in Libya: their complete reliance on Facebook posts to display products. This approach forces customers to scroll through dozens of old and new posts searching for a specific device, and forces shop owners to manually answer the same repeated questions ("How much is it?", "Is it available?") hundreds of times. The project solves this by providing a simple, fast website that gathers all of a shop's products in one place, with instant search and filtering, plus a button that takes the customer directly to a pre-filled WhatsApp conversation with the device details already included — without added complexity like a shopping cart or payment gateway, since most of these shops prefer to complete the sale manually, as they already do.

The project was built using **Python** and **Flask** as the backend framework, chosen for being lightweight and straightforward, well suited to a project of this size without the added complexity of larger frameworks like Django. The database started as **SQLite** for local development, then moved to **Supabase** (a cloud-hosted PostgreSQL database) after deployment, because Render's free hosting tier does not persist changes made to local SQLite databases after the server restarts — a problem I discovered firsthand during testing, which led me to switch to a persistent storage solution suitable for a site that a real shop would use daily. The frontend is built with **HTML** and **Bootstrap 5** to ensure a responsive design that works well on mobile phones, since most customers will browse the site from their phones rather than a computer.

**File breakdown:**

- **`app.py`**: The main application file, containing all of the app's routes. It is logically split into two parts: public customer-facing pages (`/` for the catalog with search and filtering, `/product/<id>` for device details), and password-protected admin pages (`/admin` for managing products, `/admin/settings` for editing the shop name and WhatsApp number, `/admin/change-password`). It also includes a programmatic API endpoint (`/api/v1/update-stock`), protected by a secret API key, which allows a shop that already has its own inventory system to update prices automatically without manual intervention.

- **`schema.sql`**: Defines two tables: `products`, which stores each device's data (name, brand, category, price, specs, availability status, image URL), and `settings`, which stores editable configuration (hashed password, shop name, WhatsApp number) instead of hardcoding them, making it easy to customize the site for each shop without touching the code itself.

- **`templates/`**: Contains the Jinja2 templates responsible for rendering pages: `layout.html` (the shared base layout), `index.html` (the catalog with search, filtering, and a comparison feature), `product.html` (device details and the WhatsApp button), and `admin.html` plus its related templates for the admin panel.

- **`static/`**: Contains `style.css` for additional styling, and an `uploads/` folder for product images uploaded directly by the shop owner.

- **`requirements.txt`**: Lists the libraries required to run the project (Flask, gunicorn for production serving, and others).

**Key design decisions:**

I chose to protect the admin panel with session-based authentication rather than a simpler approach, because any real shop genuinely needs to prevent regular customers from reaching its product management area. The password is stored as a **hash** (via `werkzeug.security`) rather than plain text, to avoid any security risk even if the database itself were ever accessed directly. I also chose to add a "change password" page inside the admin panel itself, so that when the site is eventually handed over to a shop, the owner can change the default password themselves immediately upon receiving it, without needing any further involvement from me.

This project, despite its apparent simplicity, practically covers most of the concepts I learned in CS50: relational databases (SQL), web development in Python, session management and security, and working with APIs. I used an AI tool (Claude) as an assistant during development to help debug errors and suggest technical solutions, in line with CS50's policy of using such tools to assist rather than replace one's own work.
