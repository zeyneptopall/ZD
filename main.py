import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
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

# ── Colour palette ───────────────────────────────────────────────────────────
SIDEBAR_BG    = "#16213e"
SIDEBAR_HOVER = "#0f3460"
MAIN_BG       = "#f0f2f5"
CARD_BG       = "#ffffff"
PRIMARY       = "#e94560"
SUCCESS       = "#22c55e"
WARNING       = "#f59e0b"
DANGER        = "#ef4444"
TEXT_DARK     = "#1e293b"
TEXT_MUTED    = "#64748b"
TEXT_LIGHT    = "#ffffff"
BORDER        = "#e2e8f0"

LOW_STOCK_THRESHOLD = 5
# ────────────────────────────────────────────────────────────────────────────


class StoreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Store Management System")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=MAIN_BG)

        self.sidebar      = None
        self.content_area = None
        self.current_user = None

        self._style_ttk()
        self.show_login_screen()

    # ── TTK styling ──────────────────────────────────────────────────────────

    def _style_ttk(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=CARD_BG, foreground=TEXT_DARK,
                        rowheight=28, fieldbackground=CARD_BG,
                        font=("Arial", 10))
        style.configure("Treeview.Heading",
                        background=SIDEBAR_BG, foreground=TEXT_LIGHT,
                        font=("Arial", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", SIDEBAR_HOVER)],
                              foreground=[("selected", TEXT_LIGHT)])
        style.configure("TCombobox", padding=5)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.sidebar = self.content_area = None

    def _clear_content(self):
        if self.content_area:
            for w in self.content_area.winfo_children():
                w.destroy()

    @staticmethod
    def _darken(hex_color, factor=0.82):
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

    def _page_title(self, parent, text):
        tk.Label(parent, text=text, font=("Arial", 20, "bold"),
                 bg=MAIN_BG, fg=TEXT_DARK).pack(anchor="w", padx=30, pady=(24, 4))
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=30, pady=(0, 20))

    def _scrollable_tree(self, parent, cols, data, widths=None, tags=None):
        frame = tk.Frame(parent, bg=CARD_BG)
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for i, col in enumerate(cols):
            tree.heading(col, text=col)
            w = (widths[i] if widths else 130)
            tree.column(col, anchor="center", width=w)

        if tags:
            for tag, cfg in tags.items():
                tree.tag_configure(tag, **cfg)

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for row in data:
            tag = ()
            if tags and "low_stock" in tags and len(row) >= 5:
                try:
                    if int(row[4]) <= LOW_STOCK_THRESHOLD:
                        tag = ("low_stock",)
                except (ValueError, TypeError):
                    pass
            tree.insert("", tk.END, values=row, tags=tag)
        return tree

    # ── Sidebar layout ───────────────────────────────────────────────────────

    def _setup_layout(self, role):
        self._clear_root()
        outer = tk.Frame(self.root, bg=MAIN_BG)
        outer.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(outer, bg=SIDEBAR_BG, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content_area = tk.Frame(outer, bg=MAIN_BG)
        self.content_area.pack(side="left", fill="both", expand=True)

        self._build_sidebar(role)

    def _build_sidebar(self, role):
        sb = self.sidebar

        hdr = tk.Frame(sb, bg=SIDEBAR_BG, height=90)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Store", font=("Arial", 20, "bold"),
                 bg=SIDEBAR_BG, fg=TEXT_LIGHT).pack(pady=(20, 0))
        tk.Label(hdr, text="Management System", font=("Arial", 8),
                 bg=SIDEBAR_BG, fg="#5577aa").pack()

        tk.Frame(sb, bg="#253555", height=1).pack(fill="x", padx=16, pady=8)

        section = "ADMIN PANEL" if role == "admin" else "CASHIER PANEL"
        tk.Label(sb, text=section, font=("Arial", 8, "bold"),
                 bg=SIDEBAR_BG, fg="#445577").pack(anchor="w", padx=20, pady=(4, 10))

        if role == "admin":
            items = [
                ("  Manage Products", self.show_manage_products),
                ("  Show Products",   self.show_products_screen),
                ("  Sales",           self.show_sales_screen),
                ("  Charts",          self.show_reports_screen),
                ("  Reports",         self.show_reports_list),
                ("  Export Data",     self.show_export_screen),
                ("  User Management", self.show_user_management),
            ]
        else:
            items = [
                ("  View Products", self.show_products_screen),
                ("  Make Sale",     self.show_sales_screen),
            ]

        for text, cmd in items:
            self._nav_btn(sb, text, cmd)

        tk.Frame(sb, bg="#253555", height=1).pack(fill="x", padx=16, side="bottom", pady=6)
        lo = tk.Button(sb, text="  Logout", anchor="w",
                       font=("Arial", 10), bg=SIDEBAR_BG, fg=DANGER,
                       activebackground=SIDEBAR_HOVER, activeforeground=DANGER,
                       bd=0, relief="flat", padx=20, pady=12, cursor="hand2",
                       command=self.show_login_screen)
        lo.pack(fill="x", side="bottom")
        lo.bind("<Enter>", lambda e: lo.config(bg=SIDEBAR_HOVER))
        lo.bind("<Leave>", lambda e: lo.config(bg=SIDEBAR_BG))

    def _nav_btn(self, parent, text, command):
        b = tk.Button(parent, text=text, anchor="w",
                      font=("Arial", 10), bg=SIDEBAR_BG, fg=TEXT_LIGHT,
                      activebackground=SIDEBAR_HOVER, activeforeground=TEXT_LIGHT,
                      bd=0, relief="flat", padx=20, pady=12, cursor="hand2",
                      command=command)
        b.pack(fill="x")
        b.bind("<Enter>", lambda e: b.config(bg=SIDEBAR_HOVER))
        b.bind("<Leave>", lambda e: b.config(bg=SIDEBAR_BG))

    # ── Login ────────────────────────────────────────────────────────────────

    def show_login_screen(self):
        self._clear_root()

        bg = tk.Frame(self.root, bg=SIDEBAR_BG)
        bg.pack(fill="both", expand=True)

        card = tk.Frame(bg, bg=CARD_BG, padx=50, pady=44)
        card.place(relx=0.5, rely=0.5, anchor="center")

        try:
            logo_img = Image.open("WhatsApp Image 2026-04-06 at 15.43.14.jpeg")
            target_w = 260
            ratio = target_w / logo_img.width
            target_h = int(logo_img.height * ratio)
            logo_img = logo_img.resize((target_w, target_h), Image.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(card, image=self._logo_photo, bg=CARD_BG).pack(pady=(0, 10))
        except Exception:
            pass

        tk.Label(card, text="Store Management",
                 font=("Arial", 22, "bold"), bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w")
        tk.Label(card, text="Sign in to your account",
                 font=("Arial", 11), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", pady=(2, 26))

        for label, attr, show in [("Username", "username_entry", ""),
                                   ("Password", "password_entry", "*")]:
            tk.Label(card, text=label, font=("Arial", 10, "bold"),
                     bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w")
            e = tk.Entry(card, show=show, font=("Arial", 11), width=28,
                         bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK)
            e.pack(fill="x", ipady=7, pady=(4, 14))
            setattr(self, attr, e)

        self.username_entry.bind("<Return>", lambda _: self.login())
        self.password_entry.bind("<Return>", lambda _: self.login())
        self._btn(card, "Sign In", self.login, color=PRIMARY).pack(fill="x", ipady=5, pady=(6, 0))

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = check_user(username, password)
        if role == "admin":
            self.current_user = username
            self._setup_layout("admin")
            self.show_manage_products()
        elif role == "cashier":
            self.current_user = username
            self._setup_layout("cashier")
            self.show_products_screen()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    # ── Manage Products ──────────────────────────────────────────────────────

    def show_manage_products(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Manage Products")

        card = self._card(c)
        card.pack(padx=30, fill="x")

        form = tk.Frame(card, bg=CARD_BG, padx=30, pady=26)
        form.pack(fill="x")

        field_defs = [
            ("Product Name", "name"),
            ("Category",     "cat"),
            ("Price (₺)",    "price"),
            ("Stock Qty",    "stock"),
        ]
        entries = {}
        for i, (lbl, key) in enumerate(field_defs):
            col = (i % 2) * 2
            row = (i // 2) * 2
            tk.Label(form, text=lbl, font=("Arial", 10, "bold"),
                     bg=CARD_BG, fg=TEXT_DARK).grid(
                         row=row, column=col, sticky="w", padx=(0, 40), pady=(10, 2))
            e = tk.Entry(form, font=("Arial", 10), width=26,
                         bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK)
            e.grid(row=row+1, column=col, sticky="ew", padx=(0, 40), ipady=6)
            entries[key] = e

        def add_action():
            name    = entries["name"].get().strip()
            cat     = entries["cat"].get().strip()
            price_t = entries["price"].get().strip()
            stock_t = entries["stock"].get().strip()
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
        self._btn(btn_row, "Add Product", add_action, color=SUCCESS).pack(side="left")

    # ── Products list ────────────────────────────────────────────────────────

    def show_products_screen(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Products")

        # Low stock warning banner
        products = get_products()
        low = [p for p in products if p[4] <= LOW_STOCK_THRESHOLD]
        if low:
            banner = tk.Frame(c, bg="#fef3c7", highlightthickness=1,
                              highlightbackground="#fbbf24")
            banner.pack(fill="x", padx=30, pady=(0, 12))
            tk.Label(banner,
                     text=f"  ⚠  {len(low)} product(s) have low stock (≤ {LOW_STOCK_THRESHOLD} units)",
                     font=("Arial", 10, "bold"), bg="#fef3c7", fg="#92400e",
                     pady=8).pack(anchor="w")

        card = self._card(c)
        card.pack(padx=30, fill="both", expand=True)

        # Search bar
        search_frame = tk.Frame(card, bg=CARD_BG, padx=20, pady=12)
        search_frame.pack(fill="x")
        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left", padx=(0, 8))
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                                font=("Arial", 10), width=30,
                                bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                                insertbackground=TEXT_DARK)
        search_entry.pack(side="left", ipady=4)

        # Tree
        tree_frame = tk.Frame(card, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        cols = ("ID", "Name", "Category", "Price", "Stock")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for i, (col, w) in enumerate(zip(cols, [60, 200, 160, 110, 80])):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=w)

        tree.tag_configure("low_stock", background="#fef3c7", foreground="#92400e")

        sb_tree = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb_tree.set)
        tree.pack(side="left", fill="both", expand=True)
        sb_tree.pack(side="right", fill="y")

        def load_tree(filter_text=""):
            tree.delete(*tree.get_children())
            for p in products:
                if filter_text.lower() in p[1].lower() or filter_text.lower() in (p[2] or "").lower():
                    tag = ("low_stock",) if p[4] <= LOW_STOCK_THRESHOLD else ()
                    tree.insert("", tk.END,
                                values=(p[0], p[1], p[2], f"{p[3]:.2f} ₺", p[4]),
                                tags=tag)

        load_tree()
        search_var.trace_add("write", lambda *_: load_tree(search_var.get()))

        # Edit / Delete buttons (admin only)
        btn_frame = tk.Frame(card, bg=CARD_BG, padx=20, pady=(0, 14))
        btn_frame.pack(fill="x")

        def edit_product():
            selected = tree.focus()
            if not selected:
                messagebox.showwarning("Select", "Please select a product to edit.")
                return
            vals = tree.item(selected, "values")
            product_id = int(vals[0])

            dialog = tk.Toplevel(self.root)
            dialog.title("Edit Product")
            dialog.geometry("360x280")
            dialog.configure(bg=CARD_BG)
            dialog.grab_set()

            fields = [("Name", vals[1]), ("Category", vals[2]),
                      ("Price", vals[3].replace(" ₺", "")), ("Stock", vals[4])]
            d_entries = {}
            for i, (lbl, val) in enumerate(fields):
                tk.Label(dialog, text=lbl, font=("Arial", 10, "bold"),
                         bg=CARD_BG, fg=TEXT_DARK).grid(
                             row=i*2, column=0, sticky="w", padx=24, pady=(12, 2))
                e = tk.Entry(dialog, font=("Arial", 10), width=28,
                             bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                             insertbackground=TEXT_DARK)
                e.insert(0, val)
                e.grid(row=i*2+1, column=0, padx=24, sticky="ew", ipady=5)
                d_entries[lbl] = e

            def save_edit():
                try:
                    new_price = float(d_entries["Price"].get().strip())
                    new_stock = int(d_entries["Stock"].get().strip())
                except ValueError:
                    messagebox.showerror("Validation", "Price must be a number, Stock must be integer.")
                    return
                update_product(product_id,
                               d_entries["Name"].get().strip(),
                               d_entries["Category"].get().strip(),
                               new_price, new_stock)
                dialog.destroy()
                self.show_products_screen()

            self._btn(dialog, "Save", save_edit, color=SUCCESS).grid(
                row=len(fields)*2, column=0, pady=14, padx=24, sticky="ew", ipady=4)

        def del_product():
            selected = tree.focus()
            if not selected:
                messagebox.showwarning("Select", "Please select a product to delete.")
                return
            vals = tree.item(selected, "values")
            if messagebox.askyesno("Confirm", f'Delete "{vals[1]}"?'):
                delete_product(int(vals[0]))
                self.show_products_screen()

        self._btn(btn_frame, "Edit", edit_product, color=WARNING, fg=TEXT_DARK).pack(side="left", padx=(0, 10))
        self._btn(btn_frame, "Delete", del_product, color=DANGER).pack(side="left")

    # ── Sales ────────────────────────────────────────────────────────────────

    def show_sales_screen(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "Sales")

        # Summary strip
        total_rev, total_cnt, top_name, _ = get_sales_summary()
        strip = tk.Frame(c, bg=MAIN_BG)
        strip.pack(fill="x", padx=30, pady=(0, 18))
        for val, lbl, color in [
            (f"{total_rev:.2f} ₺", "Total Revenue", SUCCESS),
            (str(total_cnt),        "Total Sales",   "#3b82f6"),
            (top_name,              "Top Product",   WARNING),
        ]:
            box = tk.Frame(strip, bg=CARD_BG, padx=22, pady=14,
                           highlightthickness=1, highlightbackground=BORDER)
            box.pack(side="left", padx=(0, 14), fill="x", expand=True)
            tk.Label(box, text=val, font=("Arial", 15, "bold"),
                     bg=CARD_BG, fg=color).pack(anchor="w")
            tk.Label(box, text=lbl, font=("Arial", 9),
                     bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")

        # Sale form
        form_card = self._card(c)
        form_card.pack(padx=30, pady=(0, 18), fill="x")

        fi = tk.Frame(form_card, bg=CARD_BG, padx=26, pady=20)
        fi.pack(fill="x")

        tk.Label(fi, text="New Sale", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(
                     row=0, column=0, columnspan=4, sticky="w", pady=(0, 14))

        products = get_products()
        product_map, product_names = {}, []
        for p in products:
            key = f"{p[1]}  |  {p[3]:.2f} ₺  |  Stock: {p[4]}"
            product_names.append(key)
            product_map[key] = {"id": p[0], "price": p[3], "stock": p[4]}

        tk.Label(fi, text="Product", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(row=1, column=0, sticky="w", padx=(0, 10))
        combo = ttk.Combobox(fi, values=product_names, state="readonly", width=38)
        combo.grid(row=1, column=1, padx=(0, 24), ipady=4)

        tk.Label(fi, text="Qty", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(row=1, column=2, sticky="w", padx=(0, 10))
        qty_e = tk.Entry(fi, font=("Arial", 10), width=8,
                         bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK)
        qty_e.grid(row=1, column=3, ipady=5)

        total_lbl = tk.Label(fi, text="Total: —", font=("Arial", 12, "bold"),
                              bg=CARD_BG, fg=PRIMARY)
        total_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))

        def update_total(event=None):
            sel = combo.get()
            qty_t = qty_e.get().strip()
            if sel in product_map and qty_t.isdigit():
                total_lbl.config(
                    text=f"Total: {product_map[sel]['price'] * int(qty_t):.2f} ₺")
            else:
                total_lbl.config(text="Total: —")

        combo.bind("<<ComboboxSelected>>", update_total)
        qty_e.bind("<KeyRelease>", update_total)

        def sell_action():
            sel   = combo.get()
            qty_t = qty_e.get().strip()
            if not sel:
                messagebox.showerror("Error", "Please select a product.")
                return
            if not qty_t.isdigit() or int(qty_t) <= 0:
                messagebox.showerror("Error", "Enter a valid quantity.")
                return
            result = record_sale(product_map[sel]["id"], int(qty_t),
                                 sold_by=self.current_user)
            if result == "Sale recorded successfully":
                messagebox.showinfo("Success", "Sale completed!")
                self.show_sales_screen()
            else:
                messagebox.showerror("Error", result)

        self._btn(fi, "Sell", sell_action, color=SUCCESS).grid(
            row=2, column=2, columnspan=2, sticky="e", pady=(12, 0))

        # History table with date filter
        hist_card = self._card(c)
        hist_card.pack(padx=30, pady=(0, 20), fill="both", expand=True)

        filter_row = tk.Frame(hist_card, bg=CARD_BG, padx=20, pady=12)
        filter_row.pack(fill="x")
        tk.Label(filter_row, text="Sales History", font=("Arial", 12, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(side="left", padx=(0, 20))

        tk.Label(filter_row, text="From:", font=("Arial", 10),
                 bg=CARD_BG, fg=TEXT_MUTED).pack(side="left", padx=(0, 4))
        start_e = tk.Entry(filter_row, font=("Arial", 10), width=12,
                           bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                           insertbackground=TEXT_DARK)
        start_e.insert(0, "YYYY-MM-DD")
        start_e.pack(side="left", ipady=3, padx=(0, 10))

        tk.Label(filter_row, text="To:", font=("Arial", 10),
                 bg=CARD_BG, fg=TEXT_MUTED).pack(side="left", padx=(0, 4))
        end_e = tk.Entry(filter_row, font=("Arial", 10), width=12,
                         bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK)
        end_e.insert(0, "YYYY-MM-DD")
        end_e.pack(side="left", ipady=3, padx=(0, 10))

        tf = tk.Frame(hist_card, bg=CARD_BG)
        tf.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        cols = ("ID", "Product ID", "Qty", "Total", "Date", "Sold By")
        hist_tree = ttk.Treeview(tf, columns=cols, show="headings", height=8)
        for col, w in zip(cols, [60, 90, 60, 110, 170, 100]):
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
            if s == "YYYY-MM-DD": s = None
            if e == "YYYY-MM-DD": e = None
            load_sales(s, e)

        def clear_filter():
            start_e.delete(0, tk.END)
            start_e.insert(0, "YYYY-MM-DD")
            end_e.delete(0, tk.END)
            end_e.insert(0, "YYYY-MM-DD")
            load_sales()

        self._btn(filter_row, "Filter", apply_filter, color=PRIMARY).pack(side="left", padx=(0, 6))
        self._btn(filter_row, "Clear", clear_filter, color="#64748b").pack(side="left")

        # Cancel sale button
        cancel_row = tk.Frame(hist_card, bg=CARD_BG, padx=20, pady=(0, 12))
        cancel_row.pack(fill="x")

        def cancel_selected():
            selected = hist_tree.focus()
            if not selected:
                messagebox.showwarning("Select", "Please select a sale to cancel.")
                return
            vals = hist_tree.item(selected, "values")
            if messagebox.askyesno("Confirm", f"Cancel sale #{vals[0]}? Stock will be restored."):
                result = cancel_sale(int(vals[0]))
                if result == "Sale cancelled successfully":
                    messagebox.showinfo("Cancelled", "Sale cancelled and stock restored.")
                    self.show_sales_screen()
                else:
                    messagebox.showerror("Error", result)

        self._btn(cancel_row, "Cancel Selected Sale", cancel_selected, color=DANGER).pack(side="left")

    # ── Charts ───────────────────────────────────────────────────────────────

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

        products = get_products()
        sales_data = get_sales_by_product()

        if not products:
            tk.Label(card, text="No products to display.",
                     bg=CARD_BG, fg=TEXT_MUTED, font=("Arial", 12)).pack(pady=40)
            return

        names  = [p[1] for p in products]
        stocks = [p[4] for p in products]
        sale_names = [r[0] for r in sales_data]
        sale_qtys  = [r[1] for r in sales_data]

        fig = Figure(figsize=(8, 6), facecolor=CARD_BG)

        # Stock chart
        ax1 = fig.add_subplot(211)
        ax1.set_facecolor("#f8fafc")
        bars1 = ax1.bar(names, stocks, color=PRIMARY, width=0.5, zorder=3)
        ax1.bar_label(bars1, padding=3, color=TEXT_DARK, fontsize=8, fontweight="bold")
        ax1.set_title("Stock Levels", fontsize=12, fontweight="bold", color=TEXT_DARK, pad=10)
        ax1.set_ylabel("Qty", color=TEXT_MUTED, fontsize=9)
        ax1.tick_params(axis="x", rotation=25, colors=TEXT_DARK, labelsize=8)
        ax1.tick_params(axis="y", colors=TEXT_MUTED, labelsize=8)
        ax1.spines[["top", "right"]].set_visible(False)
        ax1.yaxis.grid(True, color=BORDER, zorder=0)

        # Sales chart
        ax2 = fig.add_subplot(212)
        ax2.set_facecolor("#f8fafc")
        bars2 = ax2.bar(sale_names, sale_qtys, color=SUCCESS, width=0.5, zorder=3)
        ax2.bar_label(bars2, padding=3, color=TEXT_DARK, fontsize=8, fontweight="bold")
        ax2.set_title("Units Sold per Product", fontsize=12, fontweight="bold", color=TEXT_DARK, pad=10)
        ax2.set_ylabel("Qty Sold", color=TEXT_MUTED, fontsize=9)
        ax2.tick_params(axis="x", rotation=25, colors=TEXT_DARK, labelsize=8)
        ax2.tick_params(axis="y", colors=TEXT_MUTED, labelsize=8)
        ax2.spines[["top", "right"]].set_visible(False)
        ax2.yaxis.grid(True, color=BORDER, zorder=0)

        fig.tight_layout(pad=2.5)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    # ── Reports list ─────────────────────────────────────────────────────────

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

        self._scrollable_tree(card,
                              cols=("Sale ID", "Product ID", "Qty", "Total Price", "Date", "Sold By"),
                              data=sales,
                              widths=[70, 90, 60, 110, 170, 110])

    # ── Export ───────────────────────────────────────────────────────────────

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
                      else ["Sale ID", "Product ID", "Quantity", "Total Price", "Date", "Sold By"])

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

    # ── User Management ──────────────────────────────────────────────────────

    def show_user_management(self):
        self._clear_content()
        c = self.content_area
        self._page_title(c, "User Management")

        # Add user form
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
                         bg="#f8fafc", fg=TEXT_DARK, relief="solid", bd=1,
                         insertbackground=TEXT_DARK,
                         show=("*" if key == "pwd" else ""))
            e.grid(row=1, column=i*2+1, padx=(0, 20), ipady=5)
            u_entries[key] = e

        tk.Label(fi, text="Role", font=("Arial", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).grid(row=1, column=4, sticky="w", padx=(0, 8))
        role_var = tk.StringVar(value="cashier")
        ttk.Combobox(fi, textvariable=role_var,
                     values=["cashier", "admin"],
                     state="readonly", width=12).grid(row=1, column=5, ipady=4, padx=(0, 20))

        def add_action():
            uname = u_entries["uname"].get().strip()
            pwd   = u_entries["pwd"].get().strip()
            if not uname or not pwd:
                messagebox.showerror("Validation", "Username and password are required.")
                return
            result = add_user(uname, pwd, role_var.get())
            if result == "User added successfully":
                messagebox.showinfo("Success", f'User "{uname}" added.')
                for e in u_entries.values():
                    e.delete(0, tk.END)
                self.show_user_management()
            else:
                messagebox.showerror("Error", result)

        self._btn(fi, "Add User", add_action, color=SUCCESS).grid(
            row=2, column=0, columnspan=6, sticky="w", pady=(14, 0))

        # Users list
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
            selected = user_tree.focus()
            if not selected:
                messagebox.showwarning("Select", "Please select a user to delete.")
                return
            vals = user_tree.item(selected, "values")
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
