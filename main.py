import tkinter as tk
from tkinter import messagebox, ttk
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

try:
    database.create_tables()
except Exception as exc:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Database Configuration", str(exc))
    root.destroy()
    raise SystemExit(1) from exc


def db():
    # Reuse the shared PostgreSQL connection for normal app activity.
    # Opening a fresh SSL connection on every page refresh makes the UI feel slow.
    return database.connect_db(reuse_postgres=True)


root = tk.Tk()
root.title("SKY EXCHANGE")

styles.AppStyles.setup_theme(root)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.geometry(f"{screen_width}x{screen_height}")
root.state("zoomed")
root.minsize(1000, 600)

status_var = tk.StringVar(value="")
status_frame = tk.Frame(root, bg=styles.AppStyles.COLORS["light"])
status_frame.pack(fill="x", side="top")

status_bar = tk.Label(
    status_frame,
    textvariable=status_var,
    anchor="w",
    padx=12,
    pady=6,
    font=styles.AppStyles.FONTS["small"],
    fg=styles.AppStyles.COLORS["text_secondary"],
    bg=styles.AppStyles.COLORS["light"],
)
status_bar.pack(side="left", fill="x", expand=True)

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

_refresh_job = None
SYNC_CHECK_INTERVAL_MS = 30000
page_refresh_state = {
    name: {
        "dirty": False,
    }
    for name in pages
}
last_seen_revision = database.get_app_revision()
external_change_detected = False


def refresh_current_page():
    global _refresh_job

    selected_tab = notebook.select()
    if not selected_tab:
        return

    tab_text = notebook.tab(selected_tab, "text")
    page = pages.get(tab_text)
    if not (page and hasattr(page, "refresh")):
        return

    if _refresh_job is not None:
        root.after_cancel(_refresh_job)
        _refresh_job = None

    set_status(f"Refreshing {tab_text}...", temporary=True)
    try:
        page.refresh()
        mark_pages_fresh(tab_text)
    except Exception as exc:
        print("Manual refresh error:", exc)
    finally:
        update_idle_status()


refresh_button = tk.Button(
    status_frame,
    text="Refresh Current Page",
    command=refresh_current_page,
    font=styles.AppStyles.FONTS["small_bold"],
    bg=styles.AppStyles.COLORS["secondary"],
    fg=styles.AppStyles.COLORS["white"],
    activebackground=styles.AppStyles.COLORS["dark_secondary"],
    activeforeground=styles.AppStyles.COLORS["white"],
    relief="flat",
    bd=0,
    padx=10,
    pady=4,
    cursor="hand2",
)
refresh_button.pack(side="right", padx=(0, 10), pady=4)


def set_status(message="", temporary=False):
    if temporary:
        status_var.set(message)
        root.update_idletasks()
        return
    status_var.set(message)
    root.update_idletasks()


def update_idle_status():
    global external_change_detected

    if external_change_detected and any(
        state["dirty"] for state in page_refresh_state.values()
    ):
        set_status("Shared data changed on another PC. Open the page or click Refresh.")
        return

    if not any(state["dirty"] for state in page_refresh_state.values()):
        external_change_detected = False

    set_status("")


def mark_pages_dirty(*page_names):
    for page_name in page_names:
        if page_name in page_refresh_state:
            page_refresh_state[page_name]["dirty"] = True
    update_idle_status()


def mark_pages_fresh(page_name):
    if page_name in page_refresh_state:
        page_refresh_state[page_name]["dirty"] = False
    update_idle_status()


def should_refresh_page(page_name):
    state = page_refresh_state.get(page_name)
    if not state:
        return False
    return state["dirty"]


def wrap_page_mutation(page_name, method_name, dirty_targets):
    page = pages.get(page_name)
    if not page or not hasattr(page, method_name):
        return

    original_method = getattr(page, method_name)

    def wrapped(*args, **kwargs):
        global last_seen_revision

        result = original_method(*args, **kwargs)
        mark_pages_dirty(*dirty_targets)
        try:
            last_seen_revision = database.bump_app_revision()
        except Exception as exc:
            print("Revision bump error:", exc)
        return result

    setattr(page, method_name, wrapped)


def setup_dirty_tracking():
    transaction_targets = (
        "Transactions",
        "Receiving",
        "Manage Transactions",
        "Banker Details",
        "Reports",
    )
    rate_targets = (
        "Transactions",
        "Banker Details",
        "Reports",
    )
    master_data_targets = (
        "Transactions",
        "Receiving",
        "Manage Transactions",
        "Banker Details",
        "Reports",
    )

    wrap_page_mutation("Transactions", "save_deal", transaction_targets)
    wrap_page_mutation("Transactions", "delete_transaction", transaction_targets)

    wrap_page_mutation("Receiving", "receive_payment", transaction_targets)

    wrap_page_mutation(
        "Manage Transactions", "update_transaction", transaction_targets
    )
    wrap_page_mutation(
        "Manage Transactions", "delete_transaction", transaction_targets
    )

    wrap_page_mutation("Banker Details", "pay_banker", ("Banker Details", "Reports"))
    wrap_page_mutation(
        "Banker Details", "_update_payment_amount", ("Banker Details", "Reports")
    )

    wrap_page_mutation("Currencies", "save_customer_rate", rate_targets)
    wrap_page_mutation("Currencies", "add_currency", rate_targets)
    wrap_page_mutation("Currencies", "delete_selected", rate_targets)
    wrap_page_mutation("Banker Currency Rates", "save_rate", rate_targets)
    wrap_page_mutation("Banker Currency Rates", "delete_selected", rate_targets)

    wrap_page_mutation("Customers", "add_customer", master_data_targets)
    wrap_page_mutation("Customers", "update_customer", master_data_targets)
    wrap_page_mutation("Customers", "delete_selected", master_data_targets)
    wrap_page_mutation("Collectors", "add_collector", master_data_targets)
    wrap_page_mutation("Collectors", "update_collector", master_data_targets)
    wrap_page_mutation("Collectors", "delete_selected", master_data_targets)
    wrap_page_mutation("Bankers", "add_banker", master_data_targets)
    wrap_page_mutation("Bankers", "update_banker", master_data_targets)
    wrap_page_mutation("Bankers", "delete_banker", master_data_targets)


setup_dirty_tracking()


def check_shared_data_changes():
    global last_seen_revision, external_change_detected

    try:
        current_revision = database.get_app_revision()
        if current_revision != last_seen_revision:
            last_seen_revision = current_revision
            external_change_detected = True
            mark_pages_dirty(*pages.keys())
    except Exception as exc:
        print("Shared data check error:", exc)
    finally:
        root.after(SYNC_CHECK_INTERVAL_MS, check_shared_data_changes)


def on_tab_change(event):
    global _refresh_job

    selected_tab = notebook.select()
    tab_text = notebook.tab(selected_tab, "text")

    print("Active tab:", tab_text)

    page = pages.get(tab_text)

    if _refresh_job is not None:
        root.after_cancel(_refresh_job)
        _refresh_job = None

    if not (page and hasattr(page, "refresh")):
        update_idle_status()
        return

    if not should_refresh_page(tab_text):
        update_idle_status()
        return

    set_status(f"Loading {tab_text}...", temporary=True)

    def run_refresh():
        global _refresh_job
        try:
            page.refresh()
            mark_pages_fresh(tab_text)
        except Exception as e:
            print("Refresh error:", e)
        finally:
            update_idle_status()
            _refresh_job = None

    # Let Tkinter render the new tab first, then do the page refresh work.
    _refresh_job = root.after(60, run_refresh)


notebook.bind("<<NotebookTabChanged>>", on_tab_change)
root.after(SYNC_CHECK_INTERVAL_MS, check_shared_data_changes)

try:
    root.mainloop()

except Exception as e:
    import traceback

    traceback.print_exc()
