from flask import Flask, render_template, request, jsonify, redirect
import requests
import pandas as pd
import json
import os
import time

app = Flask(__name__)

MOEX_API = "https://iss.moex.com/iss"
PORTFOLIO_FILE = "portfolio.json"

# ---------------- тикеры ----------------
with open("moex_tickers.txt", encoding="utf-8") as f:
    ALL_TICKERS = [line.strip().upper() for line in f if line.strip()]

# ---------------- кэш ----------------
PRICE_CACHE = {}
TICKER_CACHE = {"data": [], "ts": 0}
CACHE_TTL = 60  # секунд

# ---------------- функции ----------------
def get_price(ticker):
    now = time.time()

    # кэш цены
    if ticker in PRICE_CACHE and now - PRICE_CACHE[ticker]["ts"] < CACHE_TTL:
        return PRICE_CACHE[ticker]["price"]

    if ticker not in ALL_TICKERS:
        return None

    try:
        if ticker.startswith("SU"):
            url = f"{MOEX_API}/history/engines/stock/markets/bonds/boards/TQOB/securities/{ticker}.json"
        else:
            url = f"{MOEX_API}/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"

        r = requests.get(url, params={
            "iss.only": "history",
            "sort_order": "desc",
            "sort_column": "TRADEDATE",
            "limit": 1
        }, timeout=2)

        data = r.json()
        if "history" not in data or not data["history"]["data"]:
            return None

        df = pd.DataFrame(data["history"]["data"], columns=data["history"]["columns"])
        if df.empty:
            return None

        price = round(float(df.iloc[0]["CLOSE"]), 2)

        PRICE_CACHE[ticker] = {"price": price, "ts": now}
        return price

    except:
        return None


# 🔥 КЭШИРОВАННЫЙ ТИКЕР (ускоряет сильно)
def get_ticker_tape():
    now = time.time()

    if now - TICKER_CACHE["ts"] < CACHE_TTL:
        return TICKER_CACHE["data"]

    result = []
    for t in ALL_TICKERS[:8]:  # было 30 → стало 8
        p = get_price(t)
        if p:
            result.append({"ticker": t, "price": p})

    TICKER_CACHE["data"] = result
    TICKER_CACHE["ts"] = now

    return result


# ---------------- портфель ----------------
def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except:
        return {}

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------- автопоиск ----------------
@app.route("/search")
def search():
    q = request.args.get("q", "").upper()
    return jsonify([t for t in ALL_TICKERS if t.startswith(q)][:10])


# ---------------- главная ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    portfolio = load_portfolio()
    checked_ticker = None
    checked_price = None
    error_message = None

    if request.method == "POST":

        if "check_ticker" in request.form:
            checked_ticker = request.form.get("check_ticker", "").upper().strip()
            checked_price = get_price(checked_ticker)

            if not checked_price:
                error_message = f"Тикер {checked_ticker} не найден"

        if "add_ticker" in request.form:
            ticker = request.form.get("add_ticker", "").upper().strip()
            qty = request.form.get("add_qty", "0").strip()

            if ticker not in ALL_TICKERS:
                error_message = f"Тикер {ticker} не найден"
            elif qty.isdigit() and int(qty) > 0:
                portfolio[ticker] = portfolio.get(ticker, 0) + int(qty)
                save_portfolio(portfolio)
                return redirect("/")

    # ---------------- портфель ----------------
    rows = []
    total = 0

    for t, q in portfolio.items():
        price = get_price(t)
        if price:
            value = round(price * q, 2)
            total += value
            rows.append({
                "ticker": t,
                "qty": q,
                "price": price,
                "value": value
            })

    # 🔥 используем кэш
    ticker_tape_data = get_ticker_tape()

    return render_template(
        "index.html",
        portfolio=rows,
        total=round(total, 2),
        ticker_tape=ticker_tape_data,
        checked_ticker=checked_ticker,
        checked_price=checked_price,
        error_message=error_message
    )


if __name__ == "__main__":
    app.run(debug=True)
