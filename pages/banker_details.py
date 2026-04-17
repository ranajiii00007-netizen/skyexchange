import tkinter as tk
from datetime import date, timedelta
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import styles


class BankerPage:
    def __init__(self, notebook, db):
        self.db = db

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Banker Details")

        self._build_tabs()
        self._build_summary_tab()
        self._build_payments_tab()

        self.currency_totals = []
        self.current_transactions = []
        self.current_filtered_total_usd = 0.0
        self.current_filtered_paid_usd = 0.0

        self._editing_payment_widget = None
        self._payments_loaded = False
        self._banker_filter_values = []

        self._ensure_payment_snapshot_columns()
        self.refresh()
        self.tabs.bind("<<NotebookTabChanged>>", self._on_inner_tab_changed)

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self.frame)
        self.tabs.pack(fill="both", expand=True)

        self.summary_tab = ttk.Frame(self.tabs)
        self.payments_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.summary_tab, text="Summary")
        self.tabs.add(self.payments_tab, text="Payments")

    def _build_summary_tab(self):
        main_container = styles.make_scrollable(self.summary_tab)

        filter_card = styles.create_card(main_container)
        filter_card.pack(fill="x", padx=8, pady=(5, 3))

        inner = tk.Frame(filter_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Search Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg="#8d6e63",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(fill="x")

        banker_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
        banker_frame.pack(side="left", padx=(5, 15))

        tk.Label(
            banker_frame,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.banker_filter = ttk.Combobox(
            banker_frame, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.banker_filter.pack(anchor="w", pady=(2, 0))

        from_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
        from_frame.pack(side="left", padx=(5, 15))

        tk.Label(
            from_frame,
            text="From",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.date_from = tk.Entry(
            from_frame, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.date_from.pack(anchor="w", pady=(2, 0))

        to_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
        to_frame.pack(side="left", padx=(5, 10))

        tk.Label(
            to_frame,
            text="To",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.date_to = tk.Entry(
            to_frame, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.date_to.pack(anchor="w", pady=(2, 0))

        btn_row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_row.pack(fill="x", pady=(5, 0))

        styles.styled_button(btn_row, "Search", self.search_data, "Primary").pack(
            side="left", padx=3
        )
        styles.styled_button(btn_row, "Clear", self.refresh, "Secondary").pack(
            side="left", padx=3
        )
        styles.styled_button(btn_row, "PDF", self.download_summary_pdf, "Warning").pack(
            side="left", padx=3
        )

        quick_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        quick_frame.pack(fill="x", pady=(5, 0))

        tk.Label(
            quick_frame,
            text="Quick:",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 12))

        for text, cmd in [
            ("Today", self.filter_today),
            ("Yesterday", self.filter_yesterday),
            ("This Week", self.filter_week),
            ("This Month", self.filter_month),
        ]:
            styles.styled_button(quick_frame, text, cmd, "Secondary").pack(
                side="left", padx=2
            )

        summary_frame = styles.create_card(main_container)
        summary_frame.pack(fill="x", padx=8, pady=4)

        summary_inner = tk.Frame(summary_frame, bg=styles.AppStyles.COLORS["white"])
        summary_inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            summary_inner,
            text="Currency Summary",
            font=styles.AppStyles.FONTS["heading"],
            fg="#8d6e63",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        self.currency_summary_lbl = tk.Label(
            summary_inner,
            text="No summary yet. Select banker and search.",
            justify="left",
            anchor="w",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.currency_summary_lbl.pack(fill="x", pady=(0, 5))

        totals_frame = tk.Frame(summary_inner, bg=styles.AppStyles.COLORS["white"])
        totals_frame.pack(fill="x")

        self.total_usd_lbl = tk.Label(
            totals_frame,
            text="Total USD: $0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.total_usd_lbl.pack(side="left", padx=12)

        self.paid_lbl = tk.Label(
            totals_frame,
            text="Paid USD: $0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.paid_lbl.pack(side="left", padx=12)

        self.remaining_lbl = tk.Label(
            totals_frame,
            text="Remaining: $0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["danger"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.remaining_lbl.pack(side="left", padx=12)

        pay_frame = styles.create_card(main_container)
        pay_frame.pack(fill="x", padx=8, pady=4)

        pay_inner = tk.Frame(pay_frame, bg=styles.AppStyles.COLORS["white"])
        pay_inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            pay_inner,
            text="Pay Banker",
            font=styles.AppStyles.FONTS["heading"],
            fg="#8d6e63",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(pay_inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Amount USD",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 12))

        self.pay_entry = tk.Entry(
            row, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.pay_entry.pack(side="left", padx=(0, 10))

        styles.styled_button(row, "Pay", self.pay_banker, "Success").pack(side="left")

        table_card = styles.create_card(main_container)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))

        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Transactions",
            font=styles.AppStyles.FONTS["heading"],
            fg="#8d6e63",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        cols = ("date", "currency", "amount", "rate", "usd")
        scrollbar_y = ttk.Scrollbar(container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.table = ttk.Treeview(
            container,
            columns=cols,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=xscrollbar.set,
            height=16,
        )
        scrollbar_y.config(command=self.table.yview)
        xscrollbar.config(command=self.table.xview)

        style = ttk.Style()
        style.configure(
            "Treeview.Heading",
            background=styles.AppStyles.COLORS["header_bg"],
            foreground=styles.AppStyles.COLORS["text_primary"],
            font=styles.AppStyles.FONTS["body_bold"],
        )
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])

        self.table.heading("date", text="Date")
        self.table.heading("currency", text="Currency")
        self.table.heading("amount", text="Amount Sent")
        self.table.heading("rate", text="Rate")
        self.table.heading("usd", text="USD Value")

        self.table.column("date", width=120, anchor="center", minwidth=100)
        self.table.column("currency", width=110, anchor="center", minwidth=90)
        self.table.column("amount", width=180, anchor="e", minwidth=140)
        self.table.column("rate", width=140, anchor="e", minwidth=110)
        self.table.column("usd", width=180, anchor="e", minwidth=140)

        self.table.pack(fill="both", expand=True)

    def _build_payments_tab(self):
        main_container = styles.make_scrollable(self.payments_tab)

        pay_filter = styles.create_card(main_container)
        pay_filter.pack(fill="x", padx=8, pady=(5, 3))

        inner = tk.Frame(pay_filter, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Search Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg="#8d6e63",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(fill="x")

        banker_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
        banker_frame.pack(side="left", padx=(5, 15))

        tk.Label(
            banker_frame,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.pay_banker_filter = ttk.Combobox(
            banker_frame, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.pay_banker_filter.pack(anchor="w", pady=(2, 0))

        from_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
        from_frame.pack(side="left", padx=(5, 15))

        tk.Label(
            from_frame,
            text="From",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.pay_date_from = tk.Entry(
            from_frame, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.pay_date_from.pack(anchor="w", pady=(2, 0))

        to_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
        to_frame.pack(side="left", padx=(5, 15))

        tk.Label(
            to_frame,
            text="To",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.pay_date_to = tk.Entry(
            to_frame, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.pay_date_to.pack(anchor="w", pady=(2, 0))

        styles.styled_button(row, "Search", self.load_payments, "Primary").pack(
            side="left", padx=3
        )

        pay_quick = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        pay_quick.pack(fill="x", pady=(5, 0))

        tk.Label(
            pay_quick,
            text="Quick:",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 12))

        for text, cmd in [
            ("Today", self.pay_filter_today),
            ("Yesterday", self.pay_filter_yesterday),
            ("This Week", self.pay_filter_week),
            ("This Month", self.pay_filter_month),
        ]:
            styles.styled_button(pay_quick, text, cmd, "Secondary").pack(
                side="left", padx=2
            )

        pay_totals = styles.create_card(main_container)
        pay_totals.pack(fill="x", padx=8, pady=4)

        pay_totals_inner = tk.Frame(pay_totals, bg=styles.AppStyles.COLORS["white"])
        pay_totals_inner.pack(fill="x", padx=10, pady=5)

        self.pay_total_lbl = tk.Label(
            pay_totals_inner,
            text="Total USD: $0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.pay_total_lbl.pack(side="left", padx=12)

        self.pay_paid_lbl = tk.Label(
            pay_totals_inner,
            text="Total Paid: $0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.pay_paid_lbl.pack(side="left", padx=12)

        self.pay_remaining_lbl = tk.Label(
            pay_totals_inner,
            text="Remaining: $0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["danger"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.pay_remaining_lbl.pack(side="left", padx=12)

        pay_table_frame = styles.create_card(main_container)
        pay_table_frame.pack(fill="both", expand=True, padx=8, pady=(3, 5))

        container = tk.Frame(pay_table_frame, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Payments History",
            font=styles.AppStyles.FONTS["heading"],
            fg="#8d6e63",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        cols = ("payment_id", "date", "banker", "paid", "total", "remaining")
        scrollbar_y = ttk.Scrollbar(container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.pay_table = ttk.Treeview(
            container,
            columns=cols,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=xscrollbar.set,
            height=16,
        )
        scrollbar_y.config(command=self.pay_table.yview)
        xscrollbar.config(command=self.pay_table.xview)

        style = ttk.Style()
        style.configure(
            "Treeview.Heading",
            background=styles.AppStyles.COLORS["header_bg"],
            foreground=styles.AppStyles.COLORS["text_primary"],
            font=styles.AppStyles.FONTS["body_bold"],
        )
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])

        self.pay_table.heading("date", text="Date")
        self.pay_table.heading("banker", text="Banker")
        self.pay_table.heading("paid", text="Paid USD")
        self.pay_table.heading("total", text="Total USD")
        self.pay_table.heading("remaining", text="Remaining")

        self.pay_table.column("payment_id", width=0, minwidth=0, stretch=False)
        self.pay_table.column("date", width=120, anchor="center", minwidth=100)
        self.pay_table.column("banker", width=180, anchor="w", minwidth=140)
        self.pay_table.column("paid", width=150, anchor="e", minwidth=120)
        self.pay_table.column("total", width=160, anchor="e", minwidth=130)
        self.pay_table.column("remaining", width=160, anchor="e", minwidth=130)
        self.pay_table["displaycolumns"] = (
            "date",
            "banker",
            "paid",
            "total",
            "remaining",
        )

        self.pay_table.pack(fill="both", expand=True)
        self.pay_table.bind("<Double-1>", self._on_payment_double_click)

    def _ensure_payment_snapshot_columns(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(banker_payments)")
        existing = {row[1] for row in cur.fetchall()}

        changed = False
        if "total_usd_snapshot" not in existing:
            cur.execute(
                "ALTER TABLE banker_payments ADD COLUMN total_usd_snapshot REAL DEFAULT 0"
            )
            changed = True
        if "remaining_usd_snapshot" not in existing:
            cur.execute(
                "ALTER TABLE banker_payments ADD COLUMN remaining_usd_snapshot REAL DEFAULT 0"
            )
            changed = True

        if changed:
            conn.commit()
        conn.close()

    def set_dates(self, start, end):
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, start)
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, end)
        self.search_data()

    def filter_today(self):
        today = str(date.today())
        self.set_dates(today, today)

    def filter_yesterday(self):
        y = str(date.today() - timedelta(days=1))
        self.set_dates(y, y)

    def filter_week(self):
        today = date.today()
        start = today - timedelta(days=today.weekday())
        self.set_dates(str(start), str(today))

    def filter_month(self):
        today = date.today()
        start = today.replace(day=1)
        self.set_dates(str(start), str(today))

    def pay_set_dates(self, start, end):
        self.pay_date_from.delete(0, tk.END)
        self.pay_date_from.insert(0, start)
        self.pay_date_to.delete(0, tk.END)
        self.pay_date_to.insert(0, end)
        self.load_payments()

    def pay_filter_today(self):
        today = str(date.today())
        self.pay_set_dates(today, today)

    def pay_filter_yesterday(self):
        y = str(date.today() - timedelta(days=1))
        self.pay_set_dates(y, y)

    def pay_filter_week(self):
        today = date.today()
        start = today - timedelta(days=today.weekday())
        self.pay_set_dates(str(start), str(today))

    def pay_filter_month(self):
        today = date.today()
        start = today.replace(day=1)
        self.pay_set_dates(str(start), str(today))

    def _on_payment_double_click(self, event):
        region = self.pay_table.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.pay_table.identify_row(event.y)
        col_id = self.pay_table.identify_column(event.x)
        if not row_id or col_id != "#3":
            return

        if self._editing_payment_widget:
            self._editing_payment_widget.destroy()
            self._editing_payment_widget = None

        x, y, width, height = self.pay_table.bbox(row_id, col_id)
        values = self.pay_table.item(row_id, "values")
        current_text = str(values[3]).replace("$", "").replace(",", "")

        editor = ttk.Entry(self.pay_table)
        editor.place(x=x, y=y, width=width, height=height)
        editor.insert(0, current_text)
        editor.focus_set()
        editor.select_range(0, tk.END)
        self._editing_payment_widget = editor

        def commit_edit(_event=None):
            try:
                new_amount = float(editor.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid numeric amount")
                return

            payment_id = int(values[0])
            banker_name = values[2]
            self._update_payment_amount(payment_id, banker_name, new_amount)
            editor.destroy()
            self._editing_payment_widget = None

        def cancel_edit(_event=None):
            editor.destroy()
            self._editing_payment_widget = None

        editor.bind("<Return>", commit_edit)
        editor.bind("<Escape>", cancel_edit)
        editor.bind("<FocusOut>", commit_edit)

    def _update_payment_amount(self, payment_id, banker_name, new_amount):
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE banker_payments SET paid_usd=? WHERE id=?", (new_amount, payment_id)
        )
        conn.commit()
        conn.close()
        self._recalculate_payment_snapshots(banker_name)
        self._reload_all_views_after_payment_change(banker_name)

    def _recalculate_payment_snapshots(self, banker):
        conn = self.db()
        cur = conn.cursor()

        running_paid = 0.0

        cur.execute(
            "SELECT id, payment_date, paid_usd FROM banker_payments WHERE LOWER(banker_name)=LOWER(?) ORDER BY payment_date ASC, id ASC",
            (banker,),
        )
        rows = cur.fetchall()

        for payment_id, payment_date, paid in rows:
            total_usd = self._compute_overall_usd_total(banker, up_to_date=payment_date)
            running_paid += float(paid or 0.0)
            remaining = total_usd - running_paid
            cur.execute(
                "UPDATE banker_payments SET total_usd_snapshot=?, remaining_usd_snapshot=? WHERE id=?",
                (total_usd, remaining, payment_id),
            )
        conn.commit()
        conn.close()

    def _reload_all_views_after_payment_change(self, banker_name):
        self.load_payments()
        selected_summary_banker = self.banker_filter.get()
        if selected_summary_banker == banker_name:
            self.search_data()
        else:
            self.update_remaining(banker_name)

    def get_rate(self, banker, currency, deal_date=None):
        conn = self.db()
        cur = conn.cursor()

        if deal_date:
            cur.execute(
                "SELECT rate FROM banker_currency_rates WHERE LOWER(banker_name)=LOWER(?) AND currency_code=? AND rate_date<=? ORDER BY rate_date DESC, id DESC LIMIT 1",
                (banker, currency, deal_date),
            )
            row = cur.fetchone()
            if row:
                rate = row[0]
                conn.close()
                return rate

            cur.execute(
                "SELECT rate FROM banker_currency_rates WHERE LOWER(banker_name)=LOWER(?) AND currency_code=? AND rate_date>? ORDER BY rate_date ASC, id ASC LIMIT 1",
                (banker, currency, deal_date),
            )
            row = cur.fetchone()
            rate = row[0] if row else None
            conn.close()
            return rate

        cur.execute(
            "SELECT rate FROM banker_currency_rates WHERE LOWER(banker_name)=LOWER(?) AND currency_code=? ORDER BY rate_date DESC, id DESC LIMIT 1",
            (banker, currency),
        )
        row = cur.fetchone()
        rate = row[0] if row else None
        conn.close()
        return rate

    def _get_rate_cached(self, conn, cache, banker, currency, deal_date=None):
        key = (str(banker or "").lower(), currency, deal_date)
        if key in cache:
            return cache[key]

        cur = conn.cursor()
        if deal_date:
            cur.execute(
                "SELECT rate FROM banker_currency_rates WHERE LOWER(banker_name)=LOWER(?) AND currency_code=? AND rate_date<=? ORDER BY rate_date DESC, id DESC LIMIT 1",
                (banker, currency, deal_date),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "SELECT rate FROM banker_currency_rates WHERE LOWER(banker_name)=LOWER(?) AND currency_code=? AND rate_date>? ORDER BY rate_date ASC, id ASC LIMIT 1",
                    (banker, currency, deal_date),
                )
                row = cur.fetchone()
        else:
            cur.execute(
                "SELECT rate FROM banker_currency_rates WHERE LOWER(banker_name)=LOWER(?) AND currency_code=? ORDER BY rate_date DESC, id DESC LIMIT 1",
                (banker, currency),
            )
            row = cur.fetchone()

        cache[key] = row[0] if row else None
        return cache[key]

    def _load_banker_filter_values(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM bankers WHERE status=1 ORDER BY name")
        bankers = [r[0] for r in cur.fetchall()]
        conn.close()

        if bankers != self._banker_filter_values:
            self._banker_filter_values = bankers
            self.banker_filter["values"] = bankers
            self.pay_banker_filter["values"] = bankers

    def _on_inner_tab_changed(self, _event=None):
        if self.tabs.index(self.tabs.select()) == 1 and not self._payments_loaded:
            self.load_payments()

    def refresh(self):
        self._load_banker_filter_values()

        if self.banker_filter.get().strip():
            return

        self._clear_summary_view()

    def _clear_summary_view(self):

        self.table.delete(*self.table.get_children())
        self.currency_summary_lbl.config(
            text="No summary yet. Select banker and search."
        )
        self.total_usd_lbl.config(text="Total USD: $0")
        self.paid_lbl.config(text="Paid USD: $0")
        self.remaining_lbl.config(text="Remaining: $0")

        self.current_transactions = []
        self.currency_totals = []
        self.current_filtered_total_usd = 0.0
        self.current_filtered_paid_usd = 0.0

    def search_data(self):
        banker = self.banker_filter.get().strip()
        if not banker:
            messagebox.showwarning("Warning", "Select banker")
            return

        self.table.delete(*self.table.get_children())
        self.current_transactions = []
        self.currency_totals = []

        conn = self.db()
        cur = conn.cursor()
        rate_cache = {}

        query = "SELECT deal_date, target_currency, foreign_amount FROM transactions WHERE TRIM(LOWER(banker_name)) = TRIM(LOWER(?))"
        params = [banker]

        if self.date_from.get():
            query += " AND deal_date >= ?"
            params.append(self.date_from.get())
        if self.date_to.get():
            query += " AND deal_date <= ?"
            params.append(self.date_to.get())

        query += " ORDER BY deal_date DESC"
        cur.execute(query, params)

        totals_by_currency = {}
        total_usd = 0.0

        for deal_date, currency, amount in cur.fetchall():
            rate = self._get_rate_cached(conn, rate_cache, banker, currency, deal_date)
            usd = amount / rate if rate else 0.0
            total_usd += usd

            totals = totals_by_currency.setdefault(currency, {"amount": 0, "usd": 0})
            totals["amount"] += amount
            totals["usd"] += usd

            row = {
                "date": deal_date,
                "currency": currency,
                "amount": amount,
                "rate": rate,
                "usd": usd,
            }
            self.current_transactions.append(row)

            rate_value = f"{rate:,.6f}" if rate else "N/A"
            self.table.insert(
                "",
                tk.END,
                values=(
                    deal_date,
                    currency,
                    f"{amount:,.2f}",
                    rate_value,
                    f"${usd:,.2f}",
                ),
            )

        self.table.insert(
            "", tk.END, values=("", "", "", "TOTAL", f"${total_usd:,.2f}")
        )

        self.currency_totals = sorted(totals_by_currency.items(), key=lambda x: x[0])
        self._render_currency_summary()

        self.current_filtered_total_usd = total_usd
        self.total_usd_lbl.config(text=f"Total USD: ${total_usd:,.2f}")

        paid_filtered = sum(
            paid for _, paid in self._fetch_payments_for_current_filters(banker)
        )
        self.current_filtered_paid_usd = paid_filtered
        self.paid_lbl.config(text=f"Paid USD: ${paid_filtered:,.2f}")

        self.update_remaining(banker)
        conn.close()

    def _render_currency_summary(self):
        if not self.currency_totals:
            self.currency_summary_lbl.config(
                text="No transactions found for selected filters."
            )
            return

        lines = []
        for currency, totals in self.currency_totals:
            lines.append(
                f"{currency}: {totals['amount']:,.2f}  |  USD: ${totals['usd']:,.2f}"
            )
        self.currency_summary_lbl.config(text="\n".join(lines))

    def _compute_overall_usd_total(self, banker, up_to_date=None):
        conn = self.db()
        cur = conn.cursor()
        rate_cache = {}
        query = (
            "SELECT deal_date, target_currency, foreign_amount FROM transactions "
            "WHERE LOWER(banker_name)=LOWER(?)"
        )
        params = [banker]

        if up_to_date:
            query += " AND deal_date<=?"
            params.append(up_to_date)

        cur.execute(query, params)

        total_usd = 0.0
        for deal_date, currency, amount in cur.fetchall():
            rate = self._get_rate_cached(conn, rate_cache, banker, currency, deal_date)
            total_usd += (amount / rate) if rate else 0.0
        conn.close()
        return total_usd

    def _compute_filtered_usd_total(self, banker=None, date_from=None, date_to=None):
        conn = self.db()
        cur = conn.cursor()
        rate_cache = {}

        query = "SELECT deal_date, banker_name, target_currency, foreign_amount FROM transactions WHERE 1=1"
        params = []

        if banker:
            query += " AND LOWER(banker_name)=LOWER(?)"
            params.append(banker)
        if date_from:
            query += " AND deal_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND deal_date <= ?"
            params.append(date_to)

        cur.execute(query, params)

        total_usd = 0.0
        for deal_date, banker_name, currency, amount in cur.fetchall():
            rate = self._get_rate_cached(
                conn, rate_cache, banker_name, currency, deal_date
            )
            total_usd += (amount / rate) if rate else 0.0
        conn.close()
        return total_usd

    def _compute_visible_total_usd(self):
        return sum(float(tx.get("usd") or 0.0) for tx in self.current_transactions)

    def _currency_summary_totals(self):
        total_local = total_usd = 0.0
        for _, totals in self.currency_totals:
            total_local += float(totals.get("amount", 0.0) or 0.0)
            total_usd += float(totals.get("usd", 0.0) or 0.0)
        return total_local, total_usd

    def pay_banker(self):
        banker = self.banker_filter.get()
        amount_text = self.pay_entry.get().strip()

        if not banker or not amount_text:
            messagebox.showwarning("Warning", "Select banker and enter amount")
            return

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric amount")
            return

        conn = self.db()
        cur = conn.cursor()

        payment_date = str(date.today())
        total_usd_snapshot = self._compute_overall_usd_total(
            banker, up_to_date=payment_date
        )

        cur.execute(
            "SELECT SUM(paid_usd) FROM banker_payments WHERE LOWER(banker_name) = LOWER(?)",
            (banker,),
        )
        paid_before = cur.fetchone()[0] or 0.0
        remaining_snapshot = total_usd_snapshot - (paid_before + amount)

        cur.execute(
            "INSERT INTO banker_payments (banker_name, paid_usd, payment_date, total_usd_snapshot, remaining_usd_snapshot) VALUES (?,?,?,?,?)",
            (banker, amount, payment_date, total_usd_snapshot, remaining_snapshot),
        )
        conn.commit()
        conn.close()
        self._recalculate_payment_snapshots(banker)

        self.pay_entry.delete(0, tk.END)
        self.load_payments()
        self.search_data()

    def load_payments(self, recalculate=False):
        self.pay_table.delete(*self.pay_table.get_children())
        self._payments_loaded = True

        pay_banker = self.pay_banker_filter.get() or None
        pay_from = self.pay_date_from.get() or None
        pay_to = self.pay_date_to.get() or None
        summary_banker = self.banker_filter.get().strip() or None

        if recalculate:
            if pay_banker:
                self._recalculate_payment_snapshots(pay_banker)
            elif summary_banker:
                self._recalculate_payment_snapshots(summary_banker)

        conn = self.db()
        cur = conn.cursor()

        query = "SELECT id, payment_date, banker_name, paid_usd, total_usd_snapshot, remaining_usd_snapshot FROM banker_payments WHERE 1=1"
        params = []

        if pay_banker:
            query += " AND LOWER(banker_name) = LOWER(?)"
            params.append(pay_banker)
        if pay_from:
            query += " AND payment_date >= ?"
            params.append(pay_from)
        if pay_to:
            query += " AND payment_date <= ?"
            params.append(pay_to)

        query += " ORDER BY id DESC"
        cur.execute(query, params)

        total_paid = 0.0
        for (
            payment_id,
            pay_date,
            banker_name,
            paid,
            total_snapshot,
            remaining_snapshot,
        ) in cur.fetchall():
            total_paid += paid
            self.pay_table.insert(
                "",
                tk.END,
                values=(
                    payment_id,
                    pay_date,
                    banker_name,
                    f"${paid:,.2f}",
                    f"${(total_snapshot or 0):,.2f}",
                    f"${(remaining_snapshot or 0):,.2f}",
                ),
            )

        if pay_banker or pay_from or pay_to:
            filtered_total_usd = self._compute_filtered_usd_total(
                banker=pay_banker, date_from=pay_from, date_to=pay_to
            )
            self.pay_total_lbl.config(text=f"Total USD: ${filtered_total_usd:,.2f}")
        else:
            self.pay_total_lbl.config(text="Total USD: Select banker/date")
        self.pay_paid_lbl.config(text=f"Total Paid: ${total_paid:,.2f}")
        conn.close()

    def update_remaining(self, banker):
        total_usd = self._compute_overall_usd_total(banker)

        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "SELECT SUM(paid_usd) FROM banker_payments WHERE LOWER(banker_name)=LOWER(?)",
            (banker,),
        )
        paid = cur.fetchone()[0] or 0.0
        conn.close()

        remaining = total_usd - paid
        self.remaining_lbl.config(text=f"Remaining: ${remaining:,.2f}")
        self.pay_remaining_lbl.config(text=f"Remaining: ${remaining:,.2f}")

    def download_summary_pdf(self):
        banker = self.banker_filter.get()
        if not banker:
            messagebox.showwarning("Warning", "Select banker first")
            return

        self.search_data()
        if not self.current_transactions:
            messagebox.showinfo("Info", "No transactions to export")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{banker}_summary.pdf",
        )
        if not path:
            return

        payments = self._fetch_payments_for_current_filters(banker)
        totals = self._fetch_pdf_totals(banker)

        try:
            self._write_professional_pdf(path, banker, payments, totals)
            messagebox.showinfo("Success", f"PDF downloaded:\n{path}")
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to write PDF: {exc}")

    def _fetch_payments_for_current_filters(self, banker):
        conn = self.db()
        cur = conn.cursor()

        query = "SELECT payment_date, paid_usd FROM banker_payments WHERE LOWER(banker_name)=LOWER(?)"
        params = [banker]

        if self.date_from.get():
            query += " AND payment_date >= ?"
            params.append(self.date_from.get())
        if self.date_to.get():
            query += " AND payment_date <= ?"
            params.append(self.date_to.get())

        query += " ORDER BY payment_date DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return rows

    def _fetch_pdf_totals(self, banker):
        filtered_total_usd = self._compute_visible_total_usd()
        payments_filtered = self._fetch_payments_for_current_filters(banker)
        filtered_paid = sum(float(paid or 0.0) for _, paid in payments_filtered)

        overall_total_usd = self._compute_overall_usd_total(banker)

        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "SELECT SUM(paid_usd) FROM banker_payments WHERE LOWER(banker_name)=LOWER(?)",
            (banker,),
        )
        overall_paid = cur.fetchone()[0] or 0.0
        conn.close()

        return {
            "filtered_total_usd": filtered_total_usd,
            "filtered_paid": filtered_paid,
            "overall_total_usd": overall_total_usd,
            "overall_paid": overall_paid,
            "overall_remaining": overall_total_usd - overall_paid,
        }

    def _write_professional_pdf(self, path, banker, payments, totals):
        doc = SimpleDocTemplate(
            path,
            pagesize=landscape(letter),
            rightMargin=0.35 * inch,
            leftMargin=0.35 * inch,
            topMargin=0.35 * inch,
            bottomMargin=0.35 * inch,
        )
        stylesheets = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "BankerPdfTitle",
            parent=stylesheets["Title"],
            fontSize=18,
            textColor=colors.HexColor("#0f172a"),
            alignment=1,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "BankerPdfSubtitle",
            parent=stylesheets["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#334155"),
            alignment=1,
            spaceAfter=10,
        )
        section_style = ParagraphStyle(
            "BankerPdfSection",
            parent=stylesheets["Heading2"],
            fontSize=11,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=8,
            spaceAfter=6,
        )
        small_style = ParagraphStyle(
            "BankerPdfSmall",
            parent=stylesheets["Normal"],
            fontSize=7,
            leading=9,
        )
        header_style = ParagraphStyle(
            "BankerPdfHeader",
            parent=small_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=1,
        )

        def p(value, style=small_style):
            return Paragraph(escape(str(value if value is not None else "")), style)

        def money(value):
            try:
                return f"${float(value or 0):,.2f}"
            except (TypeError, ValueError):
                return str(value or "$0.00")

        def number(value, places=2):
            try:
                return f"{float(value or 0):,.{places}f}"
            except (TypeError, ValueError):
                return str(value or "0")

        def apply_table_style(table, numeric_start=None):
            commands = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8d6e63")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
            if numeric_start is not None:
                commands.append(("ALIGN", (numeric_start, 1), (-1, -1), "RIGHT"))
            table.setStyle(TableStyle(commands))

        story.append(Paragraph("SKY EXCHANGE", title_style))
        story.append(Paragraph("Banker Settlement Summary", title_style))
        story.append(
            Paragraph(
                f"Banker: {escape(str(banker))} | Date range: {self.date_from.get() or 'Any'} to {self.date_to.get() or 'Any'} | Generated: {date.today()}",
                subtitle_style,
            )
        )

        story.append(Paragraph("Summary", section_style))
        summary_data = [
            ["Filtered Total USD", money(totals["filtered_total_usd"])],
            ["Filtered Paid", money(totals["filtered_paid"])],
            ["Overall Total USD", money(totals["overall_total_usd"])],
            ["Overall Paid", money(totals["overall_paid"])],
            ["Overall Remaining", money(totals["overall_remaining"])],
        ]
        summary_table = Table(summary_data, colWidths=[2.1 * inch, 1.4 * inch], hAlign="LEFT")
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#efebe9")),
                    ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#f8fafc")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(summary_table)

        story.append(Paragraph("Local Currency Summary", section_style))
        currency_data = [[p("Currency", header_style), p("Total Local Amount", header_style), p("USD Equivalent", header_style)]]
        for currency, totals_row in self.currency_totals:
            currency_data.append(
                [
                    p(currency),
                    p(number(totals_row.get("amount"))),
                    p(money(totals_row.get("usd"))),
                ]
            )
        if len(currency_data) == 1:
            currency_data.append([p("No rows"), p("0.00"), p("$0.00")])
        currency_table = Table(currency_data, colWidths=[1.0 * inch, 1.6 * inch, 1.4 * inch], repeatRows=1)
        apply_table_style(currency_table, numeric_start=1)
        story.append(currency_table)

        story.append(Paragraph("Transactions", section_style))
        tx_data = [[p("Date", header_style), p("Currency", header_style), p("Amount", header_style), p("Rate", header_style), p("USD", header_style)]]
        for tx in self.current_transactions:
            tx_data.append(
                [
                    p(tx.get("date")),
                    p(tx.get("currency")),
                    p(number(tx.get("amount"))),
                    p(number(tx.get("rate"), 6) if tx.get("rate") else "N/A"),
                    p(money(tx.get("usd"))),
                ]
            )
        tx_table = Table(
            tx_data,
            colWidths=[0.9 * inch, 0.9 * inch, 1.2 * inch, 1.0 * inch, 1.2 * inch],
            repeatRows=1,
        )
        apply_table_style(tx_table, numeric_start=2)
        story.append(tx_table)

        story.append(Paragraph("Payments", section_style))
        payment_data = [[p("Date", header_style), p("Paid USD", header_style)]]
        for payment_date, paid_usd in payments:
            payment_data.append([p(payment_date), p(money(paid_usd))])
        if len(payment_data) == 1:
            payment_data.append([p("No payments in selected range"), p("$0.00")])
        payment_table = Table(payment_data, colWidths=[1.2 * inch, 1.3 * inch], repeatRows=1, hAlign="LEFT")
        apply_table_style(payment_table, numeric_start=1)
        story.append(payment_table)

        doc.build(story)

    @staticmethod
    def _build_graphic_pdf(path, pages_operators):
        streams = [
            "\n".join(ops).encode("latin-1", errors="replace")
            for ops in pages_operators
        ]

        n_pages = len(streams)
        objs = []

        first_page_obj = 3
        font_obj = 3 + n_pages
        first_content_obj = font_obj + 1

        kids = " ".join(f"{first_page_obj + i} 0 R" for i in range(n_pages))
        objs.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        objs.append(
            f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {n_pages} >> endobj\n".encode(
                "ascii"
            )
        )

        for i in range(n_pages):
            page_obj_num = first_page_obj + i
            content_obj_num = first_content_obj + i
            page_obj = (
                f"{page_obj_num} 0 obj << /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
                f"/Contents {content_obj_num} 0 R >> endobj\n"
            )
            objs.append(page_obj.encode("ascii"))

        objs.append(
            f"{font_obj} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n".encode(
                "ascii"
            )
        )

        for i, stream in enumerate(streams):
            content_obj_num = first_content_obj + i
            obj = (
                f"{content_obj_num} 0 obj << /Length {len(stream)} >> stream\n".encode(
                    "ascii"
                )
                + stream
                + b"\nendstream endobj\n"
            )
            objs.append(obj)

        header = b"%PDF-1.4\n"
        offsets = [0]
        assembled = bytearray(header)

        for obj in objs:
            offsets.append(len(assembled))
            assembled.extend(obj)

        xref_pos = len(assembled)
        assembled.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        assembled.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            assembled.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        assembled.extend(
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode(
                "ascii"
            )
        )

        with open(path, "wb") as file_obj:
            file_obj.write(assembled)
