BEGIN;

-- DESTRUCTIVE! This will initialize things!
-- (But since it's inside a transaction,
--  it won't make half a database --
--  it's guaranteed to make Something)
DROP DATABASE IF EXISTS kstores;
CREATE DATABASE kstores;
USE kstores;

CREATE TABLE customer (
	customer_id INT AUTO_INCREMENT NOT NULL,
	
	first_name VARCHAR(40) NOT NULL,
	middle_name VARCHAR(40),
	last_name VARCHAR(40) NOT NULL,
	
	shipping_street_number VARCHAR(5) NOT NULL,
	shipping_street_name VARCHAR(25) NOT NULL,
	shipping_street_apt VARCHAR(25),
	shipping_city VARCHAR(40) NOT NULL,
	shipping_state CHAR(2) NOT NULL,
	shipping_zip INT NOT NULL,
	
	billing_street_number VARCHAR(5) NOT NULL,
	billing_street_name VARCHAR(25) NOT NULL,
	billing_street_apt VARCHAR(25),
	billing_city VARCHAR(40) NOT NULL,
	billing_state CHAR(2) NOT NULL,
	billing_zip INT NOT NULL,
	
	email VARCHAR(80) NOT NULL,
	password VARCHAR(64) NOT NULL,
	
	phone_number VARCHAR(10) NOT NULL,
	
	PRIMARY KEY (customer_id)
);

CREATE TABLE catalog_images (
	image_id INT AUTO_INCREMENT NOT NULL,
	
	image BLOB,
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
	FOREIGN KEY (item_image) REFERENCES catalog_images (image_id)
);

CREATE TABLE variant_catalog (
	item_id INT NOT NULL,
	variant_id INT NOT NULL,
	
	size ENUM('XS', 'S', 'M', 'L', 'XL'),
	color VARCHAR(32),
	price DECIMAL(6,2),
	stock INT,
	weight FLOAT,
	variant_image INT,
	
	PRIMARY KEY (item_id, variant_id),
	FOREIGN KEY (item_id) REFERENCES item_catalog (item_id),
	FOREIGN KEY (variant_image) REFERENCES catalog_images (image_id)
);

CREATE TABLE shopping_cart (
	customer_id INT NOT NULL,
	item_id INT NOT NULL,
	variant_id INT NOT NULL,
	
	quantity INT UNSIGNED NOT NULL,
	
	PRIMARY KEY (customer_id, item_id, variant_id),
	FOREIGN KEY (customer_id) REFERENCES customer (customer_id),
	FOREIGN KEY (item_id) REFERENCES item_catalog (item_id),
	FOREIGN KEY (item_id, variant_id) REFERENCES variant_catalog (item_id, variant_id)
);

CREATE TABLE `order` (
	order_id INT AUTO_INCREMENT NOT NULL,
	customer_id INT NOT NULL,
	
	total_price DECIMAL(6,2),
	total_weight FLOAT,
	-- stored as proper attributes since
	-- price and weight may change
	-- after an order is completed.
	
	status ENUM('ordered', 'paid', 'shipped', 'delivered'),
	
	PRIMARY KEY (order_id),
	FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
);

CREATE TABLE order_item (
	order_id INT NOT NULL,
	item_id INT NOT NULL,
	variant_id INT NOT NULL,
	
	quantity INT UNSIGNED NOT NULL,
	
	PRIMARY KEY (order_id, item_id, variant_id),
	FOREIGN KEY (order_id) REFERENCES `order` (order_id),
	FOREIGN KEY (item_id) REFERENCES item_catalog (item_id),
	FOREIGN KEY (item_id, variant_id) REFERENCES variant_catalog (item_id, variant_id)
);

COMMIT WORK;
