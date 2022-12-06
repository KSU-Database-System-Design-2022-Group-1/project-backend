import os
import csv
import mimetypes

if not os.path.exists("./images"):
	os.mkdir("./images")

replace_types = {
	'Weight': float,
	'Stock': int,
}
def indexed_typed_dict(row: dict) -> tuple[int, dict]:
	index = int(row['ID'])
	del row['ID']
	
	for key in row:
		if row[key] == '':
			row[key] = None
		elif key in replace_types:
			row[key] = replace_types[key](row[key])
	
	return (index, row)

# bad sql sanitizer. good enough?
def bad(s: str | None) -> str:
	if s is None:
		return "NULL"
	s = s.replace("'", "''")
	return f"'{s}'"

def priceFromSize(basePrice: str, size: str | None) -> str:
	if size is None:
		return basePrice
	sizes = [ 'XS', 'S', 'M', 'L', 'XL' ]
	size_index = (sizes.index(size) - 2) / 2
	return str(round(float(basePrice) + size_index, 2))

images: list[str] = []

with open('dml.sql', 'w') as dml_sql:
	items: dict[int, dict] = {}
	
	print("-- Generated file. Run generate.py to update this.", file=dml_sql)
	print("START TRANSACTION;", file=dml_sql)
	print("USE kstores;", file=dml_sql)
	
	for table in [ 'variant_catalog', 'item_catalog', 'catalog_images' ]:
		print(f"DELETE FROM {table};", file=dml_sql)
	
	with open("items.csv", newline=None) as items_csv:
		for row in csv.DictReader(items_csv):
			(i, row) = indexed_typed_dict(row)
			
			# row['variants'] = []
			
			image_index = 0
			try:
				image_index = images.index(row['Image']) + 1
			except:
				images.append(row['Image'])
				image_index = len(images)
				try:
					with open('./sourceImages/' + row['Image'], 'rb') as image:
						with open('./images/' + str(image_index), 'wb') as dest:
							dest.write(image.read())
					mime = bad(mimetypes.guess_type(row['Image'])[0])
					print(f"INSERT INTO catalog_images ( image_id, mime_type, alt_text ) VALUES ( {image_index}, {mime}, '' );", file=dml_sql)
				except:
					print(f"warning! no such image {row['Image']}")
					images.pop()
					image_index = "NULL"
			
			print(f"INSERT INTO item_catalog ( item_id, item_name, description, category, item_image ) VALUES ( {i}, {bad(row['Name'])}, {bad(row['Description'])}, {bad(row['Category'])}, {image_index} );", file=dml_sql)
			
			# items[i] = row
	
	with open("variants.csv", newline=None) as variants_csv:
		(last_index, variant_id) = (0, 0)
		for row in csv.DictReader(variants_csv):
			(i, row) = indexed_typed_dict(row)
			
			if i != last_index:
				variant_id = 0
				last_index = i
			
			image_index = 0
			try:
				image_index = images.index(row['Image']) + 1
			except:
				images.append(row['Image'])
				image_index = len(images)
				mime = bad(mimetypes.guess_type(row['Image'])[0])
				try:
					with open('./sourceImages/' + row['Image'], 'rb') as image:
						with open('./images/' + str(image_index), 'wb') as dest:
							dest.write(image.read())
					print(f"INSERT INTO catalog_images ( image_id, mime_type, alt_text ) VALUES ( {image_index}, {mime}, '' );", file=dml_sql)
				except:
					print(f"warning! no such image {row['Image']}")
					image_index = "NULL"
			
			if row['Size'] is None:
				row['Size'] = [ None ]
			else:
				row['Size'] = [ i.strip() for i in row['Size'].split(',') ]
			
			for size in row['Size']:
				print(f"INSERT INTO variant_catalog ( item_id, variant_id, size, color, price, stock, weight, variant_image ) VALUES ( {i}, {variant_id}, {bad(size)}, {bad(row['Color'])}, {bad(priceFromSize(row['Price'], size))}, {row['Stock']}, {round(row['Weight'], 2)}, {image_index} );", file=dml_sql)
				variant_id += 1
			
			# items[i]['variants'].append(row)
	
	print("COMMIT WORK;", file=dml_sql)
