import requests

file = open("moex_tickers.txt", "w", encoding="utf-8")

# АКЦИИ (TQBR)
r = requests.get(
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json",
    params={
        "iss.only": "securities",
        "securities.columns": "SECID"
    }
)

for item in r.json()["securities"]["data"]:
    file.write(item[0] + "\n")

# ОБЛИГАЦИИ (TQOB)
r = requests.get(
    "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json",
    params={
        "iss.only": "securities",
        "securities.columns": "SECID"
    }
)

for item in r.json()["securities"]["data"]:
    file.write(item[0] + "\n")

file.close()

print("moex_tickers.txt создан, все тикеры в одном списке")
