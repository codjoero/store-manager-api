from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import (jwt_required, 
                                get_jwt_identity)
from api.models import Sale
from api.__init__ import app
from api.utils.validators import validate_cart_item
from db import DB


db_conn = DB()

def formart_sale(sale_record):
    product = db_conn.get_product_by_id(int(sale_record["product_id"]))
    attendant = db_conn.get_user_by_id(int(sale_record["attendant_id"]))
    sale_record["product_name"] = product["name"]
    sale_record["attendant"] = attendant["first_name"] + " " + attendant["last_name"]
    return sale_record


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
            elif user["is_admin"] or sale_record["attendant_id"] == db_conn.get_user(current_user)["id"]:
                sale = formart_sale(sale_record)
                msg = {"message": "Sale record returned successfully", "sale_record": sale}
            else:
                msg = {"error": "You didn't make this sale"}
                status_code = 403
            if msg:
                return jsonify(msg), status_code
        # run if request is for all sale records and if it's a store
        # owner
        sales = []
        sales_reverted = []
        if user["is_admin"]:
            sale_records = db_conn.get_sale_records()
            sale_records_reverted = db_conn.get_reverted_sale_records()
        # run if request is for all sale records and if it's a store
        # attendant
        elif not user["is_admin"]:
            sale_records = db_conn.get_sale_records_user(user["id"])
            sale_records_reverted = db_conn.get_sale_records_user_reverted(user["id"])
        for sale_record in sale_records:
            sale = formart_sale(sale_record)
            sales.append(sale)
        for reverted_sale_record in sale_records_reverted:
            sale = formart_sale(reverted_sale_record)
            sales_reverted.append(sale)
        msg = {
            "message": "Sale records returned successfully", 
            "sale_records": sales, 
            "sale_records_reverted": sales_reverted
            }
        if msg:
            return jsonify(msg)
    
    @jwt_required
    def put(self, sale_id):
        """
        Perform PUT on sale records
        """
        # Get current user
        current_user = get_jwt_identity()
        user = db_conn.get_user(current_user)
        if not user["is_admin"]:
            return jsonify({
                "error": "Please login as a store owner"
            }), 403
        sale_record = db_conn.get_single_sale(int(sale_id))
        if not sale_record:
            return jsonify({
                "error": "This sale record doesn't exist"
            }), 404
        db_conn.revert_sale_record(sale_record)
        product = db_conn.get_product_by_id(sale_record["product_id"])
        quantity = product["quantity"] + sale_record["quantity"]
        db_conn.update_product(name=product["name"], unit_cost=product["unit_cost"], 
                               quantity=quantity, category_id=product.get("category_id"), 
                               product_id=sale_record["product_id"])
        return jsonify({
            "message": "Sale record has been successfully reverted"
        }), 200


app.add_url_rule('/api/v2/sales',
                 view_func=SaleView.as_view('sale_view'),
                 methods=["GET","POST"])
app.add_url_rule('/api/v2/sales/<sale_id>',
                 view_func=SaleView.as_view('sale_view1'), methods=["GET", "PUT"])
