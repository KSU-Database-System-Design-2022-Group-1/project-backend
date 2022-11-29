import sys

from mariadb import Cursor, Connection, mariadb
import flask

# copy paste from the thing
# https://mariadb.com/docs/connect/programming-languages/python/

class SomethingHappenedError(Exception):
	pass

class Database:
	def __init__(self, cur: Cursor):
		self.cur = cur
		self.cur.execute("USE kstores;")
	
	# Returns the total price and weight (in a tuple, in that order) of the cart.
	def get_cart_info(self, customer_id: int):
		self.cur.execute("""
			SELECT COALESCE(SUM(price), 0), COALESCE(SUM(weight), 0)
			FROM shopping_cart JOIN variant_catalog USING (item_id, variant_id)
			WHERE customer_id = ?;
			""", (customer_id,))
		
		# If shopping cart empty, returns (0, 0)
		# otherwise, returns (price, weight)
		return self.cur.fetchone()
	
	# # Automatically handled in item creation functions,
	# # should not be exposed to API users.
	# def get_next_variant_id(self, item_id) -> int:
	# 	self.cur.execute("""
	# 		SELECT COALESCE(MAX(variant_id)+1, 0)
	# 		FROM variant_catalog
	# 		WHERE item_id = ?;
	# 		""", (item_id,))
	# 	
	# 	return self.cur.fetchone()
	
	# Creates a catalog item and returns its new item_id.
	def create_catalog_item(
		self,
		name: str, description: str, category: str,
		variants: list[tuple[ str, str, float, float, int ]],
	) -> int:
		self.cur.execute("""
			INSERT INTO item_catalog (item_name, description, category, item_image)
			VALUES (?, ?, ?, NULL);
			""", (name, description, category))
		
		# Save auto-incrementing item_id
		item_id = self.cur.lastrowid
		
		next_variant_id = 1 # self.get_next_variant_id(item_id)
		
		variants_indexed = [ (item_id, variant_id) + variant
			for (variant_id, variant)
			in enumerate(variants, next_variant_id) ]
		
		self.cur.executemany("""
			INSERT INTO variant_catalog (
				item_id, variant_id,
				size, color,
				price, weight,
				stock)
			VALUES (
				?, ?,
				?, ?,
				?, ?,
				?);
			""", variants_indexed)
		
		# Return the auto-generated item_id
		return item_id
	
	# Creates a single catalog item variant.
	# Don't use unless you really have to.
	def create_catalog_item_variant(
		self,
		item_id: int, variant_id: int | None,
		size: str, color: str,
		price: float, weight: float,
		stock: int = 1,
	):
		params = (
			item_id, variant_id,
			size, color,
			price, weight,
			stock
		)
		
		# TODO: looks gross
		
		if variant_id is None:
			params = (item_id, item_id) + params[2:]
			
			# Hopefully will execute atomically:
			self.cur.execute("""
				INSERT INTO variant_catalog (
					item_id, variant_id,
					size, color,
					price, weight,
					stock,
					variant_image
				) VALUES (
					?, (
						SELECT COALESCE(MAX(tmp.variant_id) + 1, 0)
						FROM variant_catalog AS tmp
						WHERE tmp.item_id = ?
					),
					?, ?,
					?, ?,
					?,
					NULL);
				""", params)
		else:
			self.cur.execute("""
				INSERT INTO variant_catalog (
					item_id, variant_id,
					size, color,
					price, weight,
					stock,
					variant_image
				) VALUES (
					?, ?,
					?, ?,
					?, ?,
					?,
					NULL);
				""", params)
	
	def add_to_cart(
		self,
		customer_id: int,
		item_id: int, variant_id: int,
		quantity: int = 1
	):
		self.cur.execute("""
			INSERT INTO shopping_cart (customer_id, item_id, variant_id, quantity)
			VALUES (?, ?, ?, ?);
			""", (customer_id, item_id, variant_id, quantity))
	
	def place_order(self, customer_id: int) -> int:
		# Calculate total price and weight of shopping cart items.
		(price, weight) = self.get_cart_info(customer_id)
		
		# Create a new order and fill it with info from the shopping cart.
		self.cur.execute("""
			INSERT INTO `order` (
				customer_id,
				shipping_address,
				total_price, total_weight,
				status
			) VALUES (
				?,
				(
					SELECT shipping_address
					FROM customer AS tmp
					WHERE tmp.customer_id = ?
				),
				?, ?,
				NULL
			);
			""", (customer_id, customer_id, price, weight))
		# One of the default fields will be order_id,
		# the primary key which is auto-incremented.
		
		# We could just use LAST_INSERT_ID for everything,
		# but it'd be useful to return the new order_id to
		# Python so future queries can more easily use it:
		order_id = cur.lastrowid
		
		# Insert items from shopping cart into newly-created order.
		self.cur.execute("""
			INSERT INTO order_item
			SELECT ? AS order_id, item_id, variant_id, quantity
			FROM shopping_cart
			WHERE customer_id = ?;
			""", (order_id, customer_id))
		
		# TODO: decrement stock for items in shopping cart
		# (but what if we take too many items?)
		# (and what if Alice buys out all the stock of some item
		# Bob has in his cart before he checks out his cart?)
		
		# Remove them from shopping cart now that they're copied over.
		self.cur.execute("""
			DELETE FROM shopping_cart
			WHERE customer_id = ?;
			""", (customer_id,))
		
		# Finally, set the status to 'ordered'.
		self.cur.execute("""
			UPDATE `order`
			SET status = 'ordered'
			WHERE order_id = ?;
			""", (order_id,))
		
		# Return the new order's order_id.
		return order_id

def test_create_item_with_variants(db: Database) -> int:
	return db.create_catalog_item("Kent Shirt", "A shirt with the KSU logo", 'shirt', [
		('M', 'Blue', 19.95, 1.07, 1),
		('L', 'Green', 20.95, 1.24, 1),
		('XS', 'Green', 18.65, 0.92, 1)
	])

def test_shop_two_items_and_order(db: Database, customer_id, items):
	import random
	db.add_to_cart(customer_id, random.choice(items), random.randint(1, 3))
	db.place_order(customer_id)

def test_create_more_variants_afterward(db: Database, item_id: int):
	db.create_catalog_item_variant(item_id, None, 'XL', 'Solid Gold', 99.99, 120.0, 1)
	db.create_catalog_item_variant(item_id, 99, 'S', 'NFT', 990.99, 0.0, 1)

# def test_search_for_items(db: Database):
# 	db

def run_tests(db: Database):
	db.cur.execute("""
		INSERT INTO customer (
			first_name, middle_name, last_name,
			shipping_address, billing_address,
			email, password, phone_number
		)
		VALUES (
			'jim', NULL, 'me',
			NULL, NULL,
			'jim@cool.tld', 'hunter2', '3304206969'
		)
	""")
	guy = db.cur.lastrowid
	print(f"made up a guy. {guy}")
	
	db.cur.execute("""
		INSERT INTO address (
			street_number, street_name, street_apt,
			city, state, zip
		) VALUES (
			'123', 'among st', NULL,
			'Akron', 'OH', '44240'
		)
	""")
	addr = db.cur.lastrowid
	db.cur.execute("""
		UPDATE customer
		SET
			shipping_address = ?,
			billing_address = ?
		WHERE customer_id = ?;
	""", (addr, addr, guy))
	print("He has an Address and a Phone Number.")
	
	item1 = test_create_item_with_variants(db)
	item2 = test_create_item_with_variants(db)
	test_create_more_variants_afterward(db, item2)
	print("created all sorts of items.")
	
	test_shop_two_items_and_order(db, guy, [item1, item2])
	print("the guy bought two items and checked out.")

try:
	# Connect to the database.
	conn = mariadb.connect(
		host = "localhost",
		port = 3306,
		user = "root")
	
	if not isinstance(conn, Connection):
		print("Connection :(")
		raise SomethingHappenedError
	
	# Make a cursor into the database.
	cur = conn.cursor()
	
	if not isinstance(cur, Cursor):
		print("Cursor :(")
		raise SomethingHappenedError
	
	# Helper Object
	db = Database(cur)
	# run_tests(db)
	
	# Save everything you've done, then
	# close connection to the database.
	db.cur.close()
	conn.commit()
	conn.close()
	
except mariadb.Error as e:
	print(f"Database Error:\n{e}")
	sys.exit(1)
