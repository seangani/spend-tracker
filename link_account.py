"""
One-time setup: run this with `python link_account.py`. It opens a Plaid-
hosted page in your browser where you log into your bank (Amex), including
any redirect-based login steps — all handled on Plaid's own secure domain,
not ours. This script then polls Plaid until that's done, and saves an
access token to data/plaid_token.json so dashboard.py can pull transactions
without you doing this again (unless you want to link another account).
"""
import json
import time
import webbrowser

from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_hosted_link import LinkTokenCreateHostedLink
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.products import Products

from plaid_client import TOKEN_PATH, client

POLL_INTERVAL_SECONDS = 3
TIMEOUT_SECONDS = 600


def create_hosted_link():
    req = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id="spend-tracker-local-user"),
        client_name="Spend Tracker",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
        hosted_link=LinkTokenCreateHostedLink(),
    )
    response = client.link_token_create(req)
    return response.link_token, response.hosted_link_url


def wait_for_public_token(link_token):
    deadline = time.time() + TIMEOUT_SECONDS
    print("Waiting for you to finish linking in the browser...")

    while time.time() < deadline:
        response = client.link_token_get(LinkTokenGetRequest(link_token=link_token))
        data = response.to_dict()

        for session in data.get("link_sessions") or []:
            if session.get("finished_at") is None:
                continue
            results = session.get("results") or {}
            item_add_results = results.get("item_add_results") or []
            if item_add_results and item_add_results[0].get("public_token"):
                return item_add_results[0]["public_token"]
            print(f"Link session ended without a linked account: {session}")
            raise RuntimeError(
                "Link session ended without success — you may have closed "
                "the window or hit an error. Run this script again to retry."
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Timed out waiting for the Link flow to complete.")


def main():
    link_token, hosted_link_url = create_hosted_link()

    print(f"Opening in your browser:\n{hosted_link_url}\n")
    webbrowser.open(hosted_link_url)

    public_token = wait_for_public_token(link_token)

    exchange_response = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )

    with open(TOKEN_PATH, "w") as f:
        json.dump(
            {
                "access_token": exchange_response.access_token,
                "item_id": exchange_response.item_id,
                "cursor": None,
            },
            f,
        )

    print("Linked! You can now run: streamlit run dashboard.py")


if __name__ == "__main__":
    main()
