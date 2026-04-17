import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import styles


class AutoCompleteEntry(tk.Entry):
    active_entries = []
    _global_bind_done = False

    def __init__(self, master, values=None, clear_if_not_selected=True, **kwargs):
        super().__init__(master, **kwargs)
        self.values = values or []
        self.filtered = []
        self.popup = None
        self.listbox = None
        self.clear_if_not_selected = clear_if_not_selected
        self._selected_value = ""

        AutoCompleteEntry.active_entries.append(self)

        self.bind("<KeyRelease>", self.on_keyrelease)
        self.bind("<Down>", self.move_down)
        self.bind("<Up>", self.move_up)
        self.bind("<Return>", self.select_item)
        self.bind("<Tab>", self.tab_select)
        self.bind("<Escape>", lambda e: self.hide_popup())
        self.bind("<FocusOut>", self.on_focus_out)
        self.bind("<Destroy>", self._on_destroy)

        if not AutoCompleteEntry._global_bind_done:
            root = self.winfo_toplevel()
            root.bind_all("<Button-1>", AutoCompleteEntry.close_all_popups, add="+")
            root.bind_all("<FocusIn>", AutoCompleteEntry.close_all_popups, add="+")
            AutoCompleteEntry._global_bind_done = True

    def _on_destroy(self, _event):
        if self in AutoCompleteEntry.active_entries:
            AutoCompleteEntry.active_entries.remove(self)

    @classmethod
    def close_all_popups(cls, _event=None):
        for entry in list(cls.active_entries):
            try:
                entry.hide_popup()
            except tk.TclError:
                pass

    def set_values(self, values):
        self.values = values or []

    def on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
        self._selected_value = ""
        typed = self.get().strip().lower()
        if not typed:
            self.filtered = self.values
        else:
            self.filtered = [item for item in self.values if typed in item.lower()]
        if not self.filtered:
            self.hide_popup()
            return
        self.show_popup()

    def show_popup(self):
        if not self.popup:
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            frame = tk.Frame(self.popup, borderwidth=22, relief="solid")
            frame.pack(fill="both", expand=True)
            self.listbox = tk.Listbox(frame, height=6)
            scrollbar = tk.Scrollbar(frame)
            self.listbox.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=self.listbox.yview)
            self.listbox.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            self.listbox.bind("<Double-Button-1>", self.select_item)
            self.listbox.bind("<Return>", self.select_item)

        self.listbox.delete(0, tk.END)
        for item in self.filtered[:50]:
            self.listbox.insert(tk.END, item)
        if self.listbox.size() > 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.popup.geometry(f"{self.winfo_width()}x120+{x}+{y}")

    def hide_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.listbox = None

    def move_down(self, _event):
        if not self.listbox:
            return None
        selection = self.listbox.curselection()
        index = 0 if not selection else selection[0] + 1
        if index >= self.listbox.size():
            index = self.listbox.size() - 1
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
        return "break"

    def move_up(self, _event):
        if not self.listbox:
            return None
        selection = self.listbox.curselection()
        index = 0 if not selection else selection[0] - 1
        if index < 0:
            index = 0
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
        return "break"

    def select_item(self, _event=None):
        if not self.listbox:
            return
        selection = self.listbox.curselection()
        if not selection:
            return
        value = self.listbox.get(selection[0])
        self.delete(0, tk.END)
        self.insert(0, value)
        self._selected_value = value
        self.hide_popup()

    def tab_select(self, _event):
        self.hide_popup()
        return None

    def on_focus_out(self, _event):
        def _cleanup():
            self.hide_popup()
            if not self.clear_if_not_selected:
                return
            typed = self.get().strip()
            if not typed:
                return
            valid_exact = any(v.lower() == typed.lower() for v in self.values)
            selected_exact = (
                bool(self._selected_value)
                and self._selected_value.lower() == typed.lower()
            )
            if not (valid_exact or selected_exact):
                self.delete(0, tk.END)

        self.after(100, _cleanup)


class TransactionsManagerPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_id = None
        self._customer_names = {}
        self._customer_cell_labels = {}
        self._customer_overlay_job = None
        self.edit_popup = None

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Manage Transactions")

        self.main_container = tk.Frame(self.frame, bg=styles.AppStyles.COLORS["light"])
        self.main_container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.main_container, orient="vertical")
        canvas = tk.Canvas(
            self.main_container,
            bg=styles.AppStyles.COLORS["light"],
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.scrollable_frame = tk.Frame(canvas, bg=styles.AppStyles.COLORS["light"])
        canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw", tags="frame"
        )

        def configure_scrollregion():
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.scrollable_frame.bind(
            "<Configure>", lambda e: canvas.after(10, configure_scrollregion)
        )
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("frame", width=e.width))
        canvas.bind(
            "<Enter>",
            lambda e: canvas.bind_all(
                "<MouseWheel>",
                lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units"),
            ),
        )
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._build_filters()
        self._build_quick_filters()
        self._build_summary()
        self._build_edit_section()
        self._build_table()

        self.load_dropdowns()
        self.load_transactions()

    def _build_filters(self):
        filter_card = styles.create_card(self.scrollable_frame)
        filter_card.pack(fill="x", padx=8, pady=(5, 3))

        inner = tk.Frame(filter_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Search Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg="#5c6bc0",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row1 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row1.pack(fill="x", pady=(0, 3))

        row2 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x")

        filters = [
            ("Customer", "customer_filter", 0, 18),
            ("Exclude Customer", "exclude_customer_filter", 1, 18),
            ("Collector", "collector_filter", 2, 18),
            ("Banker", "banker_filter", 3, 18),
            ("Currency", "currency_filter", 4, 10),
        ]

        for text, attr, col, width in filters:
            tk.Label(
                row1,
                text=text,
                font=styles.AppStyles.FONTS["body"],
                fg=styles.AppStyles.COLORS["text_secondary"],
                bg=styles.AppStyles.COLORS["white"],
            ).grid(row=0, column=col, sticky="w", padx=(5, 2))

            entry = AutoCompleteEntry(row1, [], clear_if_not_selected=True, width=width)
            entry.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])
            entry.grid(row=1, column=col, sticky="w", padx=(5, 12), pady=(0, 4))
            setattr(self, attr, entry)

        tk.Label(
            row2,
            text="Status",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=0, sticky="w", padx=(5, 2))

        self.status_filter = ttk.Combobox(
            row2,
            values=["ALL", "OPEN", "CLOSED"],
            width=18,
            font=styles.AppStyles.FONTS["body"],
            state="readonly",
        )
        self.status_filter.set("ALL")
        self.status_filter.grid(row=1, column=0, sticky="w", padx=(5, 12), pady=(0, 4))

        tk.Label(
            row2,
            text="Type",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=1, sticky="w", padx=(5, 2))

        self.type_filter = ttk.Combobox(
            row2,
            values=["ALL", "REGULAR", "PERSONAL"],
            width=18,
            font=styles.AppStyles.FONTS["body"],
            state="readonly",
        )
        self.type_filter.set("ALL")
        self.type_filter.grid(row=1, column=1, sticky="w", padx=(5, 12), pady=(0, 4))

        tk.Label(
            row2,
            text="From",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=2, sticky="w", padx=(5, 2))

        self.date_from = tk.Entry(
            row2, width=18, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.date_from.grid(row=1, column=2, sticky="w", padx=(5, 12), pady=(0, 4))

        tk.Label(
            row2,
            text="To",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=3, sticky="w", padx=(5, 2))

        self.date_to = tk.Entry(
            row2, width=18, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.date_to.grid(row=1, column=3, sticky="w", padx=(5, 12), pady=(0, 4))

        btn_row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_row.pack(fill="x", pady=(6, 0))

        styles.styled_button(
            btn_row, "Search", self.search_transactions, "Primary"
        ).pack(side="left", padx=5)
        styles.styled_button(btn_row, "Clear", self.clear_filters, "Secondary").pack(
            side="left"
        )

    def _build_quick_filters(self):
        quick_card = styles.create_card(self.scrollable_frame)
        quick_card.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(quick_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            inner,
            text="Quick Filters",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(0, 10))

        for text, cmd in [
            ("Today", self.filter_today),
            ("Yesterday", self.filter_yesterday),
            ("This Week", self.filter_week),
            ("This Month", self.filter_month),
        ]:
            styles.styled_button(inner, text, cmd, "Secondary").pack(
                side="left", padx=3
            )

        note_inner = tk.Frame(quick_card, bg=styles.AppStyles.COLORS["white"])
        note_inner.pack(fill="x", padx=10, pady=(0, 5))

        tk.Label(
            note_inner,
            text="Note:",
            font=styles.AppStyles.FONTS["small_bold"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(0, 6))

        self.selected_note_label = tk.Label(
            note_inner,
            text="Select a transaction to view notes",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_primary"],
            bg=styles.AppStyles.COLORS["white"],
            anchor="w",
        )
        self.selected_note_label.pack(side="left", fill="x", expand=True)

    def _build_summary(self):
        summary_card = styles.create_card(self.scrollable_frame)
        summary_card.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(summary_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=5)

        stats = [
            ("Deals: 0", "result_label", styles.AppStyles.COLORS["text_primary"]),
            (
                "Expected: €0",
                "total_expected_label",
                styles.AppStyles.COLORS["primary"],
            ),
            (
                "Received: €0",
                "total_received_label",
                styles.AppStyles.COLORS["success"],
            ),
            ("Pending: €0", "total_pending_label", styles.AppStyles.COLORS["danger"]),
        ]

        for text, attr, color in stats:
            label = tk.Label(
                inner,
                text=text,
                font=styles.AppStyles.FONTS["body_bold"],
                fg=color,
                bg=styles.AppStyles.COLORS["white"],
            )
            label.pack(side="left", padx=15)
            setattr(self, attr, label)

    def _build_edit_section(self):
        # Editing now happens in a popup opened by double-clicking a transaction.
        self.edit_collector = None
        self.edit_banker = None
        self.edit_currency = None
        self.edit_rate = None
        self.edit_expected = None
        self.edit_received = None
        self.edit_status = None

    def _build_edit_fields(self, parent):
        inner = tk.Frame(parent, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        customer_label = tk.Label(
            inner,
            text="",
            font=styles.AppStyles.FONTS["body_bold"],
            fg="#1d4ed8",
            bg=styles.AppStyles.COLORS["white"],
        )
        customer_label.pack(anchor="w", pady=(0, 8))
        self.edit_customer_label = customer_label

        tk.Label(
            inner,
            text="Edit Transaction",
            font=styles.AppStyles.FONTS["heading"],
            fg="#5c6bc0",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row1 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row1.pack(fill="x", pady=3)

        edits = [
            ("Collector", "edit_collector", 0),
            ("Banker", "edit_banker", 2),
            ("Currency", "edit_currency", 4),
            ("Override Rate", "edit_rate", 6),
        ]

        for text, attr, col in edits:
            tk.Label(
                row1,
                text=text,
                font=styles.AppStyles.FONTS["body"],
                fg=styles.AppStyles.COLORS["text_secondary"],
                bg=styles.AppStyles.COLORS["white"],
            ).grid(row=0, column=col, sticky="w", padx=(5, 2))

            width = 18 if col in (0, 2) else 10
            entry = AutoCompleteEntry(row1, [], clear_if_not_selected=True, width=width)
            entry.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])
            entry.grid(row=1, column=col, sticky="w", padx=(5, 15), pady=(0, 5))
            setattr(self, attr, entry)

        row2 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x", pady=(4, 0))

        tk.Label(
            row2,
            text="Expected EUR",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=0, sticky="w", padx=(5, 2))

        self.edit_expected = tk.Entry(
            row2, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.edit_expected.grid(row=1, column=0, sticky="w", padx=(5, 15), pady=(0, 5))

        tk.Label(
            row2,
            text="Received EUR",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=1, sticky="w", padx=(5, 2))

        self.edit_received = tk.Entry(
            row2, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.edit_received.grid(row=1, column=1, sticky="w", padx=(5, 15), pady=(0, 5))

        tk.Label(
            row2,
            text="Status",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=2, sticky="w", padx=(5, 2))

        self.edit_status = ttk.Combobox(
            row2, values=["OPEN", "CLOSED"], width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.edit_status.grid(row=1, column=2, sticky="w", padx=(5, 15), pady=(0, 5))

        btn_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_frame.pack(fill="x", pady=(6, 0))

        styles.styled_button(
            btn_frame, "Update Transaction", self.update_transaction, "Primary"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Delete Transaction", self.delete_transaction, "Danger"
        ).pack(side="left")
        styles.styled_button(
            btn_frame, "Close", self._close_edit_popup, "Secondary"
        ).pack(side="left", padx=5)

    def _build_table(self):
        table_card = styles.create_card(self.scrollable_frame)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))

        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Transactions List",
            font=styles.AppStyles.FONTS["heading"],
            fg="#5c6bc0",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 3))

        columns = (
            "date",
            "type",
            "customer",
            "collector",
            "banker",
            "currency",
            "rate",
            "expected",
            "received",
            "pending",
            "sent",
            "status",
        )

        scrollbar_y = ttk.Scrollbar(container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        def sync_vertical_scroll(first, last):
            scrollbar_y.set(first, last)
            self._schedule_customer_cell_highlight()

        def table_yview(*args):
            self.table.yview(*args)
            self._schedule_customer_cell_highlight()

        self.table = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            yscrollcommand=sync_vertical_scroll,
        )
        scrollbar_y.config(command=table_yview)

        style = ttk.Style()
        style.configure(
            "Treeview.Heading",
            background=styles.AppStyles.COLORS["header_bg"],
            foreground=styles.AppStyles.COLORS["text_primary"],
            font=styles.AppStyles.FONTS["heading"],
        )

        headings = {
            "date": "Date",
            "type": "Type",
            "customer": "Customer",
            "collector": "Collector",
            "banker": "Banker",
            "currency": "Currency",
            "rate": "Rate",
            "expected": "Expected EUR",
            "received": "Received EUR",
            "pending": "Pending EUR",
            "sent": "Sent Amount",
            "status": "Status",
        }

        col_widths = {
            "date": 90,
            "type": 85,
            "customer": 140,
            "collector": 110,
            "banker": 110,
            "currency": 70,
            "rate": 75,
            "expected": 100,
            "received": 100,
            "pending": 100,
            "sent": 100,
            "status": 80,
        }

        for col in columns:
            self.table.heading(col, text=headings[col])
            anchor = (
                "center"
                if col in ("date", "type", "currency", "rate", "status")
                else (
                    "e" if col in ("expected", "received", "pending", "sent") else "w"
                )
            )
            w = col_widths.get(col, 100)
            self.table.column(col, width=w, anchor=anchor, minwidth=w)

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        def sync_horizontal_scroll(first, last):
            xscrollbar.set(first, last)
            self._schedule_customer_cell_highlight()

        def table_xview(*args):
            self.table.xview(*args)
            self._schedule_customer_cell_highlight()

        self.table.configure(xscrollcommand=sync_horizontal_scroll)
        xscrollbar.config(command=table_xview)

        self.table.pack(fill="both", expand=True)
        self.table.tag_configure("open", background="#fff3cd")
        self.table.tag_configure("closed", background="#d4edda")
        self.table.tag_configure("personal", background="#cce5ff")
        self.table.bind("<<TreeviewSelect>>", self.load_selected)
        self.table.bind("<Double-1>", self.open_edit_popup)
        self.table.bind(
            "<Configure>", lambda _event: self._schedule_customer_cell_highlight()
        )
        self.table.bind(
            "<ButtonRelease-1>", lambda _event: self._schedule_customer_cell_highlight()
        )
        self.table.bind(
            "<MouseWheel>", lambda _event: self._schedule_customer_cell_highlight()
        )

    def filter_today(self):
        today = date.today().strftime("%Y-%m-%d")
        self.date_from.delete(0, tk.END)
        self.date_to.delete(0, tk.END)
        self.date_from.insert(0, today)
        self.date_to.insert(0, today)
        self.search_transactions()

    def filter_yesterday(self):
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.date_from.delete(0, tk.END)
        self.date_to.delete(0, tk.END)
        self.date_from.insert(0, yesterday)
        self.date_to.insert(0, yesterday)
        self.search_transactions()

    def filter_week(self):
        today = date.today()
        start_week = today - timedelta(days=today.weekday())
        self.date_from.delete(0, tk.END)
        self.date_to.delete(0, tk.END)
        self.date_from.insert(0, start_week.strftime("%Y-%m-%d"))
        self.date_to.insert(0, today.strftime("%Y-%m-%d"))
        self.search_transactions()

    def filter_month(self):
        today = date.today()
        start_month = today.replace(day=1)
        self.date_from.delete(0, tk.END)
        self.date_to.delete(0, tk.END)
        self.date_from.insert(0, start_month.strftime("%Y-%m-%d"))
        self.date_to.insert(0, today.strftime("%Y-%m-%d"))
        self.search_transactions()

    def format_euro(self, value):
        return f"€{value:,.2f}"

    def refresh(self):
        self.load_transactions()
        self.load_dropdowns()

    def _transactions_select_query(self):
        return (
            "SELECT id, customer_name, collector_name, banker_name, target_currency, "
            "exchange_rate, eur_expected, eur_received, pending_eur, foreign_amount, "
            "status, deal_date, notes, COALESCE(transaction_type, 'REGULAR') "
            "FROM transactions"
        )

    def _clear_customer_cell_highlights(self):
        for label in self._customer_cell_labels.values():
            label.destroy()
        self._customer_cell_labels = {}

    def _schedule_customer_cell_highlight(self):
        if self._customer_overlay_job:
            self.table.after_cancel(self._customer_overlay_job)
        self._customer_overlay_job = self.table.after_idle(
            self._refresh_customer_cell_highlights
        )

    def _refresh_customer_cell_highlights(self):
        self._customer_overlay_job = None
        self._clear_customer_cell_highlights()

        for row_id, customer_name in self._customer_names.items():
            bbox = self.table.bbox(row_id, "customer")
            if not bbox:
                continue

            x, y, width, height = bbox
            if width <= 0 or height <= 0:
                continue

            tags = self.table.item(row_id, "tags")
            bg = (
                "#cce5ff"
                if "personal" in tags
                else ("#fff3cd" if "open" in tags else "#d4edda")
            )

            label = tk.Label(
                self.table,
                text=customer_name,
                font=styles.AppStyles.FONTS["body_bold"],
                fg="#1d4ed8",
                bg=bg,
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
                "<Button-1>", lambda _event, iid=row_id: self._select_table_row(iid)
            )
            label.bind(
                "<Double-1>", lambda _event, iid=row_id: self.open_edit_popup()
            )
            self._customer_cell_labels[row_id] = label

    def _select_table_row(self, row_id):
        self.table.selection_set(row_id)
        self.table.focus(row_id)
        self.selected_id = int(row_id)
        row = self._get_transaction_by_id(self.selected_id)
        if row:
            self._show_selected_note(row)

    def _show_selected_note(self, row):
        note = (row[12] or "").strip()
        if not note:
            note = "No note for selected transaction"
        if len(note) > 180:
            note = f"{note[:177]}..."
        self.selected_note_label.config(text=note)

    def load_dropdowns(self):
        conn = self.db()
        cur = conn.cursor()

        cur.execute("SELECT name FROM customers")
        customers = [r[0] for r in cur.fetchall()]
        self.customer_filter.set_values(customers)
        self.exclude_customer_filter.set_values(customers)

        cur.execute("SELECT name FROM collectors")
        collectors = [r[0] for r in cur.fetchall()]
        self.collector_filter.set_values(collectors)
        if self.edit_collector is not None:
            self.edit_collector.set_values(collectors)

        cur.execute("SELECT code FROM currencies")
        currencies = [r[0] for r in cur.fetchall()]
        self.currency_filter.set_values(currencies)
        if self.edit_currency is not None:
            self.edit_currency.set_values(currencies)

        cur.execute("SELECT name FROM bankers")
        bankers = [r[0] for r in cur.fetchall()]
        self.banker_filter.set_values(bankers)
        if self.edit_banker is not None:
            self.edit_banker.set_values(bankers)

    def search_transactions(self):
        conn = self.db()
        cur = conn.cursor()

        query = f"{self._transactions_select_query()} WHERE 1=1"
        params = []

        if self.customer_filter.get().strip():
            query += " AND LOWER(customer_name) LIKE ?"
            params.append(f"%{self.customer_filter.get().strip().lower()}%")

        if self.exclude_customer_filter.get().strip():
            query += " AND LOWER(customer_name) NOT LIKE ?"
            params.append(f"%{self.exclude_customer_filter.get().strip().lower()}%")

        if self.collector_filter.get().strip():
            query += " AND LOWER(collector_name) LIKE ?"
            params.append(f"%{self.collector_filter.get().strip().lower()}%")

        if self.banker_filter.get().strip():
            query += " AND LOWER(banker_name) LIKE ?"
            params.append(f"%{self.banker_filter.get().strip().lower()}%")

        if self.currency_filter.get().strip():
            query += " AND LOWER(target_currency) LIKE ?"
            params.append(f"%{self.currency_filter.get().strip().lower()}%")

        if self.status_filter.get() != "ALL":
            query += " AND status=?"
            params.append(self.status_filter.get())

        if self.type_filter.get() != "ALL":
            query += " AND COALESCE(transaction_type, 'REGULAR')=?"
            params.append(self.type_filter.get())

        if self.date_from.get().strip():
            query += " AND deal_date>=?"
            params.append(self.date_from.get().strip())

        if self.date_to.get().strip():
            query += " AND deal_date<=?"
            params.append(self.date_to.get().strip())

        query += " ORDER BY id DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        self.populate_table(rows)

    def populate_table(self, rows):
        self._clear_customer_cell_highlights()
        self._customer_names = {}
        self.table.delete(*self.table.get_children())

        total_expected = total_received = total_pending = 0.0

        for r in rows:
            expected = float(r[6] or 0)
            received = float(r[7] or 0)
            pending = float(r[8] or 0)
            sent = float(r[9] or 0)
            transaction_type = r[13] or "REGULAR"

            tag = (
                "personal"
                if transaction_type == "PERSONAL"
                else ("open" if r[10] == "OPEN" else "closed")
            )
            self._customer_names[str(r[0])] = r[1]
            self.table.insert(
                "",
                tk.END,
                iid=r[0],
                values=(
                    r[11],
                    transaction_type,
                    "",
                    r[2],
                    r[3],
                    r[4],
                    r[5],
                    self.format_euro(expected),
                    self.format_euro(received),
                    self.format_euro(pending),
                    f"{sent:,.2f}",
                    r[10],
                ),
                tags=(tag,),
            )

            total_expected += expected
            total_received += received
            total_pending += pending

        self._schedule_customer_cell_highlight()

        self.result_label.config(text=f"Deals: {len(rows)}")
        self.total_expected_label.config(
            text=f"Expected: {self.format_euro(total_expected)}"
        )
        self.total_received_label.config(
            text=f"Received: {self.format_euro(total_received)}"
        )
        self.total_pending_label.config(
            text=f"Pending: {self.format_euro(total_pending)}"
        )
        if not rows:
            self.selected_note_label.config(text="Select a transaction to view notes")

    def load_transactions(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute(f"{self._transactions_select_query()} ORDER BY id DESC")
        rows = cur.fetchall()
        self.populate_table(rows)

    def load_selected(self, _event):
        selected = self.table.selection()
        if not selected:
            return

        self.selected_id = int(selected[0])
        row = self._get_transaction_by_id(self.selected_id)
        if row:
            self._show_selected_note(row)
        if self.edit_popup and self.edit_popup.winfo_exists():
            if row:
                self._populate_edit_fields(row)

    def open_edit_popup(self, _event=None):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select transaction")
            return

        self.selected_id = int(selected[0])
        row = self._get_transaction_by_id(self.selected_id)
        if not row:
            messagebox.showerror("Error", "Transaction not found")
            return

        if self.edit_popup and self.edit_popup.winfo_exists():
            self.edit_popup.lift()
            self.edit_popup.focus_force()
        else:
            self.edit_popup = tk.Toplevel(self.frame)
            self.edit_popup.title("Edit Transaction")
            self.edit_popup.configure(bg=styles.AppStyles.COLORS["white"])
            self.edit_popup.transient(self.frame)
            self.edit_popup.grab_set()
            self.edit_popup.protocol("WM_DELETE_WINDOW", self._close_edit_popup)
            self._build_edit_fields(self.edit_popup)
            self.load_dropdowns()

        self._populate_edit_fields(row)

    def _close_edit_popup(self):
        if self.edit_popup and self.edit_popup.winfo_exists():
            self.edit_popup.grab_release()
            self.edit_popup.destroy()
        self.edit_popup = None
        self.edit_collector = None
        self.edit_banker = None
        self.edit_currency = None
        self.edit_rate = None
        self.edit_expected = None
        self.edit_received = None
        self.edit_status = None

    def _populate_edit_fields(self, row):
        collector_val = (row[2] or "").strip()
        banker_val = (row[3] or "").strip()
        currency_val = (row[4] or "").strip().upper()

        if hasattr(self, "edit_customer_label"):
            self.edit_customer_label.config(
                text=f"Customer: {row[1] or ''}    Date: {row[11] or ''}"
            )

        self.edit_collector.delete(0, tk.END)
        self.edit_collector.insert(0, collector_val)
        self.edit_collector._selected_value = collector_val

        self.edit_banker.delete(0, tk.END)
        self.edit_banker.insert(0, banker_val)
        self.edit_banker._selected_value = banker_val

        self.edit_currency.delete(0, tk.END)
        self.edit_currency.insert(0, currency_val)
        self.edit_currency._selected_value = currency_val

        self.edit_rate.delete(0, tk.END)
        self.edit_rate.insert(0, str(row[5] or ""))

        self.edit_expected.delete(0, tk.END)
        self.edit_expected.insert(0, str(row[6] or 0))

        self.edit_received.delete(0, tk.END)
        self.edit_received.insert(0, str(row[7] or 0))

        self.edit_status.set(row[10] or "OPEN")

    def _get_transaction_by_id(self, transaction_id):
        conn = self.db()
        cur = conn.cursor()
        cur.execute(f"{self._transactions_select_query()} WHERE id=?", (transaction_id,))
        return cur.fetchone()

    def _get_today_rate(self, currency_code):
        today = date.today().strftime("%Y-%m-%d")
        conn = self.db()
        cur = conn.cursor()

        code = (currency_code or "").strip().upper()
        if not code:
            return None

        lookup_queries = [
            (
                "SELECT rate FROM currency_rates WHERE UPPER(currency_code)=? AND rate_date=? ORDER BY id DESC LIMIT 1",
                (code, today),
            ),
            (
                "SELECT rate FROM exchange_rates WHERE UPPER(currency)=? AND date=? ORDER BY id DESC LIMIT 1",
                (code, today),
            ),
            (
                "SELECT exchange_rate FROM rates WHERE UPPER(code)=? AND rate_date=? ORDER BY id DESC LIMIT 1",
                (code, today),
            ),
        ]

        for query, params in lookup_queries:
            try:
                cur.execute(query, params)
                row = cur.fetchone()
                if row and row[0] is not None:
                    value = float(row[0])
                    if value > 0:
                        return value
            except Exception:
                continue
        return None

    def _recalculate_eur_values(
        self, old_expected_eur, old_received_eur, foreign_amount, new_rate
    ):
        if new_rate <= 0:
            raise ValueError("Rate must be > 0")

        foreign_amount = float(foreign_amount or 0)
        old_expected_eur = float(old_expected_eur or 0)
        old_received_eur = float(old_received_eur or 0)

        new_expected = foreign_amount / new_rate if foreign_amount > 0 else 0.0

        ratio = 0.0
        if old_expected_eur > 0:
            ratio = old_received_eur / old_expected_eur
            ratio = max(0.0, min(1.0, ratio))

        new_received = new_expected * ratio
        new_pending = max(0.0, new_expected - new_received)

        return new_expected, new_received, new_pending

    def update_transaction(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select transaction")
            return
        if self.edit_collector is None:
            messagebox.showwarning("Warning", "Double-click a transaction to edit")
            return

        row = self._get_transaction_by_id(self.selected_id)
        if not row:
            messagebox.showerror("Error", "Transaction not found")
            return

        old_collector = (row[2] or "").strip()
        old_banker = (row[3] or "").strip()
        old_currency = (row[4] or "").strip().upper()
        old_rate = float(row[5] or 0)
        old_expected = float(row[6] or 0)
        old_received = float(row[7] or 0)
        old_pending = float(row[8] or 0)
        old_foreign = float(row[9] or 0)
        old_status = (row[10] or "OPEN").strip().upper()

        ui_collector = self.edit_collector.get().strip()
        ui_banker = self.edit_banker.get().strip()
        ui_currency = self.edit_currency.get().strip().upper()
        ui_rate = self.edit_rate.get().strip()
        ui_expected = self.edit_expected.get().strip()
        ui_received = self.edit_received.get().strip()
        ui_status = self.edit_status.get().strip().upper()

        def canonical_from_master(raw_value, master_values):
            raw = (raw_value or "").strip()
            if not raw:
                return None
            for value in master_values or []:
                v = (value or "").strip()
                if raw.lower() == v.lower():
                    return value
            return None

        collector = old_collector
        banker = old_banker
        currency = old_currency
        new_rate = old_rate
        exp = old_expected
        rec = old_received
        pending = old_pending
        foreign_amount = old_foreign
        status = old_status if old_status in ("OPEN", "CLOSED") else "OPEN"

        collector_values = getattr(self.edit_collector, "values", [])
        banker_values = getattr(self.edit_banker, "values", [])

        if ui_collector:
            collector_candidate = canonical_from_master(ui_collector, collector_values)
            if collector_candidate is None:
                messagebox.showerror(
                    "Error", "Collector must be selected from the list"
                )
                return
            collector = collector_candidate.strip()

        if ui_banker:
            banker_candidate = canonical_from_master(ui_banker, banker_values)
            if banker_candidate is None:
                messagebox.showerror("Error", "Banker must be selected from the list")
                return
            banker = banker_candidate.strip().title()

        if not collector:
            collector = old_collector
        if not banker:
            banker = old_banker

        if ui_currency:
            currency = ui_currency

        if not banker:
            messagebox.showerror("Error", "Banker is required")
            return
        if not currency:
            messagebox.showerror("Error", "Currency is required")
            return

        currency_changed = currency != old_currency

        try:
            if currency_changed:
                today_rate = self._get_today_rate(currency)
                if today_rate is None:
                    messagebox.showerror(
                        "Rate Missing",
                        f"Today's rate for {currency} is not available ({date.today().strftime('%Y-%m-%d')}).\n"
                        "Please add/update today's rate in Customer Currency page first.",
                    )
                    return

                new_rate = float(today_rate)
                exp = old_expected
                rec = old_received
                pending = max(0.0, exp - rec)
                foreign_amount = exp * new_rate
            else:
                if ui_expected:
                    exp = float(ui_expected)
                if ui_received:
                    rec = float(ui_received)
                if ui_rate:
                    new_rate = float(ui_rate)

                if new_rate <= 0:
                    raise ValueError("Rate must be > 0")

                pending = max(0.0, exp - rec)
                foreign_amount = exp * new_rate

        except ValueError:
            messagebox.showerror(
                "Error", "Expected, Received and Rate must be valid numbers"
            )
            return

        if ui_status in ("OPEN", "CLOSED"):
            status = ui_status
        else:
            status = "CLOSED" if pending <= 0 else "OPEN"

        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE transactions SET collector_name=?, banker_name=?, target_currency=?, "
            "exchange_rate=?, eur_expected=?, eur_received=?, pending_eur=?, foreign_amount=?, status=? WHERE id=?",
            (
                collector,
                banker,
                currency,
                new_rate,
                exp,
                rec,
                pending,
                foreign_amount,
                status,
                self.selected_id,
            ),
        )
        conn.commit()

        self.edit_collector.delete(0, tk.END)
        self.edit_collector.insert(0, collector)
        self.edit_collector._selected_value = collector

        self.edit_banker.delete(0, tk.END)
        self.edit_banker.insert(0, banker)
        self.edit_banker._selected_value = banker

        self.edit_currency.delete(0, tk.END)
        self.edit_currency.insert(0, currency)
        self.edit_currency._selected_value = currency

        self.edit_rate.delete(0, tk.END)
        self.edit_rate.insert(0, f"{new_rate:.6f}".rstrip("0").rstrip("."))

        self.edit_expected.delete(0, tk.END)
        self.edit_expected.insert(0, f"{exp:.2f}")

        self.edit_received.delete(0, tk.END)
        self.edit_received.insert(0, f"{rec:.2f}")

        self.edit_status.set(status)

        messagebox.showinfo("Updated", "Transaction updated")
        self._close_edit_popup()
        self.search_transactions()

    def delete_transaction(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select transaction")
            return

        confirm = messagebox.askyesno("Confirm Delete", "Delete this transaction?")
        if not confirm:
            return

        conn = self.db()
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id=?", (self.selected_id,))
        conn.commit()

        messagebox.showinfo("Deleted", "Transaction deleted")
        self.selected_id = None
        self._close_edit_popup()
        self.search_transactions()

    def clear_filters(self):
        self.customer_filter.delete(0, tk.END)
        self.exclude_customer_filter.delete(0, tk.END)
        self.collector_filter.delete(0, tk.END)
        self.banker_filter.delete(0, tk.END)
        self.currency_filter.delete(0, tk.END)
        self.status_filter.set("ALL")
        self.type_filter.set("ALL")
        self.date_from.delete(0, tk.END)
        self.date_to.delete(0, tk.END)
        self.selected_note_label.config(text="Select a transaction to view notes")
        self.load_transactions()
