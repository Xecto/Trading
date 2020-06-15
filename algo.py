from time import sleep
import matplotlib.pyplot as plt
from functions import Bars_Helper

ret = Bars_Helper.get_Bar_Price("AAPL", limit=15)

Assets = Bars_Helper.get_Asset_List()

while True:
    for item in Assets:
        print(Bars_Helper.sanalyze_Bar_Price(item[0]))