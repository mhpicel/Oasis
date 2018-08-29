# importing the requests library
import requests
 
# api-endpoint
URL = "https://api-public.sandbox.pro.coinbase.com/products/BTC-USD/book"
  
# defining a params dict for the parameters to be sent to the API

PARAMS = {'level':2}

# sending get request and saving the response as response object
r = requests.get(url = URL, params = PARAMS)

# extracting data in json format
data = r.json()
print data
