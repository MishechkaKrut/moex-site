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

# ---------------- кэш цен ----------------
PRICE_CACHE = {}
CACHE_TTL = 30  # секунд

# ---------------- функции ----------------
def get_price(ticker):
    """Возвращает цену тикера с кешированием (акции или ОФЗ)"""
    now = time.time()
    if ticker in PRICE_CACHE and now - PRICE_CACHE[ticker]["ts"] < CACHE_TTL:
        return PRICE_CACHE[ticker]["price"]

    if ticker not in ALL_TICKERS:
        return None

    try:
        if ticker.startswith("SU") and len(ticker) >= 7:
            # ОФЗ
            url = f"{MOEX_API}/history/engines/stock/markets/bonds/boards/TQOB/securities/{ticker}.json"
        else:
            # Акции
            url = f"{MOEX_API}/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"

        r = requests.get(url, params={
            "iss.only": "history",
            "sort_order": "desc",
            "sort_column": "TRADEDATE",
            "limit": 1
        }, timeout=3)

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
    except json.JSONDecodeError:
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
        # Проверка цены
        if "check_ticker" in request.form:
            checked_ticker = request.form.get("check_ticker", "").upper().strip()
            if checked_ticker:
                if checked_ticker not in ALL_TICKERS:
                    error_message = f"Тикера {checked_ticker} нет в списке MOEX"
                    checked_price = None
                else:
                    checked_price = get_price(checked_ticker)

        # Добавление в портфель
        if "add_ticker" in request.form:
            ticker = request.form.get("add_ticker", "").upper().strip()
            qty = request.form.get("add_qty", "0").strip()
            if ticker not in ALL_TICKERS:
                error_message = f"Тикера {ticker} нет в списке MOEX"
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

    # ---------------- бегущая строка ----------------
    ticker_tape_data = []
    # Берем первые 30 тикеров файла
    for t in ALL_TICKERS[:30]:
        p = get_price(t)
        if p:
            ticker_tape_data.append({"ticker": t, "price": p})

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
