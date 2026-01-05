"""
Technical indicators client using Twelve Data API.
https://twelvedata.com/docs

Indicators (4 API calls, within free tier limit of 8/min):
1. SMA (200) - Trend: "Big Picture" - Buy when price is above
2. MACD (12, 26, 9) - Momentum: Trend strength/weakness
3. Bollinger Bands (20, 2) - Volatility: Price range from average
4. RSI (14) - Sentiment: Overbought (>70) / Oversold (<30)
"""
import os
import requests
from typing import Any, Optional
from dataclasses import dataclass

TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"


@dataclass
class SMAData:
    value: float
    timestamp: str
    raw: Any = None


@dataclass
class MACDData:
    macd: float
    macd_signal: float
    macd_hist: float
    timestamp: str
    raw: Any = None


@dataclass
class BollingerBandsData:
    upper_band: float
    middle_band: float
    lower_band: float
    timestamp: str
    raw: Any = None


@dataclass
class RSIData:
    value: float
    timestamp: str
    raw: Any = None


@dataclass
class EMAData:
    value: float
    timestamp: str
    raw: Any = None


@dataclass
class ATRData:
    value: float
    timestamp: str
    raw: Any = None


@dataclass
class TechnicalIndicators:
    sma_200: Optional[SMAData] = None
    macd: Optional[MACDData] = None
    bbands: Optional[BollingerBandsData] = None
    rsi: Optional[RSIData] = None
    current_price: Optional[float] = None


def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing: {key}")
    return value


def fetch_sma(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 200) -> SMAData:
    """Fetch Simple Moving Average (SMA) - Trend indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/sma",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"SMA data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return SMAData(
        value=float(latest["sma"]),
        timestamp=latest["datetime"],
        raw=data,
    )


def fetch_macd(
    symbol: str = "BTC/USD",
    interval: str = "1day",
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> MACDData:
    """Fetch MACD - Momentum indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/macd",
        params={
            "symbol": symbol,
            "interval": interval,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"MACD data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return MACDData(
        macd=float(latest["macd"]),
        macd_signal=float(latest["macd_signal"]),
        macd_hist=float(latest["macd_hist"]),
        timestamp=latest["datetime"],
        raw=data,
    )


def fetch_bbands(
    symbol: str = "BTC/USD",
    interval: str = "1day",
    time_period: int = 20,
    sd: float = 2.0
) -> BollingerBandsData:
    """Fetch Bollinger Bands - Volatility indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/bbands",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "sd": sd,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"Bollinger Bands data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return BollingerBandsData(
        upper_band=float(latest["upper_band"]),
        middle_band=float(latest["middle_band"]),
        lower_band=float(latest["lower_band"]),
        timestamp=latest["datetime"],
        raw=data,
    )


def fetch_rsi(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 14) -> RSIData:
    """Fetch RSI - Sentiment/Overbought/Oversold indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/rsi",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"RSI data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return RSIData(
        value=float(latest["rsi"]),
        timestamp=latest["datetime"],
        raw=data,
    )


def fetch_ema(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 21) -> EMAData:
    """Fetch Exponential Moving Average (EMA) - Trend indicator with more weight on recent prices."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/ema",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"EMA data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return EMAData(
        value=float(latest["ema"]),
        timestamp=latest["datetime"],
        raw=data,
    )


def fetch_atr(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 14) -> ATRData:
    """Fetch Average True Range (ATR) - Volatility indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/atr",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"ATR data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return ATRData(
        value=float(latest["atr"]),
        timestamp=latest["datetime"],
        raw=data,
    )


def fetch_all_indicators(symbol: str = "BTC/USD", interval: str = "1day") -> TechnicalIndicators:
    """Fetch all technical indicators for a symbol (4 API calls)."""
    return TechnicalIndicators(
        sma_200=fetch_sma(symbol, interval, time_period=200),
        macd=fetch_macd(symbol, interval),
        bbands=fetch_bbands(symbol, interval),
        rsi=fetch_rsi(symbol, interval),
    )


def format_indicators_context(indicators: TechnicalIndicators, current_price: float) -> str:
    """Format technical indicators as context for AI prompt (raw values only, no interpretation)."""
    lines = ["TECHNICAL INDICATORS:"]

    # SMA 200 - Trend (Big Picture)
    if indicators.sma_200:
        lines.append(f"1. SMA(200): ${indicators.sma_200.value:,.2f}")

    # MACD - Momentum
    if indicators.macd:
        lines.append(f"2. MACD(12,26,9): MACD={indicators.macd.macd:.2f}, Signal={indicators.macd.macd_signal:.2f}, Histogram={indicators.macd.macd_hist:.2f}")

    # Bollinger Bands - Volatility
    if indicators.bbands:
        lines.append(f"3. Bollinger Bands(20,2): Upper=${indicators.bbands.upper_band:,.2f}, Middle=${indicators.bbands.middle_band:,.2f}, Lower=${indicators.bbands.lower_band:,.2f}")

    # RSI - Sentiment
    if indicators.rsi:
        lines.append(f"4. RSI(14): {indicators.rsi.value:.1f}")

    return "\n".join(lines)
