import json, os, random, re, time

from fake_useragent import UserAgent
import requests
from bs4 import BeautifulSoup

user_agent = UserAgent(min_percentage = 3.0)

site = 'https://glovoapp.com'
city_path = '/ba/sr/banja-luka'

data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data' , 'glovo')

# scrape restaurants
def scrape_restaurants () -> dict:

	headers = {'User-Agent': user_agent.random}

	restaurant_id_pattern = re.compile(f'^{city_path}/(?!restorani_\\d)([a-z0-9._-]+)/$')

	restaurants = {}
	restaurants_page = 1

	while True:

		url = f'{site}{city_path}/restorani_1/?page={restaurants_page}'
		print(f'Fetching restaurants from {url}...')

		# network
		soup = BeautifulSoup(requests.get(url, headers = headers).content, 'html.parser')
		time.sleep(random.uniform(3, 6))

		# local file for testing
		# with open('restaurants.html', 'r') as fp:
		# 	soup = BeautifulSoup(fp, 'html.parser')

		for a in soup.find_all('a', attrs = {'data-test-id': 'store-item'}):

			if match := restaurant_id_pattern.match(a.get('href')):

				uid = match.group(1)

				name = a.find(None, attrs = {'data-test-id': 'store-card-title'}).get_text(strip = True)

				if rating := a.find(None, attrs = {'data-test-id': 'store-rating-label'}):

					rating = rating.get_text(strip = True)[:-1]
					rating = int(rating) / 100 if rating.isdecimal() else None

				else:
					rating = None

				if count := a.find(None, attrs = {'data-test-id': 'store-rating-total'}):

					count = count.get_text(strip = True).replace('+', '')[1:-1]
					count = int(count) if count.isdecimal() else None

				else:
					count = None

				print(f'Adding "{uid}"...')
				restaurants[uid] = {'name': name, 'rating': rating, 'count': count}
		#}

		if not soup.select(f'a[href="{city_path}/restorani_1/?page={restaurants_page + 1}"]'):
			break

		restaurants_page += 1
	#}

	restaurants = dict(sorted(restaurants.items()))

	with open(os.path.join(data_path, 'restaurants.json'), 'w', encoding='utf-8') as fp:
		json.dump(restaurants, fp, indent = 2, ensure_ascii = False)

	return restaurants
#}


# scrape restaurant (internal)
def _scrape_restaurant (uid: str, data: dict, seen_pages: set, *, page_id = '') -> None:

	page = f'?content={page_id}' if page_id != '' else ''

	url = f'{site}{city_path}/{uid}/{page}'
	print(f'Fetching menu items from {url}...')

	headers = {'User-Agent': user_agent.random}

	# network
	soup = BeautifulSoup(requests.get(url, headers = headers).content, 'html.parser')
	time.sleep(random.uniform(3, 6))

	# local file for testing
	# if not os.path.exists(f'{uid}-{page_id}.html'):
	# 	# print('File does not exist')
	# 	return

	# with open(f'{uid}-{page_id}.html') as fp:
	# 	soup = BeautifulSoup(fp, 'html.parser')

	# service fee
	if 'service_fee' not in data:

		if service_fee := soup.find(None, attrs = {'data-test-id': 'service-fee-label'}):

			service_fee = service_fee.get_text(strip = True)
			data['service_fee'] = float(service_fee.replace('KM', '').replace(',', '.'))

	# menu items
	if 'menu' not in data:
		data['menu'] = {}

	menu = data['menu']
	menu_items = 0

	if product_rows := soup.find_all(None, attrs = {'type' : 'PRODUCT_ROW'}):

		for product_row in product_rows:

			section = product_row.find_parent(None, attrs = {'type': 'LIST'}).find(None, attrs = {'data-test-id': 'list-title'}).get_text(strip = True)

			if section not in menu:
				menu[section] = []

			name, desc, price = product_row.get_text(strip = True, separator = '|||').split('|||')

			price = float(price.replace('KM', '').replace(',', '.'))

			menu[section].append({'name': name, 'desc': desc, 'price': price})
			menu_items += 1
		#}
	#}

	print(f'Added {menu_items} menu items.')

	# subpages
	print('Checking subpages...')

	seen_pages.add(page_id)

	page_id_pattern = re.compile(f'^{city_path}/{uid}/\\?content=(?![a-z._-]+$)([a-zA-Z0-9.%_-]+)$')

	for a in soup.find_all('a'):

		match = page_id_pattern.match(a.get('href'))

		if match is not None and match.group(1) not in seen_pages:

			_scrape_restaurant(uid, data, seen_pages, page_id = match.group(1))
	#}
#}

# scrape restaurant
def scrape_restaurant (uid: str, data: dict) -> None:

	_scrape_restaurant(uid, data, seen_pages = set())

	with open(os.path.join(data_path, 'restaurants', f'{uid}.json'), 'w', encoding='utf-8') as fp:
		json.dump(data, fp, indent = 2, ensure_ascii = False)
#}


# generate merged glovo.json
def gen_data (*, scrape_if_missing = False) -> dict:

	# load restaurants
	restaurants_file = os.path.join(data_path, 'restaurants.json')

	if os.path.exists(restaurants_file):

		print('Loading restaurant list from file...')

		with open(restaurants_file, 'r', encoding='utf-8') as fp:
			restaurants = json.load(fp)

	elif scrape_if_missing:

		print('Scraping restaurant list...')

		restaurants = scrape_restaurants()
	#}

	# loop through restaurants
	data = {}

	for uid in restaurants:

		restaurant_file = os.path.join(data_path, 'restaurants', f'{uid}.json')

		if os.path.exists(restaurant_file):

			print(f'Loading restaurant \'{uid}\' from file...')

			with open(restaurant_file, 'r', encoding='utf-8') as fp:
				restaurant = json.load(fp)

		elif scrape_if_missing:

			print(f'Scraping restaurant {uid}...')

			restaurant = scrape_restaurant(uid, restaurants[uid])

		else:
			restaurant = None
		#}

		if restaurant is not None:
			data[uid] = restaurant
	#}

	# generate merged file
	with open(os.path.join(data_path, 'glovo.json'), 'w', encoding='utf-8') as fp:
		json.dump(data, fp, indent = 2, ensure_ascii = False)

	return data
#}

