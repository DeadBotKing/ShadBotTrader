"""
LR Search دقیق — بدون نیاز به MT5

روش: 3-fold walk-forward روی داده synthetic واقع‌گرایانه
با فیچرهای کامل (causal، scope-filtered)
"""

from __future__ import annotations
import math, random, sys, time
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# -- ساخت کندل synthetic ----------------------------------------------------
def make_candles(n: int, timeframe: str = "5M", seed: int = 42):
    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp

    random.seed(seed); np.random.seed(seed)
    base  = datetime(2024, 1, 2, tzinfo=timezone.utc)
    delta = timedelta(minutes=5) if timeframe == "5M" else timedelta(days=1)
    price = 2000.0
    candles = []
    trend   = 0.0002
    vol     = 0.002

    for i in range(n):
        # Volatility clustering + trend reversal
        if random.random() < 0.03:
            trend = -trend
        vol = 0.95 * vol + 0.05 * abs(np.random.normal(0, 0.003))
        ret = trend + np.random.normal(0, vol)
        price = max(price * (1 + ret), 50.0)

        rng = abs(np.random.normal(0, price * vol * 1.5))
        hi  = price + rng * random.uniform(0.4, 1.0)
        lo  = price - rng * random.uniform(0.4, 1.0)
        op  = price + np.random.normal(0, rng * 0.3)
        lo  = min(lo, min(price, op))
        hi  = max(hi, max(price, op))
        vol_val = max(200.0 + np.random.exponential(1500.0), 10.0)

        candles.append(Candle(
            symbol     = Symbol("XAUUSD"),
            timeframe  = Timeframe(timeframe),
            open_time  = Timestamp(base + delta * i),
            open_price = Price(Decimal(str(round(op,   2)))),
            high       = Price(Decimal(str(round(hi,   2)))),
            low        = Price(Decimal(str(round(lo,   2)))),
            close      = Price(Decimal(str(round(price,2)))),
            volume     = Decimal(str(round(vol_val, 1))),
        ))
    return candles


# -- Registry بدون pywt -----------------------------------------------------
def make_registry():
    from ShadBotTrader.infrastructure.feature.calculators.adaptive_filters    import AdaptiveFiltersCalculator
    from ShadBotTrader.infrastructure.feature.calculators.atr                 import AtrCalculator
    from ShadBotTrader.infrastructure.feature.calculators.balance              import BalanceCalculator
    from ShadBotTrader.infrastructure.feature.calculators.bollinger            import BollingerCalculator
    from ShadBotTrader.infrastructure.feature.calculators.bollinger_bands      import BollingerBandsCalculator
    from ShadBotTrader.infrastructure.feature.calculators.candle_pattern       import CandlePatternCalculator
    from ShadBotTrader.infrastructure.feature.calculators.ehlers_advanced      import EhlersAdvancedCalculator
    from ShadBotTrader.infrastructure.feature.calculators.ehlers_cycle         import EhlersCycleCalculator
    from ShadBotTrader.infrastructure.feature.calculators.ema                  import EmaCalculator
    from ShadBotTrader.infrastructure.feature.calculators.fractal_stats        import FractalStatsCalculator
    from ShadBotTrader.infrastructure.feature.calculators.ichimoku             import IchimokuCalculator
    from ShadBotTrader.infrastructure.feature.calculators.macd                 import MacdCalculator
    from ShadBotTrader.infrastructure.feature.calculators.market_regime        import MarketRegimeCalculator
    from ShadBotTrader.infrastructure.feature.calculators.mean_reversion       import MeanReversionCalculator
    from ShadBotTrader.infrastructure.feature.calculators.momentum_advanced    import MomentumAdvancedCalculator
    from ShadBotTrader.infrastructure.feature.calculators.prado_features       import PradoFeaturesCalculator
    from ShadBotTrader.infrastructure.feature.calculators.price_filter         import PriceFilterCalculator
    from ShadBotTrader.infrastructure.feature.calculators.returns              import ReturnsCalculator
    from ShadBotTrader.infrastructure.feature.calculators.rsi                  import RsiCalculator
    from ShadBotTrader.infrastructure.feature.calculators.session_time         import SessionTimeCalculator
    from ShadBotTrader.infrastructure.feature.calculators.sma                  import SmaCalculator
    from ShadBotTrader.infrastructure.feature.calculators.stochastic           import StochasticCalculator
    from ShadBotTrader.infrastructure.feature.calculators.structure_features   import StructureFeaturesCalculator
    from ShadBotTrader.infrastructure.feature.calculators.target               import TargetCalculator
    from ShadBotTrader.infrastructure.feature.calculators.trend_strength       import TrendStrengthCalculator
    from ShadBotTrader.infrastructure.feature.calculators.volatility_breakout  import VolatilityBreakoutCalculator
    from ShadBotTrader.infrastructure.feature.calculators.volume_analysis      import VolumeAnalysisCalculator

    class _R:
        def __init__(self):
            self._m = {
                "adaptive_filters": AdaptiveFiltersCalculator(),
                "atr": AtrCalculator(), "balance": BalanceCalculator(),
                "bollinger": BollingerCalculator(), "bband": BollingerBandsCalculator(),
                "candle_pattern": CandlePatternCalculator(),
                "ehlers_advanced": EhlersAdvancedCalculator(),
                "ehlers_cycle": EhlersCycleCalculator(),
                "ema": EmaCalculator(), "fractal_stats": FractalStatsCalculator(),
                "ichimoku": IchimokuCalculator(), "macd": MacdCalculator(),
                "market_regime": MarketRegimeCalculator(),
                "mean_reversion": MeanReversionCalculator(),
                "momentum_advanced": MomentumAdvancedCalculator(),
                "prado_features": PradoFeaturesCalculator(),
                "price_filter": PriceFilterCalculator(),
                "returns": ReturnsCalculator(), "rsi": RsiCalculator(),
                "session_time": SessionTimeCalculator(), "sma": SmaCalculator(),
                "stochastic": StochasticCalculator(),
                "structure_features": StructureFeaturesCalculator(),
                "target": TargetCalculator(),
                "trend_strength": TrendStrengthCalculator(),
                "volatility_breakout": VolatilityBreakoutCalculator(),
                "volume_analysis": VolumeAnalysisCalculator(),
            }
        def resolve(self, f): return self._m.get(f)
    return _R()


# -- جستجوی LR --------------------------------------------------------------
def search(role_name: str, timeframe: str, n_candles: int,
           window_size: int, candidates: list[float],
           folds: int = 2, epochs: int = 2, seed: int = 42) -> list[tuple[float, float, float]]:
    """
    برای هر LR candidate:
      - `folds` fold اجرا می‌کنه
      - میانگین val_metric رو برمی‌گردونه
    خروجی: [(lr, mean_metric, std_metric)]
    """
    from ShadBotTrader.application.services.dual_model_service import DualModelService
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.model_roles import signal_model_role, range_model_role
    from ShadBotTrader.infrastructure.ai.training_progress import NullProgressReporter
    from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1

    candles   = make_candles(n_candles, timeframe, seed)
    fs        = standard_feature_set_v1()
    resolver  = make_registry()
    service   = DualModelService(feature_set=fs, resolver=resolver, include_features=True)
    metric_key = "val_loss" if role_name == "signal" else "val_mae"

    role = (signal_model_role(timeframe=timeframe, window_size=window_size)
            if role_name == "signal"
            else range_model_role(timeframe=timeframe, window_size=window_size))

    results = []
    for lr in candidates:
        fold_scores = []
        t0 = time.monotonic()
        ok = True
        for fold_seed in range(folds):
            try:
                outcome = service.train(
                    candles=make_candles(n_candles, timeframe, seed + fold_seed * 7),
                    symbol=Symbol("XAUUSD"),
                    timeframe=Timeframe(timeframe),
                    role=role,
                    run_id=f"lr-{role_name}-{lr:.1e}-f{fold_seed}",
                    epochs=epochs,
                    max_folds=1,
                    progress=NullProgressReporter(),
                    learning_rate=lr,
                )
                m = (outcome.get("fold_metrics") or [{}])[-1]
                score = m.get(metric_key) or m.get("val_loss")
                if score is None:
                    raise ValueError("no metric")
                fold_scores.append(float(score))
            except Exception as e:
                print(f"    fold {fold_seed} FAILED: {e}")
                ok = False
                break

        dt = time.monotonic() - t0
        if ok and fold_scores:
            mean_s = float(np.mean(fold_scores))
            std_s  = float(np.std(fold_scores))
            results.append((lr, mean_s, std_s))
            print(f"  {lr:.2e}  {metric_key}={mean_s:.5f} +/-{std_s:.5f}  ({dt:.0f}s)")
        else:
            results.append((lr, float("inf"), 0.0))
            print(f"  {lr:.2e}  FAILED  ({dt:.0f}s)")

    return results


def banner(text: str):
    w = 68
    print("\n" + "="*w)
    print(f"  {text}")
    print("="*w)


def main():
    import os
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    print("=" * 68)
    print("  ShadBotTrader — LR Search دقیق")
    print("  روش: 2-fold × 2-epoch روی داده synthetic XAUUSD-like")
    print("=" * 68)

    # کندیدای اولیه — بازه وسیع
    CANDIDATES_COARSE = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]

    # ================================================================
    # 1. Signal Model — جستجوی درشت
    # ================================================================
    banner("SIGNAL MODEL — جستجوی درشت (5M، window=200، 700 کندل)")
    print(f"  candidates: {[f'{c:.1e}' for c in CANDIDATES_COARSE]}\n")

    sig_coarse = search(
        role_name="signal", timeframe="5M",
        n_candles=700, window_size=200,
        candidates=CANDIDATES_COARSE,
        folds=2, epochs=2,
    )

    valid_sig = [(lr, m, s) for lr, m, s in sig_coarse if math.isfinite(m)]
    if not valid_sig:
        print("[FAIL] همه Signal candidate ها شکست خوردن")
        best_sig_coarse = 1e-4
    else:
        best_sig_coarse = min(valid_sig, key=lambda x: x[1])[0]
        print(f"\n  بهترین اولیه: {best_sig_coarse:.2e}")

    # -- جستجوی ظریف اطراف بهترین --
    idx = CANDIDATES_COARSE.index(best_sig_coarse) if best_sig_coarse in CANDIDATES_COARSE else 2
    lo  = CANDIDATES_COARSE[max(0, idx-1)]
    hi  = CANDIDATES_COARSE[min(len(CANDIDATES_COARSE)-1, idx+1)]
    CANDIDATES_FINE_SIG = sorted(set([
        lo, lo*2, lo*3,
        best_sig_coarse,
        hi/3, hi/2, hi,
    ]))
    # حذف مقادیر خیلی کوچک یا بزرگ
    CANDIDATES_FINE_SIG = [c for c in CANDIDATES_FINE_SIG if 1e-6 <= c <= 5e-2]

    banner("SIGNAL MODEL — جستجوی ظریف")
    print(f"  بازه: [{lo:.1e}, {hi:.1e}]")
    print(f"  candidates: {[f'{c:.2e}' for c in CANDIDATES_FINE_SIG]}\n")

    sig_fine = search(
        role_name="signal", timeframe="5M",
        n_candles=700, window_size=200,
        candidates=CANDIDATES_FINE_SIG,
        folds=3, epochs=2, seed=99,
    )

    valid_sig_f = [(lr, m, s) for lr, m, s in sig_fine if math.isfinite(m)]
    if valid_sig_f:
        best_sig_lr, best_sig_score, best_sig_std = min(valid_sig_f, key=lambda x: x[1])
    else:
        best_sig_lr, best_sig_score, best_sig_std = best_sig_coarse, float("inf"), 0.0

    # ================================================================
    # 2. Range Model — جستجوی درشت
    # ================================================================
    banner("RANGE MODEL — جستجوی درشت (1D، window=100، 400 کندل)")
    print(f"  candidates: {[f'{c:.1e}' for c in CANDIDATES_COARSE]}\n")

    rng_coarse = search(
        role_name="range", timeframe="1D",
        n_candles=400, window_size=100,
        candidates=CANDIDATES_COARSE,
        folds=2, epochs=2,
    )

    valid_rng = [(lr, m, s) for lr, m, s in rng_coarse if math.isfinite(m)]
    if not valid_rng:
        print("[FAIL] همه Range candidate ها شکست خوردن")
        best_rng_coarse = 1e-4
    else:
        best_rng_coarse = min(valid_rng, key=lambda x: x[1])[0]
        print(f"\n  بهترین اولیه: {best_rng_coarse:.2e}")

    idx2 = CANDIDATES_COARSE.index(best_rng_coarse) if best_rng_coarse in CANDIDATES_COARSE else 2
    lo2  = CANDIDATES_COARSE[max(0, idx2-1)]
    hi2  = CANDIDATES_COARSE[min(len(CANDIDATES_COARSE)-1, idx2+1)]
    CANDIDATES_FINE_RNG = sorted(set([
        lo2, lo2*2, lo2*3,
        best_rng_coarse,
        hi2/3, hi2/2, hi2,
    ]))
    CANDIDATES_FINE_RNG = [c for c in CANDIDATES_FINE_RNG if 1e-6 <= c <= 5e-2]

    banner("RANGE MODEL — جستجوی ظریف")
    print(f"  بازه: [{lo2:.1e}, {hi2:.1e}]")
    print(f"  candidates: {[f'{c:.2e}' for c in CANDIDATES_FINE_RNG]}\n")

    rng_fine = search(
        role_name="range", timeframe="1D",
        n_candles=400, window_size=100,
        candidates=CANDIDATES_FINE_RNG,
        folds=3, epochs=2, seed=99,
    )

    valid_rng_f = [(lr, m, s) for lr, m, s in rng_fine if math.isfinite(m)]
    if valid_rng_f:
        best_rng_lr, best_rng_score, best_rng_std = min(valid_rng_f, key=lambda x: x[1])
    else:
        best_rng_lr, best_rng_score, best_rng_std = best_rng_coarse, float("inf"), 0.0

    # ================================================================
    # گزارش نهایی
    # ================================================================
    banner("FINAL REPORT — RECOMMENDED LEARNING RATES")

    print(f"""
  ┌---------------------------------------------------------┐
  │  Signal Model (5M / window=200)                          │
  │    LR پیشنهادی:  {best_sig_lr:.2e}                           │
  │    val_loss:      {best_sig_score:.5f} +/- {best_sig_std:.5f}            │
  │                                                         │
  │  Range Model (1D / window=100)                           │
  │    LR پیشنهادی:  {best_rng_lr:.2e}                           │
  │    val_mae:       {best_rng_score:.5f} +/- {best_rng_std:.5f}            │
  └---------------------------------------------------------┘

  جدول کامل Signal:""")
    for lr, m, s in sorted(sig_coarse + sig_fine, key=lambda x: x[0]):
        marker = " <- BEST" if abs(lr - best_sig_lr) < 1e-10 else ""
        status = f"val_loss={m:.5f} +/-{s:.5f}" if math.isfinite(m) else "FAILED"
        print(f"    {lr:.2e}  {status}{marker}")

    print(f"\n  جدول کامل Range:")
    for lr, m, s in sorted(rng_coarse + rng_fine, key=lambda x: x[0]):
        marker = " <- BEST" if abs(lr - best_rng_lr) < 1e-10 else ""
        status = f"val_mae={m:.5f} +/-{s:.5f}" if math.isfinite(m) else "FAILED"
        print(f"    {lr:.2e}  {status}{marker}")

    print(f"""
  [WARN]  این نتایج از داده synthetic هستن.
  با داده واقعی XAUUSD از OPTIMISE LEARNING RATE در داشبورد استفاده کن.
""")


if __name__ == "__main__":
    main()
