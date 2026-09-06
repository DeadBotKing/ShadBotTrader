# وضعیت فعلی پروژه — 2026-09-05

## سیستم

ShadBotTrader — Dual/Triple Model Trading System
- Signal model: 5M candles → BUY/SELL
- Range model: 1D/1H/4H candles → High/Low فردا → TP/SL (ATR-normalized)
- Trend model: 1D/4H candles → GREEN/RED رنگ کندل بعدی
- Trend-signal model: 5M candles → BUY/HOLD/SELL (rolling 288)
- Trend-score model: 5M candles → score روند (−1..+1) رگرسیون
- Strategy: Triple (5M signal · 4H bracket · 1D trend)
- Broker: Alpari (spread=0.06%, session-first MT5)

## مدل‌های AI

| مدل | تایم‌فریم | نوع | تارگت | وضعیت |
|-----|-----------|------|--------|--------|
| gold_signal_5m | 5M | 2-class | first-passage ±0.6% | آموزش‌دیده (77.1%) — قدیمی، نیاز به ریترین |
| gold_range_1d | 1D | رگرسیون | High/Low ATR-normalized | قدیمی (pct) — ریترین لازم |
| gold_range_4h | 4H | رگرسیون | High/Low ATR-normalized | v3 — BEATS baseline 4% |
| gold_trend_1d | 1D | 2-class | رنگ کندل بعدی | v1 — BEATS baseline 57% vs 53.2% |
| gold_trend_score_5m | 5M | رگرسیون | score=(C−O)/(H−L) ∈(−1,+1) | در حال آموزش (window=288, 4×3) |
| gold_trend_signal_5m | 5M | 3-class | first ±0.5×ATR(1D) | نیاز به ریترین (بعد از فیکس مانع روزانه) |

## استراتژی Triple (فاز ۹۷)

```
مجوز ۱: سیگنال 5M احتمال > آستانهٔ GUI
مجوز ۲: شیب روزانه — مدل رنج 1D پیش‌بینی D1 → شیب High/Low نسبت به D0
         حالت‌ها: both | either | high | low (GUI)
مجوز ۳: سمت TP (خرید: TP > ورود)
مجوز ۴: نزدیکی ورود به سطح روزانه ≤ max_entry_distance_atr × ATR14(1D)
مجوز ۵ (آینده): رنگ ترند از gold_trend_<tf>
براکت: TP/SL از مدل رنج 4H با fallback: D0 → 5M-امروز
SL نهایی: ≥ min_sl_distance (GUI) و ≥ 2×spread
اسپرد: درصدی (GUI) — برخورد TP/SL روی BID/ASK
```

## گیت‌های فیلتر

| فیلتر | توضیح |
|-------|-------|
| EMA50 daily | SHORT ممنوع وقتی قیمت بالای EMA50، LONG وقتی زیر |
| Session filter | فقط ساعت‌های مشخص UTC |
| Min SL dist | حداقل فاصلهٔ SL از ورود (بعد از fallback) |
| 0-bar filter | حذف ترید‌های بسته‌شده در همان کندل ورود |

## زیرساخت MT5

- Session-first: اول اتصال به ترمینال (بدون credential) — اکانت‌های OTP کار می‌کنند
- symbol_select: قبل از هر fetch — خطای قابل‌فهم برای نمونه غلط/حساس به حروف
- mapping: XAUUSD → XAUUSD_i (Alpari)

## مدل‌های score (فاز ۹۸-ب)

```
gold_trend_score_5m: رگرسیون خالص
تارگت: score = (close−open)/(high−low) ∈ (−1,+1)
خروجی: Dense(1, tanh)
loss: Huber
معنی: +0.9 = صعود قوی، −0.9 = نزول قوی، ~0 = بی‌رون
```

## دستورات کلیدی

```bash
# آموزش trend_score
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend_score --range-timeframes 5M --signal-timeframe 5M \
  --epochs 50 --folds 3 --window 288 --label-horizon 288 \
  --learning-rate 0.0008 --storage-root datasets

# آموزش trend_signal (سه‌کلاسه)
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend_signal --range-timeframes 5M --signal-timeframe 5M \
  --epochs 50 --folds 3 --window 288 --learning-rate 0.0008 \
  --storage-root datasets

# آموزش trend رنگ (1D)
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend --range-timeframes 1D --signal-timeframe 1D \
  --epochs 50 --folds 3 --window 150 --learning-rate 0.0008 \
  --storage-root datasets

# بکتست triple
# GUI: strategy=triple | range_timeframe=4H | trend_filter=ema50
#      min_sl_dist=6 | atr_mult=0.5 | max_entry_distance_atr=0.25
```

## مسائل شناخته‌شده

- trend_signal مانع باید از ATR(1D) باشد نه ATR(5M) — فیکس شد (فاز ۹۸-ب) ولی مدل باید ریترین شود
- score نزدیک صفر در random walk طبیعی است — لبه واقعی از فیچرها می‌آید
- gold_signal_5m فقط 10 epoch آموزش دیده — ریترین جدی لازم دارد
- ES patience=400 عملاً خاموش است — 15-30 کافی است

## گام بعدی

1. آموزش gold_trend_signal_5m با مانع روزانه فیکس‌شده
2. آموزش gold_trend_score_5m (در جریان)
3. بکتست triple با مدل‌های جدید
4. مجوز ۶: رنگ ترند از gold_trend_<tf> در بکتست
