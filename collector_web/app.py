import os
import sys
from datetime import date
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database  # noqa: E402


app = Flask(__name__)
app.secret_key = os.environ.get("COLLECTOR_WEB_SECRET", "change-this-secret")
ADMIN_PASSWORD = os.environ.get("COLLECTOR_ADMIN_PASSWORD", "admin123")
database.create_tables()


def db():
    return database.connect_db(reuse_postgres=False)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("collector_name"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)

    return wrapper


def money(value):
    return f"{float(value or 0):,.2f}"


app.jinja_env.filters["money"] = money


@app.route("/", methods=["GET", "POST"])
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


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin_users"))

        flash("Invalid admin password.", "error")

    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin_users():
    return render_template(
        "admin_users.html",
        collectors=get_collectors(),
        users=get_collector_users(),
    )


@app.route("/admin/users/create", methods=["POST"])
@admin_required
def admin_create_user():
    collector_name = request.form.get("collector_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if collector_name not in get_collectors():
        flash("Select a valid collector.", "error")
        return redirect(url_for("admin_users"))

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
        flash("Collector account created.", "success")
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
    flash("Password reset.", "success")
    return redirect(url_for("admin_users"))


@app.route("/dashboard")
@login_required
def dashboard():
    collector_name = session["collector_name"]
    search = request.args.get("search", "").strip()

    pending_rows, pending_totals = get_transactions(
        collector_name=collector_name,
        status="OPEN",
        search=search,
    )
    received_rows, received_totals = get_transactions(
        collector_name=collector_name,
        status="CLOSED",
        search=search,
        limit=25,
    )

    return render_template(
        "dashboard.html",
        collector_name=collector_name,
        search=search,
        pending_rows=pending_rows,
        pending_totals=pending_totals,
        received_rows=received_rows,
        received_totals=received_totals,
    )


@app.route("/receive/<int:transaction_id>", methods=["POST"])
@login_required
def receive(transaction_id):
    collector_name = session["collector_name"]
    amount_text = request.form.get("amount", "").strip()

    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid received amount.", "error")
        return redirect(url_for("dashboard"))

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
            return redirect(url_for("dashboard"))

        expected = float(row[0] or 0)
        already_received = float(row[1] or 0)
        new_received = already_received + amount

        if new_received > expected:
            flash("Receiving amount is more than the pending amount.", "error")
            conn.rollback()
            return redirect(url_for("dashboard"))

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
        flash("Payment recorded.", "success")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return redirect(url_for("dashboard"))


def get_transactions(collector_name, status, search="", limit=None):
    conn = db()
    cur = conn.cursor()

    clauses = ["LOWER(t.collector_name)=LOWER(?)", "t.status=?"]
    params = [collector_name, status]

    if search:
        clauses.append(
            "(LOWER(t.customer_name) LIKE ? OR LOWER(t.target_currency) LIKE ?)"
        )
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])

    where_clause = " AND ".join(clauses)
    query = (
        "SELECT t.id, t.deal_date, t.received_date, "
        "COALESCE(t.transaction_type, 'REGULAR') AS transaction_type, "
        "t.customer_name, t.banker_name, t.target_currency, "
        "t.eur_expected, t.eur_received, t.pending_eur, t.notes "
        "FROM transactions t "
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
