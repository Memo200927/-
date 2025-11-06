# phone_app.py
import flet as ft
import sqlite3
from datetime import date
import csv

DB = "manager_app_complete.db"

# -------------------- DATABASE INITIALIZATION --------------------
def init_db():
    conn = None
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys = ON")

        # clients table
        c.execute("""
            CREATE TABLE IF NOT EXISTS clients(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                daily_rate REAL DEFAULT 0,
                days_worked INTEGER DEFAULT 0
            )
        """)

        # attendance table
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                date TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # payments table (payments and advances for clients)
        c.execute("""
            CREATE TABLE IF NOT EXISTS payments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                amount REAL,
                type TEXT,
                date TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # expenses table
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL,
                description TEXT,
                date TEXT
            )
        """)

        # ensure columns exist for older DBs
        cols = [r[1] for r in c.execute("PRAGMA table_info(clients)").fetchall()]
        if "daily_rate" not in cols:
            try:
                c.execute("ALTER TABLE clients ADD COLUMN daily_rate REAL DEFAULT 0")
            except Exception:
                pass
        if "days_worked" not in cols:
            try:
                c.execute("ALTER TABLE clients ADD COLUMN days_worked INTEGER DEFAULT 0")
            except Exception:
                pass

        conn.commit()
    except sqlite3.Error as e:
        print("DB init error:", e)
    finally:
        if conn:
            conn.close()

# -------------------- DB HELPERS --------------------
def fetch_clients(order_by_name=True, search=None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if search:
        q = f"%{search}%"
        c.execute("SELECT id, name, phone, daily_rate, days_worked FROM clients WHERE name LIKE ? ORDER BY name", (q,))
    else:
        c.execute("SELECT id, name, phone, daily_rate, days_worked FROM clients ORDER BY name" if order_by_name else "SELECT id, name, phone, daily_rate, days_worked FROM clients")
    rows = c.fetchall()
    conn.close()
    return rows

def insert_client(name, phone, rate):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO clients (name, phone, daily_rate, days_worked) VALUES (?, ?, ?, 0)", (name, phone, rate))
    conn.commit()
    conn.close()

def update_client_db(cid, name, phone, rate, days_worked=None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE clients SET name=?, phone=?, daily_rate=? WHERE id=?", (name, phone, rate, cid))
    if days_worked is not None:
        c.execute("UPDATE clients SET days_worked=? WHERE id=?", (days_worked, cid))
    conn.commit()
    conn.close()

def delete_client_db(cid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE id=?", (cid,))
    conn.commit()
    conn.close()

# attendance
def get_attendance_ids(date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT client_id FROM attendance WHERE date=?", (date_str,))
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    return ids

def register_attendance_db(cid, date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM attendance WHERE client_id=? AND date=?", (cid, date_str))
    if not c.fetchone():
        c.execute("INSERT INTO attendance (client_id, date) VALUES (?, ?)", (cid, date_str))
        c.execute("UPDATE clients SET days_worked = days_worked + 1 WHERE id=?", (cid,))
    conn.commit()
    conn.close()

def remove_attendance_db(cid, date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE client_id=? AND date=?", (cid, date_str))
    c.execute("UPDATE clients SET days_worked = days_worked - 1 WHERE id=?", (cid,))
    conn.commit()
    conn.close()

# payments
def get_payments_for_client(cid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, amount, type, date FROM payments WHERE client_id=? ORDER BY date DESC", (cid,))
    rows = c.fetchall()
    conn.close()
    return rows

def insert_payment(cid, amount, ptype):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    c.execute("INSERT INTO payments (client_id, amount, type, date) VALUES (?, ?, ?, ?)", (cid, amount, ptype, today))
    conn.commit()
    conn.close()

def delete_payment(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM payments WHERE id=?", (pid,))
    conn.commit()
    conn.close()

# expenses / incomes
def get_all_expenses():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, type, amount, description, date FROM expenses ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def insert_expense(type_, amount, desc):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    c.execute("INSERT INTO expenses (type, amount, description, date) VALUES (?, ?, ?, ?)", (type_, amount, desc, today))
    conn.commit()
    conn.close()

def delete_expense_db(eid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=?", (eid,))
    conn.commit()
    conn.close()

def update_expense_db(eid, type_, amount, desc):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE expenses SET type=?, amount=?, description=? WHERE id=?", (type_, amount, desc, eid))
    conn.commit()
    conn.close()

# report
def compute_report():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clients")
    num_clients = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM attendance")
    total_att = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM expenses WHERE type='دخل'")
    total_income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM expenses WHERE type='مصروف'")
    total_exp = c.fetchone()[0] or 0
    conn.close()
    net = (total_income or 0) - (total_exp or 0)
    return num_clients, total_att, (total_income or 0), (total_exp or 0), net

# -------------------- UI (FLET) --------------------
def main(page: ft.Page):
    init_db()

    page.title = "نظام إدارة العمال - كامل"
    page.window_width = 500
    page.window_height = 900
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#FFFDF8"

    # snackbar (use page.snack_bar so we can mutate it)
    page.snack_bar = ft.SnackBar(content=ft.Text(""), bgcolor=ft.Colors.GREEN, open=False)

    def notify(message, color="green"):
        page.snack_bar.content.value = message
        page.snack_bar.bgcolor = ft.Colors.GREEN if color == "green" else ft.Colors.RED
        page.snack_bar.open = True
        page.update()

    screens = {}

    # ---------- HOME ----------
    home_col = ft.Column([
        ft.Text("🏠 لوحة التحكم", size=22, weight="bold"),
        ft.ElevatedButton("👷 إدارة العملاء", width=320, on_click=lambda e: go("clients")),
        ft.ElevatedButton("🕒 الحضور اليومي", width=320, on_click=lambda e: go("attendance")),
        ft.ElevatedButton("💰 المصروفات والإيرادات", width=320, on_click=lambda e: go("expenses")),
        ft.ElevatedButton("📊 التقرير المالي", width=320, on_click=lambda e: go("report")),
        ft.Text("مصمم بواسطة: مريم علاء", size=12, color="#6A1B9A")
    ], spacing=12, alignment=ft.MainAxisAlignment.CENTER)
    screens["home"] = home_col

    # ---------- CLIENTS SCREEN ----------
    search_field = ft.TextField(label="بحث بالاسم", width=300)
    client_name = ft.TextField(label="الاسم", width=220)
    client_phone = ft.TextField(label="الهاتف", width=140)
    client_rate = ft.TextField(label="الأجر اليومي", width=140)
    clients_list = ft.ListView(expand=True, spacing=6)

    def refresh_clients(search=None):
        clients_list.controls.clear()
        rows = fetch_clients(search=search)
        for cid, name, phone, rate, days in rows:
            # row with name clickable
            name_btn = ft.ElevatedButton(name, expand=True, on_click=lambda e, cid=cid: open_client_detail(cid))
            info = ft.Text(f"{phone or ''} | أجر: {rate} | أيام: {days}", size=12)
            del_btn = ft.ElevatedButton("حذف", bgcolor="red", color="white", on_click=lambda e, cid=cid: (delete_client_and_refresh(cid)))
            clients_list.controls.append(ft.Row([name_btn, info, del_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        page.update()

    def delete_client_and_refresh(cid):
        delete_client_db(cid)
        notify("✅ تم حذف العميل", "green")
        refresh_clients()
        refresh_attendance()
        refresh_report_ui() # <--- تم التصحيح هنا
        page.update()

    def add_client_action(e):
        name = client_name.value.strip()
        if not name:
            notify("⚠️ ادخلي اسم العميل", "red")
            return
        try:
            rate_val = float(client_rate.value or 0)
        except:
            notify("⚠️ أدخلي أجر يومي صحيح", "red")
            return
        insert_client(name, client_phone.value.strip(), rate_val)
        client_name.value = client_phone.value = client_rate.value = ""
        notify("✅ تم إضافة العميل", "green")
        refresh_clients()
        refresh_attendance()
        refresh_report_ui() # <--- تم التصحيح هنا
        page.update()

    def open_client_detail(cid):
        # fetch client
        client = None
        for r in fetch_clients():
            if r[0] == cid:
                client = r
                break
        if not client:
            notify("⚠️ العميل غير موجود", "red")
            return
        cid, name, phone, rate, days = client

        # build detail UI
        name_f = ft.TextField(label="الاسم", value=name, width=260)
        phone_f = ft.TextField(label="الهاتف", value=phone or "", width=160)
        rate_f = ft.TextField(label="الأجر اليومي", value=str(rate or 0), width=140)
        days_f = ft.TextField(label="عدد الأيام", value=str(days or 0), width=120)

        payments_list = ft.ListView(expand=True, spacing=6)
        def refresh_payments_list():
            payments_list.controls.clear()
            for pid, amount, ptype, dt in get_payments_for_client(cid):
                payments_list.controls.append(ft.Row([ft.Text(f"{dt} | {ptype}: {amount}ج"), ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", on_click=lambda e, pid=pid: (delete_payment(pid), refresh_payments_list(), refresh_report_ui()))])) # <--- تم التصحيح هنا
            page.update()
        refresh_payments_list()

        payment_amount = ft.TextField(label="المبلغ", width=140)
        payment_type = ft.Dropdown(width=140, value="دفع", options=[ft.dropdown.Option("دفع"), ft.dropdown.Option("سلفة")])
        def add_payment_action(e):
            try:
                amt = float(payment_amount.value)
            except:
                notify("⚠️ أدخلي مبلغ صحيح", "red")
                return
            insert_payment(cid, amt, payment_type.value)
            payment_amount.value = ""
            notify("✅ تم تسجيل الدفعة", "green")
            refresh_payments_list()
            refresh_report_ui() # <--- تم التصحيح هنا
            page.update()

        def save_client_changes(e):
            new_name = name_f.value.strip()
            try:
                new_rate = float(rate_f.value or 0)
                new_days = int(days_f.value or 0)
            except:
                notify("⚠️ القيم غير صحيحة", "red")
                return
            update_client_db(cid, new_name, phone_f.value.strip(), new_rate, new_days)
            notify("✅ تم حفظ التعديلات", "green")
            refresh_clients()
            refresh_attendance()
            refresh_report_ui() # <--- تم التصحيح هنا
            go("clients")

        def delete_client_from_detail(e):
            delete_client_db(cid)
            notify("✅ تم حذف العميل", "green")
            refresh_clients()
            refresh_attendance()
            go("clients")

        details = ft.Column([
            ft.Row([ft.ElevatedButton("رجوع", on_click=lambda e: go("clients"))]),
            ft.Text(f"ملف العميل — {name}", size=18, weight="bold"),
            name_f, phone_f, rate_f, days_f,
            ft.Row([ft.ElevatedButton("💾 حفظ", on_click=save_client_changes), ft.ElevatedButton("❌ حذف العميل", bgcolor="red", color="white", on_click=delete_client_from_detail)], spacing=10),
            ft.Divider(),
            ft.Text("الدفعات:", weight="bold"),
            payments_list,
            ft.Row([payment_amount, payment_type, ft.ElevatedButton("إضافة دفعة", on_click=add_payment_action)], spacing=8)
        ], spacing=10)

        # replace clients screen content
        screens["clients"].controls.clear()
        screens["clients"].controls.append(details)
        screens["clients"].visible = True
        page.update()

    clients_controls = ft.Column([
        ft.Row([ft.ElevatedButton("رجوع", on_click=lambda e: go("home"))]),
        ft.Text("👷 إدارة العملاء", size=18, weight="bold"),
        ft.Row([search_field, ft.ElevatedButton("بحث", on_click=lambda e: refresh_clients(search_field.value))]),
        ft.Row([client_name, client_phone, client_rate, ft.ElevatedButton("حفظ", on_click=add_client_action)], spacing=8),
        ft.Text("قائمة العملاء:", weight="bold"),
        clients_list
    ], spacing=10)
    screens["clients"] = clients_controls

    # ---------- ATTENDANCE ----------
    att_date_field = ft.TextField(label="التاريخ (YYYY-MM-DD)", value=date.today().strftime("%Y-%m-%d"), width=200)
    attendance_list = ft.ListView(expand=True, spacing=6)

    def refresh_attendance():
        attendance_list.controls.clear()
        cur_date = att_date_field.value
        attended = get_attendance_ids(cur_date)
        for cid, name, phone, rate, days in fetch_clients():
            checked = cid in attended
            checkbox = ft.Checkbox(label=f"{name} | {phone or ''}", value=checked)
            def toggle(e, cid_val=cid, date_val=cur_date, chk=checkbox):
                if chk.value:
                    register_attendance_db(cid_val, date_val)
                else:
                    remove_attendance_db(cid_val, date_val)
                refresh_attendance()
                refresh_clients()
                refresh_report_ui() # <--- تم التصحيح هنا
            checkbox.on_change = toggle
            attendance_list.controls.append(checkbox)
        page.update()

    attendance_controls = ft.Column([
        ft.Row([ft.ElevatedButton("رجوع", on_click=lambda e: go("home"))]),
        ft.Text("🕒 الحضور اليومي", size=18, weight="bold"),
        att_date_field,
        ft.Row([ft.ElevatedButton("تحديث", on_click=lambda e: refresh_attendance()), ft.ElevatedButton("حفظ", on_click=lambda e: notify("✅ تم الحفظ","green"))]),
        attendance_list
    ], spacing=10)
    screens["attendance"] = attendance_controls

    # ---------- EXPENSES / INCOME ----------
    exp_type = ft.Dropdown(width=150, value="مصروف", options=[ft.dropdown.Option("مصروف"), ft.dropdown.Option("دخل")])
    exp_amount = ft.TextField(label="المبلغ", width=150)
    exp_desc = ft.TextField(label="الوصف", width=250)
    expenses_list_view = ft.ListView(expand=True, spacing=6)

    # edit state
    edit_exp_id = {"id": None}

    def refresh_expenses_ui():
        expenses_list_view.controls.clear()
        for eid, t, a, d, dt in get_all_expenses():
            edit_btn = ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, id=eid, tt=t, aa=a, dd=d: start_edit_expense(id, tt, aa, dd))
            del_btn = ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", on_click=lambda e, id=eid: (delete_expense_db(id), notify("🗑️ تم الحذف","green"), refresh_expenses_ui(), refresh_report_ui())) # <--- تم التصحيح هنا
            expenses_list_view.controls.append(ft.Row([ft.Text(f"{dt} | {t}: {a} ج.م | {d}", expand=True), edit_btn, del_btn]))
        page.update()

    def start_edit_expense(eid, t, a, d):
        exp_type.value = t
        exp_amount.value = str(a)
        exp_desc.value = d
        edit_exp_id["id"] = eid
        save_expense_button.text = "تحديث"

    def save_expense_action(e):
        try:
            amt = float(exp_amount.value)
        except:
            notify("⚠️ أدخلي مبلغ صحيح", "red")
            return
        typ = exp_type.value
        desc = exp_desc.value
        if edit_exp_id["id"]:
            update_expense_db(edit_exp_id["id"], typ, amt, desc)
            notify("✏️ تم التحديث", "green")
            edit_exp_id["id"] = None
            save_expense_button.text = "حفظ"
        else:
            insert_expense(typ, amt, desc)
            notify("✅ تم الإضافة", "green")
        exp_amount.value = exp_desc.value = ""
        refresh_expenses_ui()
        refresh_report_ui() # <--- تم التصحيح هنا
        page.update()

    save_expense_button = ft.ElevatedButton("حفظ", on_click=save_expense_action)

    expenses_controls = ft.Column([
        ft.Row([ft.ElevatedButton("رجوع", on_click=lambda e: go("home"))]),
        ft.Text("💰 المصروفات والإيرادات", size=18, weight="bold"),
        ft.Row([exp_type, exp_amount, exp_desc, save_expense_button], spacing=8),
        ft.Text("السجل:", weight="bold"),
        expenses_list_view
    ], spacing=10)
    screens["expenses"] = expenses_controls

    # ---------- REPORT ----------
    report_text = ft.Text("", size=14)

    def refresh_report_ui():
        n, att, inc, exp, net = compute_report()
        report_text.value = (
            f"عدد العملاء: {n}\n"
            f"إجمالي الحضور: {att}\n"
            f"إجمالي الدخل: {inc} ج.م\n"
            f"إجمالي المصروف: {exp} ج.م\n"
            f"صافي الأرباح: {net} ج.م"
        )
        page.update()

    report_controls = ft.Column([
        ft.Row([ft.ElevatedButton("رجوع", on_click=lambda e: go("home"))]),
        ft.Text("📊 التقرير المالي", size=18, weight="bold"),
        ft.Row([ft.ElevatedButton("تحديث", on_click=lambda e: (refresh_report_ui(), notify('✅ تم التحديث','green'))), ft.ElevatedButton("تصدير CSV", on_click=lambda e: export_report())]),
        report_text
    ], spacing=10)
    screens["report"] = report_controls

    def export_report():
        n, att, inc, exp, net = compute_report()
        with open("financial_report.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["عدد العملاء", "إجمالي الحضور", "إجمالي الدخل", "إجمالي المصروف", "صافي الأرباح"])
            w.writerow([n, att, inc, exp, net])
        notify("✅ تم تصدير financial_report.csv", "green")

    # ---------- NAV / ADD SCREENS ----------
    def go(name):
        for s in screens.values():
            s.visible = False
        screens[name].visible = True
        page.update()

    # add all screens to page
    for s in screens.values():
        page.add(s)

    # initial fills
    refresh_clients()
    refresh_attendance()
    refresh_expenses_ui()
    refresh_report_ui()

    # show home
    page.add(screens["home"])
    go("home")

# entrypoint
if __name__ == "__main__":
    init_db()
    ft.app(target=main)
