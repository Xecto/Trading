BASE_URL = "https://paper-api.alpaca.markets"
ASSETS = "/v2/assets"
BARS_URL = "https://data.alpaca.markets/v1/bars/" #example: https://data.alpaca.markets/v1/bars/day?symbols=AAPL&limit=1&start=2019-02-01&end=2019-02-10
KEY_ID = "PK2BE86M9K05KW3TWCB3"
KEY_SECRET = "V1ejDzBsTUmYnMYWQfWrQ2mxS0Tz7PtGzpqUtXQZ"
ORDER_URL = "/v2/orders"
ORDERS_URL = "/v2/orders"
CALENDER_ENDPOINT = ""
TIME_ENDPOINT = ""

class ENVIRONMENT_HELPER:
    def get_KEY_ID():
        return KEY_ID

    def get_KEY_SECRET():
        return KEY_SECRET

    def get_BASE_URL():
        return BASE_URL

    def get_BARS_URL():
        return BARS_URL

    def get_ASSETS_URL():
        return ASSETS

    def get_ORDER_URL():
        return ORDER_URL

    def get_ORDERS_URL():
        return ORDERS_URL