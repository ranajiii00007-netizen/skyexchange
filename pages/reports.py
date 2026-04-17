import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import date, timedelta
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import csv
import styles


class ReportsPage:
    def __init__(self, notebook, db):
        self.db = db
        self._customer_overlays = {}
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Reports")

        self._build_tabs()
        self._build_summary_tab()
        self._build_detailed_tab()
        self._build_currency_tab()

        self.current_filters = {}
        self.current_data = []
        self.current_detailed_data = []
        self.refresh()

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self.frame)
        self.tabs.pack(fill="both", expand=True)
        self.summary_tab = ttk.Frame(self.tabs)
        self.detailed_tab = ttk.Frame(self.tabs)
        self.currency_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.summary_tab, text="Summary Report")
        self.tabs.add(self.detailed_tab, text="Detailed Report")
        self.tabs.add(self.currency_tab, text="Currency Report")

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
            fg="#d32f2f",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row1 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row1.pack(fill="x", pady=3)
        tk.Label(
            row1,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.banker_filter = ttk.Combobox(
            row1, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.banker_filter.pack(side="left", padx=(0, 8))
        tk.Label(
            row1,
            text="Customer",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.customer_filter = ttk.Combobox(
            row1, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.customer_filter.pack(side="left", padx=(0, 8))
        tk.Label(
            row1,
            text="Collector",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.collector_filter = ttk.Combobox(
            row1, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.collector_filter.pack(side="left")

        row2 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x", pady=(4, 0))
        tk.Label(
            row2,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.currency_filter = ttk.Combobox(
            row2, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.currency_filter.pack(side="left", padx=(0, 8))
        tk.Label(
            row2,
            text="Status",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.status_filter = ttk.Combobox(
            row2,
            state="readonly",
            width=22,
            font=styles.AppStyles.FONTS["body"],
            values=[
                "All",
                "Open",
                "Closed",
                "Pending",
                "Received",
                "Expected",
                "Partial",
            ],
        )
        self.status_filter.set("All")
        self.status_filter.pack(side="left", padx=(0, 8))
        tk.Label(
            row2,
            text="From",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.date_from = tk.Entry(
            row2, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.date_from.pack(side="left", padx=(0, 8))
        self.date_from.insert(0, str(date.today() - timedelta(days=30)))
        tk.Label(
            row2,
            text="To",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.date_to = tk.Entry(
            row2, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.date_to.pack(side="left", padx=(0, 8))
        self.date_to.insert(0, str(date.today()))

        button_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        button_frame.pack(fill="x", pady=(5, 0))
        styles.styled_button(
            button_frame, "Search", self.search_summary, "Primary"
        ).pack(side="left", padx=3)
        styles.styled_button(
            button_frame, "Clear", self.clear_filters, "Secondary"
        ).pack(side="left", padx=3)
        styles.styled_button(
            button_frame, "PDF", self.download_summary_pdf, "Warning"
        ).pack(side="left", padx=3)
        styles.styled_button(
            button_frame, "Excel", self.download_excel, "Success"
        ).pack(side="left", padx=3)

        quick_card = styles.create_card(main_container)
        quick_card.pack(fill="x", padx=8, pady=4)
        quick_inner = tk.Frame(quick_card, bg=styles.AppStyles.COLORS["white"])
        quick_inner.pack(fill="x", padx=10, pady=5)
        tk.Label(
            quick_inner,
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
            ("90 Days", self.filter_90_days),
        ]:
            styles.styled_button(quick_inner, text, cmd, "Secondary").pack(
                side="left", padx=2
            )

        stats_card = styles.create_card(main_container)
        stats_card.pack(fill="x", padx=8, pady=4)
        stats_inner = tk.Frame(stats_card, bg=styles.AppStyles.COLORS["white"])
        stats_inner.pack(fill="x", padx=10, pady=5)
        tk.Label(
            stats_inner,
            text="Summary Statistics",
            font=styles.AppStyles.FONTS["heading"],
            fg="#d32f2f",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(0, 14))
        self.total_transactions_label = tk.Label(
            stats_inner,
            text="Total Transactions: 0",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["text_primary"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.total_transactions_label.pack(side="left", padx=12)
        self.total_expected_label = tk.Label(
            stats_inner,
            text="Total Expected (EUR): €0.00",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.total_expected_label.pack(side="left", padx=12)
        self.total_received_label = tk.Label(
            stats_inner,
            text="Total Received (EUR): €0.00",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.total_received_label.pack(side="left", padx=12)
        self.total_pending_label = tk.Label(
            stats_inner,
            text="Total Pending (EUR): €0.00",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["danger"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.total_pending_label.pack(side="left", padx=12)

        tree_card = styles.create_card(main_container)
        tree_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        tree_inner = tk.Frame(tree_card, bg=styles.AppStyles.COLORS["white"])
        tree_inner.pack(fill="both", expand=True, padx=8, pady=8)

        scrollbar_y = ttk.Scrollbar(tree_inner, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(tree_inner, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")
        self._init_customer_overlay("summary")

        self.summary_tree = ttk.Treeview(
            tree_inner,
            columns=(
                "Date",
                "Customer",
                "Banker",
                "Currency",
                "Expected EUR",
                "Received EUR",
                "Pending EUR",
                "Status",
            ),
            height=16,
            show="headings",
            yscrollcommand=lambda first, last: self._sync_customer_y_scroll(
                "summary", scrollbar_y, first, last
            ),
            xscrollcommand=lambda first, last: self._sync_customer_x_scroll(
                "summary", xscrollbar, first, last
            ),
        )
        scrollbar_y.config(
            command=lambda *args: self._customer_table_yview("summary", *args)
        )
        xscrollbar.config(
            command=lambda *args: self._customer_table_xview("summary", *args)
        )
        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])
        style.configure("Treeview.Heading", font=styles.AppStyles.FONTS["body_bold"])
        for col, width in [
            ("Date", 110),
            ("Customer", 160),
            ("Banker", 150),
            ("Currency", 100),
            ("Expected EUR", 130),
            ("Received EUR", 130),
            ("Pending EUR", 130),
            ("Status", 90),
        ]:
            anchor = (
                "center"
                if col in ("Date", "Currency", "Status")
                else ("e" if "EUR" in col else "w")
            )
            self.summary_tree.column(col, width=width, anchor=anchor, minwidth=width)
            self.summary_tree.heading(col, text=col)
        self.summary_tree.pack(side="left", fill="both", expand=True)
        self.summary_tree.bind(
            "<Configure>", lambda _event: self._schedule_customer_cell_highlight("summary")
        )
        self.summary_tree.bind(
            "<ButtonRelease-1>",
            lambda _event: self._schedule_customer_cell_highlight("summary"),
        )
        self.summary_tree.bind(
            "<MouseWheel>", lambda _event: self._schedule_customer_cell_highlight("summary")
        )

    def _build_detailed_tab(self):
        main_container = styles.make_scrollable(self.detailed_tab)

        filter_card = styles.create_card(main_container)
        filter_card.pack(fill="x", padx=8, pady=(5, 3))
        inner = tk.Frame(filter_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)
        tk.Label(
            inner,
            text="Advanced Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg="#d32f2f",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row1 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row1.pack(fill="x")
        tk.Label(
            row1,
            text="From Date",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.det_date_from = tk.Entry(
            row1, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.det_date_from.pack(side="left", padx=(0, 8))
        self.det_date_from.insert(0, str(date.today() - timedelta(days=30)))
        tk.Label(
            row1,
            text="To Date",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.det_date_to = tk.Entry(
            row1, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.det_date_to.pack(side="left", padx=(0, 8))
        self.det_date_to.insert(0, str(date.today()))
        tk.Label(
            row1,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.det_banker_filter = ttk.Combobox(
            row1, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.det_banker_filter.pack(side="left")

        row2 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x", pady=(4, 0))
        tk.Label(
            row2,
            text="Customer",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.det_customer_filter = ttk.Combobox(
            row2, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.det_customer_filter.pack(side="left", padx=(0, 8))
        tk.Label(
            row2,
            text="Collector",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.det_collector_filter = ttk.Combobox(
            row2, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.det_collector_filter.pack(side="left", padx=(0, 8))
        tk.Label(
            row2,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.det_currency_filter = ttk.Combobox(
            row2, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.det_currency_filter.pack(side="left")

        btn_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_frame.pack(fill="x", pady=(5, 0))
        styles.styled_button(btn_frame, "Apply", self.search_detailed, "Primary").pack(
            side="left", padx=3
        )
        styles.styled_button(
            btn_frame, "Reset", self.clear_detailed_filters, "Secondary"
        ).pack(side="left", padx=3)
        styles.styled_button(
            btn_frame, "Export PDF", self.download_detailed_pdf, "Warning"
        ).pack(side="left", padx=3)

        tree_card = styles.create_card(main_container)
        tree_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        tree_inner = tk.Frame(tree_card, bg=styles.AppStyles.COLORS["white"])
        tree_inner.pack(fill="both", expand=True, padx=8, pady=8)

        scrollbar_y = ttk.Scrollbar(tree_inner, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(tree_inner, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")
        self._init_customer_overlay("detailed")

        self.detailed_tree = ttk.Treeview(
            tree_inner,
            columns=(
                "ID",
                "Date",
                "Customer",
                "Collector",
                "Banker",
                "Currency",
                "Amount",
                "Rate",
                "Expected EUR",
                "Received EUR",
                "Pending EUR",
                "Status",
            ),
            height=16,
            show="headings",
            yscrollcommand=lambda first, last: self._sync_customer_y_scroll(
                "detailed", scrollbar_y, first, last
            ),
            xscrollcommand=lambda first, last: self._sync_customer_x_scroll(
                "detailed", xscrollbar, first, last
            ),
        )
        scrollbar_y.config(
            command=lambda *args: self._customer_table_yview("detailed", *args)
        )
        xscrollbar.config(
            command=lambda *args: self._customer_table_xview("detailed", *args)
        )
        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])
        style.configure("Treeview.Heading", font=styles.AppStyles.FONTS["body_bold"])
        for col, width in [
            ("ID", 60),
            ("Date", 110),
            ("Customer", 150),
            ("Collector", 140),
            ("Banker", 140),
            ("Currency", 100),
            ("Amount", 120),
            ("Rate", 100),
            ("Expected EUR", 130),
            ("Received EUR", 130),
            ("Pending EUR", 130),
            ("Status", 90),
        ]:
            anchor = (
                "center"
                if col in ("ID", "Date", "Currency", "Rate", "Status")
                else ("e" if "EUR" in col or col == "Amount" else "w")
            )
            self.detailed_tree.column(col, width=width, anchor=anchor, minwidth=width)
            self.detailed_tree.heading(col, text=col)
        self.detailed_tree.pack(side="left", fill="both", expand=True)
        self.detailed_tree.bind(
            "<Configure>", lambda _event: self._schedule_customer_cell_highlight("detailed")
        )
        self.detailed_tree.bind(
            "<ButtonRelease-1>",
            lambda _event: self._schedule_customer_cell_highlight("detailed"),
        )
        self.detailed_tree.bind(
            "<MouseWheel>", lambda _event: self._schedule_customer_cell_highlight("detailed")
        )

    def _build_currency_tab(self):
        main_container = styles.make_scrollable(self.currency_tab)

        filter_card = styles.create_card(main_container)
        filter_card.pack(fill="x", padx=8, pady=(5, 3))
        inner = tk.Frame(filter_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)
        tk.Label(
            inner,
            text="Currency Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg="#d32f2f",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(fill="x")
        tk.Label(
            row,
            text="From Date",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.cur_date_from = tk.Entry(
            row, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.cur_date_from.pack(side="left", padx=(0, 8))
        self.cur_date_from.insert(0, str(date.today() - timedelta(days=30)))
        tk.Label(
            row,
            text="To Date",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.cur_date_to = tk.Entry(
            row, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.cur_date_to.pack(side="left", padx=(0, 8))
        self.cur_date_to.insert(0, str(date.today()))
        tk.Label(
            row,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.cur_currency_filter = ttk.Combobox(
            row, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.cur_currency_filter.pack(side="left")

        btn_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_frame.pack(fill="x", pady=(5, 0))
        styles.styled_button(
            btn_frame, "Analyze", self.search_currency, "Primary"
        ).pack(side="left", padx=3)
        styles.styled_button(
            btn_frame, "Clear", self.clear_currency_filters, "Secondary"
        ).pack(side="left", padx=3)
        styles.styled_button(
            btn_frame, "Export PDF", self.download_currency_pdf, "Warning"
        ).pack(side="left", padx=3)

        tree_card = styles.create_card(main_container)
        tree_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        tree_inner = tk.Frame(tree_card, bg=styles.AppStyles.COLORS["white"])
        tree_inner.pack(fill="both", expand=True, padx=8, pady=8)

        scrollbar_y = ttk.Scrollbar(tree_inner, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(tree_inner, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.currency_tree = ttk.Treeview(
            tree_inner,
            columns=(
                "Currency",
                "Count",
                "Total Amount",
                "Avg Rate",
                "Total Expected EUR",
                "Total Received EUR",
                "Total Pending EUR",
            ),
            height=16,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=xscrollbar.set,
        )
        scrollbar_y.config(command=self.currency_tree.yview)
        xscrollbar.config(command=self.currency_tree.xview)
        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])
        style.configure("Treeview.Heading", font=styles.AppStyles.FONTS["body_bold"])
        for col, width in [
            ("Currency", 110),
            ("Count", 80),
            ("Total Amount", 150),
            ("Avg Rate", 120),
            ("Total Expected EUR", 160),
            ("Total Received EUR", 160),
            ("Total Pending EUR", 160),
        ]:
            anchor = "center" if col in ("Currency", "Count", "Avg Rate") else "e"
            self.currency_tree.column(col, width=width, anchor=anchor, minwidth=width)
            self.currency_tree.heading(col, text=col)
        self.currency_tree.pack(side="left", fill="both", expand=True)

    def load_dropdown_values(self):
        try:
            conn = self.db()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT name FROM bankers ORDER BY name")
            bankers = [row[0] for row in cur.fetchall()]
            for combo in [self.banker_filter, self.det_banker_filter]:
                combo["values"] = ["All"] + bankers
            cur.execute("SELECT DISTINCT name FROM customers ORDER BY name")
            customers = [row[0] for row in cur.fetchall()]
            for combo in [self.customer_filter, self.det_customer_filter]:
                combo["values"] = ["All"] + customers
            cur.execute("SELECT DISTINCT name FROM collectors ORDER BY name")
            collectors = [row[0] for row in cur.fetchall()]
            for combo in [self.collector_filter, self.det_collector_filter]:
                combo["values"] = ["All"] + collectors
            cur.execute("SELECT DISTINCT code FROM currencies ORDER BY code")
            currencies = [row[0] for row in cur.fetchall()]
            for combo in [
                self.currency_filter,
                self.det_currency_filter,
                self.cur_currency_filter,
            ]:
                combo["values"] = ["All"] + currencies
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dropdown values: {e}")

    def _init_customer_overlay(self, table_key):
        self._customer_overlays[table_key] = {
            "names": {},
            "labels": {},
            "job": None,
        }

    def _get_customer_table(self, table_key):
        return self.summary_tree if table_key == "summary" else self.detailed_tree

    def _sync_customer_y_scroll(self, table_key, scrollbar, first, last):
        scrollbar.set(first, last)
        self._schedule_customer_cell_highlight(table_key)

    def _sync_customer_x_scroll(self, table_key, scrollbar, first, last):
        scrollbar.set(first, last)
        self._schedule_customer_cell_highlight(table_key)

    def _customer_table_yview(self, table_key, *args):
        table = self._get_customer_table(table_key)
        table.yview(*args)
        self._schedule_customer_cell_highlight(table_key)

    def _customer_table_xview(self, table_key, *args):
        table = self._get_customer_table(table_key)
        table.xview(*args)
        self._schedule_customer_cell_highlight(table_key)

    def _clear_customer_cell_highlights(self, table_key):
        overlay = self._customer_overlays.get(table_key)
        if not overlay:
            return
        for label in overlay["labels"].values():
            label.destroy()
        overlay["labels"] = {}

    def _schedule_customer_cell_highlight(self, table_key):
        overlay = self._customer_overlays.get(table_key)
        if not overlay:
            return
        table = self._get_customer_table(table_key)
        if overlay["job"]:
            table.after_cancel(overlay["job"])
        overlay["job"] = table.after_idle(
            lambda key=table_key: self._refresh_customer_cell_highlights(key)
        )

    def _refresh_customer_cell_highlights(self, table_key):
        overlay = self._customer_overlays.get(table_key)
        if not overlay:
            return

        table = self._get_customer_table(table_key)
        overlay["job"] = None
        self._clear_customer_cell_highlights(table_key)

        for row_id, customer_name in overlay["names"].items():
            bbox = table.bbox(row_id, "Customer")
            if not bbox:
                continue

            x, y, width, height = bbox
            if width <= 0 or height <= 0:
                continue

            label = tk.Label(
                table,
                text=customer_name,
                font=styles.AppStyles.FONTS["body_bold"],
                fg="#1d4ed8",
                bg=styles.AppStyles.COLORS["white"],
                anchor="w",
                padx=4,
            )
            label.place(
                x=x + 1,
                y=y + 1,
                width=max(width - 2, 1),
                height=max(height - 2, 1),
            )
            label.bind(
                "<Button-1>",
                lambda _event, key=table_key, iid=row_id: self._select_customer_row(
                    key, iid
                ),
            )
            overlay["labels"][row_id] = label

    def _select_customer_row(self, table_key, row_id):
        table = self._get_customer_table(table_key)
        table.selection_set(row_id)
        table.focus(row_id)

    def _apply_payment_status_filter(self, query, params, status_value):
        status = (status_value or "").strip().lower()
        if not status or status == "all":
            return query, params

        if status == "open":
            query += " AND UPPER(status) = 'OPEN'"
        elif status in ("closed", "completed"):
            query += " AND UPPER(status) = 'CLOSED'"
        elif status == "pending":
            query += " AND COALESCE(pending_eur, 0) > 0"
        elif status == "received":
            query += " AND COALESCE(eur_received, 0) > 0"
        elif status == "expected":
            query += " AND COALESCE(eur_expected, 0) > 0"
        elif status == "partial":
            query += (
                " AND COALESCE(eur_received, 0) > 0"
                " AND COALESCE(pending_eur, 0) > 0"
            )
        return query, params

    def _add_pdf_header(self, story, stylesheet, title):
        company_style = ParagraphStyle(
            "CompanyHeader",
            parent=stylesheet["Title"],
            fontSize=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
            alignment=1,
        )
        title_style = ParagraphStyle(
            f"{title.replace(' ', '')}Title",
            parent=stylesheet["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#d32f2f"),
            spaceAfter=14,
            alignment=1,
        )
        story.append(Paragraph("SKY EXCHANGE", company_style))
        story.append(Paragraph(title, title_style))

    def _pdf_text(self, value):
        return escape(str(value if value is not None else ""))

    def _pdf_paragraph(self, value, style):
        return Paragraph(self._pdf_text(value), style)

    def _format_pdf_amount(self, value):
        try:
            return f"{float(value or 0):,.2f}"
        except (TypeError, ValueError):
            return str(value or "0.00")

    def _summary_filter_rows(self):
        filters = [
            ("Period", f"{self.date_from.get() or 'Any'} to {self.date_to.get() or 'Any'}"),
            ("Banker", self.banker_filter.get() or "All"),
            ("Customer", self.customer_filter.get() or "All"),
            ("Collector", self.collector_filter.get() or "All"),
            ("Currency", self.currency_filter.get() or "All"),
            ("Status", self.status_filter.get() or "All"),
        ]
        return [[label, value] for label, value in filters]

    def search_summary(self):
        try:
            conn = self.db()
            cur = conn.cursor()
            query = "SELECT deal_date, customer_name, banker_name, target_currency, eur_expected, eur_received, pending_eur, status FROM transactions WHERE 1=1"
            params = []
            if self.banker_filter.get() and self.banker_filter.get() != "All":
                query += " AND banker_name = ?"
                params.append(self.banker_filter.get())
            if self.customer_filter.get() and self.customer_filter.get() != "All":
                query += " AND customer_name = ?"
                params.append(self.customer_filter.get())
            if self.collector_filter.get() and self.collector_filter.get() != "All":
                query += " AND collector_name = ?"
                params.append(self.collector_filter.get())
            if self.currency_filter.get() and self.currency_filter.get() != "All":
                query += " AND target_currency = ?"
                params.append(self.currency_filter.get())
            query, params = self._apply_payment_status_filter(
                query, params, self.status_filter.get()
            )
            if self.date_from.get():
                query += " AND deal_date >= ?"
                params.append(self.date_from.get())
            if self.date_to.get():
                query += " AND deal_date <= ?"
                params.append(self.date_to.get())
            query += " ORDER BY deal_date DESC"
            cur.execute(query, params)
            rows = cur.fetchall()
            self.current_data = rows
            self._clear_customer_cell_highlights("summary")
            self._customer_overlays["summary"]["names"] = {}
            for item in self.summary_tree.get_children():
                self.summary_tree.delete(item)
            total_transactions = total_expected = total_received = total_pending = 0
            for index, row in enumerate(rows):
                row_id = f"summary_{index}"
                self._customer_overlays["summary"]["names"][row_id] = row[1]
                values = (row[0], "", row[2], row[3], row[4], row[5], row[6], row[7])
                self.summary_tree.insert("", "end", iid=row_id, values=values)
                total_transactions += 1
                total_expected += row[4] or 0
                total_received += row[5] or 0
                total_pending += row[6] or 0
            self._schedule_customer_cell_highlight("summary")
            self.total_transactions_label.config(
                text=f"Total Transactions: {total_transactions}"
            )
            self.total_expected_label.config(
                text=f"Total Expected (EUR): €{total_expected:,.2f}"
            )
            self.total_received_label.config(
                text=f"Total Received (EUR): €{total_received:,.2f}"
            )
            self.total_pending_label.config(
                text=f"Total Pending (EUR): €{total_pending:,.2f}"
            )
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to search: {e}")

    def search_detailed(self):
        try:
            conn = self.db()
            cur = conn.cursor()
            query = """SELECT id, deal_date, customer_name, collector_name, banker_name, target_currency, foreign_amount, exchange_rate, eur_expected, eur_received, pending_eur, status FROM transactions WHERE 1=1"""
            params = []
            if self.det_banker_filter.get() and self.det_banker_filter.get() != "All":
                query += " AND banker_name = ?"
                params.append(self.det_banker_filter.get())
            if (
                self.det_customer_filter.get()
                and self.det_customer_filter.get() != "All"
            ):
                query += " AND customer_name = ?"
                params.append(self.det_customer_filter.get())
            if (
                self.det_collector_filter.get()
                and self.det_collector_filter.get() != "All"
            ):
                query += " AND collector_name = ?"
                params.append(self.det_collector_filter.get())
            if (
                self.det_currency_filter.get()
                and self.det_currency_filter.get() != "All"
            ):
                query += " AND target_currency = ?"
                params.append(self.det_currency_filter.get())
            if self.det_date_from.get():
                query += " AND deal_date >= ?"
                params.append(self.det_date_from.get())
            if self.det_date_to.get():
                query += " AND deal_date <= ?"
                params.append(self.det_date_to.get())
            query += " ORDER BY deal_date DESC"
            cur.execute(query, params)
            rows = cur.fetchall()
            self.current_detailed_data = rows
            self._clear_customer_cell_highlights("detailed")
            self._customer_overlays["detailed"]["names"] = {}
            for item in self.detailed_tree.get_children():
                self.detailed_tree.delete(item)
            for row in rows:
                row_id = str(row[0])
                self._customer_overlays["detailed"]["names"][row_id] = row[2]
                values = [str(x) for x in row]
                values[2] = ""
                self.detailed_tree.insert("", "end", iid=row_id, values=values)
            self._schedule_customer_cell_highlight("detailed")
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to search: {e}")

    def search_currency(self):
        try:
            conn = self.db()
            cur = conn.cursor()
            query = """SELECT target_currency, COUNT(*) as count, SUM(foreign_amount) as total_amount, AVG(exchange_rate) as avg_rate,
                      SUM(eur_expected) as total_expected, SUM(eur_received) as total_received, SUM(pending_eur) as total_pending FROM transactions WHERE 1=1"""
            params = []
            if (
                self.cur_currency_filter.get()
                and self.cur_currency_filter.get() != "All"
            ):
                query += " AND target_currency = ?"
                params.append(self.cur_currency_filter.get())
            if self.cur_date_from.get():
                query += " AND deal_date >= ?"
                params.append(self.cur_date_from.get())
            if self.cur_date_to.get():
                query += " AND deal_date <= ?"
                params.append(self.cur_date_to.get())
            query += " GROUP BY target_currency ORDER BY target_currency"
            cur.execute(query, params)
            rows = cur.fetchall()
            for item in self.currency_tree.get_children():
                self.currency_tree.delete(item)
            for row in rows:
                formatted_row = (
                    row[0],
                    row[1],
                    f"{row[2]:,.2f}" if row[2] else "0.00",
                    f"{row[3]:,.4f}" if row[3] else "0.0000",
                    f"€{row[4]:,.2f}" if row[4] else "€0.00",
                    f"€{row[5]:,.2f}" if row[5] else "€0.00",
                    f"€{row[6]:,.2f}" if row[6] else "€0.00",
                )
                self.currency_tree.insert("", "end", values=formatted_row)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to search: {e}")

    def filter_today(self):
        today = str(date.today())
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, today)
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, today)
        self.search_summary()

    def filter_yesterday(self):
        yesterday = str(date.today() - timedelta(days=1))
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, yesterday)
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, yesterday)
        self.search_summary()

    def filter_week(self):
        today = date.today()
        week_ago = today - timedelta(days=7)
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, str(week_ago))
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, str(today))
        self.search_summary()

    def filter_month(self):
        today = date.today()
        month_ago = today - timedelta(days=30)
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, str(month_ago))
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, str(today))
        self.search_summary()

    def filter_90_days(self):
        today = date.today()
        days_90_ago = today - timedelta(days=90)
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, str(days_90_ago))
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, str(today))
        self.search_summary()

    def clear_filters(self):
        self.banker_filter.set("")
        self.customer_filter.set("")
        self.collector_filter.set("")
        self.currency_filter.set("")
        self.status_filter.set("All")
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, str(date.today() - timedelta(days=30)))
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, str(date.today()))
        self.refresh()

    def clear_detailed_filters(self):
        self.det_banker_filter.set("")
        self.det_customer_filter.set("")
        self.det_collector_filter.set("")
        self.det_currency_filter.set("")
        self.det_date_from.delete(0, tk.END)
        self.det_date_from.insert(0, str(date.today() - timedelta(days=30)))
        self.det_date_to.delete(0, tk.END)
        self.det_date_to.insert(0, str(date.today()))
        self.current_detailed_data = []
        self._clear_customer_cell_highlights("detailed")
        self._customer_overlays["detailed"]["names"] = {}
        for item in self.detailed_tree.get_children():
            self.detailed_tree.delete(item)

    def clear_currency_filters(self):
        self.cur_currency_filter.set("")
        self.cur_date_from.delete(0, tk.END)
        self.cur_date_from.insert(0, str(date.today() - timedelta(days=30)))
        self.cur_date_to.delete(0, tk.END)
        self.cur_date_to.insert(0, str(date.today()))
        for item in self.currency_tree.get_children():
            self.currency_tree.delete(item)

    def _safe_filename_part(self, value):
        text = str(value or "").strip()
        if not text or text == "All":
            return ""
        safe = []
        for char in text:
            safe.append(char if char.isalnum() or char in ("-", "_") else "_")
        return "".join(safe).strip("_")

    def _build_export_filename(self, selected_name, fallback_name, date_from, date_to, extension):
        name = self._safe_filename_part(selected_name) or fallback_name
        parts = [name]
        for value in (date_from, date_to):
            safe = self._safe_filename_part(value)
            if safe:
                parts.append(safe)
        return "_".join(parts) + extension

    def _first_selected_filter(self, *values):
        for value in values:
            safe = self._safe_filename_part(value)
            if safe:
                return safe
        return ""

    def download_summary_pdf(self):
        try:
            initialfile = self._build_export_filename(
                self._first_selected_filter(
                    self.customer_filter.get(),
                    self.banker_filter.get(),
                    self.collector_filter.get(),
                    self.currency_filter.get(),
                    self.status_filter.get(),
                ),
                "all",
                self.date_from.get(),
                self.date_to.get(),
                ".pdf",
            )
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=initialfile,
            )
            if not file_path:
                return
            doc = SimpleDocTemplate(
                file_path,
                pagesize=landscape(letter),
                rightMargin=0.35 * inch,
                leftMargin=0.35 * inch,
                topMargin=0.35 * inch,
                bottomMargin=0.35 * inch,
            )
            story = []
            stylesheet = getSampleStyleSheet()
            small_style = ParagraphStyle(
                "SummaryPdfSmall",
                parent=stylesheet["Normal"],
                fontSize=7,
                leading=9,
            )
            header_style = ParagraphStyle(
                "SummaryPdfHeader",
                parent=small_style,
                fontName="Helvetica-Bold",
                textColor=colors.white,
                alignment=1,
            )
            section_style = ParagraphStyle(
                "SummaryPdfSection",
                parent=stylesheet["Heading2"],
                fontSize=11,
                textColor=colors.HexColor("#0f172a"),
                spaceBefore=8,
                spaceAfter=6,
            )
            self._add_pdf_header(story, stylesheet, "Transaction Summary Report")
            story.append(Paragraph(f"Generated: {date.today()}", stylesheet["Normal"]))
            story.append(Spacer(1, 0.12 * inch))

            story.append(Paragraph("Selected Filters", section_style))
            filter_table = Table(
                self._summary_filter_rows(),
                colWidths=[1.2 * inch, 2.2 * inch],
                hAlign="LEFT",
            )
            filter_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(filter_table)
            story.append(Spacer(1, 0.12 * inch))

            total_transactions = len(self.current_data)
            total_expected = sum(float(row[4] or 0) for row in self.current_data)
            total_received = sum(float(row[5] or 0) for row in self.current_data)
            total_pending = sum(float(row[6] or 0) for row in self.current_data)
            story.append(Paragraph("Summary", section_style))
            stats_data = [
                [
                    "Total Transactions",
                    str(total_transactions),
                ],
                [
                    "Total Expected EUR",
                    self._format_pdf_amount(total_expected),
                ],
                [
                    "Total Received EUR",
                    self._format_pdf_amount(total_received),
                ],
                [
                    "Total Pending EUR",
                    self._format_pdf_amount(total_pending),
                ],
            ]
            stats_table = Table(stats_data, colWidths=[2.2 * inch, 1.5 * inch])
            stats_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fee2e2")),
                        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#f8fafc")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(stats_table)
            story.append(Spacer(1, 0.12 * inch))
            story.append(Paragraph("Transactions", section_style))
            table_data = [
                [
                    self._pdf_paragraph("Date", header_style),
                    self._pdf_paragraph("Customer", header_style),
                    self._pdf_paragraph("Banker", header_style),
                    self._pdf_paragraph("Currency", header_style),
                    self._pdf_paragraph("Expected EUR", header_style),
                    self._pdf_paragraph("Received EUR", header_style),
                    self._pdf_paragraph("Pending EUR", header_style),
                    self._pdf_paragraph("Status", header_style),
                ]
            ]
            for row in self.current_data:
                table_data.append(
                    [
                        self._pdf_paragraph(row[0], small_style),
                        self._pdf_paragraph(row[1], small_style),
                        self._pdf_paragraph(row[2], small_style),
                        self._pdf_paragraph(row[3], small_style),
                        self._pdf_paragraph(self._format_pdf_amount(row[4]), small_style),
                        self._pdf_paragraph(self._format_pdf_amount(row[5]), small_style),
                        self._pdf_paragraph(self._format_pdf_amount(row[6]), small_style),
                        self._pdf_paragraph(row[7], small_style),
                    ]
                )
            data_table = Table(
                table_data,
                colWidths=[
                    0.75 * inch,
                    1.35 * inch,
                    1.25 * inch,
                    0.75 * inch,
                    0.95 * inch,
                    0.95 * inch,
                    0.95 * inch,
                    0.7 * inch,
                ],
                repeatRows=1,
            )
            data_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d32f2f")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (3, -1), "CENTER"),
                        ("ALIGN", (4, 1), (6, -1), "RIGHT"),
                        ("ALIGN", (7, 1), (7, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f8fafc")],
                        ),
                    ]
                )
            )
            story.append(data_table)
            doc.build(story)
            messagebox.showinfo("Success", f"PDF downloaded successfully: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download PDF: {e}")

    def download_detailed_pdf(self):
        try:
            initialfile = self._build_export_filename(
                self._first_selected_filter(
                    self.det_customer_filter.get(),
                    self.det_banker_filter.get(),
                    self.det_collector_filter.get(),
                    self.det_currency_filter.get(),
                ),
                "all",
                self.det_date_from.get(),
                self.det_date_to.get(),
                ".pdf",
            )
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=initialfile,
            )
            if not file_path:
                return
            doc = SimpleDocTemplate(file_path, pagesize=landscape(letter))
            story = []
            stylesheet = getSampleStyleSheet()
            self._add_pdf_header(story, stylesheet, "Detailed Transaction Report")
            story.append(Spacer(1, 0.2 * inch))
            table_data = [
                [
                    "ID",
                    "Date",
                    "Customer",
                    "Collector",
                    "Currency",
                    "Amount",
                    "Rate",
                    "Expected EUR",
                    "Received EUR",
                    "Pending EUR",
                    "Status",
                ]
            ]
            for values in self.current_detailed_data:
                table_data.append(
                    [
                        values[0],
                        values[1],
                        values[2],
                        values[3],
                        values[5],
                        values[6],
                        values[7],
                        values[8],
                        values[9],
                        values[10],
                        values[11],
                    ]
                )
            data_table = Table(
                table_data,
                colWidths=[
                    0.4 * inch,
                    0.6 * inch,
                    0.8 * inch,
                    0.8 * inch,
                    0.5 * inch,
                    0.7 * inch,
                    0.5 * inch,
                    0.7 * inch,
                    0.7 * inch,
                    0.7 * inch,
                    0.5 * inch,
                ],
            )
            data_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d32f2f")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.whitesmoke, colors.lightgrey],
                        ),
                    ]
                )
            )
            story.append(data_table)
            doc.build(story)
            messagebox.showinfo("Success", f"PDF downloaded successfully: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download PDF: {e}")

    def download_currency_pdf(self):
        try:
            initialfile = self._build_export_filename(
                self.cur_currency_filter.get(),
                "all",
                self.cur_date_from.get(),
                self.cur_date_to.get(),
                ".pdf",
            )
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=initialfile,
            )
            if not file_path:
                return
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            story = []
            stylesheet = getSampleStyleSheet()
            self._add_pdf_header(story, stylesheet, "Currency Analysis Report")
            story.append(Spacer(1, 0.3 * inch))
            table_data = [
                [
                    "Currency",
                    "Count",
                    "Total Amount",
                    "Avg Rate",
                    "Total Expected EUR",
                    "Total Received EUR",
                    "Total Pending EUR",
                ]
            ]
            for item in self.currency_tree.get_children():
                table_data.append(self.currency_tree.item(item)["values"])
            data_table = Table(
                table_data,
                colWidths=[
                    1 * inch,
                    0.8 * inch,
                    1.2 * inch,
                    1 * inch,
                    1.3 * inch,
                    1.3 * inch,
                    1.3 * inch,
                ],
            )
            data_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d32f2f")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.whitesmoke, colors.lightgrey],
                        ),
                    ]
                )
            )
            story.append(data_table)
            doc.build(story)
            messagebox.showinfo("Success", f"PDF downloaded successfully: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download PDF: {e}")

    def download_excel(self):
        try:
            initialfile = self._build_export_filename(
                self._first_selected_filter(
                    self.customer_filter.get(),
                    self.banker_filter.get(),
                    self.collector_filter.get(),
                    self.currency_filter.get(),
                    self.status_filter.get(),
                ),
                "all",
                self.date_from.get(),
                self.date_to.get(),
                ".csv",
            )
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
                initialfile=initialfile,
            )
            if not file_path:
                return
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Date",
                        "Customer",
                        "Currency",
                        "Expected EUR",
                        "Received EUR",
                        "Pending EUR",
                        "Status",
                    ]
                )
                for row in self.current_data:
                    writer.writerow(
                        [row[0], row[1], row[3], row[4], row[5], row[6], row[7]]
                    )
            messagebox.showinfo(
                "Success", f"Excel file downloaded successfully: {file_path}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download Excel: {e}")

    def refresh(self):
        self.load_dropdown_values()
        self.search_summary()
