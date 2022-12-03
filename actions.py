from typing import Any
from collections.abc import Callable

from mariadb import Cursor

sizes = ['XS', 'S', 'M', 'L', 'XL']

# Check if user's email/password pair is valid.
def check_login(cur: Cursor, email: str, password: str) -> bool:
	cur.execute("""
		SELECT COUNT(*)
		FROM accounts
		WHERE email = ?
		AND password = ?;
	""", (email, password))
	return bool(cur.fetchall()[0][0])

# Create a new customer with no set addresses.
def create_customer(
	cur: Cursor,
	first_name: str, middle_name: str, last_name: str,
	email: str, password: str,
	phone_number: str,
	shipping_addr: int | None = None,
	billing_addr: int | None = None
) -> int:
	cur.execute("""
		INSERT INTO customer (
			first_name, middle_name, last_name,
			shipping_address, billing_address,
			email, password,
			phone_number
		) VALUES (
			?, ?, ?,
			?, ?,
			?, ?,
			?
		)
	""", (
		first_name, middle_name, last_name,
		shipping_addr, billing_addr,
		email, password,
		phone_number
	))
	return cur.lastrowid # type: ignore

# Create a new address.
# (May return existing address_ids if they match.)
def create_address(
	cur: Cursor,
	street_number: str, street_name: str, street_apt: str | None,
	city: str, state: str, zip: int
) -> int:
	cur.execute("""
		SELECT MIN(address_id)
		FROM address
		WHERE street_number = ?
		AND	street_name = ?
		AND street_apt = ?
		AND city = ? AND state = ?
		AND zip = ?;
	""", (
		street_number, street_name, street_apt,
		city, state, zip
	))
	existing_address: int | None = cur.fetchone()[0]
	
	if existing_address is None:
		cur.execute("""
			INSERT INTO address (
				street_number, street_name,
				street_apt,
				city, state, zip
			) VALUES (?, ?, ?, ?, ?, ?);
		""", (
			street_number, street_name, street_apt,
			city, state, zip
		))
		return cur.lastrowid # type: ignore
	else:
		return existing_address # type: ignore

# Fancy search function.
# Set keyword args to add different types of filters.
# It'll construct a query using all of them.
def search_catalog(cur: Cursor, **filters):
	# The **filters thing is a keyword argument list.
	# It'll store a dict[str, Any] containing any other
	# keyword arguments you provide. Keyword arguments
	# are those things like name="jim" and such.
	# The great thing is that you aren't required to
	# include all of them, so you can skip the checks
	# you don't need.
	
	query = """
		SELECT
			item_id, variant_id,
			item_name, category,
			size, color,
			price, weight,
			COALESCE(variant_image, item_image) AS image_id
		FROM variant_catalog JOIN item_catalog USING (item_id)
		WHERE 1=1""" # (dummy expression to require use of AND)
	params = []
	
	# This is a list that maps a filter name to an SQL query,
	# and provides a function to turn an argument given with
	# the filter name into something that an SQL query can use.
	filters_map: dict[str, tuple[str, Callable[[Any], Any]]] = {
		'name':     ("item_name LIKE ?", lambda p: f"%{p}%"),
		'category': ("category = ?",     lambda p: str(p)),
		'size':     ("size = ?",         lambda p: p if p in sizes else None),
		'color':    ("LOWER(color) = ?", lambda p: str(p).lower()),
		'minprice': ("? <= price",       lambda p: float(p)),
		'maxprice': ("price <= ?",       lambda p: float(p)),
		'instock':  ("SIGN(stock) = ?",  lambda p: int(bool(p))),
	}
	
	# Build query from keyword arguments.
	for (f, p) in filters.items():
		if not p:
			continue
		
		query += "\nAND "
		
		(part, param_fn) = filters_map[f]
		
		# If it's a list and not just one value,
		if isinstance(p, list):
			# the SQL query should check if store items
			# match any single value in the list.
			query += '\nOR '.join([part]*len(p))
			
			# make a parameter out of each item in that list.
			params += [param_fn(pi) for pi in p]
		else:
			# Otherwise, it's pretty simple!
			query += part
			params.append(param_fn(p))
	query += ";"
	
	# Run query!
	cur.execute(query, params)
	
	return [{
		'id': { 'item': item_id, 'variant': variant_id },
		'name': item_name,
		'category': category,
		'size': size, # warning: nullable!
		'color': color, # warning: nullable!
		'price': price,
		'weight': weight,
		'image': image_id, # -> links to image endpoint?
	} for (
		item_id, variant_id,
		item_name, category,
		size, color,
		price, weight,
		image_id
	) in cur]

def create_image(cur: Cursor, mime_type: str, alt_text: str | None = None) -> int:
	cur.execute("""
		INSERT INTO catalog_images (
			mime_type, alt_text
		) VALUES (?, ?);
		""", (mime_type, alt_text))
	return cur.lastrowid # type: ignore

def get_image_info(cur: Cursor, image_id: int) -> tuple[str, str]:
	cur.execute("""
		SELECT mime_type, alt_text
		FROM catalog_images
		WHERE image_id = ?;
		""", (image_id,))
	(mime_type, alt_text) = cur.fetchone()
	return (mime_type, alt_text)

def get_item_info(cur: Cursor, item_id: int):
	cur.execute("""
		SELECT item_name, description, category, item_image
		FROM item_catalog
		WHERE item_id = ?;
		""", (item_id,))
	
	if cur.rowcount < 1:
		raise Exception("item not found")
	
	(item_name, description, category, item_image) = cur.fetchone()
	
	cur.execute("""
		SELECT item_id, variant_id,
			size, color,
			price, weight,
			COALESCE(variant_image, item_image) AS image_id
		FROM variant_catalog JOIN item_catalog USING (item_id)
		WHERE item_id = ?;
		""", (item_id,))
	variants = [{
		'id': { 'item': item_id, 'variant': variant_id },
		'size': size, # warning: nullable!
		'color': color, # warning: nullable!
		'price': price,
		'weight': weight,
		'image': image_id
	} for (
		item_id, variant_id,
		size, color,
		price, weight,
		image_id
	) in cur]
	
	return {
		'id': item_id,
		'name': item_name,
		'description': description,
		'category': category,
		'image': item_image,
		'variants': variants
	}

# Returns the items in the cart.
def get_cart_items(cur: Cursor, customer_id: int):
	cur.execute("""
		WITH this_cart (item_id, variant_id, quantity) AS (
			SELECT item_id, variant_id, quantity
			FROM shopping_cart
			WHERE customer_id = ? )
		SELECT
			item_id, variant_id,
			item_name,
			size, color,
			price, weight,
			quantity,
			COALESCE(variant_image, item_image) AS image_id
		FROM this_cart JOIN (
			variant_catalog JOIN item_catalog USING (item_id)
		) USING (item_id, variant_id);
		""", (customer_id,))
	
	return [{
		'id': { 'customer': customer_id, 'item': item_id, 'variant': variant_id },
		'name': item_name,
		'size': size, 'color': color,
		'price': price, 'weight': weight,
		'quantity': quantity,
		'image': image_id
	} for (
		item_id, variant_id,
		item_name,
		size, color,
		price, weight,
		quantity,
		image_id
	) in cur]

# Returns the total price and weight (in a tuple, in that order) of the cart.
def get_cart_info(cur: Cursor, customer_id: int):
	cur.execute("""
		SELECT COUNT(*), COALESCE(SUM(price), 0), COALESCE(SUM(weight), 0)
		FROM shopping_cart JOIN variant_catalog USING (item_id, variant_id)
		WHERE customer_id = ?;
		""", (customer_id,))
	
	(count, price, weight) = cur.fetchone()
	
	# If shopping cart empty, returns (0, 0, 0)
	# otherwise, returns (count, price, weight)
	return { 'count': count, 'price': price, 'weight': weight }

# Creates a catalog item and returns its new item_id.
def create_catalog_item(
	cur: Cursor,
	name: str, description: str, category: str,
	variants: list[tuple[ str, str, float, float, int ]],
) -> int:
	cur.execute("""
		INSERT INTO item_catalog (item_name, description, category, item_image)
		VALUES (?, ?, ?, NULL);
		""", (name, description, category))
	
	# Save auto-incrementing item_id
	item_id = cur.lastrowid
	
	next_variant_id = 1 # get_next_variant_id(item_id)
	
	variants_indexed = [
		(item_id, variant_id) + variant
		for (variant_id, variant)
		in enumerate(variants, next_variant_id) ]
	
	cur.executemany("""
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
	return item_id # type: ignore

# Creates a single catalog item variant.
# Don't use unless you really have to.
def create_catalog_item_variant(
	cur: Cursor,
	item_id: int, variant_id: int | None,
	size: str, color: str,
	price: float, weight: float,
	stock: int = 1, image: int | None = None
):
	params = (
		item_id, variant_id,
		size, color,
		price, weight,
		stock, image
	)
	
	if variant_id is None:
		params = (item_id, item_id) + params[2:]
		
		# Hopefully will execute atomically:
		cur.execute("""
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
				?);
			""", params)
	else:
		cur.execute("""
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
				?);
			""", params)

def add_to_cart(
	cur: Cursor,
	customer_id: int,
	item_id: int, variant_id: int,
	quantity: int = 1
):
	cur.execute("""
		REPLACE INTO shopping_cart (
			customer_id, item_id, variant_id, quantity
		) VALUES (?, ?, ?, ?);
		""", (customer_id, item_id, variant_id, quantity))
def remove_from_cart(
	cur: Cursor,
	customer_id: int,
	item_id: int | None, variant_id: int | None
):
	print("aaaa", item_id, variant_id)
	if item_id is None or variant_id is None:
		cur.execute("""
			DELETE FROM shopping_cart
			WHERE customer_id = ?;
			""", (customer_id,))
	else:
		cur.execute("""
			DELETE FROM shopping_cart
			WHERE customer_id = ?
			AND item_id = ?
			AND variant_id = ?;
			""", (customer_id, item_id, variant_id))

def place_order(cur: Cursor, customer_id: int) -> int:
	# Calculate total price and weight of shopping cart items.
	(price, weight) = get_cart_info(cur, customer_id)
	
	# Create a new order and fill it with info from the shopping cart.
	cur.execute("""
		INSERT INTO `order` (
			customer_id,
			order_date,
			shipping_address, billing_address,
			total_price, total_weight,
			status
		) VALUES (
			?,
			CURRENT_TIMESTAMP(),
			(
				SELECT shipping_address
				FROM customer AS tmp
				WHERE tmp.customer_id = ?
			),
			(
				SELECT billing_address
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
	cur.execute("""
		INSERT INTO order_item
		SELECT ? AS order_id, item_id, variant_id, quantity
		FROM shopping_cart
		WHERE customer_id = ?;
		""", (order_id, customer_id))
	
	# TODO: decrement stock for items in shopping cart
	# (but what if we take too many items?)
	# (and what if Alice buys out all the stock of some item
	# Bob has in his cart before he checks out his cart?)
	# TODO: lock / unlock variant table to set stock
	
	# Remove them from shopping cart now that they're copied over.
	cur.execute("""
		DELETE FROM shopping_cart
		WHERE customer_id = ?;
		""", (customer_id,))
	
	# Finally, set the status to 'ordered'.
	cur.execute("""
		UPDATE `order`
		SET status = 'ordered'
		WHERE order_id = ?;
		""", (order_id,))
	
	# Return the new order's order_id.
	return order_id # type: ignore

def list_orders(cur: Cursor, customer_id: int):
	cur.execute("""
		SELECT
			order_id, status,
			total_price, total_weight,
			order_date
		FROM `order`
		WHERE customer_id = ?;
	""", (customer_id,))
	
	return [{
		'id': { 'customer': customer_id, 'order': order_id },
		'status': status,
		'price': total_price, 'weight': total_weight,
		'timestamp': order_date
	} for (
		order_id, status,
		total_price, total_weight,
		order_date
	) in cur]

def get_order_info(cur: Cursor, order_id: int):
	cur.execute("""
		SELECT
			customer_id, status,
			total_price, total_weight,
			order_date
		FROM `order`
		WHERE order_id = ?;
	""", (order_id,))
	
	(
		customer_id, status,
		total_price, total_weight,
		order_date
	) = cur.fetchone()
	
	return {
		'id': { 'customer': customer_id, 'order': order_id },
		'status': status,
		'price': total_price, 'weight': total_weight,
		'timestamp': order_date
	}

def list_order_items(cur: Cursor, order_id: int):
	cur.execute("""
		WITH this_order (item_id, variant_id, quantity) AS (
			SELECT item_id, variant_id, quantity
			FROM order_item
			WHERE order_id = ? )
		SELECT
			item_id, variant_id,
			item_name,
			size, color,
			price, weight,
			quantity,
			COALESCE(variant_image, item_image) AS image_id
		FROM this_order JOIN (
			variant_catalog JOIN item_catalog USING (item_id)
		) USING (item_id, variant_id);
	""", (order_id,))
	
	return [{
		'id': { 'order': order_id, 'item': item_id, 'variant': variant_id },
		'name': item_name,
		'size': size, 'color': color,
		'price': price, 'weight': weight,
		'quantity': quantity,
		'image': image_id
	} for (
		item_id, variant_id,
		item_name,
		size, color,
		price, weight,
		quantity,
		image_id
	) in cur]
