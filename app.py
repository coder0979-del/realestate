from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'my_super_secret_key_12345'

# ---------------------------------------------------------
# Database Setup & Initialization
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("real_estate.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            type TEXT,
            address TEXT,
            rent_price REAL,
            status TEXT DEFAULT 'شاغر'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_code TEXT UNIQUE,
            tenant_name TEXT,
            property_name TEXT,
            total_amount REAL,
            start_date TEXT,
            status TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_code TEXT,
            payment_number INTEGER,
            due_date TEXT,
            amount REAL,
            status TEXT,
            FOREIGN KEY (contract_code) REFERENCES contracts (contract_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_name TEXT,
            category TEXT,
            amount REAL,
            expense_date TEXT,
            notes TEXT,
            FOREIGN KEY (property_name) REFERENCES properties (name)
        )
    """)
    
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# Routes / Views
# ---------------------------------------------------------
ADMIN_CREDENTIALS = {
    "email": "coder0979@gmail.com",
    "password": "admin123"
}

def init_db():
    conn = sqlite3.connect('real_estate.db')
    cursor = conn.cursor()
    # جدول العقارات
    cursor.execute('''CREATE TABLE IF NOT EXISTS properties (
                        name TEXT PRIMARY KEY, type TEXT, address TEXT, price REAL, status TEXT)''')
    # جدول العقود
    cursor.execute('''CREATE TABLE IF NOT EXISTS contracts (
                        contract_no TEXT PRIMARY KEY, tenant_name TEXT, property_name TEXT, start_date TEXT, total_amount REAL)''')
    # جدول الدفعات
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, contract_no TEXT, installment_no INTEGER, 
                        due_date TEXT, amount REAL, status TEXT)''')
    # جدول المصاريف
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, property_name TEXT, category TEXT, 
                        amount REAL, expense_date TEXT, notes TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == ADMIN_CREDENTIALS["email"] and password == ADMIN_CREDENTIALS["password"]:
            session['logged_in'] = True
            session['admin_email'] = email
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('index'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

# --- مسار إعادة تعيين كلمة المرور ---
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        
        if email == ADMIN_CREDENTIALS["email"]:
            ADMIN_CREDENTIALS["password"] = new_password
            flash('تم تحديث كلمة المرور بنجاح، يمكنك تسجيل الدخول الآن', 'success')
            return redirect(url_for('login'))
        else:
            flash('البريد الإلكتروني غير مسجل في النظام', 'danger')
    return render_template('reset_password.html')

# --- تسجيل الخروج ---
@app.route('/logout')
def logout():
    session.clear()
    
    return redirect(url_for('login'))

@app.route('/')
def index():
    # إذا لم يكن المستخدم مسجلاً للدخول، قم بعرض صفحة الهبوط بدلاً من لوحة التحكم
    if not session.get('logged_in'):
        return render_template('landing.html')
        
    conn = sqlite3.connect('real_estate.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()

    cursor.execute("SELECT * FROM contracts")
    contracts = cursor.fetchall()

    cursor.execute("SELECT * FROM payments")
    payments = cursor.fetchall()

    cursor.execute("SELECT * FROM expenses")
    expenses = cursor.fetchall()

    total_props = len(properties)
    rented_props = sum(1 for p in properties if p[4] == 'مؤجر')
    occ_rate = round((rented_props / total_props * 100) if total_props > 0 else 0, 1)

    total_inc = sum(p[4] for p in payments if p[5] == 'تم المدفوع')
    total_exp = sum(e[3] for e in expenses)
    net_profit = total_inc - total_exp

    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT contract_no, due_date, amount, status FROM payments WHERE due_date >= ? AND status != 'تم المدفوع' ORDER BY due_date ASC LIMIT 5", (today_str,))
    upcoming_payments = cursor.fetchall()

    conn.close()

    return render_template('index.html', 
                           properties=properties, 
                           contracts=contracts, 
                           payments=payments, 
                           expenses=expenses,
                           total_props=total_props,
                           occ_rate=occ_rate,
                           total_inc=total_inc,
                           net_profit=net_profit,
                           upcoming_payments=upcoming_payments)


@app.route('/add_property', methods=['POST'])
def add_property():
    name = request.form.get('name')
    p_type = request.form.get('type')
    address = request.form.get('address')
    price = request.form.get('price')

    if name and price:
        conn = sqlite3.connect("real_estate.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO properties (name, type, address, rent_price, status) VALUES (?, ?, ?, ?, ?)",
                           (name, p_type, address, float(price), "شاغر"))
            conn.commit()
        except:
            pass
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_contract', methods=['POST'])
def add_contract():
    tenant = request.form.get('tenant_name')
    property_name = request.form.get('property_name')
    total_amount = float(request.form.get('total_amount'))
    plan = int(request.form.get('installment_plan'))
    start_date = request.form.get('start_date')

    conn = sqlite3.connect("real_estate.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM contracts")
    count = cursor.fetchone()[0] + 101
    contract_code = f"CNT-{count}"

    cursor.execute("INSERT INTO contracts (contract_code, tenant_name, property_name, total_amount, start_date, status) VALUES (?, ?, ?, ?, ?, ?)",
                   (contract_code, tenant, property_name, total_amount, start_date, "نشط"))

    cursor.execute("UPDATE properties SET status = 'مؤجر' WHERE name = ?", (property_name,))

    installments_map = {1: 1, 2: 2, 4: 4, 12: 12}
    num_payments = installments_map.get(plan, 1)
    months_step = 12 // num_payments
    installment_amount = total_amount / num_payments

    from datetime import datetime, timedelta
    base_date = datetime.strptime(start_date, "%Y-%m-%d")

    for i in range(num_payments):
        due_date = (base_date + timedelta(days=30 * i * months_step)).strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO payments (contract_code, payment_number, due_date, amount, status) VALUES (?, ?, ?, ?, ?)",
                       (contract_code, i + 1, due_date, installment_amount, "مستحقة"))

    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/pay/<int:pay_id>')
def pay_payment(pay_id):
    conn = sqlite3.connect("real_estate.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status = 'تم المدفوع' WHERE id = ?", (pay_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    prop_name = request.form.get('property_name')
    category = request.form.get('category')
    amount = request.form.get('amount')
    exp_date = request.form.get('expense_date')
    notes = request.form.get('notes')

    if prop_name and amount:
        conn = sqlite3.connect("real_estate.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO expenses (property_name, category, amount, expense_date, notes) VALUES (?, ?, ?, ?, ?)",
                       (prop_name, category, float(amount), exp_date, notes))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=False, port=5000)