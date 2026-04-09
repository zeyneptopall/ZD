import sqlite3
from datetime import datetime


def create_database():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT,
        price REAL NOT NULL DEFAULT 0,
        stock_quantity INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        sale_date TEXT NOT NULL,
        sold_by TEXT,
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )
    """)

    conn.commit()
    conn.close()


def insert_default_users():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin", "admin"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("cashier", "cashier", "cashier"),
    )
    conn.commit()
    conn.close()


def check_user(username, password):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# ── Products ─────────────────────────────────────────────────────────────────

def add_product(name, category, price, stock):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (product_name, category, price, stock_quantity) VALUES (?, ?, ?, ?)",
        (name, category, price, stock),
    )
    conn.commit()
    conn.close()


def get_products():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products


def update_product(product_id, name, category, price, stock):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE products
           SET product_name = ?, category = ?, price = ?, stock_quantity = ?
           WHERE product_id = ?""",
        (name, category, price, stock, product_id),
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()


# ── Sales ─────────────────────────────────────────────────────────────────────

def get_sales(start_date=None, end_date=None):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute(
            "SELECT * FROM sales WHERE sale_date >= ? AND sale_date <= ?",
            (start_date + " 00:00:00", end_date + " 23:59:59"),
        )
    else:
        cursor.execute("SELECT * FROM sales")
    sales = cursor.fetchall()
    conn.close()
    return sales


def get_sales_summary():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()

    cursor.execute("SELECT IFNULL(SUM(total_price), 0) FROM sales")
    total_revenue = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sales")
    total_sales_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT p.product_name, IFNULL(SUM(s.quantity), 0) as total_qty
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        GROUP BY s.product_id
        ORDER BY total_qty DESC
        LIMIT 1
    """)
    top_product = cursor.fetchone()

    conn.close()

    if top_product:
        return total_revenue, total_sales_count, top_product[0], top_product[1]
    return total_revenue, total_sales_count, "No sales yet", 0


def get_sales_by_product():
    """Returns (product_name, total_qty_sold) for chart."""
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.product_name, IFNULL(SUM(s.quantity), 0) as total_qty
        FROM products p
        LEFT JOIN sales s ON s.product_id = p.product_id
        GROUP BY p.product_id
        ORDER BY total_qty DESC
    """)
    result = cursor.fetchall()
    conn.close()
    return result


def record_sale(product_id, quantity, sold_by=None):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT price, stock_quantity FROM products WHERE product_id = ?",
        (product_id,),
    )
    product = cursor.fetchone()

    if not product:
        conn.close()
        return "Product not found"

    price, stock_quantity = product

    if quantity > stock_quantity:
        conn.close()
        return "Not enough stock"

    total_price = price * quantity
    sale_date   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO sales (product_id, quantity, total_price, sale_date, sold_by)
        VALUES (?, ?, ?, ?, ?)
    """, (product_id, quantity, total_price, sale_date, sold_by))

    cursor.execute("""
        UPDATE products SET stock_quantity = stock_quantity - ?
        WHERE product_id = ?
    """, (quantity, product_id))

    conn.commit()
    conn.close()
    return "Sale recorded successfully"


def cancel_sale(sale_id):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT product_id, quantity FROM sales WHERE sale_id = ?", (sale_id,)
    )
    sale = cursor.fetchone()

    if not sale:
        conn.close()
        return "Sale not found"

    product_id, quantity = sale

    cursor.execute("""
        UPDATE products SET stock_quantity = stock_quantity + ?
        WHERE product_id = ?
    """, (quantity, product_id))

    cursor.execute("DELETE FROM sales WHERE sale_id = ?", (sale_id,))

    conn.commit()
    conn.close()
    return "Sale cancelled successfully"


# ── Users ─────────────────────────────────────────────────────────────────────

def get_users():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return users


def add_user(username, password, role):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role),
        )
        conn.commit()
        conn.close()
        return "User added successfully"
    except sqlite3.IntegrityError:
        conn.close()
        return "Username already exists"


def delete_user(user_id):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
