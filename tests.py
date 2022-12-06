import sys

from mariadb import Cursor, Connection, mariadb

import actions

# def test_create_item_with_variants(cur: Cursor) -> int:
# 	return actions.create_catalog_item(cur, "Kent Shirt", "A shirt with the KSU logo", 'shirt', [
# 		('M', 'Blue', 19.95, 1.07, 1),
# 		('L', 'Green', 20.95, 1.24, 1),
# 		('XS', 'Green', 18.65, 0.92, 1)
# 	])

def test_shop_two_items_and_order(cur: Cursor, customer_id: int, items: list[int]):
	import random
	actions.add_to_cart(cur, customer_id, random.choice(items), random.randint(1, 3))
	# actions.place_order(cur, customer_id)

# def test_create_more_variants_afterward(cur: Cursor, item_id: int):
# 	actions.create_catalog_item_variant(cur, item_id, None, 'XL', 'Solid Gold', 99.99, 120.0, 1)
# 	actions.create_catalog_item_variant(cur, item_id, 99, 'S', 'NFT', 990.99, 0.0, 1)

def run_tests(cur: Cursor):
	cur.execute("""
		INSERT INTO customer (
			first_name, middle_name, last_name,
			shipping_address, billing_address,
			email, password, phone_number
		)
		VALUES (
			'jim', NULL, 'me',
			NULL, NULL,
			'jim@cool.tld', 'hunter2', '3304206969'
		);
	""")
	guy: int = cur.lastrowid # type: ignore
	print(f"made up a guy. {guy}")
	
	cur.execute("""
		INSERT INTO address (
			street, city, state, zip
		) VALUES (
			'123 among st',
			'Akron', 'OH', '44240'
		);
	""")
	addr: int = cur.lastrowid # type: ignore
	cur.execute("""
		UPDATE customer
		SET
			shipping_address = ?,
			billing_address = ?
		WHERE customer_id = ?;
	""", (addr, addr, guy))
	print("He has an Address and a Phone Number.")
	
	# item1 = test_create_item_with_variants(cur)
	# item2 = test_create_item_with_variants(cur)
	# test_create_more_variants_afterward(cur, item2)
	# print("created all sorts of items.")
	
	test_shop_two_items_and_order(cur, guy, [1, 2])
	print("the guy bought two items and checked out.")

if __name__ == '__main__':
	try:
		# Connect to the database.
		conn = mariadb.connect(
			host = 'localhost',
			port = 3306,
			user = 'root',
			database = 'kstores'
		)
		
		if not isinstance(conn, Connection):
			print("Connection :(")
			raise Exception
		
		# Make a cursor into the database.
		cur = conn.cursor()
		
		# Helper Object
		run_tests(cur)
		
		# Save everything you've done, then
		# close connection to the database.
		cur.close()
		conn.commit()
		conn.close()
		
	except mariadb.Error as e:
		print(f"Database Error:\n{e}")
		sys.exit(1)
