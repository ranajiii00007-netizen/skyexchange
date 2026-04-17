import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import styles


class BankerCurrenciesPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_id = None
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Banker Currency Rates")

        self.main_container = styles.make_scrollable(self.frame)

        self._build_assign_currency()
        self._build_assigned_currencies()
        self._build_search_filter()
        self._build_table()

        self.load_lists()
        self.banker_combo.bind("<<ComboboxSelected>>", self.load_assigned_currencies)
        self.search_rates()

    def _build_assign_currency(self):
        assign_card = styles.create_card(self.main_container)
        assign_card.pack(fill="x", padx=8, pady=(5, 3))
        inner = tk.Frame(assign_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Assign Currency To Banker",
            font=styles.AppStyles.FONTS["heading"],
            fg="#26a69a",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.banker_combo = ttk.Combobox(
            row, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.banker_combo.pack(side="left", padx=(4, 16))

        tk.Label(
            row,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.currency_combo = ttk.Combobox(
            row, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.currency_combo.pack(side="left", padx=(4, 16))

        styles.styled_button(
            row, "Assign Currency", self.assign_currency, "Success"
        ).pack(side="left")

    def _build_assigned_currencies(self):
        self.assigned_frame = styles.create_card(self.main_container)
        self.assigned_frame.pack(fill="x", padx=8, pady=4)
        self.currency_container = tk.Frame(
            self.assigned_frame, bg=styles.AppStyles.COLORS["white"]
        )
        self.currency_container.pack(fill="x", padx=10, pady=6)

        tk.Label(
            self.currency_container,
            text="Assigned Currencies",
            font=styles.AppStyles.FONTS["heading"],
            fg="#26a69a",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        headers_frame = tk.Frame(
            self.currency_container, bg=styles.AppStyles.COLORS["light"]
        )
        headers_frame.pack(fill="x", pady=(0, 3))

        tk.Label(
            headers_frame,
            text="Currency",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)
        tk.Label(
            headers_frame,
            text="Rate",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)
        tk.Label(
            headers_frame,
            text="Rate Date (YYYY-MM-DD)",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)
        tk.Label(
            headers_frame,
            text="Actions",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)

    def _build_search_filter(self):
        search_card = styles.create_card(self.main_container)
        search_card.pack(fill="x", padx=8, pady=4)
        inner = tk.Frame(search_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Search & Filter",
            font=styles.AppStyles.FONTS["heading"],
            fg="#26a69a",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Banker",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.search_banker = ttk.Combobox(row, width=22, font=styles.AppStyles.FONTS["body"])
        self.search_banker.pack(side="left", padx=(4, 16))

        tk.Label(
            row,
            text="Date Filter",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 6))
        self.date_filter = ttk.Combobox(
            row,
            values=["Today", "Yesterday", "This Week", "This Month", "All"],
            state="readonly",
            width=22,
            font=styles.AppStyles.FONTS["body"],
        )
        self.date_filter.pack(side="left", padx=(4, 16))
        self.date_filter.current(0)

        styles.styled_button(row, "Search", self.search_rates, "Primary").pack(
            side="left"
        )

    def _build_table(self):
        table_card = styles.create_card(self.main_container)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Banker Rate History",
            font=styles.AppStyles.FONTS["heading"],
            fg="#26a69a",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        scrollbar_y = ttk.Scrollbar(container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.table = ttk.Treeview(
            container,
            columns=("date", "banker", "currency", "rate"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=xscrollbar.set,
            height=16,
        )
        scrollbar_y.config(command=self.table.yview)
        xscrollbar.config(command=self.table.xview)

        self.table.heading("date", text="Date")
        self.table.heading("banker", text="Banker")
        self.table.heading("currency", text="Currency")
        self.table.heading("rate", text="Rate")
        self.table.column("date", width=120, anchor="center", minwidth=100)
        self.table.column("banker", width=220, anchor="w", minwidth=160)
        self.table.column("currency", width=120, anchor="center", minwidth=90)
        self.table.column("rate", width=160, anchor="e", minwidth=120)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", self.open_edit_rate_dialog)

    def load_lists(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute("SELECT code FROM currencies WHERE status=1")
        self.currency_combo["values"] = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT name FROM bankers WHERE status=1")
        bankers = [r[0] for r in cur.fetchall()]
        self.banker_combo["values"] = bankers
        self.search_banker["values"] = [""] + bankers

    def assign_currency(self):
        banker = self.banker_combo.get()
        currency = self.currency_combo.get()
        if not banker or not currency:
            messagebox.showerror("Error", "Select banker and currency")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM banker_currencies WHERE banker_name=? AND currency_code=?",
            (banker, currency),
        )
        if cur.fetchone():
            messagebox.showwarning("Warning", "Currency already assigned")
            return
        cur.execute(
            "INSERT INTO banker_currencies (banker_name,currency_code) VALUES (?,?)",
            (banker, currency),
        )
        conn.commit()
        messagebox.showinfo("Success", "Currency assigned")
        self.load_assigned_currencies()

    def load_assigned_currencies(self, event=None):
        banker = self.banker_combo.get()
        if not banker:
            return

        for widget in self.currency_container.winfo_children():
            if widget not in [self.currency_container.winfo_children()[0]]:
                widget.destroy()

        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "SELECT currency_code FROM banker_currencies WHERE banker_name=?", (banker,)
        )
        currencies = [r[0] for r in cur.fetchall()]

        headers_frame = tk.Frame(
            self.currency_container, bg=styles.AppStyles.COLORS["light"]
        )
        headers_frame.pack(fill="x", pady=(0, 3))
        tk.Label(
            headers_frame,
            text="Currency",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)
        tk.Label(
            headers_frame,
            text="Rate",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)
        tk.Label(
            headers_frame,
            text="Rate Date (YYYY-MM-DD)",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)
        tk.Label(
            headers_frame,
            text="Actions",
            font=styles.AppStyles.FONTS["body_bold"],
            bg=styles.AppStyles.COLORS["light"],
        ).pack(side="left", padx=10, pady=5)

        for currency in currencies:
            row_frame = tk.Frame(
                self.currency_container, bg=styles.AppStyles.COLORS["white"]
            )
            row_frame.pack(fill="x", pady=4)

            tk.Label(
                row_frame,
                text=currency,
                font=styles.AppStyles.FONTS["heading"],
                width=22,
                bg=styles.AppStyles.COLORS["white"],
            ).pack(side="left", padx=10)

            rate_entry = tk.Entry(
                row_frame, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
            )
            rate_entry.pack(side="left", padx=10)

            date_entry = tk.Entry(
                row_frame, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
            )
            date_entry.insert(0, str(date.today()))
            date_entry.pack(side="left", padx=10)

            btn_frame = tk.Frame(row_frame, bg=styles.AppStyles.COLORS["white"])
            btn_frame.pack(side="left", padx=10)
            styles.styled_button(
                btn_frame,
                "Save",
                lambda c=currency, r=rate_entry, d=date_entry: self.save_rate(c, r, d),
                "Success",
            ).pack(side="left", padx=2)
            styles.styled_button(
                btn_frame,
                "Remove",
                lambda c=currency: self.remove_currency(c),
                "Danger",
            ).pack(side="left", padx=2)

    def save_rate(self, currency, rate_entry, date_entry):
        banker = self.banker_combo.get()
        rate_text = rate_entry.get().strip()
        date_text = date_entry.get().strip()
        try:
            rate = float(rate_text)
            if rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Rate must be a positive number")
            return
        try:
            from datetime import datetime

            parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Error", "Date must be in YYYY-MM-DD format")
            return

        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO banker_currency_rates (banker_name,currency_code,rate,rate_date) VALUES (?,?,?,?)",
            (banker, currency, rate, str(parsed_date)),
        )
        conn.commit()
        messagebox.showinfo("Success", f"{currency} rate saved for {parsed_date}")
        self.search_rates()

    def remove_currency(self, currency):
        banker = self.banker_combo.get()
        if not messagebox.askyesno("Confirm", f"Remove {currency} from {banker}?"):
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM banker_currencies WHERE banker_name=? AND currency_code=?",
            (banker, currency),
        )
        conn.commit()
        self.load_assigned_currencies()

    def search_rates(self):
        self.table.delete(*self.table.get_children())
        conn = self.db()
        cur = conn.cursor()
        banker = self.search_banker.get()
        filter_type = self.date_filter.get()
        today = date.today()

        query = "SELECT id,rate_date,banker_name,currency_code,rate FROM banker_currency_rates WHERE 1=1"
        params = []
        if banker:
            query += " AND banker_name=?"
            params.append(banker)
        if filter_type == "Today":
            query += " AND rate_date=?"
            params.append(str(today))
        elif filter_type == "Yesterday":
            query += " AND rate_date=?"
            params.append(str(today - timedelta(days=1)))
        elif filter_type == "This Week":
            query += " AND rate_date>=?"
            params.append(str(today - timedelta(days=today.weekday())))
        elif filter_type == "This Month":
            query += " AND rate_date>=?"
            params.append(str(today.replace(day=1)))
        query += " ORDER BY rate_date DESC"
        cur.execute(query, params)
        for row in cur.fetchall():
            self.table.insert(
                "", tk.END, iid=row[0], values=(row[1], row[2], row[3], row[4])
            )

    def open_edit_rate_dialog(self, _event=None):
        selected = self.table.selection()
        if not selected:
            return
        row_id = selected[0]
        values = self.table.item(row_id, "values")

        dialog = tk.Toplevel(self.frame)
        dialog.title("Edit Rate")
        dialog.transient(self.frame)
        dialog.grab_set()

        inner = tk.Frame(dialog, bg=styles.AppStyles.COLORS["white"], padx=20, pady=20)
        inner.pack()

        tk.Label(
            inner,
            text=f"Banker: {values[1]}",
            font=styles.AppStyles.FONTS["subtitle"],
            fg=styles.AppStyles.COLORS["text_primary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        tk.Label(
            inner,
            text=f"Currency: {values[2]}",
            font=("Segoe UI", 11),
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 15))

        tk.Label(
            inner,
            text="Rate",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=2, column=0, sticky="w", pady=(0, 5))
        rate_entry = tk.Entry(
            inner, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        rate_entry.insert(0, values[3])
        rate_entry.grid(row=3, column=0, pady=(0, 15), sticky="w")

        tk.Label(
            inner,
            text="Date (YYYY-MM-DD)",
            font=styles.AppStyles.FONTS["body"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).grid(row=2, column=1, sticky="w", padx=(15, 0), pady=(0, 5))
        date_entry = tk.Entry(
            inner, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        date_entry.insert(0, values[0])
        date_entry.grid(row=3, column=1, pady=(0, 15), padx=(15, 0), sticky="w")

        btn_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        def do_update():
            rate_text = rate_entry.get().strip()
            date_text = date_entry.get().strip()
            try:
                rate = float(rate_text)
                if rate <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Rate must be a positive number")
                return
            try:
                from datetime import datetime

                parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Error", "Date must be in YYYY-MM-DD format")
                return
            conn = self.db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE banker_currency_rates SET rate=?, rate_date=? WHERE id=?",
                (rate, str(parsed_date), row_id),
            )
            conn.commit()
            dialog.destroy()
            messagebox.showinfo("Success", "Rate updated successfully")
            self.search_rates()

        styles.styled_button(btn_frame, "Update", do_update, "Primary").pack(
            side="left", padx=10
        )
        styles.styled_button(btn_frame, "Cancel", dialog.destroy, "Secondary").pack(
            side="left"
        )

    def refresh(self):
        self.load_lists()
        self.load_assigned_currencies()
        self.search_rates()
