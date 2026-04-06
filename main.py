import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import csv
from PIL import Image, ImageTk
from database import (
    create_database,
    insert_default_users,
    check_user,
    add_product,
    get_products,
    update_product,
    delete_product,
    get_sales,
    get_sales_summary,
    get_sales_by_product,
    record_sale,
    cancel_sale,
    get_users,
    add_user,
    delete_user,
)

# ── Colour palette ────────────────────────────────────────────────────────────
MAIN_BG       = "#f5f0e8"
SIDEBAR_BG    = "#ffffff"
SIDEBAR_HOVER = "#fdf6ec"
CARD_BG       = "#ffffff"
PRIMARY       = "#c9a96e"   # gold
PRIMARY_DARK  = "#a8823d"
SUCCESS       = "#6aaa64"
WARNING       = "#e8a838"
DANGER        = "#e06464"
TEXT_DARK     = "#2c2417"
TEXT_MUTED    = "#8c7b6b"
TEXT_LIGHT    = "#ffffff"
BORDER        = "#e8dfd0"
SIDEBAR_TEXT  = "#5c4a32"

LOW_STOCK_THRESHOLD = 5
LOGO_PATH = "WhatsApp Image 2026-04-06 at 15.43.14.jpeg"
# ─────────────────────────────────────────────────────────────────────────────


class StoreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StockStyle — Store Management")
        self.root.geometry("1150x720")
        self.root.minsize(950, 620)
        self.root.configure(bg=MAIN_BG)

        self.sidebar      = None
        self.content_area = None
        self.current_user = None
        self.current_role = None
        self._logo_photo  = None
        self._sb_logo     = None

        # Cart state for cashier
        self.cart = {}   # {product_id: {"name": ..., "price": ..., "qty": ...}}

        self._style_ttk()
        self.show_login_screen()

    # ── TTK styling ───────────────────────────────────────────────────────────

    def _style_ttk(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=CARD_BG, foreground=TEXT_DARK,
                        rowheight=28, fieldbackground=CARD_BG,
                        font=("Arial", 10))
        style.configure("Treeview.Heading",
                        background=PRIMARY, foreground=TEXT_LIGHT,
                        font=("Arial", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", PRIMARY)],
                              foreground=[("selected", TEXT_LIGHT)])
        style.configure("TCombobox", padding=5)
        style.configure("Gold.TButton",
                        background=PRIMARY, foreground=TEXT_LIGHT,
                        font=("Arial", 10, "bold"))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.sidebar = self.content_area = None

    def _clear_content(self):
        if self.content_area:
            for w in self.content_area.winfo_children():
                w.destroy()

    @staticmethod
    def _darken(hex_color, factor=0.88):
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return "#{:02x}{:02x}{:02x}".format(int(r*factor), int(g*factor), int(b*factor))

    def _btn(self, parent, text, command, color=None, fg=TEXT_LIGHT, **kw):
        if color is None:
            color = PRIMARY
        b = tk.Button(parent, text=text, command=command,
                      bg=color, fg=fg, activebackground=self._darken(color),
                      activeforeground=fg, font=("Arial", 10, "bold"),
                      bd=0, relief="flat", padx=18, pady=8, cursor="hand2", **kw)
        b.bind("<Enter>", lambda e: b.config(bg=self._darken(color)))
        b.bind("<Leave>", lambda e: b.config(bg=color))
        return b

    def _card(self, parent, **kw):
        return tk.Frame(parent, bg=CARD_BG, bd=0,
                        highlightthickness=1, highlightbackground=BORDER, **kw)

    def _page_title(self, parent, text, subtitle=""):
        hdr = tk.Frame(parent, bg=MAIN_BG)
        hdr.pack(fill="x", padx=30, pady=(24, 0))
        tk.Label(hdr, text=text, font=("Georgia", 20, "bold"),
                 bg=MAIN_BG, fg=TEXT_DARK).pack(anchor="w")
        if subtitle:
            tk.Label(hdr, text=subtitle, font=("Arial", 10),
                     bg=MAIN_BG, fg=TEXT_MUTED).pack(anchor="w", pady=(2, 0))
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=30, pady=(10, 18))

    def _stat_card(self, parent, label, value, color=PRIMARY):
        f = tk.Frame(parent, bg=CARD_BG, padx=22, pady=16,
                     highlightthickness=1, highlightbackground=BORDER)
        f.pack(side="left", padx=(0, 14), fill="x", expand=True)
        tk.Label(f, text=label, font=("Arial", 9), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        tk.Label(f, text=value, font=("Arial", 18, "bold"),
                 bg=CARD_BG, fg=color).pack(anchor="w", pady=(4, 0))
        return f

    def _load_logo(self, width=140, bg_color=None):
        try:
            img = Image.open(LOGO_PATH).convert("RGBA")
            # Replace white/near-white pixels with the given background color
            if bg_color:
                r_bg, g_bg, b_bg = (int(bg_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                data = img.getdata()
                new_data = []
                for r, g, b, a in data:
                    if r > 220 and g > 215 and b > 205:
                        new_data.append((r_bg, g_bg, b_bg, 255))
                    else:
                        new_data.append((r, g, b, a))
                img.putdata(new_data)
            img = img.convert("RGB")
            ratio = width / img.width
            img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    # ── Sidebar layout ────────────────────────────────────────────────────────

    def _setup_layout(self, role):
        self._clear_root()
        self.current_role = role
        self.cart = {}

        outer = tk.Frame(self.root, bg=MAIN_BG)
        outer.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(outer, bg=SIDEBAR_BG, width=210,
                                highlightthickness=1, highlightbackground=BORDER)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content_area = tk.Frame(outer, bg=MAIN_BG)
        self.content_area.pack(side="left", fill="both", expand=True)

        self._build_sidebar(role)

    def _build_sidebar(self, role):
        sb = self.sidebar

        # Logo area
        logo_frame = tk.Frame(sb, bg=SIDEBAR_BG, height=110)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        self._sb_logo = self._load_logo(width=130, bg_color=SIDEBAR_BG)
        if self._sb_logo:
            tk.Label(logo_frame, image=self._sb_logo,
                     bg=SIDEBAR_BG).pack(pady=12)
        else:
            tk.Label(logo_frame, text="StockStyle",
                     font=("Georgia", 16, "bold"),
                     bg=SIDEBAR_BG, fg=PRIMARY).pack(pady=30)

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=16, pady=2)

        # Nav items
        if role == "admin":
            items = [
                ("Dashboard",        self.show_dashboard),
                ("Manage Products",  self.show_manage_products),
                ("Sales",            self.show_sales_screen),
                ("Charts",           self.show_reports_screen),
                ("Reports",          self.show_reports_list),
                ("Export Data",      self.show_export_screen),
                ("User Management",  self.show_user_management),
            ]
        else:
            items = [
                ("Dashboard",    self.show_dashboard),
                ("Products",     self.show_products_screen),
                ("Sales / Cart", self.show_cashier_cart),
            ]

        for text, cmd in items:
            self._nav_btn(sb, text, cmd)

        # Logout
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=16, side="bottom", pady=6)
        lo = tk.Button(sb, text="  Logout", anchor="w",
                       font=("Arial", 10), bg=SIDEBAR_BG, fg=DANGER,
                       activebackground="#fff0f0", activeforeground=DANGER,
                       bd=0, relief="flat", padx=20, pady=12, cursor="hand2",
                       command=self.show_login_screen)
        lo.pack(fill="x", side="bottom")
        lo.bind("<Enter>", lambda e: lo.config(bg="#fff0f0"))
        lo.bind("<Leave>", lambda e: lo.config(bg=SIDEBAR_BG))

    def _nav_btn(self, parent, text, command):
        b = tk.Button(parent, text=f"  {text}", anchor="w",
                      font=("Arial", 10), bg=SIDEBAR_BG, fg=SIDEBAR_TEXT,
                      activebackground=SIDEBAR_HOVER, activeforeground=TEXT_DARK,
                      bd=0, relief="flat", padx=16, pady=11, cursor="hand2",
                      command=command)
        b.pack(fill="x")
        b.bind("<Enter>", lambda e: b.config(bg=SIDEBAR_HOVER))
        b.bind("<Leave>", lambda e: b.config(bg=SIDEBAR_BG))

    # ── Login ─────────────────────────────────────────────────────────────────

    def show_login_screen(self):
        self._clear_root()
        self.root.configure(bg=MAIN_BG)

        outer = tk.Frame(self.root, bg=MAIN_BG)
        outer.pack(fill="both", expand=True)

        # ── Left: logo centered ──────────────────────────────────────────────
        left = tk.Frame(outer, bg=MAIN_BG)
        left.pack(side="left", fill="both", expand=True)

        logo_wrap = tk.Frame(left, bg=MAIN_BG)
        logo_wrap.place(relx=0.65, rely=0.5, anchor="center")

        logo_ph = self._load_logo(width=420, bg_color=MAIN_BG)
        if logo_ph:
            self._logo_photo = logo_ph
            tk.Label(logo_wrap, image=self._logo_photo, bg=MAIN_BG).pack()
        else:
            tk.Label(logo_wrap, text="Stock", font=("Georgia", 36, "bold"),
                     bg=MAIN_BG, fg=TEXT_DARK).pack()
            tk.Label(logo_wrap, text="Style", font=("Georgia", 36, "bold"),
                     bg=MAIN_BG, fg=PRIMARY).pack()

        # ── Right: login form ────────────────────────────────────────────────
        right = tk.Frame(outer, bg=MAIN_BG)
        right.pack(side="right", fill="both", expand=True)

        form_wrap = tk.Frame(right, bg=MAIN_BG)
        form_wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(form_wrap, text="Log in",
                 font=("Georgia", 30, "bold"),
                 bg=MAIN_BG, fg=TEXT_DARK).pack(anchor="w", pady=(0, 28))

        # Email field
        email_frame = tk.Frame(form_wrap, bg=CARD_BG,
                               highlightthickness=1, highlightbackground=BORDER)
        email_frame.pack(fill="x", pady=(0, 12), ipady=2)
        tk.Label(email_frame, text=" ✉  ", font=("Arial", 12),
                 bg=CARD_BG, fg=TEXT_MUTED).pack(side="left", padx=(10, 0))
        self.username_entry = tk.Entry(email_frame, font=("Arial", 11), width=28,
                                       bg=CARD_BG, fg=TEXT_MUTED, relief="flat",
                                       insertbackground=TEXT_DARK)
        self.username_entry.insert(0, "Email")
        self.username_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(4, 10))

        def on_email_focus_in(e):
            if self.username_entry.get() == "Email":
                self.username_entry.delete(0, tk.END)
                self.username_entry.config(fg=TEXT_DARK)

        def on_email_focus_out(e):
            if not self.username_entry.get():
                self.username_entry.insert(0, "Email")
                self.username_entry.config(fg=TEXT_MUTED)

        self.username_entry.bind("<FocusIn>",  on_email_focus_in)
        self.username_entry.bind("<FocusOut>", on_email_focus_out)

        # Password field
        pwd_frame = tk.Frame(form_wrap, bg=CARD_BG,
                             highlightthickness=1, highlightbackground=BORDER)
        pwd_frame.pack(fill="x", pady=(0, 6), ipady=2)
        tk.Label(pwd_frame, text=" 🔒  ", font=("Arial", 11),
                 bg=CARD_BG, fg=TEXT_MUTED).pack(side="left", padx=(10, 0))
        self.password_entry = tk.Entry(pwd_frame, font=("Arial", 11), width=28,
                                        bg=CARD_BG, fg=TEXT_MUTED, relief="flat",
                                        insertbackground=TEXT_DARK)
        self.password_entry.insert(0, "Password")
        self.password_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(4, 10))

        def on_pwd_focus_in(e):
            if self.password_entry.get() == "Password":
                self.password_entry.delete(0, tk.END)
                self.password_entry.config(show="*", fg=TEXT_DARK)

        def on_pwd_focus_out(e):
            if not self.password_entry.get():
                self.password_entry.config(show="")
                self.password_entry.insert(0, "Password")
                self.password_entry.config(fg=TEXT_MUTED)

        self.password_entry.bind("<FocusIn>",  on_pwd_focus_in)
        self.password_entry.bind("<FocusOut>", on_pwd_focus_out)

        # Forgot password
        tk.Label(form_wrap, text="Forgot password?",
                 font=("Arial", 10), bg=MAIN_BG, fg=PRIMARY,
                 cursor="hand2").pack(anchor="e", pady=(2, 20))

        # Login button
        self.username_entry.bind("<Return>", lambda _: self.login())
        self.password_entry.bind("<Return>", lambda _: self.login())

        login_btn = tk.Button(form_wrap, text="Log in",
                              command=self.login,
                              font=("Arial", 12, "bold"),
                              bg=PRIMARY, fg=TEXT_LIGHT,
                              activebackground=PRIMARY_DARK,
                              activeforeground=TEXT_LIGHT,
                              bd=0, relief="flat", cursor="hand2",
                              width=32, pady=12)
        login_btn.pack(fill="x")
        login_btn.bind("<Enter>", lambda e: login_btn.config(bg=PRIMARY_DARK))
        login_btn.bind("<Leave>", lambda e: login_btn.config(bg=PRIMARY))

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if username == "Email":
            username = ""
        if password == "Password":
            password = ""
        role = check_user(username, password)
        if role == "admin":
            self.current_user = username
            self._setup_layout("admin")
            self.show_dashboard()
        elif role == "cashier":
            self.current_user = username
            self._setup_layout("cashier")
            self.show_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def show_dashboard(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, f"Welcome, {self.current_user.capitalize()}",
                         "Here's an overview of your stock & sales performance.")

        # Stat cards
        total_rev, total_cnt, top_name, top_qty = get_sales_summary()
        products = get_products()

        strip = tk.Frame(c, bg=MAIN_BG)
        strip.pack(fill="x", padx=30, pady=(0, 20))

        self._stat_card(strip, "Total Products", str(len(products)), color=PRIMARY)
        self._stat_card(strip, "Total Sales",    str(total_cnt),     color="#3b82f6")
        self._stat_card(strip, "Total Revenue",  f"{total_rev:.2f} ₺", color=SUCCESS)
        self._stat_card(strip, "Top Product",    top_name,           color=WARNING)

        # Recent sales
        recent_card = self._card(c)
        recent_card.pack(padx=30, fill="both", expand=True)

        hdr = tk.Frame(recent_card, bg=CARD_BG, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Recent Sales", font=("Arial", 13, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left")

        tf = tk.Frame(recent_card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        cols = ("ID", "Product ID", "Qty", "Total", "Date", "Sold By")
        tree = ttk.Treeview(tf, columns=cols, show="headings", height=10)
        for col, w in zip(cols, [60, 90, 60, 110, 180, 110]):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=w)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for s in reversed(get_sales()[-20:]):
            tree.insert("", tk.END, values=s)

    # ── Manage Products ───────────────────────────────────────────────────────

    def show_manage_products(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Manage Products")

        # Stat cards
        products = get_products()
        total    = len(products)
        low      = len([p for p in products if p[4] <= LOW_STOCK_THRESHOLD])
        priciest = max(products, key=lambda p: p[3]) if products else None

        strip = tk.Frame(c, bg=MAIN_BG)
        strip.pack(fill="x", padx=30, pady=(0, 18))
        self._stat_card(strip, "Total Products",  str(total), color=PRIMARY)
        self._stat_card(strip, "Low Stock Items", str(low),   color=DANGER)
        self._stat_card(strip, "Most Expensive",
                        f"{priciest[1]}  —  {priciest[3]:.2f} ₺" if priciest else "—",
                        color=WARNING)

        # Add form
        card = self._card(c)
        card.pack(padx=30, fill="x")

        form = tk.Frame(card, bg=CARD_BG, padx=30, pady=26)
        form.pack(fill="x")

        tk.Label(form, text="Add New Product", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(
                     row=0, column=0, columnspan=4, sticky="w", pady=(0, 16))

        field_defs = [("Product Name", "name"), ("Category", "cat"),
                      ("Price (₺)", "price"), ("Stock Qty", "stock")]
        entries = {}
        for i, (lbl, key) in enumerate(field_defs):
            col = (i % 2) * 2
            row = (i // 2) * 2 + 1
            tk.Label(form, text=lbl, font=("Arial", 10, "bold"),
                     bg=CARD_BG, fg=TEXT_DARK).grid(
                         row=row, column=col, sticky="w", padx=(0, 40), pady=(8, 2))
            e = tk.Entry(form, font=("Arial", 10), width=26,
                         bg="#faf8f4", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK)
            e.grid(row=row+1, column=col, sticky="ew", padx=(0, 40), ipady=6)
            entries[key] = e

        def add_action():
            name, cat = entries["name"].get().strip(), entries["cat"].get().strip()
            price_t, stock_t = entries["price"].get().strip(), entries["stock"].get().strip()
            if not name:
                messagebox.showerror("Validation", "Name is required.")
                return
            try:
                price = float(price_t) if price_t else 0.0
            except ValueError:
                messagebox.showerror("Validation", "Price must be a number.")
                return
            try:
                stock = int(stock_t) if stock_t else 0
            except ValueError:
                messagebox.showerror("Validation", "Stock must be an integer.")
                return
            add_product(name, cat, price, stock)
            messagebox.showinfo("Success", f'"{name}" added successfully.')
            for e in entries.values():
                e.delete(0, tk.END)

        btn_row = tk.Frame(card, bg=CARD_BG, padx=30, pady=(0, 22))
        btn_row.pack(fill="x")
        self._btn(btn_row, "+ Add New Product", add_action, color=PRIMARY).pack(side="left")

        # Products table
        list_card = self._card(c)
        list_card.pack(padx=30, pady=(16, 0), fill="both", expand=True)

        hdr_row = tk.Frame(list_card, bg=CARD_BG, padx=20, pady=12)
        hdr_row.pack(fill="x")
        tk.Label(hdr_row, text="All Products", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left")

        tf = tk.Frame(list_card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        cols = ("ID", "Name", "Category", "Price", "Stock", "Actions")
        tree = ttk.Treeview(tf, columns=cols, show="headings", height=8)
        for col, w in zip(cols, [50, 180, 140, 100, 80, 120]):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=w)
        tree.tag_configure("low_stock", background="#fef3c7", foreground="#92400e")

        sb2 = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb2.set)
        tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        def load_products():
            tree.delete(*tree.get_children())
            for p in get_products():
                tag = ("low_stock",) if p[4] <= LOW_STOCK_THRESHOLD else ()
                tree.insert("", tk.END,
                            values=(p[0], p[1], p[2], f"{p[3]:.2f} ₺", p[4], "Edit | Delete"),
                            tags=tag)

        load_products()

        def edit_product():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Please select a product.")
                return
            vals = tree.item(sel, "values")
            pid = int(vals[0])

            dlg = tk.Toplevel(self.root)
            dlg.title("Edit Product")
            dlg.geometry("360x300")
            dlg.configure(bg=CARD_BG)
            dlg.grab_set()

            fields = [("Name", vals[1]), ("Category", vals[2]),
                      ("Price", vals[3].replace(" ₺", "")), ("Stock", vals[4])]
            d_entries = {}
            for i, (lbl, val) in enumerate(fields):
                tk.Label(dlg, text=lbl, font=("Arial", 10, "bold"),
                         bg=CARD_BG, fg=TEXT_DARK).grid(
                             row=i*2, column=0, sticky="w", padx=24, pady=(14, 2))
                e = tk.Entry(dlg, font=("Arial", 10), width=28,
                             bg="#faf8f4", fg=TEXT_DARK, relief="solid", bd=1,
                             insertbackground=TEXT_DARK)
                e.insert(0, val)
                e.grid(row=i*2+1, column=0, padx=24, sticky="ew", ipady=5)
                d_entries[lbl] = e

            def save():
                try:
                    np = float(d_entries["Price"].get().strip())
                    ns = int(d_entries["Stock"].get().strip())
                except ValueError:
                    messagebox.showerror("Validation", "Invalid price or stock.")
                    return
                update_product(pid, d_entries["Name"].get().strip(),
                               d_entries["Category"].get().strip(), np, ns)
                dlg.destroy()
                load_products()

            self._btn(dlg, "Save Changes", save, color=PRIMARY).grid(
                row=len(fields)*2, column=0, pady=16, padx=24, sticky="ew", ipady=4)

        def del_product():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Please select a product.")
                return
            vals = tree.item(sel, "values")
            if messagebox.askyesno("Confirm", f'Delete "{vals[1]}"?'):
                delete_product(int(vals[0]))
                load_products()

        act_row = tk.Frame(list_card, bg=CARD_BG, padx=20, pady=(0, 14))
        act_row.pack(fill="x")
        self._btn(act_row, "Edit", edit_product, color=WARNING, fg=TEXT_DARK).pack(side="left", padx=(0, 10))
        self._btn(act_row, "Delete", del_product, color=DANGER).pack(side="left")

    # ── Products (view only) ──────────────────────────────────────────────────

    def show_products_screen(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Products")

        products = get_products()
        low = [p for p in products if p[4] <= LOW_STOCK_THRESHOLD]
        if low:
            banner = tk.Frame(c, bg="#fef3c7",
                              highlightthickness=1, highlightbackground="#fbbf24")
            banner.pack(fill="x", padx=30, pady=(0, 12))
            tk.Label(banner,
                     text=f"  ⚠  {len(low)} product(s) have low stock (≤ {LOW_STOCK_THRESHOLD})",
                     font=("Arial", 10, "bold"), bg="#fef3c7", fg="#92400e",
                     pady=8).pack(anchor="w")

        card = self._card(c)
        card.pack(padx=30, fill="both", expand=True)

        search_frame = tk.Frame(card, bg=CARD_BG, padx=20, pady=12)
        search_frame.pack(fill="x")
        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left", padx=(0, 8))
        search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=search_var, font=("Arial", 10), width=30,
                 bg="#faf8f4", fg=TEXT_DARK, relief="solid", bd=1,
                 insertbackground=TEXT_DARK).pack(side="left", ipady=4)

        tf = tk.Frame(card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        cols = ("ID", "Name", "Category", "Price", "Stock")
        tree = ttk.Treeview(tf, columns=cols, show="headings")
        for col, w in zip(cols, [60, 200, 160, 110, 80]):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=w)
        tree.tag_configure("low_stock", background="#fef3c7", foreground="#92400e")

        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def load(filter_text=""):
            tree.delete(*tree.get_children())
            for p in products:
                if filter_text.lower() in p[1].lower() or \
                   filter_text.lower() in (p[2] or "").lower():
                    tag = ("low_stock",) if p[4] <= LOW_STOCK_THRESHOLD else ()
                    tree.insert("", tk.END,
                                values=(p[0], p[1], p[2], f"{p[3]:.2f} ₺", p[4]),
                                tags=tag)

        load()
        search_var.trace_add("write", lambda *_: load(search_var.get()))

    # ── Cashier Cart ──────────────────────────────────────────────────────────

    def show_cashier_cart(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Sales / Cart")

        outer = tk.Frame(c, bg=MAIN_BG)
        outer.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Left: product list
        left = tk.Frame(outer, bg=MAIN_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))

        search_frame = tk.Frame(left, bg=MAIN_BG)
        search_frame.pack(fill="x", pady=(0, 10))
        search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=search_var, font=("Arial", 10), width=30,
                 bg=CARD_BG, fg=TEXT_DARK, relief="solid", bd=1,
                 insertbackground=TEXT_DARK,
                 ).pack(side="left", fill="x", expand=True, ipady=6)

        product_list_frame = self._card(left)
        product_list_frame.pack(fill="both", expand=True)

        pl_inner = tk.Frame(product_list_frame, bg=CARD_BG)
        pl_inner.pack(fill="both", expand=True, padx=12, pady=12)

        canvas = tk.Canvas(pl_inner, bg=CARD_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(pl_inner, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=CARD_BG)

        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        products = get_products()

        def render_products(filter_text=""):
            for w in scroll_frame.winfo_children():
                w.destroy()
            filtered = [p for p in products
                        if filter_text.lower() in p[1].lower() or
                        filter_text.lower() in (p[2] or "").lower()]
            for p in filtered:
                row = tk.Frame(scroll_frame, bg=CARD_BG, pady=6,
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", pady=3, padx=4)

                info = tk.Frame(row, bg=CARD_BG)
                info.pack(side="left", fill="x", expand=True, padx=10)
                tk.Label(info, text=p[1], font=("Arial", 10, "bold"),
                         bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w")
                tk.Label(info, text=f"{p[3]:.2f} ₺  |  {p[4]} in stock",
                         font=("Arial", 9), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")

                def make_add(prod=p):
                    def add_to_cart():
                        pid = prod[0]
                        if pid in self.cart:
                            if self.cart[pid]["qty"] >= prod[4]:
                                messagebox.showwarning("Stock", "Not enough stock.")
                                return
                            self.cart[pid]["qty"] += 1
                        else:
                            self.cart[pid] = {"name": prod[1], "price": prod[3], "qty": 1}
                        refresh_cart()
                    return add_to_cart

                self._btn(row, "Add", make_add(), color=PRIMARY,
                          padx=12, pady=4).pack(side="right", padx=10)

        search_var.trace_add("write", lambda *_: render_products(search_var.get()))
        render_products()

        # Right: cart
        right = tk.Frame(outer, bg=MAIN_BG, width=280)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        cart_card = self._card(right)
        cart_card.pack(fill="both", expand=True)

        cart_hdr = tk.Frame(cart_card, bg=CARD_BG, padx=16, pady=12)
        cart_hdr.pack(fill="x")
        tk.Label(cart_hdr, text="Cart", font=("Arial", 13, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left")

        cart_body = tk.Frame(cart_card, bg=CARD_BG)
        cart_body.pack(fill="both", expand=True, padx=14, pady=6)

        total_lbl = tk.Label(cart_card, text="Total  $0.00",
                             font=("Arial", 14, "bold"),
                             bg=CARD_BG, fg=TEXT_DARK)
        total_lbl.pack(pady=(4, 8))

        def refresh_cart():
            for w in cart_body.winfo_children():
                w.destroy()
            total = 0.0
            for pid, item in self.cart.items():
                subtotal = item["price"] * item["qty"]
                total += subtotal

                row = tk.Frame(cart_body, bg=CARD_BG)
                row.pack(fill="x", pady=4)

                info = tk.Frame(row, bg=CARD_BG)
                info.pack(side="left", fill="x", expand=True)
                tk.Label(info, text=item["name"], font=("Arial", 9, "bold"),
                         bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w")
                tk.Label(info, text=f"{item['price']:.2f} ₺",
                         font=("Arial", 9), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")

                qty_frame = tk.Frame(row, bg=CARD_BG)
                qty_frame.pack(side="right")

                def make_dec(p=pid):
                    def dec():
                        if self.cart[p]["qty"] > 1:
                            self.cart[p]["qty"] -= 1
                        else:
                            del self.cart[p]
                        refresh_cart()
                    return dec

                def make_inc(p=pid, prod_stock=None):
                    def inc():
                        # find current stock
                        prods = get_products()
                        for pp in prods:
                            if pp[0] == p:
                                if self.cart[p]["qty"] >= pp[4]:
                                    messagebox.showwarning("Stock", "Not enough stock.")
                                    return
                                break
                        self.cart[p]["qty"] += 1
                        refresh_cart()
                    return inc

                tk.Button(qty_frame, text="−", font=("Arial", 10, "bold"),
                          bg=BORDER, fg=TEXT_DARK, bd=0, relief="flat",
                          width=2, cursor="hand2",
                          command=make_dec(pid)).pack(side="left")
                tk.Label(qty_frame, text=str(item["qty"]), font=("Arial", 10, "bold"),
                         bg=CARD_BG, fg=TEXT_DARK, width=3).pack(side="left")
                tk.Button(qty_frame, text="+", font=("Arial", 10, "bold"),
                          bg=BORDER, fg=TEXT_DARK, bd=0, relief="flat",
                          width=2, cursor="hand2",
                          command=make_inc(pid)).pack(side="left")

                tk.Label(cart_body, text=f"  {subtotal:.2f} ₺",
                         font=("Arial", 9), bg=CARD_BG,
                         fg=TEXT_MUTED).pack(anchor="e")

            total_lbl.config(text=f"Total  {total:.2f} ₺")

        def complete_sale():
            if not self.cart:
                messagebox.showwarning("Cart", "Cart is empty.")
                return
            errors = []
            for pid, item in self.cart.items():
                result = record_sale(pid, item["qty"], sold_by=self.current_user)
                if result != "Sale recorded successfully":
                    errors.append(f"{item['name']}: {result}")
            if errors:
                messagebox.showerror("Errors", "\n".join(errors))
            else:
                messagebox.showinfo("Success", "Sale completed successfully!")
                self.cart = {}
                refresh_cart()
                render_products(search_var.get())

        self._btn(cart_card, "Complete Sale", complete_sale,
                  color=PRIMARY).pack(fill="x", padx=14, pady=(0, 14), ipady=6)

        def clear_cart():
            self.cart = {}
            refresh_cart()

        self._btn(cart_card, "Clear Cart", clear_cart,
                  color=DANGER).pack(fill="x", padx=14, pady=(0, 14), ipady=4)

        refresh_cart()

    # ── Admin Sales screen ────────────────────────────────────────────────────

    def show_sales_screen(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Sales Management")

        total_rev, total_cnt, top_name, _ = get_sales_summary()
        strip = tk.Frame(c, bg=MAIN_BG)
        strip.pack(fill="x", padx=30, pady=(0, 18))
        self._stat_card(strip, "Total Revenue", f"{total_rev:.2f} ₺", color=SUCCESS)
        self._stat_card(strip, "Total Sales",   str(total_cnt),        color="#3b82f6")
        self._stat_card(strip, "Top Product",   top_name,              color=WARNING)

        hist_card = self._card(c)
        hist_card.pack(padx=30, fill="both", expand=True)

        filter_row = tk.Frame(hist_card, bg=CARD_BG, padx=20, pady=12)
        filter_row.pack(fill="x")
        tk.Label(filter_row, text="Sales History", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left", padx=(0, 20))

        for lbl in ("From:", "To:"):
            tk.Label(filter_row, text=lbl, font=("Arial", 10),
                     bg=CARD_BG, fg=TEXT_MUTED).pack(side="left", padx=(0, 4))
            e = tk.Entry(filter_row, font=("Arial", 10), width=12,
                         bg="#faf8f4", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK)
            e.insert(0, "YYYY-MM-DD")
            e.pack(side="left", ipady=3, padx=(0, 10))
            if lbl == "From:":
                start_e = e
            else:
                end_e = e

        tf = tk.Frame(hist_card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        cols = ("ID", "Product ID", "Qty", "Total", "Date", "Sold By")
        hist_tree = ttk.Treeview(tf, columns=cols, show="headings", height=10)
        for col, w in zip(cols, [60, 90, 60, 110, 180, 110]):
            hist_tree.heading(col, text=col)
            hist_tree.column(col, anchor="center", width=w)
        sb2 = ttk.Scrollbar(tf, orient="vertical", command=hist_tree.yview)
        hist_tree.configure(yscrollcommand=sb2.set)
        hist_tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        def load_sales(start=None, end=None):
            hist_tree.delete(*hist_tree.get_children())
            for s in get_sales(start, end):
                hist_tree.insert("", tk.END, values=s)

        load_sales()

        def apply_filter():
            s = start_e.get().strip()
            e = end_e.get().strip()
            load_sales(None if s == "YYYY-MM-DD" else s,
                       None if e == "YYYY-MM-DD" else e)

        def clear_filter():
            for entry, placeholder in [(start_e, "YYYY-MM-DD"), (end_e, "YYYY-MM-DD")]:
                entry.delete(0, tk.END)
                entry.insert(0, placeholder)
            load_sales()

        self._btn(filter_row, "Filter", apply_filter, color=PRIMARY).pack(side="left", padx=(0, 6))
        self._btn(filter_row, "Clear",  clear_filter, color="#64748b").pack(side="left")

        cancel_row = tk.Frame(hist_card, bg=CARD_BG, padx=20, pady=(0, 12))
        cancel_row.pack(fill="x")

        def cancel_selected():
            sel = hist_tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Please select a sale to cancel.")
                return
            vals = hist_tree.item(sel, "values")
            if messagebox.askyesno("Confirm", f"Cancel sale #{vals[0]}? Stock will be restored."):
                result = cancel_sale(int(vals[0]))
                if result == "Sale cancelled successfully":
                    messagebox.showinfo("Cancelled", "Sale cancelled and stock restored.")
                    self.show_sales_screen()
                else:
                    messagebox.showerror("Error", result)

        self._btn(cancel_row, "Cancel Selected Sale", cancel_selected, color=DANGER).pack(side="left")

    # ── Charts ────────────────────────────────────────────────────────────────

    def show_reports_screen(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Charts")

        card = self._card(c)
        card.pack(padx=30, fill="both", expand=True)

        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot  # noqa
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception as e:
            tk.Label(card, text=f"matplotlib not available:\n{e}",
                     bg=CARD_BG, fg="red", font=("Arial", 11)).pack(pady=40)
            return

        products   = get_products()
        sales_data = get_sales_by_product()

        if not products:
            tk.Label(card, text="No products to display.",
                     bg=CARD_BG, fg=TEXT_MUTED, font=("Arial", 12)).pack(pady=40)
            return

        names      = [p[1] for p in products]
        stocks     = [p[4] for p in products]
        sale_names = [r[0] for r in sales_data]
        sale_qtys  = [r[1] for r in sales_data]

        fig = Figure(figsize=(8, 6), facecolor=CARD_BG)

        ax1 = fig.add_subplot(211)
        ax1.set_facecolor("#faf8f4")
        bars1 = ax1.bar(names, stocks, color=PRIMARY, width=0.5, zorder=3)
        ax1.bar_label(bars1, padding=3, color=TEXT_DARK, fontsize=8, fontweight="bold")
        ax1.set_title("Stock Levels", fontsize=12, fontweight="bold", color=TEXT_DARK, pad=10)
        ax1.set_ylabel("Qty", color=TEXT_MUTED, fontsize=9)
        ax1.tick_params(axis="x", rotation=25, colors=TEXT_DARK, labelsize=8)
        ax1.tick_params(axis="y", colors=TEXT_MUTED, labelsize=8)
        ax1.spines[["top", "right"]].set_visible(False)
        ax1.yaxis.grid(True, color=BORDER, zorder=0)

        ax2 = fig.add_subplot(212)
        ax2.set_facecolor("#faf8f4")
        bars2 = ax2.bar(sale_names, sale_qtys, color=SUCCESS, width=0.5, zorder=3)
        ax2.bar_label(bars2, padding=3, color=TEXT_DARK, fontsize=8, fontweight="bold")
        ax2.set_title("Units Sold per Product", fontsize=12, fontweight="bold",
                      color=TEXT_DARK, pad=10)
        ax2.set_ylabel("Qty Sold", color=TEXT_MUTED, fontsize=9)
        ax2.tick_params(axis="x", rotation=25, colors=TEXT_DARK, labelsize=8)
        ax2.tick_params(axis="y", colors=TEXT_MUTED, labelsize=8)
        ax2.spines[["top", "right"]].set_visible(False)
        ax2.yaxis.grid(True, color=BORDER, zorder=0)

        fig.tight_layout(pad=2.5)
        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    # ── Reports list ──────────────────────────────────────────────────────────

    def show_reports_list(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Reports")

        card = self._card(c)
        card.pack(padx=30, fill="both", expand=True)

        sales = get_sales()
        if not sales:
            tk.Label(card, text="No sales recorded yet.",
                     bg=CARD_BG, fg=TEXT_MUTED, font=("Arial", 12)).pack(pady=40)
            return

        tf = tk.Frame(card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=16)

        cols = ("Sale ID", "Product ID", "Qty", "Total Price", "Date", "Sold By")
        tree = ttk.Treeview(tf, columns=cols, show="headings")
        for col, w in zip(cols, [70, 90, 60, 110, 180, 110]):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=w)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for s in sales:
            tree.insert("", tk.END, values=s)

    # ── Export ────────────────────────────────────────────────────────────────

    def show_export_screen(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Export Data")

        card = self._card(c)
        card.pack(padx=30)

        inner = tk.Frame(card, bg=CARD_BG, padx=40, pady=34)
        inner.pack()

        tk.Label(inner, text="Data", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(row=0, column=0, sticky="w", pady=(0, 4))
        data_var = tk.StringVar(value="Products")
        ttk.Combobox(inner, textvariable=data_var,
                     values=["Products", "Sales"],
                     state="readonly", width=24).grid(row=1, column=0, padx=(0, 30), ipady=5)

        tk.Label(inner, text="Format", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(row=0, column=1, sticky="w", pady=(0, 4))
        fmt_var = tk.StringVar(value="CSV")
        ttk.Combobox(inner, textvariable=fmt_var,
                     values=["CSV", "Excel (.xlsx)"],
                     state="readonly", width=24).grid(row=1, column=1, ipady=5)

        def do_export():
            choice = data_var.get()
            fmt    = fmt_var.get()
            rows   = get_products() if choice == "Products" else get_sales()
            hdrs   = (["ID", "Name", "Category", "Price", "Stock"]
                      if choice == "Products"
                      else ["Sale ID", "Product ID", "Qty", "Total Price", "Date", "Sold By"])
            if not rows:
                messagebox.showwarning("No Data", f"No {choice.lower()} to export.")
                return
            if fmt == "CSV":
                fp = filedialog.asksaveasfilename(
                    defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                    initialfile=f"{choice.lower()}_export.csv")
                if not fp:
                    return
                with open(fp, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows([hdrs] + [list(r) for r in rows])
                messagebox.showinfo("Exported", f"Saved to:\n{fp}")
            else:
                try:
                    import openpyxl
                except ImportError:
                    messagebox.showerror("Missing library", "Run: pip install openpyxl")
                    return
                fp = filedialog.asksaveasfilename(
                    defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                    initialfile=f"{choice.lower()}_export.xlsx")
                if not fp:
                    return
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = choice
                ws.append(hdrs)
                for r in rows:
                    ws.append(list(r))
                wb.save(fp)
                messagebox.showinfo("Exported", f"Saved to:\n{fp}")

        self._btn(inner, "Export", do_export, color=PRIMARY).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(24, 0), ipady=5)

    # ── User Management ───────────────────────────────────────────────────────

    def show_user_management(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "User Management")

        form_card = self._card(c)
        form_card.pack(padx=30, pady=(0, 20), fill="x")

        fi = tk.Frame(form_card, bg=CARD_BG, padx=26, pady=20)
        fi.pack(fill="x")

        tk.Label(fi, text="Add New User", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(
                     row=0, column=0, columnspan=6, sticky="w", pady=(0, 14))

        fields_info = [("Username", "uname"), ("Password", "pwd")]
        u_entries = {}
        for i, (lbl, key) in enumerate(fields_info):
            tk.Label(fi, text=lbl, font=("Arial", 10, "bold"),
                     bg=CARD_BG, fg=TEXT_DARK).grid(
                         row=1, column=i*2, sticky="w", padx=(0, 8))
            e = tk.Entry(fi, font=("Arial", 10), width=18,
                         bg="#faf8f4", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK,
                         show=("*" if key == "pwd" else ""))
            e.grid(row=1, column=i*2+1, padx=(0, 20), ipady=5)
            u_entries[key] = e

        tk.Label(fi, text="Role", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(row=1, column=4, sticky="w", padx=(0, 8))
        role_var = tk.StringVar(value="cashier")
        ttk.Combobox(fi, textvariable=role_var, values=["cashier", "admin"],
                     state="readonly", width=12).grid(row=1, column=5, ipady=4, padx=(0, 20))

        def add_action():
            uname = u_entries["uname"].get().strip()
            pwd   = u_entries["pwd"].get().strip()
            if not uname or not pwd:
                messagebox.showerror("Validation", "Username and password required.")
                return
            result = add_user(uname, pwd, role_var.get())
            if result == "User added successfully":
                messagebox.showinfo("Success", f'User "{uname}" added.')
                for e in u_entries.values():
                    e.delete(0, tk.END)
                self.show_user_management()
            else:
                messagebox.showerror("Error", result)

        self._btn(fi, "Add User", add_action, color=PRIMARY).grid(
            row=2, column=0, columnspan=6, sticky="w", pady=(14, 0))

        list_card = self._card(c)
        list_card.pack(padx=30, fill="both", expand=True)

        tk.Label(list_card, text="All Users", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(14, 0))

        tf = tk.Frame(list_card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=10)

        cols = ("ID", "Username", "Role")
        user_tree = ttk.Treeview(tf, columns=cols, show="headings", height=8)
        for col, w in zip(cols, [60, 200, 120]):
            user_tree.heading(col, text=col)
            user_tree.column(col, anchor="center", width=w)
        sb3 = ttk.Scrollbar(tf, orient="vertical", command=user_tree.yview)
        user_tree.configure(yscrollcommand=sb3.set)
        user_tree.pack(side="left", fill="both", expand=True)
        sb3.pack(side="right", fill="y")

        for u in get_users():
            user_tree.insert("", tk.END, values=u)

        def del_user():
            sel = user_tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Please select a user.")
                return
            vals = user_tree.item(sel, "values")
            if vals[1] == self.current_user:
                messagebox.showerror("Error", "You cannot delete your own account.")
                return
            if messagebox.askyesno("Confirm", f'Delete user "{vals[1]}"?'):
                delete_user(int(vals[0]))
                self.show_user_management()

        btn_row = tk.Frame(list_card, bg=CARD_BG, padx=20, pady=(0, 14))
        btn_row.pack(fill="x")
        self._btn(btn_row, "Delete User", del_user, color=DANGER).pack(side="left")


if __name__ == "__main__":
    create_database()
    insert_default_users()
    root = tk.Tk()
    app = StoreApp(root)
    root.mainloop()
