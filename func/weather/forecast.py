"""Open-Meteo から天気予報を取得し、Discord に送るテキストにする。"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

import aiohttp


API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE_NAME = "Asia/Tokyo"
WEEKDAYS = ("月", "火", "水", "木", "金", "土", "日")

HOURLY_FIELDS = ("temperature_2m", "precipitation_probability", "weather_code")
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
)

# WMO weather code -> (絵文字, 日本語)
_WEATHER = {
    0: ("☀️", "快晴"),
    1: ("🌤️", "晴れ"),
    2: ("⛅", "晴れ時々曇り"),
    3: ("☁️", "曇り"),
    45: ("🌫️", "霧"),
    48: ("🌫️", "霧"),
    51: ("🌦️", "霧雨"),
    53: ("🌦️", "霧雨"),
    55: ("🌦️", "霧雨"),
    56: ("🌧️", "着氷性の霧雨"),
    57: ("🌧️", "着氷性の霧雨"),
    61: ("🌧️", "小雨"),
    63: ("🌧️", "雨"),
    65: ("🌧️", "強い雨"),
    66: ("🌧️", "着氷性の雨"),
    67: ("🌧️", "着氷性の雨"),
    71: ("🌨️", "小雪"),
    73: ("🌨️", "雪"),
    75: ("🌨️", "大雪"),
    77: ("🌨️", "霧雪"),
    80: ("🌦️", "にわか雨"),
    81: ("🌧️", "にわか雨"),
    82: ("🌧️", "激しいにわか雨"),
    85: ("🌨️", "にわか雪"),
    86: ("🌨️", "強いにわか雪"),
    95: ("⛈️", "雷雨"),
    96: ("⛈️", "雷雨（ひょう）"),
    99: ("⛈️", "雷雨（ひょう）"),
}


@dataclass(frozen=True)
class HourlyForecast:
    time: datetime
    temperature: float | None
    precipitation_probability: int | None
    weather_code: int | None


@dataclass(frozen=True)
class DailyForecast:
    date: date
    temperature_max: float | None
    temperature_min: float | None
    precipitation_probability: int | None
    weather_code: int | None


@dataclass(frozen=True)
class Forecast:
    daily: list[DailyForecast]
    hourly: list[HourlyForecast]


def build_params(latitude: float, longitude: float, start: date, end: date) -> dict[str, str]:
    return {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "timezone": TIMEZONE_NAME,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
    }


async def fetch_forecast(latitude: float, longitude: float, start: date, end: date) -> Forecast:
    """start〜end（両端含む）の日別・時間別予報を取得する。"""
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(API_URL, params=build_params(latitude, longitude, start, end)) as response:
            response.raise_for_status()
            data = await response.json()
    return parse_forecast(data)


def _value(section: dict, key: str, index: int):
    values = section.get(key) or []
    return values[index] if index < len(values) else None


def parse_forecast(data: dict) -> Forecast:
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}
    return Forecast(
        daily=[
            DailyForecast(
                date=date.fromisoformat(day),
                temperature_max=_value(daily, "temperature_2m_max", i),
                temperature_min=_value(daily, "temperature_2m_min", i),
                precipitation_probability=_value(daily, "precipitation_probability_max", i),
                weather_code=_value(daily, "weather_code", i),
            )
            for i, day in enumerate(daily.get("time") or [])
        ],
        hourly=[
            HourlyForecast(
                time=datetime.fromisoformat(time),
                temperature=_value(hourly, "temperature_2m", i),
                precipitation_probability=_value(hourly, "precipitation_probability", i),
                weather_code=_value(hourly, "weather_code", i),
            )
            for i, time in enumerate(hourly.get("time") or [])
        ],
    )


def weather_label(code: int | None) -> tuple[str, str]:
    """(絵文字, 日本語)。未知のコードは ("❔", "不明")。"""
    return _WEATHER.get(code, ("❔", "不明"))


def format_date(day: date) -> str:
    return f"{day:%m/%d}({WEEKDAYS[day.weekday()]})"


def _round(value: float) -> int:
    """四捨五入（round() や :.0f は偶数丸めなので使わない）。"""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _temperature(value: float | None) -> str:
    return "-" if value is None else str(_round(value))


def _probability(value: int | None) -> str:
    return "-" if value is None else f"{_round(value)}%"


def format_day_summary(day: DailyForecast) -> str:
    emoji, label = weather_label(day.weather_code)
    return (
        f"{emoji} {label}　最高 {_temperature(day.temperature_max)}°C / 最低 {_temperature(day.temperature_min)}°C"
        f"　降水確率 {_probability(day.precipitation_probability)}"
    )


def format_hourly(hours: list[HourlyForecast]) -> str:
    """1 時間ごとの気温・降水確率をコードブロックで並べる。"""
    rows = [
        f"{hour.time:%H}時 {_temperature(hour.temperature):>3}°C {_probability(hour.precipitation_probability):>4}"
        f" {weather_label(hour.weather_code)[0]}"
        for hour in hours
    ]
    return "```\n" + "\n".join(rows) + "\n```"


def format_week(days: list[DailyForecast]) -> str:
    """日ごとの最高/最低気温・降水確率をコードブロックで並べる。"""
    rows = []
    for day in days:
        emoji, label = weather_label(day.weather_code)
        rows.append(
            f"{format_date(day.date)} {_temperature(day.temperature_max):>3}/{_temperature(day.temperature_min):>2}°C"
            f" {_probability(day.precipitation_probability):>4} {emoji} {label}"
        )
    return "```\n" + "\n".join(rows) + "\n```"
