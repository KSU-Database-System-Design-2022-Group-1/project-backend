import sys, os

from mariadb import mariadb, Cursor, Connection
from flask import Flask, request, send_file

import actions
from decorators import catch_exception, fill_dict_from_form, fill_params_from_form

# FIXME: mariadb connection only has threadsafety of 1..
# pool: ConnectionPool = None # type: ignore
cur: Cursor = None # type: ignore
conn: Connection = None # type: ignore

app = Flask(__name__)

if not os.path.exists("./images"):
	os.mkdir("./images")

app.config["DEBUG"] = True

db_config = {
	'host': 'localhost',
	'port': 3306,
	'user': 'root',
	'database': 'kstores'
}

# ROUTES

@app.route("/customer/signup", methods=['POST'])
@catch_exception
@fill_dict_from_form({
	'first_name': str, 'middle_name': str, 'last_name': str,
	'email': str, 'password': str,
	'phone_number': str,
	
	'shipping_street_number': str, 'shipping_street_name': str,
	'shipping_street_apt': str, # | None,
	'shipping_city': str, 'shipping_state': str, 'shipping_zip': int,
	
	'billing_street_number': str, 'billing_street_name': str,
	'billing_street_apt': str, # | None,
	'billing_city': str, 'billing_state': str, 'billing_zip': int
})
def create_customer(form):
	shipping_id = actions.create_address( cur,
		form['shipping_street_number'], form['shipping_street_name'],
		form['shipping_street_apt'],
		form['shipping_city'], form['shipping_state'], form['shipping_zip']
	)
	billing_id = actions.create_address( cur,
		form['billing_street_number'], form['billing_street_name'],
		form['billing_street_apt'],
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

@app.route("/catalog/search", methods=['GET'])
@catch_exception
@fill_dict_from_form({
	'name': list[str],
	'category': list[str],
	'size': list[str],
	'color': list[str],
	'instock': bool,
})
def catalog_list(form):
	return { 'items': actions.search_catalog( cur, **form ) }

@app.route("/image/create", methods=['POST'])
@catch_exception
def create_image():
	image_req = request.files['image']
	image_id = actions.create_image(cur, image_req.mimetype, request.form.get('alt_text'))
	image_req.save(f"./images/{image_id}")
	return { 'image': image_id }

@app.route("/image/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def get_image(image: int):
	(mime_type, _) = actions.get_image_info(cur, image)
	return send_file(f"./images/{image}", mimetype=mime_type)

@app.route("/cart/list", methods=['GET'])
@catch_exception
@fill_params_from_form
def cart_list(customer: int):
	return { 'items': actions.get_cart(cur, customer) }

@app.route("/catalog/get", methods=['GET'])
@catch_exception
@fill_params_from_form
def get_item_info(item: int):
	return actions.get_item_info(cur, item)

@app.route("/cart/add", methods=['POST'])
@catch_exception
@fill_params_from_form
def add_to_cart(customer: int, item: int, variant: int):
	return { 'items': actions.add_to_cart(cur, customer, item, variant) }

@app.route("/cart/checkout", methods=['POST'])
@catch_exception
@fill_params_from_form
def checkout(customer: int):
	return { 'order_id': actions.place_order(cur, customer) }

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
<form>
	<input type=number name=customer_id value=1 />
	<input action="/cart/list" formmethod=get type=submit value="List Cart Items" />
</form>"""
	return {
		'form': request.form,
		'url': request.args,
		'cookies': request.cookies
	}

# https://mariadb.com/docs/connect/programming-languages/python/

try:
	# # Set up a connection pool
	# pool = mariadb.ConnectionPool(
	# 	pool_name = 'kstores_pool', pool_size = 4,
	# 	**db_config
	# )
	
	# Connect to the database.
	conn = mariadb.connect(**db_config) # type: ignore
	
	if not isinstance(conn, Connection):
		print("Connection :(")
		raise Exception
	
	# Make a cursor into the database.
	cur = conn.cursor()
	
	# Run the server
	app.run()
	
except mariadb.Error as e:
	print(f"Database Error ({e.__name__}):\n{e}")
	sys.exit(1)
	
except Exception as e:
	print(repr(e))
	
finally:
	if isinstance(cur, Cursor):
		cur.close()
	
	# Save everything you've done, then
	# close connection to the database.
	if isinstance(conn, Connection):
		conn.commit()
		conn.close()
