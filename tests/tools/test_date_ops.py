import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from tools.date_ops import (
    get_current_date,
    calculate_future_date,
    resolve_travel_date,
    _resolve_to_date,
    _days_until_weekday,
)


class TestGetCurrentDate:
    def test_returns_string(self):
        result = get_current_date.invoke({})
        assert isinstance(result, str)

    def test_includes_date_and_weekday(self):
        result = get_current_date.invoke({})
        parts = result.split()
        assert len(parts) == 2
        datetime.strptime(parts[0], '%Y-%m-%d')
        assert parts[1] in ('Monday', 'Tuesday', 'Wednesday', 'Thursday',
                             'Friday', 'Saturday', 'Sunday')

    @patch('tools.date_ops.datetime')
    def test_returns_mocked_date_and_weekday(self, mock_dt):
        mock_dt.now.return_value = datetime(2025, 10, 9, 12, 0, 0)  # Thursday
        result = get_current_date.invoke({})
        assert result == '2025-10-09 Thursday'

    def test_tool_has_description(self):
        assert get_current_date.description


class TestCalculateFutureDate:
    def test_returns_string(self):
        assert isinstance(calculate_future_date.invoke({'days': 5}), str)

    def test_date_format(self):
        result = calculate_future_date.invoke({'days': 10})
        datetime.strptime(result, '%Y-%m-%d')

    @patch('tools.date_ops.datetime')
    def test_zero_days(self, mock_dt):
        mock_dt.now.return_value = datetime(2025, 10, 9, 12, 0, 0)
        assert calculate_future_date.invoke({'days': 0}) == '2025-10-09'

    @patch('tools.date_ops.datetime')
    def test_positive_days(self, mock_dt):
        mock_dt.now.return_value = datetime(2025, 10, 9, 12, 0, 0)
        assert calculate_future_date.invoke({'days': 7}) == '2025-10-16'

    @patch('tools.date_ops.datetime')
    def test_negative_days(self, mock_dt):
        mock_dt.now.return_value = datetime(2025, 10, 9, 12, 0, 0)
        assert calculate_future_date.invoke({'days': -5}) == '2025-10-04'

    def test_tool_has_description(self):
        assert calculate_future_date.description

    def test_tool_has_args_schema(self):
        assert calculate_future_date.args_schema


class TestDaysUntilWeekday:
    def test_same_day_returns_seven(self):
        assert _days_until_weekday(0, 0) == 7  # Monday → Monday

    def test_forward(self):
        assert _days_until_weekday(0, 4) == 4  # Monday → Friday

    def test_wraps_correctly(self):
        assert _days_until_weekday(5, 0) == 2  # Saturday → Monday


class TestResolveTravelDate:
    """Tests for _resolve_to_date (pure function) and the tool wrapper."""

    def _on(self, weekday_idx: int) -> datetime:
        """Return a Monday-anchored datetime offset by weekday_idx."""
        monday = datetime(2026, 5, 18)  # known Monday
        return monday + timedelta(days=weekday_idx)

    # --- tomorrow ---
    def test_tomorrow(self):
        thursday = self._on(3)  # Thu May 21
        result = _resolve_to_date.__wrapped__('tomorrow') if hasattr(_resolve_to_date, '__wrapped__') else None
        # Use direct call via patching datetime
        with patch('tools.date_ops.datetime') as mock_dt:
            mock_dt.now.return_value = thursday
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _resolve_to_date('tomorrow')
        assert result.strftime('%A') == 'Friday'

    # --- weekend expressions ---
    @pytest.mark.parametrize('weekday_idx,expr,expected_day', [
        (0, 'next weekend',  'Saturday'),   # Mon → Sat
        (1, 'next weekend',  'Saturday'),   # Tue → Sat
        (3, 'next weekend',  'Saturday'),   # Thu → Sat  (the user's bug case)
        (4, 'next weekend',  'Saturday'),   # Fri → Sat
        (5, 'next weekend',  'Saturday'),   # Sat → next Sat (7 days)
        (6, 'this weekend',  'Saturday'),   # Sun → next Sat
        (0, 'this weekend',  'Saturday'),   # Mon → Sat
        (5, 'this weekend',  'Saturday'),   # Sat → today (days=0)
    ])
    def test_weekend_expressions(self, weekday_idx, expr, expected_day):
        anchor = self._on(weekday_idx)
        with patch('tools.date_ops.datetime') as mock_dt:
            mock_dt.now.return_value = anchor
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _resolve_to_date(expr)
        assert result.strftime('%A') == expected_day

    # --- named weekday expressions ---
    @pytest.mark.parametrize('weekday_idx,expr,expected_day', [
        (0, 'next Friday',   'Friday'),    # Mon → Fri
        (3, 'next Friday',   'Friday'),    # Thu → Fri (1 day)
        (4, 'next Friday',   'Friday'),    # Fri → following Fri (7 days)
        (0, 'this Saturday', 'Saturday'),  # Mon → Sat
        (2, 'next Monday',   'Monday'),    # Wed → Mon
    ])
    def test_named_weekday_expressions(self, weekday_idx, expr, expected_day):
        anchor = self._on(weekday_idx)
        with patch('tools.date_ops.datetime') as mock_dt:
            mock_dt.now.return_value = anchor
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _resolve_to_date(expr)
        assert result.strftime('%A') == expected_day

    # --- numeric fallback via dateparser ---
    def test_in_7_days(self):
        # dateparser reads system time internally so we compare against the real now
        result = _resolve_to_date('in 7 days')
        expected = datetime.now() + timedelta(days=7)
        assert result.date() == expected.date()

    def test_invalid_expression_raises(self):
        with patch('tools.date_ops.datetime') as mock_dt:
            mock_dt.now.return_value = self._on(0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with pytest.raises(ValueError):
                _resolve_to_date('gzorp florp baz')

    def test_tool_returns_iso_date(self):
        result = resolve_travel_date.invoke({'expression': 'tomorrow'})
        datetime.strptime(result, '%Y-%m-%d')

    def test_tool_has_description(self):
        assert resolve_travel_date.description

    def test_tool_has_args_schema(self):
        assert resolve_travel_date.args_schema
