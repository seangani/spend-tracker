import os

from dotenv import load_dotenv
from plaid.api import plaid_api
from plaid.api_client import ApiClient
from plaid.configuration import Configuration

load_dotenv()

PLAID_CLIENT_ID = os.environ["PLAID_CLIENT_ID"]
PLAID_SECRET = os.environ["PLAID_SECRET"]
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox")

_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "production": "https://production.plaid.com",
}

_configuration = Configuration(
    host=_HOSTS[PLAID_ENV],
    api_key={
        "clientId": PLAID_CLIENT_ID,
        "secret": PLAID_SECRET,
    },
)
_api_client = ApiClient(_configuration)
client = plaid_api.PlaidApi(_api_client)

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "data", "plaid_token.json")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "transactions_cache.json")
