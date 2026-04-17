import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import styles


class CustomerCurrenciesPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_id = None

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Customer Rates")

        self.main_container = tk.Frame(self.frame, bg=styles.AppStyles.COLORS["light"])
        self.main_container.pack(fill="both", expand=True)

        self._build_add_currency()
        self._build_rate_entry()
        self._build_search_filter()
        self._build_table()

        self.load_currencies()
        self.search_customer_rates()

    def _build_add_currency(self):
        add_card = styles.create_card(self.main_container)
        add_card.pack(fill="x", padx=15, pady=(20, 15))
        inner = tk.Frame(add_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=15, pady=15)

        tk.Label(
            inner,
            text="Add New Currency",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(5, 12))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Country",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.country_name = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.country_name.pack(side="left", padx=(20, 40))

        tk.Label(
            row,
            text="Currency Code",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.new_currency = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.new_currency.pack(side="left", padx=(20, 40))

        styles.styled_button(row, "Add Currency", self.add_currency, "Success").pack(
            side="left"
        )

    def _build_rate_entry(self):
        rate_card = styles.create_card(self.main_container)
        rate_card.pack(fill="x", padx=15, pady=15)
        inner = tk.Frame(rate_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=15, pady=15)

        tk.Label(
            inner,
            text="Set Currency Rate",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(5, 12))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.customer_currency = ttk.Combobox(
            row, state="readonly", width=22, font=styles.AppStyles.FONTS["body"]
        )
        self.customer_currency.pack(side="left", padx=(20, 40))

        tk.Label(
            row,
            text="Rate",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.customer_rate = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.customer_rate.pack(side="left", padx=(20, 40))

        styles.styled_button(row, "Save Rate", self.save_customer_rate, "Primary").pack(
            side="left", padx=10
        )
        styles.styled_button(
            row, "Delete Selected", self.delete_selected, "Danger"
        ).pack(side="left")

    def _build_search_filter(self):
        search_card = styles.create_card(self.main_container)
        search_card.pack(fill="x", padx=15, pady=15)
        inner = tk.Frame(search_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=15, pady=15)

        tk.Label(
            inner,
            text="Search & Filter",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(5, 12))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Currency",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.search_currency = ttk.Combobox(row, width=22, font=styles.AppStyles.FONTS["body"])
        self.search_currency.pack(side="left", padx=(20, 40))

        tk.Label(
            row,
            text="Filter",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.filter_option = ttk.Combobox(
            row,
            values=["Today", "Yesterday", "This Week", "This Month", "All"],
            state="readonly",
            width=22,
            font=styles.AppStyles.FONTS["body"],
        )
        self.filter_option.pack(side="left", padx=(20, 40))
        self.filter_option.current(0)

        tk.Label(
            row,
            text="From",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.from_date = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.from_date.pack(side="left", padx=(5, 12))

        tk.Label(
            row,
            text="To",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(10, 15))
        self.to_date = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.to_date.pack(side="left", padx=(5, 12))

        styles.styled_button(row, "Search", self.search_customer_rates, "Primary").pack(
            side="left"
        )

    def _build_table(self):
        table_card = styles.create_card(self.main_container)
        table_card.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=10, pady=15)

        tk.Label(
            container,
            text="Currency Rates History",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        scrollbar = ttk.Scrollbar(container, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.table = ttk.Treeview(
            container,
            columns=("date", "currency", "rate"),
            show="headings",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.table.yview)

        self.table.heading("date", text="Date")
        self.table.heading("currency", text="Currency")
        self.table.heading("rate", text="Rate")
        self.table.column("date", width=22, anchor="center")
        self.table.column("currency", width=22, anchor="center")
        self.table.column("rate", width=22, anchor="center")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.select_row)

    def load_currencies(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute("SELECT code FROM currencies WHERE status=1")
        currencies = [r[0] for r in cur.fetchall()]
        self.customer_currency["values"] = currencies
        self.search_currency["values"] = [""] + currencies

    def add_currency(self):
        currency = self.new_currency.get().upper()
        country = self.country_name.get()
        if not currency or not country:
            messagebox.showerror("Error", "Enter country and currency code")
            return
        conn = self.db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO currencies (name,code,status) VALUES (?,?,1)",
                (country, currency),
            )
            conn.commit()
            messagebox.showinfo("Success", "Currency Added")
            self.new_currency.delete(0, tk.END)
            self.country_name.delete(0, tk.END)
            self.load_currencies()
        except:
            messagebox.showerror("Error", "Currency already exists")

    def save_customer_rate(self):
        currency = self.customer_currency.get()
        rate = self.customer_rate.get()
        if not currency or not rate:
            messagebox.showerror("Error", "Enter currency and rate")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO currency_rates (currency_code, base_currency, rate, rate_date) VALUES (?,?,?,?)",
            (currency, "EUR", float(rate), str(date.today())),
        )
        conn.commit()
        messagebox.showinfo("Success", "Rate saved")
        self.customer_rate.delete(0, tk.END)
        self.search_customer_rates()

    def search_customer_rates(self):
        self.table.delete(*self.table.get_children())
        conn = self.db()
        cur = conn.cursor()
        currency = self.search_currency.get()
        filter_type = self.filter_option.get()
        today = date.today()

        query = "SELECT id,rate_date,currency_code,rate FROM currency_rates WHERE 1=1"
        params = []

        if currency:
            query += " AND currency_code=?"
            params.append(currency)

        if self.from_date.get() and self.to_date.get():
            query += " AND rate_date BETWEEN ? AND ?"
            params.append(self.from_date.get())
            params.append(self.to_date.get())
        else:
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
            self.table.insert("", tk.END, iid=row[0], values=(row[1], row[2], row[3]))

    def select_row(self, event):
        selected = self.table.selection()
        if not selected:
            return
        self.selected_id = selected[0]
        row = self.table.item(selected[0])["values"]
        self.customer_currency.set(row[1])
        self.customer_rate.delete(0, tk.END)
        self.customer_rate.insert(0, row[2])

    def delete_selected(self):
        if not self.selected_id:
            return
        confirm = messagebox.askyesno("Confirm", "Delete selected rate?")
        if not confirm:
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute("DELETE FROM currency_rates WHERE id=?", (self.selected_id,))
        conn.commit()
        self.selected_id = None
        self.search_customer_rates()
