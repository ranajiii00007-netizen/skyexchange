import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import styles


class BankersPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_id = None
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Bankers")

        self.main_container = styles.make_scrollable(self.frame)

        self._build_form()
        self._build_buttons()
        self._build_search()
        self._build_table()
        self.load_bankers()

    def _build_form(self):
        form_card = styles.create_card(self.main_container)
        form_card.pack(fill="x", padx=8, pady=(5, 3))
        inner = tk.Frame(form_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Banker Information",
            font=styles.AppStyles.FONTS["heading"],
            fg="#7e57c2",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w", pady=3)

        tk.Label(
            row,
            text="Name",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.name_entry = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=20, relief="solid", bd=1
        )
        self.name_entry.pack(side="left", padx=(4, 12))

        tk.Label(
            row,
            text="Phone",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.phone_entry = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=20, relief="solid", bd=1
        )
        self.phone_entry.pack(side="left", padx=(4, 12))

        tk.Label(
            row,
            text="Bank Name",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.bank_entry = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=20, relief="solid", bd=1
        )
        self.bank_entry.pack(side="left", padx=(4, 12))

        tk.Label(
            row,
            text="City",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.city_entry = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=20, relief="solid", bd=1
        )
        self.city_entry.pack(side="left", padx=(4, 0))

    def _build_buttons(self):
        btn_frame = tk.Frame(self.main_container, bg=styles.AppStyles.COLORS["light"])
        btn_frame.pack(pady=5)
        styles.styled_button(btn_frame, "Add Banker", self.add_banker, "Success").pack(
            side="left", padx=5
        )
        styles.styled_button(
            btn_frame, "Update Banker", self.update_banker, "Primary"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Delete Banker", self.delete_banker, "Danger"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Clear Form", self.clear_fields, "Secondary"
        ).pack(side="left", padx=5)

    def _build_search(self):
        search_card = styles.create_card(self.main_container)
        search_card.pack(fill="x", padx=8, pady=4)
        inner = tk.Frame(search_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            inner,
            text="Search",
            font=styles.AppStyles.FONTS["body_bold"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 8))
        self.search_entry = tk.Entry(
            inner, font=styles.AppStyles.FONTS["body"], width=22, relief="solid", bd=1
        )
        self.search_entry.pack(side="left", padx=6)
        styles.styled_button(inner, "Search", self.load_bankers, "Primary").pack(
            side="left", padx=5
        )
        styles.styled_button(inner, "Show All", self.load_bankers, "Secondary").pack(
            side="left"
        )

    def _build_table(self):
        table_card = styles.create_card(self.main_container)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Bankers List",
            font=styles.AppStyles.FONTS["heading"],
            fg="#7e57c2",
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 3))

        scrollbar_y = ttk.Scrollbar(container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.table = ttk.Treeview(
            container,
            columns=("name", "phone", "bank", "city", "status", "date"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=xscrollbar.set,
            height=14,
        )
        scrollbar_y.config(command=self.table.yview)
        xscrollbar.config(command=self.table.xview)

        self.table.heading("name", text="Name")
        self.table.heading("phone", text="Phone")
        self.table.heading("bank", text="Bank")
        self.table.heading("city", text="City")
        self.table.heading("status", text="Status")
        self.table.heading("date", text="Created At")

        self.table.column("name", width=170, anchor="w", minwidth=130)
        self.table.column("phone", width=130, anchor="center", minwidth=100)
        self.table.column("bank", width=160, anchor="w", minwidth=120)
        self.table.column("city", width=120, anchor="w", minwidth=90)
        self.table.column("status", width=80, anchor="center", minwidth=70)
        self.table.column("date", width=110, anchor="center", minwidth=100)

        self.table.tag_configure(
            "cust_name",
            background=styles.AppStyles.COLORS["customer_name_bg"],
            foreground="#1e3a8a",
        )

        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.select_row)

    def refresh(self):
        self.load_bankers()

    def add_banker(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Banker name required")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM bankers WHERE TRIM(name) = TRIM(?)", (name,))
        if cur.fetchone():
            messagebox.showwarning("Warning", "Banker already exists")
            return
        cur.execute(
            "INSERT INTO bankers (name, phone, bank_name, city, created_at) VALUES (?,?,?,?,?)",
            (
                name,
                self.phone_entry.get().strip(),
                self.bank_entry.get().strip(),
                self.city_entry.get().strip(),
                str(date.today()),
            ),
        )
        conn.commit()
        self.clear_fields()
        self.load_bankers()
        messagebox.showinfo("Success", "Banker Added")

    def update_banker(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select banker first")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE bankers SET name=?, phone=?, bank_name=?, city=? WHERE id=?",
            (
                self.name_entry.get().strip(),
                self.phone_entry.get().strip(),
                self.bank_entry.get().strip(),
                self.city_entry.get().strip(),
                self.selected_id,
            ),
        )
        conn.commit()
        self.load_bankers()
        messagebox.showinfo("Updated", "Banker updated")

    def delete_banker(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select banker first")
            return
        if not messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete this banker?"
        ):
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute("DELETE FROM bankers WHERE id=?", (self.selected_id,))
        conn.commit()
        self.selected_id = None
        self.load_bankers()
        messagebox.showinfo("Deleted", "Banker removed")

    def load_bankers(self):
        self.table.delete(*self.table.get_children())
        conn = self.db()
        cur = conn.cursor()
        keyword = self.search_entry.get()
        if keyword:
            cur.execute(
                "SELECT id, name, phone, bank_name, city, status, created_at FROM bankers WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC",
                (f"%{keyword}%", f"%{keyword}%"),
            )
        else:
            cur.execute(
                "SELECT id, name, phone, bank_name, city, status, created_at FROM bankers ORDER BY id DESC"
            )
        for row in cur.fetchall():
            self.table.insert(
                "", tk.END, iid=row[0], values=row[1:], tags=("cust_name",)
            )

    def select_row(self, _event):
        selected = self.table.selection()
        if not selected:
            return
        self.selected_id = selected[0]
        row = self.table.item(selected[0])["values"]
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, row[0])
        self.phone_entry.delete(0, tk.END)
        self.phone_entry.insert(0, row[1])
        self.bank_entry.delete(0, tk.END)
        self.bank_entry.insert(0, row[2])
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, row[3])

    def clear_fields(self):
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.bank_entry.delete(0, tk.END)
        self.city_entry.delete(0, tk.END)
        self.selected_id = None
