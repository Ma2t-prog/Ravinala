"""Lightweight global market header utilities used by legacy tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


STATUS_COLORS = {
    "OPEN": "#00C853",
    "PRE-MARKET": "#FFD600",
    "LUNCH": "#FF9100",
    "POST-MARKET": "#448AFF",
    "CLOSED": "#616161",
    "WEEKEND": "#757575",
    "HOLIDAY": "#9E9E9E",
}


@dataclass(frozen=True)
class MarketSession:
    name: str
    timezone: str
    open_time: time
    close_time: time
    flag: str
    pre_market_start: time | None = None
    post_market_end: time | None = None
    lunch_start: time | None = None
    lunch_end: time | None = None


class WorldMarketClocks:
    MARKETS = [
        MarketSession("NYSE", "America/New_York", time(9, 30), time(16, 0), "🇺🇸", pre_market_start=time(4, 0), post_market_end=time(20, 0)),
        MarketSession("LSE", "Europe/London", time(8, 0), time(16, 30), "🇬🇧"),
        MarketSession("EUREX", "Europe/Berlin", time(9, 0), time(17, 30), "🇩🇪"),
        MarketSession("TSE", "Asia/Tokyo", time(9, 0), time(15, 0), "🇯🇵", lunch_start=time(11, 30), lunch_end=time(12, 30)),
    ]

    def get_market_status(self, market: MarketSession, _now: datetime | None = None) -> dict:
        now = _now or datetime.now(ZoneInfo(market.timezone))
        local_now = now.astimezone(ZoneInfo(market.timezone))
        weekday = local_now.weekday()

        if weekday >= 5:
            status = "WEEKEND"
            progress = None
            time_to_open = None
            time_to_close = None
        else:
            current = local_now.timetz().replace(tzinfo=None)
            open_dt = datetime.combine(local_now.date(), market.open_time, tzinfo=local_now.tzinfo)
            close_dt = datetime.combine(local_now.date(), market.close_time, tzinfo=local_now.tzinfo)
            pre_dt = datetime.combine(local_now.date(), market.pre_market_start, tzinfo=local_now.tzinfo) if market.pre_market_start else None
            post_dt = datetime.combine(local_now.date(), market.post_market_end, tzinfo=local_now.tzinfo) if market.post_market_end else None
            lunch_start_dt = datetime.combine(local_now.date(), market.lunch_start, tzinfo=local_now.tzinfo) if market.lunch_start else None
            lunch_end_dt = datetime.combine(local_now.date(), market.lunch_end, tzinfo=local_now.tzinfo) if market.lunch_end else None

            if lunch_start_dt and lunch_end_dt and lunch_start_dt.time() <= current < lunch_end_dt.time():
                status = "LUNCH"
                progress = None
                time_to_open = None
                time_to_close = lunch_end_dt - local_now
            elif market.open_time <= current <= market.close_time:
                status = "OPEN"
                total_seconds = (close_dt - open_dt).total_seconds()
                elapsed = max((local_now - open_dt).total_seconds(), 0.0)
                progress = max(0.0, min(elapsed / total_seconds, 1.0)) if total_seconds > 0 else 0.0
                time_to_open = None
                time_to_close = close_dt - local_now
            elif pre_dt and pre_dt.time() <= current < market.open_time:
                status = "PRE-MARKET"
                progress = None
                time_to_open = open_dt - local_now
                time_to_close = None
            elif post_dt and market.close_time < current <= post_dt.time():
                status = "POST-MARKET"
                progress = None
                time_to_open = None
                time_to_close = None
            else:
                status = "CLOSED"
                progress = None
                next_open = open_dt if current < market.open_time else open_dt + timedelta(days=1)
                time_to_open = next_open - local_now
                time_to_close = None

        next_event = "Closed"
        if status == "OPEN" and time_to_close is not None:
            next_event = f"Closes in {self._fmt_delta(time_to_close)}"
        elif status == "PRE-MARKET" and time_to_open is not None:
            next_event = f"Opens in {self._fmt_delta(time_to_open)}"
        elif status == "POST-MARKET":
            next_event = "Post-market"
        elif status == "LUNCH":
            next_event = "Lunch break"
        elif time_to_open is not None:
            next_event = f"Next open in {self._fmt_delta(time_to_open)}"

        return {
            "name": market.name,
            "flag": market.flag,
            "status": status,
            "status_color": STATUS_COLORS[status],
            "session_progress_pct": progress,
            "time_to_open": time_to_open,
            "time_to_close": time_to_close,
            "open_str": market.open_time.strftime("%H:%M"),
            "next_event": next_event,
        }

    def get_all_statuses(self) -> list[dict]:
        statuses = [self.get_market_status(market) for market in self.MARKETS]
        order = {"OPEN": 0, "PRE-MARKET": 1, "LUNCH": 2, "POST-MARKET": 3, "CLOSED": 4, "WEEKEND": 5, "HOLIDAY": 6}
        return sorted(statuses, key=lambda item: order.get(item["status"], 99))

    def get_session_overlap_matrix(self) -> dict:
        open_count = sum(1 for status in self.get_all_statuses() if status["status"] == "OPEN")
        if open_count >= 3:
            liquidity = "HIGH"
        elif open_count >= 2:
            liquidity = "MEDIUM"
        else:
            liquidity = "LOW"
        return {"liquidity_level": liquidity, "open_markets": open_count}

    @staticmethod
    def _fmt_delta(delta: timedelta) -> str:
        minutes = max(int(delta.total_seconds() // 60), 0)
        hours, mins = divmod(minutes, 60)
        if hours:
            return f"{hours}h{mins:02d}"
        return f"{mins}m"


class MarketHeatStrip:
    HEAT_INSTRUMENTS = ["^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^FCHI", "^GDAXI", "^FTSE", "^N225", "^VIX", "BTC-USD", "CL=F"]
    LABELS = {
        "^GSPC": "S&P",
        "^IXIC": "Nasdaq",
        "^DJI": "Dow",
        "^STOXX50E": "SX5E",
        "^FCHI": "CAC",
        "^GDAXI": "DAX",
        "^FTSE": "FTSE",
        "^N225": "Nikkei",
        "^VIX": "VIX",
        "BTC-USD": "BTC",
        "CL=F": "WTI",
    }

    def _color_for_pct(self, pct: float, inverted: bool = False) -> str:
        value = -pct if inverted else pct
        if value >= 2.5:
            return "#00C853"
        if value >= 0.5:
            return "#66BB6A"
        if value <= -2.5:
            return "#FF1744"
        if value <= -0.5:
            return "#EF5350"
        return "#616161"

    def compute_heat(self, _prices: dict[str, tuple[float, float]] | None = None) -> list[dict]:
        prices = _prices or {symbol: (100.0, 100.0) for symbol in self.HEAT_INSTRUMENTS}
        cells = []
        for symbol in self.HEAT_INSTRUMENTS:
            last, prev = prices.get(symbol, (100.0, 100.0))
            change_pct = ((last / prev) - 1.0) * 100 if prev else 0.0
            inverted = symbol == "^VIX"
            cells.append(
                {
                    "symbol": symbol,
                    "label": self.LABELS.get(symbol, symbol),
                    "last": last,
                    "change_pct": change_pct,
                    "heat_color": self._color_for_pct(change_pct, inverted=inverted),
                    "heat_level": "flat",
                    "tooltip": f"{symbol}: {change_pct:+.2f}%",
                }
            )
        return cells

    def compute_global_sentiment(self, cells: list[dict]) -> dict:
        if not cells:
            return {"score": 0.0, "label": "NEUTRAL", "color": "#616161", "emoji": "•", "description": "No market data"}

        score = sum(float(cell.get("change_pct", 0.0)) for cell in cells) / max(len(cells), 1)
        score = max(min(score * 10.0, 100.0), -100.0)
        if score >= 20:
            label, color, emoji, desc = "RISK ON", "#00C853", "↑", "Broad risk appetite"
        elif score <= -20:
            label, color, emoji, desc = "PANIC", "#FF1744", "↓", "Broad risk aversion"
        elif score > 5:
            label, color, emoji, desc = "CAUTIOUS", "#FFD600", "•", "Positive but measured"
        else:
            label, color, emoji, desc = "NEUTRAL", "#616161", "•", "Mixed market tone"
        return {"score": score, "label": label, "color": color, "emoji": emoji, "description": desc}


class MarketPulseTicker:
    def build(self, prices: dict[str, tuple[float, float]] | None = None) -> list[dict]:
        prices = prices or {}
        data = []
        for symbol, (last, prev) in prices.items():
            change_pct = ((last / prev) - 1.0) * 100 if prev else 0.0
            data.append({"symbol": symbol, "last": last, "change_pct": change_pct})
        return data


class MarketAlertEngine:
    def __init__(self):
        self._cooldown: dict[str, bool] = {}

    def scan_alerts(self, data: dict) -> list[dict]:
        alerts: list[dict] = []
        heat_cells = data.get("heat_cells", [])
        ticker_data = data.get("ticker_data", [])
        clocks = data.get("clock_statuses", [])

        def add(level: str, category: str, message: str):
            key = f"{category}:{message}"
            if self._cooldown.get(key):
                return
            self._cooldown[key] = True
            alerts.append({"level": level, "category": category, "message": message})

        for item in heat_cells:
            if item.get("symbol") == "^VIX":
                if float(item.get("last", 0)) >= 40 or float(item.get("change_pct", 0)) >= 15:
                    add("CRITICAL", "VOL", "VIX extreme")
                elif float(item.get("last", 0)) >= 30 or float(item.get("change_pct", 0)) >= 5:
                    add("WARNING", "VOL", "VIX spike")
            if item.get("symbol") == "^GSPC" and abs(float(item.get("change_pct", 0))) >= 4:
                add("WARNING", "EQUITY", "Large S&P move")

        for item in ticker_data:
            if item.get("symbol") == "BTC-USD" and float(item.get("last", 0)) >= 100000:
                add("INFO", "CRYPTO", "BTC above 100k")
            if item.get("symbol") == "CL=F" and float(item.get("last", 0)) >= 100:
                add("WARNING", "COMMODITY", "WTI above 100")

        for clock in clocks:
            if clock.get("status") == "PRE-MARKET" and isinstance(clock.get("time_to_open"), timedelta):
                if clock["time_to_open"] <= timedelta(minutes=15):
                    add("INFO", "SESSION", f"{clock.get('name', 'Market')} opening soon")

        priority = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        return sorted(alerts, key=lambda alert: priority.get(alert["level"], 99))[:5]


class SessionTimeline:
    def __init__(self):
        self.clocks = WorldMarketClocks()

    def generate_timeline_data(self) -> dict:
        statuses = self.clocks.get_all_statuses()
        markets = []
        for market in self.clocks.MARKETS:
            status = next(item for item in statuses if item["name"] == market.name)
            segments = []
            if market.pre_market_start:
                segments.append({"start": self._to_hour(market.pre_market_start), "end": self._to_hour(market.open_time), "type": "pre"})
            segments.append({"start": self._to_hour(market.open_time), "end": self._to_hour(market.close_time), "type": "open"})
            if market.lunch_start and market.lunch_end:
                segments.append({"start": self._to_hour(market.lunch_start), "end": self._to_hour(market.lunch_end), "type": "lunch"})
            if market.post_market_end:
                segments.append({"start": self._to_hour(market.close_time), "end": self._to_hour(market.post_market_end), "type": "post"})

            markets.append(
                {
                    "market_name": market.name,
                    "segments": segments,
                    "is_open_now": status["status"] == "OPEN",
                }
            )

        now_utc = datetime.now(timezone.utc)
        return {"current_time_utc": now_utc.hour + now_utc.minute / 60.0, "markets": markets}

    @staticmethod
    def _to_hour(value: time) -> float:
        return value.hour + value.minute / 60.0
