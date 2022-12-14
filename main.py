import sys, os

from mariadb import mariadb, Cursor, Connection, ConnectionPool
from flask import Flask, request, send_file
from flask_cors import CORS

import actions
from decorators import catch_exception, db_connect, fill_dict_from_form, fill_params_from_form

app = Flask(__name__)
CORS(app)

if not os.path.exists("./images"):
	os.mkdir("./images")

app.config["DEBUG"] = True

# ROUTES

# - customer modify

@app.route("/customer/signin", methods=['GET'])
@catch_exception
@fill_params_from_form
def signin(cur: Cursor, email: str, password: str):
	(valid, customer) = actions.check_login(cur, email, password)
	return { 'valid': valid, 'customer': customer }

@app.route("/customer/signup", methods=['POST'])
@catch_exception
@fill_dict_from_form({
	'first_name': str, 'middle_name': str, 'last_name': str,
	'email': str, 'password': str,
	'phone_number': str,
	
	'shipping_street': str,
	'shipping_city': str, 'shipping_state': str, 'shipping_zip': int,
	
	'billing_street': str,
	'billing_city': str, 'billing_state': str, 'billing_zip': int
})
def create_customer(cur: Cursor, form):
	shipping_id = actions.create_address( cur,
		form['shipping_street'],
		form['shipping_city'], form['shipping_state'], form['shipping_zip']
	)
	billing_id = actions.create_address( cur,
		form['billing_street'],
		form['billing_city'], form['billing_state'], form['billing_zip']
	)
	customer_id = actions.create_customer( cur,
		form['first_name'], form['middle_name'], form['last_name'],
		form['email'], form['password'],
		form['phone_number'],
		shipping_id, billing_id
	)
	return {
		'customer': customer_id,
		'address': {
			'shipping': shipping_id,
			'billing': billing_id
		}
	}

@app.route("/customer/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def get_customer(cur: Cursor, customer: int):
	return actions.get_customer_info(cur, customer)

@app.route("/customer/edit", methods=['POST'])
@catch_exception
@fill_dict_from_form({
	'customer': int,
	
	'first_name': str, 'middle_name': str, 'last_name': str,
	'email': str, 'password': str,
	'phone_number': str
})
def edit_customer(cur: Cursor, form):
	customer = form['customer']
	actions.edit_customer( cur, customer, **form )
	return {}

@app.route("/address/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def get_address(cur: Cursor, address: int):
	return actions.get_address_info(cur, address)

@app.route("/address/edit", methods=['POST'])
@catch_exception
@fill_dict_from_form({
	'customer': int,
	'type': str, # Literal['shipping'] | Literal['billing'],
	
	'street': str, 'city': str, 'state': str, 'zip': int,
})
def edit_customer_address(cur: Cursor, form):
	customer = form['customer']
	address_type = form['type']
	return actions.update_customer_address(cur, customer, address_type, **form)

@app.route("/image/create", methods=['POST'])
@catch_exception
def create_image(cur: Cursor):
	image_req = request.files['image']
	image_id = actions.create_image(cur, image_req.mimetype, request.form.get('alt_text'))
	image_req.save(f"./images/{image_id}")
	return { 'image': image_id }

@app.route("/image/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def get_image(cur: Cursor, image: int):
	if image is None:
		raise Exception("no image with that id")
	x = actions.get_image_info(cur, image)
	mime_type = x['mime_type']
	return send_file(f"./images/{image}", mimetype=mime_type)

@app.route("/catalog/search", methods=['GET'])
@catch_exception
@fill_dict_from_form({
	'name': list[str],
	'category': list[str],
	'size': list[str],
	'color': list[str],
	'minprice': int,
	'maxprice': int,
	'instock': bool,
})
def catalog_list(cur: Cursor, form):
	return { 'items': actions.search_catalog( cur, **form ) }

@app.route("/catalog/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def get_item_info(cur: Cursor, item: int):
	return actions.get_item_info(cur, item)

@app.route("/cart/info", methods=['GET'])
@catch_exception
@fill_params_from_form
def cart_count(cur: Cursor, customer: int):
	return actions.get_cart_info(cur, customer)

@app.route("/cart/list", methods=['GET'])
@catch_exception
@fill_params_from_form
def cart_list(cur: Cursor, customer: int):
	return { 'items': actions.get_cart_items(cur, customer) }

@app.route("/cart/add", methods=['POST'])
@catch_exception
@fill_params_from_form
def add_to_cart(cur: Cursor, customer: int, item: int, variant: int, quantity: int):
	actions.add_to_cart(cur, customer, item, variant, quantity)
	return {}

# @app.route("/cart/remove", methods=['POST'])
# @catch_exception
# @fill_params_from_form()
# def remove_from_cart(customer: int, item: int, variant: int):
# 	actions.remove_from_cart(cur, customer, item, variant)
# 	return {}

@app.route("/cart/checkout", methods=['POST'])
@catch_exception
@fill_params_from_form
def checkout(cur: Cursor, customer: int):
	return { 'order': actions.place_order(cur, customer) }

@app.route("/order/list", methods=['GET'])
@catch_exception
@fill_params_from_form
def list_orders(cur: Cursor, customer: int):
	return { 'orders': actions.list_orders(cur, customer) }

@app.route("/order/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def list_order(cur: Cursor, order: int):
	return {
		**actions.get_order_info(cur, order),
		'items': actions.list_order_items(cur, order)
	}

# Secret zone where you can ???
@app.route("/echo", methods=['GET', 'POST'])
def aaa():
	if request.method == 'GET':
		return """<!DOCTYPE html>
<style>form { margin: 1em; }</style>
<form method=post>
	<input type=text name=abc placeholder="Hi!" />
	<input type=submit />
</form>
<hr />
<form>
	<input formaction="/catalog/search" formmethod=get type=submit value="List Catalog Items" />
	<input formaction="/catalog/search" formmethod=get type=submit value="List Catalog Items" />
</form>
<form action="/image/create" method=post enctype="multipart/form-data">
	<input type=file name=image /><label for=image>New Image</label>
	<input type=submit value="Upload" />
</form>
<div>
	<input type=number name=customer value=1 />
	<input type=submit value="Upload" />
	<img src="" />
</div>
<form>
	<input type=number name=customer value=1 />
	<input action="/cart/list" formmethod=get type=submit value="List Cart Items" />
</form>"""
	return {
		'form': request.form,
		'url': request.args,
		'cookies': request.cookies
	}

# https://mariadb.com/docs/connect/programming-languages/python/

try:
	
	# Connect to the database.
	# conn = mariadb.connect(**db_config) # type: ignore
	
	# Run the server
	app.run(port=3000)
	
except mariadb.Error as e:
	print(f"Database Error ({e.__name__}):\n{e}")
	sys.exit(1)
	
except Exception as e:
	print(repr(e))
