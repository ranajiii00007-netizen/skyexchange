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


class ReceivingPage:
    def __init__(self, notebook, db):
        self.db = db
        self.selected_id = None
        self._customer_overlays = {}

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Receiving")

        self._build_tabs()
        self._build_pending_tab()
        self._build_received_tab()

        self.load_filters()

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self.frame)
        self.tabs.pack(fill="both", expand=True)

        self.pending_tab = ttk.Frame(self.tabs)
        self.received_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.pending_tab, text="Pending")
        self.tabs.add(self.received_tab, text="Received")

    def _build_pending_tab(self):
        main_container = styles.make_scrollable(self.pending_tab)

        self._build_pending_filters(main_container)
        self._build_pending_totals(main_container)
        self._build_receive_section(main_container)
        self._build_pending_table(main_container)

    def _build_pending_filters(self, parent):
        pf = styles.create_card(parent)
        pf.pack(fill="x", padx=8, pady=(5, 3))

        inner = tk.Frame(pf, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["warning"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(fill="x")

        filters = [
            ("From", "p_from", True),
            ("To", "p_to", True),
            ("Customer", "p_customer", False),
            ("Exclude Customer", "p_exclude_customer", False),
            ("Collector", "p_collector", False),
            ("Banker", "p_banker", False),
            ("Currency", "p_currency", False),
        ]

        for text, attr, is_date in filters:
            field_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
            field_frame.pack(side="left", padx=5)

            tk.Label(
                field_frame,
                text=text,
                font=styles.AppStyles.FONTS["small"],
                fg=styles.AppStyles.COLORS["text_secondary"],
                bg=styles.AppStyles.COLORS["white"],
            ).pack(anchor="w")

            if is_date:
                entry = tk.Entry(
                    field_frame, width=12, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
                )
            else:
                entry = AutoCompleteEntry(
                    field_frame, [], clear_if_not_selected=True, width=14
                )
                entry.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])

            entry.pack(anchor="w", pady=(2, 0))
            setattr(self, attr, entry)

        btn_row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_row.pack(fill="x", pady=(5, 0))

        styles.styled_button(btn_row, "Search", self.load_pending, "Primary").pack(
            side="left", padx=3
        )
        styles.styled_button(
            btn_row, "Clear", self.clear_pending_filters, "Secondary"
        ).pack(side="left")

        qf = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        qf.pack(fill="x", pady=(5, 0))

        tk.Label(
            qf,
            text="Quick:",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 12))

        for text, cmd in [
            ("Today", self.p_today),
            ("Yesterday", self.p_yesterday),
            ("This Week", self.p_week),
            ("This Month", self.p_month),
        ]:
            styles.styled_button(qf, text, cmd, "Secondary").pack(side="left", padx=2)

    def _build_pending_totals(self, parent):
        totals = styles.create_card(parent)
        totals.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(totals, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            inner,
            text="Totals (Regular Only)",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["warning"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(5, 12))

        stats_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        stats_frame.pack(fill="x")

        stats = [
            ("Deals: 0", "p_deals", styles.AppStyles.COLORS["text_primary"]),
            ("Open Deals: 0", "p_open", styles.AppStyles.COLORS["warning"]),
            ("Closed Deals: 0", "p_closed", styles.AppStyles.COLORS["success"]),
            ("Expected €0", "p_exp", styles.AppStyles.COLORS["primary"]),
            ("Received €0", "p_rec", styles.AppStyles.COLORS["success"]),
            ("Pending €0", "p_pen", styles.AppStyles.COLORS["danger"]),
        ]

        for text, attr, color in stats:
            label = tk.Label(
                stats_frame,
                text=text,
                font=styles.AppStyles.FONTS["body_bold"],
                fg=color,
                bg=styles.AppStyles.COLORS["white"],
            )
            label.pack(side="left", padx=12)
            setattr(self, attr, label)

    def _build_receive_section(self, parent):
        receive = styles.create_card(parent)
        receive.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(receive, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Receive Payment",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["warning"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(anchor="w")

        tk.Label(
            row,
            text="Receive EUR",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 12))

        self.receive_entry = tk.Entry(
            row, width=22, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.receive_entry.pack(side="left", padx=(0, 10))

        styles.styled_button(row, "Add Payment", self.receive_payment, "Success").pack(
            side="left"
        )

    def _build_pending_table(self, parent):
        table = styles.create_card(parent)
        table.pack(fill="both", expand=True, padx=8, pady=(3, 5))

        container = tk.Frame(table, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(
            container,
            text="Pending Transactions",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["warning"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        cols = (
            "date",
            "type",
            "customer",
            "collector",
            "currency",
            "expected",
            "received",
            "pending",
        )

        pending_scroll_y = ttk.Scrollbar(container, orient="vertical")
        pending_scroll_y.pack(side="right", fill="y")
        self._init_customer_overlay("pending")

        self.pending_table = ttk.Treeview(
            container,
            columns=cols,
            show="headings",
            yscrollcommand=lambda first, last: self._sync_customer_y_scroll(
                "pending", pending_scroll_y, first, last
            ),
        )
        pending_scroll_y.config(
            command=lambda *args: self._customer_table_yview("pending", *args)
        )

        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])
        style.configure(
            "Treeview.Heading",
            background=styles.AppStyles.COLORS["header_bg"],
            foreground=styles.AppStyles.COLORS["text_primary"],
            font=styles.AppStyles.FONTS["body_bold"],
        )

        headings = {
            "date": "Date",
            "type": "Type",
            "customer": "Customer",
            "collector": "Collector",
            "currency": "Currency",
            "expected": "Expected EUR",
            "received": "Received EUR",
            "pending": "Pending EUR",
        }

        pending_col_widths = {
            "date": 90, "type": 75, "customer": 140, "collector": 110,
            "currency": 70, "expected": 100, "received": 100, "pending": 100,
        }
        for c in cols:
            self.pending_table.heading(c, text=headings[c])
            anchor = (
                "center"
                if c in ("date", "type", "currency")
                else ("e" if c in ("expected", "received", "pending") else "w")
            )
            w = pending_col_widths.get(c, 100)
            self.pending_table.column(c, width=w, anchor=anchor, minwidth=w)

        xscrollbar_p = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar_p.pack(side="bottom", fill="x")
        self.pending_table.configure(
            xscrollcommand=lambda first, last: self._sync_customer_x_scroll(
                "pending", xscrollbar_p, first, last
            )
        )
        xscrollbar_p.config(
            command=lambda *args: self._customer_table_xview("pending", *args)
        )

        self.pending_table.pack(fill="both", expand=True)
        self.pending_table.tag_configure("pending", background="#fff3cd")
        self.pending_table.bind("<<TreeviewSelect>>", self.select_row)
        self.pending_table.bind(
            "<Configure>", lambda _event: self._schedule_customer_cell_highlight("pending")
        )
        self.pending_table.bind(
            "<ButtonRelease-1>",
            lambda _event: self._schedule_customer_cell_highlight("pending"),
        )
        self.pending_table.bind(
            "<MouseWheel>", lambda _event: self._schedule_customer_cell_highlight("pending")
        )

    def _build_received_tab(self):
        main_container = styles.make_scrollable(self.received_tab)

        self._build_received_filters(main_container)
        self._build_received_totals(main_container)
        self._build_received_table(main_container)

    def _build_received_filters(self, parent):
        rf = styles.create_card(parent)
        rf.pack(fill="x", padx=8, pady=(5, 3))

        inner = tk.Frame(rf, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(
            inner,
            text="Filters",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(3, 6))

        row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row.pack(fill="x")

        filters = [
            ("Deal From", "r_from"),
            ("Deal To", "r_to"),
            ("Customer", "r_customer"),
            ("Exclude Customer", "r_exclude_customer"),
            ("Collector", "r_collector"),
            ("Banker", "r_banker"),
            ("Currency", "r_currency"),
        ]

        for text, attr in filters:
            field_frame = tk.Frame(row, bg=styles.AppStyles.COLORS["white"])
            field_frame.pack(side="left", padx=5)

            tk.Label(
                field_frame,
                text=text,
                font=styles.AppStyles.FONTS["small"],
                fg=styles.AppStyles.COLORS["text_secondary"],
                bg=styles.AppStyles.COLORS["white"],
            ).pack(anchor="w")

            is_date = "From" in text or "To" in text
            if is_date:
                entry = tk.Entry(
                    field_frame, width=12, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
                )
            else:
                entry = AutoCompleteEntry(
                    field_frame, [], clear_if_not_selected=True, width=14
                )
                entry.configure(relief="solid", bd=1, font=styles.AppStyles.FONTS["body"])

            entry.pack(anchor="w", pady=(2, 0))
            setattr(self, attr, entry)

        row2 = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        row2.pack(fill="x", pady=(8, 0))

        received_from_frame = tk.Frame(row2, bg=styles.AppStyles.COLORS["white"])
        received_from_frame.pack(side="left", padx=(5, 12))

        tk.Label(
            received_from_frame,
            text="Received From",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.r_received_from = tk.Entry(
            received_from_frame, width=12, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.r_received_from.pack(anchor="w", pady=(2, 0))

        received_to_frame = tk.Frame(row2, bg=styles.AppStyles.COLORS["white"])
        received_to_frame.pack(side="left", padx=(5, 12))

        tk.Label(
            received_to_frame,
            text="Received To",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w")

        self.r_received_to = tk.Entry(
            received_to_frame, width=12, font=styles.AppStyles.FONTS["body"], relief="solid", bd=1
        )
        self.r_received_to.pack(anchor="w", pady=(2, 0))

        btn_row = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        btn_row.pack(fill="x", pady=(8, 0))

        styles.styled_button(btn_row, "Search", self.load_received, "Primary").pack(
            side="left", padx=3
        )
        styles.styled_button(
            btn_row, "Clear", self.clear_received_filters, "Secondary"
        ).pack(side="left")

        rq = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        rq.pack(fill="x", pady=(8, 0))

        tk.Label(
            rq,
            text="Quick:",
            font=styles.AppStyles.FONTS["small"],
            fg=styles.AppStyles.COLORS["text_secondary"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(side="left", padx=(5, 12))

        for text, cmd in [
            ("Today", self.r_today),
            ("Yesterday", self.r_yesterday),
            ("This Week", self.r_week),
            ("This Month", self.r_month),
        ]:
            styles.styled_button(rq, text, cmd, "Secondary").pack(side="left", padx=2)

    def _build_received_totals(self, parent):
        rtot = styles.create_card(parent)
        rtot.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(rtot, bg=styles.AppStyles.COLORS["white"])
        inner.pack(fill="x", padx=10, pady=5)

        tk.Label(
            inner,
            text="Totals (Regular Only)",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(5, 12))

        stats_frame = tk.Frame(inner, bg=styles.AppStyles.COLORS["white"])
        stats_frame.pack(fill="x")

        stats = [
            ("Deals: 0", "r_deals", styles.AppStyles.COLORS["text_primary"]),
            ("Open Deals: 0", "r_open", styles.AppStyles.COLORS["warning"]),
            ("Closed Deals: 0", "r_closed", styles.AppStyles.COLORS["success"]),
            ("Expected €0", "r_exp", styles.AppStyles.COLORS["primary"]),
            ("Received €0", "r_rec", styles.AppStyles.COLORS["success"]),
        ]

        for text, attr, color in stats:
            label = tk.Label(
                stats_frame,
                text=text,
                font=styles.AppStyles.FONTS["body_bold"],
                fg=color,
                bg=styles.AppStyles.COLORS["white"],
            )
            label.pack(side="left", padx=12)
            setattr(self, attr, label)

    def _build_received_table(self, parent):
        rtable = styles.create_card(parent)
        rtable.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        container = tk.Frame(rtable, bg=styles.AppStyles.COLORS["white"])
        container.pack(fill="both", expand=True, padx=10, pady=15)

        tk.Label(
            container,
            text="Completed Transactions",
            font=styles.AppStyles.FONTS["heading"],
            fg=styles.AppStyles.COLORS["success"],
            bg=styles.AppStyles.COLORS["white"],
        ).pack(anchor="w", pady=(0, 5))

        cols2 = (
            "deal_date",
            "received_date",
            "type",
            "customer",
            "collector",
            "currency",
            "expected",
            "received",
        )

        received_scroll_y = ttk.Scrollbar(container, orient="vertical")
        received_scroll_y.pack(side="right", fill="y")
        self._init_customer_overlay("received")

        self.received_table = ttk.Treeview(
            container,
            columns=cols2,
            show="headings",
            yscrollcommand=lambda first, last: self._sync_customer_y_scroll(
                "received", received_scroll_y, first, last
            ),
        )
        received_scroll_y.config(
            command=lambda *args: self._customer_table_yview("received", *args)
        )

        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=styles.AppStyles.FONTS["body"])
        style.configure(
            "Treeview.Heading",
            background=styles.AppStyles.COLORS["header_bg"],
            foreground=styles.AppStyles.COLORS["text_primary"],
            font=styles.AppStyles.FONTS["body_bold"],
        )

        headings2 = {
            "deal_date": "Deal Date",
            "received_date": "Received Date",
            "type": "Type",
            "customer": "Customer",
            "collector": "Collector",
            "currency": "Currency",
            "expected": "Expected EUR",
            "received": "Received EUR",
        }

        for c in cols2:
            self.received_table.heading(c, text=headings2[c])
            anchor = (
                "center"
                if c in ("deal_date", "received_date", "type", "currency")
                else ("e" if c in ("expected", "received") else "w")
            )
            self.received_table.column(
                c,
                width=140
                if c == "customer"
                else (110 if c == "collector" else (70 if c == "currency" else 100)),
                anchor=anchor,
                minwidth=90 if c in ("customer", "collector") else 70,
            )

        xscrollbar_r = ttk.Scrollbar(container, orient="horizontal")
        xscrollbar_r.pack(side="bottom", fill="x")
        self.received_table.configure(
            xscrollcommand=lambda first, last: self._sync_customer_x_scroll(
                "received", xscrollbar_r, first, last
            )
        )
        xscrollbar_r.config(
            command=lambda *args: self._customer_table_xview("received", *args)
        )

        self.received_table.pack(fill="both", expand=True)
        self.received_table.tag_configure("closed", background="#d4edda")
        self.received_table.bind(
            "<Configure>", lambda _event: self._schedule_customer_cell_highlight("received")
        )
        self.received_table.bind(
            "<ButtonRelease-1>",
            lambda _event: self._schedule_customer_cell_highlight("received"),
        )
        self.received_table.bind(
            "<MouseWheel>",
            lambda _event: self._schedule_customer_cell_highlight("received"),
        )

    def select_row(self, _event):
        sel = self.pending_table.selection()
        if sel:
            self.selected_id = int(sel[0])

    def _init_customer_overlay(self, table_key):
        self._customer_overlays[table_key] = {
            "names": {},
            "labels": {},
            "job": None,
        }

    def _get_customer_table(self, table_key):
        return self.pending_table if table_key == "pending" else self.received_table

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
            bbox = table.bbox(row_id, "customer")
            if not bbox:
                continue

            x, y, width, height = bbox
            if width <= 0 or height <= 0:
                continue

            tags = table.item(row_id, "tags")
            bg = "#fff3cd" if "pending" in tags else "#d4edda"
            label = tk.Label(
                table,
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
        if table_key == "pending":
            self.selected_id = int(row_id)

    def receive_payment(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select transaction first")
            return

        try:
            amount = float(self.receive_entry.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid amount")
            return

        conn = self.db()
        cur = conn.cursor()

        cur.execute(
            "SELECT eur_expected, eur_received FROM transactions WHERE id=?",
            (self.selected_id,),
        )
        row = cur.fetchone()
        if not row:
            messagebox.showerror("Error", "Transaction not found")
            return

        exp, rec = row
        exp = float(exp or 0)
        rec = float(rec or 0)

        new_rec = rec + amount
        if new_rec > exp:
            messagebox.showerror("Error", "Receiving exceeds expected")
            return

        pending = exp - new_rec
        status = "CLOSED" if pending == 0 else "OPEN"

        cur.execute(
            "UPDATE transactions SET eur_received=?, pending_eur=?, status=?, received_date=? WHERE id=?",
            (new_rec, pending, status, str(date.today()), self.selected_id),
        )
        conn.commit()

        self.receive_entry.delete(0, tk.END)
        self.selected_id = None
        self.load_pending()
        self.load_received()
        messagebox.showinfo("Success", "Payment Recorded")

    def load_filters(self):
        conn = self.db()
        cur = conn.cursor()

        cur.execute("SELECT name FROM customers WHERE status=1")
        customers = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT name FROM collectors WHERE status=1")
        collectors = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT code FROM currencies WHERE status=1")
        currencies = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT name FROM bankers WHERE status=1")
        bankers = [r[0] for r in cur.fetchall()]

        self.p_customer.set_values(customers)
        self.p_exclude_customer.set_values(customers)
        self.r_customer.set_values(customers)
        self.r_exclude_customer.set_values(customers)
        self.p_collector.set_values(collectors)
        self.r_collector.set_values(collectors)
        self.p_banker.set_values(bankers)
        self.r_banker.set_values(bankers)
        self.p_currency.set_values(currencies)
        self.r_currency.set_values(currencies)

    def _pending_where_clause(self, include_status=True):
        clauses = []
        params = []
        if include_status:
            clauses.append("t.status='OPEN'")

        if self.p_from.get().strip():
            clauses.append("t.deal_date>=?")
            params.append(self.p_from.get().strip())
        if self.p_to.get().strip():
            clauses.append("t.deal_date<=?")
            params.append(self.p_to.get().strip())
        if self.p_customer.get().strip():
            clauses.append("LOWER(t.customer_name) LIKE ?")
            params.append(f"%{self.p_customer.get().strip().lower()}%")
        if self.p_exclude_customer.get().strip():
            clauses.append("LOWER(t.customer_name) NOT LIKE ?")
            params.append(f"%{self.p_exclude_customer.get().strip().lower()}%")
        if self.p_collector.get().strip():
            clauses.append("LOWER(t.collector_name) LIKE ?")
            params.append(f"%{self.p_collector.get().strip().lower()}%")
        if self.p_banker.get().strip():
            clauses.append("LOWER(t.banker_name) LIKE ?")
            params.append(f"%{self.p_banker.get().strip().lower()}%")
        if self.p_currency.get().strip():
            clauses.append("LOWER(t.target_currency) LIKE ?")
            params.append(f"%{self.p_currency.get().strip().lower()}%")

        where_clause = " AND ".join(clauses) if clauses else "1=1"
        return where_clause, params

    def _received_where_clause(self, include_status=True):
        clauses = []
        params = []
        if include_status:
            clauses.append("t.status='CLOSED'")

        if self.r_from.get().strip():
            clauses.append("t.deal_date>=?")
            params.append(self.r_from.get().strip())
        if self.r_to.get().strip():
            clauses.append("t.deal_date<=?")
            params.append(self.r_to.get().strip())
        if self.r_customer.get().strip():
            clauses.append("LOWER(t.customer_name) LIKE ?")
            params.append(f"%{self.r_customer.get().strip().lower()}%")
        if self.r_exclude_customer.get().strip():
            clauses.append("LOWER(t.customer_name) NOT LIKE ?")
            params.append(f"%{self.r_exclude_customer.get().strip().lower()}%")
        if self.r_collector.get().strip():
            clauses.append("LOWER(t.collector_name) LIKE ?")
            params.append(f"%{self.r_collector.get().strip().lower()}%")
        if self.r_banker.get().strip():
            clauses.append("LOWER(t.banker_name) LIKE ?")
            params.append(f"%{self.r_banker.get().strip().lower()}%")
        if self.r_currency.get().strip():
            clauses.append("LOWER(t.target_currency) LIKE ?")
            params.append(f"%{self.r_currency.get().strip().lower()}%")
        if self.r_received_from.get().strip():
            clauses.append("t.received_date>=?")
            params.append(self.r_received_from.get().strip())
        if self.r_received_to.get().strip():
            clauses.append("t.received_date<=?")
            params.append(self.r_received_to.get().strip())

        where_clause = " AND ".join(clauses) if clauses else "1=1"
        return where_clause, params

    def load_pending(self):
        self._clear_customer_cell_highlights("pending")
        self._customer_overlays["pending"]["names"] = {}
        self.pending_table.delete(*self.pending_table.get_children())

        conn = self.db()
        cur = conn.cursor()

        where_clause, params = self._pending_where_clause(include_status=True)
        query = (
            "SELECT t.id, t.deal_date, COALESCE(t.transaction_type, 'REGULAR') AS transaction_type, "
            "t.customer_name, t.collector_name, t.target_currency, t.eur_expected, t.eur_received, t.pending_eur "
            "FROM transactions t "
            f"WHERE {where_clause} ORDER BY t.id DESC"
        )
        cur.execute(query, params)
        rows = cur.fetchall()

        for r in rows:
            self._customer_overlays["pending"]["names"][str(r[0])] = r[3]
            values = (r[1], r[2], "", r[4], r[5], r[6], r[7], r[8])
            self.pending_table.insert(
                "", tk.END, iid=r[0], values=values, tags=("pending",)
            )
        self._schedule_customer_cell_highlight("pending")

        totals_where_clause, totals_params = self._pending_where_clause(
            include_status=False
        )
        totals_query = (
            "SELECT COUNT(*), "
            "SUM(CASE WHEN t.status='OPEN' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN t.status='CLOSED' THEN 1 ELSE 0 END), "
            "SUM(t.eur_expected), SUM(t.eur_received), SUM(t.pending_eur) "
            "FROM transactions t "
            f"WHERE {totals_where_clause} AND COALESCE(t.transaction_type, 'REGULAR')='REGULAR'"
        )
        cur.execute(totals_query, totals_params)
        deals, open_deals, closed_deals, exp, rec, pen = cur.fetchone()

        self.p_deals.config(text=f"Deals: {deals or 0}")
        self.p_open.config(text=f"Open Deals: {open_deals or 0}")
        self.p_closed.config(text=f"Closed Deals: {closed_deals or 0}")
        self.p_exp.config(text=f"Expected €{(exp or 0):,.2f}")
        self.p_rec.config(text=f"Received €{(rec or 0):,.2f}")
        self.p_pen.config(text=f"Pending €{(pen or 0):,.2f}")

    def load_received(self):
        self._clear_customer_cell_highlights("received")
        self._customer_overlays["received"]["names"] = {}
        self.received_table.delete(*self.received_table.get_children())

        conn = self.db()
        cur = conn.cursor()

        where_clause, params = self._received_where_clause(include_status=True)
        query = (
            "SELECT t.id, t.deal_date, t.received_date, COALESCE(t.transaction_type, 'REGULAR') AS transaction_type, "
            "t.customer_name, t.collector_name, t.target_currency, t.eur_expected, t.eur_received "
            "FROM transactions t "
            f"WHERE {where_clause} ORDER BY t.id DESC"
        )
        cur.execute(query, params)
        rows = cur.fetchall()

        for r in rows:
            self._customer_overlays["received"]["names"][str(r[0])] = r[4]
            values = (r[1], r[2], r[3], "", r[5], r[6], r[7], r[8])
            self.received_table.insert(
                "", tk.END, iid=r[0], values=values, tags=("closed",)
            )
        self._schedule_customer_cell_highlight("received")

        totals_where_clause, totals_params = self._received_where_clause(
            include_status=False
        )
        totals_query = (
            "SELECT COUNT(*), "
            "SUM(CASE WHEN t.status='OPEN' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN t.status='CLOSED' THEN 1 ELSE 0 END), "
            "SUM(t.eur_expected), SUM(t.eur_received) "
            "FROM transactions t "
            f"WHERE {totals_where_clause} AND COALESCE(t.transaction_type, 'REGULAR')='REGULAR'"
        )
        cur.execute(totals_query, totals_params)
        deals, open_deals, closed_deals, exp, rec = cur.fetchone()

        self.r_deals.config(text=f"Deals: {deals or 0}")
        self.r_open.config(text=f"Open Deals: {open_deals or 0}")
        self.r_closed.config(text=f"Closed Deals: {closed_deals or 0}")
        self.r_exp.config(text=f"Expected €{(exp or 0):,.2f}")
        self.r_rec.config(text=f"Received €{(rec or 0):,.2f}")

    def clear_pending_filters(self):
        self.p_from.delete(0, tk.END)
        self.p_to.delete(0, tk.END)
        self.p_customer.delete(0, tk.END)
        self.p_exclude_customer.delete(0, tk.END)
        self.p_collector.delete(0, tk.END)
        self.p_banker.delete(0, tk.END)
        self.p_currency.delete(0, tk.END)
        self.p_today()

    def clear_received_filters(self):
        self.r_from.delete(0, tk.END)
        self.r_to.delete(0, tk.END)
        self.r_customer.delete(0, tk.END)
        self.r_exclude_customer.delete(0, tk.END)
        self.r_collector.delete(0, tk.END)
        self.r_banker.delete(0, tk.END)
        self.r_currency.delete(0, tk.END)
        self.r_received_from.delete(0, tk.END)
        self.r_received_to.delete(0, tk.END)
        self.r_today()

    def p_today(self):
        today = str(date.today())
        self.p_from.delete(0, tk.END)
        self.p_to.delete(0, tk.END)
        self.p_from.insert(0, today)
        self.p_to.insert(0, today)
        self.load_pending()

    def p_yesterday(self):
        d = str(date.today() - timedelta(days=1))
        self.p_from.delete(0, tk.END)
        self.p_to.delete(0, tk.END)
        self.p_from.insert(0, d)
        self.p_to.insert(0, d)
        self.load_pending()

    def p_week(self):
        today = date.today()
        start = today - timedelta(days=today.weekday())
        self.p_from.delete(0, tk.END)
        self.p_to.delete(0, tk.END)
        self.p_from.insert(0, str(start))
        self.p_to.insert(0, str(today))
        self.load_pending()

    def p_month(self):
        today = date.today()
        start = today.replace(day=1)
        self.p_from.delete(0, tk.END)
        self.p_to.delete(0, tk.END)
        self.p_from.insert(0, str(start))
        self.p_to.insert(0, str(today))
        self.load_pending()

    def r_today(self):
        today = str(date.today())
        self.r_from.delete(0, tk.END)
        self.r_to.delete(0, tk.END)
        self.r_from.insert(0, today)
        self.r_to.insert(0, today)
        self.load_received()

    def r_yesterday(self):
        d = str(date.today() - timedelta(days=1))
        self.r_from.delete(0, tk.END)
        self.r_to.delete(0, tk.END)
        self.r_from.insert(0, d)
        self.r_to.insert(0, d)
        self.load_received()

    def r_week(self):
        today = date.today()
        start = today - timedelta(days=today.weekday())
        self.r_from.delete(0, tk.END)
        self.r_to.delete(0, tk.END)
        self.r_from.insert(0, str(start))
        self.r_to.insert(0, str(today))
        self.load_received()

    def r_month(self):
        today = date.today()
        start = today.replace(day=1)
        self.r_from.delete(0, tk.END)
        self.r_to.delete(0, tk.END)
        self.r_from.insert(0, str(start))
        self.r_to.insert(0, str(today))
        self.load_received()

    def refresh(self):
        self.load_filters()
        self.load_pending()
        self.load_received()
