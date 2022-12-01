import sys
from functools import wraps
from typing import Any, Dict, List, Tuple

from mariadb import mariadb, Cursor, Connection
from flask import Flask, request

import actions

cur, conn = None, None
app = Flask(__name__)

app.config["DEBUG"] = True

db_config = {
	'host': 'localhost',
	'port': 3306,
	'user': 'root',
	'database': 'kstores'
}

# TODO: extend to catch and explain database errors as well
def catch_exception(fn, msg="Server error."):
	@wraps(fn)
	def inner():
		try:
			return { 'success': True, **fn() }
		except:
			return { 'success': False, 'message': msg }
	return inner

@app.route("/catalog/search", methods=['GET'])
@catch_exception
def catalog_list():
	r = actions.search_catalog(cur, category="shirt", color=["red", 'blue'], instock=True)
	return { 'items': r }

@app.route("/cart/list", methods=['GET'])
@catch_exception
def cart_list():
	customer_id = request.form.get('customer_id')
	if customer_id and customer_id.isnumeric():
		customer_id = int(customer_id)
		return { 'success': True, 'items': actions.get_cart(cur, customer_id) }
	else:
		return { 'success': False, 'message': "Supply a valid customer_id." }

@app.route("/cart/add", methods=['POST'])
@catch_exception
def add_to_cart():
	customer_id = request.form.get('customer_id')
	if customer_id and customer_id.isnumeric():
		customer_id = int(customer_id)
		return { 'success': True, 'items': actions.add_to_cart(cur, customer_id,) }
	else:
		return { 'success': False, 'message': "Supply a valid customer_id." }

@app.route("/cart/checkout", methods=['POST'])
@catch_exception
def checkout():
	try:
		return { 'success': True, 'order_id': actions.place_order(cur, 11) }
	except:
		return { 'success': False, 'message': "Server error." }

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
	<input formaction="/catalog/search" formmethod=get type=submit value="List Catalog Items" />
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
	# Connect to the database.
	conn = mariadb.connect(**db_config)
	
	if not isinstance(conn, Connection):
		print("Connection :(")
		raise Exception
	
	# Make a cursor into the database.
	cur = conn.cursor()
	
	# Run the server
	app.run()
	
except mariadb.Error as e:
	print(f"Database Error:\n{e}")
	sys.exit(1)
	
except Exception as e:
	print(e)
	
finally:
	if isinstance(cur, Cursor):
		cur.close()
	
	# Save everything you've done, then
	# close connection to the database.
	if isinstance(conn, Connection):
		conn.commit()
		conn.close()
