import alpaca_trade_api as tradeapi
import requests
import time
from ta import macd
import numpy as np
from datetime import datetime, timedelta
from pytz import timezone

api = tradeapi.REST()

session = requests.session()

min_share_price = 2.0
max_share_price = 13.0
min_last_dollar_volume = 10000000
risk = 0.001

def get_1000m_history_data(symbols):
    minute_history = {}
    c = 0
    for symbol in symbols:
        minute_history[symbol] = api.polygon.historic_agg(
            size="minute", symbol=symbol, limit=1000
        ).df
        c+=1
        print('{}/{}'.format(c, len(symbols)))
    return minute_history

def get_tickers():
    tickers = api.polygon.all_tickers()['tickers']
    print('got tickers')
    assets = api.list_assets()
    symbols = [asset.symbol for asset in assets if asset.tradable]
    return [ticker for ticker in tickers
        if ticker['ticker'] in symbols
            and ticker['lastTrade']['p'] >= min_share_price
            and ticker['lastTrade']['p'] <= max_share_price
            and ticker['prevDay']['v'] * ticker['lastTrade']['p']
                > min_last_dollar_volume
            and ticker['todaysChangePerc'] >= 3.5
    ]

def get_market_open():
    nyc = timezone('America/New_York')
    current_dt = datetime.today().astimezone(nyc)
    return current_dt - timedelta(
        hours=current_dt.hour-9,
        minutes=current_dt.minute-30,
        seconds=current_dt.second
    )

def find_stop(current_value, minute_history, now):
    series = minute_history['low'][-100:] \
                .dropna().resample('5min').min()
    series = series[now.floor('1D'):]
    diff = np.diff(series.values)
    low_index = np.where((diff[:-1] <= 0) & (diff[1:] > 0))[0] + 1
    if len(low_index) > 0:
        return series[low_index[-1]] - 0.01
    return current_value * 0.95

def run(tickers):
    # Establish streaming connection
    conn = tradeapi.StreamConn()

    # Update initial state with information from tickers
    volume_today = {}
    prev_closes = {}
    for ticker in tickers:
        symbol = ticker['ticker']
        prev_closes[symbol] = ticker['prevDay']['c']
        volume_today[symbol] = ticker['day']['v']

    symbols = [ticker['ticker'] for ticker in tickers]
    minute_history = get_1000m_history_data(symbols)

    portfolio_value = float(api.get_account().portfolio_value)

    open_orders = {}
    positions = {}

    # Cancel any existing open orders on watched symbols
    existing_orders = api.list_orders(limit=500)
    for order in existing_orders:
        if order.symbol in symbols:
            api.cancel_order(order.id)

    stop_prices = {}
    latest_cost_basis = {}

    # Track any positions bought during previous executions
    existing_positions = api.list_positions()
    for position in existing_positions:
        if position.symbol in symbols:
            positions[position.symbol] = float(position.qty)
            # Recalculate cost basis and stop price
            latest_cost_basis[position.symbol] = float(position.cost_basis)
            stop_prices[position.symbol] = float(position.cost_basis) * .95

    # Keep track of what we're buying/selling
    target_prices = {}
    partial_fills = {}

    # Use trade updates to keep track of our portfolio
    @conn.on(r'trade_update')
    async def handle_trade_update(conn, channel, data):
        symbol = data.order['symbol']
        last_order = open_orders.get(symbol)
        if last_order is not None:
            event = data.event
            if event == 'partial_fill':
                qty = data.order['filled_qty']
                if data.order['side'] == 'sell':
                    qty = qty * -1
                positions[symbol] = (
                    positions.get(symbol, 0) - partial_fills.get(symbol, 0)
                )
                partial_fills[symbol] = qty
                positions[symbol] += qty
                open_orders[symbol] = data.order
            elif event == 'filled':
                qty = data.order['filled_qty']
                if data.order['side'] == 'sell':
                    qty = qty * -1
                positions[symbol] = (
                    positions.get(symbol, 0) - partial_fills.get(symbol, 0)
                )
                partial_fills[symbol] = 0
                positions[symbol] += qty
                open_orders[symbol] = None
            elif event == 'canceled' or event == 'rejected':
                partial_fills[symbol] = 0
                open_orders[symbol] = None

    @conn.on(r'A\..*')
    async def handle_second_bar(conn, channel, data):
        symbol = data.symbol
        print('reading for {}'.format(symbol))

        # First, aggregate 1s bars for up-to-date MACD calculations
        ts = data.start
        ts -= timedelta(seconds=ts.second, microseconds=ts.microsecond)
        try:
            current_data = minute_history[data.symbol].loc[ts]
        except KeyError:
            current_data = None
        new_data = []
        if current_data is None:
            new_data = [
                data.open,
                data.high,
                data.low,
                data.close,
                data.volume
            ]
        else:
            new_data = [
                current_data.open,
                data.high if data.high > current_data.high else current_data.high,
                data.low if data.low < current_data.low else current_data.low,
                data.close,
                current_data.volume + data.volume
            ]
        minute_history[symbol].loc[ts] = new_data

        # Next, check for existing orders for the stock
        existing_order = open_orders.get(symbol)
        if existing_order is not None:
            # Make sure the order's not too old
            submission_ts = existing_order.submitted_at.astimezone(
                timezone('America/New_York')
            )
            order_lifetime = ts - submission_ts
            if order_lifetime.seconds // 60 > 1:
                # Cancel it so we can try again for a fill
                api.cancel_order(existing_order.id)
            return

        # Now we check to see if it might be time to buy or sell
        since_market_open = ts - get_market_open()
        if (
            since_market_open.seconds // 60 > 15
            #and since_market_open.seconds // 60 < 120
        ):
            print('reading symbol {}'.format(symbol))
            # Check for buy signals

            # See if we've already bought in first
            position = positions.get(symbol, 0)
            if position > 0:
                return

            # See how high the price went during the first 15 minutes
            lbound = get_market_open()
            ubound = lbound.replace(minute=45)
            high_15m = minute_history[symbol][lbound:ubound]['high'].max()

            # Get the change since yesterday's market close
            daily_pct_change = ((data.close - prev_closes[symbol])
                                / prev_closes[symbol])
            if (
                daily_pct_change > .04
                and data.close > high_15m
                and volume_today[symbol] > 30000
            ):
                # check for a positive, increasing MACD
                hist = macd(minute_history[symbol]['close'].dropna(), n_fast=12, n_slow=26)
                print(hist)
                if (
                    hist[-1] < 0
                    or not (hist[-3] < hist[-2] < hist[-1])
                ):
                    return
                hist = macd(minute_history[symbol]['close'].dropna(), n_fast=40, n_slow=60)
                if hist[-1] < 0 or np.diff(hist)[-1] < 0:
                    return

                # Stock has passed all checks; figure out how much to buy
                stop_price = find_stop(
                    data.close, minute_history[symbol], ts
                )
                stop_prices[symbol] = stop_price
                target_prices[symbol] = data.close + (
                    (data.close - stop_price) * 3
                )
                shares_to_buy = portfolio_value * risk // (
                    data.close - stop_price
                )
                if shares_to_buy == 0:
                    shares_to_buy = 1
                shares_to_buy -= positions.get(symbol, 0)
                if shares_to_buy <= 0:
                    return

                try:
                    o = api.submit_order(
                        symbol=symbol, qty=str(shares_to_buy), side='buy',
                        type='limit', time_in_force='day',
                        limit_price=str(data.close)
                    )
                    open_orders[symbol] = o
                    latest_cost_basis[symbol] = data.close
                except Exception as e:
                    print(e)
                return
        if(
            since_market_open.seconds // 60 >= 24
            and since_market_open.seconds // 60 < 360
        ):
            # Check for liquidation signals

            # We can't liquidate if there's no position
            position = positions.get(symbol, 0)
            if position == 0:
                return

            # Sell for a loss if it's fallen below our stop price
            # Sell for a loss if it's below our cost basis and MACD < 0
            # Sell for a profit if it's above our target price
            hist = macd(minute_history[symbol]['close'].dropna(), n_fast=13, n_slow=21)
            if (
                data.close <= stop_prices[symbol]
                or (data.close >= target_prices[symbol]
                    and hist[-1] <= 0)
                or (data.close <= latest_cost_basis[symbol]
                    and hist[-1] <= 0)
            ):
                try:
                    o = api.submit_order(
                        symbol=symbol, qty=str(position), side='sell',
                        type='limit', time_in_force='day',
                        limit_price=str(data.close)
                    )
                    open_orders[symbol] = o
                    latest_cost_basis[symbol] = data.close
                except Exception as e:
                    print(e)
            return

    # Replace aggregated 1s bars with incoming 1m bars
    @conn.on(r'AM\..*')
    async def handle_minute_bar(conn, channel, data):
        ts = data.start
        ts -= timedelta(microseconds=ts.microsecond)
        minute_history[data.symbol].loc[ts] = [
            data.open,
            data.high,
            data.low,
            data.close,
            data.volume
        ]
        volume_today[data.symbol] += data.volume

    channels = ['trade_updates']
    for symbol in symbols:
        symbol_channels = ['A.{}'.format(symbol), 'AM.{}'.format(symbol)]
        channels += symbol_channels
    run_ws(conn, channels)

# Handle failed websocket connections by reconnecting
def run_ws(conn, channels):
    try:
        conn.run(channels)
    except Exception as e:
        print(e)
        conn.close
        run_ws(conn, channels)

if __name__ == "__main__":

    # Wait until after we might want to trade
    nyc = timezone('America/New_York')
    current_dt = datetime.today().astimezone(nyc)
    since_market_open = current_dt - get_market_open
    while since_market_open.seconds // 60 <= 14:
        time.sleep(1)

    run(get_tickers())