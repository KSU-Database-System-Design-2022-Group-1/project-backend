from functools import wraps
import inspect
from typing import Any
from types import GenericAlias, NoneType

from flask import request

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
def fill_dict_from_form(types: dict[str, type]):
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
