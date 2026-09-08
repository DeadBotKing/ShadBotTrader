# فاز ۱۱۶ — پیشنهاد: Hybrid Range-Aware Decision Engine

**وضعیت:** 🟡 پیشنهادی / طراحی مستند شد  
**نوع:** Ensemble decision layer / استفادهٔ کامل از مدل‌های range موجود  
**اولویت:** خیلی بالا بعد از فازهای ۱۱۰، ۱۱۱ و branch benchmark فاز ۱۱۲

---

## هدف

ساخت تصمیم نهایی معاملاتی از چند شاخهٔ مستقل، به جای تکیه روی یک مدل direction.

مدل‌های موجود که باید حتماً در طراحی لحاظ شوند:

```text
gold_range_1d  → high/low فردا، daily envelope
gold_range_4h  → high/low چهار ساعت آینده، TP/SL محلی
gold_trend_signal_5m → SELL/HOLD/BUY probability روی horizon 24h
```

مدل‌های پیشنهادی آینده:

```text
Tabular Boosters: LightGBM/CatBoost/XGBoost
BUY/SELL specialists: gold_buy_event_5m / gold_sell_event_5m
Meta-labeler: trade/no-trade filter
Conformal/Bayesian uncertainty gate
```

---

## معماری تصمیم نهایی

```text
5M feature window
      |
      |------------------------------
      |                              |
Direction branch                Range branch
      |                              |
WaveNet trend_signal             1D range: tomorrow envelope
Booster trend_signal             4H range: TP/SL bracket
BUY/SELL specialists             volatility/range sufficiency
      |                              |
      -------- calibrated signals ----
                    |
             Meta-label filter
                    |
          Uncertainty/no-trade gate
                    |
              Final decision
            BUY / SELL / NO_TRADE
```

---

## نقش دقیق هر مدل

### 1) `gold_trend_signal_5m`

وظیفه:

```text
احتمال SELL/HOLD/BUY بر اساس 24h گذشته و 24h horizon آینده
```

استفاده:

```text
side confidence اولیه
```

مثال:

```text
buy_prob=0.64, hold_prob=0.18, sell_prob=0.18 → BUY candidate
```

---

### 2) `gold_range_1d`

وظیفه:

```text
پیش‌بینی high/low فردا
```

استفاده:

```text
- daily envelope gate
- ممنوع کردن BUY نزدیک سقف پیش‌بینی‌شدهٔ فردا
- ممنوع کردن SELL نزدیک کف پیش‌بینی‌شدهٔ فردا
- بررسی کافی بودن فضای حرکت روزانه
```

قانون نمونه:

```text
BUY فقط اگر predicted_daily_high - entry >= min_reward_distance
SELL فقط اگر entry - predicted_daily_low  >= min_reward_distance
```

---

### 3) `gold_range_4h`

وظیفه:

```text
پیش‌بینی high/low چهار ساعت آینده
```

استفاده:

```text
- ساخت TP و SL واقع‌بینانه برای معاملهٔ جاری
- جلوگیری از TP غیرمنطقی خارج از range نزدیک
```

قانون نمونه برای BUY:

```text
TP = min(predicted_4h_high, predicted_daily_high)
SL = پایین‌تر از entry یا نزدیک predicted_4h_low، با رعایت min_sl_distance و spread
```

قانون نمونه برای SELL:

```text
TP = max(predicted_4h_low, predicted_daily_low)
SL = بالاتر از entry یا نزدیک predicted_4h_high، با رعایت min_sl_distance و spread
```

---

### 4) Booster / POSNEG branches

وظیفه:

```text
تأیید یا رد سیگنال direction اصلی
```

نمونه:

```text
trend_signal says BUY
LightGBM says BUY with enough probability
buy_event confirms
sell_event does not block
→ candidate stays alive
```

---

### 5) Meta-labeler

وظیفه:

```text
آیا این candidate واقعاً ارزش اجرا دارد؟
```

label برای meta-model:

```text
1 = اگر بعد از ورود، TP قبل از SL بخورد
0 = اگر SL اول بخورد یا timeout شود
```

ورودی meta-model:

```text
probabilities from all models
range_1d distances
range_4h TP/SL distances
spread/slippage/session/regime features
```

---

### 6) Uncertainty gate

وظیفه:

```text
اگر مدل‌ها نامطمئن‌اند، NO_TRADE بده.
```

روش‌های پیشنهادی:

```text
probability margin
entropy
conformal prediction set
MC-dropout/Bayesian uncertainty later
```

---

## Decision rule پیشنهادی نسخهٔ اول

### BUY

```text
BUY اگر:
  trend_signal.buy_prob >= buy_threshold
  و trend_signal.buy_prob - max(sell_prob, hold_prob) >= min_margin
  و buy_event_prob >= buy_event_threshold          [بعد از فاز 111]
  و sell_event_prob <= sell_block_threshold        [بعد از فاز 111]
  و predicted_4h_high - entry >= min_tp_distance
  و predicted_daily_high - entry >= min_daily_room
  و TP/SL پس از spread/slippage معتبر باشد
  و meta_filter_prob >= meta_threshold             [بعد از meta]
```

### SELL

```text
SELL اگر:
  trend_signal.sell_prob >= sell_threshold
  و trend_signal.sell_prob - max(buy_prob, hold_prob) >= min_margin
  و sell_event_prob >= sell_event_threshold
  و buy_event_prob <= buy_block_threshold
  و entry - predicted_4h_low >= min_tp_distance
  و entry - predicted_daily_low >= min_daily_room
  و TP/SL پس از spread/slippage معتبر باشد
  و meta_filter_prob >= meta_threshold
```

در غیر این صورت:

```text
NO_TRADE
```

---

## چرا این حالت از یک مدل تنها بهتر است؟

```text
- direction model فقط جهت را می‌گوید.
- range_4h می‌گوید آیا برای 4 ساعت آینده TP/SL منطقی داریم یا نه.
- range_1d می‌گوید آیا در envelope روزانه فضا داریم یا نه.
- POS/NEG متخصص‌ها BUY و SELL را جدا می‌سنجند.
- meta-labeler false positiveها را کم می‌کند.
- uncertainty gate جلوی معامله روی پیش‌بینی نامطمئن را می‌گیرد.
```

---

## فایل‌های درگیر پیشنهادی

```text
src/ShadBotTrader/domain/strategy/hybrid_decision.py
src/ShadBotTrader/application/services/hybrid_decision_service.py
src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py
src/ShadBotTrader/infrastructure/simulation/hybrid_prediction_source.py
scripts/run_hybrid_backtest.py
scripts/evaluate_hybrid_decisions.py
```

اما نباید معماری فعلی بدون اجازه redesign شود. نسخهٔ اول می‌تواند با extension روی backtest/strategy فعلی ساخته شود.

---

## معیار پذیرش

```text
- هیچ trade بدون reason log باز/رد نشود.
- 1D range و 4H range هر دو در تصمیم نهایی ثبت شوند.
- TP/SL خروجی همیشه spread/slippage/min distance را رعایت کند.
- اگر یکی از مدل‌ها missing/mismatched بود، خطای قابل فهم یا graceful fallback بدهد.
- نتیجه باید با model-only و random baseline مقایسه شود.
```
