#!/usr/bin/env python3
"""抓取中国银行外汇牌价，生成 rate.json（供页面读取）。只用标准库。"""
import json, re, sys, urllib.request, urllib.error
from html.parser import HTMLParser

BASE = "https://www.boc.cn/sourcedb/whpj/"
NAME_CODE = {
    "美元": "USD", "欧元": "EUR", "英镑": "GBP", "日元": "JPY", "港币": "HKD",
    "澳大利亚元": "AUD", "澳元": "AUD", "加拿大元": "CAD", "加元": "CAD", "新加坡元": "SGD",
    "瑞士法郎": "CHF", "新西兰元": "NZD", "韩元": "KRW", "泰铢": "THB",
    "马来西亚林吉特": "MYR", "林吉特": "MYR", "澳门元": "MOP", "印度尼西亚盾": "IDR", "印尼盾": "IDR",
    "菲律宾比索": "PHP", "阿联酋迪拉姆": "AED", "沙特阿拉伯里亚尔": "SAR", "沙特里亚尔": "SAR",
    "墨西哥比索": "MXN", "俄罗斯卢布": "RUB", "卢布": "RUB", "土耳其里拉": "TRY",
    "波兰兹罗提": "PLN", "瑞典克朗": "SEK", "挪威克朗": "NOK", "丹麦克朗": "DKK",
    "新台币": "TWD", "越南盾": "VND", "印度卢比": "INR", "巴西雷亚尔": "BRL",
}


class RowParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self._row is not None and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if len(self._row) >= 8:
                self.rows.append(self._row)
            self._row = None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (rate-bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def num(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def parse_rows(rows, out, meta):
    for r in rows:
        code = NAME_CODE.get(re.sub(r"\s+", "", r[0]))
        if not code or code in out:
            continue
        spot, cash = num(r[1]), num(r[2])
        if spot:
            out[code] = {"spot_buy": spot}
        elif cash:
            out[code] = {"spot_buy": cash, "cash_only": True}
        else:
            continue
        if code == "USD" and r[6] and r[7]:
            meta["updated"] = r[6].replace(".", "/").replace("-", "/") + " " + r[7]


def main():
    out, meta = {}, {}
    for i in range(0, 12):  # 中行牌价分页：index.html、index_1.html、index_2.html ...
        url = BASE if i == 0 else f"{BASE}index_{i}.html"
        try:
            html = fetch(url)
        except urllib.error.HTTPError as e:
            if e.code == 404 and i > 0:
                break
            raise
        p = RowParser()
        p.feed(html)
        before = len(out)
        parse_rows(p.rows, out, meta)
        if i > 0 and len(out) == before:
            break
    if "USD" not in out or len(out) < 5 or "updated" not in meta:
        print("解析失败，保留旧的 rate.json：", sorted(out), meta, file=sys.stderr)
        sys.exit(1)
    data = {"updated": meta["updated"], "currencies": {k.lower(): v for k, v in sorted(out.items())}}
    with open("rate.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("ok", len(out), meta["updated"])


if __name__ == "__main__":
    main()
