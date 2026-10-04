"""
Run with: streamlit run dashboard.py
Then open the Local URL shown in your terminal on your laptop, or the
Network URL on your phone (same wifi).
"""
import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from plaid_client import CACHE_PATH, TOKEN_PATH, client

st.set_page_config(page_title="Spend Tracker", layout="wide")

BAR_COLOR = "#2E5AAC"


def load_token():
    if not os.path.exists(TOKEN_PATH):
        st.error(
            "No linked account yet. Run `python link_account.py`, open "
            "http://localhost:5001, and link your Amex first."
        )
        st.stop()
    with open(TOKEN_PATH) as f:
        return json.load(f)


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(transactions_by_id):
    # Serialize fully in memory first so a crash mid-write can never leave
    # a corrupted, half-written file on disk.
    serialized = json.dumps(transactions_by_id, default=str)
    with open(CACHE_PATH, "w") as f:
        f.write(serialized)


def sync_transactions(token_data):
    transactions_by_id = load_cache()
    cursor = token_data.get("cursor")
    has_more = True

    while has_more:
        kwargs = {"access_token": token_data["access_token"]}
        if cursor:
            kwargs["cursor"] = cursor
        req = TransactionsSyncRequest(**kwargs)
        response = client.transactions_sync(req)

        for txn in response.added + response.modified:
            transactions_by_id[txn.transaction_id] = txn.to_dict()
        for removed in response.removed:
            transactions_by_id.pop(removed.transaction_id, None)

        cursor = response.next_cursor
        has_more = response.has_more

    save_cache(transactions_by_id)

    token_data["cursor"] = cursor
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f)

    return transactions_by_id


def to_dataframe(transactions_by_id):
    rows = []
    for txn in transactions_by_id.values():
        category = (txn.get("personal_finance_category") or {}).get(
            "primary", "UNCATEGORIZED"
        )
        rows.append(
            {
                "date": txn["date"],
                "name": txn["merchant_name"] or txn["name"],
                "amount": txn["amount"],
                "category": category.replace("_", " ").title(),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    # Plaid: positive amount = money out (a purchase). Drop refunds/payments (negative).
    df = df[df["amount"] > 0]
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df


token_data = load_token()

with st.spinner("Syncing transactions from Plaid..."):
    transactions_by_id = sync_transactions(token_data)

df = to_dataframe(transactions_by_id)

st.title("Spend Tracker")

if df.empty:
    st.info("No transactions yet.")
    st.stop()

months = sorted(df["month"].unique(), reverse=True)
month_labels = {m: pd.Period(m).strftime("%B %Y") for m in months}
selected_month = st.selectbox(
    "Month", options=months, format_func=lambda m: month_labels[m]
)
st.caption(f"Showing **{month_labels[selected_month]}**")

month_df = df[df["month"] == selected_month]

col1, col2, col3 = st.columns(3)
col1.metric("Spend this month", f"${month_df['amount'].sum():,.2f}")
col2.metric("Transactions this month", len(month_df))
col3.metric("Months of history", df["month"].nunique())

by_category = (
    month_df.groupby("category")["amount"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)
fig_category = px.bar(
    by_category,
    x="amount",
    y="category",
    orientation="h",
    text="amount",
)
fig_category.update_traces(
    marker_color=BAR_COLOR,
    texttemplate="$%{text:,.0f}",
    textposition="outside",
)
fig_category.update_layout(
    yaxis={"categoryorder": "total ascending"},
    xaxis_title="Spend ($)",
    yaxis_title=None,
    showlegend=False,
)
st.subheader(f"Spend by category — {month_labels[selected_month]}")
st.plotly_chart(fig_category, use_container_width=True)

by_month = df.groupby("month")["amount"].sum().reset_index()
fig_month = px.area(by_month, x="month", y="amount")
fig_month.update_traces(line_color=BAR_COLOR, fillcolor="rgba(46, 90, 172, 0.2)")
fig_month.update_layout(xaxis_title=None, yaxis_title="Spend ($)")
st.subheader("Spend over time (all history)")
st.plotly_chart(fig_month, use_container_width=True)

st.subheader(f"Transactions — {month_labels[selected_month]}")
category_filter = st.multiselect(
    "Filter by category", options=sorted(month_df["category"].unique())
)
filtered = (
    month_df
    if not category_filter
    else month_df[month_df["category"].isin(category_filter)]
)
st.dataframe(
    filtered.sort_values("date", ascending=False)[
        ["date", "name", "category", "amount"]
    ],
    use_container_width=True,
    hide_index=True,
)
