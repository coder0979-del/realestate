from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
app.secret_key = 'my_super_secret_key_12345'

# ---------------------------------------------------------
# Database Setup & Initialization
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("real_estate.db")
    cursor = conn.cursor()
    
    # جدول العقارات (الاعتماد على name كـ Primary Key ومطابقة أسماء الأعمدة)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            name TEXT PRIMARY KEY, 
            type TEXT, 
            address TEXT, 
            price REAL, 
            status TEXT DEFAULT 'شاغر'
        )
    """)
    
    # جدول العقود
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            contract_code TEXT PRIMARY KEY, 
            tenant_name TEXT, 
            property_name TEXT, 
            start_date TEXT, 
            total_amount REAL,
            status TEXT DEFAULT 'نشط'
        )
    """)
    
    # جدول الدفعات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            contract_code TEXT, 
            installment_no INTEGER, 
            due_date TEXT, 
            amount REAL, 
            status TEXT,
            FOREIGN KEY (contract_code) REFERENCES contracts (contract_code)
        )
    """)

    # جدول المصاريف
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

init_db()

# ---------------------------------------------------------
# Routes / Views
# ---------------------------------------------------------
ADMIN_CREDENTIALS = {
    "email": "coder0979@gmail.com",
    "password": "admin123"
}

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
    # إذا لم يكن المستخدم مسجلاً للدخول، عرض صفحة الهبوط
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
    cursor.execute("SELECT contract_code, due_date, amount, status FROM payments WHERE due_date >= ? AND status != 'تم المدفوع' ORDER BY due_date ASC LIMIT 5", (today_str,))
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
    if not session.get('logged_in'): return redirect(url_for('login'))
    name = request.form.get('name')
    p_type = request.form.get('type')
    address = request.form.get('address')
    price = request.form.get('price')

    if name and price:
        conn = sqlite3.connect("real_estate.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO properties (name, type, address, price, status) VALUES (?, ?, ?, ?, ?)",
                           (name, p_type, address, float(price), "شاغر"))
            conn.commit()
        except Exception as e:
            print("Error adding property:", e)
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete_property/<name>')
def delete_property(name):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect('real_estate.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM properties WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    flash('تم حذف العقار بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/add_contract', methods=['POST'])
def add_contract():
    if not session.get('logged_in'): return redirect(url_for('login'))
    tenant = request.form.get('tenant_name')
    property_name = request.form.get('property_name')
    total_amount = float(request.form.get('total_amount'))
    plan = int(request.form.get('installment_plan', 1))
    start_date = request.form.get('start_date')

    conn = sqlite3.connect("real_estate.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM contracts")
    count = cursor.fetchone()[0] + 101
    contract_code = f"CNT-{count}"

    cursor.execute("INSERT INTO contracts (contract_code, tenant_name, property_name, start_date, total_amount, status) VALUES (?, ?, ?, ?, ?, ?)",
                   (contract_code, tenant, property_name, start_date, total_amount, "نشط"))

    cursor.execute("UPDATE properties SET status = 'مؤجر' WHERE name = ?", (property_name,))

    num_payments = plan
    months_step = 12 // num_payments if num_payments <= 12 else 1
    installment_amount = total_amount / num_payments

    base_date = datetime.strptime(start_date, "%Y-%m-%d")

    for i in range(num_payments):
        due_date = (base_date + timedelta(days=30 * i * months_step)).strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO payments (contract_code, installment_no, due_date, amount, status) VALUES (?, ?, ?, ?, ?)",
                       (contract_code, i + 1, due_date, installment_amount, "مستحقة"))

    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_contract/<contract_code>')
def delete_contract(contract_code):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect('real_estate.db')
    cursor = conn.cursor()
    
    # تحرير العقار وإعادته لحالة شاغر
    cursor.execute("SELECT property_name FROM contracts WHERE contract_code = ?", (contract_code,))
    res = cursor.fetchone()
    if res:
        prop_name = res[0]
        cursor.execute("UPDATE properties SET status = 'شاغر' WHERE name = ?", (prop_name,))
    
    # حذف العقد والدفعات المرتبطة به
    cursor.execute("DELETE FROM contracts WHERE contract_code = ?", (contract_code,))
    cursor.execute("DELETE FROM payments WHERE contract_code = ?", (contract_code,))
    
    conn.commit()
    conn.close()
    flash('تم حذف العقد وتحرير العقار بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/pay/<int:pay_id>')
def pay_payment(pay_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect("real_estate.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status = 'تم المدفوع' WHERE id = ?", (pay_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not session.get('logged_in'): return redirect(url_for('login'))
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

@app.route('/download_pdf_report')
def download_pdf_report():
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
        
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 750, "Amlak Enterprise - Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, "This is an automated financial and property report.")
    
    conn = sqlite3.connect('real_estate.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, type, price, status FROM properties")
    props = cursor.fetchall()
    conn.close()
    
    y = 650
    for prop in props:
        text = f"Property: {prop[0]} | Type: {prop[1]} | Price: {prop[2]} | Status: {prop[3]}"
        p.drawString(50, y, text)
        y -= 25
        if y < 50:
            p.showPage()
            y = 750

    p.save()
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name="amlak_report.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, port=5000)