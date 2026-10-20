"""Best Learning Rate Finder — مستقل از MT5 و داده واقعی.

این اسکریپت با داده‌های synthetic واقع‌گرایانه (شبیه XAUUSD) تست می‌کنه
و بهترین learning rate برای هر مدل رو پیدا می‌کنه.

اجرا:
  python scripts/find_best_lr.py

نتیجه:
  - بهترین LR برای signal model
  - بهترین LR برای range model
  - جدول کامل نتایج
"""

from __future__ import annotations

import math
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp


def make_synthetic_candles(
    n: int = 500,
    timeframe: str = "5M",
    seed: int = 42,
    trend_strength: float = 0.0003,
    vol: float = 0.002,
) -> list[Candle]:
    """کندل‌های synthetic واقع‌گرایانه شبیه XAUUSD.

    شامل:
    - Trend تصادفی (با احتمال تغییر)
    - Volatility Clustering (نویز متغیر)
    - Volume تقریبی
    """
    random.seed(seed)
    np.random.seed(seed)

    base_time = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    if timeframe == "5M":
        delta = timedelta(minutes=5)
    elif timeframe == "1H":
        delta = timedelta(hours=1)
    else:
        delta = timedelta(days=1)

    price = 2000.0
    candles = []
    trend = trend_strength
    vol_state = vol

    for i in range(n):
        # تغییر تصادفی جهت ترند
        if random.random() < 0.03:
            trend = -trend

        # Volatility Clustering
        vol_state = 0.95 * vol_state + 0.05 * (vol * (1 + 2 * random.random()))

        # حرکت قیمت
        ret = trend + np.random.normal(0, vol_state)
        price = price * (1 + ret)
        price = max(price, 100.0)

        # ساختار کندل
        rng = abs(np.random.normal(0, vol_state * 2)) * price
        high = price + rng * (0.5 + 0.5 * random.random())
        low = price - rng * (0.5 + 0.5 * random.random())
        open_ = price + np.random.normal(0, rng * 0.3)
        low = min(low, min(price, open_))
        high = max(high, max(price, open_))

        volume = max(500.0 + np.random.exponential(1000.0), 10.0)

        ts = base_time + delta * i
        candles.append(
            Candle(
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(ts),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(high, 2)))),
                low=Price(Decimal(str(round(low, 2)))),
                close=Price(Decimal(str(round(price, 2)))),
                volume=Decimal(str(round(volume, 1))),
            )
        )
    return candles


def rule(text: str, width: int = 70) -> None:
    print(f"\n{'-' * width}")
    print(f"  {text}")
    print(f"{'-' * width}")


def search_lr_for_role(
    role_name: str,
    timeframe: str,
    n_candles: int,
    window_size: int,
    candidates: list[float],
    pilot_epochs: int = 1,
    pilot_folds: int = 1,
    seed: int = 42,
) -> tuple[float, list[tuple[float, float, str]]]:
    """بهترین LR رو با pilot training پیدا می‌کنه."""
    from ShadBotTrader.application.services.dual_model_service import DualModelService
    from ShadBotTrader.domain.feature.ports import FeatureCalculator
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.model_roles import range_model_role, signal_model_role
    from ShadBotTrader.infrastructure.ai.training_progress import NullProgressReporter
    from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1

    def _safe_registry():
        """Registry بدون pywt — فقط causal calculators."""
        from ShadBotTrader.infrastructure.feature.calculators.adaptive_filters import AdaptiveFiltersCalculator
        from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
        from ShadBotTrader.infrastructure.feature.calculators.balance import BalanceCalculator
        from ShadBotTrader.infrastructure.feature.calculators.bollinger import BollingerCalculator
        from ShadBotTrader.infrastructure.feature.calculators.bollinger_bands import BollingerBandsCalculator
        from ShadBotTrader.infrastructure.feature.calculators.candle_pattern import CandlePatternCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ehlers_advanced import EhlersAdvancedCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ehlers_cycle import EhlersCycleCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
        from ShadBotTrader.infrastructure.feature.calculators.fractal_stats import FractalStatsCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ichimoku import IchimokuCalculator
        from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
        from ShadBotTrader.infrastructure.feature.calculators.market_regime import MarketRegimeCalculator
        from ShadBotTrader.infrastructure.feature.calculators.mean_reversion import MeanReversionCalculator
        from ShadBotTrader.infrastructure.feature.calculators.momentum_advanced import MomentumAdvancedCalculator
        from ShadBotTrader.infrastructure.feature.calculators.prado_features import PradoFeaturesCalculator
        from ShadBotTrader.infrastructure.feature.calculators.price_filter import PriceFilterCalculator
        from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
        from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
        from ShadBotTrader.infrastructure.feature.calculators.session_time import SessionTimeCalculator
        from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
        from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator
        from ShadBotTrader.infrastructure.feature.calculators.structure_features import StructureFeaturesCalculator
        from ShadBotTrader.infrastructure.feature.calculators.target import TargetCalculator
        from ShadBotTrader.infrastructure.feature.calculators.trend_strength import TrendStrengthCalculator
        from ShadBotTrader.infrastructure.feature.calculators.volatility_breakout import VolatilityBreakoutCalculator
        from ShadBotTrader.infrastructure.feature.calculators.volume_analysis import VolumeAnalysisCalculator

        class _SafeRegistry:
            def __init__(self):
                self._map = {
                    "adaptive_filters": AdaptiveFiltersCalculator(),
                    "atr": AtrCalculator(),
                    "balance": BalanceCalculator(),
                    "bollinger": BollingerCalculator(),
                    "bband": BollingerBandsCalculator(),
                    "candle_pattern": CandlePatternCalculator(),
                    "ehlers_advanced": EhlersAdvancedCalculator(),
                    "ehlers_cycle": EhlersCycleCalculator(),
                    "ema": EmaCalculator(),
                    "fractal_stats": FractalStatsCalculator(),
                    "ichimoku": IchimokuCalculator(),
                    "macd": MacdCalculator(),
                    "market_regime": MarketRegimeCalculator(),
                    "mean_reversion": MeanReversionCalculator(),
                    "momentum_advanced": MomentumAdvancedCalculator(),
                    "prado_features": PradoFeaturesCalculator(),
                    "price_filter": PriceFilterCalculator(),
                    "returns": ReturnsCalculator(),
                    "rsi": RsiCalculator(),
                    "session_time": SessionTimeCalculator(),
                    "sma": SmaCalculator(),
                    "stochastic": StochasticCalculator(),
                    "structure_features": StructureFeaturesCalculator(),
                    "target": TargetCalculator(),
                    "trend_strength": TrendStrengthCalculator(),
                    "volatility_breakout": VolatilityBreakoutCalculator(),
                    "volume_analysis": VolumeAnalysisCalculator(),
                }

            def resolve(self, family: str):
                return self._map.get(family)

        return _SafeRegistry()

    try:
        from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
    except ImportError:
        CalculatorRegistry = None

    rule(f"LR SEARCH — {role_name.upper()} / {timeframe}  ({n_candles} candles)")
    print(f"  window_size : {window_size}")
    print(f"  candidates  : {', '.join(f'{r:.1e}' for r in candidates)}")
    print(f"  pilot       : {pilot_epochs} epoch(s), {pilot_folds} fold(s)")
    print()

    candles = make_synthetic_candles(n=n_candles, timeframe=timeframe, seed=seed)

    feature_set = standard_feature_set_v1()
    # CalculatorRegistry به pywt وابسته‌ست — از resolver ای استفاده می‌کنیم
    # که فقط causal calculators رو load می‌کنه
    try:
        if CalculatorRegistry is not None:
            resolver = CalculatorRegistry()
        else:
            resolver = _safe_registry()
    except Exception:
        resolver = _safe_registry()
    service = DualModelService(
        feature_set=feature_set,
        resolver=resolver,
        include_features=True,
    )

    if role_name == "signal":
        role = signal_model_role(timeframe=timeframe, window_size=window_size)
        metric_key = "val_loss"
    else:
        role = range_model_role(timeframe=timeframe, window_size=window_size)
        metric_key = "val_mae"

    results: list[tuple[float, float, str]] = []

    for lr in candidates:
        t0 = time.monotonic()
        print(f"  testing {lr:.1e} ...", end=" ", flush=True)
        try:
            outcome = service.train(
                candles=candles,
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe(timeframe),
                role=role,
                run_id=f"lr-search-{role_name}-{lr:.1e}",
                epochs=pilot_epochs,
                max_folds=pilot_folds,
                progress=NullProgressReporter(),
                learning_rate=lr,
            )
            metrics_list = outcome.get("fold_metrics") or [{}]
            m = metrics_list[-1] if metrics_list else {}
            score = m.get(metric_key) or m.get("val_loss")
            if score is None:
                raise ValueError(f"متریک {metric_key} پیدا نشد")
            score = float(score)
            dt = time.monotonic() - t0
            status = f"{metric_key}={score:.6f}  ({dt:.1f}s)"
            results.append((lr, score, status))
            print(status)
        except Exception as e:
            dt = time.monotonic() - t0
            status = f"FAILED: {type(e).__name__}: {str(e)[:60]}  ({dt:.1f}s)"
            results.append((lr, float("inf"), status))
            print(status)

    valid = [(lr, s, st) for lr, s, st in results if math.isfinite(s)]
    if not valid:
        raise RuntimeError("همه candidate ها شکست خوردن")

    best_lr, best_score, _ = min(valid, key=lambda x: x[1])
    print(f"\n  [OK] بهترین LR: {best_lr:.2e}  ({metric_key}={best_score:.6f})")
    return best_lr, results


def main() -> None:
    print("=" * 70)
    print("  ShadBotTrader — Best Learning Rate Finder")
    print("  با داده synthetic واقع‌گرایانه (XAUUSD-like)")
    print("=" * 70)

    # -- تنظیمات جستجو ----------------------------------------------------
    # candidates: بازه وسیع از خیلی کوچیک تا خیلی بزرگ
    LR_CANDIDATES = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3]

    # حداقل کندل = max_warmup(~80) + window_size + horizon + min_train + val_size
    # Signal: 80 + 200 + 0 + 50 + 50 = 380  ->  600 کندل برای تست کافیه
    # Range:  80 + 100 + 5 + 30 + 30 = 245  ->  400 کندل روزانه
    # pilot_folds=1: فقط یه fold — کافیه برای مقایسه نسبی LR ها
    SIGNAL_CONFIG = {
        "timeframe": "5M",
        "n_candles": 700,   # 80 warmup + 200 window + 420 training
        "window_size": 200, # مطابق با تنظیمات کاربر (200 × 5M)
        "pilot_epochs": 1,
        "pilot_folds": 1,
    }

    RANGE_CONFIG = {
        "timeframe": "1D",
        "n_candles": 400,   # 80 warmup + 100 window + 220 training
        "window_size": 100, # مطابق با تنظیمات کاربر (100 × 1D)
        "pilot_epochs": 1,
        "pilot_folds": 1,
    }

    all_results = {}

    # -- Signal Model -----------------------------------------------------
    try:
        best_signal_lr, signal_results = search_lr_for_role(
            role_name="signal",
            candidates=LR_CANDIDATES,
            **SIGNAL_CONFIG,
        )
        all_results["signal"] = {
            "best_lr": best_signal_lr,
            "results": signal_results,
            "config": SIGNAL_CONFIG,
        }
    except Exception as e:
        print(f"\n[FAIL] Signal search خطا: {e}")
        best_signal_lr = 1e-4
        all_results["signal"] = {"best_lr": best_signal_lr, "error": str(e)}

    # -- Range Model -------------------------------------------------------
    try:
        best_range_lr, range_results = search_lr_for_role(
            role_name="range",
            candidates=LR_CANDIDATES,
            **RANGE_CONFIG,
        )
        all_results["range"] = {
            "best_lr": best_range_lr,
            "results": range_results,
            "config": RANGE_CONFIG,
        }
    except Exception as e:
        print(f"\n[FAIL] Range search خطا: {e}")
        best_range_lr = 1e-4
        all_results["range"] = {"best_lr": best_range_lr, "error": str(e)}

    # -- گزارش نهایی -------------------------------------------------------
    rule("FINAL REPORT — RECOMMENDED LEARNING RATES")

    print(f"\n  {'Model':<12} {'Best LR':<12} {'Config'}")
    print(f"  {'-'*12} {'-'*12} {'-'*40}")

    if "results" in all_results.get("signal", {}):
        sig_config = all_results["signal"]["config"]
        print(
            f"  {'Signal':<12} {all_results['signal']['best_lr']:<12.2e} "
            f"{sig_config['timeframe']}, window={sig_config['window_size']}, "
            f"candles={sig_config['n_candles']}"
        )
        print(f"\n  جدول کامل Signal:")
        for lr, score, status in all_results["signal"]["results"]:
            marker = " <- BEST" if lr == all_results["signal"]["best_lr"] else ""
            print(f"    {lr:.1e}  ->  {status}{marker}")

    if "results" in all_results.get("range", {}):
        rng_config = all_results["range"]["config"]
        print(
            f"\n  {'Range':<12} {all_results['range']['best_lr']:<12.2e} "
            f"{rng_config['timeframe']}, window={rng_config['window_size']}, "
            f"candles={rng_config['n_candles']}"
        )
        print(f"\n  جدول کامل Range:")
        for lr, score, status in all_results["range"]["results"]:
            marker = " <- BEST" if lr == all_results["range"]["best_lr"] else ""
            print(f"    {lr:.1e}  ->  {status}{marker}")

    print("\n" + "=" * 70)
    print("  [OK] خلاصه توصیه:")
    print(f"  Signal Model LR : {all_results.get('signal', {}).get('best_lr', '?'):.2e}")
    print(f"  Range  Model LR : {all_results.get('range',  {}).get('best_lr', '?'):.2e}")
    print()
    print("  نکته: این نتایج از داده synthetic هستن.")
    print("  با داده واقعی (5M و 1D) نتایج متفاوت می‌تونه باشه.")
    print("  از OPTIMISE LEARNING RATE در داشبورد با داده واقعی هم استفاده کنید.")
    print("=" * 70)


if __name__ == "__main__":
    main()
