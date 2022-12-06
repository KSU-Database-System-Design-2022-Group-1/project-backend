from typing import Any, Literal
from collections.abc import Callable

from mariadb import Cursor

sizes = ['XS', 'S', 'M', 'L', 'XL']

def check_login(cur: Cursor, email: str, password: str) -> bool:
	""" Check if user's email/password pair is valid. """
	cur.execute("""
		SELECT COUNT(*)
		FROM customer
		WHERE email = ?
		AND password = ?;
	""", (email, password))
	return bool(cur.fetchall()[0][0])

def create_customer(
	cur: Cursor,
	first_name: str, middle_name: str, last_name: str,
	email: str, password: str,
	phone_number: str,
	shipping_addr: int | None = None,
	billing_addr: int | None = None
) -> int:
	""" Create a new customer. By default, they won't have any addresses. """
	
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

# Get a customer's information.
def get_customer_info(cur: Cursor, customer_id: int):
	""" Get a customer's information. Merges in the shipping and billing addresses too. """
	
	# TODO: hey!! this might be null! Jeez! This really is 3 am code...
	
	cur.execute("""
			SELECT
				first_name, middle_name, last_name,
				email, password,
				shipping_address,
				shipping.street, shipping.city, shipping.state, shipping.zip,
				billing_address,
				billing.street, billing.city, billing.state, billing.zip,
				phone_number
			FROM customer
				JOIN address AS shipping ON shipping_address = shipping.address_id
				JOIN address AS billing ON billing_address = billing.address_id
			WHERE customer_id = ?;
		""", (customer_id,))
	
	(
		first_name, middle_name, last_name,
		email, password,
		shipping_address,
		shipping_street,
		shipping_city, shipping_state, shipping_zip,
		billing_address,
		billing_street,
		billing_city, billing_state, billing_zip,
		phone_number
	) = cur.fetchone()
	
	return {
		'name': {
			'first': first_name,
			'middle': middle_name,
			'last': last_name
		},
		'email': email,
		'password': password,
		'address': {
			'shipping': {
				'id': shipping_address,
				'street': shipping_street,
				'city': shipping_city,
				'state': shipping_state,
				'zip': shipping_zip
			},
			'billing': {
				'id': billing_address,
				'street': billing_street,
				'city': billing_city,
				'state': billing_state,
				'zip': billing_zip
			}
		},
		'phone_number': phone_number
	}

def edit_customer(cur: Cursor, customer_id: int, **fields):
	"""
	Edit a customer. Only accepts fields from `valid_fields`.
	Don't include fields you don't want to modify.
	"""
	
	valid_fields = [
		'first_name', 'middle_name', 'last_name',
		'email', 'password',
		'phone_number'
	]
	
	if customer_id is None:
		raise Exception("missing customer id!")
	
	query = """
		UPDATE customer
		SET """
	params = []
	annoying_comma = False
	
	for (field, value) in fields.items():
		if field not in valid_fields \
		or value is None:
			continue # skip invalid fields
		
		if annoying_comma:
			query += ',\n'
		else:
			annoying_comma = True
		
		query += f"{field} = ?"
		params.append(value)
	
	query += "\nWHERE customer_id = ? LIMIT 1;"
	params.append(customer_id)
	
	cur.execute(query, params)

def create_address(
	cur: Cursor,
	street: str, city: str, state: str, zip: int
) -> int:
	"""
	Create a new address.
	(May return existing address_ids if they match.)
	"""
	
	cur.execute("""
		SELECT MIN(address_id)
		FROM address
		WHERE street = ?
		AND city = ? AND state = ?
		AND zip = ?;
	""", (
		street, city, state, zip
	))
	existing_address: int | None = cur.fetchone()[0]
	
	if existing_address is None:
		cur.execute("""
			INSERT INTO address (
				street, city, state, zip
			) VALUES (?, ?, ?, ?);
		""", ( street, city, state, zip ))
		return cur.lastrowid # type: ignore
	else:
		return existing_address # type: ignore

def get_address_info(cur: Cursor, address_id: int):
	""" Gets an address from an address ID number. """
	
	cur.execute("""
		SELECT
			street, city, state, zip
		FROM address
		WHERE address_id = ?;
		""", (address_id,))
	
	( street, city, state, zip_code ) = cur.fetchone()
	
	return {
		'id': address_id,
		'street': street,
		'city': city, 'state': state,
		'zip': zip_code
	}

def update_customer_address(
	cur: Cursor,
	customer_id: int, address_type: Literal['shipping'] | Literal['billing'],
	**fields
):
	"""
	Updates either the billing or shipping address associated with a specific customer.
	Also, checks to see if the underlying ID is used anywhere else, and if so it'll
	create a new address entry.
	"""
	
	valid_fields = [ 'street', 'city', 'state', 'zip' ]
	
	if address_type not in ['shipping', 'billing']:
		raise Exception("address_type must be either 'shipping' or 'billing'")
	
	# if we had a billion orders, this'd be problematic.
	# (maybe it'd necessitate separate customer_address
	#  and order_address tables!!) but this is fine.
	
	cur.execute(f"""
		SELECT {address_type}_address
		FROM customer
		WHERE customer_id = ?;
		""", (customer_id,))
	(address_id,) = cur.fetchone()
	
	other_addr_type = 'shipping' if address_type == 'billing' else 'billing'
	cur.execute(f"""
		SELECT COUNT(*)
		FROM customer
		WHERE {other_addr_type}_address = ?
		OR (customer_id <> ?
		AND {address_type}_address = ?);
		""", (address_id, customer_id, address_id))
	(customer_usage,) = cur.fetchone()
	
	need_to_clone = customer_usage > 0
	
	if not need_to_clone:
		cur.execute(f"""
			SELECT COUNT(*)
			FROM `order`
			WHERE shipping_address = ?
			OR billing_address = ?;
			""", (address_id, address_id))
		(order_usage,) = cur.fetchone()
		
		need_to_clone = order_usage > 0
	
	if need_to_clone:
		query = """
			INSERT INTO address (
				street, city, state, zip
			) SELECT 
		"""
		params = []
		annoying_comma = False
		
		for field in valid_fields:
			if annoying_comma:
				query += ",\n"
			else:
				annoying_comma = True
			
			if field in fields \
			and fields[field] is not None:
				query += "?"
				params.append(fields[field])
			else:
				query += field
		
		query += "\n" + """
			FROM address
			WHERE address_id = ?;
		"""
		params.append(address_id)
		
		cur.execute(query, params)
		address_id = cur.lastrowid # type: ignore
		
		cur.execute(f"""
			UPDATE customer
			SET {address_type}_address = ?
			WHERE customer_id = ? LIMIT 1;
		""", (address_id, customer_id))
	else:
		query = """
			UPDATE address
			SET 
		"""
		params = []
		annoying_comma = False
		
		for (field, value) in fields.items():
			if field not in valid_fields \
			or value is None:
				continue # skip invalid fields
			
			if annoying_comma:
				query += ",\n"
			else:
				annoying_comma = True
			
			query += f"{field} = ?"
			params.append(value)
		
		query += "\nWHERE address_id = ? LIMIT 1;"
		params.append(address_id)
		
		cur.execute(query, params)
	
	return { 'address': address_id }

def search_catalog(cur: Cursor, **filters):
	"""
	Fancy search function.
	Set keyword args to add different types of filters.
	It'll construct a query using all of them.
	
	The `**filters` parameter is a keyword argument list.
	It'll store a dict[str, Any] containing any other
	keyword arguments you provide. Keyword arguments
	are those things like `name="jim"` and such.
	The great thing is that you aren't required to
	include all of them, so you can skip the filters
	you don't need.
	"""
	
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
	"""
	Creates everything but the image's data.
	Images are fetched in `main.py`, via the `images/` directory.
	"""
	# TODO: that should be extracted to this file if i have time ( i don't)
	cur.execute("""
		INSERT INTO catalog_images (
			mime_type, alt_text
		) VALUES (?, ?);
		""", (mime_type, alt_text))
	return cur.lastrowid # type: ignore

def get_image_info(cur: Cursor, image_id: int):
	"""
	Fetches image info. Returns a dict containing the image's MIME type and
	a fallback image description for if the image file is missing or the user
	is using a screen reader.
	"""
	cur.execute("""
		SELECT mime_type, alt_text
		FROM catalog_images
		WHERE image_id = ?;
		""", (image_id,))
	(mime_type, alt_text) = cur.fetchone()
	return { 'mime_type': mime_type, 'alt_text': alt_text }

def get_item_info(cur: Cursor, item_id: int):
	"""
	Returns all the metadata from an item, along with a list of
	all the item's variants with metadata from those variants.
	"""
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

def get_cart_items(cur: Cursor, customer_id: int):
	""" Returns the items in the cart, with details about each one. """
	
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
			quantity, stock,
			(price * quantity) AS total_price,
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
		'quantity': quantity, 'stock': stock,
		'total_price': total_price,
		'image': image_id
	} for (
		item_id, variant_id,
		item_name,
		size, color,
		price, weight,
		quantity, stock,
		total_price,
		image_id
	) in cur]

def get_cart_info(cur: Cursor, customer_id: int):
	"""
	Returns the number of items in, and the total price and weight,
	(in a dict with fancy names!!) of the cart.
	If cart is empty, all these are zero, thankfully.
	"""
	
	cur.execute("""
		SELECT
			COUNT(*),
			COALESCE(SUM(price * quantity), 0),
			COALESCE(SUM(weight * quantity), 0)
		FROM shopping_cart JOIN variant_catalog USING (item_id, variant_id)
		WHERE customer_id = ?;
		""", (customer_id,))
	
	(count, price, weight) = cur.fetchone()
	
	# If shopping cart empty, returns (0, 0, 0)
	# otherwise, returns (count, price, weight)
	return { 'count': count, 'price': price, 'weight': weight }

def create_catalog_item(
	cur: Cursor,
	name: str, description: str, category: str,
	variants: list[tuple[ str, str, float, float, int ]],
) -> int:
	""" Creates a catalog item and returns its new item_id. """
	
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

def create_catalog_item_variant(
	cur: Cursor,
	item_id: int, variant_id: int | None,
	size: str, color: str,
	price: float, weight: float,
	stock: int = 1, image: int | None = None
):
	"""
	Creates a single catalog item variant.
	Don't use unless you really have to.
	"""
	
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
	"""
	Add the item variant to the cart. Optionally, provide a quantity.
	If the item is already present in the cart, this will reset its
	quantity to the specified number blah blah.
	"""
	if quantity > 0:
		cur.execute("""
			REPLACE INTO shopping_cart (
				customer_id, item_id, variant_id, quantity
			) VALUES (?, ?, ?, ?);
			""", (customer_id, item_id, variant_id, quantity))
	else:
		cur.execute("""
			DELETE FROM shopping_cart
			WHERE customer_id = ?
			AND item_id = ?
			AND variant_id = ?;
			""", (customer_id, item_id, variant_id))
# def remove_from_cart(
# 	cur: Cursor,
# 	customer_id: int,
# 	item_id: int | None, variant_id: int | None
# ):
# 	""" Remove an item from the cart / the entire cart's contents. """
# 	if item_id is None or variant_id is None:
# 		cur.execute("""
# 			DELETE FROM shopping_cart
# 			WHERE customer_id = ?;
# 			""", (customer_id,))
# 	else:
# 		cur.execute("""
# 			DELETE FROM shopping_cart
# 			WHERE customer_id = ?
# 			AND item_id = ?
# 			AND variant_id = ?;
# 			""", (customer_id, item_id, variant_id))

def place_order(cur: Cursor, customer_id: int) -> int:
	"""
	Places an order, clearing the items from the cart and creating
	a new entry in the orders table. Returns the new order's ID.
	
	Uuugh. should probably decrement the stock.
	"""
	
	# Calculate total price and weight of shopping cart items.
	cart_info = get_cart_info(cur, customer_id)
	( count, price, weight ) = (
		cart_info['count'],
		cart_info['price'],
		cart_info['weight']
	)
	
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
		""", (customer_id, customer_id, customer_id, price, weight))
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
	""" Returns a list of all orders associated with a customer. """
	
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
	"""
	Gets information about a specific order.
	(Like list_orders but for one order...)
	"""
	
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
	""" List the items ordered in an order. """
	
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
