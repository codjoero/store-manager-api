"""
File to handle application views
"""
from flask import jsonify, request
from flask.views import MethodView
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import (create_access_token, 
                                jwt_required, 
                                get_jwt_identity)
from api.models import User
from api.__init__ import app
from api.utils.validators import validate_login_data, validate_register_data
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


# Map urls to view classes
app.add_url_rule('/api/v2/auth/login',
                 view_func=LoginView.as_view('login_view'))
app.add_url_rule('/api/v2/auth/signup',
                 view_func=RegisterView.as_view('register_view'))
