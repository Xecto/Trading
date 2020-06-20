from time import sleep
import matplotlib.pyplot as plt
from functions import Bars_Helper

ret = Bars_Helper.get_Bar_Price("AAPL", limit=15)

Assets = Bars_Helper.get_Asset_List()

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