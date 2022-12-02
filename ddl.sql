START TRANSACTION;

-- DESTRUCTIVE! This will initialize things!
-- (But since it's inside a transaction,
--  it won't make half a database --
--  it's guaranteed to make Something)
DROP DATABASE IF EXISTS kstores;
CREATE DATABASE kstores;
USE kstores;

CREATE TABLE `address` (
	address_id INT AUTO_INCREMENT NOT NULL,
	
	street_number VARCHAR(5) NOT NULL,
	street_name VARCHAR(25) NOT NULL,
	street_apt VARCHAR(25),
	city VARCHAR(40) NOT NULL,
	state CHAR(2) NOT NULL,
	zip INT NOT NULL,
	
	PRIMARY KEY (address_id)
);

CREATE TABLE customer (
	customer_id INT AUTO_INCREMENT NOT NULL,
	
	first_name VARCHAR(40) NOT NULL,
	middle_name VARCHAR(40),
	last_name VARCHAR(40) NOT NULL,
	
	shipping_address INT,
	billing_address INT,
	
	email VARCHAR(80) NOT NULL,
	password VARCHAR(64) NOT NULL,
	
	phone_number VARCHAR(10) NOT NULL,
	
	PRIMARY KEY (customer_id),
	FOREIGN KEY `fk_customer_shipping_address` (shipping_address) REFERENCES `address` (address_id),
	FOREIGN KEY `fk_customer_billing_address` (billing_address) REFERENCES `address` (address_id)
);

CREATE TABLE catalog_images (
	image_id INT AUTO_INCREMENT NOT NULL,
	
	mime_type VARCHAR(64),
	alt_text TINYTEXT,
	
	PRIMARY KEY (image_id)
);

CREATE TABLE item_catalog (
	item_id INT AUTO_INCREMENT NOT NULL,
	
	item_name VARCHAR(64),
	description TEXT,
	category VARCHAR(32),
	item_image INT,
	
	-- price_max -- get price of the most expensive variant
	-- price_min -- get price of the least expensive variant
	
	PRIMARY KEY (item_id),
	FOREIGN KEY `fk_item_image` (item_image) REFERENCES catalog_images (image_id)
);

CREATE TABLE variant_catalog (
	item_id INT NOT NULL,
	variant_id INT NOT NULL,
	
	size ENUM('XS', 'S', 'M', 'L', 'XL'),
	color VARCHAR(32),
	price DECIMAL(6,2) NOT NULL,
	stock INT UNSIGNED NOT NULL,
	weight FLOAT NOT NULL,
	variant_image INT,
	
	PRIMARY KEY (item_id, variant_id),
	FOREIGN KEY `fk_variant_item` (item_id) REFERENCES item_catalog (item_id),
	FOREIGN KEY `fk_variant_image` (variant_image) REFERENCES catalog_images (image_id)
);

CREATE TABLE shopping_cart (
	customer_id INT NOT NULL,
	item_id INT NOT NULL,
	variant_id INT NOT NULL,
	
	quantity INT UNSIGNED NOT NULL,
	
	PRIMARY KEY (customer_id, item_id, variant_id),
	FOREIGN KEY `fk_cart_customer` (customer_id) REFERENCES customer (customer_id),
	FOREIGN KEY `fk_cart_item` (item_id) REFERENCES item_catalog (item_id),
	FOREIGN KEY `fk_cart_variant` (item_id, variant_id) REFERENCES variant_catalog (item_id, variant_id)
);

CREATE TABLE `order` (
	order_id INT AUTO_INCREMENT NOT NULL,
	customer_id INT NOT NULL,
	
	order_date TIMESTAMP NOT NULL,
	
	shipping_address INT NOT NULL,
	billing_address INT NOT NULL,
	
	total_price DECIMAL(6,2) NOT NULL,
	total_weight FLOAT NOT NULL,
	-- stored as proper attributes since
	-- price and weight may change
	-- after an order is completed.
	
	status ENUM('ordered', 'paid', 'shipped', 'delivered'),
	
	PRIMARY KEY (order_id),
	FOREIGN KEY `fk_order_customer` (customer_id) REFERENCES customer (customer_id),
	FOREIGN KEY `fk_order_shipping_address` (shipping_address) REFERENCES `address` (address_id)
);

CREATE TABLE order_item (
	order_id INT NOT NULL,
	item_id INT NOT NULL,
	variant_id INT NOT NULL,
	
	quantity INT UNSIGNED NOT NULL,
	
	PRIMARY KEY (order_id, item_id, variant_id),
	FOREIGN KEY `fk_order_item_order` (order_id) REFERENCES `order` (order_id),
	FOREIGN KEY `fk_order_item_item` (item_id) REFERENCES item_catalog (item_id),
	FOREIGN KEY `fk_order_item_variant` (item_id, variant_id) REFERENCES variant_catalog (item_id, variant_id)
);

COMMIT WORK;
