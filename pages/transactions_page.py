import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import styles


class AutoCompleteEntry(tk.Entry):
    def __init__(self, master, values=None, **kwargs):
        super().__init__(master, **kwargs)
        self.values = values or []
        self.filtered = []
        self.popup = None
        self.listbox = None
        self.bind("<KeyRelease>", self.on_keyrelease)
        self.bind("<Down>", self.move_down)
        self.bind("<Up>", self.move_up)
        self.bind("<Return>", self.select_item)
        self.bind("<Tab>", self.tab_select)
        self.bind("<Escape>", lambda e: self.hide_popup())
        self.bind("<FocusOut>", self.on_focus_out)

    def set_values(self, values):
        self.values = values

    def on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
        typed = self.get().lower()
        self.filtered = (
            self.values
            if not typed
            else [item for item in self.values if typed in item.lower()]
        )
        if not self.filtered:
            self.hide_popup()
            return
        self.show_popup()

    def show_popup(self):
        if not self.popup:
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            frame = tk.Frame(self.popup, borderwidth=22, relief="solid")
            frame.pack()
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
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height()
        self.popup.geometry(f"{self.winfo_width()}x120+{x}+{y}")

    def hide_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.listbox = None

    def move_down(self, event):
        if not self.listbox:
            return
        index = min(
            self.listbox.curselection()[0] + 1
            if self.listbox.curselection()
            else 0 + 1,
            self.listbox.size() - 1,
        )
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
        return "break"

    def move_up(self, event):
        if not self.listbox:
            return
        index = max(
            (self.listbox.curselection()[0] if self.listbox.curselection() else 1) - 1,
            0,
        )
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
        return "break"

    def select_item(self, event=None):
        if self.listbox:
            selection = self.listbox.curselection()
            if selection:
                value = self.listbox.get(selection[0])
                self.delete(0, tk.END)
                self.insert(0, value)
        self.hide_popup()

    def tab_select(self, event):
        if self.listbox:
            self.select_item()
        return None

    def on_focus_out(self, event):
        self.after(100, self.hide_popup)


class TransactionsPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_transaction_id = None
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Transactions")

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

        self._build_summary()
        self._build_new_deal()
        self._build_table()
        self._build_footer_buttons()
        self.refresh()

    def _build_summary(self):
        summary_card = styles.create_card(self.scrollable_frame)
        summary_card.pack(fill="x", padx=8, pady=(5, 3))
        inner = tk.Frame(summary_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=6)

        tk.Label(
            inner,
            text="Today's Summary (Regular Only)",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        stats_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        stats_frame.pack(fill="x")

        stats = [
            ("Open Deals", "lbl_open", styles.AppStyles.COLORS["warning"], "0"),
            ("Closed Deals", "lbl_closed", styles.AppStyles.COLORS["success"], "0"),
            ("Expected", "lbl_expected", styles.AppStyles.COLORS["primary"], "€0.00"),
            ("Received", "lbl_received", styles.AppStyles.COLORS["success"], "€0.00"),
            ("Pending", "lbl_pending", styles.AppStyles.COLORS["danger"], "€0.00"),
        ]

        for text, attr, color, default in stats:
            stat_frame = tk.Frame(
                stats_frame, bg=styles.AppStyles.COLORS["light"], relief="solid", bd=1
            )
            stat_frame.pack(side="left", padx=3, fill="both", expand=True)
            tk.Label(
                stat_frame,
                text=text,
                font=styles.AppStyles.FONTS["small"],
                fg=styles.AppStyles.COLORS["text_secondary"],
                bg=styles.AppStyles.COLORS["light"],
            ).pack(pady=(6, 2), padx=6)
            label = tk.Label(
                stat_frame,
                text=default,
                font=styles.AppStyles.FONTS["subtitle"],
                fg=color,
                bg=styles.AppStyles.COLORS["light"],
            )
            label.pack(pady=(0, 6), padx=6)
            setattr(self, attr, label)

    def _build_new_deal(self):
        deal_card = styles.create_card(self.scrollable_frame)
        deal_card.pack(fill="x", padx=8, pady=4)
        inner = tk.Frame(deal_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="New Transaction",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row1 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row1.pack(fill="x", pady=3)

        tk.Label(
            row1,
            text="Customer",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.deal_customer = AutoCompleteEntry(row1, [], width=18)
        self.deal_customer.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])
        self.deal_customer.pack(side="left", padx=(4, 12))

        tk.Label(
            row1,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.deal_currency = AutoCompleteEntry(row1, [], width=12)
        self.deal_currency.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])
        self.deal_currency.pack(side="left", padx=(4, 12))

        tk.Label(
            row1,
            text="Collector",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.deal_collector = AutoCompleteEntry(row1, [], width=18)
        self.deal_collector.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])
        self.deal_collector.pack(side="left", padx=(4, 12))

        tk.Label(
            row1,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.deal_banker = AutoCompleteEntry(row1, [], width=18)
        self.deal_banker.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])
        self.deal_banker.pack(side="left", padx=(4, 0))

        row2 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x", pady=3)

        tk.Label(
            row2,
            text="Override Rate",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.override_rate = tk.Entry(
            row2, font=styles.AppStyles.FONTS["body"], width=14, relief="solid", bd=1
        )
        self.override_rate.pack(side="left", padx=(4, 12))

        tk.Label(
            row2,
            text="Local Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.local_currency_amount = tk.Entry(
            row2, font=styles.AppStyles.FONTS["body"], width=14, relief="solid", bd=1
        )
        self.local_currency_amount.pack(side="left", padx=(4, 12))

        tk.Label(
            row2,
            text="Expected EUR",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.eur_expected = tk.Entry(
            row2, font=styles.AppStyles.FONTS["body"], width=14, relief="solid", bd=1
        )
        self.eur_expected.pack(side="left", padx=(4, 12))

        tk.Label(
            row2,
            text="Sent Amount",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.sent_amount = tk.Label(
            row2,
            text="0",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        )
        self.sent_amount.pack(side="left", padx=(4, 0))

        row3 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row3.pack(fill="x", pady=(4, 0))

        tk.Label(
            row3,
            text="Notes",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.notes_entry = tk.Entry(
            row3, font=styles.AppStyles.FONTS["body"], width=30, relief="solid", bd=1
        )
        self.notes_entry.pack(side="left", padx=(4, 12))

        btn_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_frame.pack(fill="x", pady=(5, 0))
        styles.styled_button(
            btn_frame,
            "Save Transaction",
            lambda: self.save_deal(transaction_type="REGULAR"),
            "Success",
        ).pack(side="left", padx=10)
        styles.styled_button(
            btn_frame,
            "Save Personal Transaction",
            lambda: self.save_deal(transaction_type="PERSONAL"),
            "Primary",
        ).pack(side="left", padx=10)

        self.eur_expected.bind("<KeyRelease>", self.calculate_sent)
        self.override_rate.bind("<KeyRelease>", self.on_rate_changed)
        self.local_currency_amount.bind("<KeyRelease>", self.calculate_eur_from_local)
        self.deal_currency.bind("<KeyRelease>", self.on_rate_changed, add="+")

    def _build_table(self):
        table_card = styles.create_card(self.scrollable_frame)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Today's Transactions (Regular + Personal)",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["success"],
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
        scrollbar = ttk.Scrollbar(container)
        scrollbar.pack(side="right", fill="y")

        self._customer_names = {}
        self._customer_cell_labels = {}
        self._customer_overlay_job = None

        def sync_vertical_scroll(first, last):
            scrollbar.set(first, last)
            self._schedule_customer_cell_highlight()

        def table_yview(*args):
            self.trans_table.yview(*args)
            self._schedule_customer_cell_highlight()

        self.trans_table = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            yscrollcommand=sync_vertical_scroll,
        )
        scrollbar.config(command=table_yview)

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
        widths = {
            "date": 90,
            "type": 80,
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
            self.trans_table.heading(col, text=headings[col])
            anchor = (
                "center"
                if col in ("date", "type", "currency", "rate", "status")
                else (
                    "e" if col in ("expected", "received", "pending", "sent") else "w"
                )
            )
            self.trans_table.column(col, width=widths[col], anchor=anchor, minwidth=widths[col])

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        def sync_horizontal_scroll(first, last):
            xscrollbar.set(first, last)
            self._schedule_customer_cell_highlight()

        def table_xview(*args):
            self.trans_table.xview(*args)
            self._schedule_customer_cell_highlight()

        self.trans_table.configure(xscrollcommand=sync_horizontal_scroll)
        xscrollbar.config(command=table_xview)

        self.trans_table.pack(fill="both", expand=True)
        self.trans_table.tag_configure("open", background="#fff3cd")
        self.trans_table.tag_configure("closed", background="#d4edda")
        self.trans_table.tag_configure("personal", background="#bfdbfe")
        self.trans_table.bind("<<TreeviewSelect>>", self.on_row_select)
        self.trans_table.bind(
            "<Configure>", lambda _event: self._schedule_customer_cell_highlight()
        )
        self.trans_table.bind(
            "<ButtonRelease-1>", lambda _event: self._schedule_customer_cell_highlight()
        )
        self.trans_table.bind(
            "<MouseWheel>", lambda _event: self._schedule_customer_cell_highlight()
        )

    def _build_footer_buttons(self):
        btn_frame = tk.Frame(self.scrollable_frame, bg=styles.AppStyles.COLORS["light"])
        btn_frame.pack(pady=6)
        styles.styled_button(
            btn_frame, "Remove Selected Transaction", self.delete_transaction, "Danger"
        ).pack()

    def format_euro(self, value):
        return f"€{value:,.2f}"

    def get_active_rate(self):
        if self.override_rate.get().strip():
            return float(self.override_rate.get())
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rate FROM currency_rates WHERE currency_code=? AND rate_date=?",
            (self.deal_currency.get(), str(date.today())),
        )
        row = cur.fetchone()
        return float(row[0]) if row else None

    def refresh(self):
        self.load_dropdowns()
        self.load_transactions()
        self.load_summary()

    def load_dropdowns(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM customers WHERE status=1")
        self.deal_customer.values = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT name FROM collectors WHERE status=1")
        self.deal_collector.values = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT code FROM currencies WHERE status=1")
        self.deal_currency.values = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT name FROM bankers WHERE status=1")
        self.deal_banker.values = [r[0] for r in cur.fetchall()]

    def calculate_eur_from_local(self, event=None):
        try:
            local_amount = float(self.local_currency_amount.get())
            rate = self.get_active_rate()
            if not rate:
                return
            expected_eur = local_amount / rate if rate else 0
            self.eur_expected.delete(0, tk.END)
            self.eur_expected.insert(0, f"{expected_eur:.2f}")
            self.calculate_sent()
        except ValueError:
            if not self.local_currency_amount.get().strip():
                self.eur_expected.delete(0, tk.END)
            self.calculate_sent()

    def on_rate_changed(self, event=None):
        if self.local_currency_amount.get().strip():
            self.calculate_eur_from_local()
        else:
            self.calculate_sent()

    def calculate_sent(self, event=None):
        try:
            exp = float(self.eur_expected.get())
            rate = self.get_active_rate()
            if rate:
                self.sent_amount.config(text=f"{exp * rate:,.2f}")
        except Exception:
            self.sent_amount.config(text="0")

    def load_summary(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            """SELECT SUM(eur_expected), SUM(eur_received), SUM(pending_eur),
                      SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END), SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END)
                      FROM transactions WHERE deal_date=? AND COALESCE(transaction_type, 'REGULAR')='REGULAR'""",
            (str(date.today()),),
        )
        exp, rec, pend, open_c, closed_c = cur.fetchone()
        self.lbl_expected.config(text=self.format_euro(exp or 0))
        self.lbl_received.config(text=self.format_euro(rec or 0))
        self.lbl_pending.config(text=self.format_euro(pend or 0))
        self.lbl_open.config(text=f"{open_c or 0}")
        self.lbl_closed.config(text=f"{closed_c or 0}")

    def save_deal(self, transaction_type="REGULAR"):
        if not self.deal_customer.get() or not self.deal_currency.get():
            messagebox.showerror("Error", "Customer and Currency required")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rate FROM currency_rates WHERE currency_code=? AND rate_date=?",
            (self.deal_currency.get(), str(date.today())),
        )
        row = cur.fetchone()
        if not row and not self.override_rate.get().strip():
            messagebox.showerror("Error", "No rate for today")
            return
        rate = (
            float(self.override_rate.get())
            if self.override_rate.get()
            else float(row[0])
        )
        try:
            exp = float(self.eur_expected.get())
        except ValueError:
            messagebox.showerror("Error", "Expected EUR must be a valid number")
            return
        pending, foreign_amt = exp, exp * rate
        cur.execute(
            """INSERT INTO transactions (customer_name, collector_name, banker_name, target_currency, exchange_rate,
                      eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date, notes, transaction_type)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.deal_customer.get(),
                self.deal_collector.get(),
                self.deal_banker.get(),
                self.deal_currency.get(),
                rate,
                exp,
                0,
                pending,
                foreign_amt,
                "OPEN",
                str(date.today()),
                self.notes_entry.get(),
                transaction_type,
            ),
        )
        conn.commit()
        self.eur_expected.delete(0, tk.END)
        self.local_currency_amount.delete(0, tk.END)
        self.override_rate.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self.sent_amount.config(text="0")
        self.refresh()
        messagebox.showinfo(
            "Success",
            f"{'Personal ' if transaction_type == 'PERSONAL' else ''}Transaction Saved",
        )

    def on_row_select(self, event):
        if self.trans_table.selection():
            self.selected_transaction_id = self.trans_table.selection()[0]

    def _clear_customer_cell_highlights(self):
        for label in self._customer_cell_labels.values():
            label.destroy()
        self._customer_cell_labels = {}

    def _schedule_customer_cell_highlight(self):
        if self._customer_overlay_job:
            self.trans_table.after_cancel(self._customer_overlay_job)
        self._customer_overlay_job = self.trans_table.after_idle(
            self._refresh_customer_cell_highlights
        )

    def _refresh_customer_cell_highlights(self):
        self._customer_overlay_job = None
        self._clear_customer_cell_highlights()

        for row_id, customer_name in self._customer_names.items():
            bbox = self.trans_table.bbox(row_id, "customer")
            if not bbox:
                continue

            x, y, width, height = bbox
            if width <= 0 or height <= 0:
                continue

            tags = self.trans_table.item(row_id, "tags")
            bg = "#bfdbfe" if "personal" in tags else (
                "#fff3cd" if "open" in tags else "#d4edda"
            )

            label = tk.Label(
                self.trans_table,
                text=customer_name,
                font=styles.AppStyles.FONTS["body_bold"],
                fg="#1d4ed8",
                bg=bg,
                anchor="w",
                padx=4,
            )
            label.place(x=x + 1, y=y + 1, width=max(width - 2, 1), height=max(height - 2, 1))
            label.bind("<Button-1>", lambda _event, iid=row_id: self._select_table_row(iid))
            self._customer_cell_labels[row_id] = label

    def _select_table_row(self, row_id):
        self.trans_table.selection_set(row_id)
        self.trans_table.focus(row_id)
        self.selected_transaction_id = row_id

    def delete_transaction(self):
        if not self.selected_transaction_id:
            messagebox.showwarning("Warning", "Please select a transaction")
            return
        if not messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete this transaction?"
        ):
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM transactions WHERE id=?", (self.selected_transaction_id,)
        )
        conn.commit()
        self.selected_transaction_id = None
        self.refresh()
        messagebox.showinfo("Deleted", "Transaction removed successfully")

    def load_transactions(self):
        self._clear_customer_cell_highlights()
        self._customer_names = {}
        self.trans_table.delete(*self.trans_table.get_children())
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, customer_name, collector_name, banker_name, target_currency, exchange_rate,
                      eur_expected, eur_received, pending_eur, foreign_amount, status, deal_date,
                      COALESCE(transaction_type, 'REGULAR') as transaction_type
                      FROM transactions WHERE deal_date=? ORDER BY id DESC""",
            (str(date.today()),),
        )
        for r in cur.fetchall():
            tx_type = r[12]
            row_tag = (
                "personal"
                if tx_type == "PERSONAL"
                else ("open" if r[10] == "OPEN" else "closed")
            )
            self._customer_names[str(r[0])] = r[1]
            self.trans_table.insert(
                "",
                tk.END,
                iid=r[0],
                values=(
                    r[11],
                    tx_type,
                    "",
                    r[2],
                    r[3],
                    r[4],
                    r[5],
                    self.format_euro(r[6]),
                    self.format_euro(r[7]),
                    self.format_euro(r[8]),
                    f"{r[9]:,.2f}",
                    r[10],
                ),
                tags=(row_tag,),
            )
        self._schedule_customer_cell_highlight()
