import requests
import time
from Private_Constants import QUESTRADE_TOKEN
from Private_Constants import QUESTRADE_ACCOUNT_ID

from Data_structures.SingletonPattern import Singleton
from Questrade_Interface.Valuation import Valuation


class QuestradeAPIManager(metaclass=Singleton):
    def __init__(self):
        self.access_token = ""
        self.api_server = "https://api01.iq.questrade.com/"
        self.expires_at = time.time() + 1600
        self.refresh()

    def refresh(self):
        r = requests.get(
            f"https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token={QUESTRADE_TOKEN}"
        )
        r.raise_for_status()
        data = r.json()
        self.access_token = data["access_token"]
        self.api_server = data["api_server"]
        self.expires_at = time.time() + data["expires_in"] - 10  # refresh 10 sec early

    def ensure_token(self):
        if time.time() >= self.expires_at:
            self.refresh()

    def get_headers(self):
        self.ensure_token()
        return {"Authorization": f"Bearer {self.access_token}"}

    def get(self, endpoint: str, params=None):
        url = self.api_server + endpoint
        headers = self.get_headers()
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    def post(self, endpoint: str, json_data=None):
        url = self.api_server + endpoint
        headers = self.get_headers()
        r = requests.post(url, headers=headers, json=json_data)
        r.raise_for_status()
        return r.json()

    def get_pending_transactions(self):
        endpoint = f"v1/accounts/{QUESTRADE_ACCOUNT_ID}/transactions"
        transactions = self.get(endpoint)
        pending = [t for t in transactions.get("transactions", []) if t["status"] == "Pending"]
        return pending

    def get_balances(self):
        balances = self.get(f"v1/accounts/{QUESTRADE_ACCOUNT_ID}/balances")["perCurrencyBalances"]
        balances = {Valuation(b["currency"], b["cash"]) for b in balances}
        usd_balance = [b for b in balances if b.currency == "USD"][0]
        can_balance = [b for b in balances if b.currency == "CAN"][0]
        return {'CAN': can_balance, 'USD': usd_balance}

    def get_positions(self):
        positions = self.get(f"v1/accounts/{QUESTRADE_ACCOUNT_ID}/positions")["positions"]
        positions_dict = {}
        for p in positions:
            positions_dict[p["symbol"]] = {
                "quantity": p["openQuantity"],
                "market_value": p["currentMarketValue"],
                "currency": p["currency"]
            }
        return positions_dict

    def get_share_value(self, symbol):
        endpoint = "v1/markets/quotes"
        data = self.get(endpoint, params={"symbols": symbol})
        quotes = data.get("quotes", [])
        if not quotes:
            raise ValueError(f"No quote found for symbol: {symbol}")
        quote = quotes[0]
        return Valuation(quote.get("currency", "Unknown"), quote["lastTradePrice"])

