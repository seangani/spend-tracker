# Spend Tracker

A personal spending dashboard: pulls Amex transactions via Plaid, shows
spend by category and over time in a local Streamlit app.

## How it works

1. `link_account.py` — run **once** to connect your Amex through Plaid. It
   opens a Plaid-hosted page in your browser (Plaid's "Hosted Link") where
   you log in — including Amex's own redirect-based login — entirely on
   Plaid's domain, not ours. The script then polls Plaid until that
   finishes and saves an access token to `data/plaid_token.json`
   (gitignored — never commit this file).
2. `dashboard.py` — a Streamlit app you run whenever you want to check
   spending. Pulls new transactions, caches them locally, and charts them.

## One-time setup

1. **Create a free Plaid developer account**: https://dashboard.plaid.com/signup
2. In the Plaid dashboard, grab your **Client ID** and your **Sandbox secret**
   (Team Settings → Keys).
3. Copy `.env.example` to `.env` and fill in `PLAID_CLIENT_ID` / `PLAID_SECRET`.
   Leave `PLAID_ENV=sandbox` for now.
4. Install dependencies (ideally in a virtualenv):
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. **Test the flow with fake data first** (no real bank login yet):
   ```
   python link_account.py
   ```
   A browser tab opens automatically. In Plaid's test mode, search for any
   institution and log in with username `user_good` / password `pass_good`
   (if it asks for a one-time code, use `123456`). The terminal prints
   "Linked!" once it detects you're done.
6. Run the dashboard against this fake data to confirm the whole pipeline
   works:
   ```
   streamlit run dashboard.py
   ```

## Switching to your real Amex

Plaid no longer has a separate "Development" environment — real bank data
only comes from the **Production** host. Most individual developers are
auto-approved for Plaid's free **Trial plan** on Production: real data,
no approval wait, capped at 10 linked accounts (you only need 1).

1. In the Plaid dashboard, grab your **Production secret** (same Keys page).
   If Production isn't visible yet, look for a "request Production access"
   / "Trial" prompt in the dashboard — it's typically instant for personal
   use cases.
2. In `.env`, set `PLAID_ENV=production` and swap `PLAID_SECRET` to the
   production secret.
3. Delete the old test link so you start clean:
   ```
   rm data/plaid_token.json data/transactions_cache.json
   ```
4. Run `python link_account.py` again — same flow as before, but this time
   search for "American Express" and log in with your real credentials.
5. Run `streamlit run dashboard.py` — this now pulls real transactions.

## Viewing on your phone

When you run `streamlit run dashboard.py`, the terminal prints both a
**Local URL** (for your laptop) and a **Network URL** (e.g.
`http://192.168.x.x:8501`). Open the Network URL in your phone's browser
while it's on the same wifi network as your laptop.

## Notes

- Transactions sync incrementally (`transactions_sync` with a cursor), so
  re-running the dashboard only pulls what's new.
- Refunds/payments (negative amounts in Plaid's convention) are excluded
  from spend totals — only purchases count.
- Categories come from Plaid's own categorization
  (`personal_finance_category`). Good enough for a first version; a future
  iteration could override/correct categories manually.
- Everything runs locally — your access token and transaction cache never
  leave your machine (see `.gitignore`).
