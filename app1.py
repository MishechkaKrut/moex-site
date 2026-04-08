from flask import Flask, render_template, request
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

MOEX_API_BASE_URL = "https://iss.moex.com/iss"


@app.route('/', methods=['GET', 'POST'])
def index():
    # Значения по умолчанию
    ofz_rate = "Нет данных"
    last_updated = "Неизвестно"
    status_message = None
    error_message = None

    stock_price = "Нет данных"
    stock_last_updated = "Неизвестно"
    stock_error_message = None

    # Тикеры по умолчанию
    OFZ_TICKER = "SU29010RMFS4"
    STOCK_TICKER = "SBER"
    OFZ_BOARD = "TQOB"
    STOCK_BOARD = "TQBR"

    if request.method == "POST":
        form_type = request.form.get("form_type")
        print(form_type.text)

        # -----------------------------
        #   ОБРАБОТКА ОФЗ
        # -----------------------------
        if form_type == "ofz":
            OFZ_TICKER = request.form.get("ticker", "").strip().upper()

            try:
                url = (
                    f"{MOEX_API_BASE_URL}/history/engines/stock/markets/bonds/"
                    f"boards/{OFZ_BOARD}/securities/{OFZ_TICKER}.json"
                )

                params = {
                    'iss.only': 'history',
                    'sort_order': 'desc',
                    'sort_column': 'TRADEDATE',
                    'limit': 1
                }

                r = requests.get(url, params=params)
                r.raise_for_status()

                data = r.json()

                df = pd.DataFrame(data["history"]["data"], columns=data["history"]["columns"])

                if df.empty:
                    status_message = f"Данные для '{OFZ_TICKER}' отсутствуют."
                else:
                    row = df.iloc[0]
                    price = row["CLOSE"]
                    date = row["TRADEDATE"]

                    ofz_rate = f"{price:.2f}"
                    last_updated = date

            except Exception as e:
                error_message = f"Ошибка: {e}"

        # -----------------------------
        #   ОБРАБОТКА АКЦИЙ
        # -----------------------------
        elif form_type == "stock":
            STOCK_TICKER = request.form.get("stock", "").strip().upper()

            try:
                url = (
                    f"{MOEX_API_BASE_URL}/history/engines/stock/markets/shares/"
                    f"boards/{STOCK_BOARD}/securities/{STOCK_TICKER}.json"
                )

                params = {
                    'iss.only': 'history',
                    'sort_order': 'desc',
                    'sort_column': 'TRADEDATE',
                    'limit': 1
                }

                r = requests.get(url, params=params)
                r.raise_for_status()

                data = r.json()

                df = pd.DataFrame(data["history"]["data"], columns=data["history"]["columns"])

                if df.empty:
                    stock_error_message = f"Данные для '{STOCK_TICKER}' отсутствуют."
                else:
                    row = df.iloc[0]
                    price = row["CLOSE"]
                    date = row["TRADEDATE"]

                    stock_price = f"{price:.2f}"
                    stock_last_updated = date

            except Exception as e:
                stock_error_message = f"Ошибка: {e}"

    return render_template(
        'index.html',
        usd_rub_rate=ofz_rate,
        last_updated=last_updated,
        status_message=status_message,
        error_message=error_message,
        OFZ_TICKER=OFZ_TICKER,

        stock_price=stock_price,
        stock_last_updated=stock_last_updated,
        stock_error_message=stock_error_message,
        STOCK_TICKER=STOCK_TICKER
    )


if __name__ == '__main__':
    app.run(debug=True)
