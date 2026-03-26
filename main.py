from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
LOW_STOCK = 5

# ── Colors ──────────────────────────────
BG    = (0.95, 0.95, 0.95, 1)
WHITE = (1,    1,    1,    1)
BLUE  = (0.13, 0.46, 0.84, 1)
DBLUE = (0.08, 0.30, 0.60, 1)
RED   = (0.85, 0.2,  0.2,  1)
GREEN = (0.18, 0.65, 0.35, 1)
DARK  = (0.1,  0.1,  0.1,  1)
YELLOW= (0.75, 0.55, 0.0,  1)
GREY  = (0.5,  0.5,  0.5,  1)
ROW1  = (1,    1,    1,    1)
ROW2  = (0.91, 0.94, 1,    1)
ROWLO = (1,    0.85, 0.85, 1)
PURPLE= (0.45, 0.18, 0.65, 1)

# ── Helpers ─────────────────────────────
def bg_rect(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, v: setattr(rect, 'pos', v),
                size=lambda w, v: setattr(rect, 'size', v))

def make_input(hint, password=False, numeric=False):
    return TextInput(
        hint_text=hint, multiline=False, password=password,
        input_filter="float" if numeric else None,
        size_hint_y=None, height=dp(42), font_size=dp(16),
        background_color=(0.85, 0.85, 0.85, 1), foreground_color=(0, 0, 0, 1),
        hint_text_color=(0.2, 0.2, 0.2, 1),
        cursor_color=BLUE, padding=[dp(10), dp(11)]
    )

def make_btn(text, color, cb, width=None):
    b = Button(text=text, size_hint_y=None, height=dp(44),
               background_color=color, color=WHITE,
               font_size=dp(16), bold=True)
    if width:
        b.size_hint_x = None
        b.width = width
    b.bind(on_release=cb)
    return b

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def show_msg(title, msg):
    content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
    bg_rect(content, (0.96, 0.96, 0.96, 1))
    lbl = Label(text=msg, color=DARK, font_size=dp(14),
                halign="center", valign="middle",
                text_size=(dp(280), None))
    content.add_widget(lbl)
    btn = make_btn("OK", BLUE, lambda x: popup.dismiss())
    content.add_widget(btn)
    popup = Popup(title=title, content=content,
                  size_hint=(0.85, 0.42), title_color=DARK)
    popup.open()

# ── Database ────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role     TEXT DEFAULT 'user'
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS categories (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        category_id INTEGER,
        quantity    INTEGER DEFAULT 0,
        price       REAL,
        supplier    TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        type       TEXT,
        quantity   INTEGER,
        note       TEXT,
        date       TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")
    # Default admin
    try:
        conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                     ("admin", hash_pw("admin123"), "admin"))
    except:
        pass
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

# ════════════════════════════════════════
#  LOGIN SCREEN
# ════════════════════════════════════════
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        bg_rect(root, BG)

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(80))
        bg_rect(header, BLUE)
        header.add_widget(Label(text="Inventory Manager", font_size=dp(24),
                                bold=True, color=WHITE))
        root.add_widget(header)

        # Spacer
        root.add_widget(BoxLayout(size_hint_y=0.2))

        # Card
        card = BoxLayout(orientation="vertical", size_hint=(0.85, None),
                         height=dp(300), spacing=dp(12),
                         padding=dp(24), pos_hint={"center_x": 0.5})
        bg_rect(card, WHITE)

        card.add_widget(Label(text="Sign In", font_size=dp(20),
                              bold=True, color=DARK,
                              size_hint_y=None, height=dp(36)))

        self.u_input = make_input("Username")
        self.p_input = make_input("Password", password=True)
        card.add_widget(self.u_input)
        card.add_widget(self.p_input)
        card.add_widget(make_btn("Login", BLUE, self.do_login))

        self.msg_lbl = Label(text="", color=RED, font_size=dp(13),
                             size_hint_y=None, height=dp(28))
        card.add_widget(self.msg_lbl)
        root.add_widget(card)
        root.add_widget(BoxLayout(size_hint_y=1))
        self.add_widget(root)

    def do_login(self, *args):
        u = self.u_input.text.strip()
        p = self.p_input.text.strip()
        if not u or not p:
            self.msg_lbl.text = "Please enter username and password."
            return
        conn = get_conn()
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE username=? AND password=?",
            (u, hash_pw(p))
        ).fetchone()
        conn.close()
        if row:
            self.manager.current = "home"
            self.manager.get_screen("home").set_user(row[1], row[2])
            self.u_input.text = ""
            self.p_input.text = ""
            self.msg_lbl.text = ""
        else:
            self.msg_lbl.text = "Invalid username or password."

# ════════════════════════════════════════
#  HOME SCREEN
# ════════════════════════════════════════
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_row = None
        self.current_user = ""
        self.current_role = ""
        self.build_ui()

    def set_user(self, username, role):
        self.current_user = username
        self.current_role = role
        self.user_lbl.text = f"User: {username} ({role})"
        self.load_products()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(6))
        bg_rect(root, BG)

        # ── Top bar ──
        topbar = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(8), dp(6)],
                           spacing=dp(6))
        bg_rect(topbar, BLUE)
        topbar.add_widget(Label(text="Inventory Manager", font_size=dp(18),
                                bold=True, color=WHITE, size_hint_x=0.4))
        self.user_lbl = Label(text="", font_size=dp(12), color=WHITE, size_hint_x=0.3)
        topbar.add_widget(self.user_lbl)

        for txt, col, cb in [
            ("Low Stock", YELLOW,  lambda x: self.show_low_stock()),
            ("Reports",   PURPLE,  lambda x: self.manager.current == "reports" or setattr(self.manager, "current", "reports")),
            ("Logout",    RED,     lambda x: self.do_logout()),
        ]:
            b = make_btn(txt, col, cb, width=dp(90))
            topbar.add_widget(b)
        root.add_widget(topbar)

        # ── Tab buttons ──
        tabs = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for txt, col, cb in [
            ("Products",    BLUE,   lambda x: self.show_tab("products")),
            ("Categories",  DBLUE,  lambda x: self.show_tab("categories")),
            ("Transactions",GREY,   lambda x: self.show_tab("transactions")),
        ]:
            tabs.add_widget(make_btn(txt, col, cb))
        root.add_widget(tabs)

        # ── Search ──
        self.search = TextInput(
            hint_text="Search...", multiline=False,
            size_hint_y=None, height=dp(38), font_size=dp(13),
            background_color=(0.9, 0.9, 0.9, 1), foreground_color=(0, 0, 0, 1),
            padding=[dp(8), dp(10)]
        )
        self.search.bind(text=lambda i, v: self.load_products())
        root.add_widget(self.search)

        # ── Table header ──
        self.header = GridLayout(cols=5, size_hint_y=None, height=dp(34), spacing=dp(1))
        bg_rect(self.header, BLUE)
        for col in ["Name", "Category", "Qty", "Price (K)", "Supplier"]:
            self.header.add_widget(Label(text=col, bold=True, color=WHITE, font_size=dp(12)))
        root.add_widget(self.header)

        # ── List ──
        scroll = ScrollView(size_hint=(1, 1))
        self.list_layout = GridLayout(cols=5, spacing=dp(1), size_hint_y=None,
                                      row_default_height=dp(34))
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)

        # ── Product form ──
        self.product_form = self.build_product_form()
        root.add_widget(self.product_form)

        # ── Category form (hidden initially) ──
        self.category_form = self.build_category_form()
        self.category_form.opacity = 0
        self.category_form.disabled = True
        root.add_widget(self.category_form)

        # ── Transaction form (hidden initially) ──
        self.transaction_form = self.build_transaction_form()
        self.transaction_form.opacity = 0
        self.transaction_form.disabled = True
        root.add_widget(self.transaction_form)

        self.add_widget(root)
        self.current_tab = "products"

    def build_product_form(self):
        form = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(150), spacing=dp(4))
        form.add_widget(Label(text="Product Details", size_hint_y=None,
                              height=dp(22), color=DARK, bold=True, font_size=dp(12)))
        r1 = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        self.f_name     = make_input("Product Name *")
        self.f_category = make_input("Category")
        r1.add_widget(self.f_name)
        r1.add_widget(self.f_category)
        form.add_widget(r1)

        r2 = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        self.f_qty      = make_input("Quantity *",  numeric=True)
        self.f_price    = make_input("Price (K) *", numeric=True)
        self.f_supplier = make_input("Supplier")
        r2.add_widget(self.f_qty)
        r2.add_widget(self.f_price)
        r2.add_widget(self.f_supplier)
        form.add_widget(r2)

        btns = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(42))
        btns.add_widget(make_btn("Add",    GREEN, lambda x: self.add_product()))
        btns.add_widget(make_btn("Update", BLUE,  lambda x: self.update_product()))
        btns.add_widget(make_btn("Delete", RED,   lambda x: self.delete_product()))
        btns.add_widget(make_btn("Clear",  DARK,  lambda x: self.clear_product_form()))
        form.add_widget(btns)
        return form

    def build_category_form(self):
        form = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(100), spacing=dp(4))
        form.add_widget(Label(text="Category Management", size_hint_y=None,
                              height=dp(22), color=DARK, bold=True, font_size=dp(12)))
        r1 = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        self.c_name = make_input("Category Name *")
        r1.add_widget(self.c_name)
        form.add_widget(r1)
        btns = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(42))
        btns.add_widget(make_btn("Add Category",    GREEN, lambda x: self.add_category()))
        btns.add_widget(make_btn("Delete Category", RED,   lambda x: self.delete_category()))
        btns.add_widget(make_btn("Clear",           DARK,  lambda x: setattr(self.c_name, 'text', '')))
        form.add_widget(btns)
        return form

    def build_transaction_form(self):
        form = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(100), spacing=dp(4))
        form.add_widget(Label(text="Stock In / Out", size_hint_y=None,
                              height=dp(22), color=DARK, bold=True, font_size=dp(12)))
        r1 = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        self.t_qty  = make_input("Quantity *", numeric=True)
        self.t_note = make_input("Note (optional)")
        r1.add_widget(self.t_qty)
        r1.add_widget(self.t_note)
        form.add_widget(r1)
        btns = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(42))
        btns.add_widget(make_btn("Stock IN",  GREEN, lambda x: self.do_transaction("IN")))
        btns.add_widget(make_btn("Stock OUT", RED,   lambda x: self.do_transaction("OUT")))
        form.add_widget(btns)
        return form

    # ── TABS ──────────────────────────────
    def show_tab(self, tab):
        self.current_tab = tab
        self.product_form.opacity    = 1 if tab == "products"     else 0
        self.product_form.disabled   = tab != "products"
        self.category_form.opacity   = 1 if tab == "categories"   else 0
        self.category_form.disabled  = tab != "categories"
        self.transaction_form.opacity= 1 if tab == "transactions" else 0
        self.transaction_form.disabled= tab != "transactions"

        # Update header and list
        for col_widget in self.header.children:
            self.header.remove_widget(col_widget)

        if tab == "products":
            self.header.cols = 5
            for col in ["Name", "Category", "Qty", "Price (K)", "Supplier"]:
                self.header.add_widget(Label(text=col, bold=True, color=WHITE, font_size=dp(12)))
            self.load_products()
        elif tab == "categories":
            self.header.cols = 2
            for col in ["ID", "Category Name"]:
                self.header.add_widget(Label(text=col, bold=True, color=WHITE, font_size=dp(12)))
            self.load_categories()
        elif tab == "transactions":
            self.header.cols = 5
            for col in ["Product", "Type", "Qty", "Note", "Date"]:
                self.header.add_widget(Label(text=col, bold=True, color=WHITE, font_size=dp(12)))
            self.load_transactions()

    # ── PRODUCTS ──────────────────────────
    def load_products(self):
        if self.current_tab != "products":
            return
        self.list_layout.cols = 5
        self.list_layout.clear_widgets()
        search = self.search.text.strip()
        conn = get_conn()
        q = """SELECT p.id, p.name, IFNULL(c.name,'-'), p.quantity, p.price, IFNULL(p.supplier,'-')
               FROM products p LEFT JOIN categories c ON p.category_id=c.id
               WHERE p.name LIKE ? OR p.supplier LIKE ?"""
        rows = conn.execute(q, (f"%{search}%", f"%{search}%")).fetchall()
        conn.close()
        for i, row in enumerate(rows):
            pid, name, cat, qty, price, sup = row
            low = qty <= LOW_STOCK
            bg  = ROWLO if low else (ROW1 if i % 2 == 0 else ROW2)
            for v in [name, cat, str(qty), f"K{price:.2f}", sup]:
                cell = BoxLayout()
                bg_rect(cell, bg)
                lbl = Label(text=str(v), color=(0, 0, 0, 1), font_size=dp(15),
                            halign="center", valign="middle")
                lbl.bind(size=lbl.setter("text_size"))
                cell.add_widget(lbl)
                cell.bind(on_touch_down=lambda w, t, r=row:
                          self.select_product(r) if w.collide_point(*t.pos) else None)
                self.list_layout.add_widget(cell)

    def select_product(self, row):
        self.selected_row = row
        self.f_name.text     = row[1]
        conn = get_conn()
        cat = conn.execute("SELECT name FROM categories WHERE id=?",
                           (row[2] if len(row) > 2 else 0,)).fetchone()
        conn.close()
        self.f_category.text = cat[0] if cat else ""
        self.f_qty.text      = str(row[3])
        self.f_price.text    = str(row[4])
        self.f_supplier.text = row[5] if row[5] != "-" else ""

    def get_product_vals(self):
        name  = self.f_name.text.strip()
        cat_n = self.f_category.text.strip()
        sup   = self.f_supplier.text.strip()
        qty_s = self.f_qty.text.strip()
        pri_s = self.f_price.text.strip()
        if not name or not qty_s or not pri_s:
            show_msg("Validation", "Name, Quantity and Price are required.")
            return None
        try:
            qty   = int(float(qty_s))
            price = float(pri_s)
        except ValueError:
            show_msg("Validation", "Quantity and Price must be numbers.")
            return None
        conn = get_conn()
        cat_row = conn.execute("SELECT id FROM categories WHERE name=?", (cat_n,)).fetchone()
        cat_id = cat_row[0] if cat_row else None
        conn.close()
        return (name, cat_id, qty, price, sup)

    def add_product(self):
        vals = self.get_product_vals()
        if not vals:
            return
        conn = get_conn()
        conn.execute("INSERT INTO products (name,category_id,quantity,price,supplier) VALUES (?,?,?,?,?)", vals)
        conn.commit()
        conn.close()
        self.load_products()
        self.clear_product_form()
        show_msg("Success", "Product added!")

    def update_product(self):
        if not self.selected_row:
            show_msg("Select", "Click a product row first.")
            return
        vals = self.get_product_vals()
        if not vals:
            return
        conn = get_conn()
        conn.execute("UPDATE products SET name=?,category_id=?,quantity=?,price=?,supplier=? WHERE id=?",
                     (*vals, self.selected_row[0]))
        conn.commit()
        conn.close()
        self.selected_row = None
        self.load_products()
        self.clear_product_form()
        show_msg("Success", "Product updated!")

    def delete_product(self):
        if not self.selected_row:
            show_msg("Select", "Click a product row first.")
            return
        conn = get_conn()
        conn.execute("DELETE FROM products WHERE id=?", (self.selected_row[0],))
        conn.commit()
        conn.close()
        self.selected_row = None
        self.load_products()
        self.clear_product_form()

    def clear_product_form(self):
        for f in [self.f_name, self.f_category, self.f_qty, self.f_price, self.f_supplier]:
            f.text = ""
        self.selected_row = None

    # ── CATEGORIES ────────────────────────
    def load_categories(self):
        self.list_layout.cols = 2
        self.list_layout.clear_widgets()
        conn = get_conn()
        rows = conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
        conn.close()
        for i, row in enumerate(rows):
            bg = ROW1 if i % 2 == 0 else ROW2
            for v in [str(row[0]), row[1]]:
                cell = BoxLayout()
                bg_rect(cell, bg)
                lbl = Label(text=v, color=DARK, font_size=dp(13),
                            halign="center", valign="middle")
                lbl.bind(size=lbl.setter("text_size"))
                cell.add_widget(lbl)
                cell.bind(on_touch_down=lambda w, t, r=row:
                          setattr(self.c_name, 'text', r[1]) if w.collide_point(*t.pos) else None)
                self.list_layout.add_widget(cell)

    def add_category(self):
        name = self.c_name.text.strip()
        if not name:
            show_msg("Validation", "Category name is required.")
            return
        try:
            conn = get_conn()
            conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
            self.c_name.text = ""
            self.load_categories()
            show_msg("Success", f"Category '{name}' added!")
        except:
            show_msg("Error", "Category already exists.")

    def delete_category(self):
        name = self.c_name.text.strip()
        if not name:
            show_msg("Select", "Click a category row first.")
            return
        conn = get_conn()
        conn.execute("DELETE FROM categories WHERE name=?", (name,))
        conn.commit()
        conn.close()
        self.c_name.text = ""
        self.load_categories()

    # ── TRANSACTIONS ──────────────────────
    def load_transactions(self):
        self.list_layout.cols = 5
        self.list_layout.clear_widgets()
        conn = get_conn()
        rows = conn.execute("""
            SELECT p.name, t.type, t.quantity, IFNULL(t.note,'-'), t.date
            FROM transactions t JOIN products p ON t.product_id=p.id
            ORDER BY t.id DESC LIMIT 100
        """).fetchall()
        conn.close()
        for i, row in enumerate(rows):
            bg = ROW1 if i % 2 == 0 else ROW2
            for j, v in enumerate(row):
                cell = BoxLayout()
                bg_rect(cell, bg)
                color = GREEN if (j == 1 and v == "IN") else RED if (j == 1 and v == "OUT") else DARK
                lbl = Label(text=str(v), color=color, font_size=dp(11),
                            halign="center", valign="middle")
                lbl.bind(size=lbl.setter("text_size"))
                cell.add_widget(lbl)
                self.list_layout.add_widget(cell)

    def do_transaction(self, t_type):
        if not self.selected_row:
            show_msg("Select", "Click a product row in Products tab first.")
            return
        qty_s = self.t_qty.text.strip()
        note  = self.t_note.text.strip()
        if not qty_s:
            show_msg("Validation", "Quantity is required.")
            return
        qty = int(float(qty_s))
        conn = get_conn()
        current_qty = conn.execute("SELECT quantity FROM products WHERE id=?",
                                   (self.selected_row[0],)).fetchone()[0]
        if t_type == "OUT" and qty > current_qty:
            conn.close()
            show_msg("Error", f"Not enough stock! Current qty: {current_qty}")
            return
        new_qty = current_qty + qty if t_type == "IN" else current_qty - qty
        conn.execute("UPDATE products SET quantity=? WHERE id=?",
                     (new_qty, self.selected_row[0]))
        conn.execute("INSERT INTO transactions (product_id,type,quantity,note,date) VALUES (?,?,?,?,?)",
                     (self.selected_row[0], t_type, qty, note,
                      datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        self.t_qty.text  = ""
        self.t_note.text = ""
        self.load_products()
        show_msg("Success", f"Stock {t_type}: {qty} units.\nNew quantity: {new_qty}")

    # ── LOW STOCK ─────────────────────────
    def show_low_stock(self):
        conn = get_conn()
        rows = conn.execute(
            "SELECT name, quantity FROM products WHERE quantity <= ?", (LOW_STOCK,)
        ).fetchall()
        conn.close()
        if not rows:
            msg = "All products are well stocked!"
        else:
            msg = "Low Stock Items:\n\n" + "\n".join(f"{r[0]} - Qty: {r[1]}" for r in rows)
        show_msg("Low Stock Alert", msg)

    def do_logout(self):
        self.manager.current = "login"

# ════════════════════════════════════════
#  REPORTS SCREEN
# ════════════════════════════════════════
class ReportsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        bg_rect(root, BG)

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(8), dp(6)])
        bg_rect(header, PURPLE)
        header.add_widget(Label(text="Reports", font_size=dp(20), bold=True, color=WHITE))
        header.add_widget(make_btn("Back", BLUE, lambda x: setattr(self.manager, "current", "home"),
                                   width=dp(80)))
        root.add_widget(header)

        # Report buttons
        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        btns.add_widget(make_btn("Stock Value",      BLUE,   lambda x: self.show_stock_value()))
        btns.add_widget(make_btn("Low Stock Report", RED,    lambda x: self.show_low_stock()))
        btns.add_widget(make_btn("Category Summary", DBLUE,  lambda x: self.show_category_summary()))
        root.add_widget(btns)

        # Report header
        self.report_header = GridLayout(cols=3, size_hint_y=None, height=dp(34), spacing=dp(1))
        bg_rect(self.report_header, BLUE)
        root.add_widget(self.report_header)

        # Report table
        scroll = ScrollView(size_hint=(1, 1))
        self.report_list = GridLayout(cols=3, spacing=dp(1), size_hint_y=None,
                                      row_default_height=dp(34))
        self.report_list.bind(minimum_height=self.report_list.setter("height"))
        scroll.add_widget(self.report_list)
        root.add_widget(scroll)

        # Summary label
        self.summary_lbl = Label(text="", color=DARK, font_size=dp(14),
                                 bold=True, size_hint_y=None, height=dp(36))
        root.add_widget(self.summary_lbl)

        self.add_widget(root)

    def set_header(self, cols):
        for w in list(self.report_header.children):
            self.report_header.remove_widget(w)
        self.report_header.cols = len(cols)
        self.report_list.cols   = len(cols)
        for col in cols:
            self.report_header.add_widget(
                Label(text=col, bold=True, color=WHITE, font_size=dp(12)))

    def add_rows(self, rows):
        self.report_list.clear_widgets()
        for i, row in enumerate(rows):
            bg = ROW1 if i % 2 == 0 else ROW2
            for v in row:
                cell = BoxLayout()
                bg_rect(cell, bg)
                lbl = Label(text=str(v), color=DARK, font_size=dp(12),
                            halign="center", valign="middle")
                lbl.bind(size=lbl.setter("text_size"))
                cell.add_widget(lbl)
                self.report_list.add_widget(cell)

    def show_stock_value(self):
        self.set_header(["Product", "Qty", "Value (K)"])
        conn = get_conn()
        rows = conn.execute(
            "SELECT name, quantity, ROUND(quantity*price,2) FROM products ORDER BY quantity*price DESC"
        ).fetchall()
        total = conn.execute("SELECT ROUND(SUM(quantity*price),2) FROM products").fetchone()[0]
        conn.close()
        self.add_rows(rows)
        self.summary_lbl.text = f"Total Stock Value: K{total or 0:.2f}"

    def show_low_stock(self):
        self.set_header(["Product", "Category", "Qty"])
        conn = get_conn()
        rows = conn.execute("""
            SELECT p.name, IFNULL(c.name,'-'), p.quantity
            FROM products p LEFT JOIN categories c ON p.category_id=c.id
            WHERE p.quantity <= ? ORDER BY p.quantity
        """, (LOW_STOCK,)).fetchall()
        conn.close()
        self.add_rows(rows)
        self.summary_lbl.text = f"Low Stock Items: {len(rows)}"

    def show_category_summary(self):
        self.set_header(["Category", "Products", "Total Value (K)"])
        conn = get_conn()
        rows = conn.execute("""
            SELECT IFNULL(c.name,'Uncategorized'),
                   COUNT(p.id),
                   ROUND(SUM(p.quantity*p.price),2)
            FROM products p LEFT JOIN categories c ON p.category_id=c.id
            GROUP BY p.category_id
        """).fetchall()
        conn.close()
        self.add_rows(rows)
        self.summary_lbl.text = f"Total Categories: {len(rows)}"

# ════════════════════════════════════════
#  APP
# ════════════════════════════════════════
class InventoryApp(App):
    def build(self):
        init_db()
        from kivy.core.window import Window
        Window.clearcolor = BG
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(ReportsScreen(name="reports"))
        return sm

if __name__ == "__main__":
    InventoryApp().run()
