# RESEARCH — استفاده از PyTorch یا FastAI برای مدل‌های Signal و Range

> **تاریخ:** 2026-08-26 · **وضعیت:** تحقیق — هنوز تصمیمِ معماری گرفته نشده
> **سؤال کاربر:** آیا می‌توانیم در ساخت مدل‌های سیگنال و رنج از PyTorch یا FastAI
> استفاده کنیم؟ اگر بله، آیا به دقت بالاتر کمک می‌کند؟
> **مبنای بررسی:** کد واقعی (`wavenet.py` · `wavenet_trainer.py` · `ports.py` ·
> `window_generator.py` · `dual_predictor.py` · requirements-ai.txt) + منابع TSC.

---

## ۱. جواب کوتاه

**بله، از نظر معماری و فنی کاملاً ممکن است** — و طراحی فعلیِ پروژه عمداً
این اجازه را داده است. اما دو نکتهٔ مهم:

1. **FastAI روی PyTorch ساخته شده** — «FastAI یا PyTorch» در واقع یک انتخاب
   است، نه دو انتخاب. FastAI یک لایهٔ high-level بالای torch است.
2. **فریمورک به‌خودی‌خود دقت را بالا نمی‌برد.** با معماری/دیتا/لیبل یکسان،
   نتیجهٔ TF و PyTorch از نظر آماری برابر است. دقت از چیزهای دیگری می‌آید
   (بخش ۳).

---

## ۲. چرا ممکن است؟ (شواهد از کد)

### معماری از قبل «فریمورک‌آگنوستیک» طراحی شده

- `domain/ai/ports.py` → پورت‌های انتزاعی `ModelTrainer` و `ModelPredictor`
  حتی ویژگی `framework` دارند («e.g. ``tensorflow``»). یک
  `PytorchWavenetTrainer` صرفاً یک **آداپتور جدید در infrastructure** است —
  نه redesign. با قاعدهٔ NO REDESIGN سازگار است.
- لایهٔ Domain (استراتژی، براکت، forecastها، پنجره‌ها) **صفر وابستگی به TF
  دارد**. زنجیرهٔ بکتست (`DualModelPredictionSource` → strategy → bracket)
  هیچ‌جا Keras صدا نمی‌زند.

### نقاط وابسته به TF (هزینهٔ واقعی مهاجرت)

TF/Keras فقط در **۸ فایل src** حضور دارد:

| فایل | وابستگی | سختی پورت به torch |
|---|---|---|
| `infrastructure/ai/wavenet/wavenet.py` | لایه‌های سفارشی `GatedActivationUnit`، `LastTimestep` | 🟢 آسان — WaveNet/TCN در torch کتاب‌درسی است؛ لایه‌ها فقط slicing/activation‌اند |
| `infrastructure/ai/wavenet/wavenet_trainer.py` | کل حلقهٔ آموزش (۱۰۰۰+ خط): folds، `tf.data`، callbacks، serialize `.keras` | 🟡 متوسط — `ReduceLROnPlateau`/`EarlyStopping`/`AdamW` همگی **native** در torch؛ serialize → `state_dict` (ساده‌تر از Keras!) |
| `infrastructure/ai/window_generator.py` | `tf.data.Dataset` استریم | 🟡 باید `DataLoader` معادل شود |
| `infrastructure/ai/dual_predictor.py` | `_load` → `tf.keras.models.load_model` + custom_objects | 🟡 باید بر اساس metadata فریمورک branch بخورد |
| `infrastructure/ai/model_diagram.py` · `training_progress.py` · `infrastructure/deployment/health_checks.py` · `presentation/commands/handlers.py` | فرعی | 🟢 |
| `ShadBotTrader_Colab.ipynb` | نصب TF | 🟢 |
| **۱۴ فایل تست** | TF را import می‌کنند (منشأ ۴۹ skip) | 🟡 |

### هزینهٔ پنهان: مدل‌های ذخیره‌شدهٔ فعلی

آرتیفکت‌های فعلی (`gold_signal_5m v1` · `gold_range_1d v1–v3`) فرمت `.keras`
هستند. هر مدل جدید torch **باید از صفر آموزش ببیند** — مدل‌های فعلی با آن
قابل استفاده نیستند (مگر از مسیر Keras-3-torch-backend، بخش ۴-الف).

### محیط اجرا

- **آموزش:** Colab GPU — هر دو فریمورک از قبل نصب‌اند. ✅
- **اجرای زنده (ویندوز/Alpari):** فقط inference روی CPU —
  `torch` CPU (~200MB) سبک نصب می‌شود؛ TF هم همین وضع را دارد. ✅
- ⚠️ دو استک DL همزمان (TF + torch) یعنی نصب سنگین‌تر و دو مسیر نگهداری —
  یا باید جایگزینی کامل باشد، یا موازی با پرچمِ فریمورک در metadata.

---

## ۳. آیا دقت بالاتر می‌رود؟ (جواب صادقانه و تفکیک‌شده)

### چیزی که فریمورک «نمی‌دهد»

معماری WaveNet فعلی در هر دو فریمورک **همان ریاضیات** است: causal conv +
gated activation + skip connections. با همان دیتا، همان لیبل، همان
hyperparameters، اختلاف دقت مورد انتظار ≈ نویز seed است، نه بیشتر.
**«با PyTorch دقیق‌تر می‌شویم» به‌خودی‌خود یک وعدهٔ غیرواقعی است.**

### چیزی که واقعاً می‌تواند دقت را بالا ببرد (و torch/FastAI بهش نزدیک‌تر می‌کند)

| اهرم | توضیح | ارتباط با torch/FastAI |
|---|---|---|
| **1. label smoothing** | در فاز ۵۷/۵۸ امتحان شد و با `SparseCategoricalCrossentropy` سازگار نبود و **حذف شد**. در torch، `CrossEntropyLoss(label_smoothing=…)` **native** است. | 🟢 مزیت مشخص torch |
| **2. معماری‌های جایگزین SOTA** | برای طبقه‌بندی سری زمانی، `InceptionTime` (آنسم ۵ شبکه) روی بنچمارک‌ها معمولاً از معماری‌های سفارشیِ تکی بهتر است. کتابخانهٔ **tsai** (ساخته‌شده روی fastai/torch) این‌ها را آماده دارد. | 🟢 بزرگ‌ترین پتانسیل واقعی برای مدل سیگنال |
| **3. حلقهٔ آزمایش سریع‌تر** | `lr_find` و `one_cycle` فست‌ای، کنترل کاملِ loop در torch، بدون دردسرهای serialize که چشیدیم (باگ‌های `_Seq2SeqMAE`/`_RangeLoss`). آزمایش بیشتر در واحد زمان → یافتن تنظیم بهتر. | 🟡 غیرمستقیم ولی واقعی |
| **4. تکنیک‌های سخت‌تر در Keras** | SWA، gradient accumulation، schedulerهای سفارشی، per-sample weighting — در torch چند خط است؛ در Keras یعنی callback سفارشی + ریسک serialize جدید. | 🟡 |
| **5. لیبل/فیچر/اعتبارسنجی بهتر** | آستانهٔ حرکت، افق، کیفیت ۲۲۷ فیچر، پروتکل walk-forward — **مهم‌ترین اهرم‌های دقت** و مستقل از فریمورک. | ⚪ هیچ — ولی اولویت اول است |

### زمینهٔ پروژه (مهم!)

مستندات خودمان (`IMPLEMENTATION_STATUS.md`) نتیجهٔ مهمی ثبت کرده:
روی دیتای نمونهٔ تصادفی، بهبود مدل بی‌معناست؛ و گلوگاه فعلی
`trades=0` در بکتست با مدل‌های واقعی است. یعنی **اول: آموزش درست دو مدل با
معماری فعلی روی دیتای واقعی MT5 + بکتست. بعد: جنگ دقت با اهرم‌های ۱–۵.**

---

## ۴. سه مسیر ممکن (از ارزان به گران)

### الف) مسیر ارزان — Keras 3 با بک‌اند PyTorch (نیم‌راه حاضر!)

`requirements` ما `tensorflow-cpu>=2.16` است که Keras 3 می‌آورد — و Keras 3
**بک‌اند PyTorch/JAX** دارد: `KERAS_BACKEND=torch`. لایه‌های سفارشی ما فقط
slicing/activation‌اند و با `keras.ops` قابل پورت به بک‌اند‌محور هستند؛
`AdamW`/`ReduceLR`/`EarlyStopping` از قبل Keras API هستند و بک‌اند‌محورند.
تنها قطعهٔ TF-خالص، `tf.data` استریم است که باید `DataLoader` شود.
⚠️ هنوز باید آزمایش شود؛ مزیتش: بدون تغییر فرمت آرتیفکت و بدون استک دوم.

### ب) مسیر میانه — آداپتور موازی PyTorch (سازگار با قوانین پروژه)

`PytorchWavenetTrainer(ModelTrainer)` با `framework="pytorch"` + پرچم فریمورک
در `ModelRecord` + branch در `_load` پیش‌بین‌ها. کد فعلی **دست نمی‌خورد**؛
مقایسهٔ علمی روی **همان walk-forward folds و همان metrics** انجام می‌شود و
هر کدام بهتر بود همان می‌ماند. هزینه: چند روز کار + نگهداری دو مسیر تا
تعیین برنده.

### ج) مسیر تجربی — tsai/FastAI برای مدل سیگنال

برای طبقه‌بندی BUY/SELL، آزمودن `InceptionTime`/`ResNet`/`FCN` از **tsai**
در کنار WaveNet فعلی (به‌عنوان candidate سوم، با پروتکل مقایسهٔ یکسان).
این مسیر **بیشترین پتانسیل افزایش دقت واقعی** را دارد چون معماری را عوض
می‌کند نه فقط فریمورک را. (درکمارِ InceptionTime به‌عنوان SOTA طبقه‌بندی
سری زمانی در مقالات ۲۰۲۰–۲۰۲۴ تکرار شده؛ tsai پیاده‌سازی fastai-محور آن است.)

---

## ۵. جمع‌بندی و پیشنهاد

1. **ممکن است؟ بله** — پورت‌ها از قبل برای این باز هستند؛ FastAI خودش torch است.
2. **دقت؟ فریمورک به‌تنهایی ≈ صفر اثر؛** ولی torch/tsai سه چیز ملموس می‌دهد:
   label smoothing native، معماری‌های SOTA آماده، حلقهٔ آزمایش سریع‌تر.
3. **ترتیب پیشنهادی:**
   - الان: آموزش دو مدل با کد فعلی روی دیتای واقعی + بکتست (`trades>0`) —
     گلوگاه فعلی فریمورک نیست.
   - بعد: اگر دقت سیگنال گلوگاه شد → مسیر ج (tsai/InceptionTime) به‌صورت
     آزمایش موازی با پروتکل مقایسهٔ عادلانه؛ مسیر الف به‌عنوان گزینهٔ ارزان
     برای آزادشدن از TF.
   - هر تصمیم باید همین‌جا به‌عنوان Decision ثبت شود (طبق قاعدهٔ پروژه).

---

## منابع

- کد: `src/ShadBotTrader/domain/ai/ports.py` · `infrastructure/ai/wavenet/*` ·
  `window_generator.py` · `dual_predictor.py` · `requirements-ai.txt`
- `docs/IMPLEMENTATION_STATUS.md` §«چرا بک‌تست ضرر می‌دهد» ·
  `docs/Report/SESSION_2026_08_26.md` (باگ label_smoothing)
- InceptionTime (Ismail Fawaz et al., 2020) — SOTA طبقه‌بندی سری زمانی؛
  مقایسه‌های ۲۰۲۴ (LITE، InceptionTime-vs-Wavelet) همچنان آن را در صدر می‌دانند.
