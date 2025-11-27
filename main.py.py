# main.py - النسخة النهائية والكاملة للتطبيق
import flet as ft
import sqlite3
from datetime import date
import csv
import os

# -------------------- ضبط المسار (نهائي) --------------------
# يضمن حفظ قاعدة البيانات بجوار ملف التشغيل
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "worker_manager_final.db"
DB = os.path.join(BASE_DIR, DB_NAME)

# -------------------- دوال قاعدة البيانات --------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    
    # جداول العملاء والحضور والمدفوعات والمصروفات
    c.execute("""CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, daily_rate REAL DEFAULT 0, days_worked INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, date TEXT, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, amount REAL, type TEXT, date TEXT, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, amount REAL, description TEXT, date TEXT)""")
    
    conn.commit()
    conn.close()

def fetch_clients(search=None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if search:
        c.execute("SELECT id, name, phone, daily_rate, days_worked FROM clients WHERE name LIKE ? ORDER BY name", (f"%{search}%",))
    else:
        c.execute("SELECT id, name, phone, daily_rate, days_worked FROM clients ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return rows

def insert_client(name, phone, rate):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO clients (name, phone, daily_rate, days_worked) VALUES (?, ?, ?, 0)", (name, phone, rate))
    conn.commit()
    conn.close()

def update_client_db(cid, name, phone, rate, days_worked):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE clients SET name=?, phone=?, daily_rate=?, days_worked=? WHERE id=?", (name, phone, rate, days_worked, cid))
    conn.commit()
    conn.close()

def delete_client_db(cid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE id=?", (cid,))
    conn.commit()
    conn.close()

def get_attendance_ids(date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT client_id FROM attendance WHERE date=?", (date_str,))
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    return ids

def toggle_attendance_db(cid, date_str, is_present):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM attendance WHERE client_id=? AND date=?", (cid, date_str))
    exists = c.fetchone()
    
    if is_present and not exists:
        c.execute("INSERT INTO attendance (client_id, date) VALUES (?, ?)", (cid, date_str))
        c.execute("UPDATE clients SET days_worked = days_worked + 1 WHERE id=?", (cid,))
    elif not is_present and exists:
        c.execute("DELETE FROM attendance WHERE client_id=? AND date=?", (cid, date_str))
        c.execute("UPDATE clients SET days_worked = days_worked - 1 WHERE id=?", (cid,))
    
    conn.commit()
    conn.close()


def get_payments(cid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, amount, type, date FROM payments WHERE client_id=? ORDER BY date DESC", (cid,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_payment_db(cid, amount, ptype):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    c.execute("INSERT INTO payments (client_id, amount, type, date) VALUES (?, ?, ?, ?)", (cid, amount, ptype, today))
    conn.commit()
    conn.close()

def delete_payment_db(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM payments WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    
def get_expenses():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, type, amount, description, date FROM expenses ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def add_expense_db(etype, amount, desc):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    c.execute("INSERT INTO expenses (type, amount, description, date) VALUES (?, ?, ?, ?)", (etype, amount, desc, today))
    conn.commit()
    conn.close()

def delete_expense_db(eid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=?", (eid,))
    conn.commit()
    conn.close()

def get_report_data():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clients")
    n_clients = c.fetchone()[0] or 0
    c.execute("SELECT SUM(days_worked) FROM clients")
    n_att = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM expenses WHERE type='دخل'")
    inc = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM expenses WHERE type='مصروف'")
    exp = c.fetchone()[0] or 0
    conn.close()
    return n_clients, n_att, inc, exp
# -------------------- نهاية دوال قاعدة البيانات --------------------

# -------------------- الواجهة (Flet) --------------------
def main(page: ft.Page):
    init_db()
    
    page.title = "مدير العمال"
    page.window_width = 400
    page.window_height = 800
    page.bgcolor = "#F0F4F8"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT

    snack = ft.SnackBar(content=ft.Text(""), bgcolor="green")
    page.overlay.append(snack)
    
    def notify(msg, color="green"):
        snack.content.value = msg
        snack.bgcolor = color
        snack.open = True
        page.update()

    screens = {}
    
    def go(screen_name):
        for name, col in screens.items():
            col.visible = (name == screen_name)
        
        if screen_name == "clients":
            load_clients_list()
        elif screen_name == "attendance":
            load_attendance_list()
        elif screen_name == "expenses":
            load_expenses_list()
        elif screen_name == "report":
            load_report_data()
        
        page.update()

    # --- مكونات شاشة التفاصيل (Client Details Screen Controls) ---
    detail_name = ft.TextField(label="الاسم")
    detail_phone = ft.TextField(label="موبايل")
    detail_rate = ft.TextField(label="اليومية")
    detail_days = ft.TextField(label="أيام العمل الإجمالية", disabled=True)
    detail_payments_list = ft.ListView(height=150, spacing=2)
    detail_pay_amt = ft.TextField(label="مبلغ", width=100)
    detail_pay_type = ft.Dropdown(width=100, options=[ft.dropdown.Option("دفع"), ft.dropdown.Option("سلفة")], value="دفع")
    current_cid = [None]

    # --- دوال شاشة التفاصيل ---

    def delete_pay_click(e):
        pid = e.control.data
        delete_payment_db(pid)
        load_payments_on_detail_screen(current_cid[0])
        notify("تم حذف الدفعة")

    def load_payments_on_detail_screen(cid):
        detail_payments_list.controls.clear()
        data = get_payments(cid)
        for row in data:
            pid, amt, typ, dt = row
            detail_payments_list.controls.append(
                ft.Row([
                    ft.Text(f"{dt} | {typ}: {amt}ج", expand=True),
                    ft.IconButton(ft.Icons.DELETE, icon_color="red", size=20, on_click=delete_pay_click, data=pid)
                ])
            )
        page.update()

    def save_client_details_click(e):
        if not current_cid[0]: return
        try:
            r = float(detail_rate.value)
            d = int(detail_days.value)
        except: return
        update_client_db(current_cid[0], detail_name.value, detail_phone.value, r, d)
        notify("تم حفظ التعديلات بنجاح")
        page.update()

    def add_pay_click(e):
        if not current_cid[0]: return
        try:
            val = float(detail_pay_amt.value)
        except:
            notify("المبلغ خطأ", "red"); return
        add_payment_db(current_cid[0], val, detail_pay_type.value)
        detail_pay_amt.value = ""
        load_payments_on_detail_screen(current_cid[0])
        notify("تم تسجيل العملية")

    def open_client_details_screen(cid):
        current_cid[0] = cid
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE id=?", (cid,))
        res = c.fetchone()
        conn.close()
        
        if res:
            detail_name.value = res[1]
            detail_phone.value = res[2]
            detail_rate.value = str(res[3])
            detail_days.value = str(res[4])
            load_payments_on_detail_screen(cid)
            go("client_details")
        else:
            notify("خطأ في تحميل بيانات العميل", "red")

    # -------------------- شاشة العملاء --------------------
    cl_search = ft.TextField(label="بحث بالاسم", prefix_icon=ft.Icons.SEARCH, width=250)
    cl_name_in = ft.TextField(label="اسم جديد", expand=True)
    cl_phone_in = ft.TextField(label="تليفون", width=120)
    cl_rate_in = ft.TextField(label="يومية", width=100)
    cl_list = ft.ListView(expand=True, spacing=5)

    def on_tile_click(e):
        cid = e.control.data
        open_client_details_screen(cid)

    def delete_client_click(e):
        cid = e.control.data
        delete_client_db(cid)
        notify("تم الحذف", "red")
        load_clients_list()

    def load_clients_list(e=None):
        cl_list.controls.clear()
        data = fetch_clients(cl_search.value)
        for row in data:
            cid, name, phone, rate, days = row
            tile = ft.ListTile(
                leading=ft.Icon(ft.Icons.PERSON),
                title=ft.Text(name, weight="bold"),
                subtitle=ft.Text(f"{phone} | {rate}ج | {days} يوم"),
                data=cid,
                on_click=on_tile_click,
                trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", data=cid, on_click=delete_client_click)
            )
            cl_list.controls.append(ft.Card(content=tile, elevation=2))
        page.update()

    def add_client_btn(e):
        if not cl_name_in.value: return
        try:
            r = float(cl_rate_in.value or 0)
        except: return
        insert_client(cl_name_in.value, cl_phone_in.value, r)
        cl_name_in.value = cl_phone_in.value = cl_rate_in.value = ""
        load_clients_list()
        notify("تمت الإضافة")

    screens["clients"] = ft.Column([
        ft.ElevatedButton("الرئيسية", icon=ft.Icons.HOME, on_click=lambda e: go("home")),
        ft.Text("إدارة العملاء", size=20, weight="bold"),
        ft.Row([cl_search, ft.IconButton(ft.Icons.REFRESH, on_click=load_clients_list)]),
        ft.Row([cl_name_in, cl_phone_in, cl_rate_in]),
        ft.ElevatedButton("إضافة عميل", on_click=add_client_btn, bgcolor="blue", color="white", width=400),
        ft.Divider(),
        cl_list
    ])
    
    # -------------------- شاشة تفاصيل العميل --------------------
    screens["client_details"] = ft.Column([
        ft.ElevatedButton("رجوع للعملاء", icon=ft.Icons.ARROW_BACK, on_click=lambda e: go("clients")),
        ft.Text("تعديل بيانات العميل", size=20, weight="bold"),
        detail_name, detail_phone, detail_rate, detail_days,
        ft.ElevatedButton("حفظ التعديلات", on_click=save_client_details_click, bgcolor="green", color="white", width=400),
        ft.Divider(),
        ft.Text("السجل المالي:", weight="bold"),
        detail_payments_list,
        ft.Row([detail_pay_amt, detail_pay_type, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="blue", on_click=add_pay_click)])
    ])
    
    # -----------------------------------------------------------
    # -------------------- شاشة الحضور --------------------
    # -----------------------------------------------------------
    att_date = ft.TextField(value=date.today().strftime("%Y-%m-%d"), label="تاريخ اليوم")
    att_list = ft.ListView(expand=True)

    def att_check_change(e):
        cid = e.control.data
        toggle_attendance_db(cid, att_date.value, e.control.value)

    def load_attendance_list(e=None):
        att_list.controls.clear()
        present_ids = get_attendance_ids(att_date.value)
        for row in fetch_clients():
            cid, name, _, _, _ = row
            chk = ft.Checkbox(
                label=name, 
                value=(cid in present_ids), 
                data=cid, 
                on_change=att_check_change
            )
            att_list.controls.append(chk)
        page.update()

    att_date.on_change = load_attendance_list

    screens["attendance"] = ft.Column([
        ft.ElevatedButton("الرئيسية", icon=ft.Icons.HOME, on_click=lambda e: go("home")),
        ft.Text("تسجيل الحضور اليومي", size=20, weight="bold"),
        att_date,
        ft.Divider(),
        att_list
    ])

    # -----------------------------------------------------------
    # -------------------- شاشة المصروفات --------------------
    # -----------------------------------------------------------
    exp_t = ft.Dropdown(options=[ft.dropdown.Option("مصروف"), ft.dropdown.Option("دخل")], value="مصروف", width=100)
    exp_a = ft.TextField(label="مبلغ", width=100)
    exp_d = ft.TextField(label="بيان/وصف", expand=True)
    exp_list = ft.ListView(expand=True)

    def del_exp(e):
        delete_expense_db(e.control.data)
        load_expenses_list()

    def load_expenses_list():
        exp_list.controls.clear()
        for row in get_expenses():
            eid, t, a, d, dt = row
            exp_list.controls.append(ft.Row([
                ft.Text(f"{dt} | {t}: {a}ج ({d})", expand=True),
                ft.IconButton(ft.Icons.DELETE, icon_color="red", data=eid, on_click=del_exp)
            ]))
        page.update()

    def add_exp(e):
        try:
            val = float(exp_a.value)
        except: return
        add_expense_db(exp_t.value, val, exp_d.value)
        exp_a.value = exp_d.value = ""
        load_expenses_list()

    screens["expenses"] = ft.Column([
        ft.ElevatedButton("الرئيسية", icon=ft.Icons.HOME, on_click=lambda e: go("home")),
        ft.Text("المصروفات والدخل", size=20, weight="bold"),
        ft.Row([exp_t, exp_a, exp_d]),
        ft.ElevatedButton("إضافة عملية", on_click=add_exp, bgcolor="blue", color="white"),
        ft.Divider(),
        exp_list
    ])

    # -----------------------------------------------------------
    # -------------------- شاشة التقرير --------------------
    # -----------------------------------------------------------
    rep_view = ft.Column(scroll=ft.ScrollMode.AUTO)

    def load_report_data():
        n, att, inc, exp = get_report_data()
        net = inc - exp
        
        rep_view.controls = [
            ft.Text(f"عدد العملاء المسجلين: {n}", size=18),
            ft.Text(f"إجمالي أيام العمل: {att}", size=18),
            ft.Divider(),
            ft.Text(f"إجمالي المقبوضات (الدخل): {inc} ج", size=18, color="green"),
            ft.Text(f"إجمالي المصروفات: {exp} ج", size=18, color="red"),
            ft.Text(f"الصافي: {net} ج", size=22, weight="bold", color="blue"),
        ]
        page.update()

    screens["report"] = ft.Column([
        ft.ElevatedButton("الرئيسية", icon=ft.Icons.HOME, on_click=lambda e: go("home")),
        ft.Text("التقرير المالي العام", size=20, weight="bold"),
        ft.ElevatedButton("تحديث البيانات", on_click=lambda e: load_report_data()),
        ft.Container(content=rep_view, padding=20, bgcolor="white", border_radius=10)
    ])

    # -----------------------------------------------------------
    # -------------------- الشاشة الرئيسية --------------------
    # -----------------------------------------------------------
    screens["home"] = ft.Column([
        ft.Icon(ft.Icons.DASHBOARD, size=60, color="blue"),
        ft.Text("نظام إدارة العمال", size=30, weight="bold"),
        ft.Container(height=20),
        ft.ElevatedButton("العملاء", width=250, height=60, on_click=lambda e: go("clients"), icon=ft.Icons.PEOPLE),
        ft.ElevatedButton("الحضور", width=250, height=60, on_click=lambda e: go("attendance"), icon=ft.Icons.CHECK),
        ft.ElevatedButton("المصروفات", width=250, height=60, on_click=lambda e: go("expenses"), icon=ft.Icons.MONEY),
        ft.ElevatedButton("التقرير", width=250, height=60, on_click=lambda e: go("report"), icon=ft.Icons.ANALYTICS),
    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    for s in screens.values(): page.add(s)
    go("home")

ft.app(target=main)
