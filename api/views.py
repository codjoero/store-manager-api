"""
File to handle application views
"""
from flask import jsonify, request
from flask.views import MethodView
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import (create_access_token, 
                                jwt_required, 
                                get_jwt_identity)
from api.models import Product, User, Category, Sale
from api.__init__ import app
from api.utils.validators import (validate_product, 
                                  validate_login_data, 
                                  validate_register_data, 
                                  validate_cart_item,
                                  validate_category,
                                  validate_data)
from db import DB


db_conn = DB()

@app.route("/")
def home_page():
    return "Welcome to store"


class LoginView(MethodView):
    """
    Class to login a user
    """
    def post(self):
        """
        Function to perform user login
        """
        # Validate the data
        res = validate_login_data(request)
        if res:
            return res
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        # Check if user already registered
        user = db_conn.get_user(email)
        if not user:
            return jsonify({"error": "Please register to login"}), 401
        msg = None
        # Check if it's a store owner and the password is theirs
        if user["is_admin"] and check_password_hash(user["password"], password):
            access_token = create_access_token(identity=email)
            msg = {"message": "Store owner logged in successfully", "token": access_token}
        # Check if it's a store attendant and the password is theirs
        elif not user["is_admin"] and check_password_hash(user["password"], password):
            access_token = create_access_token(identity=email)
            msg = {"message": "Store attendant logged in successfully", "token": access_token}
        else:
            return jsonify({"error": "Invalid email or password"}), 401
        if msg:
            return jsonify(msg)


class RegisterView(MethodView):
    """
    Class to handle adding a store attendant
    """
    @jwt_required
    def post(self):
        """
        Function to add a store attendant
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # Check if it's not store owner
        if not loggedin_user["is_admin"]:
            return jsonify({
                "error": "Please login as store owner to add store attendant"
            }), 403

        # Validate the data
        res = validate_register_data(request)
        if res:
            return res
        data = request.get_json()
        # Get attributes of the data sent
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        
        # Check if user is already registered
        user_exists = db_conn.get_user(email)
        if user_exists:
            return jsonify({
                "error": "User with this email already exists"
            }), 400

        new_user = User(first_name=first_name, last_name=last_name, 
                        email=email, password=generate_password_hash(password))
        # Add user to database
        db_conn.create_user(new_user)
        return jsonify({
            "message": "Store attendant added successfully"
        }), 201


class ProductView(MethodView):
    """
    Class to perform http methods on products
    """
    @jwt_required
    def post(self):
        """
        Handles creating of a product
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # # Check if it's not store owner
        if not loggedin_user["is_admin"]:
            return jsonify({
                "error": "Please login as a store owner"
            }), 403

        res = validate_product(request)
        if res:
            return res
        
        data = request.get_json()
        # Get the fields which were sent
        name = data.get("name")
        unit_cost = data.get("unit_cost")
        quantity = data.get("quantity")
        category_id = data.get("category_id")


        # create a product object
        new_product = Product(name=name, unit_cost=unit_cost, 
                              quantity=quantity, category_id=category_id)
        # Check if product exists with this name
        product = db_conn.get_product_by_name(name)
        if product:
            return jsonify({
                "error": "Product with this name already exists"
            }), 400
        # Add product to database
        db_conn.add_product(new_product)
        return jsonify({
            "message": "Product created successfully",
            "product": db_conn.get_product_by_name(name)
            }), 201

    @jwt_required
    def get(self, product_id=None):
        """
        Get all products
        """
        # Check if an id has been passed
        if product_id:
            product = db_conn.get_product_by_id(int(product_id))
            # Check if product doesn't exist
            if not product:
                return jsonify({
                    "error": "This product does not exist"
                }), 404
            return jsonify({
                "message": "Product returned successfully",
                "product": product
                })
        # Get all products
        products = db_conn.get_products()
        return jsonify({
            "message": "Products returned successfully",
            "products": products
        })
    
    @jwt_required
    def put(self, product_id):
        """
        Funtion to modify a product
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # # Check if it's not store owner
        if not loggedin_user["is_admin"]:
            return jsonify({
                "error": "Please login as a store owner"
            }), 403
        
        res = validate_product(request)
        if res:
            return res
        
        # Check if product exists
        product = db_conn.get_product_by_id(int(product_id))
        if not product:
            return jsonify({
                "error": "The product you're trying to modify doesn't exist"
            }), 404

        data = request.get_json()
        # Get the fields which were sent
        name = data.get("name")
        unit_cost = data.get("unit_cost")
        quantity = data.get("quantity")
        category_id = data.get("category_id")            
        
        # Modify product
        db_conn.update_product(name=name, unit_cost=unit_cost, quantity=quantity, 
                               product_id=int(product_id), category_id=category_id)
        return jsonify({
            "message": "Product updated successfully",
            "product": db_conn.get_product_by_id(product_id)
        })
    
    @jwt_required
    def delete(self, product_id):
        """
        Funtion to delete a product
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # Check if it's not store owner
        if not loggedin_user["is_admin"]:
            return jsonify({
                "error": "Please login as a store owner"
            }), 403
        
        # Check if product exists
        product = db_conn.get_product_by_id(int(product_id))
        if not product:
            return jsonify({
                "error": "Product you're trying to delete doesn't exist"
            }), 404

        # Delete product
        db_conn.delete_product(int(product_id))
        return jsonify({
            "message": "Product has been deleted successfully"
        })


class SaleView(MethodView):
    """
    Class to perform http methods on sales
    """
    @jwt_required
    def post(self):
        """
        Method to create a sale record
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # Check if it's a store owner
        if loggedin_user["is_admin"]:
            return jsonify({
                "error": "Please login as a store attendant"
            }), 403

        # Validate the data
        res = validate_cart_item(request)
        if res:
            return res
        data = request.get_json()
        product_id = data.get("product_id")
        # Get the product to from db
        product = db_conn.get_product_by_id(product_id)
        quantity = data.get("quantity")
        # Calculate the total
        total = product["unit_cost"] * quantity
        new_quantity = product["quantity"] - quantity
        # Update the product quantity
        db_conn.update_product(name=product["name"], unit_cost=product["unit_cost"],
                               quantity=new_quantity, product_id=product_id)
        # Make the sale
        new_sale = Sale(loggedin_user["id"], product_id, quantity, total)
        db_conn.add_sale(sale=new_sale)
        return jsonify({
            "message": "Sale made successfully"
            }), 201

    @jwt_required
    def get(self, sale_id=None):
        """
        Perform GET on sale records
        """
        # Get current user
        current_user = get_jwt_identity()
        user = db_conn.get_user(current_user)
        msg = None
        # run if request is for a single sale record
        if sale_id:
            # Get a single sale record
            sale_record = db_conn.get_single_sale(int(sale_id))
            status_code = 200
            # # Check if sale doesn't exist
            if not sale_record:
                msg = {"error": "Sale record with this id doesn't exist"}
                status_code = 404
            # run if it's a store owner
            elif user["is_admin"]:
                msg = {"message": "Sale record returned successfully", "sale_record": sale_record}
            # run if it's a store attendant
            elif sale_record["attendant_id"] == db_conn.get_user(current_user)["id"]:
                msg = {"message": "Sale record returned successfully", "sale_record": sale_record}
            else:
                msg = {"error": "You didn't make this sale"}
                status_code = 403
            if msg:
                return jsonify(msg), status_code
        # run if request is for all sale records and if it's a store
        # owner
        if user["is_admin"]:
            sale_records = db_conn.get_sale_records()
            msg = {"message": "Sale records returned successfully", "sale_records": sale_records}
        # run if request is for all sale records and if it's a store
        # attendant
        elif not user["is_admin"]:
            sale_records = db_conn.get_sale_records_user(user["id"])
            msg = {"message": "Sale records returned successfully", "sale_records": sale_records}
        if msg:
            return jsonify(msg)


class CategoryView(MethodView):
    """
    Handles http methods on category
    """

    @jwt_required
    def post(self):
        """
        Function to create category
        """
        # Get logged in user
        current_user = get_jwt_identity()
        user = db_conn.get_user(current_user)
        # Check if it's store attendant
        if not user["is_admin"]:
            return jsonify({
                "error": "Please login as a store owner"
            }), 403
        res = validate_category(request)
        if res:
            return res
        # Get data sent
        data = request.get_json()
        name = data.get("name")
        description = data.get("description")
        # Get a specific category
        category = db_conn.get_category_by_name(name)
        new_category = Category(name, description=description)
        # Add category to database
        db_conn.add_category(new_category)
        return jsonify({
            "message": "Successfully created product category",
            "category": db_conn.get_category_by_name(name)
        }), 201

    @jwt_required
    def put(self, category_id):
        """
        Function to modify a category
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # # Check if it's not store owner
        if not loggedin_user["is_admin"]:
            return jsonify({
                "error": "Please login as a store owner"
            }), 403
        
        # Check if category exists
        category = db_conn.get_category_by_id(int(category_id))
        if not category:
            return jsonify({
                "error": "The category you're trying to modify doesn't exist"
            }), 404

        data = request.get_json()
        # Get the fields which were sent
        name = data.get("name")
        description = data.get("description")
        if not name:
            return jsonify({
                "error": "The category name is required"
            }), 400
        
        # Modify category
        db_conn.update_category(name, description, category_id)
        return jsonify({
            "message": "Category updated successfully",
            "category": db_conn.get_category_by_id(int(category_id))
        })

    @jwt_required
    def delete(self, category_id):
        """
        Funtion to category a product
        """
        # Get logged in user
        current_user = get_jwt_identity()
        loggedin_user = db_conn.get_user(current_user)
        # Check if it's not store owner
        if loggedin_user["is_admin"]:
            # Check if category exists
            category = db_conn.get_category_by_id(int(category_id))
            if not category:
                return jsonify({
                    "error": "Category you're trying to delete doesn't exist"
                }), 404

            # Delete category
            db_conn.delete_category(int(category_id))
            return jsonify({
                "message": "Category has been deleted successfully"
            })
        return jsonify({
            "error": "Please login as a store owner"
        }), 403


# Map urls to view classes
app.add_url_rule('/api/v2/auth/login',
                 view_func=LoginView.as_view('login_view'))
app.add_url_rule('/api/v2/auth/signup',
                 view_func=RegisterView.as_view('register_view'))
app.add_url_rule('/api/v2/products',
                 view_func=ProductView.as_view('product_view'),
                 methods=["GET", "POST"])
app.add_url_rule('/api/v2/products/<product_id>',
                 view_func=ProductView.as_view('product_view1'),
                 methods=["GET", "PUT", "DELETE"])
app.add_url_rule('/api/v2/sales',
                 view_func=SaleView.as_view('sale_view'),
                 methods=["GET","POST"])
app.add_url_rule('/api/v2/sales/<sale_id>',
                 view_func=SaleView.as_view('sale_view1'), methods=["GET"])
app.add_url_rule('/api/v2/categories',
                 view_func=CategoryView.as_view('category_view'),
                 methods=["POST"])
app.add_url_rule('/api/v2/categories/<category_id>',
                 view_func=CategoryView.as_view('category_view1'), 
                 methods=["PUT", "DELETE"])
