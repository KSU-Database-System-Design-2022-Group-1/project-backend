from functools import wraps
import inspect
from typing import Any
from types import GenericAlias, NoneType

from flask import request
from mariadb import mariadb, Cursor, Connection, ConnectionPool

db_config = {
	'host': 'localhost',
	'port': 3306,
	'user': 'root',
	'database': 'kstores'
}

# Set up a connection pool
pool = mariadb.ConnectionPool(
	pool_name = 'kstores_pool', pool_size = 16,
	**db_config
)

def db_connect(pool: ConnectionPool):
	def inner_decorator(fn):
		@wraps(fn)
		def inner(cur, *arg, **args):
			r = fn(cur, *arg, **args)
			return r
		return inner
	return inner_decorator

def catch_exception(fn):
	@wraps(fn)
	def inner():
		try:
			r = fn()
			if isinstance(r, dict):
				return { 'success': True, **r }, 200
			else:
				return r, 200
		except Exception as e:
			print(type(e).__name__, str(e))
			return { 'success': False, 'error': type(e).__name__, 'message': str(e) }, 500
	return inner

# Provides the function with a "form" dictionary containing all the
# keys specified in `types`, converted to their corresponding type value.
def fill_dict_from_form(types: dict[str, type]):
	def inner_decorator(fn):
		@wraps(fn)
		def inner():
			form = {}
			conn = pool.get_connection()
			if conn is None:
				raise Exception("out of connections")
			cur = conn.cursor()
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
				if form[param] == "" \
				or form[param] == [""] \
				or form[param] == []:
					form[param] = None
			r = fn(cur, form)
			cur.close()
			conn.commit()
			conn.close()
			return r
		return inner
	return inner_decorator

# Looks at the function's type hints to fill in the corresponding arguments
# from the request.form object, converting the strings to the types specified.
def fill_params_from_form(fn):
	@wraps(fn)
	def inner():
		args = {}
		conn = pool.get_connection()
		if conn is None:
			raise Exception("out of connections")
		cur = conn.cursor()
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
			elif param == 'cur':
				continue
			else:
				args[param] = request.form.get(param, type=ty)
			if args[param] == "" \
			or args[param] == [] \
			or args[param] == [""]:
				args[param] = None
		r = fn(cur, **args)
		cur.close()
		conn.commit()
		conn.close()
		return r
	return inner

# TODO: it'd be nice if these handled optionals and raised an error if they were absent.
#  it's not a requirement. our frontend is in our control, so we can simply check these
#  frontend-side. also, most actions will raise an SQL error if they're missing an arg.
