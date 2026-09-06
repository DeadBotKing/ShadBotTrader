# خلاصهٔ کامل جلسه — فاز ۹۵ تا ۹۹

**بازه:** 2026-08-30 تا 2026-09-05
**تعداد کامیت:** 74
**مدل‌های جدید:** ۴ (trend_1d، trend_score_5m، trend_signal_5m، range_4h)
**فایل‌های تغییرکرده:** 100+

---

## فاز ۹۵ — تارگت ATR-نرمال‌شده

**مشکل ریشه‌ای:** مدل رنج با تارگت `(high−close)/close` همیشه یک درصدد
ثابت را پیش‌بینی می‌کرد (±0.6% برای 1D، ±0.06% برای 1H) — چون ورودی
minmax بود و تارگت هم بدون مقیاس.

**راه‌حل:** تارگت = `(high−close)/ATR14` — مقیاس مستقل از قیمت،
مستقیماً قابل‌ترجمه به دلار (mult × ATR14 = دلار).

**زیرسیستم‌ها:**
- target_builder: wilder_atr_series + atr_from_candles
- RangeForecast: target_units + atr_reference + high/low_atr_mult
- RangePredictor: تبدیل ATR → دلار
- ModelRecord.target_units: "atr" یا "pct"

---

## فاز ۹۵-ب — گزارش آموزش ATR-آگاه

- ConsoleProgressReporter با واحد درست (ATR نه قیمت)
- سربرگ آموزش: `constant base` (خط پایهٔ پیش‌بینی ثابت)
- QUALITY: حکم صریح BEATS / NO BETTER

---

## فاز ۹۵-ج — حکم صادقانه + جلوگیری از مرگ LR

- val_mae تمام-سکانس vs final-step: فقط final-step معیار ترید است
- ReduceLR min_delta: 1e-6 → 1e-4 (کاسکید LR 8e-4→1e-6 رفع شد)
- ES min_delta: 1e-6 → 1e-4 (ES بالاخره واقعاً fire می‌شود)

---

## فاز ۹۵-د — پروفایل لیبل بر حسب k + خطای per-step

- `label profile`: میانهٔ لیبل هر گام k (train vs recent)
- `per-step MAE`: val_step{k}_mae

---

## فاز ۹۵-ه — رسم مسیر forecast روی چارت /data

- renderForecast هرگز draw() صدا نمی‌زد → مسیر رسم نمی‌شد
- localIdx باید slice-local باشد نه global

---

## فاز ۹۵-و — sanity prediction با مدل ذخیره‌شده

- save_model آرتیفکت واقعاً ذخیره‌شده را برمی‌گرداند
- sanity prediction با best checkpoint (نه خامِ آخرین فولد)

---

## فاز ۹۵-ز — حکم سطح-براکت (worst-case vs worst-case)

- val_bracket_mae: MAEِ (max_k high, min_k low) پیش‌بینی در برابر واقعی
- حکم VERDICT (bracket level)

---

## فاز ۹۶ — انتخاب نسخهٔ مدل در بکتست

- فرم: Range model = `id:vN` (مثلاً gold_range_1d:v1)
- بدون نسخه → latest (که می‌تواند مدل قدیمی باشد!)
- هشدار بلند: `range units: pct ‼️ PRE-Phase95 model`

---

## فاز ۹۶-ب — فیلتر ترند EMA50

- SHORT ممنوع وقتی قیمت بالای EMA50 روزانه؛ LONG وقتی زیر
- فرم: `trend_filter = ema50`
- آمار: `trend blocks: N`

---

## فاز ۹۷ — استراتژی سه‌تایم‌فریمی

```
پنجره: 288 کندل 5M (rolling — هر کندل یک نمونه)
خروجی: 3-class softmax (BUY / HOLD / SELL)
برچسب: اولین برخورد ±X×ATR14(1D) در 288 کندل آینده
       X = threshold (GUI، پیش‌فرض 0.5)
```

### مجوزهای ورود

| مجوز | شرط | منبع |
|------|------|-------|
| ۱ | P(signal) > آستانهٔ GUI | مدل 5M |
| ۲ | شیب روزانه (High/Low پیش‌بینی D1 vs D0 واقعی) ≥ 0 (خرید) | مدل رنج 1D |
| ۳ | سمت TP (خرید: TP > ورود) | محاسبه |
| ۴ | نزدیکی ورود به سطح روزانه ≤ max_entry_distance_atr | فیلتر |
| ۵ | (آینده) رنگ ترند از gold_trend_<tf> | مدل trend |
| ۶ | (آینده) P(BUY) > آستانه و > P(HOLD) | مدل trend_signal |

### براکت TP/SL

```
TP از مدل رنج 4H (High/Low پیش‌بینی)
SL از مدل رنج 4H
fallback 1: SL ≥ ورود → SL = Low(D0) / High(D0)
fallback 2: هنوز غلط → کمترین Low زیر ورود از 5Mهای امروز − اسپرد
کف: SL ≥ max(min_sl_distance, 2×spread)
```

---

## فاز ۹۸ — مدل ترند (رنگ کندل بعدی)

- `gold_trend_<tf>` — طبقه‌بندی GREEN/RED
- GREEN = close بعدی ≥ close فعلی
- /data: کلیک روی کندل → ▲ سبز/▼ قرمز + درصد

---

## فاز ۹۸-ب — مدل trend_score + رفع HOLD + رفع‌های /data

### trend_score
- رگرسیون خالص: score = (close−open)/(high−low) ∈ (−1,+1)
- Dense(1, tanh) — نه Dense(2, linear)
- خروجی مستقیماً «قدرت روند» را نشان می‌دهد

### رفع HOLD=0%
- مانع باید از بازهٔ 288 کندلی باشد (نه ATR14(5M)≈$2)
- بازه = max(high)−min(low) در 288 کندل → ~$30-40
- تأیید: sell 17.7% / hold 26.4% / buy 55.9% ✓

### رفع‌های /data
- مدل ترند در dropdown + کلیک → ▲/▼ رنگ + درصد
- فقط مدل‌های هم‌تایم‌فریم نمایش داده می‌شوند
- fetchTrendColor از مدل انتخابی استفاده می‌کند (نه hardcoded)
- renderTrendModel برای score/signal خروجی مخصوص دارد

---

## فاز ۹۹ — مدل سیگنال ترند (سه‌کلاسه)

- `gold_trend_signal_<tf>` — 3-class softmax (BUY/HOLD/SELL)
- برچسب: اولین برخورد ±X×ATR14(1D) در افق 288 کندل
- مانع از بازهٔ روزانه (نه ATR14(5M)) → HOLD واقعی تولید می‌شود
- PredictionTarget.num_classes: 1 (regression) / 2 / 3

---

## رفع‌های زیرساخت MT5

| فیکس | توضیح |
|-------|-------|
| Session-first | اول اتصال بدون credential (اکانت‌های OTP) |
| symbol_select | قبل از هر fetch + خطای قابل‌فهم |
| Case-sensitive | XAUUSD_i با i کوچک — پیام راهنما |

---

## جدول لبهٔ مدل‌ها

| مدل | baseline | val_acc/MAE | لبه |
|-----|----------|-------------|-----|
| trend_1d (رنگ) | 53.2% | 57.0% | +3.8% |
| range_4h (ATR) | 0.3848 | 0.239 | −38% MAE |
| trend_signal_5m | 55.1% | 44.9% | هنوز بدون لبه (نویز) |
| range_1d (5D horizon) | — | — | +55% skill |

## گام بعدی اپراتور

1. آموزش gold_trend_signal_5m با مانع روزانه فیکس‌شده
2. آموزش gold_trend_score_5m (در جریان — window=288, 4×3)
3. بکتست triple با مدل‌های جدید
4. مجوز ۶: رنگ ترند + score در بکتست
