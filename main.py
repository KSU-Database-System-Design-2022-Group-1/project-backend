import sys
from functools import wraps
import inspect

from typing import Any
from collections.abc import Callable
from types import GenericAlias

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

# DECORATORS

def catch_exception(fn):
	@wraps(fn)
	def inner():
		try:
			return { 'success': True, **fn() }
		except Exception as e:
			return { 'success': False, 'error': type(e).__name__, 'message': str(e) }
	return inner

# Provides the function with a "form" dictionary containing all the
# keys specified in `types`, converted to their corresponding type value.
def fill_dict_from_form(types: dict[str, Callable[[str], Any]]):
	def inner_decorator(fn):
		@wraps(fn)
		def inner():
			form = {}
			for param, ty in types.items():
				if ty == list:
					# special case: return a list of strings
					form[param] = request.form.getlist(param)
				elif isinstance(ty, GenericAlias):
					# special case: return a list of [generic type]
					if ty.__origin__ == list:
						form[param] = request.form.getlist(param, type=ty.__args__[0])
					else:
						raise Exception("unknown generic")
				else:
					form[param] = request.form.get(param, type=ty)
			return fn(form)
		return inner
	return inner_decorator

# Looks at the function's type hints to fill in the corresponding arguments
# from the request.form object, converting the strings to the types specified.
def fill_params_from_form(fn):
	@wraps(fn)
	def inner():
		args = {}
		for param, info in inspect.signature(fn).parameters.items():
			ty = str if info.annotation == inspect.Parameter.empty else info.annotation
			if ty == list:
				# special case: return a list of strings
				args[param] = request.form.getlist(param)
			elif isinstance(ty, GenericAlias):
				# special case: return a list of [generic type]
				if ty.__origin__ == list:
					args[param] = request.form.getlist(param, type=ty.__args__[0])
				else:
					raise Exception("unknown generic")
			else:
				args[param] = request.form.get(param, type=ty)
		return fn(**args)
	return inner

# ROUTES

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

@app.route("/cart/list", methods=['GET'])
@catch_exception
@fill_params_from_form
def cart_list(customer: int):
	return { 'items': actions.get_cart(cur, customer) }

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
