import unittest
from datetime import date, datetime

from func.weather.forecast import (
    DailyForecast,
    HourlyForecast,
    build_params,
    format_day_summary,
    format_hourly,
    format_week,
    parse_forecast,
    weather_label,
)


SAMPLE = {
    "timezone": "Asia/Tokyo",
    "hourly": {
        "time": ["2026-10-19T00:00", "2026-10-19T01:00"],
        "temperature_2m": [19.5, 19.2],
        "precipitation_probability": [0, 40],
        "weather_code": [1, 61],
    },
    "daily": {
        "time": ["2026-10-19", "2026-10-20"],
        "weather_code": [53, 63],
        "temperature_2m_max": [26.4, 25.6],
        "temperature_2m_min": [18.0, -1.2],
        "precipitation_probability_max": [8, None],
    },
}


class BuildParamsTest(unittest.TestCase):
    def test_range_and_fields(self):
        params = build_params(35.68, 139.77, date(2026, 10, 19), date(2026, 10, 25))
        self.assertEqual(params["start_date"], "2026-10-19")
        self.assertEqual(params["end_date"], "2026-10-25")
        self.assertEqual(params["timezone"], "Asia/Tokyo")
        self.assertIn("precipitation_probability", params["hourly"])
        self.assertIn("temperature_2m_max", params["daily"])


class ParseForecastTest(unittest.TestCase):
    def test_parse(self):
        forecast = parse_forecast(SAMPLE)
        self.assertEqual(forecast.hourly[1], HourlyForecast(datetime(2026, 10, 19, 1), 19.2, 40, 61))
        self.assertEqual(forecast.daily[0], DailyForecast(date(2026, 10, 19), 26.4, 18.0, 8, 53))
        self.assertIsNone(forecast.daily[1].precipitation_probability)

    def test_missing_columns_become_none(self):
        forecast = parse_forecast({"daily": {"time": ["2026-10-19"]}})
        self.assertEqual(forecast.daily, [DailyForecast(date(2026, 10, 19), None, None, None, None)])
        self.assertEqual(forecast.hourly, [])


class FormatTest(unittest.TestCase):
    def setUp(self):
        self.forecast = parse_forecast(SAMPLE)

    def test_weather_label(self):
        self.assertEqual(weather_label(0), ("☀️", "快晴"))
        self.assertEqual(weather_label(999), ("❔", "不明"))
        self.assertEqual(weather_label(None), ("❔", "不明"))

    def test_hourly_rows(self):
        text = format_hourly(self.forecast.hourly)
        self.assertEqual(
            text,
            "```\n"
            "00時  20°C   0% 🌤️\n"
            "01時  19°C  40% 🌧️\n"
            "```",
        )

    def test_round_half_up(self):
        hours = [HourlyForecast(datetime(2026, 10, 19, 0), 2.5, 0, 0), HourlyForecast(datetime(2026, 10, 19, 1), -2.5, 0, 0)]
        self.assertEqual(
            format_hourly(hours),
            "```\n"
            "00時   3°C   0% ☀️\n"
            "01時  -3°C   0% ☀️\n"
            "```",
        )

    def test_week_rows(self):
        text = format_week(self.forecast.daily)
        self.assertEqual(
            text,
            "```\n"
            "10/19(月)  26/18°C   8% 🌦️ 霧雨\n"
            "10/20(火)  26/-1°C    - 🌧️ 雨\n"
            "```",
        )

    def test_day_summary(self):
        self.assertEqual(
            format_day_summary(self.forecast.daily[0]),
            "🌦️ 霧雨　最高 26°C / 最低 18°C　降水確率 8%",
        )


if __name__ == "__main__":
    unittest.main()
