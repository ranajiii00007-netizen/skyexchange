import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import styles


class CollectorsPage:
    def __init__(self, notebook, db):
        self.db = db
        self.checked_items = set()

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Collectors")

        self.main_container = styles.make_scrollable(self.frame)

        self._build_form()
        self._build_buttons()
        self._build_search()
        self._build_table()

        self.load_collectors()

    def _build_form(self):
        form_card = styles.create_card(self.main_container)
        form_card.pack(fill="x", padx=8, pady=(5, 3))
        inner = tk.Frame(form_card, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Collector Details",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["info"],
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
            text="Area",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 4))
        self.area_entry = tk.Entry(
            row, font=styles.AppStyles.FONTS["body"], width=20, relief="solid", bd=1
        )
        self.area_entry.pack(side="left", padx=(4, 0))

    def _build_buttons(self):
        btn_frame = tk.Frame(self.main_container, bg=styles.AppStyles.COLORS["light"])
        btn_frame.pack(pady=5)
        styles.styled_button(
            btn_frame, "Add Collector", self.add_collector, "Success"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Update Collector", self.update_collector, "Primary"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Delete Selected", self.delete_selected, "Danger"
        ).pack(side="left", padx=5)
        styles.styled_button(
            btn_frame, "Clear Form", self.clear_form, "Secondary"
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

        styles.styled_button(inner, "Search", self.load_collectors, "Primary").pack(
            side="left", padx=5
        )
        styles.styled_button(inner, "Clear", self.load_collectors, "Secondary").pack(
            side="left"
        )

    def _build_table(self):
        table_card = styles.create_card(self.main_container)
        table_card.pack(fill="both", expand=True, padx=8, pady=(3, 5))
        container = tk.Frame(table_card, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Collectors List",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["info"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 3))

        scrollbar_y = ttk.Scrollbar(container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar.pack(side="bottom", fill="x")

        self.table = ttk.Treeview(
            container,
            columns=("check", "name", "phone", "area", "date"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=xscrollbar.set,
            height=14,
        )
        scrollbar_y.config(command=self.table.yview)
        xscrollbar.config(command=self.table.xview)

        self.table.heading("check", text="✓")
        self.table.heading("name", text="Name")
        self.table.heading("phone", text="Phone")
        self.table.heading("area", text="Area")
        self.table.heading("date", text="Created")

        self.table.column("check", width=40, anchor="center", minwidth=40)
        self.table.column("name", width=200, anchor="w", minwidth=150)
        self.table.column("phone", width=130, anchor="center", minwidth=100)
        self.table.column("area", width=160, anchor="w", minwidth=120)
        self.table.column("date", width=110, anchor="center", minwidth=100)

        self.table.tag_configure(
            "cust_name",
            background=styles.AppStyles.COLORS["customer_name_bg"],
            foreground="#1e3a8a",
        )

        self.table.pack(fill="both", expand=True)
        self.table.bind("<Button-1>", self.handle_click)
        self.table.bind("<<TreeviewSelect>>", self.select_row)

    def handle_click(self, event):
        region = self.table.identify("region", event.x, event.y)
        column = self.table.identify_column(event.x)
        if region == "heading" and column == "#1":
            self.toggle_select_all()
            return "break"
        if region == "cell" and column == "#1":
            row = self.table.identify_row(event.y)
            if row:
                if row in self.checked_items:
                    self.checked_items.remove(row)
                else:
                    self.checked_items.add(row)
                self.refresh_checkboxes()
                self.update_header_text()
            return "break"

    def toggle_select_all(self):
        items = self.table.get_children()
        if len(self.checked_items) == len(items):
            self.checked_items.clear()
            self.table.heading("check", text="✓")
        else:
            self.checked_items = set(items)
            self.table.heading("check", text="✗")
        self.refresh_checkboxes()

    def update_header_text(self):
        items = self.table.get_children()
        self.table.heading(
            "check",
            text="✗"
            if len(self.checked_items) == len(items) and items
            else "✓",
        )

    def refresh_checkboxes(self):
        for item in self.table.get_children():
            values = list(self.table.item(item, "values"))
            values[0] = "☑" if item in self.checked_items else "☐"
            self.table.item(item, values=values)

    def add_collector(self):
        if not self.name_entry.get():
            messagebox.showerror("Error", "Collector name required")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO collectors (name, phone, area, created_at) VALUES (?, ?, ?, ?)",
            (
                self.name_entry.get(),
                self.phone_entry.get(),
                self.area_entry.get(),
                str(date.today()),
            ),
        )
        conn.commit()
        self.clear_form()
        self.load_collectors()
        messagebox.showinfo("Success", "Collector Added")

    def update_collector(self):
        selected = self.table.focus()
        if not selected:
            messagebox.showerror("Error", "Select collector to update")
            return
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE collectors SET name = ?, phone = ?, area = ? WHERE id = ?",
            (
                self.name_entry.get(),
                self.phone_entry.get(),
                self.area_entry.get(),
                selected,
            ),
        )
        conn.commit()
        self.clear_form()
        self.load_collectors()
        messagebox.showinfo("Updated", "Collector Updated")

    def delete_selected(self):
        if not self.checked_items:
            messagebox.showerror("Error", "No collectors selected")
            return
        confirm = messagebox.askyesno("Confirm", "Delete selected collectors?")
        if not confirm:
            return
        conn = self.db()
        cur = conn.cursor()
        for item in self.checked_items:
            cur.execute("DELETE FROM collectors WHERE id = ?", (item,))
        conn.commit()
        self.checked_items.clear()
        self.load_collectors()
        messagebox.showinfo("Deleted", "Collectors removed")

    def load_collectors(self):
        self.table.delete(*self.table.get_children())
        self.checked_items.clear()
        self.table.heading("check", text="✓")

        conn = self.db()
        cur = conn.cursor()
        keyword = self.search_entry.get()

        if keyword:
            cur.execute(
                "SELECT id, name, phone, area, created_at FROM collectors WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC",
                (f"%{keyword}%", f"%{keyword}%"),
            )
        else:
            cur.execute(
                "SELECT id, name, phone, area, created_at FROM collectors ORDER BY id DESC"
            )

        for row in cur.fetchall():
            self.table.insert(
                "",
                tk.END,
                iid=str(row[0]),
                values=("☐", row[1], row[2], row[3], row[4]),
                tags=("cust_name",),
            )

    def select_row(self, _event):
        selected = self.table.focus()
        if not selected:
            return
        values = self.table.item(selected, "values")
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.area_entry.delete(0, tk.END)
        self.name_entry.insert(0, values[1])
        self.phone_entry.insert(0, values[2])
        self.area_entry.insert(0, values[3])

    def clear_form(self):
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.area_entry.delete(0, tk.END)
