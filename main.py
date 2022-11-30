import sys
import json

from mariadb import Cursor, Connection, mariadb
import flask

import actions

cur, conn = None, None
app = flask.Flask(__name__)

app.config["DEBUG"] = True # it's how it is

db_config = {
	'host': 'localhost',
	'port': 3306,
	'user': 'root',
	'database': 'kstores'
}

@app.route("/cart/checkout", methods=['POST'])
def checkout():
	return json.dumps({ 'success': True, 'order_id': actions.place_order(cur, 11) })

# https://mariadb.com/docs/connect/programming-languages/python/

# More convenient query format. Emulates Python formatting with named args.
# Replace your ?s with {}s to make my life easier.
def convenient(query: str, *ordered_args: list[type], **named_args: dict[str, type]) -> tuple[str, list[type]]:
	class IDunno():
		def __init__(cur): pass
		def __getitem__(cur, _) -> str: return '?'
	
	class NoRightBracketException(Exception): pass
	
	args = []
	next_ordered_index = 0
	
	other_bracket = 0
	next_bracket = query.find('{')
	while next_bracket >= 0:
		other_bracket = query.find('}', next_bracket)
		
		if other_bracket < 0:
			raise NoRightBracketException
		
		inner = query[(next_bracket + 1):other_bracket]
		print(next_bracket, other_bracket, inner)
		
		if inner.isnumeric():
			args.append(ordered_args[int(inner)])
		elif inner:
			args.append(named_args[inner])
		else:
			args.append(ordered_args[next_ordered_index])
			next_ordered_index += 1
		
		next_bracket = query.find('{', other_bracket + 1)
	
	return (query.replace('{}','?').format_map(IDunno()), args)

try:
	# Connect to the database.
	conn = mariadb.connect(**db_config)
	
	if not isinstance(conn, Connection):
		print("Connection :(")
		raise Exception
	
	# Make a cursor into the database.
	cur = conn.cursor()
	
	if not isinstance(cur, Cursor):
		print("Cursor :(")
		raise Exception
	
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
