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
	
	# Creates a catalog item and returns its new item_id.
	def create_catalog_item(
		self,
		name: str, description: str, category: str
	) -> int:
		self.cur.execute("""
			INSERT INTO item_catalog (item_name, description, category, item_image)
			VALUES (?, ?, ?, NULL);
			""", (name, description, category))
		
		# Return auto-incrementing item_id
		return self.cur.lastrowid
	
	# Creates a catalog item variant.
	# You must come up with a new variant_id.
	def create_catalog_item_variant(
		self,
		item_id: int, variant_id: int,
		size: str, color: str,
		price: float, weight: float,
		stock: int = 1
	):
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
			""", (
				item_id, variant_id,
				size, color,
				price, weight,
				stock
			))
	
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
	
	def place_order(self, customer_id: int):
		# Create a new empty order with default fields.
		self.cur.execute("""
			INSERT INTO `order` (customer_id)
			VALUES (?);
			""", (customer_id,))
		# One of the default fields will be order_id,
		# the primary key which is auto-incremented.
		
		# Thanks to LAST_INSERT_ID, we don't need to fetch
		# the auto-incremented order_id, but if we needed:
		#   order_id = cur.lastrowid
		print(self.cur.lastrowid)
		
		# Insert items from shopping cart into newly-created order.
		self.cur.execute("""
			INSERT INTO order_item
			SELECT LAST_INSERT_ID() AS order_id, item_id, variant_id, quantity
			FROM shopping_cart
			WHERE customer_id = ?;
			""", (customer_id,))
		
		# Remove them from shopping cart now that they're copied over.
		self.cur.execute("""
			DELETE FROM shopping_cart
			WHERE customer_id = ?;
			""", (customer_id,))
		
		# Finally, update the other data about the order.
		# In our final store, these values will be derived.
		self.cur.execute("""
			UPDATE `order`
			SET	total_price = 44.59,
				total_weight = 4.2,
				status = 'ordered'
			WHERE order_id = LAST_INSERT_ID();
			""")

def test_create_item_with_variants(db: Database) -> int:
	i = db.create_catalog_item("Kent Shirt", "A shirt with the KSU logo", 'shirt')
	print(i)
	db.create_catalog_item_variant(i, 0, 'M', 'Blue', 19.95, 1.07)
	db.create_catalog_item_variant(i, 1, 'L', 'Green', 20.95, 1.24)
	db.create_catalog_item_variant(i, 2, 'XS', 'Green', 18.65, 0.92)
	return i

def test_shop_two_items_and_order(db: Database, customer_id, items):
	db.add_to_cart(customer_id, items, 0)
	db.add_to_cart(customer_id, items + 1, 2)
	db.place_order(customer_id)

# def test_search_for_items(db: Database):
# 	db

def run_tests(db: Database):
	db.cur.execute("""
		INSERT INTO customer (customer_id, first_name, middle_name, last_name, shipping_street_number, shipping_street_name, shipping_street_apt, shipping_city, shipping_state, shipping_zip, billing_street_number, billing_street_name, billing_street_apt, billing_city, billing_state, billing_zip, email, password, phone_number)
		VALUES (1, 'jim', NULL, 'me', '123', 'amongst', NULL, 'kent', 'OH', '44240', '123', 'amongst', NULL, 'kent', 'OH', '44240', 'jim@cool.site', 'hunter2', '3304206969')
	""")
	guy = db.cur.lastrowid
	print(f"made up a guy. {guy}")
	
	item1 = test_create_item_with_variants(db)
	item2 = test_create_item_with_variants(db)
	print("created all sorts of items.")
	
	test_shop_two_items_and_order(db, guy, item1)
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
	run_tests(db)
	
	# Save everything you've done, then
	# close connection to the database.
	db.cur.close()
	conn.commit()
	conn.close()
	
except mariadb.Error as e:
	print(f"Error connecting to the database: {e}")
	sys.exit(1)
