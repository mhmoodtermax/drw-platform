from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_123"

# ================= DB =================
def init_db():
    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        invite_code TEXT,
        referred_by TEXT
)
""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        message TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= HOME =================
@app.route("/")
def home():
    if "email" not in session:
        return redirect("/login")

    email = session["email"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE email = ?", (email,))
    user = c.fetchone()

    c.execute(
    "SELECT message, date FROM notifications WHERE email = ? ORDER BY id DESC LIMIT 5",
    (email,)
)

    notifications = c.fetchall()

    conn.close()

    balance = user[0] if user else 0

    return render_template(
    "home.html",
    email=email,
    balance=balance,
    notifications=notifications
)

from datetime import datetime

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():

    if "email" not in session:
        return redirect("/login")

    email = session["email"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute(
        "SELECT balance FROM users WHERE email = ?",
        (email,)
    )

    user = c.fetchone()
    balance = user[0] if user else 0

    if request.method == "POST":

        amount_text = request.form.get("amount")

        if not amount_text:
            conn.close()
            flash("❌ أدخل مبلغ")
            return redirect("/withdraw")

        amount = float(amount_text)

        if amount < 15:
            conn.close()
            flash("❌ الحد الأدنى 15")
            return redirect("/withdraw")

        if amount > balance:
            conn.close()
            flash("❌ لا يوجد رصيد كافي")
            return redirect("/withdraw")

        # خصم الرصيد
        new_balance = balance - amount

        c.execute(
            "UPDATE users SET balance = ? WHERE email = ?",
            (new_balance, email)
        )

        # التاريخ الحقيقي
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # إشعار
        message = f"تم السحب بنجاح {amount} USDT"

        c.execute(
            "INSERT INTO notifications (email, message, date) VALUES (?, ?, ?)",
            (email, message, now)
        )

        conn.commit()
        conn.close()

        flash("✅ تم السحب بنجاح")
        return redirect("/")

    conn.close()

    return render_template(
        "withdraw.html",
        balance=balance
    )

# ================= DEPOSIT (IMPORTANT) =================
@app.route("/deposit")
def deposit():
    return render_template("deposit.html")

# ================= TEAM =================
@app.route("/team")
def team():

    email = session["email"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    # 🔥 جلب كود الدعوة
    c.execute("SELECT invite_code FROM users WHERE email=?", (email,))
    row = c.fetchone()

    invite_code = row[0] if row else ""

    # 🔥 رابط الدعوة
    invite_link = f"http://127.0.0.1:8080/register?ref={invite_code}"

    # 🔥 عدد الفريق
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (invite_code,))
    team_count = c.fetchone()[0]

    conn.close()

    return render_template(
        "team.html",
        invite_link=invite_link,
        team_count=team_count
    )

# ================= TASKS =================
@app.route("/tasks")
def tasks():
    return render_template("tasks.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if "@gmail.com" not in email:
            return "❌ لازم Gmail فقط"

        conn = sqlite3.connect("db.db")
        c = conn.cursor()

        # 🔥 كود الدعوة
        invite_code = email.split("@")[0]

        # 🔥 كود الإحالة من الرابط (لو موجود)
        ref = request.args.get("ref")

        try:
            c.execute(
                "INSERT INTO users (email, password, balance, invite_code, referred_by) VALUES (?, ?, ?, ?, ?)",
                (email, password, 15, invite_code, ref)
            )

            conn.commit()

        except:
            return "❌ الحساب موجود"

        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("db.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()

        conn.close()

        if user:
            session["email"] = email
            return redirect("/")
        else:
            return "❌ خطأ بيانات"

    return render_template("login.html")

# ================= VIP =================
@app.route("/vip")
def vip():

    if "email" not in session:
        return redirect("/login")

    email = session["email"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE email=?", (email,))
    row = c.fetchone()

    balance = row[0] if row else 0

    conn.close()

    return render_template("vip.html", balance=balance)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
