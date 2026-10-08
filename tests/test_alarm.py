import unittest
from datetime import datetime

from func.alarm.schedule import EVERY, parse_alarm


def schedule(text: str, now: datetime, count: int = 5) -> list[datetime]:
    """now から最大 count 回分の通知時刻。"""
    spec = parse_alarm(text)
    first = spec.first(now)
    if first is None:
        return []
    result = [first]
    while len(result) < count:
        nxt = spec.next_after(result[-1], first)
        if nxt is None:
            break
        result.append(nxt)
    return result


NOW = datetime(2026, 10, 7, 10, 5, 30)


class ParseAlarmTest(unittest.TestCase):
    def test_minute_only(self):
        self.assertEqual(parse_alarm("12").fields, (None, None, None, None, 12, 0))

    def test_hour_minute(self):
        self.assertEqual(parse_alarm("12:50").fields, (None, None, None, 12, 50, 0))
        self.assertEqual(parse_alarm("12:").fields, (None, None, None, 12, 0, 0))
        self.assertEqual(parse_alarm(":30").fields, (None, None, None, None, 30, 0))

    def test_hour_minute_second(self):
        self.assertEqual(parse_alarm("1:2:3").fields, (None, None, None, 1, 2, 3))
        self.assertEqual(parse_alarm(":5:10").fields, (None, None, None, None, 5, 10))

    def test_date_only_sets_time_to_zero(self):
        self.assertEqual(parse_alarm("/5").fields, (None, None, 5, 0, 0, 0))
        self.assertEqual(parse_alarm("11/").fields, (None, 11, 1, 0, 0, 0))

    def test_full(self):
        self.assertEqual(
            parse_alarm("*/*/5 10:*:20").fields,
            (EVERY, EVERY, 5, 10, EVERY, 20),
        )

    def test_time_before_date(self):
        self.assertEqual(parse_alarm("12: /5").fields, parse_alarm("/5 12:").fields)

    def test_era_year(self):
        for text in ("令和8/1/1", "令和8年/1/1", "R8/1/1", "r8/1/1", "2026/1/1"):
            with self.subTest(text=text):
                self.assertEqual(parse_alarm(text).fields[0], 2026)
        self.assertEqual(parse_alarm("H30/1/1").fields[0], 2018)
        self.assertEqual(parse_alarm("平成30年/1/1").fields[0], 2018)
        self.assertEqual(parse_alarm("令和元年/5/1").fields[0], 2019)

    def test_fullwidth(self):
        self.assertEqual(parse_alarm("／５　１２：５０").fields, parse_alarm("/5 12:50").fields)

    def test_invalid(self):
        for text in ("", "  ", "1:2:3:4", "1/2/3/4", "13/1", "/32", "24:00", "60", "abc",
                     "/5 /6", "12 13", "元年/1/1", "S60/1/1"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_alarm(text)


class AlarmScheduleTest(unittest.TestCase):
    def test_next_minute(self):
        self.assertEqual(schedule("12", NOW), [datetime(2026, 10, 7, 10, 12)])
        self.assertEqual(schedule("12", datetime(2026, 10, 7, 10, 30)), [datetime(2026, 10, 7, 11, 12)])

    def test_exact_time_is_not_now(self):
        self.assertEqual(schedule("12", datetime(2026, 10, 7, 10, 12)), [datetime(2026, 10, 7, 11, 12)])

    def test_next_day_of_month(self):
        self.assertEqual(schedule("/5 12:", NOW), [datetime(2026, 11, 5, 12)])

    def test_every_day_this_month(self):
        result = schedule("/* 12:50", datetime(2026, 10, 29, 13, 0), count=10)
        self.assertEqual(result, [datetime(2026, 10, 30, 12, 50), datetime(2026, 10, 31, 12, 50)])

    def test_every_day_starts_next_month_when_month_is_over(self):
        result = schedule("/* 12:50", datetime(2026, 10, 31, 13, 0), count=40)
        self.assertEqual(result[0], datetime(2026, 11, 1, 12, 50))
        self.assertEqual(result[-1], datetime(2026, 11, 30, 12, 50))
        self.assertEqual(len(result), 30)

    def test_every_year_every_month(self):
        result = schedule("*/*/5 10:*:20", NOW, count=62)
        self.assertEqual(result[0], datetime(2026, 11, 5, 10, 0, 20))
        self.assertEqual(result[1], datetime(2026, 11, 5, 10, 1, 20))
        self.assertEqual(result[59], datetime(2026, 11, 5, 10, 59, 20))
        self.assertEqual(result[60], datetime(2026, 12, 5, 10, 0, 20))
        self.assertEqual(result[61], datetime(2026, 12, 5, 10, 1, 20))

    def test_every_minute_within_current_hour(self):
        result = schedule("*", datetime(2026, 10, 7, 10, 57, 30), count=10)
        self.assertEqual(result, [datetime(2026, 10, 7, 10, 58), datetime(2026, 10, 7, 10, 59)])

    def test_unspecified_middle_field(self):
        self.assertEqual(schedule("令和8//5", NOW), [datetime(2026, 11, 5)])
        self.assertEqual(schedule("R9//5", NOW), [datetime(2027, 1, 5)])

    def test_unspecified_field_finer_than_every_is_not_fixed(self):
        result = schedule("*//5", NOW, count=3)
        self.assertEqual(result, [datetime(2026, 11, 5), datetime(2026, 12, 5), datetime(2027, 1, 5)])
        result = schedule("/* :30", datetime(2026, 10, 31, 22, 0), count=5)
        self.assertEqual(result, [datetime(2026, 10, 31, 22, 30), datetime(2026, 10, 31, 23, 30)])
        result = schedule("*/5 :30", NOW, count=3)
        self.assertEqual(
            result,
            [datetime(2026, 11, 5, 0, 30), datetime(2026, 11, 5, 1, 30), datetime(2026, 11, 5, 2, 30)],
        )

    def test_unspecified_field_coarser_than_every_is_fixed(self):
        self.assertEqual(schedule("*/5", NOW, count=5), [datetime(2026, 11, 5), datetime(2026, 12, 5)])

    def test_past_year(self):
        self.assertEqual(schedule("H30/1/1", NOW), [])

    def test_leap_day(self):
        self.assertEqual(schedule("2/29", NOW), [datetime(2028, 2, 29)])
        self.assertEqual(schedule("*/2/29", NOW, count=2), [datetime(2028, 2, 29), datetime(2032, 2, 29)])

    def test_nonexistent_date(self):
        self.assertEqual(schedule("2/30", NOW), [])
        self.assertEqual(schedule("2026/4/31", NOW), [])

    def test_last_year(self):
        self.assertEqual(schedule("9999/12/31 23:59:59", NOW), [datetime(9999, 12, 31, 23, 59, 59)])
        self.assertEqual(schedule("*/12/31 23:59:59", datetime(9999, 12, 31, 23, 59, 59)), [])

    def test_one_shot_does_not_repeat(self):
        spec = parse_alarm("12:50")
        self.assertFalse(spec.repeats)
        first = spec.first(NOW)
        self.assertIsNone(spec.next_after(first, first))


if __name__ == "__main__":
    unittest.main()
