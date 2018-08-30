import json
from websocket import create_connection
import curses
import requests

bid_book = dict()
ask_book = dict()
sequence = 0

def apply_snapshot(snapshot):
	for bid in snapshot["bids"]:
		bid_book[float(bid[0])] = float(bid[1])
	for ask in snapshot["asks"]:
		ask_book[float(ask[0])] = float(ask[1])	
	return snapshot["sequence"]

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

PARAMS = {'level':3}
get_response = requests.get(url = URL, params = PARAMS)
print get_response
book_snapshot = get_response.json()
sequence = apply_snapshot(book_snapshot)
print sequence
#clear books
#snapshot seq num
#catchup
#stdscr = curses.initscr()
print ("Ask book:\n")
print (print_ask_book(DEPTH))
print ("Bid book:\n")
print (print_bid_book(DEPTH))
while True:
	rr = ws.recv()
	update = json.loads(rr)
	uType = update["type"]
	acceptedTypes = ["done", "open", "match", "change"]
	if uType in acceptedTypes:
		update_sequence = update["sequence"]
		if (update_sequence <= sequence):
			print "Discarding %s update #%d" % (uType, update_sequence)
		else:
			print "Applying %s update #%d" % (uType, update_sequence)
			if uType == "received":
				onRecieve(
			elif uType == "done":
			elif uType == "open":
			elif uType == "match":
			else:
				print "error"
				exit(1)
			
	else:
		print "Unknown message types %s" % uType
	#print book
	#stdscr.clear()
	#stdscr.addstr("Ask book:\n")
	#stdscr.addstr(print_ask_book(DEPTH))
	#stdscr.addstr("Bid book:\n")
	#stdscr.addstr(print_bid_book(DEPTH))
	#stdscr.refresh()
	
ws.close()
