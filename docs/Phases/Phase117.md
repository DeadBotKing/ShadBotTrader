# فاز ۱۱۷ — پیشنهاد: Advanced Neural Architecture Benchmarks

**وضعیت:** 🟡 پیشنهادی / فقط بعد از داشتن baselineهای قوی  
**نوع:** Research benchmark، نه جایگزینی فوری production  
**اولویت:** متوسط بعد از LightGBM/POSNEG/Hybrid decision

---

## هدف

تست معماری‌های neural جدیدتر فقط وقتی معنی دارد که baselineهای ساده‌تر ما مشخص باشند. این فاز برای پیدا کردن معماری بهتر از WaveNet فعلی است، اما هیچ معماری صرفاً به خاطر اسم جدید وارد production نمی‌شود.

---

## مدل‌های قابل تست

### 1) WaveNet عمیق‌تر / TCN tuned

مدل فعلی `trend_signal` معمولاً:

```text
window=288
n_layers=3
n_blocks=2
RF=57 bars ≈ 4h45m
```

تست پیشنهادی:

```text
n_layers=5
n_blocks=2
RF=249 bars ≈ 20h45m
```

مزیت:

```text
پوشش بیشتر از پنجرهٔ 24 ساعته
```

ریسک:

```text
overfit بیشتر
```

---

### 2) MiniRocket / MultiRocket

برای time-series classification سریع و قوی است.

کاربرد:

```text
SELL/HOLD/BUY benchmark روی windowهای 5M
```

مزیت:

```text
سرعت بالا، هزینه کم، baseline جدی برای classification
```

---

### 3) LITE / LITEMV / InceptionTime

برای time-series classification با چند kernel/scale.

مزیت:

```text
الگوهای کوتاه و بلند را همزمان می‌بیند.
```

برای ما مخصوصاً روی XAUUSD مناسب است چون حرکت‌ها در sessionهای مختلف scale متفاوت دارند.

---

### 4) xLSTM-TS + wavelet denoising

ایده:

```text
اول نویز قیمت/return با wavelet کاهش یابد
بعد xLSTM-TS sequence را یاد بگیرد
```

مزیت:

```text
memory/gating بهتر از LSTM معمولی
```

ریسک:

```text
پیاده‌سازی سنگین‌تر و نیازمند PyTorch/کتابخانهٔ جدید
```

---

### 5) TSMixer / TiDE

مدل‌های سبک‌تر از Transformer برای forecasting/time-series.

کاربرد برای ما:

```text
classification head روی representation خروجی
یا forecasting auxiliary برای range/volatility
```

---

### 6) PatchTST

Transformer patch-based برای long lookback.

کاربرد:

```text
288 کندل → patchهای 12/24 کندلی → classifier
```

ریسک:

```text
ممکن است روی دیتای مالی کم‌سیگنال فقط overfit کند؛ باید با baseline و significance سنجیده شود.
```

---

### 7) Mamba / Attention-Mamba

State-space model برای long sequence با هزینه کمتر از attention کامل.

کاربرد:

```text
branch تحقیقاتی برای trend_signal یا range/volatility
```

---

### 8) KAN / KANsLTformer / KAN-GAT

به‌خصوص برای gold در researchها نتایج جذاب دیده شده، اما جدید و پرریسک است.

کاربرد پیشنهادی:

```text
فقط بعد از داشتن external/regime features و baselineهای قوی.
```

---

## مدل‌هایی که فعلاً رد می‌شوند

```text
Vanilla LSTM ساده
Vanilla GRU ساده
Transformer خام بدون patching/gating
Dense+Flatten بزرگ
GAN برای تولید signal
RL به عنوان predictor اصلی
```

دلیل:

```text
یا از مدل فعلی بهتر نیستند، یا validation/backtest آنها در finance بسیار شکننده است.
```

---

## معیار پذیرش

هر معماری advanced باید از این‌ها عبور کند:

```text
- همان split/purge مثل مدل فعلی
- همان train_ratio و label rule
- class weights/calibration قابل اعمال
- مقایسه با WaveNet و LightGBM/CatBoost/XGBoost
- action_precision و coverage بهتر بعد از calibration
- PnL بهتر با spread/slippage
- significance check بعد از انتخاب بهترین candidate
```

اگر فقط `accuracy` یا `train loss` بهتر بود ولی PnL/precision/significance بهتر نشد، رد می‌شود.
