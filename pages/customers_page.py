import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import styles


class CustomersPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_id = None
        self.checked_items = set()
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Customers")

        self.main_container = styles.make_scrollable(self.frame)
        self._build_form()
        self._build_buttons()
        self._build_search()
        self._build_table()

        self.load_customers()

    def _build_form(self):
        form_card = styles.create_card(self.main_container)
        form_card.pack(fill="x", padx=8, pady=(5, 3))

        form_inner = tk.Frame(form_card, bg=styles.AppStyles.COLORS["white"])
        form_inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            form_inner,
            text="Customer Information",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["primary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        fields_frame = tk.Frame(form_inner, bg=styles.AppStyles.COLORS["white"])
        fields_frame.pack(fill="x")

        row1 = tk.Frame(fields_frame, bg=styles.AppStyles.COLORS["white"])
        row1.pack(fill="x", pady=3)

        tk.Label(
            row1,
            text="Customer Name",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_name = tk.Entry(
            row1, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_name.pack(side="left", padx=(4, 12))

        tk.Label(
            row1,
            text="Phone 1",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_phone = tk.Entry(
            row1, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_phone.pack(side="left", padx=(4, 12))

        tk.Label(
            row1,
            text="Phone 2",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_phone2 = tk.Entry(
            row1, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_phone2.pack(side="left", padx=(4, 12))

        tk.Label(
            row1,
            text="Phone 3",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_phone3 = tk.Entry(
            row1, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_phone3.pack(side="left", padx=(4, 0))

        row2 = tk.Frame(fields_frame, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x", pady=3)

        tk.Label(
            row2,
            text="Address",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_address = tk.Entry(
            row2, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_address.pack(side="left", padx=(4, 12))

        tk.Label(
            row2,
            text="Reference",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_reference = tk.Entry(
            row2, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_reference.pack(side="left", padx=(4, 12))

        tk.Label(
            row2,
            text="Country",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.cust_country = tk.Entry(
            row2, font=styles.AppStyles.FONTS["body"], width=18, relief="solid", bd=1
        )
        self.cust_country.pack(side="left", padx=(4, 0))

    def _build_buttons(self):
        btn_frame = tk.Frame(self.main_container, bg=styles.AppStyles.COLORS["light"])
        btn_frame.pack(pady=5)

        styles.styled_button(
            btn_frame, "Add Customer", self.add_customer, "Success"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Update Customer", self.update_customer, "Primary"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Delete Selected", self.delete_selected, "Danger"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Clear Form", self.clear_fields, "Secondary"
        ).pack(side="left", padx=5)

    def _build_search(self):
        search_card = styles.create_card(self.main_container)
        search_card.pack(fill="x", padx=8, pady=4)

        search_inner = tk.Frame(search_card, bg=styles.AppStyles.COLORS["white"])
        search_inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            search_inner,
            text="Search",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 8))

        self.cust_search_entry = tk.Entry(
            search_inner, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.cust_search_entry.pack(side="left", padx=6)

        styles.styled_button(
            search_inner, "Search", self.load_customers, "Primary"
        ).pack(side="left", padx=5)
        styles.styled_button(search_inner, "Clear", self.refresh, "Secondary").pack(
            side="left"
        )

    def _build_table(self):
        table_card = styles.create_card(self.main_container)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))

        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        scrollbar = ttk.Scrollbar(container, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.cust_table = ttk.Treeview(
            container,
            columns=(
                "check",
                "name",
                "phone",
                "phone2",
                "phone3",
                "address",
                "reference",
                "country",
                "date",
            ),
            show="headings",
            yscrollcommand=scrollbar.set,
            xscrollcommand=xscrollbar.set,
            height=14,
        )
        scrollbar.config(command=self.cust_table.yview)
        xscrollbar.config(command=self.cust_table.xview)

        for col, text, width in [
            ("check", "✓", 40),
            ("name", "Customer Name", 160),
            ("phone", "Phone 1", 110),
            ("phone2", "Phone 2", 110),
            ("phone3", "Phone 3", 110),
            ("address", "Address", 180),
            ("reference", "Reference", 130),
            ("country", "Country", 100),
            ("date", "Created", 100),
        ]:
            anchor = (
                "center"
                if col in ("check", "phone", "phone2", "phone3", "country", "date")
                else "w"
            )
            self.cust_table.heading(col, text=text)
            self.cust_table.column(col, width=width, anchor=anchor, minwidth=width)

        self.cust_table.tag_configure(
            "cust_name",
            background=styles.AppStyles.COLORS["customer_name_bg"],
            foreground="#1e3a8a",
        )

        self.cust_table.pack(fill="both", expand=True)
        self.cust_table.bind("<Button-1>", self.handle_click)
        self.cust_table.bind("<<TreeviewSelect>>", self.load_selected)

    def handle_click(self, event):
        region = self.cust_table.identify("region", event.x, event.y)
        column = self.cust_table.identify_column(event.x)
        if region == "heading" and column == "#1":
            self.toggle_select_all()
            return "break"
        if region == "cell" and column == "#1":
            row = self.cust_table.identify_row(event.y)
            if row:
                if row in self.checked_items:
                    self.checked_items.remove(row)
                else:
                    self.checked_items.add(row)
                self.refresh_checkboxes()
                self.update_header_text()
            return "break"

    def toggle_select_all(self):
        items = self.cust_table.get_children()
        if len(self.checked_items) == len(items):
            self.checked_items.clear()
            self.cust_table.heading("check", text="✓")
        else:
            self.checked_items = set(items)
            self.cust_table.heading("check", text="✗")
        self.refresh_checkboxes()

    def update_header_text(self):
        items = self.cust_table.get_children()
        self.cust_table.heading(
            "check",
            text="✗"
            if len(self.checked_items) == len(items) and items
            else "✓",
        )

    def refresh_checkboxes(self):
        for item in self.cust_table.get_children():
            values = list(self.cust_table.item(item, "values"))
            values[0] = "☑" if item in self.checked_items else "☐"
            self.cust_table.item(item, values=values)

    def refresh(self):
        self.load_customers()

    def add_customer(self):
        if not self.cust_name.get():
            messagebox.showerror("Error", "Customer name required")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO customers (name, phone, phone2, phone3, address, reference, country, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                self.cust_name.get(),
                self.cust_phone.get(),
                self.cust_phone2.get(),
                self.cust_phone3.get(),
                self.cust_address.get(),
                self.cust_reference.get(),
                self.cust_country.get(),
                str(date.today()),
            ),
        )
        conn.commit()
        self.clear_fields()
        self.load_customers()
        messagebox.showinfo("Success", "Customer Added")

    def load_customers(self):
        self.cust_table.delete(*self.cust_table.get_children())
        self.checked_items.clear()
        self.cust_table.heading("check", text="✓")

        conn = self.db()
        cur = conn.cursor()
        keyword = self.cust_search_entry.get()

        if keyword:
            cur.execute(
                "SELECT id,name,phone,phone2,phone3,address,reference,country,created_at FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC",
                (f"%{keyword}%", f"%{keyword}%"),
            )
        else:
            cur.execute(
                "SELECT id,name,phone,phone2,phone3,address,reference,country,created_at FROM customers ORDER BY id DESC"
            )

        for row in cur.fetchall():
            self.cust_table.insert(
                "",
                tk.END,
                iid=row[0],
                values=(
                    "☐",
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                ),
                tags=("cust_name",),
            )

    def load_selected(self, _event):
        selected = self.cust_table.selection()
        if not selected:
            return
        row = self.cust_table.item(selected[0])["values"]
        self.selected_id = selected[0]

        self.cust_name.delete(0, tk.END)
        self.cust_name.insert(0, row[1])
        self.cust_phone.delete(0, tk.END)
        self.cust_phone.insert(0, row[2])
        self.cust_phone2.delete(0, tk.END)
        self.cust_phone2.insert(0, row[3])
        self.cust_phone3.delete(0, tk.END)
        self.cust_phone3.insert(0, row[4])
        self.cust_address.delete(0, tk.END)
        self.cust_address.insert(0, row[5])
        self.cust_reference.delete(0, tk.END)
        self.cust_reference.insert(0, row[6])
        self.cust_country.delete(0, tk.END)
        self.cust_country.insert(0, row[7])

    def update_customer(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select customer first")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE customers SET name=?, phone=?, phone2=?, phone3=?, address=?, reference=?, country=? WHERE id=?",
            (
                self.cust_name.get(),
                self.cust_phone.get(),
                self.cust_phone2.get(),
                self.cust_phone3.get(),
                self.cust_address.get(),
                self.cust_reference.get(),
                self.cust_country.get(),
                self.selected_id,
            ),
        )
        conn.commit()
        self.refresh()
        messagebox.showinfo("Updated", "Customer updated")

    def delete_selected(self):
        if not self.checked_items:
            messagebox.showwarning("Warning", "Select customers first")
            return
        confirm = messagebox.askyesno("Confirm", "Delete selected customers?")
        if not confirm:
            return
        conn = self.db()
        cur = conn.cursor()
        for item in self.checked_items:
            cur.execute("DELETE FROM customers WHERE id=?", (item,))
        conn.commit()
        self.refresh()
        messagebox.showinfo("Deleted", "Customers removed")

    def clear_fields(self):
        self.cust_name.delete(0, tk.END)
        self.cust_phone.delete(0, tk.END)
        self.cust_phone2.delete(0, tk.END)
        self.cust_phone3.delete(0, tk.END)
        self.cust_address.delete(0, tk.END)
        self.cust_reference.delete(0, tk.END)
        self.cust_country.delete(0, tk.END)
        self.selected_id = None
