import requests
import json
from Environment import ENVIRONMENT_HELPER
from datetime import date, datetime

#startegies
#+5 rebuy
#+10 rebuy

class Bars_Helper:
    def Test():
        print(date.today())

    def get_Asset_List():
        concat_url = ENVIRONMENT_HELPER.get_BASE_URL() + ENVIRONMENT_HELPER.get_ASSETS_URL()
        r = requests.get(concat_url, headers={'APCA-API-KEY-ID': ENVIRONMENT_HELPER.get_KEY_ID(), 'APCA-API-SECRET-KEY':ENVIRONMENT_HELPER.get_KEY_SECRET()})
        ret = []
        for name in json.loads(r.text):
            if "active" in name["status"] and name["tradable"] == True:
                ret.append([name["symbol"],name["name"]])
        return ret

    def get_Asset_Information(symbol):
        concat_url = ENVIRONMENT_HELPER.get_BASE_URL() + ENVIRONMENT_HELPER.get_ASSETS_URL() + "/" + str(symbol)
        r = requests.get(concat_url, headers={'APCA-API-KEY-ID': ENVIRONMENT_HELPER.get_KEY_ID(), 'APCA-API-SECRET-KEY':ENVIRONMENT_HELPER.get_KEY_SECRET()})
        return json.loads(r.text)

    def get_Bar_Price(symbol, limit=5, interval="minute", start=date.today(), end=date.today()):
        concat_url = ENVIRONMENT_HELPER.get_BARS_URL() + str(interval) + "?symbols=" + str(symbol) + "&limit=" + str(limit) + "&start=" + str(start) + "&end=" + str(end)
        r = requests.get(concat_url, headers={'APCA-API-KEY-ID': ENVIRONMENT_HELPER.get_KEY_ID(), 'APCA-API-SECRET-KEY':ENVIRONMENT_HELPER.get_KEY_SECRET()})
        return json.loads(r.text)

    def analyze_Bar_Price(symbol):
        concat_url = ENVIRONMENT_HELPER.get_BARS_URL() + "minute?symbols=" + str(symbol) + "&limit=15&start=" + str(date.today()) + "&end=" + str(date.today())
        r = requests.get(concat_url, headers={'APCA-API-KEY-ID': ENVIRONMENT_HELPER.get_KEY_ID(), 'APCA-API-SECRET-KEY':ENVIRONMENT_HELPER.get_KEY_SECRET()})
        try:
            base = json.loads(r.text)[symbol][0]["o"]
            for item in json.loads(r.text)[symbol]:
                if float(item["o"])/float(base) > 1.05:
                    return True
        except Exception as e:
            print("No data available")
            return False   
        return False

    def make_Order(symbol, quantity, side, ptype, time_in_force):
        concat_url = ENVIRONMENT_HELPER.get_BASE_URL() + ENVIRONMENT_HELPER.get_ORDER_URL()
        payload = "{\n    \"symbol\": \"" + symbol + "\",\n    \"qty\": " + quantity + ",\n    \"side\": \"" + side + "\",\n    \"type\": \"" + ptype + "\",\n    \"time_in_force\": \"" + time_in_force + "\"\n}"
        r = requests.request("POST", concat_url, data=payload, headers={'APCA-API-KEY-ID': ENVIRONMENT_HELPER.get_KEY_ID(), 'APCA-API-SECRET-KEY':ENVIRONMENT_HELPER.get_KEY_SECRET()})

    def get_Orders():
        concat_url = ENVIRONMENT_HELPER.get_BASE_URL() + ENVIRONMENT_HELPER.get_ORDERS_URL()
        r = requests.get(concat_url, headers={'APCA-API-KEY-ID': ENVIRONMENT_HELPER.get_KEY_ID(), 'APCA-API-SECRET-KEY':ENVIRONMENT_HELPER.get_KEY_SECRET()})
        return json.loads(r.text)

class Pyramide_Strategy:
    Assets = []
    Assets_Bought = []
    def __init__(self):
        self.Assets = []
        self.get_Assets_Name()

    def get_Assets_Name(self):
        tmpAssets = Bars_Helper.get_Asset_List()
        for item in tmpAssets:
            self.Assets.append(item[0])

    def analyze_new_Assets(self):
        while True:
            for counter, asset in enumerate(self.Assets):
                ret_analyze = Bars_Helper.analyze_Bar_Price(asset)
                print("Testing " + asset + " for trading: " + str(ret_analyze))
                #clear Assets with no data
                if "No data available" in str(ret_analyze):
                    self.Assets.pop(counter)
                
                #make order
                if ret_analyze == True:
                    print("Make order")
                    self.Assets.pop(counter)
                

class MACD_Class:
    def __init__(self):
        print("init")

    def calculate(symbols, start, end):
        print("calculating MACD")
        ret = []
        for symbol in list_symbols:
            prices = Bars_Helper.get_Bar_Price(symbol, limit=100,interval="day", start=start, end=end)
            EMA9 = 0
            EMA26 = 0
            close_prices = []
            for price in prices[symbol]:
                close_prices.append(float(price["c"]))
            for i in range(len(close_prices)):
                if i==0:
                    EMA9 = close_prices[len(close_prices)-10]
                    EMA26 = close_prices[len(close_prices)-27]
                else:
                    if i<9:
                        EMA9 = (close_prices[len(close_prices)-9+i]-EMA9)*0.2+EMA9
                    if i<26:
                        EMA26 = (close_prices[len(close_prices)-26+i]-EMA26)*0.0741+EMA26
                    if i>=26:
                        break
            MACD = EMA9-EMA26
            tmp = {"Symbol":symbol,"MACD":MACD}
            ret.append(tmp)

        return ret




symbols = Bars_Helper.get_Asset_List()
list_symbols = []
for counter, symbol in enumerate(symbols):
    list_symbols.append(symbol[0])
    if counter>0:
        break

from datetime import datetime, timedelta
past = str(datetime.today() - timedelta(days=100)).replace(" ","T")[:19]+"-01:00"
list_symbols = ["AAPL", "GOOGL"]
tmp = []
for i in range(7):
    today=str(datetime.today() - timedelta(days=i)).replace(" ","T")[:19]+"-01:00"
    #tmp.append(MACD_Class.calculate(list_symbols, past,today))