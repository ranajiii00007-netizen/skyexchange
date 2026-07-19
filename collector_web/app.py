import os
import sys
import io
import csv
from datetime import date, timedelta, datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file,
    send_from_directory,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import uuid

# ReportLab Imports
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("COLLECTOR_WEB_SECRET", "change-this-secret")

# File Upload Settings
is_vercel_env = bool(os.environ.get("VERCEL"))
if is_vercel_env:
    UPLOAD_FOLDER = "/tmp"
else:
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "collector_web", "static", "uploads")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}

# Make sure folder exists
if not is_vercel_env:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import base64

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, filename):
    file_data = file.read()
    mime_type = file.mimetype or "application/octet-stream"
    encoded_data = base64.b64encode(file_data).decode("utf-8")
    
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR REPLACE INTO uploaded_files (filename, mime_type, data) VALUES (?, ?, ?)",
            (filename, mime_type, encoded_data)
        )
        conn.commit()
    finally:
        conn.close()

@app.route("/static/uploads/<path:filename>")
def custom_static_uploads(filename):
    # Try fetching from DB first
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT mime_type, data FROM uploaded_files WHERE filename=?", (filename,))
        row = cur.fetchone()
        if row:
            mime_type, encoded_data = row
            file_data = base64.b64decode(encoded_data)
            return Response(file_data, mimetype=mime_type)
    except Exception:
        pass
    finally:
        conn.close()

    # Fallback to local files
    if is_vercel_env:
        return send_from_directory("/tmp", filename)
    else:
        return send_from_directory(os.path.join(app.static_folder, "uploads"), filename)

@app.route("/manifest_customer.json")
def manifest_customer():
    return send_from_directory(app.static_folder, "manifest_customer.json", mimetype="application/json")

@app.route("/manifest_banker.json")
def manifest_banker():
    return send_from_directory(app.static_folder, "manifest_banker.json", mimetype="application/json")

@app.route("/manifest_collector.json")
def manifest_collector():
    return send_from_directory(app.static_folder, "manifest_collector.json", mimetype="application/json")

@app.route("/sw_customer.js")
def sw_customer():
    response = send_from_directory(app.static_folder, "sw_customer.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@app.route("/sw_banker.js")
def sw_banker():
    response = send_from_directory(app.static_folder, "sw_banker.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@app.route("/sw_collector.js")
def sw_collector():
    response = send_from_directory(app.static_folder, "sw_collector.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response

_DATABASE_READY = False



def is_vercel():
    return bool(os.environ.get("VERCEL"))


def get_admin_password():
    for key in ("COLLECTOR_ADMIN_PASSWORD", "ADMIN_PASSWORD"):
        value = os.environ.get(key, "")
        if value.strip():
            return value.strip()
    return "admin123"


def ensure_database_ready():
    global _DATABASE_READY
    if _DATABASE_READY:
        return

    if is_vercel() and not database.using_postgres():
        raise RuntimeError("DATABASE_URL is not configured in Vercel.")

    if not is_vercel():
        database.create_tables()

    _DATABASE_READY = True


def db():
    ensure_database_ready()
    return database.connect_db(reuse_postgres=True)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("collector_name"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def log_admin_action(action, details=""):
    admin_username = session.get("admin_username", "Unknown Admin")
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO admin_logs (admin_username, action, details, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                admin_username,
                action,
                details,
                request.remote_addr or "N/A",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
    except Exception as exc:
        print(f"Error logging admin action: {exc}")
    finally:
        conn.close()


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)

    return wrapper


def super_admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin") or session.get("admin_role") != "SUPER":
            flash("This page is restricted to Super Admin only.", "error")
            return redirect(url_for("admin_dashboard"))
        return view_func(*args, **kwargs)

    return wrapper


def money(value):
    return f"{float(value or 0):,.2f}"


def safe_float(val, default=0.0):
    try:
        val_clean = str(val or "").strip()
        if not val_clean:
            return default
        return float(val_clean)
    except ValueError:
        return default


app.jinja_env.filters["money"] = money


def customer_phones(row):
    phones = []
    # Index adjustments based on query select
    # In collector_web dashboard rows, phone elements are indices 11, 12, 13
    for value in row[11:14]:
        if value and str(value).strip():
            phones.append(str(value).strip())
    return phones


app.jinja_env.filters["customer_phones"] = customer_phones


def resolve_date_filter(period, date_from, date_to):
    today = date.today()
    period = (period or "today").strip().lower()
    date_from = (date_from or "").strip()
    date_to = (date_to or "").strip()

    if date_from or date_to:
        return date_from or None, date_to or None, "custom", "Custom"

    if period == "all":
        return None, None, "all", "All"
    if period == "yesterday":
        day = today - timedelta(days=1)
        return str(day), str(day), "yesterday", "Yesterday"
    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return str(start), str(today), "this_week", "This Week"
    if period == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return str(start), str(end), "last_week", "Last Week"
    if period == "this_month":
        return str(today.replace(day=1)), str(today), "this_month", "This Month"

    return str(today), str(today), "today", "Today"


@app.route("/healthz")
def healthz():
    if not database.using_postgres():
        return jsonify({"ok": False, "error": "DATABASE_URL is not configured"}), 500

    try:
        ensure_database_ready()
        conn = database.connect_db(reuse_postgres=False)
        cur = conn.cursor()
        checks = {}
        for table_name in ("collector_users", "customer_users", "collectors", "transactions"):
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            checks[table_name] = cur.fetchone()[0]
        conn.close()
    except Exception as exc:
        return jsonify({"ok": False, "error": type(exc).__name__, "detail": str(exc)}), 500

    return jsonify({"ok": True, "tables": checks})


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("collector_name"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT collector_name, password_hash
            FROM collector_users
            WHERE username=? AND status=1
            """,
            (username,),
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session.clear()
            session["username"] = username
            session["collector_name"] = user[0]
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def customer_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("customer_name"):
            return redirect(url_for("customer_login"))
        return view_func(*args, **kwargs)
    return wrapper


def banker_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("banker_name"):
            return redirect(url_for("banker_login"))
        return view_func(*args, **kwargs)
    return wrapper



@app.route("/", methods=["GET", "POST"])
@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():
    if session.get("customer_name"):
        return redirect(url_for("customer_dashboard"))


    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT customer_name, password_hash
            FROM customer_users
            WHERE username=? AND status=1
            """,
            (username,),
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session.clear()
            session["username"] = username
            session["customer_name"] = user[0]
            return redirect(url_for("customer_dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("customer_login.html")





@app.route("/customer/logout")
def customer_logout():
    session.clear()
    return redirect(url_for("customer_login"))


@app.route("/customer/dashboard")
@customer_required
def customer_dashboard():
    customer_name = session["customer_name"]
    conn = db()
    cur = conn.cursor()

    # Fetch active currencies
    cur.execute("SELECT code FROM currencies WHERE status=1 ORDER BY code")
    currencies = [dict(code=row[0]) for row in cur.fetchall()]

    # Fetch current exchange rates for active currencies (today or latest fallback)
    current_rates = {}
    for cur_obj in currencies:
        code = cur_obj["code"]
        cur.execute("SELECT rate FROM currency_rates WHERE currency_code=? AND rate_date=?", (code, str(date.today())))
        row = cur.fetchone()
        if row:
            current_rates[code] = float(row[0])
        else:
            cur.execute("SELECT rate FROM currency_rates WHERE currency_code=? ORDER BY rate_date DESC, id DESC LIMIT 1", (code,))
            row = cur.fetchone()
            current_rates[code] = float(row[0]) if row else 1.0

    # Fetch customer's pending transactions
    cur.execute(
        """
        SELECT id, deal_date, target_currency, exchange_rate, foreign_amount, eur_expected, eur_received, pending_eur, notes, status, bank_account_details, bank_account_attachment
        FROM transactions
        WHERE LOWER(customer_name)=LOWER(?) AND status='OPEN'
        ORDER BY id DESC
        """,
        (customer_name,),
    )
    pending_rows = [dict(
        id=r[0], deal_date=r[1], target_currency=r[2], exchange_rate=r[3], foreign_amount=r[4],
        eur_expected=r[5], eur_received=r[6], pending_eur=r[7], notes=r[8], status=r[9],
        bank_account_details=r[10], bank_account_attachment=r[11]
    ) for r in cur.fetchall()]

    # Fetch customer's completed transactions
    cur.execute(
        """
        SELECT id, deal_date, received_date, target_currency, exchange_rate, foreign_amount, eur_expected, eur_received, notes, status, bank_account_details, bank_account_attachment
        FROM transactions
        WHERE LOWER(customer_name)=LOWER(?) AND status='CLOSED'
        ORDER BY id DESC
        """,
        (customer_name,),
    )
    received_rows = [dict(
        id=r[0], deal_date=r[1], received_date=r[2], target_currency=r[3], exchange_rate=r[4], foreign_amount=r[5],
        eur_expected=r[6], eur_received=r[7], notes=r[8], status=r[9],
        bank_account_details=r[10], bank_account_attachment=r[11]
    ) for r in cur.fetchall()]

    # Fetch customer's saved bank accounts
    cur.execute(
        """
        SELECT id, bank_name, account_holder_name, account_number, iban, swift_code, routing_code, notes, attachment_path
        FROM customer_bank_accounts
        WHERE LOWER(customer_name)=LOWER(?) AND status=1
        ORDER BY id DESC
        """,
        (customer_name,),
    )
    bank_accounts = [dict(
        id=r[0], bank_name=r[1], account_holder_name=r[2], account_number=r[3],
        iban=r[4], swift_code=r[5], routing_code=r[6], notes=r[7], attachment_path=r[8]
    ) for r in cur.fetchall()]

    # Calculate totals
    cur.execute(
        """
        SELECT COUNT(*), SUM(eur_expected), SUM(eur_received), SUM(pending_eur)
        FROM transactions
        WHERE LOWER(customer_name)=LOWER(?)
        """,
        (customer_name,),
    )
    totals_row = cur.fetchone()
    conn.close()

    summary = {
        "count": totals_row[0] or 0,
        "expected": totals_row[1] or 0,
        "received": totals_row[2] or 0,
        "pending": totals_row[3] or 0,
    }

    return render_template(
        "customer_dashboard.html",
        customer_name=customer_name,
        currencies=currencies,
        current_rates=current_rates,
        pending_txs=pending_rows,
        received_txs=received_rows,
        summary=summary,
        bank_accounts=bank_accounts,
    )


@app.route("/customer/bank-accounts/save", methods=["POST"])
@customer_required
def customer_bank_accounts_save():
    customer_name = session["customer_name"]
    account_id = request.form.get("id", "").strip()
    bank_name = request.form.get("bank_name", "").strip()
    account_holder_name = request.form.get("account_holder_name", "").strip()
    account_number = request.form.get("account_number", "").strip()
    iban = request.form.get("iban", "").strip() or None
    swift_code = request.form.get("swift_code", "").strip() or None
    routing_code = request.form.get("routing_code", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    if not bank_name or not account_holder_name or not account_number:
        flash("Bank Name, Holder Name, and Account Number are required.", "error")
        return redirect(url_for("customer_dashboard"))

    attachment_path = request.form.get("existing_attachment", "") or None
    file = request.files.get("attachment")
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        
        # Save to database
        save_uploaded_file(file, unique_name)
        
        # Optionally save to disk (local dev fallback)
        if not is_vercel_env:
            try:
                file.seek(0)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                file.save(filepath)
            except Exception:
                pass
                
        attachment_path = f"uploads/{unique_name}"

    conn = db()
    cur = conn.cursor()
    try:
        if account_id:
            cur.execute(
                """
                UPDATE customer_bank_accounts
                SET bank_name=?, account_holder_name=?, account_number=?, iban=?, swift_code=?, routing_code=?, notes=?, attachment_path=?
                WHERE id=? AND LOWER(customer_name)=LOWER(?)
                """,
                (bank_name, account_holder_name, account_number, iban, swift_code, routing_code, notes, attachment_path, int(account_id), customer_name)
            )
            flash("Bank account updated successfully.", "success")
        else:
            cur.execute(
                """
                INSERT INTO customer_bank_accounts (customer_name, bank_name, account_holder_name, account_number, iban, swift_code, routing_code, notes, attachment_path, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (customer_name, bank_name, account_holder_name, account_number, iban, swift_code, routing_code, notes, attachment_path, str(date.today()))
            )
            flash("Bank account saved successfully.", "success")
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving bank account: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("customer_dashboard"))


@app.route("/customer/bank-accounts/<int:account_id>/delete", methods=["POST"])
@customer_required
def customer_bank_accounts_delete(account_id):
    customer_name = session["customer_name"]
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE customer_bank_accounts
            SET status=0
            WHERE id=? AND LOWER(customer_name)=LOWER(?)
            """,
            (account_id, customer_name)
        )
        conn.commit()
        database.bump_app_revision()
        flash("Bank account deleted successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting bank account: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("customer_dashboard"))


@app.route("/customer/transaction/new", methods=["POST"])
@customer_required
def customer_transaction_new():
    customer_name = session["customer_name"]
    target_currency = request.form.get("target_currency", "").strip()
    foreign_amount = safe_float(request.form.get("foreign_amount"))
    eur_expected = safe_float(request.form.get("eur_expected"))
    notes = request.form.get("notes", "").strip() or None

    if not target_currency:
        flash("Target currency is required.", "error")
        return redirect(url_for("customer_dashboard"))

    if foreign_amount <= 0 and eur_expected <= 0:
        flash("Please enter either Foreign Amount or Expected EUR.", "error")
        return redirect(url_for("customer_dashboard"))

    bank_account_choice = request.form.get("bank_account_choice", "").strip()
    bank_account_id = None
    bank_account_details = None
    bank_account_attachment = None

    conn = db()
    cur = conn.cursor()

    try:
        # 1. Determine exchange rate
        cur.execute("SELECT rate FROM currency_rates WHERE currency_code=? AND rate_date=?", (target_currency, str(date.today())))
        row = cur.fetchone()
        if row:
            exchange_rate = float(row[0])
        else:
            cur.execute("SELECT rate FROM currency_rates WHERE currency_code=? ORDER BY rate_date DESC, id DESC LIMIT 1", (target_currency,))
            row = cur.fetchone()
            exchange_rate = float(row[0]) if row else 1.0

        # Calculations
        if eur_expected <= 0 and foreign_amount > 0:
            eur_expected = foreign_amount / exchange_rate
        elif foreign_amount <= 0 and eur_expected > 0:
            foreign_amount = eur_expected * exchange_rate

        pending_eur = eur_expected
        status = "CLOSED" if pending_eur == 0 else "OPEN"

        # 2. Process Bank Details
        if bank_account_choice:
            cur.execute(
                """
                SELECT id, bank_name, account_holder_name, account_number, iban, swift_code, routing_code, notes, attachment_path
                FROM customer_bank_accounts
                WHERE id=? AND LOWER(customer_name)=LOWER(?) AND status=1
                """,
                (int(bank_account_choice), customer_name)
            )
            ac_row = cur.fetchone()
            if ac_row:
                bank_account_id = ac_row[0]
                bank_account_details = f"Bank: {ac_row[1]}\nHolder: {ac_row[2]}\nA/C: {ac_row[3]}"
                if ac_row[4]: bank_account_details += f"\nIBAN: {ac_row[4]}"
                if ac_row[5]: bank_account_details += f"\nSWIFT: {ac_row[5]}"
                if ac_row[6]: bank_account_details += f"\nRouting: {ac_row[6]}"
                if ac_row[7]: bank_account_details += f"\nNotes: {ac_row[7]}"
                bank_account_attachment = ac_row[8]
        else:
            new_bank_name = request.form.get("new_bank_name", "").strip()
            new_account_holder_name = request.form.get("new_account_holder_name", "").strip()
            new_account_number = request.form.get("new_account_number", "").strip()
            new_iban = request.form.get("new_iban", "").strip() or None
            new_swift_code = request.form.get("new_swift_code", "").strip() or None
            new_routing_code = request.form.get("new_routing_code", "").strip() or None
            new_notes = request.form.get("new_notes", "").strip() or None

            if new_bank_name and new_account_holder_name and new_account_number:
                bank_account_details = f"Bank: {new_bank_name}\nHolder: {new_account_holder_name}\nA/C: {new_account_number}"
                if new_iban: bank_account_details += f"\nIBAN: {new_iban}"
                if new_swift_code: bank_account_details += f"\nSWIFT: {new_swift_code}"
                if new_routing_code: bank_account_details += f"\nRouting: {new_routing_code}"
                if new_notes: bank_account_details += f"\nNotes: {new_notes}"

                # Handle upload
                file = request.files.get("new_attachment")
                if file and file.filename and allowed_file(file.filename):
                    ext = file.filename.rsplit(".", 1)[1].lower()
                    unique_name = f"{uuid.uuid4().hex}.{ext}"
                    
                    # Save to database
                    save_uploaded_file(file, unique_name)
                    
                    # Optionally save to disk (local dev fallback)
                    if not is_vercel_env:
                        try:
                            file.seek(0)
                            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                            file.save(filepath)
                        except Exception:
                            pass
                            
                    bank_account_attachment = f"uploads/{unique_name}"

                # Save if user checked "Save this account"
                save_for_future = request.form.get("save_for_future") == "1"
                if save_for_future:
                    cur.execute(
                        """
                        INSERT INTO customer_bank_accounts (customer_name, bank_name, account_holder_name, account_number, iban, swift_code, routing_code, notes, attachment_path, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                        """,
                        (customer_name, new_bank_name, new_account_holder_name, new_account_number, new_iban, new_swift_code, new_routing_code, new_notes, bank_account_attachment, str(date.today()))
                    )
                    conn.commit()

        # 3. Create Transaction
        cur.execute(
            """
            INSERT INTO transactions (customer_name, collector_name, banker_name, target_currency, exchange_rate, 
                                      eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, 
                                      picked_by, notes, transaction_type, received_date, bank_account_id, 
                                      bank_account_details, bank_account_attachment)
            VALUES (?, NULL, NULL, ?, ?, ?, 0.0, ?, ?, ?, ?, 'Customer Portal', ?, 'REGULAR', NULL, ?, ?, ?)
            """,
            (
                customer_name,
                target_currency,
                exchange_rate,
                eur_expected,
                pending_eur,
                foreign_amount,
                status,
                str(date.today()),
                notes,
                bank_account_id,
                bank_account_details,
                bank_account_attachment
            ),
        )
        conn.commit()
        database.bump_app_revision()
        flash("Transaction request submitted successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error submitting transaction: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("customer_dashboard"))



@app.route("/banker/login", methods=["GET", "POST"])
def banker_login():
    if session.get("banker_name"):
        return redirect(url_for("banker_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT banker_name, password_hash
            FROM banker_users
            WHERE username=? AND status=1
            """,
            (username,),
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session.clear()
            session["username"] = username
            session["banker_name"] = user[0]
            return redirect(url_for("banker_dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("banker_login.html")


@app.route("/banker/logout")
def banker_logout():
    session.clear()
    return redirect(url_for("banker_login"))


@app.route("/banker/dashboard")
@banker_required
def banker_dashboard():
    banker_name = clean_banker_name(session["banker_name"])
    conn = db()
    cur = conn.cursor()

    # Fetch banker details
    cur.execute(
        """
        SELECT phone, bank_name, city, status 
        FROM bankers 
        WHERE LOWER(TRIM(REPLACE(REPLACE(name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    banker_row = cur.fetchone()
    banker_details = {}
    if banker_row:
        banker_details = dict(phone=banker_row[0], bank_name=banker_row[1], city=banker_row[2], status=banker_row[3])

    # Fetch banker's payments
    cur.execute("""
        SELECT id, payment_date, paid_usd, total_usd_snapshot, remaining_usd_snapshot 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY payment_date DESC, id DESC
    """, ('%2520', '%20', banker_name))
    payments = [dict(
        id=r[0], payment_date=r[1], paid_usd=r[2], 
        total_usd_snapshot=r[3], remaining_usd_snapshot=r[4]
    ) for r in cur.fetchall()]

    # Fetch banker rates
    cur.execute(
        """
        SELECT currency_code, rate_date, rate 
        FROM banker_currency_rates 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY rate_date ASC
        """,
        ('%2520', '%20', banker_name),
    )
    rates_raw = cur.fetchall()
    rates_by_currency = {}
    for currency, r_date, rate in rates_raw:
        rates_by_currency.setdefault(currency, []).append((r_date, rate))

    # Fetch transactions
    cur.execute(
        """
        SELECT id, deal_date, target_currency, foreign_amount, customer_name, status, notes, 
               bank_account_details, bank_account_attachment, eur_expected, eur_received, pending_eur 
        FROM transactions 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY deal_date DESC, id DESC
        """,
        ('%2520', '%20', banker_name),
    )
    tx_rows = cur.fetchall()

    ledger_txs = []
    overall_total_usd = 0.0
    currency_totals = {}

    for tx_id, deal_date, currency, amount, customer_name, status, notes, ac_details, ac_attachment, eur_expected, eur_received, pending_eur in tx_rows:
        c_rates = rates_by_currency.get(currency, [])
        rate = get_banker_rate(c_rates, currency, deal_date)
        usd = (amount / rate) if rate else 0.0
        overall_total_usd += usd

        # Accumulate currency summary
        curr_sum = currency_totals.setdefault(currency, {"amount": 0.0, "usd": 0.0})
        curr_sum["amount"] += amount
        curr_sum["usd"] += usd

        ledger_txs.append(dict(
            id=tx_id, date=deal_date, currency=currency, amount=amount, rate=rate, usd=usd,
            customer_name=customer_name, status=status, notes=notes,
            bank_account_details=ac_details, bank_account_attachment=ac_attachment,
            eur_expected=eur_expected, eur_received=eur_received, pending_eur=pending_eur
        ))

    # Calculate overall paid USD
    cur.execute(
        """
        SELECT SUM(paid_usd) 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    overall_paid_usd = cur.fetchone()[0] or 0.0
    overall_remaining_usd = overall_total_usd - overall_paid_usd

    # Get today's banker currency rates (active rates)
    # Get active currencies assigned to banker
    cur.execute(
        """
        SELECT currency_code 
        FROM banker_currencies 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY currency_code
        """,
        ('%2520', '%20', banker_name),
    )
    assigned_currencies = [row[0] for row in cur.fetchall()]

    current_rates = {}
    for code in assigned_currencies:
        cur.execute(
            """
            SELECT rate 
            FROM banker_currency_rates 
            WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
              AND currency_code=? 
              AND rate_date=?
            """,
            ('%2520', '%20', banker_name, code, str(date.today())),
        )
        row = cur.fetchone()
        if row:
            current_rates[code] = float(row[0])
        else:
            cur.execute(
                """
                SELECT rate 
                FROM banker_currency_rates 
                WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
                  AND currency_code=? 
                ORDER BY rate_date DESC, id DESC 
                LIMIT 1
                """,
                ('%2520', '%20', banker_name, code),
            )
            row = cur.fetchone()
            current_rates[code] = float(row[0]) if row else 1.0

    conn.close()

    summary = {
        "overall_total_usd": overall_total_usd,
        "overall_paid_usd": overall_paid_usd,
        "overall_remaining_usd": overall_remaining_usd,
        "currency_totals": sorted(currency_totals.items(), key=lambda x: x[0]),
    }

    pending_txs = [tx for tx in ledger_txs if tx["status"] == "OPEN"]
    completed_txs = [tx for tx in ledger_txs if tx["status"] == "CLOSED"]

    return render_template(
        "banker_dashboard.html",
        banker_name=banker_name,
        banker_details=banker_details,
        current_rates=current_rates,
        pending_txs=pending_txs,
        completed_txs=completed_txs,
        payments=payments,
        summary=summary,
    )


@app.route("/banker/transaction/<int:transaction_id>/complete", methods=["POST"])
@banker_required
def banker_transaction_complete(transaction_id):
    banker_name = clean_banker_name(session["banker_name"])
    conn = db()
    cur = conn.cursor()
    try:
        lock_sql = ""
        if database.using_postgres():
            lock_sql = " FOR UPDATE"

        cur.execute(
            """
            SELECT eur_expected, status
            FROM transactions
            WHERE id=? AND LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) AND status='OPEN'
            """ + lock_sql,
            (transaction_id, '%2520', '%20', banker_name),
        )
        row = cur.fetchone()
        if not row:
            flash("Transaction not found or already completed.", "error")
            conn.rollback()
            return redirect(url_for("banker_dashboard"))

        eur_expected = float(row[0] or 0)
        
        # Mark as completed
        cur.execute(
            """
            UPDATE transactions
            SET status='CLOSED', eur_received=?, pending_eur=0.0, received_date=?
            WHERE id=?
            """,
            (eur_expected, str(date.today()), transaction_id),
        )
        conn.commit()
        database.bump_app_revision()
        flash("Transaction payment marked as completed successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error completing transaction: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("banker_dashboard"))



@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        is_super = False
        is_manager = False

        if username.lower() in ("admin", "super_admin", "superadmin", ""):
            if password == get_admin_password():
                is_super = True
                username = "super_admin"
        else:
            conn = db()
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT id, password_hash, status
                    FROM manager_admins
                    WHERE LOWER(username)=LOWER(?) AND status=1
                    """,
                    (username,),
                )
                row = cur.fetchone()
                if row and check_password_hash(row[1], password):
                    is_manager = True
            except Exception as exc:
                print(f"Error checking manager admin login: {exc}")
            finally:
                conn.close()

        if is_super or is_manager:
            session.clear()
            session["is_admin"] = True
            session["admin_role"] = "SUPER" if is_super else "MANAGER"
            session["admin_username"] = username
            
            # Log action
            log_admin_action("LOGIN", f"Admin login successful as {session['admin_role']}")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin username or password.", "error")

    return render_template("admin_login.html")


# ==============================================================================
# ADMIN SECTION
# ==============================================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = db()
    cur = conn.cursor()
    
    # Financial metrics
    cur.execute("SELECT COUNT(*), SUM(eur_expected), SUM(eur_received), SUM(pending_eur) FROM transactions")
    tx_summary = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) FROM transactions WHERE UPPER(status)='OPEN'")
    open_count = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM customers")
    cust_count = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM collectors")
    coll_count = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM bankers")
    bank_count = cur.fetchone()[0] or 0
    
    # Recent deals
    cur.execute("""
        SELECT deal_date, customer_name, eur_expected, eur_received, pending_eur, status, collector_name, banker_name 
        FROM transactions 
        ORDER BY id DESC LIMIT 10
    """)
    recent = [dict(
        deal_date=r[0], customer_name=r[1], eur_expected=r[2], 
        eur_received=r[3], pending_eur=r[4], status=r[5], 
        collector_name=r[6], banker_name=r[7]
    ) for r in cur.fetchall()]
    
    conn.close()
    
    stats = {
        "total_txs": tx_summary[0] or 0,
        "open_txs": open_count,
        "total_expected": tx_summary[1] or 0.0,
        "total_received": tx_summary[2] or 0.0,
        "total_pending": tx_summary[3] or 0.0,
        "total_customers": cust_count,
        "total_collectors": coll_count,
        "total_bankers": bank_count,
    }
    
    return render_template("admin_dashboard.html", active_page="dashboard", stats=stats, recent_txs=recent)


# CUSTOMERS CRUD
@app.route("/admin/customers")
@admin_required
def admin_customers():
    search = request.args.get("search", "").strip()
    conn = db()
    cur = conn.cursor()
    
    if search:
        keywords = search.lower().split()
        if keywords:
            conds = []
            params = []
            for k in keywords:
                conds.append(
                    """
                    (LOWER(name) LIKE ? OR 
                     LOWER(reference) LIKE ? OR 
                     LOWER(phone) LIKE ? OR 
                     LOWER(phone2) LIKE ? OR 
                     LOWER(phone3) LIKE ? OR 
                     LOWER(address) LIKE ? OR 
                     LOWER(country) LIKE ?)
                    """
                )
                term = f"%{k}%"
                params.extend([term, term, term, term, term, term, term])
            
            where_clause = " AND ".join(conds)
            query = f"""
                SELECT id, name, phone, phone2, phone3, address, reference, country, status, created_at 
                FROM customers 
                WHERE {where_clause}
                ORDER BY name
            """
            cur.execute(query, params)
        else:
            cur.execute("SELECT id, name, phone, phone2, phone3, address, reference, country, status, created_at FROM customers ORDER BY name")
    else:
        cur.execute("SELECT id, name, phone, phone2, phone3, address, reference, country, status, created_at FROM customers ORDER BY name")
        
    customers = [dict(
        id=r[0], name=r[1], phone=r[2], phone2=r[3], phone3=r[4],
        address=r[5], reference=r[6], country=r[7], status=r[8], created_at=r[9]
    ) for r in cur.fetchall()]

    # Fetch customer logins
    cur.execute(
        """
        SELECT id, customer_name, username, status, created_at
        FROM customer_users
        ORDER BY customer_name, username
        """
    )
    customer_users = [dict(
        id=r[0], customer_name=r[1], username=r[2], status=r[3], created_at=r[4]
    ) for r in cur.fetchall()]

    conn.close()
    
    return render_template(
        "admin_customers.html", 
        active_page="customers", 
        customers=customers, 
        customer_users=customer_users, 
        search=search
    )


@app.route("/admin/customers/save", methods=["POST"])
@admin_required
def admin_customers_save():
    cust_id = request.form.get("id", "").strip()
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip() or None
    phone2 = request.form.get("phone2", "").strip() or None
    phone3 = request.form.get("phone3", "").strip() or None
    address = request.form.get("address", "").strip() or None
    reference = request.form.get("reference", "").strip() or None
    country = request.form.get("country", "").strip() or None
    status = int(request.form.get("status", "1"))
    
    if not name:
        flash("Customer name is required.", "error")
        return redirect(url_for("admin_customers"))
        
    conn = db()
    cur = conn.cursor()
    try:
        if cust_id:
            cur.execute(
                """
                UPDATE customers 
                SET name=?, phone=?, phone2=?, phone3=?, address=?, reference=?, country=?, status=? 
                WHERE id=?
                """,
                (name, phone, phone2, phone3, address, reference, country, status, int(cust_id))
            )
            log_admin_action("UPDATE_CUSTOMER", f"Updated customer: {name} (ID: {cust_id})")
            flash("Customer updated successfully.", "success")
        else:
            cur.execute(
                """
                INSERT INTO customers (name, phone, phone2, phone3, address, reference, country, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, phone, phone2, phone3, address, reference, country, status, str(date.today()))
            )
            log_admin_action("CREATE_CUSTOMER", f"Created customer: {name}")
            flash("Customer created successfully.", "success")
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving customer: {exc}", "error")
    finally:
        conn.close()
        
    return redirect(url_for("admin_customers"))


@app.route("/admin/customers/<int:customer_id>/delete", methods=["POST"])
@admin_required
def admin_customers_delete(customer_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        conn.commit()
        database.bump_app_revision()
        log_admin_action("DELETE_CUSTOMER", f"Deleted customer profile (ID: {customer_id})")
        flash("Customer profile deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting customer: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_customers"))


@app.route("/admin/customers/create_user", methods=["POST"])
@admin_required
def admin_customers_create_user():
    creds_id = request.form.get("id", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if len(username) < 3:
        flash("Username must be at least 3 characters.", "error")
        return redirect(url_for("admin_customers"))

    if not creds_id and len(password) < 6:
        flash("Password is required and must be at least 6 characters for a new account.", "error")
        return redirect(url_for("admin_customers"))

    if creds_id and password and len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin_customers"))

    conn = db()
    cur = conn.cursor()
    try:
        if creds_id:
            if password:
                hashed = generate_password_hash(password)
                cur.execute(
                    """
                    UPDATE customer_users
                    SET customer_name=?, username=?, password_hash=?
                    WHERE id=?
                    """,
                    (customer_name, username, hashed, int(creds_id)),
                )
            else:
                cur.execute(
                    """
                    UPDATE customer_users
                    SET customer_name=?, username=?
                    WHERE id=?
                    """,
                    (customer_name, username, int(creds_id)),
                )
            log_admin_action("UPDATE_CUSTOMER_USER", f"Updated customer web credentials for {customer_name} (Username: {username})")
            flash("Customer credentials updated successfully.", "success")
        else:
            cur.execute(
                """
                INSERT INTO customer_users (customer_name, username, password_hash, status, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    customer_name,
                    username,
                    generate_password_hash(password),
                    str(date.today()),
                ),
            )
            log_admin_action("CREATE_CUSTOMER_USER", f"Created customer web login: {username} for {customer_name}")
            flash("Customer web account created successfully.", "success")
            
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving customer credentials: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_customers"))


@app.route("/admin/customers/user/<int:user_id>/status", methods=["POST"])
@admin_required
def admin_set_customer_user_status(user_id):
    status = 1 if request.form.get("status") == "1" else 0
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE customer_users SET status=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()
    database.bump_app_revision()
    flash("Customer login status updated.", "success")
    return redirect(url_for("admin_customers"))




@app.route("/admin/customers/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_customer_user(user_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM customer_users WHERE id=?", (user_id,))
        conn.commit()
        database.bump_app_revision()
        flash("Customer login credentials deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting login: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_customers"))


# COLLECTORS CRUD (on top of collector login management)
@app.route("/admin/collectors/save", methods=["POST"])
@admin_required
def admin_collectors_save():
    collector_id = request.form.get("id", "").strip()
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip() or None
    area = request.form.get("area", "").strip() or None
    status = int(request.form.get("status", "1"))
    
    if not name:
        flash("Collector name is required.", "error")
        return redirect(url_for("admin_users"))
        
    conn = db()
    cur = conn.cursor()
    try:
        if collector_id:
            cur.execute(
                "UPDATE collectors SET name=?, phone=?, area=?, status=? WHERE id=?",
                (name, phone, area, status, int(collector_id))
            )
            flash("Collector profile updated.", "success")
        else:
            cur.execute(
                "INSERT INTO collectors (name, phone, area, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, phone, area, status, str(date.today()))
            )
            flash("Collector profile created.", "success")
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving collector: {exc}", "error")
    finally:
        conn.close()
        
    return redirect(url_for("admin_users"))


@app.route("/admin/collectors/<int:collector_id>/delete", methods=["POST"])
@admin_required
def admin_collectors_delete(collector_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM collectors WHERE id=?", (collector_id,))
        conn.commit()
        database.bump_app_revision()
        flash("Collector profile deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting collector profile: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_users"))


@app.route("/admin")
@admin_required
def admin_root():
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/collectors")
@admin_required
def admin_users():
    conn = db()
    cur = conn.cursor()
    
    # Fetch collectors profiles
    cur.execute("SELECT id, name, phone, area, status FROM collectors ORDER BY name")
    collectors = [dict(id=r[0], name=r[1], phone=r[2], area=r[3], status=r[4]) for r in cur.fetchall()]
    
    # Fetch web logins
    cur.execute(
        """
        SELECT id, collector_name, username, status, created_at
        FROM collector_users
        ORDER BY collector_name, username
        """
    )
    users = cur.fetchall()
    conn.close()
    
    return render_template(
        "admin_users.html",
        active_page="collectors",
        collectors=collectors,
        users=users,
    )


@app.route("/admin/users/create", methods=["POST"])
@admin_required
def admin_create_user():
    collector_name = request.form.get("collector_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if len(username) < 3:
        flash("Username must be at least 3 characters.", "error")
        return redirect(url_for("admin_users"))

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin_users"))

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO collector_users (collector_name, username, password_hash, status, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                collector_name,
                username,
                generate_password_hash(password),
                str(date.today()),
            ),
        )
        conn.commit()
        database.bump_app_revision()
        flash("Collector web account created.", "success")
    except Exception:
        conn.rollback()
        flash("That username already exists.", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/status", methods=["POST"])
@admin_required
def admin_set_user_status(user_id):
    status = 1 if request.form.get("status") == "1" else 0
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE collector_users SET status=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()
    database.bump_app_revision()
    flash("Collector access updated.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/password", methods=["POST"])
@admin_required
def admin_reset_user_password(user_id):
    password = request.form.get("password", "")
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin_users"))

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE collector_users SET password_hash=? WHERE id=?",
        (generate_password_hash(password), user_id),
    )
    conn.commit()
    conn.close()
    database.bump_app_revision()
    flash("Password reset successfully.", "success")
    return redirect(url_for("admin_users"))


# BANKERS CRUD & LEDGER
@app.route("/admin/bankers")
@admin_required
def admin_bankers():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, bank_name, city, status FROM bankers ORDER BY name")
    bankers = [dict(id=r[0], name=r[1], phone=r[2], bank_name=r[3], city=r[4], status=r[5]) for r in cur.fetchall()]
    
    # Fetch banker logins
    cur.execute(
        """
        SELECT id, banker_name, username, status, created_at
        FROM banker_users
        ORDER BY banker_name, username
        """
    )
    banker_users = [dict(
        id=r[0], banker_name=r[1], username=r[2], status=r[3], created_at=r[4]
    ) for r in cur.fetchall()]
    conn.close()
    return render_template("admin_bankers.html", active_page="bankers", bankers=bankers, banker_users=banker_users)


@app.route("/admin/bankers/create_user", methods=["POST"])
@admin_required
def admin_bankers_create_user():
    banker_name = request.form.get("banker_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if len(username) < 3:
        flash("Username must be at least 3 characters.", "error")
        return redirect(url_for("admin_bankers"))

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin_bankers"))

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO banker_users (banker_name, username, password_hash, status, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                banker_name,
                username,
                generate_password_hash(password),
                str(date.today()),
            ),
        )
        conn.commit()
        database.bump_app_revision()
        flash("Banker web account created successfully.", "success")
    except Exception:
        conn.rollback()
        flash("That username already exists.", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_bankers"))


@app.route("/admin/bankers/user/<int:user_id>/status", methods=["POST"])
@admin_required
def admin_set_banker_user_status(user_id):
    status = 1 if request.form.get("status") == "1" else 0
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE banker_users SET status=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()
    database.bump_app_revision()
    flash("Banker login status updated.", "success")
    return redirect(url_for("admin_bankers"))


@app.route("/admin/bankers/user/<int:user_id>/password", methods=["POST"])
@admin_required
def admin_reset_banker_user_password(user_id):
    password = request.form.get("password", "")
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin_bankers"))

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE banker_users SET password_hash=? WHERE id=?",
        (generate_password_hash(password), user_id),
    )
    conn.commit()
    conn.close()
    database.bump_app_revision()
    flash("Banker password reset successfully.", "success")
    return redirect(url_for("admin_bankers"))


@app.route("/admin/bankers/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_banker_user(user_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM banker_users WHERE id=?", (user_id,))
        conn.commit()
        database.bump_app_revision()
        flash("Banker login credentials deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting login: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_bankers"))



@app.route("/admin/bankers/save", methods=["POST"])
@admin_required
def admin_bankers_save():
    banker_id = request.form.get("id", "").strip()
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip() or None
    bank_name = request.form.get("bank_name", "").strip() or None
    city = request.form.get("city", "").strip() or None
    status = int(request.form.get("status", "1"))
    
    if not name:
        flash("Banker name is required.", "error")
        return redirect(url_for("admin_bankers"))
        
    conn = db()
    cur = conn.cursor()
    try:
        if banker_id:
            cur.execute(
                "UPDATE bankers SET name=?, phone=?, bank_name=?, city=?, status=? WHERE id=?",
                (name, phone, bank_name, city, status, int(banker_id))
            )
            flash("Banker updated successfully.", "success")
        else:
            cur.execute(
                "INSERT INTO bankers (name, phone, bank_name, city, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, phone, bank_name, city, status, str(date.today()))
            )
            flash("Banker created successfully.", "success")
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving banker: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_bankers"))


@app.route("/admin/bankers/<int:banker_id>/delete", methods=["POST"])
@admin_required
def admin_bankers_delete(banker_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM bankers WHERE id=?", (banker_id,))
        conn.commit()
        database.bump_app_revision()
        flash("Banker profile deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting banker profile: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_bankers"))


# Banker details helpers
def clean_banker_name(name):
    import urllib.parse
    if not name:
        return ""
    for _ in range(3):
        if "%" in name:
            name = urllib.parse.unquote(name)
        else:
            break
    return name.strip()


def get_banker_rate(rates, currency, deal_date):
    matched_rate = None
    for r_date, r_val in rates:
        if r_date <= deal_date:
            matched_rate = r_val
        else:
            break
    if matched_rate is None and rates:
        matched_rate = rates[0][1]
    return matched_rate


def recalculate_banker_payments(cur, banker_name):
    banker_name = clean_banker_name(banker_name)
    # Fetch all payments
    cur.execute(
        """
        SELECT id, payment_date, paid_usd 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY payment_date ASC, id ASC
        """,
        ('%2520', '%20', banker_name),
    )
    payments = cur.fetchall()
    
    # Fetch all transactions
    cur.execute(
        """
        SELECT deal_date, target_currency, foreign_amount 
        FROM transactions 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY deal_date ASC
        """,
        ('%2520', '%20', banker_name),
    )
    txs = cur.fetchall()
    
    # Fetch banker rates
    cur.execute(
        """
        SELECT currency_code, rate_date, rate 
        FROM banker_currency_rates 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY rate_date ASC
        """,
        ('%2520', '%20', banker_name),
    )
    rates_raw = cur.fetchall()
    rates_by_currency = {}
    for currency, r_date, rate in rates_raw:
        rates_by_currency.setdefault(currency, []).append((r_date, rate))
        
    # Calculate cumulative USD equivalent for transactions by date
    usd_by_date = []
    for deal_date, currency, amount in txs:
        c_rates = rates_by_currency.get(currency, [])
        rate = get_banker_rate(c_rates, currency, deal_date)
        usd = (amount / rate) if rate else 0.0
        usd_by_date.append((deal_date, usd))
        
    # Recalculate snapshots
    running_paid = 0.0
    for p_id, p_date, paid in payments:
        total_usd_up_to_date = sum(usd for d_date, usd in usd_by_date if d_date <= p_date)
        running_paid += float(paid or 0.0)
        remaining = total_usd_up_to_date - running_paid
        cur.execute("UPDATE banker_payments SET total_usd_snapshot=?, remaining_usd_snapshot=? WHERE id=?", (total_usd_up_to_date, remaining, p_id))


@app.route("/admin/bankers/details/<banker_name>")
@admin_required
def admin_banker_details(banker_name):
    banker_name = clean_banker_name(banker_name)
    period = request.args.get("period", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None
    
    if period:
        resolved_from, resolved_to, period, date_label = resolve_date_filter(period, date_from, date_to)
        date_from = resolved_from
        date_to = resolved_to
        
    conn = db()
    cur = conn.cursor()
    
    # Fetch bankers list for dropdown combobox navigation
    cur.execute("SELECT name FROM bankers ORDER BY name")
    bankers_list = [dict(name=row[0]) for row in cur.fetchall()]
    
    # Fetch payments
    cur.execute("""
        SELECT id, payment_date, paid_usd, total_usd_snapshot, remaining_usd_snapshot 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY payment_date DESC, id DESC
    """, ('%2520', '%20', banker_name))
    payments = [dict(
        id=r[0], payment_date=r[1], paid_usd=r[2], 
        total_usd_snapshot=r[3], remaining_usd_snapshot=r[4]
    ) for r in cur.fetchall()]
    
    # Fetch banker rates for conversion lookup
    cur.execute(
        """
        SELECT currency_code, rate_date, rate 
        FROM banker_currency_rates 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY rate_date ASC
        """,
        ('%2520', '%20', banker_name),
    )
    rates_raw = cur.fetchall()
    rates_by_currency = {}
    for currency, r_date, rate in rates_raw:
        rates_by_currency.setdefault(currency, []).append((r_date, rate))
        
    # Fetch transactions (with date filters for display)
    tx_query = """
        SELECT deal_date, target_currency, foreign_amount 
        FROM transactions 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
    """
    tx_params = ['%2520', '%20', banker_name]
    if date_from:
        tx_query += " AND deal_date >= ?"
        tx_params.append(date_from)
    if date_to:
        tx_query += " AND deal_date <= ?"
        tx_params.append(date_to)
    tx_query += " ORDER BY deal_date DESC"
    cur.execute(tx_query, tx_params)
    tx_rows = cur.fetchall()
    
    ledger_txs = []
    filtered_total_usd = 0.0
    currency_totals = {}
    
    for deal_date, currency, amount in tx_rows:
        c_rates = rates_by_currency.get(currency, [])
        rate = get_banker_rate(c_rates, currency, deal_date)
        usd = (amount / rate) if rate else 0.0
        filtered_total_usd += usd
        
        # Accumulate currency summary
        curr_sum = currency_totals.setdefault(currency, {"amount": 0.0, "usd": 0.0})
        curr_sum["amount"] += amount
        curr_sum["usd"] += usd
        
        ledger_txs.append(dict(
            date=deal_date, currency=currency, amount=amount, rate=rate, usd=usd
        ))
        
    # Calculate overall total expected USD (ignoring filters)
    cur.execute(
        """
        SELECT deal_date, target_currency, foreign_amount 
        FROM transactions 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    all_txs = cur.fetchall()
    overall_total_usd = 0.0
    for deal_date, currency, amount in all_txs:
        c_rates = rates_by_currency.get(currency, [])
        rate = get_banker_rate(c_rates, currency, deal_date)
        overall_total_usd += (amount / rate) if rate else 0.0
        
    # Calculate overall paid USD
    cur.execute(
        """
        SELECT SUM(paid_usd) 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    overall_paid_usd = cur.fetchone()[0] or 0.0
    overall_remaining_usd = overall_total_usd - overall_paid_usd
    
    conn.close()
    
    ledger = {
        "transactions": ledger_txs,
        "payments": payments,
        "filtered_total_usd": filtered_total_usd,
        "overall_total_usd": overall_total_usd,
        "overall_paid_usd": overall_paid_usd,
        "overall_remaining_usd": overall_remaining_usd,
        "currency_totals": sorted(currency_totals.items(), key=lambda x: x[0]),
    }
    
    filters = {"date_from": date_from or "", "date_to": date_to or "", "period": period or ""}
    return render_template(
        "admin_banker_details.html", 
        active_page="bankers", 
        banker_name=banker_name, 
        ledger=ledger, 
        filters=filters, 
        bankers_list=bankers_list, 
        today=str(date.today())
    )


@app.route("/admin/bankers/details/<banker_name>/pay", methods=["POST"])
@admin_required
def admin_banker_details_pay(banker_name):
    banker_name = clean_banker_name(banker_name)
    payment_date = request.form.get("payment_date", "").strip() or str(date.today())
    paid_usd = float(request.form.get("paid_usd", "0"))
    
    if paid_usd <= 0:
        flash("Enter a valid payment amount.", "error")
        return redirect(url_for("admin_banker_details", banker_name=banker_name))
        
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO banker_payments (banker_name, paid_usd, payment_date) VALUES (?, ?, ?)",
            (banker_name, paid_usd, payment_date)
        )
        conn.commit()
        recalculate_banker_payments(cur, banker_name)
        conn.commit()
        database.bump_app_revision()
        flash("Banker payment recorded successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving banker payment: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_banker_details", banker_name=banker_name))


@app.route("/admin/bankers/details/<banker_name>/pay/<int:payment_id>/delete", methods=["POST"])
@admin_required
def admin_banker_details_delete_pay(banker_name, payment_id):
    banker_name = clean_banker_name(banker_name)
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM banker_payments WHERE id=?", (payment_id,))
        conn.commit()
        recalculate_banker_payments(cur, banker_name)
        conn.commit()
        database.bump_app_revision()
        flash("Payment entry deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting payment entry: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_banker_details", banker_name=banker_name))


@app.route("/admin/bankers/details/<banker_name>/pdf")
@admin_required
def admin_banker_details_pdf(banker_name):
    banker_name = clean_banker_name(banker_name)
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None
    period = request.args.get("period", "").strip() or None
    
    if period:
        resolved_from, resolved_to, period, date_label = resolve_date_filter(period, date_from, date_to)
        date_from = resolved_from
        date_to = resolved_to
        
    conn = db()
    cur = conn.cursor()
    
    # Fetch banker details/info
    cur.execute(
        """
        SELECT phone, bank_name, city 
        FROM bankers 
        WHERE LOWER(TRIM(REPLACE(REPLACE(name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    banker_row = cur.fetchone()
    banker_info = dict(phone=banker_row[0], bank_name=banker_row[1], city=banker_row[2]) if banker_row else {}
    
    # Fetch payments
    cur.execute("""
        SELECT payment_date, paid_usd, total_usd_snapshot, remaining_usd_snapshot 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY payment_date ASC, id ASC
    """, ('%2520', '%20', banker_name))
    payments = [dict(
        payment_date=r[0], paid_usd=r[1], 
        total_usd_snapshot=r[2], remaining_usd_snapshot=r[3]
    ) for r in cur.fetchall()]
    
    # Fetch banker rates
    cur.execute(
        """
        SELECT currency_code, rate_date, rate 
        FROM banker_currency_rates 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?)) 
        ORDER BY rate_date ASC
        """,
        ('%2520', '%20', banker_name),
    )
    rates_raw = cur.fetchall()
    rates_by_currency = {}
    for currency, r_date, rate in rates_raw:
        rates_by_currency.setdefault(currency, []).append((r_date, rate))
        
    # Fetch transactions (with date filters for display)
    tx_query = """
        SELECT deal_date, target_currency, foreign_amount 
        FROM transactions 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
    """
    tx_params = ['%2520', '%20', banker_name]
    if date_from:
        tx_query += " AND deal_date >= ?"
        tx_params.append(date_from)
    if date_to:
        tx_query += " AND deal_date <= ?"
        tx_params.append(date_to)
    tx_query += " ORDER BY deal_date ASC"
    cur.execute(tx_query, tx_params)
    tx_rows = cur.fetchall()
    
    ledger_txs = []
    filtered_total_usd = 0.0
    currency_totals = {}
    
    for deal_date, currency, amount in tx_rows:
        c_rates = rates_by_currency.get(currency, [])
        rate = get_banker_rate(c_rates, currency, deal_date)
        usd = (amount / rate) if rate else 0.0
        filtered_total_usd += usd
        
        # Accumulate currency summary
        curr_sum = currency_totals.setdefault(currency, {"amount": 0.0, "usd": 0.0})
        curr_sum["amount"] += amount
        curr_sum["usd"] += usd
        
        ledger_txs.append(dict(
            date=deal_date, currency=currency, amount=amount, rate=rate, usd=usd
        ))
        
    # Calculate overall total expected USD (ignoring filters)
    cur.execute(
        """
        SELECT deal_date, target_currency, foreign_amount 
        FROM transactions 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    all_txs = cur.fetchall()
    overall_total_usd = 0.0
    for deal_date, currency, amount in all_txs:
        c_rates = rates_by_currency.get(currency, [])
        rate = get_banker_rate(c_rates, currency, deal_date)
        overall_total_usd += (amount / rate) if rate else 0.0
        
    # Calculate overall paid USD
    cur.execute(
        """
        SELECT SUM(paid_usd) 
        FROM banker_payments 
        WHERE LOWER(TRIM(REPLACE(REPLACE(banker_name, ?, ' '), ?, ' '))) = LOWER(TRIM(?))
        """,
        ('%2520', '%20', banker_name),
    )
    overall_paid_usd = cur.fetchone()[0] or 0.0
    overall_remaining_usd = overall_total_usd - overall_paid_usd
    
    conn.close()
    
    # Generate PDF in memory buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            rightMargin=0.35 * inch, leftMargin=0.35 * inch,
                            topMargin=0.35 * inch, bottomMargin=0.35 * inch)
    story = []
    stylesheet = getSampleStyleSheet()
    
    title_style = ParagraphStyle("BankerPdfTitle", parent=stylesheet["Title"], fontSize=18, spaceAfter=4)
    subtitle_style = ParagraphStyle("BankerPdfSubtitle", parent=stylesheet["Normal"], fontSize=9, textColor=colors.HexColor("#475569"), spaceAfter=12)
    section_style = ParagraphStyle("BankerPdfSection", parent=stylesheet["Heading2"], fontSize=12, textColor=colors.HexColor("#1e293b"), spaceBefore=12, spaceAfter=6)
    
    story.append(Paragraph(f"Banker Statement: {banker_name}", title_style))
    info_text = f"Bank: {banker_info.get('bank_name') or 'N/A'} | City: {banker_info.get('city') or 'N/A'} | Phone: {banker_info.get('phone') or 'N/A'}"
    story.append(Paragraph(info_text, subtitle_style))
    
    # Summary Totals Card
    summary_data = [
        ["Overall Expected USD", "Overall Paid USD", "Overall Remaining Balance"],
        [f"${overall_total_usd:,.2f}", f"${overall_paid_usd:,.2f}", f"${overall_remaining_usd:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[2.5 * inch, 2.5 * inch, 2.5 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#10b981")),
        ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#e11d48")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.15 * inch))
    
    # Ledger Transactions section
    story.append(Paragraph("Transactions Ledger", section_style))
    tx_headers = ["Date", "Currency", "Amount Sent", "Rate", "USD Value"]
    tx_rows_data = [tx_headers]
    for tx in ledger_txs:
        tx_rows_data.append([
            tx["date"], tx["currency"], f"{tx['amount']:,.2f}", 
            f"{tx['rate']:.4f}" if tx["rate"] else "N/A", f"${tx['usd']:,.2f}"
        ])
    tx_rows_data.append(["Total USD Value", "", "", "", f"${filtered_total_usd:,.2f}"])
    
    tx_table = Table(tx_rows_data, colWidths=[1.5 * inch, 1.2 * inch, 1.8 * inch, 1.2 * inch, 1.8 * inch])
    tx_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(tx_table)
    story.append(Spacer(1, 0.15 * inch))
    
    # Payments history section
    story.append(Paragraph("Payments History", section_style))
    pay_headers = ["Date", "Paid USD", "Total USD", "Remaining"]
    pay_rows_data = [pay_headers]
    for p in payments:
        pay_rows_data.append([
            p["payment_date"], f"${p['paid_usd']:,.2f}", 
            f"${p['total_usd_snapshot']:,.2f}", f"${p['remaining_usd_snapshot']:,.2f}"
        ])
    if not payments:
        pay_rows_data.append(["No payments recorded.", "", "", ""])
        
    pay_table = Table(pay_rows_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
    pay_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8d6e63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(pay_table)
    
    doc.build(story)
    buffer.seek(0)
    
    filename = f"banker_{banker_name.lower().replace(' ', '_')}_ledger.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


# CURRENCY & RATES PANEL
@app.route("/admin/rates")
@admin_required
def admin_rates():
    conn = db()
    cur = conn.cursor()
    
    # Fetch active currencies
    cur.execute("SELECT id, name, code, status FROM currencies ORDER BY code")
    currencies = [dict(id=r[0], name=r[1], code=r[2], status=r[3]) for r in cur.fetchall()]
    
    # Fetch customer rates
    cur.execute("SELECT id, currency_code, base_currency, rate, rate_date FROM currency_rates ORDER BY rate_date DESC, id DESC")
    cust_rates = [dict(id=r[0], currency_code=r[1], base_currency=r[2], rate=r[3], rate_date=r[4]) for r in cur.fetchall()]
    
    # Fetch banker rates
    cur.execute("SELECT id, banker_name, currency_code, rate, rate_date FROM banker_currency_rates ORDER BY rate_date DESC, id DESC")
    banker_rates = [dict(id=r[0], banker_name=r[1], currency_code=r[2], rate=r[3], rate_date=r[4]) for r in cur.fetchall()]
    
    # Active Bankers list
    cur.execute("SELECT name FROM bankers WHERE status=1 ORDER BY name")
    bankers = [dict(name=r[0]) for r in cur.fetchall()]
    
    conn.close()
    
    return render_template(
        "admin_rates.html", active_page="rates", currencies=currencies, 
        customer_rates=cust_rates, banker_rates=banker_rates, bankers=bankers,
        today=str(date.today())
    )


@app.route("/admin/currencies/add", methods=["POST"])
@admin_required
def admin_currencies_add():
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    
    if not code:
        flash("Currency code is required.", "error")
        return redirect(url_for("admin_rates"))
        
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO currencies (name, code, status) VALUES (?, ?, 1)", (name or code, code))
        conn.commit()
        database.bump_app_revision()
        flash(f"Currency {code} added successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error adding currency: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_rates"))


@app.route("/admin/currencies/delete/<int:currency_id>", methods=["POST"])
@admin_required
def admin_currencies_delete(currency_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT code FROM currencies WHERE id=?", (currency_id,))
        row = cur.fetchone()
        if not row:
            flash("Currency not found.", "error")
            return redirect(url_for("admin_rates"))
        
        currency_code = row[0]
        
        # Check if the currency code is in use by transactions
        cur.execute("SELECT COUNT(*) FROM transactions WHERE target_currency=?", (currency_code,))
        if cur.fetchone()[0] > 0:
            # In use: deactivate
            cur.execute("UPDATE currencies SET status=0 WHERE id=?", (currency_id,))
            flash(f"Currency {currency_code} is in use by transactions. Deactivated it instead of deleting.", "success")
        else:
            # Not in use: delete completely
            cur.execute("DELETE FROM currencies WHERE id=?", (currency_id,))
            cur.execute("DELETE FROM currency_rates WHERE currency_code=?", (currency_code,))
            cur.execute("DELETE FROM banker_currency_rates WHERE currency_code=?", (currency_code,))
            flash(f"Currency {currency_code} deleted successfully.", "success")
            
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting currency: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_rates"))


@app.route("/admin/customer_rates/save", methods=["POST"])
@admin_required
def admin_customer_rates_save():
    code = request.form.get("currency_code", "").strip().upper()
    rate_date = request.form.get("rate_date", "").strip() or str(date.today())
    rate = float(request.form.get("rate", "0"))
    
    if not code or rate <= 0:
        flash("Select a valid currency and rate amount.", "error")
        return redirect(url_for("admin_rates"))
        
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR REPLACE INTO currency_rates (currency_code, base_currency, rate, rate_date) VALUES (?, ?, ?, ?)",
            (code, "EUR", rate, rate_date)
        )
        conn.commit()
        database.bump_app_revision()
        flash("Exchange rate updated.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error setting exchange rate: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_rates"))


@app.route("/admin/customer_rates/delete/<int:rate_id>", methods=["POST"])
@admin_required
def admin_customer_rates_delete(rate_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM currency_rates WHERE id=?", (rate_id,))
        conn.commit()
        database.bump_app_revision()
        flash("Exchange rate record deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting rate record: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_rates"))


@app.route("/admin/banker_rates/save", methods=["POST"])
@admin_required
def admin_banker_rates_save():
    banker_name = clean_banker_name(request.form.get("banker_name", ""))
    code = request.form.get("currency_code", "").strip().upper()
    rate_date = request.form.get("rate_date", "").strip() or str(date.today())
    rate = float(request.form.get("rate", "0"))
    
    if not banker_name or not code or rate <= 0:
        flash("Select valid fields.", "error")
        return redirect(url_for("admin_rates"))
        
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR REPLACE INTO banker_currency_rates (banker_name, currency_code, rate, rate_date) VALUES (?, ?, ?, ?)",
            (banker_name, code, rate, rate_date)
        )
        conn.commit()
        recalculate_banker_payments(cur, banker_name)
        conn.commit()
        database.bump_app_revision()
        flash("Banker rate recorded successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving banker rate: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_rates"))


@app.route("/admin/banker_rates/delete/<int:rate_id>", methods=["POST"])
@admin_required
def admin_banker_rates_delete(rate_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT banker_name FROM banker_currency_rates WHERE id=?", (rate_id,))
        row = cur.fetchone()
        banker_name = row[0] if row else None

        cur.execute("DELETE FROM banker_currency_rates WHERE id=?", (rate_id,))
        conn.commit()

        if banker_name:
            recalculate_banker_payments(cur, banker_name)
            conn.commit()

        database.bump_app_revision()
        flash("Banker specific rate record deleted.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting banker rate record: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_rates"))


# TRANSACTIONS MANAGEMENT
@app.route("/admin/transactions")
@admin_required
def admin_transactions():
    customer = request.args.get("customer", "").strip()
    search = request.args.get("search", "").strip()
    collector = request.args.get("collector", "").strip()
    banker = request.args.get("banker", "").strip()
    status = request.args.get("status", "ALL").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    conn = db()
    cur = conn.cursor()

    # Dropdowns caching
    cur.execute("SELECT name FROM customers WHERE status=1 ORDER BY name")
    customers = [dict(name=row[0]) for row in cur.fetchall()]

    cur.execute("SELECT name FROM collectors WHERE status=1 ORDER BY name")
    collectors = [dict(name=row[0]) for row in cur.fetchall()]

    cur.execute("SELECT code, name FROM currencies WHERE status=1 ORDER BY code")
    currencies = [dict(code=row[0], name=row[1]) for row in cur.fetchall()]

    cur.execute("SELECT name FROM bankers WHERE status=1 ORDER BY name")
    bankers = [dict(name=row[0]) for row in cur.fetchall()]

    # Today's customer currency rates lookup for autocomplete
    cur.execute("SELECT currency_code, rate FROM currency_rates WHERE rate_date=?", (str(date.today()),))
    current_rates = {row[0]: row[1] for row in cur.fetchall()}

    # Fetch Transactions Ledger
    query = """
        SELECT id, customer_name, collector_name, banker_name, target_currency, exchange_rate, 
               eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, 
               picked_by, notes, transaction_type, received_date
        FROM transactions 
        WHERE 1=1
    """
    params = []
    
    if search:
        keywords = search.lower().split()
        for k in keywords:
            query += """ AND (
                LOWER(customer_name) LIKE ? OR 
                LOWER(collector_name) LIKE ? OR 
                LOWER(banker_name) LIKE ? OR 
                LOWER(target_currency) LIKE ? OR 
                LOWER(notes) LIKE ? OR 
                LOWER(picked_by) LIKE ? OR
                LOWER(transaction_type) LIKE ? OR
                LOWER(status) LIKE ?
            )"""
            term = f"%{k}%"
            params.extend([term, term, term, term, term, term, term, term])
            
    if customer:
        keywords = customer.lower().split()
        for k in keywords:
            query += " AND LOWER(customer_name) LIKE ?"
            params.append(f"%{k}%")
        
    if collector:
        query += " AND collector_name = ?"
        params.append(collector)
    if banker:
        query += " AND banker_name = ?"
        params.append(banker)
    if status != "ALL":
        query += " AND status = ?"
        params.append(status)
    if date_from:
        query += " AND deal_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND deal_date <= ?"
        params.append(date_to)
        
    query += " ORDER BY deal_date DESC, id DESC"
    cur.execute(query, params)
    
    transactions = [dict(
        id=r[0], customer_name=r[1], collector_name=r[2], banker_name=r[3], target_currency=r[4],
        exchange_rate=r[5], eur_expected=r[6], eur_received=r[7], pending_eur=r[8], foreign_amount=r[9],
        status=r[10], deal_date=r[11], picked_by=r[12], notes=r[13], transaction_type=r[14], received_date=r[15]
    ) for r in cur.fetchall()]
    
    conn.close()

    filters = {
        "customer": customer, "search": search, "collector": collector, "banker": banker, 
        "status": status, "date_from": date_from, "date_to": date_to
    }
    
    dropdowns = {
        "customers": customers, "collectors": collectors, "currencies": currencies, "bankers": bankers
    }

    return render_template(
        "admin_transactions.html", active_page="transactions", dropdowns=dropdowns, 
        current_rates=current_rates, transactions=transactions, filters=filters, today=str(date.today())
    )


@app.route("/admin/transactions/save", methods=["POST"])
@admin_required
def admin_transactions_save():
    tx_id = request.form.get("id", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    target_currency = request.form.get("target_currency", "").strip()
    exchange_rate = safe_float(request.form.get("exchange_rate"))
    foreign_amount = safe_float(request.form.get("foreign_amount"))
    eur_expected = safe_float(request.form.get("eur_expected"))
    eur_received = safe_float(request.form.get("eur_received"))
    
    collector_name = request.form.get("collector_name", "").strip() or None
    banker_name = request.form.get("banker_name", "").strip() or None
    deal_date = request.form.get("deal_date", "").strip() or str(date.today())
    received_date = request.form.get("received_date", "").strip() or None
    transaction_type = request.form.get("transaction_type", "REGULAR")
    picked_by = request.form.get("picked_by", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    
    if not customer_name:
        flash("Customer name is required.", "error")
        return redirect(url_for("admin_transactions"))
        
    if not target_currency:
        flash("Target currency is required.", "error")
        return redirect(url_for("admin_transactions"))
        
    conn = db()
    cur = conn.cursor()
    try:
        # Default exchange rate if not specified
        if exchange_rate <= 0:
            cur.execute("SELECT rate FROM currency_rates WHERE currency_code=? AND rate_date=?", (target_currency, str(date.today())))
            row = cur.fetchone()
            if row:
                exchange_rate = float(row[0])
            else:
                cur.execute("SELECT rate FROM currency_rates WHERE currency_code=? ORDER BY rate_date DESC, id DESC LIMIT 1", (target_currency,))
                row = cur.fetchone()
                exchange_rate = float(row[0]) if row else 1.0

        # Calculate values automatically if left blank
        if eur_expected <= 0 and foreign_amount > 0:
            eur_expected = foreign_amount / exchange_rate
        elif foreign_amount <= 0 and eur_expected > 0:
            foreign_amount = eur_expected * exchange_rate

        pending_eur = max(0.0, eur_expected - eur_received)
        status = "CLOSED" if pending_eur == 0 else "OPEN"
        if status == "CLOSED" and not received_date:
            received_date = str(date.today())

        if tx_id:
            cur.execute(
                """
                UPDATE transactions 
                SET customer_name=?, collector_name=?, banker_name=?, target_currency=?, exchange_rate=?, 
                    eur_expected=?, eur_received=?, pending_eur=?, foreign_amount=?, status=?, deal_date=?, 
                    picked_by=?, notes=?, transaction_type=?, received_date=? 
                WHERE id=?
                """,
                (customer_name, collector_name, banker_name, target_currency, exchange_rate, 
                 eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, 
                 picked_by, notes, transaction_type, received_date, int(tx_id))
            )
            flash("Deal modified successfully.", "success")
        else:
            cur.execute(
                """
                INSERT INTO transactions (customer_name, collector_name, banker_name, target_currency, exchange_rate, 
                                          eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, 
                                          picked_by, notes, transaction_type, received_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (customer_name, collector_name, banker_name, target_currency, exchange_rate, 
                 eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, 
                 picked_by, notes, transaction_type, received_date)
            )
            flash("Deal created successfully.", "success")
            
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving transaction deal: {exc}", "error")
    finally:
        conn.close()
        
    return redirect(url_for("admin_transactions"))


@app.route("/admin/transactions/delete/<int:transaction_id>", methods=["POST"])
@admin_required
def admin_transactions_delete(transaction_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
        conn.commit()
        database.bump_app_revision()
        flash("Deal record deleted successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting transaction record: {exc}", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_transactions"))


# ==============================================================================
# MANAGER ADMINS CRUD
# ==============================================================================

@app.route("/admin/managers")
@admin_required
@super_admin_required
def admin_managers():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, status, created_at FROM manager_admins ORDER BY id DESC")
    managers = [dict(id=row[0], username=row[1], status=row[2], created_at=row[3]) for row in cur.fetchall()]
    conn.close()
    return render_template("admin_managers.html", managers=managers, active_page="managers")


@app.route("/admin/managers/save", methods=["POST"])
@admin_required
@super_admin_required
def admin_managers_save():
    manager_id = request.form.get("id", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    status = int(request.form.get("status", "1"))

    if not username:
        flash("Username is required.", "error")
        return redirect(url_for("admin_managers"))

    conn = db()
    cur = conn.cursor()
    try:
        if manager_id:
            # Edit existing manager
            if password:
                # Update password
                hashed = generate_password_hash(password)
                cur.execute(
                    """
                    UPDATE manager_admins
                    SET username=?, password_hash=?, status=?
                    WHERE id=?
                    """,
                    (username, hashed, status, int(manager_id)),
                )
            else:
                cur.execute(
                    """
                    UPDATE manager_admins
                    SET username=?, status=?
                    WHERE id=?
                    """,
                    (username, status, int(manager_id)),
                )
            log_admin_action("UPDATE_MANAGER", f"Updated manager: {username} (ID: {manager_id})")
            flash("Manager Admin updated successfully.", "success")
        else:
            # Create new manager
            if not password:
                flash("Password is required for new manager.", "error")
                return redirect(url_for("admin_managers"))
            hashed = generate_password_hash(password)
            cur.execute(
                """
                INSERT INTO manager_admins (username, password_hash, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, hashed, status, str(date.today())),
            )
            log_admin_action("CREATE_MANAGER", f"Created manager: {username}")
            flash("Manager Admin created successfully.", "success")
        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error saving manager admin: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_managers"))


@app.route("/admin/managers/<int:manager_id>/status", methods=["POST"])
@admin_required
@super_admin_required
def admin_managers_status(manager_id):
    status = int(request.form.get("status", "1"))
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT username FROM manager_admins WHERE id=?", (manager_id,))
        row = cur.fetchone()
        username = row[0] if row else "Unknown"

        cur.execute("UPDATE manager_admins SET status=? WHERE id=?", (status, manager_id))
        conn.commit()
        database.bump_app_revision()
        
        status_text = "enabled" if status == 1 else "disabled"
        log_admin_action("TOGGLE_MANAGER_STATUS", f"Set manager {username} status to {status_text}")
        flash(f"Manager login {status_text}.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error updating status: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_managers"))


@app.route("/admin/managers/<int:manager_id>/password", methods=["POST"])
@admin_required
@super_admin_required
def admin_managers_password(manager_id):
    password = request.form.get("password", "").strip()
    if not password:
        flash("Password cannot be empty.", "error")
        return redirect(url_for("admin_managers"))

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT username FROM manager_admins WHERE id=?", (manager_id,))
        row = cur.fetchone()
        username = row[0] if row else "Unknown"

        hashed = generate_password_hash(password)
        cur.execute("UPDATE manager_admins SET password_hash=? WHERE id=?", (hashed, manager_id))
        conn.commit()
        database.bump_app_revision()
        
        log_admin_action("RESET_MANAGER_PASSWORD", f"Reset password for manager: {username}")
        flash("Manager password reset successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error resetting password: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_managers"))


@app.route("/admin/managers/<int:manager_id>/delete", methods=["POST"])
@admin_required
@super_admin_required
def admin_managers_delete(manager_id):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT username FROM manager_admins WHERE id=?", (manager_id,))
        row = cur.fetchone()
        username = row[0] if row else "Unknown"

        cur.execute("DELETE FROM manager_admins WHERE id=?", (manager_id,))
        conn.commit()
        database.bump_app_revision()
        
        log_admin_action("DELETE_MANAGER", f"Deleted manager: {username}")
        flash("Manager credentials deleted successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error deleting credentials: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_managers"))


# ==============================================================================
# AUDIT LOGS VIEWER
# ==============================================================================

@app.route("/admin/logs")
@admin_required
@super_admin_required
def admin_logs():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, admin_username, action, details, ip_address, created_at FROM admin_logs ORDER BY id DESC LIMIT 1000")
    logs = [dict(id=row[0], username=row[1], action=row[2], details=row[3], ip_address=row[4], created_at=row[5]) for row in cur.fetchall()]
    conn.close()
    return render_template("admin_logs.html", logs=logs, active_page="logs")


# REPORTS VIEWS & EXPORTS
def get_reports_data(filters):
    conn = db()
    cur = conn.cursor()
    
    query = """
        SELECT id, deal_date, customer_name, collector_name, banker_name, target_currency, 
               foreign_amount, exchange_rate, eur_expected, eur_received, pending_eur, status, transaction_type
        FROM transactions 
        WHERE 1=1
    """
    params = []
    
    if filters.get("banker"):
        keywords = filters["banker"].lower().split()
        for k in keywords:
            query += " AND LOWER(banker_name) LIKE ?"
            params.append(f"%{k}%")
    if filters.get("customer"):
        keywords = filters["customer"].lower().split()
        for k in keywords:
            query += " AND LOWER(customer_name) LIKE ?"
            params.append(f"%{k}%")
    if filters.get("collector"):
        keywords = filters["collector"].lower().split()
        for k in keywords:
            query += " AND LOWER(collector_name) LIKE ?"
            params.append(f"%{k}%")
    if filters.get("currency"):
        query += " AND target_currency = ?"
        params.append(filters["currency"])
        
    # Status custom filter matching desktop app's _apply_payment_status_filter
    status = (filters.get("status") or "").strip().lower()
    if status and status != "all":
        if status == "open":
            query += " AND UPPER(status) = 'OPEN'"
        elif status in ("closed", "completed"):
            query += " AND UPPER(status) = 'CLOSED'"
        elif status == "pending":
            query += " AND pending_eur > 0"
        elif status == "received":
            query += " AND eur_received > 0"
        elif status == "expected":
            query += " AND eur_expected > 0"
        elif status == "partial":
            query += " AND eur_received > 0 AND pending_eur > 0"
            
    if filters.get("date_from"):
        query += " AND deal_date >= ?"
        params.append(filters["date_from"])
    if filters.get("date_to"):
        query += " AND deal_date <= ?"
        params.append(filters["date_to"])
        
    query += " ORDER BY deal_date DESC, id DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    
    data = [dict(
        id=r[0], deal_date=r[1], customer_name=r[2], collector_name=r[3], banker_name=r[4],
        target_currency=r[5], foreign_amount=r[6], exchange_rate=r[7], eur_expected=r[8],
        eur_received=r[9], pending_eur=r[10], status=r[11], transaction_type=r[12]
    ) for r in rows]
    
    conn.close()
    return data


@app.route("/admin/receiving")
@admin_required
def admin_receiving():
    customer = request.args.get("customer", "").strip()
    collector = request.args.get("collector", "").strip()
    banker = request.args.get("banker", "").strip()
    currency = request.args.get("currency", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    active_tab = request.args.get("tab", "pending").strip()

    conn = db()
    cur = conn.cursor()

    # Fetch dropdowns
    cur.execute("SELECT name FROM customers WHERE status=1 ORDER BY name")
    customers = [dict(name=row[0]) for row in cur.fetchall()]
    cur.execute("SELECT name FROM collectors WHERE status=1 ORDER BY name")
    collectors = [dict(name=row[0]) for row in cur.fetchall()]
    cur.execute("SELECT code FROM currencies WHERE status=1 ORDER BY code")
    currencies = [dict(code=row[0]) for row in cur.fetchall()]
    cur.execute("SELECT name FROM bankers WHERE status=1 ORDER BY name")
    bankers = [dict(name=row[0]) for row in cur.fetchall()]

    dropdowns = {
        "customers": customers, "collectors": collectors, "currencies": currencies, "bankers": bankers
    }

    # Base filter clauses
    filter_clause = ""
    params = []
    if customer:
        keywords = customer.lower().split()
        for k in keywords:
            filter_clause += " AND LOWER(customer_name) LIKE ?"
            params.append(f"%{k}%")
    if collector:
        filter_clause += " AND collector_name = ?"
        params.append(collector)
    if banker:
        filter_clause += " AND banker_name = ?"
        params.append(banker)
    if currency:
        filter_clause += " AND target_currency = ?"
        params.append(currency)
    if date_from:
        filter_clause += " AND deal_date >= ?"
        params.append(date_from)
    if date_to:
        filter_clause += " AND deal_date <= ?"
        params.append(date_to)

    # Fetch pending list
    pending_query = """
        SELECT id, customer_name, collector_name, banker_name, target_currency, exchange_rate, 
               eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date
        FROM transactions 
        WHERE pending_eur > 0 AND UPPER(status)='OPEN'
    """
    cur.execute(pending_query + filter_clause + " ORDER BY deal_date DESC, id DESC", params)
    pending_txs = [dict(
        id=r[0], customer_name=r[1], collector_name=r[2], banker_name=r[3], target_currency=r[4],
        exchange_rate=r[5], eur_expected=r[6], eur_received=r[7], pending_eur=r[8], foreign_amount=r[9],
        status=r[10], deal_date=r[11]
    ) for r in cur.fetchall()]

    # Fetch received list
    received_query = """
        SELECT id, customer_name, collector_name, banker_name, target_currency, exchange_rate, 
               eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, received_date
        FROM transactions 
        WHERE eur_received > 0 AND UPPER(status)='CLOSED'
    """
    cur.execute(received_query + filter_clause + " ORDER BY deal_date DESC, id DESC", params)
    received_txs = [dict(
        id=r[0], customer_name=r[1], collector_name=r[2], banker_name=r[3], target_currency=r[4],
        exchange_rate=r[5], eur_expected=r[6], eur_received=r[7], pending_eur=r[8], foreign_amount=r[9],
        status=r[10], deal_date=r[11], received_date=r[12]
    ) for r in cur.fetchall()]

    conn.close()

    # Summary totals for active list
    active_list = pending_txs if active_tab == "pending" else received_txs
    summary = {
        "expected": sum(tx["eur_expected"] for tx in active_list),
        "received": sum(tx["eur_received"] for tx in active_list),
        "pending": sum(tx["pending_eur"] for tx in active_list),
    }

    filters = {
        "customer": customer, "collector": collector, "banker": banker,
        "currency": currency, "date_from": date_from, "date_to": date_to
    }

    return render_template(
        "admin_receiving.html", active_page="receiving", active_tab=active_tab, 
        dropdowns=dropdowns, filters=filters, summary=summary,
        pending_txs=pending_txs, received_txs=received_txs, today=str(date.today())
    )


@app.route("/admin/receiving/pay/<int:transaction_id>", methods=["POST"])
@admin_required
def admin_receiving_pay(transaction_id):
    amount_text = request.form.get("amount", "").strip()
    collector_name = request.form.get("collector_name", "").strip() or None
    banker_name = request.form.get("banker_name", "").strip() or None

    redirect_args = {
        key: request.args.get(key, "").strip()
        for key in ("customer", "collector", "banker", "currency", "date_from", "date_to")
        if request.args.get(key, "").strip()
    }
    redirect_args["tab"] = "pending"

    amount = safe_float(amount_text)

    conn = db()
    cur = conn.cursor()

    try:
        lock_sql = ""
        if database.using_postgres():
            lock_sql = " FOR UPDATE"

        cur.execute(
            """
            SELECT eur_expected, eur_received
            FROM transactions
            WHERE id=? AND status='OPEN'
            """ + lock_sql,
            (transaction_id,),
        )
        row = cur.fetchone()

        if not row:
            flash("Transaction was not found or is already closed.", "error")
            conn.rollback()
            return redirect(url_for("admin_receiving", **redirect_args))

        if amount > 0:
            expected = float(row[0] or 0)
            already_received = float(row[1] or 0)
            new_received = already_received + amount

            if new_received > expected:
                flash("Receiving amount exceeds the pending amount.", "error")
                conn.rollback()
                return redirect(url_for("admin_receiving", **redirect_args))

            pending = expected - new_received
            status = "CLOSED" if pending == 0 else "OPEN"

            cur.execute(
                """
                UPDATE transactions
                SET collector_name=?, banker_name=?, eur_received=?, pending_eur=?, status=?, received_date=?, picked_by=?
                WHERE id=?
                """,
                (
                    collector_name,
                    banker_name,
                    new_received,
                    pending,
                    status,
                    str(date.today()),
                    "Admin",
                    transaction_id,
                ),
            )
            flash("Transaction updated and payment recorded successfully.", "success")
        else:
            cur.execute(
                """
                UPDATE transactions
                SET collector_name=?, banker_name=?
                WHERE id=?
                """,
                (
                    collector_name,
                    banker_name,
                    transaction_id,
                ),
            )
            flash("Transaction assignments updated successfully.", "success")

        conn.commit()
        database.bump_app_revision()
    except Exception as exc:
        conn.rollback()
        flash(f"Error updating transaction: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_receiving", **redirect_args))


@app.route("/admin/reports")
@admin_required
def admin_reports():
    banker = request.args.get("banker", "").strip()
    customer = request.args.get("customer", "").strip()
    collector = request.args.get("collector", "").strip()
    currency = request.args.get("currency", "").strip()
    status = request.args.get("status", "All").strip()
    date_from = request.args.get("date_from", "").strip() or str(date.today() - timedelta(days=30))
    date_to = request.args.get("date_to", "").strip() or str(date.today())
    active_tab = request.args.get("tab", "summary").strip()

    filters = {
        "banker": banker, "customer": customer, "collector": collector,
        "currency": currency, "status": status, "date_from": date_from, "date_to": date_to
    }

    # Fetch filters options
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM customers WHERE status=1 ORDER BY name")
    customers = [dict(name=row[0]) for row in cur.fetchall()]
    cur.execute("SELECT name FROM collectors WHERE status=1 ORDER BY name")
    collectors = [dict(name=row[0]) for row in cur.fetchall()]
    cur.execute("SELECT code FROM currencies WHERE status=1 ORDER BY code")
    currencies = [dict(code=row[0]) for row in cur.fetchall()]
    cur.execute("SELECT name FROM bankers WHERE status=1 ORDER BY name")
    bankers = [dict(name=row[0]) for row in cur.fetchall()]
    conn.close()

    dropdowns = {
        "customers": customers, "collectors": collectors, "currencies": currencies, "bankers": bankers
    }

    data = get_reports_data(filters)

    # General totals
    expected_sum = sum(tx["eur_expected"] for tx in data)
    received_sum = sum(tx["eur_received"] for tx in data)
    pending_sum = sum(tx["pending_eur"] for tx in data)

    summary = {
        "expected": expected_sum,
        "received": received_sum,
        "pending": pending_sum,
    }

    # Compile Currency volume summary
    cur_summary = {}
    for tx in data:
        curr = tx["target_currency"]
        c_tot = cur_summary.setdefault(curr, {"count": 0, "foreign_amount": 0.0, "expected": 0.0, "received": 0.0, "pending": 0.0})
        c_tot["count"] += 1
        c_tot["foreign_amount"] += tx["foreign_amount"]
        c_tot["expected"] += tx["eur_expected"]
        c_tot["received"] += tx["eur_received"]
        c_tot["pending"] += tx["pending_eur"]

    return render_template(
        "admin_reports.html", active_page="reports", dropdowns=dropdowns, 
        filters=filters, active_tab=active_tab, data=data, summary=summary, currency_summary=cur_summary
    )


@app.route("/admin/reports/pdf")
@admin_required
def admin_reports_pdf():
    # Fetch parameters same way
    filters = {
        "banker": request.args.get("banker", "").strip(),
        "customer": request.args.get("customer", "").strip(),
        "collector": request.args.get("collector", "").strip(),
        "currency": request.args.get("currency", "").strip(),
        "status": request.args.get("status", "All").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    
    active_tab = request.args.get("tab", "summary").strip()
    data = get_reports_data(filters)
    
    # Generate PDF in memory buffer
    buffer = io.BytesIO()
    
    if active_tab == "detailed":
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        story = []
        stylesheet = getSampleStyleSheet()
        
        # Add PDF header
        title_style = ParagraphStyle("TitleStyle", parent=stylesheet["Title"], fontSize=20, spaceAfter=15)
        story.append(Paragraph("Detailed Transaction Report", title_style))
        story.append(Paragraph(f"Date Range: {filters['date_from'] or 'All'} to {filters['date_to'] or 'All'}", stylesheet["Normal"]))
        story.append(Spacer(1, 0.2 * inch))
        
        table_data = [
            ["ID", "Date", "Customer", "Collector", "Banker", "Currency", "Amount", "Rate", "Expected EUR", "Received EUR", "Pending EUR", "Status"]
        ]
        for tx in data:
            table_data.append([
                str(tx["id"]), tx["deal_date"], tx["customer_name"], tx["collector_name"] or "", tx["banker_name"] or "",
                tx["target_currency"], f"{tx['foreign_amount']:,.2f}", str(tx["exchange_rate"]), 
                f"{tx['eur_expected']:,.2f}", f"{tx['eur_received']:,.2f}", f"{tx['pending_eur']:,.2f}", tx["status"]
            ])
            
        data_table = Table(
            table_data,
            colWidths=[0.4 * inch, 0.7 * inch, 1.2 * inch, 1.2 * inch, 1.0 * inch, 0.5 * inch, 0.8 * inch, 0.5 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch, 0.6 * inch]
        )
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(data_table)
    else:
        # Default to summary
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        stylesheet = getSampleStyleSheet()
        
        title_style = ParagraphStyle("TitleStyle", parent=stylesheet["Title"], fontSize=20, spaceAfter=15)
        story.append(Paragraph("Transaction Summary Report", title_style))
        story.append(Paragraph(f"Date Range: {filters['date_from'] or 'All'} to {filters['date_to'] or 'All'}", stylesheet["Normal"]))
        story.append(Spacer(1, 0.2 * inch))
        
        # Summary totals card
        total_exp = sum(tx["eur_expected"] for tx in data)
        total_rec = sum(tx["eur_received"] for tx in data)
        total_pend = sum(tx["pending_eur"] for tx in data)
        
        stats_data = [
            ["Metric", "Value"],
            ["Total Expected EUR", f"EUR {total_exp:,.2f}"],
            ["Total Received EUR", f"EUR {total_rec:,.2f}"],
            ["Total Pending EUR", f"EUR {total_pend:,.2f}"],
        ]
        stats_table = Table(stats_data, colWidths=[2.5 * inch, 2.5 * inch])
        stats_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.2 * inch))
        
        table_data = [
            ["Date", "Customer", "Banker", "Currency", "Expected EUR", "Received EUR", "Pending EUR", "Status"]
        ]
        for tx in data:
            table_data.append([
                tx["deal_date"], tx["customer_name"], tx["banker_name"] or "", tx["target_currency"],
                f"{tx['eur_expected']:,.2f}", f"{tx['eur_received']:,.2f}", f"{tx['pending_eur']:,.2f}", tx["status"]
            ])
            
        data_table = Table(table_data, colWidths=[0.9 * inch, 1.4 * inch, 1.2 * inch, 0.6 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 0.6 * inch])
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(data_table)
        
    doc.build(story)
    buffer.seek(0)
    
    filename = f"report_{active_tab}_{date.today()}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/admin/reports/csv")
@admin_required
def admin_reports_csv():
    filters = {
        "banker": request.args.get("banker", "").strip(),
        "customer": request.args.get("customer", "").strip(),
        "collector": request.args.get("collector", "").strip(),
        "currency": request.args.get("currency", "").strip(),
        "status": request.args.get("status", "All").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    
    data = get_reports_data(filters)
    
    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "ID", "Deal Date", "Customer Name", "Collector Name", "Banker Name", 
        "Target Currency", "Exchange Rate", "Expected EUR", "Received EUR", 
        "Pending EUR", "Status", "Transaction Type"
    ])
    
    # Data rows
    for tx in data:
        writer.writerow([
            tx["id"], tx["deal_date"], tx["customer_name"], tx["collector_name"] or "", tx["banker_name"] or "",
            tx["target_currency"], tx["exchange_rate"], tx["eur_expected"], tx["eur_received"],
            tx["pending_eur"], tx["status"], tx["transaction_type"]
        ])
        
    output.seek(0)
    bytes_output = io.BytesIO(output.getvalue().encode('utf-8'))
    
    filename = f"report_{date.today()}.csv"
    return send_file(bytes_output, as_attachment=True, download_name=filename, mimetype="text/csv")


# ==============================================================================
# EXISTING COLLECTOR VIEWS
# ==============================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    collector_name = session["collector_name"]
    search = request.args.get("search", "").strip()
    raw_date_from = request.args.get("date_from", "").strip()
    raw_date_to = request.args.get("date_to", "").strip()
    date_from, date_to, period, date_label = resolve_date_filter(
        request.args.get("period"),
        raw_date_from,
        raw_date_to,
    )

    pending_rows, pending_totals = get_transactions(
        collector_name=collector_name,
        status="OPEN",
        search=search,
        date_from=date_from,
        date_to=date_to,
        date_field="deal_date",
    )
    received_rows, received_totals = get_transactions(
        collector_name=collector_name,
        status="CLOSED",
        search=search,
        date_from=date_from,
        date_to=date_to,
        date_field="received_date",
    )
    summary_totals = combine_totals(pending_totals, received_totals)

    return render_template(
        "dashboard.html",
        collector_name=collector_name,
        search=search,
        period=period,
        date_from=raw_date_from,
        date_to=raw_date_to,
        date_label=date_label,
        pending_rows=pending_rows,
        pending_totals=pending_totals,
        received_rows=received_rows,
        received_totals=received_totals,
        summary_totals=summary_totals,
    )


@app.route("/receive/<int:transaction_id>", methods=["POST"])
@login_required
def receive(transaction_id):
    collector_name = session["collector_name"]
    amount_text = request.form.get("amount", "").strip()
    redirect_args = {
        key: request.form.get(key, "").strip()
        for key in ("search", "period", "date_from", "date_to")
        if request.form.get(key, "").strip()
    }

    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid received amount.", "error")
        return redirect(url_for("dashboard", **redirect_args))

    conn = db()
    cur = conn.cursor()

    try:
        lock_sql = ""
        if database.using_postgres():
            lock_sql = " FOR UPDATE"

        cur.execute(
            """
            SELECT eur_expected, eur_received
            FROM transactions
            WHERE id=? AND LOWER(collector_name)=LOWER(?) AND status='OPEN'
            """ + lock_sql,
            (transaction_id, collector_name),
        )
        row = cur.fetchone()

        if not row:
            flash("Transaction was not found or is already closed.", "error")
            conn.rollback()
            return redirect(url_for("dashboard", **redirect_args))

        expected = float(row[0] or 0)
        already_received = float(row[1] or 0)
        new_received = already_received + amount

        if new_received > expected:
            flash("Receiving amount is more than the pending amount.", "error")
            conn.rollback()
            return redirect(url_for("dashboard", **redirect_args))

        pending = expected - new_received
        status = "CLOSED" if pending == 0 else "OPEN"

        cur.execute(
            """
            UPDATE transactions
            SET eur_received=?, pending_eur=?, status=?, received_date=?
            WHERE id=? AND LOWER(collector_name)=LOWER(?)
            """,
            (
                new_received,
                pending,
                status,
                str(date.today()),
                transaction_id,
                collector_name,
            ),
        )
        conn.commit()
        database.bump_app_revision()
        flash("Payment recorded.", "success")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return redirect(url_for("dashboard", **redirect_args))


def get_transactions(
    collector_name,
    status,
    search="",
    date_from=None,
    date_to=None,
    date_field="deal_date",
    limit=None,
):
    conn = db()
    cur = conn.cursor()

    clauses = ["LOWER(t.collector_name)=LOWER(?)", "t.status=?"]
    params = [collector_name, status]

    if date_from:
        clauses.append(f"t.{date_field}>=?")
        params.append(date_from)
    if date_to:
        clauses.append(f"t.{date_field}<=?")
        params.append(date_to)

    if search:
        keywords = search.lower().split()
        for k in keywords:
            clauses.append(
                """(
                LOWER(t.customer_name) LIKE ? OR 
                LOWER(t.target_currency) LIKE ? OR 
                LOWER(COALESCE(c.phone, '')) LIKE ? OR 
                LOWER(COALESCE(c.phone2, '')) LIKE ? OR 
                LOWER(COALESCE(c.phone3, '')) LIKE ? OR
                LOWER(COALESCE(t.notes, '')) LIKE ? OR
                LOWER(COALESCE(t.banker_name, '')) LIKE ?
                )"""
            )
            term = f"%{k}%"
            params.extend([term, term, term, term, term, term, term])

    where_clause = " AND ".join(clauses)
    query = (
        "SELECT t.id, t.deal_date, t.received_date, "
        "COALESCE(t.transaction_type, 'REGULAR') AS transaction_type, "
        "t.customer_name, t.banker_name, t.target_currency, "
        "t.eur_expected, t.eur_received, t.pending_eur, t.notes, "
        "c.phone, c.phone2, c.phone3 "
        "FROM transactions t "
        "LEFT JOIN customers c ON LOWER(TRIM(c.name)) = LOWER(TRIM(t.customer_name)) "
        f"WHERE {where_clause} "
        "ORDER BY t.id DESC"
    )
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query, params)
    rows = cur.fetchall()

    totals_query = (
        "SELECT COUNT(*), SUM(t.eur_expected), SUM(t.eur_received), SUM(t.pending_eur) "
        "FROM transactions t "
        "LEFT JOIN customers c ON LOWER(TRIM(c.name)) = LOWER(TRIM(t.customer_name)) "
        f"WHERE {where_clause}"
    )
    cur.execute(totals_query, params)
    total_row = cur.fetchone()
    conn.close()

    totals = {
        "count": total_row[0] or 0,
        "expected": total_row[1] or 0,
        "received": total_row[2] or 0,
        "pending": total_row[3] or 0,
    }
    return rows, totals


def combine_totals(pending_totals, received_totals):
    return {
        "deals": pending_totals["count"] + received_totals["count"],
        "pending_deals": pending_totals["count"],
        "expected": pending_totals["expected"] + received_totals["expected"],
        "received": pending_totals["received"] + received_totals["received"],
        "pending": pending_totals["pending"] + received_totals["pending"],
    }


def get_collectors():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM collectors WHERE status=1 ORDER BY name")
    collectors = [row[0] for row in cur.fetchall()]
    conn.close()
    return collectors


def get_collector_users():
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, collector_name, username, status, created_at
        FROM collector_users
        ORDER BY collector_name, username
        """
    )
    users = cur.fetchall()
    conn.close()
    return users


if __name__ == "__main__":
    port = int(os.environ.get("COLLECTOR_WEB_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=False)
