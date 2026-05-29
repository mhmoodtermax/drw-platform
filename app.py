from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "secret_key_123"

# ================== DB ==================
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
        referred_by TEXT,
        verified INTEGER DEFAULT 0
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS email_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        code TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= HOME =================
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE email = ?", (email,))
    user = c.fetchone()

    c.execute("SELECT message, date FROM notifications")
    notifications = c.fetchall()

    conn.close()

    balance = user[0] if user else 0

    return render_template(
        "home.html",
        email=email,
        balance=balance,
        notifications=notifications
    )

# ================= WITHDRAW =================
@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():

    if "user" not in session:
        return redirect("/login")

    email = session["user"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    if request.method == "POST":

        c.execute("SELECT balance FROM users WHERE email=?", (email,))
        row = c.fetchone()

        if not row:
            conn.close()
            return "User not found"

        balance = row[0]

        amount = float(request.form["amount"])

        if amount < 15:
            flash("❌ الحد الأدنى 15")
            conn.close()
            return redirect("/withdraw")

        if amount > balance:
            flash("❌ رصيد غير كافي")
            conn.close()
            return redirect("/withdraw")

        new_balance = balance - amount

        c.execute("UPDATE users SET balance=? WHERE email=?", (new_balance, email))

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        c.execute(
            "INSERT INTO notifications(email,message,date) VALUES(?,?,?)",
            (email, f"تم السحب {amount} USDT", now)
        )

        conn.commit()
        conn.close()

        flash("✅ تم السحب")
        return redirect("/")

    # GET request
    c.execute("SELECT balance FROM users WHERE email=?", (email,))
    row = c.fetchone()

    balance = row[0] if row else 0

    conn.close()

    return render_template("withdraw.html", balance=balance)

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():

    # نخزن ref من الرابط (GET)
    ref = request.args.get("ref")

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if "@gmail.com" not in email:
            return "❌ لازم Gmail فقط"

        conn = sqlite3.connect("db.db")
        c = conn.cursor()

        c.execute("SELECT id FROM users WHERE email=?", (email,))
        if c.fetchone():
            conn.close()
            return "❌ الحساب موجود"

        import uuid
        invite_code = str(uuid.uuid4())[:8]

        # 🔥 حفظ بيانات المستخدم مع الإحالة
        c.execute("""
            INSERT INTO users (email, password, balance, invite_code, referred_by)
            VALUES (?, ?, ?, ?, ?)
        """, (email, password, 0, invite_code, ref))

        conn.commit()
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

        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()

        conn.close()

        if user:
            session["user"] = email
            return redirect("/")
        else:
            return "❌ خطأ بيانات"

    return render_template("login.html")

# ================= TEAM =================
@app.route("/team")
def team():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    # invite code للمستخدم
    c.execute("SELECT invite_code FROM users WHERE email=?", (email,))
    row = c.fetchone()

    if not row:
        conn.close()
        return "User not found"

    invite_code = row[0]

    # رابط الدعوة الصحيح
    link = f"https://drw-platform.onrender.com/register?ref={invite_code}"

    # عدد الفريق (المهم هنا referred_by)
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (invite_code,))
    count = c.fetchone()[0]

    conn.close()

    return render_template("team.html", invite_link=link, team_count=count)

# ================= VIP =================
@app.route("/vip")
def vip():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE email=?", (email,))
    balance = c.fetchone()[0]

    conn.close()

    return render_template("vip.html", balance=balance)

# ================= 🔥 NEW ROUTES (FIXED BUTTONS) =================

@app.route("/deposit")
def deposit():
    if "user" not in session:
        return redirect("/login")
    return render_template("deposit.html")


@app.route("/tasks")
def tasks():
    if "user" not in session:
        return redirect("/login")
    return render_template("tasks.html")


@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    return render_template("profile.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
