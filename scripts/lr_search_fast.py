"""
LR Search سریع — مدل کوچک، داده کم، ولی معنادار
هدف: پیدا کردن بازه بهینه LR برای هر مدل
"""
from __future__ import annotations
import math, os, random, sys, time
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_candles(n: int, tf: str = "5M", seed: int = 42):
    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp
    random.seed(seed); np.random.seed(seed)
    base = datetime(2024, 1, 2, tzinfo=timezone.utc)
    delta = timedelta(minutes=5) if tf == "5M" else timedelta(days=1)
    price, trend, vol = 2000.0, 0.0002, 0.002
    out = []
    for i in range(n):
        if random.random() < 0.03: trend = -trend
        vol = 0.95*vol + 0.05*abs(np.random.normal(0, 0.003))
        price = max(price*(1 + trend + np.random.normal(0, vol)), 50.0)
        rng = abs(np.random.normal(0, price*vol*1.5))
        hi = price + rng*random.uniform(0.4, 1.0)
        lo = price - rng*random.uniform(0.4, 1.0)
        op = price + np.random.normal(0, rng*0.3)
        lo = min(lo, min(price, op)); hi = max(hi, max(price, op))
        out.append(Candle(symbol=Symbol("XAUUSD"), timeframe=Timeframe(tf),
            open_time=Timestamp(base + delta*i),
            open_price=Price(Decimal(str(round(op,2)))),
            high=Price(Decimal(str(round(hi,2)))),
            low=Price(Decimal(str(round(lo,2)))),
            close=Price(Decimal(str(round(price,2)))),
            volume=Decimal(str(round(max(100.0+np.random.exponential(800),10),1)))))
    return out


def train_one(role_name, tf, n_candles, window_size, lr, seed=42, epochs=1, max_folds=1):
    """یه training کوچک — فقط بازگشت val metric"""
    from ShadBotTrader.application.services.dual_model_service import DualModelService
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.model_roles import signal_model_role, range_model_role
    from ShadBotTrader.infrastructure.ai.training_progress import NullProgressReporter
    from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1
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
                "adaptive_filters":AdaptiveFiltersCalculator(),"atr":AtrCalculator(),
                "balance":BalanceCalculator(),"bollinger":BollingerCalculator(),
                "bband":BollingerBandsCalculator(),"candle_pattern":CandlePatternCalculator(),
                "ehlers_advanced":EhlersAdvancedCalculator(),"ehlers_cycle":EhlersCycleCalculator(),
                "ema":EmaCalculator(),"fractal_stats":FractalStatsCalculator(),
                "ichimoku":IchimokuCalculator(),"macd":MacdCalculator(),
                "market_regime":MarketRegimeCalculator(),"mean_reversion":MeanReversionCalculator(),
                "momentum_advanced":MomentumAdvancedCalculator(),"prado_features":PradoFeaturesCalculator(),
                "price_filter":PriceFilterCalculator(),"returns":ReturnsCalculator(),
                "rsi":RsiCalculator(),"session_time":SessionTimeCalculator(),"sma":SmaCalculator(),
                "stochastic":StochasticCalculator(),"structure_features":StructureFeaturesCalculator(),
                "target":TargetCalculator(),"trend_strength":TrendStrengthCalculator(),
                "volatility_breakout":VolatilityBreakoutCalculator(),"volume_analysis":VolumeAnalysisCalculator(),
            }
        def resolve(self, f): return self._m.get(f)

    candles  = make_candles(n_candles, tf, seed)
    fs       = standard_feature_set_v1()
    resolver = _R()
    svc      = DualModelService(feature_set=fs, resolver=resolver, include_features=True)
    role     = (signal_model_role(timeframe=tf, window_size=window_size)
                if role_name == "signal"
                else range_model_role(timeframe=tf, window_size=window_size))
    metric_k = "val_loss" if role_name == "signal" else "val_mae"

    out = svc.train(candles=candles, symbol=Symbol("XAUUSD"),
                    timeframe=Timeframe(tf), role=role,
                    run_id=f"lr-{role_name}-{lr:.1e}",
                    epochs=epochs, max_folds=max_folds,
                    progress=NullProgressReporter(), learning_rate=lr)
    m = (out.get("fold_metrics") or [{}])[-1]
    score = m.get(metric_k) or m.get("val_loss")
    if score is None:
        raise ValueError(f"no metric in {list(m.keys())}")
    return float(score)


def search_two_phase(role_name, tf, n_candles, window_size):
    """جستجوی دو مرحله‌ای: coarse → fine"""
    print(f"\n{'═'*60}")
    print(f"  {role_name.upper()} MODEL  ({tf}, window={window_size}, {n_candles} candles)")
    print(f"{'═'*60}")

    # ── Phase 1: Coarse (log-scale) ─────────────────────────────────
    coarse = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
    print(f"\n  Phase 1 — Coarse (1 epoch, 1 fold):")
    coarse_res = []
    for lr in coarse:
        t0 = time.monotonic()
        try:
            score = train_one(role_name, tf, n_candles, window_size, lr,
                              seed=42, epochs=1, max_folds=1)
            dt = time.monotonic() - t0
            coarse_res.append((lr, score))
            print(f"    {lr:.1e}  →  {score:.5f}  ({dt:.0f}s)")
        except Exception as e:
            dt = time.monotonic() - t0
            coarse_res.append((lr, float("inf")))
            print(f"    {lr:.1e}  →  FAILED: {str(e)[:60]}  ({dt:.0f}s)")

    valid = [(lr, s) for lr, s in coarse_res if math.isfinite(s)]
    if not valid:
        print("  ❌ همه coarse شکست خوردن")
        return None, coarse_res, []

    # سه تا بهترین coarse
    top3 = sorted(valid, key=lambda x: x[1])[:3]
    top3_lrs = [lr for lr, _ in top3]
    best_coarse_lr = top3_lrs[0]
    print(f"\n  Top-3 coarse: {[f'{lr:.1e}' for lr in top3_lrs]}")

    # ── Phase 2: Fine (دو طرف هر کدام از top-3) ─────────────────────
    fine_cands = set()
    for lr in top3_lrs:
        fine_cands.add(lr)
        fine_cands.add(lr * 1.5)
        fine_cands.add(lr * 2.0)
        fine_cands.add(lr / 1.5)
        fine_cands.add(lr / 2.0)
    fine_cands = sorted(c for c in fine_cands if 5e-6 <= c <= 2e-2)
    # حذف تکراری با coarse
    fine_cands = sorted(set(fine_cands) - set(c for c, _ in coarse_res))

    if not fine_cands:
        best_lr = best_coarse_lr
        return best_lr, coarse_res, []

    print(f"\n  Phase 2 — Fine (2 epoch, 2 fold):")
    fine_res = []
    for lr in fine_cands:
        scores = []
        t0 = time.monotonic()
        for s in [42, 77]:  # 2 different seeds = 2 folds
            try:
                sc = train_one(role_name, tf, n_candles, window_size, lr,
                               seed=s, epochs=2, max_folds=1)
                scores.append(sc)
            except Exception:
                scores.append(float("inf"))
        dt = time.monotonic() - t0
        mean_s = float(np.mean(scores))
        std_s  = float(np.std(scores))
        fine_res.append((lr, mean_s, std_s))
        status = f"{mean_s:.5f} ±{std_s:.5f}" if math.isfinite(mean_s) else "FAILED"
        print(f"    {lr:.2e}  →  {status}  ({dt:.0f}s)")

    # ترکیب همه نتایج
    all_valid = ([(lr, s, 0.0) for lr, s in valid] +
                 [(lr, m, st) for lr, m, st in fine_res if math.isfinite(m)])
    if not all_valid:
        return best_coarse_lr, coarse_res, fine_res

    best = min(all_valid, key=lambda x: x[1])
    best_lr = best[0]
    print(f"\n  ✅ بهترین LR: {best_lr:.2e}  (score={best[1]:.5f})")
    return best_lr, coarse_res, fine_res


def main():
    print("=" * 60)
    print("  ShadBotTrader — LR Search دقیق (2-phase)")
    print("  داده synthetic واقع‌گرایانه XAUUSD-like")
    print("=" * 60)

    best_sig, sig_c, sig_f = search_two_phase(
        "signal", "5M", n_candles=700, window_size=200)

    best_rng, rng_c, rng_f = search_two_phase(
        "range", "1D", n_candles=400, window_size=100)

    # ── گزارش نهایی ────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("  FINAL RECOMMENDATION")
    print(f"{'═'*60}")
    print(f"\n  Signal Model (5M / window=200):  LR = {best_sig:.2e}"
          if best_sig else "\n  Signal: failed")
    print(f"  Range  Model (1D / window=100):  LR = {best_rng:.2e}"
          if best_rng else "\n  Range: failed")

    print(f"\n  جدول کامل Signal:")
    all_sig = ([(lr, s, 0.0) for lr, s in sig_c] +
               [(lr, m, st) for lr, m, st in sig_f])
    for lr, m, std in sorted(all_sig, key=lambda x: x[0]):
        mark = " ← BEST" if best_sig and abs(lr - best_sig) < 1e-10 else ""
        line = f"val_loss={m:.5f}" if math.isfinite(m) else "FAILED"
        if std > 0: line += f" ±{std:.5f}"
        print(f"    {lr:.2e}  {line}{mark}")

    print(f"\n  جدول کامل Range:")
    all_rng = ([(lr, s, 0.0) for lr, s in rng_c] +
               [(lr, m, st) for lr, m, st in rng_f])
    for lr, m, std in sorted(all_rng, key=lambda x: x[0]):
        mark = " ← BEST" if best_rng and abs(lr - best_rng) < 1e-10 else ""
        line = f"val_mae={m:.5f}" if math.isfinite(m) else "FAILED"
        if std > 0: line += f" ±{std:.5f}"
        print(f"    {lr:.2e}  {line}{mark}")

    print("\n  ⚠️  نتایج از داده synthetic — با داده واقعی از OPTIMISE LR استفاده کن.\n")


if __name__ == "__main__":
    main()
