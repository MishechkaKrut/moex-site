from flask import Flask, render_template, request, jsonify, redirect
import requests
import pandas as pd
import json
import os
import time

app = Flask(__name__)

MOEX_API = "https://iss.moex.com/iss"
PORTFOLIO_FILE = "portfolio.json"

# ---- тикеры ----
with open("moex_tickers.txt", encoding="utf-8") as f:
    ALL_TICKERS = [line.strip().upper() for line in f if line.strip()]

# ---- кэш ----
PRICE_CACHE = {}
CACHE_TTL = 60


# ---------------- цена ----------------
def get_price(ticker):
    now = time.time()

    if ticker in PRICE_CACHE and now - PRICE_CACHE[ticker]["ts"] < CACHE_TTL:
        return PRICE_CACHE[ticker]["price"]

    if ticker not in ALL_TICKERS:
        return None

    try:
        url = f"{MOEX_API}/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"

        r = requests.get(url, params={
            "iss.only": "history",
            "sort_order": "desc",
            "sort_column": "TRADEDATE",
            "limit": 1
        }, timeout=3)

        data = r.json()
        df = pd.DataFrame(data["history"]["data"], columns=data["history"]["columns"])

        if df.empty:
            return None

        price = round(float(df.iloc[0]["CLOSE"]), 2)

        PRICE_CACHE[ticker] = {"price": price, "ts": now}
        return price

    except:
        return None


# ---------------- портфель ----------------
def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------- поиск ----------------
@app.route("/search")
def search():
    q = request.args.get("q", "").upper()
    return jsonify([t for t in ALL_TICKERS if t.startswith(q)][:10])


# ---------------- история графика ----------------
@app.route("/history/<ticker>")
def history(ticker):
    try:
        url = f"{MOEX_API}/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"

        r = requests.get(url, params={
            "iss.only": "history",
            "limit": 30
        }, timeout=3)

        data = r.json()
        df = pd.DataFrame(data["history"]["data"], columns=data["history"]["columns"])

        result = []
        for _, row in df.iterrows():
            if row["CLOSE"]:
                result.append({
                    "date": row["TRADEDATE"],
                    "price": float(row["CLOSE"])
                })

        return jsonify(result[::-1])

    except:
        return jsonify([])


# ---------------- главная ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    portfolio = load_portfolio()

    checked_ticker = None
    checked_price = None
    error_message = None

    if request.method == "POST":
        action = request.form.get("action")

        # 🔍 ПОИСК ЦЕНЫ (ФИКС)
        if action == "check":
            checked_ticker = request.form.get("check_ticker", "").upper().strip()
            checked_price = get_price(checked_ticker)

            if not checked_price:
                error_message = "Тикер не найден"

        # ➕ ДОБАВЛЕНИЕ
        if action == "add":
            ticker = request.form.get("add_ticker", "").upper().strip()
            qty = request.form.get("add_qty", "0")

            if ticker in ALL_TICKERS and qty.isdigit():
                portfolio[ticker] = portfolio.get(ticker, 0) + int(qty)
                save_portfolio(portfolio)
                return redirect("/")

    # ---------------- портфель ----------------
    rows = []
    total = 0

    for t, q in portfolio.items():
        price = get_price(t)
        if price:
            value = price * q
            total += value
            rows.append({
                "ticker": t,
                "qty": q,
                "price": price,
                "value": round(value, 2)
            })

    return render_template(
        "index.html",
        portfolio=rows,
        total=round(total, 2),
        checked_ticker=checked_ticker,
        checked_price=checked_price,
        error_message=error_message
    )


if __name__ == "__main__":
    app.run(debug=True)
