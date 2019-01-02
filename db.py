"""
File to handle my database operations
"""

commands = (
    """
    CREATE TABLE IF NOT EXISTS public.users(
    id SERIAL PRIMARY KEY,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password VARCHAR NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.categories(
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        description VARCHAR NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.products(
        id SERIAL PRIMARY KEY,
        name VARCHAR UNIQUE NOT NULL,
        unit_cost INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        category INTEGER REFERENCES public.categories(id) ON DELETE CASCADE NULL,
        deleted BOOLEAN DEFAULT FALSE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.sales(
        id SERIAL PRIMARY KEY,
        attendant_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
        product_id INTEGER REFERENCES public.products(id) ON DELETE CASCADE NOT NULL,
        quantity INTEGER NOT NULL,
        total INTEGER NOT NULL,
        revert BOOLEAN DEFAULT FALSE NOT NULL
    )
    """,
    """
    INSERT INTO public.users(first_name, last_name, email, password, is_admin) SELECT 'admin', 'owner', 'admin@email.com', 'pbkdf2:sha256:50000$q5STunEW$09107a77f6c6a7d7042aa1d1e5755736ea128a2eeac0219724bfeddf91bfd88b', True WHERE NOT EXISTS (SELECT * FROM public.users WHERE email='admin@email.com')
    """
    )

import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash
from api.__init__ import app


class DB:
    def __init__(self):
        try:
            if app.config["TESTING"]:
                self.conn = psycopg2.connect(host="localhost", 
                                             database="test_db", 
                                             user="postgres", 
                                             password="pass1234")
            else:
                self.conn = psycopg2.connect("postgres://lqrvapuohprshd:5663d19e339d24463a34ce0c8016bcadf880621cb80e2754ee677af468dafb3b@ec2-107-21-93-132.compute-1.amazonaws.com:5432/d5f8cj1fcjbd3r")
            self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
            self.conn.autocommit = True
            for command in commands:
                self.cur.execute(command)
        except psycopg2.OperationalError as e:
            print("Failed to connect" + e)
    
    def drop_tables(self):
        self.cur.execute("DROP TABLE IF EXISTS sales")
        self.cur.execute("DROP TABLE IF EXISTS products")
        self.cur.execute("DROP TABLE IF EXISTS categories")
        self.cur.execute("DROP TABLE IF EXISTS users")
    
    def get_user(self, email):
        self.cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        return self.cur.fetchone()
    
    def update_user_rights(self, user_id, is_admin):
        if is_admin:
            self.cur.execute("UPDATE users SET is_admin=%s WHERE id=%s", (False, user_id))
        else:
            self.cur.execute("UPDATE users SET is_admin=%s WHERE id=%s", (True, user_id))
    
    def get_user_by_id(self, user_id):
        self.cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        return self.cur.fetchone()
    
    def get_users(self):
        self.cur.execute("SELECT * FROM users")
        return self.cur.fetchall()
    
    def get_attendants(self):
        self.cur.execute("SELECT * FROM users WHERE id!=%s", (1,))
        return self.cur.fetchall()
    
    def create_user(self, user):
        self.cur.execute("INSERT INTO users(first_name, last_name, email, password) VALUES (%s, %s, %s, %s)", 
                         (user.first_name, user.last_name, user.email, user.password))
    
    def add_product(self, product):
        if product.category_id:
            self.cur.execute("INSERT INTO products(name, unit_cost, quantity, category) VALUES (%s, %s, %s, %s)", 
                             (product.name, product.unit_cost, product.quantity, product.category_id))
        else:
            self.cur.execute("INSERT INTO products(name, unit_cost, quantity) VALUES (%s, %s, %s)", 
                             (product.name, product.unit_cost, product.quantity))
    
    def get_product_by_name(self, name):
        self.cur.execute("SELECT * FROM products WHERE name=%s", (name,))
        return self.cur.fetchone()
    
    def get_products(self):
        self.cur.execute("SELECT * FROM products WHERE deleted=%s", (False,))
        return self.cur.fetchall()
    
    def get_deleted_products(self):
        self.cur.execute("SELECT * FROM products WHERE deleted=%s", (True,))
        return self.cur.fetchall()
    
    def get_product_by_id(self, product_id):
        self.cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        return self.cur.fetchone()
    
    def update_product(self, **kwargs):
        name = kwargs.get("name")
        unit_cost = kwargs.get("unit_cost")
        quantity = kwargs.get("quantity")
        category_id = kwargs.get("category_id")
        product_id = kwargs.get("product_id")
        if category_id is not None:
            self.cur.execute("UPDATE products SET name=%s, unit_cost=%s, quantity=%s, category=%s WHERE id=%s", 
                             (name, unit_cost, quantity, category_id, product_id))
        else:
            self.cur.execute("UPDATE products SET name=%s, unit_cost=%s, quantity=%s WHERE id=%s", 
                             (name, unit_cost, quantity, product_id))
    
    def delete_product(self, product_id):
        self.cur.execute("UPDATE products SET deleted=%s WHERE id=%s", (True, product_id,))

    def add_sale(self, **kwargs):
        sale = kwargs.get("sale")
        self.cur.execute("INSERT INTO sales(attendant_id, product_id, quantity, total) VALUES (%s, %s, %s, %s)",
                         (sale.attendant_id, sale.product_id, sale.quantity, sale.total))

    def get_sale_records(self):
        self.cur.execute("SELECT * FROM sales WHERE revert=%s", (False,))
        return self.cur.fetchall()
    
    def get_reverted_sale_records(self):
        self.cur.execute("SELECT * FROM sales WHERE revert=%s", (True,))
        return self.cur.fetchall()

    def get_single_sale(self, sale_id):
        self.cur.execute("SELECT * FROM sales WHERE id=%s", (sale_id,))
        return self.cur.fetchone()

    def get_sale_records_user(self, user_id):
        self.cur.execute("SELECT * FROM sales WHERE attendant_id=%s AND revert=%s", (user_id, False))
        return self.cur.fetchall()

    def get_sale_records_user_reverted(self, user_id):
        self.cur.execute("SELECT * FROM sales WHERE attendant_id=%s AND revert=%s", (user_id, True))
        return self.cur.fetchall()
    
    def revert_sale_record(self, sale_record):
        print(sale_record)
        self.cur.execute("UPDATE sales SET attendant_id=%s, product_id=%s, quantity=%s, total=%s, revert=%s", (sale_record["attendant_id"], sale_record["product_id"], sale_record["quantity"], sale_record["total"], True))

    def get_category_by_name(self, name):
        self.cur.execute("SELECT * FROM categories WHERE name=%s", (name,))
        return self.cur.fetchone()

    def add_category(self, category):
        self.cur.execute("INSERT INTO categories(name, description) VALUES (%s, %s)", 
                         (category.name, category.description))

    def get_category_by_id(self, category_id):
        self.cur.execute("SELECT * FROM categories WHERE id=%s", (category_id,))
        return self.cur.fetchone()

    def update_category(self, name, description, category_id):
        self.cur.execute("UPDATE categories SET name=%s, description=%s WHERE id=%s", 
                         (name, description, category_id))

    def get_categories(self):
        self.cur.execute("SELECT * FROM categories")
        return self.cur.fetchall()

    def delete_category(self, category_id):
        self.cur.execute("DELETE FROM categories WHERE id=%s", (category_id,))
