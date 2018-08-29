import json
from websocket import create_connection
import curses

bid_book = dict()
ask_book = dict()
last_trade = [0,0, "sell"]

def decode_snapshot(snapshot):
	for bid in snapshot['bids']:
		bid_book[float(bid[0])] = float(bid[1])
	for ask in snapshot['asks']:
		ask_book[float(ask[0])] = float(ask[1])

def decode_l2update(update):
	for change in update['changes']:
		if change[0] == "buy":
			level = float(change[1])
			size = float(change[2])
			if (size == 0):
				del bid_book[level]
			else:
				bid_book[level] = size
		else:
			level = float(change[1])
			size = float(change[2])
			if (size == 0):
				del ask_book[level]
			else:
				ask_book[level] = size

def print_bid_book(depth):
	ret = ""
	it = 0
	for level, size in sorted(bid_book.iteritems(), reverse=True):
		ret+="%f : %f\n" %(level, size)
		if (it < depth):
			it+=1
		else:
			break
	return ret

def print_ask_book(depth):
	ret = ""
	levels = []
	it = 0
	for level, size in sorted(ask_book.iteritems(), reverse=False):
		if (it < depth):
			it+=1
			levels.insert(0, "%f : %f\n" %(level, size))
		else:
			break
	for s in levels:
		ret += s
	return ret
	#for level, size in levels:
		#print "%f : %f" %(level, size)

def set_last_trade(match):
	last_trade[0] = float(match['price'])
	last_trade[1] = float(match['size'])
	last_trade[2] = str(match['side'])

stdscr = curses.initscr()
DEPTH = 5
ws = create_connection("wss://ws-feed.pro.coinbase.com")
#ws = create_connection("wss://ws-feed-public.sandbox.pro.coinbase.com")
sub = json.dumps(
{
"type": "subscribe",
"channels": [{ "name": "level2", "product_ids": ["BTC-USD"] }, { "name": "matches", "product_ids": ["BTC-USD"] }]
})
ws.send(sub)
while True:
	rr = ws.recv()
	#print rr
	update = json.loads(rr)
	uType = update["type"]
	if uType == "snapshot":
		decode_snapshot(update)
	elif uType == "l2update":
		decode_l2update(update)
	elif uType == "match":
		set_last_trade(update)
	else:
		print "Unknown message types %s" % uType
	#print book
	stdscr.clear()
	stdscr.addstr("Last trade: %s @ $%f : %f\n" % (last_trade[2], last_trade[0], last_trade[1]))
	stdscr.addstr("Ask book:\n")
	stdscr.addstr(print_ask_book(DEPTH))
	stdscr.addstr("Bid book:\n")
	stdscr.addstr(print_bid_book(DEPTH))
	stdscr.refresh()
	
ws.close()
