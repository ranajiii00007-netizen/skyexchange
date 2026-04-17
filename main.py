import tkinter as tk
from tkinter import ttk
import database
import styles

from pages.customer_rates import CustomerCurrenciesPage
from pages.customers_page import CustomersPage
from pages.collectors_page import CollectorsPage
from pages.transactions_page import TransactionsPage
from pages.transactions_manager_page import TransactionsManagerPage
from pages.bankers_page import BankersPage
from pages.banker_details import BankerPage
from pages.receiving_page import ReceivingPage
from pages.banker_rates import BankerCurrenciesPage
from pages.reports import ReportsPage

database.create_tables()


def db():
    return database.connect_db()


root = tk.Tk()
root.title("SKY EXCHANGE")

styles.AppStyles.setup_theme(root)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.geometry(f"{screen_width}x{screen_height}")
root.state("zoomed")
root.minsize(1000, 600)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

style = ttk.Style()
style.configure(
    "TNotebook",
    background=styles.AppStyles.COLORS["light"],
    tabmargins=[2, 5, 0, 0],
)

style.configure(
    "TNotebook.Tab",
    font=("Segoe UI", 9, "bold"),
    foreground=styles.AppStyles.COLORS["text_secondary"],
    background=styles.AppStyles.COLORS["light"],
    padding=[10, 5],
    relief="flat",
)

style.map(
    "TNotebook.Tab",
    background=[
        ("selected", styles.AppStyles.COLORS["white"]),
        ("active", styles.AppStyles.COLORS["hover"]),
    ],
    foreground=[
        ("selected", styles.AppStyles.COLORS["primary"]),
        ("active", styles.AppStyles.COLORS["text_primary"]),
    ],
)

pages = {}

pages["Currencies"] = CustomerCurrenciesPage(notebook, db)
pages["Customers"] = CustomersPage(notebook, db)
pages["Collectors"] = CollectorsPage(notebook, db)

pages["Transactions"] = TransactionsPage(notebook, db)

pages["Receiving"] = ReceivingPage(notebook, db)

pages["Manage Transactions"] = TransactionsManagerPage(notebook, db)

pages["Bankers"] = BankersPage(notebook, db)

pages["Banker Details"] = BankerPage(notebook, db)
pages["Banker Currency Rates"] = BankerCurrenciesPage(notebook, db)

pages["Reports"] = ReportsPage(notebook, db)


def on_tab_change(event):
    selected_tab = notebook.select()
    tab_text = notebook.tab(selected_tab, "text")

    print("Active tab:", tab_text)

    page = pages.get(tab_text)

    if page and hasattr(page, "refresh"):
        try:
            page.refresh()
        except Exception as e:
            print("Refresh error:", e)


notebook.bind("<<NotebookTabChanged>>", on_tab_change)


try:
    root.mainloop()

except Exception as e:
    import traceback

    traceback.print_exc()
