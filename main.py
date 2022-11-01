import sys

import mariadb
import flask

# copy paste from the thing
# https://mariadb.com/docs/connect/programming-languages/python/

# keeping this example but unused for now
def print_contacts(cur):
	"""Retrieves the list of contacts from the database and prints to stdout"""
	
	# Initialize Variables
	contacts = []

	# Retrieve Contacts
	cur.execute("SELECT first_name, last_name, email FROM test.contacts")

	# Prepare Contacts
	for (first_name, last_name, email) in cur:
		contacts.append(f"{first_name} {last_name} <{email}>")

	# List Contacts
	print("\n".join(contacts))

# Try to connect to MariaDB
try:
	conn = mariadb.connect(
		host = "localhost",
		port = 3306,
		user = "root")
	
	# Instantiate Cursor
	cur = conn.cursor()
	
	print("oh hi server. ok now i'm leaving")
	
	# Close Connection
	conn.close()
except mariadb.Error as e:
	print(f"Error connecting to the database: {e}")
	sys.exit(1)
