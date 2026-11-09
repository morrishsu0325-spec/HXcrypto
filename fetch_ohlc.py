"""抓 BTC K 線（1 小時、4 小時、日、週），存成 data/ohlc.json 給月報的 K 線圖使用。
資料來源：OKX BTC-USDT。日 K、週 K 以台灣時間 00:00 為界。"""
import datetime as dt
import json
import os
import time
import urllib.request

INST = "BTC-USDT"
OUT = "data/ohlc.json"
# 每種週期要抓幾根 K 棒（越多歷史越久，檔案越大）
BARS = {
    "1H": 1000,   # 約 42 天
    "4H": 1500,   # 約 250 天
    "1D": 1500,   # 約 4 年
    "1W": 520,    # 約 10 年
}
TW = dt.timezone(dt.timedelta(hours=8))


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(bar, want):
    rows, after = {}, ""
    # 先抓最新的（含尚未收盤的那一根）
    j = get(f"https://www.okx.com/api/v5/market/candles?instId={INST}&bar={bar}&limit=300")
    for r in j.get("data", []):
        rows[int(r[0]) // 1000] = r
    while len(rows) < want:
        oldest = min(rows) * 1000 if rows else ""
        j = get(f"https://www.okx.com/api/v5/market/history-candles?instId={INST}&bar={bar}&limit=100&after={oldest}")
        data = j.get("data", [])
        if not data:
            break
        n0 = len(rows)
        for r in data:
            rows[int(r[0]) // 1000] = r
        if len(rows) == n0:
            break
        time.sleep(0.25)
    out = []
    for t in sorted(rows)[-want:]:
        r = rows[t]
        out.append([t, float(r[1]), float(r[2]), float(r[3]), float(r[4])])
    return out


def main():
    data = {"source": f"OKX {INST}", "bars": {}}
    if os.path.exists(OUT):
        try:
            data = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            pass
    ok = 0
    for bar, want in BARS.items():
        try:
            got = fetch(bar, want)
            if got:
                data["bars"][bar] = got
                ok += 1
            print(bar, "取得", len(got), "根")
        except Exception as e:
            print(bar, "失敗:", e)
    data["updated"] = dt.datetime.now(TW).strftime("%Y-%m-%d %H:%M (台灣時間)")
    os.makedirs("data", exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if ok == 0:
        raise SystemExit("全部週期都抓取失敗")


main()
