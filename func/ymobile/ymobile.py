import dataclasses
import re

import requests
from bs4 import BeautifulSoup as bs
from dotenv import dotenv_values

LOGIN_PAGE_URL = "https://my.ymobile.jp/muc/d/webLink/doSend/MWBWL0130"
LOGIN_POST_URL = "https://id.my.ymobile.jp/sbid_auth/type1/2.0/login.php"
USAGE_LINK_URL = "https://my.ymobile.jp/muc/d/webLink/doSend/MRERE0000"
USAGE_PAGE_URL = "https://re61.my.ymobile.jp/resfe/top/"
TIMEOUT = 15
RETRY = 2


class YmobileError(Exception):
    """My Y!mobile から残量を取得できなかったときの例外"""


class YmobileMaintenance(YmobileError):
    """My Y!mobile がメンテナンス中"""


def to_soup(html) -> bs:
    # ヘッダに charset が無いページがあり r.text だと文字化けするので、bytes を渡して <meta charset> で判定させる
    soup = bs(html, "html.parser")
    if "メンテナンスを実施中" in soup.get_text():
        raise YmobileMaintenance("My Y!mobile はメンテナンス中です")
    return soup


@dataclasses.dataclass
class YmobileData:
    kurikoshi: int = None
    base: int = None
    used: int = None
    all_usable: int = None
    remaining: int = None
    mon: str = None
    period: str = None
    tel: str = None


def get_mb(s: str) -> int:
    """'1.5GB' / '10GB' / '500MB' / '1,024MB' を MB（1GB = 1000MB）に変換する"""
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*([GM]B)", s)
    if m is None:
        raise ValueError(f"データ量を解釈できません: {s!r}")
    value = float(m.group(1).replace(",", ""))
    if m.group(2) == "GB":
        value *= 1000
    return round(value)


def parse(html) -> YmobileData:
    res = to_soup(html)
    content = res.find(class_="list-toggle-content")
    if content is None:
        raise YmobileError("残量ページの形式が想定と違います（ログイン失敗かメンテナンス中の可能性）")

    data = {}
    for t in content.find_all("table"):
        th = t.find("th")
        td = t.find("td")
        if th is None or td is None:
            continue
        data[th.get_text(strip=True)] = td.get_text(strip=True)

    kurikoshi = 0
    base = 0
    used = 0
    other = 0
    for k, v in data.items():
        if "くりこし分" in k:
            kurikoshi = get_mb(v)
        elif k == "基本データ量 残り":
            base = get_mb(v.split("／")[0])
        elif k == "使用量 合計":
            used = get_mb(v)
        else:
            try:
                other += get_mb(v)
            except ValueError:
                # データ量以外の行（「-」など）は無視する
                pass
    all_usable = kurikoshi + base + other

    mon = res.find("h2", class_="res-fs16")
    p = res.find_all("p", class_="res-fs14")
    return YmobileData(
        kurikoshi=kurikoshi,
        base=base,
        used=used,
        all_usable=all_usable,
        remaining=all_usable - used,
        mon=mon.get_text(strip=True) if mon else "",
        period=p[0].get_text(strip=True) if len(p) > 0 else "",
        tel=p[1].get_text(strip=True) if len(p) > 1 else "",
    )


class Ymobile():
    def __init__(self, _PhoneNumber, _PassWord):
        self.PhoneNumber = _PhoneNumber
        self.PassWord = _PassWord

    def login(self, s: requests.Session):
        r = s.get(LOGIN_PAGE_URL, timeout=TIMEOUT)
        r.raise_for_status()
        soup = to_soup(r.content)
        ticket = soup.find("input", attrs={"name": "ticket"}) or soup.find("input", type="hidden")
        if ticket is None:
            raise YmobileError("ログインページから ticket を取得できません")
        payload = {
            "telnum": self.PhoneNumber,
            "password": self.PassWord,
            "ticket": ticket.get("value"),
        }
        s.post(LOGIN_POST_URL, data=payload, timeout=TIMEOUT).raise_for_status()

    def access(self, s: requests.Session) -> str:
        r = s.get(USAGE_LINK_URL, timeout=TIMEOUT)
        r.raise_for_status()
        soup = to_soup(r.content)
        inputs = soup.find_all("input")
        payload = {}
        for i, name in enumerate(("mfiv", "mfym")):
            tag = soup.find("input", attrs={"name": name})
            if tag is None and len(inputs) > i:
                tag = inputs[i]
            if tag is None or tag.get("value") is None:
                raise YmobileError(f"残量ページへの遷移に必要な {name} を取得できません（ログイン失敗の可能性）")
            payload[name] = tag.get("value")
        req = s.post(USAGE_PAGE_URL, data=payload, timeout=TIMEOUT)
        req.raise_for_status()
        return req.content

    def get(self) -> YmobileData:
        # 前回のログイン状態（期限切れの Cookie）が残ると遷移が変わるので、毎回新しいセッションで取得する
        last_error = None
        for _ in range(RETRY):
            try:
                with requests.Session() as s:
                    self.login(s)
                    return parse(self.access(s))
            except YmobileMaintenance:
                # メンテ中はリトライしても無駄
                raise
            except (requests.RequestException, YmobileError, ValueError) as e:
                last_error = e
        raise last_error


if __name__ == "__main__":
    config = dotenv_values(".env")
    y = Ymobile(config.get("PHONE_NUMBER"), config.get("YMOBILE_PASSWORD"))
    data = y.get()
    print(data)
