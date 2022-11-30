from typing import Any, Dict, List, Tuple

from mariadb import Cursor

# Returns the items in the cart.
def get_cart(cur: Cursor, customer_id: int):
	cur.execute("""
		SELECT item_id, variant_id, quantity
		FROM shopping_cart WHERE customer_id = ?;
		""", (customer_id,))
	return [{
		'id': { 'item': item_id, 'variant': variant_id },
		'quantity': quantity
	} for (item_id, variant_id, quantity) in cur]

# Returns the total price and weight (in a tuple, in that order) of the cart.
def get_cart_info(cur: Cursor, customer_id: int):
	cur.execute("""
		SELECT COALESCE(SUM(price), 0), COALESCE(SUM(weight), 0)
		FROM shopping_cart JOIN variant_catalog USING (item_id, variant_id)
		WHERE customer_id = ?;
		""", (customer_id,))
	
	# If shopping cart empty, returns (0, 0)
	# otherwise, returns (price, weight)
	return cur.fetchone()

# Creates a catalog item and returns its new item_id.
def create_catalog_item(
	cur: Cursor,
	name: str, description: str, category: str,
	variants: List[Tuple[ str, str, float, float, int ]],
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
	return item_id

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
		INSERT INTO shopping_cart (
			customer_id, item_id, variant_id, quantity
		) VALUES (?, ?, ?, ?);
		""", (customer_id, item_id, variant_id, quantity))

def place_order(cur: Cursor, customer_id: int) -> int:
	# Calculate total price and weight of shopping cart items.
	(price, weight) = get_cart_info(cur, customer_id)
	
	# Create a new order and fill it with info from the shopping cart.
	cur.execute("""
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
	return order_id
