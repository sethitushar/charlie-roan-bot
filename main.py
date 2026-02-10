import asyncio, json, logging, re
import requests, websockets, random, string
from decouple import config

# Setup logging

if len(logging.getLogger().handlers):
    logging.getLogger().setLevel(logging.INFO)
else: logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define constant states

ticker = 'PEPPERSTONE:ETHUSD'
base_url = 'https://papertrading.tradingview.com'
state = {'balance': 0, 'position': 0, 'price': 0}

headers = {
    'Cookie': f"sessionid={config('TV_SESSION_ID')}",
    'Origin': 'https://www.tradingview.com',
    'Referer': 'https://www.tradingview.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

# Utility functions

def generate_session() -> str:
    chars = [random.choice(string.ascii_lowercase) for _ in range(12)]
    return 'qs_' + ''.join(chars)

def format_ws_message(payload: dict) -> str:
    json_str = json.dumps(payload)
    return '~m~' + str(len(json_str)) + '~m~' + json_str

# TradingView rest API endpoints

def account_info() -> dict:
    url = f"{base_url}/trading/account/{config('TV_ACCOUNT_ID')}"
    return requests.post(url, headers=headers).json()

def place_order(side: str, qty_percent: int = 90, sl_percent: int = 0.5, tp_percent: int = 0.5) -> dict:
    url = f"{base_url}/trading/place/{config('TV_ACCOUNT_ID')}"
    quantity = round((state['balance'] * qty_percent / 100) / state['price'], 2)
    stoploss = round(state['price'] + (state['price'] * sl_percent / 100) * (1 if side == 'sell' else -1), 2)
    takeprof = round(state['price'] + (state['price'] * tp_percent / 100) * (-1 if side == 'sell' else 1), 2)
    payload = {'symbol': ticker, 'type': 'market', 'qty': quantity, 'side': side, 'sl': stoploss, 'tp': takeprof, 'outside_rth': False, 'outside_rth_tp': False}
    return requests.post(url, json=payload, headers=headers).json()

# TradingView private feeds websocket

async def private_feeds():
    global state

    uri = 'wss://pushstream.tradingview.com/message-pipe-ws/private_feed'
    async with websockets.connect(uri, extra_headers=headers, ping_interval=None) as websocket:
        await websocket.send(format_ws_message({'m': 'set_auth_token', 'p': [config('TV_SESSION_ID')]}))

        while True:
            message = json.loads(await websocket.recv())

            if message['text']['content']['m'] == 'balance_update':
                state['balance'] = message['text']['content']['p']['balance']
                logging.info(f"Balance updated: {state['balance']}")
            
            if message['text']['content']['m'] == 'position_update':
                state['position'] = message['text']['content']['p']['qty']
                logging.info(f"Position updated: {state['position']}")

            if message['text']['content']['m'] == 'order_update':
                info = message['text']['content']['p']
                if info['label'] in ['tp', 'sl'] and info['status'] == 'filled':
                    response = place_order(info['side'] if info['label'] == 'sl' else ('sell' if info['side'] == 'buy' else 'buy'))
                    logging.info(f"Order response: {response}")

# TradingView public feeds websocket

async def public_feeds():
    global state

    uri = 'wss://data.tradingview.com/socket.io/websocket'
    async with websockets.connect(uri, extra_headers=headers, ping_interval=None) as websocket:
        await websocket.send(format_ws_message({'m': 'set_auth_token', 'p': ['unauthorized_user_token']}))

        qs_session = generate_session()
        await websocket.send(format_ws_message({'m': 'quote_create_session', 'p': [qs_session]}))
        await websocket.send(format_ws_message({'m': 'quote_set_fields', 'p': [qs_session, 'lp', 'volume', 'ch', 'chp']}))
        await websocket.send(format_ws_message({'m': 'quote_add_symbols', 'p': [qs_session, ticker]}))
        
        while True:
            message = await websocket.recv()

            if re.compile(r"~m~\d+~m~~h~\d+").fullmatch(message):
                await websocket.send(message)

            match = re.search(r'"lp":\s*(\d+(?:\.\d+)?)', message)                
            if match and state['price']:
                state['price'] = float(match.group(1))

            if match and not state['price']:
                state['price'] = float(match.group(1))
                if not state['position']:
                    response = place_order('buy')
                    logging.info(f"Order response: {response}")

            logging.info(f"Ticker Price updated: {state['price']}")


# Starting the main process

async def process():
    global state
    account = account_info()
    state['balance'] = account['balance']
    state['position'] = next((item['qty'] for item in account['positions'] if item['symbol'] == ticker), 0)
    await asyncio.gather(private_feeds(), public_feeds())

if __name__ == '__main__':
    asyncio.run(process())