import json
from websocket import create_connection
import curses
import requests

from sortedcontainers import SortedDict
from decimal import Decimal

import time

class OrderBook(object):
	def __init__(self, url):
		self._asks = SortedDict()
		self._bids = SortedDict()
		self._sequence = -1
		self._current_ticker = None
		self._snap_url = url

	def on_message(self, message):
		sequence = message.get('sequence', -1)
		if self._sequence == -1:
			self.reset_book()
			return
		if sequence <= self._sequence:
			# ignore older messages (e.g. before order book initialization from getProductOrderBook)
			return
		elif sequence > self._sequence + 1:
			self.on_sequence_gap(self._sequence, sequence)
			return
		
		mType = update["type"]
		if mType == "open":
			self.add(message)
		elif mType == "done" and "price" in message:
			self.remove(message)
		elif mType == "match":
			self.match(message)
			self._current_ticker = message
		elif mType == "change" and "price" in message:
			self.change(message)

		self._sequence = sequence

	def on_sequence_gap(self, gap_start, gap_end):
		self.reset_book()
		print('Error: messages missing ({} - {}). Re-initializing  book at sequence.'.format(
			gap_start, gap_end, self._sequence))

	def reset_book(self):
		self._asks.clear()
		self._bids.clear()
		self._sequence = -1
		self._current_ticker = None
		get_response = requests.get(url = self._snap_url, params = {'level':3})
#print get_response
		book_snapshot = get_response.json()
		for bid in book_snapshot['bids']:
			self.add({
				'order_id': bid[2],
				'side': 'buy',
				'price': Decimal(bid[0]),
				'remaining_size': Decimal(bid[1])
			})
		for ask in book_snapshot['asks']:
			self.add({
				'order_id': ask[2],
				'side': 'sell',
				'price': Decimal(ask[0]),
				'remaining_size': Decimal(ask[1])
			})
		self._sequence = book_snapshot['sequence']
	
	def add(self, order):
		order = {
			'id': order['order_id'],
			'side': order['side'],
			'price': Decimal(order['price']),
			'size': Decimal(order['remaining_size'])
		}
		if order['side'] == 'buy':
			#self._bids.get(order['price']).append(order)
			bids = self._bids.get(order['price'])
			if bids is None:
				bids = [order]
			else:
				bids.append(order)
			self._bids[order['price']] = bids
		else:
			#self._asks.get(order['price']).append(order)
			asks = self._asks.get(order['price'])
			if asks is None:
				asks = [order]
			else:
				asks.append(order)
			self._asks[order['price']] = asks

	def remove(self, order):
		price = Decimal(order['price'])
		if order['side'] == 'buy':
			bids = self._bids.get(price)
			if bids is not None:
				bids = [o for o in bids if o['id'] != order['order_id']]
				if len(bids) > 0:
					self._bids[price] = bids
				else:
					del self._bids[price]
		else:
			asks = self._asks.get(price)
			if asks is not None:
				asks = [o for o in asks if o['id'] != order['order_id']]
				if len(asks) > 0:
					self._asks[price] = asks
				else:
					del self._asks[price]

	def match(self, order):
		size = Decimal(order['size'])
		price = Decimal(order['price'])

		if order['side'] == 'buy':
			bids = self._bids.get(price)
			if not bids:
				return
			assert bids[0]['id'] == order['maker_order_id']
			if bids[0]['size'] == size:
				self._bids[price] = bids[1:]
			else:
				bids[0]['size'] -= size
				self._bids[price] = bids
		else:
			asks = self._asks.get(price)
			if not asks:
				return
			assert asks[0]['id'] == order['maker_order_id']
			if asks[0]['size'] == size:
				self._asks[price] = asks[1:]
			else:
				asks[0]['size'] -= size
				self._asks[price]= asks

	def change(self, order):
		new_size = Decimal(order['new_size'])
		price = Decimal(order['price'])

		if order['side'] == 'buy':
			bids = self._bids.get(price)
			if bids is None or not any(o['id'] == order['order_id'] for o in bids):
				return
			index = [b['id'] for b in bids].index(order['order_id'])
			bids[index]['size'] = new_size
			self._bids[price] = bids
		else:
			asks = self._asks.get(price)
			if asks is None or not any(o['id'] == order['order_id'] for o in asks):
				return
			index = [a['id'] for a in asks].index(order['order_id'])
			asks[index]['size'] = new_size
			self._asks[price] = asks

		""" idk whats going on here...?
		tree = self._asks if order['side'] == 'sell' else self._bids
		node = tree.get(price)

		if node is None or not any(o['id'] == order['order_id'] for o in node):
			return
		"""

	def get_current_ticker(self):
		return self._current_ticker

	def get_current_book(self):
		result = {
			'sequence': self._sequence,
			'asks': [],
			'bids': [],
		}
		for ask in self._asks:
			try:
				# There can be a race condition here, where a price point is removed
				# between these two ops
				this_ask = self._asks[ask]
			except KeyError:
				continue
			for order in this_ask:
				result['asks'].append([order['price'], order['size'], order['id']])
		for bid in self._bids:
			try:
				# There can be a race condition here, where a price point is removed
				# between these two ops
				this_bid = self._bids[bid]
			except KeyError:
				continue

			for order in this_bid:
				result['bids'].append([order['price'], order['size'], order['id']])
		return result

#main:
def print_bids(bids, depth):
	if (bids is None):
		return "No bid book"
	bids.reverse()
	ret = ""
	last_l = -1
	aQty = Decimal(0)
	dCount = 0
	it=0
	while (dCount < depth and it < len(bids)):
		b = bids[it]
		if (last_l == -1):
			last_l = b[0]
		if (last_l == b[0]):
			aQty += b[1]
		else:
			dCount+=1
			ret+="%s : %s\n" %(last_l, aQty)
			last_l = b[0]
			aQty = b[1]

		it+=1
		if (it == len(bids) and dCount < depth):
			ret+="%s : %s\n" %(last_l, aQty)
	return ret

def print_asks(asks, depth):
	if (asks is None):
		return "No ask book"
	
	ret = ""
	levels = []
	last_l = -1
	aQty = Decimal(0)
	dCount = 0
	it=0
	while (dCount < depth and it < len(asks)):
		a = asks[it]
		if (last_l == -1):
			last_l = a[0]
		if (last_l == a[0]):
			aQty += a[1]
		else:
			dCount+=1
			levels.insert(0, "%s : %s\n" %(last_l, aQty))
			last_l = a[0]
			aQty = a[1]

		it+=1
		if (it == len(asks) and dCount < depth):
			levels.insert(0, "%s : %s\n" %(last_l, aQty))

	for s in levels:
		ret += s
	return ret

DEPTH = 5
MD_FEED = "wss://ws-feed.pro.coinbase.com"
#MD_FEED = "wss://ws-feed-public.sandbox.pro.coinbase.com"
URL = "https://api.pro.coinbase.com/products/BTC-USD/book"
#https://api-public.sandbox.pro.coinbase.com/products/BTC-USD/book"
#URL = "https://api-public.sandbox.pro.coinbase.com/products/BTC-USD/book"
ws = create_connection(MD_FEED)
sub = json.dumps(
{
"type": "subscribe",
"channels": [{ "name": "full", "product_ids": ["BTC-USD"] }]
})
ws.send(sub)
#should be subscriptions response
update = json.loads(ws.recv())
if update["type"] != "subscriptions":
	print "Unexpected initial message type %s" % update["type"]
	print update
	exit(1)

#connect
#listen
#disconnect

book = OrderBook(URL)
stdscr = curses.initscr()
ttime = 0
while True:
	rr = ws.recv()
	update = json.loads(rr)
	book.on_message(update)
	#print book
	if (time.time() - ttime > .1):
		stdscr.clear()
		cb = book.get_current_book()
		stdscr.addstr("Ask book:\n")
		stdscr.addstr(print_asks(cb["asks"], DEPTH))
		stdscr.addstr("Bid book:\n")
		stdscr.addstr(print_bids(cb["bids"], DEPTH))
		stdscr.addstr("Last trade info: %s\n" % book.get_current_ticker())
		stdscr.addstr("Current sequence number: %d\n" % cb["sequence"])
		stdscr.refresh()
		ttime = time.time()
