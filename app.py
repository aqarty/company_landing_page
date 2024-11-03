import os
import sqlite3
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# التأكد من إنشاء مجلد التحميل إذا لم يكن موجودًا
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# السماح بامتدادات ملفات معينة فقط
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# بيانات الدخول الخاصة بالمدير
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = bcrypt.hashpw("admin_password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# إعداد قاعدة البيانات وإنشاء الجداول
def init_db():
    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    # إنشاء جدول الشركات الرئيسية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            logo_url TEXT NOT NULL,
            website_url TEXT NOT NULL,
            description TEXT
        )
    ''')

    # إنشاء جدول الشركات التابعة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subsidiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_company_id INTEGER NULL,
            name TEXT NOT NULL,
            logo_url TEXT NOT NULL,
            website_url TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (parent_company_id) REFERENCES companies (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# استدعاء تهيئة قاعدة البيانات
init_db()

# صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # تحقق من صحة بيانات الدخول
        if username == ADMIN_USERNAME and bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8')):
            session['logged_in'] = True
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('admin'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')

    return render_template('login.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('login'))

# حماية لوحة التحكم
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        flash('يجب تسجيل الدخول للوصول إلى لوحة التحكم', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()

    # إضافة شركة جديدة (رئيسية أو تابعة)
    if request.method == 'POST':
        company_type = request.form['company_type']
        name = request.form['name']
        logo_url = ""
        website_url = request.form['website_url']
        description = request.form['description']
        
        # التحقق من رفع صورة والتحقق من نوعها
        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                logo_url = file_path
            else:
                flash("صيغة الملف غير مدعومة. الرجاء رفع صورة بصيغة PNG، JPG، أو GIF.", "danger")
                return redirect(url_for('admin'))

        if company_type == 'main':  # إضافة شركة رئيسية
            cursor.execute('INSERT INTO companies (name, logo_url, website_url, description) VALUES (?, ?, ?, ?)',
                           (name, logo_url, website_url, description))
            flash('تمت إضافة الشركة الرئيسية بنجاح!', 'success')
        elif company_type == 'subsidiary':  # إضافة شركة تابعة
            cursor.execute('INSERT INTO subsidiaries (parent_company_id, name, logo_url, website_url, description) VALUES (?, ?, ?, ?, ?)',
                           (None, name, logo_url, website_url, description))
            flash('تمت إضافة الشركة التابعة بنجاح!', 'success')
        
        conn.commit()
        return redirect(url_for('admin'))

    # جلب قائمة الشركات الرئيسية
    cursor.execute('SELECT * FROM companies')
    companies = cursor.fetchall()

    # جلب قائمة الشركات التابعة
    cursor.execute('SELECT * FROM subsidiaries')
    subsidiaries = cursor.fetchall()

    conn.close()
    return render_template('admin.html', companies=companies, subsidiaries=subsidiaries)

# تعديل شركة رئيسية
@app.route('/edit_company/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    if not session.get('logged_in'):
        flash('يجب تسجيل الدخول للوصول إلى لوحة التحكم', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        company = cursor.fetchone()
        conn.close()
        return render_template('edit_company.html', company=company)
    
    elif request.method == 'POST':
        name = request.form['name']
        website_url = request.form['website_url']
        description = request.form['description']
        logo_url = request.form['logo_url']  # الشعار الحالي

        # التحقق من رفع شعار جديد والتحقق من نوعه
        if 'new_logo' in request.files:
            file = request.files['new_logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                logo_url = file_path  # تحديث الشعار إلى الشعار الجديد
            else:
                flash("صيغة الملف غير مدعومة. الرجاء رفع صورة بصيغة PNG، JPG، أو GIF.", "danger")
                return redirect(url_for('admin'))

        cursor.execute('UPDATE companies SET name = ?, logo_url = ?, website_url = ?, description = ? WHERE id = ?',
                       (name, logo_url, website_url, description, company_id))
        conn.commit()
        conn.close()
        flash('تم تعديل الشركة بنجاح!', 'success')
        return redirect(url_for('admin'))

# تعديل شركة تابعة
@app.route('/edit_subsidiary/<int:subsidiary_id>', methods=['GET', 'POST'])
def edit_subsidiary(subsidiary_id):
    if not session.get('logged_in'):
        flash('يجب تسجيل الدخول للوصول إلى لوحة التحكم', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute('SELECT * FROM subsidiaries WHERE id = ?', (subsidiary_id,))
        subsidiary = cursor.fetchone()
        conn.close()
        return render_template('edit_subsidiary.html', subsidiary=subsidiary)
    
    elif request.method == 'POST':
        name = request.form['name']
        website_url = request.form['website_url']
        description = request.form['description']
        logo_url = request.form['logo_url']  # الشعار الحالي

        # التحقق من رفع شعار جديد والتحقق من نوعه
        if 'new_logo' in request.files:
            file = request.files['new_logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                logo_url = file_path  # تحديث الشعار إلى الشعار الجديد
            else:
                flash("صيغة الملف غير مدعومة. الرجاء رفع صورة بصيغة PNG، JPG، أو GIF.", "danger")
                return redirect(url_for('admin'))

        cursor.execute('UPDATE subsidiaries SET name = ?, logo_url = ?, website_url = ?, description = ? WHERE id = ?',
                       (name, logo_url, website_url, description, subsidiary_id))
        conn.commit()
        conn.close()
        flash('تم تعديل الشركة التابعة بنجاح!', 'success')
        return redirect(url_for('admin'))

# حذف شركة رئيسية
@app.route('/delete_company/<int:company_id>', methods=['POST'])
def delete_company(company_id):
    if not session.get('logged_in'):
        flash('يجب تسجيل الدخول للوصول إلى لوحة التحكم', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    # حذف الشركات التابعة المرتبطة بالشركة الرئيسية
    cursor.execute('DELETE FROM subsidiaries WHERE parent_company_id = ?', (company_id,))
    cursor.execute('DELETE FROM companies WHERE id = ?', (company_id,))
    
    conn.commit()
    conn.close()
    flash('تم حذف الشركة الرئيسية وجميع الشركات التابعة لها بنجاح!', 'danger')
    return redirect(url_for('admin'))

# حذف شركة تابعة
@app.route('/delete_subsidiary/<int:subsidiary_id>', methods=['POST'])
def delete_subsidiary(subsidiary_id):
    if not session.get('logged_in'):
        flash('يجب تسجيل الدخول للوصول إلى لوحة التحكم', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM subsidiaries WHERE id = ?', (subsidiary_id,))
    
    conn.commit()
    conn.close()
    flash('تم حذف الشركة التابعة بنجاح!', 'danger')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
