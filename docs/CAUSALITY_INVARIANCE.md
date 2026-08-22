# Causality and Transformer Invariance Audit

## هدف

وجود `causality=CAUSAL` در کاتالوگ به‌تنهایی proof نیست. برای اثبات عملی،
آزمون runtime دو دیتاست می‌سازد:

- `D`: سری اصلی؛
- `D'`: همان سری تا نقطهٔ `T`، اما با آیندهٔ متفاوت.

برای هر feature و برای ماتریس production باید داشته باشیم:

```text
F(D)[0:T] == F(D')[0:T]
```

اگر یک feature اعلام کرده باشد causal اما prefix تغییر کند، audit شکست می‌خورد.
Featureهای research-only عمداً ممکن است تغییر کنند، ولی چون `causal_only=True`
هستند وارد model/live input نمی‌شوند.

## چه چیزی در کد اضافه شد

ماژول زیر ابزار مشترک تست و dashboard است:

```text
src/ShadBotTrader/infrastructure/feature/invariance_audit.py
```

این ماژول سه تست دارد:

1. `audit_feature_set_invariance` — تمام 109 calculator definition؛
2. `audit_matrix_invariance` — ماتریس کامل 70 ستونی causal؛
3. `audit_transformer_invariance` — تشخیص fit روی کل سری در برابر fit روی train prefix.

دکمهٔ dashboard:

```text
Run causality invariance test
```

با دادهٔ ذخیره‌شده کار می‌کند. اگر هنوز داده‌ای در storage نباشد، عملیات reject
می‌شود و باید ابتدا از dashboard دادهٔ واقعی fetch شود.

## وضعیت PCA / Fourier / Wavelet / Divergence

این خانواده‌ها هنوز full-series یا centered هستند و production-safe نیستند:

- Wavelet noise filter؛
- Fourier dominant-period fit؛
- PCA/SVD؛
- Ichimoku `chikou`؛
- divergence با centered extrema؛
- future target shifts.

آن‌ها در catalog نگه داشته شده‌اند تا research catalog کامل بماند، اما در causal
model input مسدود هستند. نتیجهٔ فعلی:

```text
catalog       109
causal input   56 catalogue features + 14 candle columns = 70 columns
excluded       53
```

PCA stateful و Fourier train-prefix transformer هنوز به production اضافه نشده‌اند؛
در نتیجه artifact state آن‌ها هم وجود ندارد و استفادهٔ تصادفی از آن‌ها ممکن نیست.

## Scaler

مدل فعلی از `minmax_scale_window` استفاده می‌کند. این scaler برای هر input window
به‌صورت محلی محاسبه می‌شود و فقط همان window را می‌بیند؛ بنابراین fit سراسری روی
train+test ندارد. تست invariance آن نیز اضافه شده است.

هر scaler یا transformer آینده باید یکی از این دو قرارداد را رعایت کند:

```text
fit(train_prefix) -> frozen state
transform(train/validation/test/live) -> same state
```

یا کاملاً window-local باشد و از محدودهٔ تصمیم جاری بیرون نرود. `fit_transform` روی
کل سری برای production ممنوع است.

## Purged validation

`expanding_split` اکنون علاوه بر gap عادی، در صورت داشتن endpoint target، train را
تا اولین نقطهٔ unsafe کوتاه می‌کند. این برای signal first-passage لازم است، چون
horizon آن variable و unbounded است. برای range نیز endpoint برابر `window_end +
range_horizon` ثبت می‌شود.

هر fold باید این را پاس کند:

```text
train input end < validation input start
train target end < validation input start
```

## Window count

`PreparedDataset` قبل از trainer به ردیف‌های دارای label کامل join می‌شود. بنابراین
برای range horizon قبلاً از tail حذف شده و نباید دوباره در گزارش window count کم شود.
فرمول trainer در این مرحله:

```text
windows = aligned_rows - window_size + 1
```

کم‌کردن horizon برای بار دوم اصلاح شد و گزارش matrix نیز صریحاً می‌گوید که horizon
قبلاً روی labelها اعمال شده است.

## Range metrics

`val_mae` کلی به‌تنهایی کافی نیست. آموزش و independent evaluation اکنون جداگانه
گزارش می‌کنند:

```text
high_mae / low_mae
high_rmse / low_rmse
high_bias / low_bias
```

در independent evaluation، high/low آینده ابتدا از `return_1` و high/low نسبی
هر candle به offset نسبت به close فعلی تبدیل می‌شود؛ مقایسهٔ مستقیم `max(high_rel)`
اصلاح شده است.

## محدودیت فعلی

این audit proof اجرای واقعی روی دادهٔ کاربر نیست تا زمانی که دادهٔ واقعی از dashboard
fetch و اجرا شود. در workspace عمداً dataset/model نگه‌داری نمی‌شود. بنابراین:

- correctness code و synthetic invariance tests قابل تأیید هستند؛
- عدد واقعی `179.32%`، کیفیت مدل و independent test فقط پس از بازسازی data/model
  قابل تأییدند.
