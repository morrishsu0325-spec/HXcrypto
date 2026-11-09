import datetime as dt
import json
import os
import sys
import time
import urllib.request

START = dt.date(2026, 9, 1)            # 起算日
COINS = ["BTC", "ETH"]                 # ← 你交易的幣,要加就加,例如 ["BTC", "ETH", "SOL"]
OUT = "data/prices.json"
TW = dt.timezone(dt.timedelta(hours=8))


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def day(ts_seconds):
    return dt.datetime.fromtimestamp(ts_seconds, TW).date().isoformat()


def okx_daily(coin):
    """OKX 日K(1D 以台灣時間 00:00 為界),只取已收盤的。"""
    out, after = {}, ""
    for _ in range(10):
        j = get(f"https://www.okx.com/api/v5/market/history-candles?instId={coin}-USDT&bar=1D&limit=100{after}")
        rows = j.get("data", [])
        if not rows:
            break
        for r in rows:
            d = day(int(r[0]) / 1000)
            if d >= START.isoformat():
                out[d] = float(r[4])
        oldest = int(rows[-1][0])
        if day(oldest / 1000) <= START.isoformat():
            break
        after = f"&after={oldest}"
        time.sleep(0.5)
    return out


def coinbase_daily(coin):
    """備援:Coinbase 日K(以 UTC 為界,和 OKX 差 8 小時)。"""
    start = START.isoformat() + "T00:00:00Z"
    j = get(f"https://api.exchange.coinbase.com/products/{coin}-USD/candles?granularity=86400&start={start}")
    return {dt.datetime.utcfromtimestamp(r[0]).date().isoformat(): float(r[4]) for r in j}


def okx_last(coin):
    j = get(f"https://www.okx.com/api/v5/market/ticker?instId={coin}-USDT")
    return float(j["data"][0]["last"])


def max_fx_daily():
    """MAX 交易所 USDT/TWD 日K 收盤。"""
    j = get("https://max-api.maicoin.com/api/v2/k?market=usdttwd&limit=200&period=1440")
    out = {}
    for r in j:
        d = day(r[0])
        if d >= START.isoformat():
            out[d] = float(r[4])
    return out


def max_fx_last():
    j = get("https://max-api.maicoin.com/api/v2/tickers/usdttwd")
    return float(j["last"])


def main():
    data = {}
    if os.path.exists(OUT):
        data = json.load(open(OUT, encoding="utf-8"))
    close = data.setdefault("close", {})
    latest = data.setdefault("latest", {})
    fx = data.setdefault("fx", {}).setdefault("USDTTWD", {})
    failed = []
    for coin in COINS:
        got = {}
        try:
            got = okx_daily(coin)
        except Exception as e:
            print(coin, "OKX 失敗:", e)
        if not got:
            try:
                got = coinbase_daily(coin)
                print(coin, "改用 Coinbase")
            except Exception as e:
                print(coin, "Coinbase 也失敗:", e)
        print(coin, "取得", len(got), "天,最新:", max(got) if got else "無")
        if got:
            close.setdefault(coin, {}).update(got)
        else:
            failed.append(coin)
        try:
            latest[coin] = okx_last(coin)
        except Exception as e:
            print(coin, "即時價失敗:", e)
        time.sleep(0.5)
    try:
        got = max_fx_daily()
        fx.update(got)
        print("USDTTWD 取得", len(got), "天,最新:", max(got) if got else "無")
    except Exception as e:
        print("USDTTWD 日K失敗:", e)
        failed.append("USDTTWD")
    try:
        latest["USDTTWD"] = max_fx_last()
    except Exception as e:
        print("USDTTWD 即時失敗:", e)
    now = dt.datetime.now(TW)
    latest["at"] = now.strftime("%Y-%m-%d %H:%M (台灣時間)")
    data["updated"] = latest["at"]
    os.makedirs("data", exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    if failed:
        print("失敗項目:", failed)
        sys.exit(1)


main()
