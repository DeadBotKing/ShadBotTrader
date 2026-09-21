# WORKLOG — دفترچهٔ کار

## 2026-09-07 — فاز ۱۰۹: threshold calibration و heatmap برای trend_signal

**درخواست اپراتور:** بعد از شروع train فاز ۱۰۸، فاز ۱۰۹ هم طبق roadmap اجرا شود تا
بعد از اتمام training بتوان thresholdهای BUY/SELL را کالیبره کرد.

**پیاده‌سازی:**
- `scripts/calibrate_trend_signal_thresholds.py` اضافه شد.
- grid برای `buy_threshold × sell_threshold` با `threshold_min/max/step` پیاده شد.
- decision rule با `min_margin` بین BUY/SELL/HOLD اضافه شد.
- metricهای grid: trades, buy/sell trades, precision, recall, action_f1, coverage,
  false_positive, ambiguous/no_trade.
- خروجی CSV/HTML/JSON در `run_logs/trend_signal_thresholds/` نوشته می‌شود.
- `ModelRecord` فیلد `decision_thresholds` گرفت؛ با `--save-record 1` threshold منتخب
  داخل `v*_training.json` ذخیره می‌شود.
- GUI command جدید اضافه شد: `Calibrate trend-signal thresholds` با action
  `calibrate_trend_signal`.

**تست‌ها:**
```text
tests/unit/ai/test_threshold_calibration.py
tests/integration/test_trend_signal_calibration_gui.py
→ passed
Targeted ruff/black روی فایل‌های تغییرکرده: OK
```

**محدودیت صریح:** این فاز فعلاً label/probability calibration است، نه full PnL
backtest با TP/SL. برای profit-aware calibration کامل باید thresholdها به triple
backtest وصل شوند.

**گام بعد:** بعد از اتمام training فعلی `gold_trend_signal_5m`، اپراتور خروجی
QUALITY را بفرستد و سپس command جدید calibration را اجرا کند.

## 2026-09-07 — فاز ۱۰۸: class weights + F1/PR-AUC برای trend_signal

**درخواست اپراتور:** بعد از audit واقعی Phase107، فاز بعدی طبق ترتیب پیشنهادی اجرا شود.
هدف فاز ۱۰۸ این بود که `trend_signal` فقط با accuracy قضاوت نشود و imbalance/fold
regime-shift با class weights و metricهای per-class دیده شود.

**پیاده‌سازی:**
- CLI جدید در `run_dual_models.py`: `--class-weight {auto,off}`.
- فقط برای `gold_trend_signal_*` حالت `auto` فعال می‌شود؛ سایر مدل‌ها historical
  unweighted باقی می‌مانند.
- `WavenetTrainer` برای هر roll-forward train fold وزن کلاس‌ها را فقط از همان train
  slice محاسبه می‌کند: `total / (num_classes * count_i)`.
- مسیر in-memory با `sample_weight=` به `model.fit` وصل شد؛ مسیر streamed با
  `tf.data.Dataset` سه‌تایی `(x,y,sample_weight)` کار می‌کند.
- metric callback اضافه شد و validation epoch-end این‌ها را به logs تزریق می‌کند:
  precision/recall/F1/AP برای SELL/HOLD/BUY، `val_macro_f1`, `val_weighted_f1`,
  `val_buy_sell_f1`, `val_balanced_accuracy` و probability mean/stdev per class.
- `run_dual_models.print_quality` این metricهای trend_signal را در QUALITY چاپ می‌کند.
- GUI فیلد جدید گرفت: `Trend-signal class weights = auto/off` در Train/Retrain/Optimise.

**تست/تأیید:**
```text
Targeted ruff/black روی فایل‌های تغییرکرده: OK
Targeted tests:
  test_classification_weights_metrics
  test_window_generator
  test_streamed_fold_progress
  test_phase108_trend_signal_training_config
  test_training_visibility
  test_architecture_knobs_gui
→ passed

python -m pytest -q
→ passed (full suite in this environment; TF tests skipped by existing markers)

full mypy src
→ همان 28 خطای pre-existing؛ خطای جدیدی باقی نماند
```
Smoke بدون TensorFlow روی TESTSYM نشان داد لاگ درست است:
`class wgt.: auto (balanced per roll-forward train fold)`.

**گام بعد:** اپراتور یک training واقعی `trend_signal` با `class_weight=auto` اجرا کند
و خروجی QUALITY را بفرستد؛ سپس Phase109 برای threshold calibration/heatmap اجرا می‌شود.

## 2026-09-07 — فاز ۱۰۷: audit کامل trend_signal + GUI command

**درخواست اپراتور:** اجرای فازهای پیشنهادی به ترتیب شروع شود، با تست دقیق، GUI،
مستندسازی و zip نهایی. اولین فاز ترتیب پیشنهادی، audit کامل `trend_signal_5m` بود.

**پیاده‌سازی:**
- `scripts/evaluate_trend_signal_5m.py` اضافه شد: بدون نیاز به TensorFlow، labelها،
  baselineها، fold geometry، feature matrix و اگر model artifact موجود باشد metricهای
  مدل را audit می‌کند.
- `TrendSignalLabels` در `target_builder.py` metadata گرفت: `ambiguous_count`,
  `warmup_skipped`, `partial_horizon_count`, `examined_count`, `barrier_price_dist`.
- GUI command جدید اضافه شد: `Audit trend-signal labels` با action
  `audit_trend_signal` و فیلدهای symbol/dataset/window/label_horizon/atr_mult/folds/val_size/model_id/max_windows.
- مسیر command از live log موجود استفاده می‌کند و script جدید را اجرا می‌کند.
- JSON خروجی audit در `run_logs/trend_signal_audit_latest.json` نوشته می‌شود.

**Smoke test واقعی روی دیتای تست موجود:**
```text
TESTSYM 5M, window=50, horizon=20, atr_mult=0.5
candles=500
labels=211 accepted from 211 examined starts
warmup skip=288
ambiguous=0
partial horizon=19 accepted labels
SELL=0, HOLD=211, BUY=0
majority baseline=100%, always-HOLD=100%
feature columns=179, labelled windows=211
```
این نشان داد audit imbalance شدید و near-tail partial horizon را درست گزارش می‌کند.

**تست‌ها:**
```text
python -m pytest tests/unit/ai/test_trend_signal_labels.py \
  tests/integration/test_trend_signal_audit.py \
  tests/unit/presentation/test_commands.py \
  tests/integration/test_gui_coverage.py -q
→ 66 passed

python -m pytest -q
→ passed (full suite in this environment; TF tests skipped by existing markers)
```

**Quality gate:**
- targeted `ruff`/`black --check` روی فایل‌های تغییرکرده سبز شد.
- full `ruff check .`, `black --check .`, `mypy src` همچنان به خطاهای قدیمی/pre-existing
  خارج از این فاز می‌خورند (ruff≈219، black≈21 فایل، mypy=28 خطا). این خطاها قبل از
  Phase107 هم وجود داشتند و در فایل‌های touched خطای ruff/black جدید نماند.

**اجرای واقعی اپراتور روی XAUUSD 5M:**
```text
candles=53,198 | labels=52,881 از 52,909 examined
SELL=21,130 (40.0%) | HOLD=12,715 (24.0%) | BUY=19,036 (36.0%)
majority baseline=40.0% | always-HOLD=24.0%
ambiguous=28 | warmup skip=288 | partial horizon accepted=287
first-hit median=104 bars | barrier median=$50.155
foldهای validation آخر: BUY-heavy (982/932/891) نسبت به SELL (424/627/640)
```

**رفع follow-up:** اجرای اپراتور هنگام scoring مدل ذخیره‌شده کرش کرد چون audit با
`window=288` اجرا شده بود ولی مدل ذخیره‌شده `gold_trend_signal_5m` ورودی
`(None, 150, 179)` می‌خواست. `score_model()` حالا قبل از `model.predict` هم window
و هم feature width را بررسی می‌کند و در mismatch، model scoring را graceful skip
می‌کند؛ label/fold audit همچنان معتبر می‌ماند.

**گام بعد:** اپراتور بعد از دریافت zip می‌تواند دوباره GUI audit را اجرا کند؛ دیگر
روی مدل قدیمی window=150 کرش نمی‌کند. سپس Phase108: class weights + F1/PR-AUC.

## 2026-09-07 — ثبت نهایی handoff و خردکردن roadmap در Docs/Phases

**درخواست اپراتور:** همهٔ پیشنهادهای استخراج‌شده از این چت به صورت چند فاز در
`docs/Phases` ثبت شود؛ هر کاری که در کل چت انجام شده دقیق و قابل فهم برای چت
جدید مستند شود؛ سپس پروژه zip شود.

**انجام‌شده:**
- برای فازهای انجام‌شدهٔ این جلسه فایل مستقل ساخته شد:
  `Phase100.md` تا `Phase106.md`.
- برای فازهای پیشنهادی آینده فایل مستقل ساخته شد:
  `Phase107.md` تا `Phase115.md`.
- index سریع ساخته شد:
  `docs/Phases/README_PHASE100_115.md`.
- handoff کامل جلسه ساخته شد:
  `docs/SESSION_HANDOFF_2026-09-07.md`.
- گزارش‌های review خارجی در `docs/Report` نگه داشته شدند:
  `PHASE105_LECI37_CODE_REVIEW_AND_ADOPTION_PLAN.md` و
  `PHASE106_ALPACA_ARI99_ONEPAGECODE_REVIEW_AND_SHADBOT_PLAN.md`.

**وضعیت اجرایی بعدی:** اگر اپراتور تأیید کند، اجرای واقعی باید از `Phase107` شروع
شود: audit کامل `trend_signal_5m`، بعد `Phase108` برای class weights + F1/PR-AUC.

**Quality/verification این بستهٔ مستنداتی:**
- `git diff --check` سبز شد.
- `python -m pytest -q` سبز شد.
- `ruff check .`، `black --check .` و `mypy src` همچنان به خطاهای قدیمی/pre-existing
  خارج از این تغییرات می‌خورند: ruff حدود 219 خطا، black حدود 22 فایل قدیمی، mypy
  همان 28 خطای شناخته‌شده. این مرحله code production را تغییر نداد؛ تغییرات اصلی
  مستندسازی و phase planning بود.

## 2026-09-07 — فاز ۱۰۶: بررسی Alpaca، ari99/algorithmic_trading و Onepagecode برای نقشهٔ تکامل مدل‌های event

**درخواست اپراتور:** سه منبع جدید دقیق بررسی شوند؛ اگر کدی لازم است وارد workspace شود؛
و اطلاعات لازم در Docs اضافه شود.

**انجام‌شده:**
- مقالهٔ Alpaca `tensorflow-market-forecasting` کامل بررسی شد: MLP دودسته‌ای با
  RSI/Stoch، target جهت روز بعد، train/eval chronological، overfit واضح، توصیه به
  normalized features، windows، neutral class و استفادهٔ ML فقط به‌عنوان indicator کمکی.
- repo `ari99/algorithmic_trading` موقتاً در workspace clone شد، commit `c8479f3`؛
  بعد از استخراج نکات برای خلوت‌کردن workspace حذف شد؛ کدهای data download، feature engineering، labels، RNN/LSTM،
  class weights، threshold grid، VectorBT backtest، random/Monte Carlo/White checks
  و Alpaca paper trading بررسی شدند.
- مقالهٔ Onepagecode/Substack بررسی شد؛ بخش public شامل Alpha Vantage fetch،
  MinMaxScaler train-only، MLP regression، MSE/relative error و CLI pipeline بود؛
  source download پشت paywall بود و قابل clone نبود.
- گزارش کامل نوشته شد:
  `docs/Report/PHASE106_ALPACA_ARI99_ONEPAGECODE_REVIEW_AND_SHADBOT_PLAN.md`.

**نتیجهٔ فنی:** هیچ‌کدام برای کپی مستقیم کد production مناسب نیستند؛ اما چند ایده
باید وارد roadmap شود: event/action targets، class weights + F1/PR-AUC، POS/NEG
binary models، feature selection train-only، threshold grid/backtest heatmap، random
baseline، Monte Carlo/White Reality significance، و دو-branch returns+features model.

## 2026-09-07 — فاز ۱۰۵: clone و بررسی کد پروژهٔ Leci37 برای استخراج الگوهای قابل استفاده

**درخواست اپراتور:** پروژهٔ `TensorFlow-stocks-prediction-Machine-learning-RealTime`
به workspace آورده شود، کد آن دقیق بررسی شود، و مشخص شود کدام feature/model/method
ها برای ShadBotTrader قابل استفاده‌اند و روند کامل تغییرات چیست.

**انجام‌شده:**
- repo موقتاً در workspace clone شد، commit `7520351`؛ بعد از استخراج نکات برای خلوت‌کردن workspace حذف شد.
- فایل‌های کلیدی بررسی شدند: `Utils_buy_sell_points.py`, `Feature_selection_create_json.py`,
  `Data_multidimension.py`, `Model_TF_definitions.py`, `Model_train_*`,
  `Model_predictions_*`, `Utils_scoring.py`, `5_predict_POOL_enque_Thread.py`,
  `features_W3_old/v3.py`, `README.md`.
- گزارش کامل نوشته شد:
  `docs/Report/PHASE105_LECI37_CODE_REVIEW_AND_ADOPTION_PLAN.md`.

**جمع‌بندی فنی:**
- ارزش اصلی پروژهٔ Leci37 برای ما کپی کد نیست؛ ایده‌های عملیاتی است:
  event-based GT، POS/NEG binary models، feature selection، class weighting،
  threshold calibration، model ensemble و profit-aware evaluation.
- کد direct-use نیست چون dependencyها قدیمی/سنگین‌اند، بخش‌هایی private/missing هستند،
  و خود README دربارهٔ indicators آینده‌نگر هشدار می‌دهد.
- مسیر پیشنهادی برای ShadBotTrader: تمرکز از `trend_score` regression به سمت
  `trend_signal`/event-classification + class weights/F1 + feature selection +
  consensus/profit-aware backtest.

## 2026-09-07 — فاز ۱۰۴: input scaling مخصوص trend_score به بازهٔ [-1,+1]

**درخواست اپراتور:** برای مدل score، نرمال‌سازی input به جای `[-2,+2]` در بازهٔ
`[-1,+1]` باشد؛ مدل range همان `[-2,+2]` را نگه دارد؛ و مطمئن شو همهٔ featureها
به‌خصوص قیمت‌های اصلی از این بازه بیرون نمی‌زنند.

**تغییرات:**
- `data_windowing.py`: ثابت‌های `DEFAULT_SCALE_RANGE=(-2,+2)` و
  `TREND_SCORE_SCALE_RANGE=(-1,+1)` اضافه شد؛ `minmax_scale_window` و سازنده‌های
  sample حالا `scale_range` می‌گیرند.
- `model_roles.py`: فیلد `input_scale_range` به `ModelRole` اضافه شد؛ همهٔ مدل‌ها
  پیش‌فرض `[-2,+2]` دارند ولی `trend_score_model_role()` صریحاً `[-1,+1]` دارد.
- `WavenetTrainer` و `WindowGenerator`: هم مسیر in-memory و هم streamed training
  scale range نقش مدل را مصرف می‌کنند؛ پس train واقعی score با `[-1,+1]` انجام
  می‌شود، نه فقط log.
- Inference/evaluation: مسیرهای `run_dual_models` sanity prediction، `/data`
  (`RangeForecastInspector` و `server.py`)، `ModelEvaluationService` و
  `evaluate_trend_score_1d.py` از scale range ذخیره‌شدهٔ model record استفاده
  می‌کنند. مدل‌های قدیمی که این فیلد را ندارند برای سازگاری `[-2,+2]` می‌مانند؛
  مدل‌های جدید score `[-1,+1]` را در record ذخیره می‌کنند.
- `ModelRecord`: فیلد `input_scale_range` اضافه شد و در `v*_training.json` ذخیره
  می‌شود. اگر checkpoint قدیمی با scale متفاوت برای resume انتخاب شود، resume
  رد می‌شود و آموزش از صفر شروع می‌شود تا وزن‌های `[-2,+2]` با input جدید
  `[-1,+1]` قاطی نشوند.
- `run_dual_models.py`: در سربرگ آموزش چاپ می‌کند:
  `input scale: minmax [-1, +1] per feature/window` و در شروع training برای score
  audit اول/آخر window را انجام می‌دهد که همهٔ featureهای scaled داخل بازه باشند
  و target column داخل input نباشد.

**تأیید عددی روی دیتای موجود سندباکس:**
```text
gold_trend_score_1d scale (-1.0, 1.0) shape (150, 182) min -1.0 max 1.0 target_col_excluded True
gold_range_1d       scale (-2.0, 2.0) shape (150, 182) min -2.0 max 2.0 target_col_excluded True
```
یعنی قیمت‌های اصلی و تمام featureهای پنجرهٔ score بعد از scaling داخل `[-1,+1]`
هستند و ستون target از input حذف شده است.

**تست/کیفیت:**
- targeted ruff/black روی فایل‌های تغییرکرده: سبز.
- targeted tests: `test_data_windowing`, `test_window_generator`, `test_dual_models`,
  `test_range_atr_wiring`, `test_evaluate_and_inspect`, `test_model_selection` سبز.
- full pytest محیط فعلی سبز شد.
- گیت کامل همچنان همان خطاهای pre-existing خارج از این فاز را دارد:
  `ruff check .` = 219 خطای قدیمی، `black --check .` = 22 فایل قدیمی، `mypy src` =
  28 خطای قدیمی. خطای mypy جدیدی باقی نماند.

## 2026-09-07 — فاز ۱۰۳: ممیزی نرمال‌سازی/تارگت trend_score و حذف لیبل جعلی tail

**درخواست اپراتور:** چون loss آموزش trend_score مثل مدل قوی رفتار نمی‌کرد،
محاسبات score و نرمال‌سازی بررسی شود.

**نتیجهٔ ممیزی با کد واقعی:**
- محاسبهٔ score درست است: برای row با original index=t، تارگت برابر score کندل
  واقعی `t+1` است:
  `score = (close[t+1] - open[t+1]) / (high[t+1] - low[t+1])`.
- مقادیر target finite و در بازهٔ `[-1,+1]` هستند.
- input windowها فقط featureها را دارند؛ ستون target از ورودی حذف می‌شود.
- feature normalization درست انجام می‌شود: هر ستون هر window جداگانه به بازهٔ
  `[-2,+2]` min-max می‌شود؛ target scale نمی‌شود چون خودش dimensionless است.
- یک باگ کوچک ولی واقعی پیدا شد: در مسیر `trend_score`، آخرین ردیف‌هایی که آینده
  ندارند با `0.0` پر می‌شدند، نه اینکه مثل range با `attach_targets` حذف شوند.
  این یعنی جدیدترین پنجرهٔ آموزشی می‌توانست یک score خنثی جعلی داشته باشد.

**تغییر:**
- `DualModelService.prepare()` برای `gold_trend_score_*` حالا targets را با
  `ts.source_index` به `attach_targets` می‌دهد؛ tail بدون لیبل حذف می‌شود، نه
  صفرسازی.
- شاخهٔ duplicate تاریخی trend_score هم همان اصلاح را گرفت تا رفتار آینده یکسان
  بماند.
- تست regression اضافه شد: `test_trend_score_drops_the_final_unlabelled_candle`.

**تأیید عددی روی دیتای موجود سندباکس:**
- بعد از fix: `candles=2513`, `rows=2295`, آخرین target = `-0.3608903` که score
  کندل واقعی آخر است؛ دیگر fake `0.0` برای tail وجود ندارد.
- `finite=True`, target range=`[-1,+1]`.
- full pytest محیط فعلی سبز شد؛ ruff/black روی فایل‌های touched سبز است. گیت کامل
  ruff/black/mypy همچنان همان خطاهای pre-existing خارج از این تغییر را دارد.

**محدودیت تفسیر:** این باگ فقط یک/چند ردیف tail را آلوده می‌کرد و توضیح اصلی
ضعف trend_score نیست. علت اصلی همچنان نویزی بودن direction/score یک‌روزهٔ طلاست،
اما از این به بعد تارگت از نظر integrity تمیزتر است.

## 2026-09-07 — فاز ۱۰۲: گزینهٔ MAE برای trend_score + انتخاب epoch بر اساس val_mae

**درخواست اپراتور:** چون در آموزش `gold_trend_score_1d` مقدار `val_mae` مهم‌ترین
عدد بود و کم‌شدن/نشدنش معیار واقعی محسوب می‌شد، آموزش و بهینه‌سازی روی MAE
امکان‌پذیر شود؛ بدون دست‌زدن به مدل‌های range که با loss ترکیبی فعلی بهتر جواب
داده‌اند.

**تغییرات (بدون redesign):**
- `scripts/run_dual_models.py`:
  - فلگ جدید `--trend-score-loss {composite,mae}` اضافه شد.
  - حالت پیش‌فرض `composite` همان loss فعلی است: `3*Huber + 6*MAE + 1*MSE`.
  - حالت `mae` فقط برای `gold_trend_score_*` فعال می‌شود؛ سایر مدل‌ها این فلگ را
    نادیده می‌گیرند.
  - monitor خودکار برای `trend_score` از این به بعد `val_mae` است؛ یعنی
    checkpoint، EarlyStopping و ReduceLR همان عددی را کمینه می‌کنند که برای score
    معیار قضاوت است.
  - لاگ شروع آموزش حالا `objective` و `monitor` را صریح چاپ می‌کند.
- `WavenetTrainer`: `monitor_metric` به callbacks اضافه شد؛ برای MAE خالص در
  seq2seq، همان تمرکز 40٪ کل sequence + 60٪ آخرین timestep حفظ شد تا خروجی مصرفی
  forecast بهینه شود.
- `DualModelService`: `loss_name` و `monitor_metric` به قرارداد train/build_trainer
  اضافه شد و در hyperparameters مدل ذخیره می‌شود.
- GUI:
  - فیلد `Trend-score loss` به Train / Retrain / Find best learning rate اضافه شد.
  - فقط وقتی model=`trend_score` باشد `--trend-score-loss` به اسکریپت پاس داده
    می‌شود؛ range/signal/trend دست‌نخورده می‌مانند.
  - مسیر optimise برای `trend_score` هم dataset را درست به `--signal-timeframe`
    پاس می‌دهد و LR sweep را با `val_mae` انتخاب می‌کند.

**نحوهٔ استفاده:**
```bash
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend_score --signal-timeframe 1D \
  --epochs 50 --folds 3 --window 150 \
  --learning-rate 0.0008 --trend-score-loss mae \
  --storage-root datasets
```
در GUI: `Train a model` → `model=trend_score` → `dataset=1D` →
`Trend-score loss=mae`.

**تأیید:**
- اجرای dry-run بدون TensorFlow تا مرحله آماده‌سازی نشان داد لاگ درست است:
  `objective: mae` و `monitor: val_mae (minimize)`.
- targeted tests سبز:
  `tests/unit/presentation/test_architecture_knobs_gui.py`,
  `tests/integration/test_training_visibility.py`,
  `tests/unit/ai/test_training_progress.py`, `tests/unit/ai/test_wavenet.py`.
- کل pytest محیط فعلی سبز شد (تست‌های TensorFlow طبق مارکرهای موجود skip شدند).
- ruff/black روی فایل‌های تغییرکرده سبز است.
- گیت کامل همچنان خطاهای pre-existing خارج از این فاز دارد: `ruff check .` = 239
  خطا (notebook/فایل‌های قدیمی)، `black --check .` = 24 فایل قدیمی، `mypy src` =
  همان 28 خطای قدیمی. این فاز خطای جدیدی روی فایل‌های touched اضافه نکرد.

## 2026-09-07 — فاز ۱۰۱: رفع لاگ زندهٔ آموزش در GUI ویندوز

**درخواست اپراتور:** آموزش از داخل GUI مثل قبل شروع شود و لاگ زنده واقعاً چاپ شود؛
اجرای مستقیم PowerShell با `python -u` خروجی داشت ولی پنل لاگ GUI خالی می‌ماند.

**عیب‌یابی (کد = واقعیت):** مسیر Train a model از
`CommandBus.dispatch_async → AccountCommandHandlers.train_dual_models → _run_script`
می‌گذرد. دو نقطهٔ شکننده پیدا شد:
- race در `dispatch_async`: صفحه بعد از POST بلافاصله redirect می‌شد، اما `_running`
  فقط داخل thread پس‌زمینه set می‌شد؛ اگر GET بعد از redirect زودتر می‌رسید،
  dashboard اصلاً بنر live-log را رندر نمی‌کرد.
- Windows pipe decoding/reading: child process متن فارسی و علامت‌های UTF-8
  (`—`, `−`, `·`) چاپ می‌کند؛ parent با `text=True` بدون `encoding` ممکن بود با
  codepage ویندوز decode کند و reader قبل از epoch اول قطع شود. علاوه بر آن،
  نگه‌داشتن write handle فایل لاگ در تمام زمان آموزش روی Windows می‌تواند خواندن
  همزمان `/api/log` را flaky کند.

**تغییرات:**
- `presentation/commands/bus.py`: رزرو synchronous وضعیت busy قبل از برگشت
  `dispatch_async`؛ thread دیگر `dispatch()` را دوباره صدا نمی‌زند، بلکه handler
  رزروشده را اجرا و history/running state را در یک مسیر مشترک جمع می‌کند.
- `presentation/commands/handlers.py`: `_run_script` حالا child را با `python -u`
  اجرا می‌کند، `PYTHONUNBUFFERED=1`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`
  می‌گذارد، pipe را صریحاً با `encoding="utf-8", errors="replace"` می‌خواند، و
  فایل live log را با appendهای کوتاه باز/بسته می‌کند تا `/api/log` بتواند وسط
  آموزش روی Windows بخواند.
- `run_dual_models.py`: لاگ نمایشی trend_score اصلاح شد؛ دیگر `training: nothing`
  و `RANGE MODEL` برای score چاپ نمی‌شود و واحد تارگت score به‌صورت
  dimensionless `−1..+1` چاپ می‌شود.
- تست‌ها: پوشش race فوری `dispatch_async` و الزام UTF-8/unbuffered برای stream
  داشبورد اضافه شد.

**تأیید:**
- اجرای مستقیم اسکریپت trend_score بدون TensorFlow تا مرحلهٔ آماده‌سازی تأیید کرد
  که سربرگ اکنون `training: trend_score(1D)` و `TREND_SCORE MODEL` چاپ می‌کند.
- targeted tests: `tests/unit/presentation/test_commands.py` و
  `tests/integration/test_training_visibility.py` سبز شدند.
- کل pytest محیط فعلی سبز شد (TensorFlow در سندباکس نصب نیست، پس تست‌های AI وابسته
  به TF طبق مارکرهای موجود skip شدند).
- ruff/black روی فایل‌های تغییرکرده سبز است.
- گیت کامل lint/type محیط فعلی هنوز خطاهای pre-existing و خارج از این فیکس دارد
  (ruff/black روی notebook/فایل‌های قدیمی و mypy روی چند فایل قدیمی)؛ این فیکس
  خطای جدیدی در فایل‌های touched اضافه نکرد.

## 2026-09-06 — فاز ۱۰۰: trend_score روی کندل واقعی 1D + آموزش v1 روی 10 سال دیتای واقعی

**درخواست اپراتور:** «مدل رو بساز اول — ما باید اول ی تخمین درست‌حسابی از روند
آینده بدست بیاریم» → اجرای پروپوزال مصوب `TREND_SCORE_1D_PROPOSAL.md`.

**سیم‌کشی (بدون redesign — reuse کامل پایپ‌لاین رنج):**
- `run_dual_models.py`: `--label-horizon` پیش‌فرض 0=خودکار — trend_score روی 1D
  → **1** (score از کندل واقعی فردا)، بقیه → 288. متن قانون برچسب تطبیقی.
- **رفع باگ sanity prediction:** trend_score (name="range") وارد مسیر
  RangePredictor (۲ کانال) می‌شد و روی خروجی تک‌کاناله کرش می‌کرد — شاخهٔ
  اختصاصی score اضافه شد.
- `model_roles.py`: توضیح تطبیقی horizon=1 → «NEXT REAL {tf} candle».
- `target_builder.py`: مستندسازی حالت کندل واقعی (horizon=1).
- `handlers.py`: فیلد GUI horizon خالی/0 = خودکار + hintهای سه فرم.
- `wavenet_trainer.py`: `SHADBOT_STREAM_THRESHOLD_BYTES` — override آستانهٔ
  stream برای ماشین کم‌رم (پیش‌فرض 512MB دست‌نخورده). در سندباکس 1GB بدون
  این، متریالایز X=250MB → OOM/137.
- `print_quality`: پیام QUALITY مخصوص score (واحد −1..+1، نه USD per bound)
  + hint مخصوص score در حالت بدون لبه.
- جدید: `scripts/fetch_1d_gold_yahoo.py`، `scripts/evaluate_trend_score_1d.py`.

**دیتا:** Yahoo GC=F (فیوچرز COMEX — نزدیک‌ترین سری آزاد به spot) —
2,513 کندل روزانه 2016-09-06..2026-09-04 → `XAUUSD/1D/v1.parquet`.
شفاف: فیوچرز است نه spot بروکر؛ اپراتور با MT5 بازآموزی می‌کند.

**آموزش + حکم صادقانه:**
- `gold_trend_score_1d v1` (150×1D، 182 فیچر، seq2seq tanh، ۲ فولد):
  val_mae فریز ~0.59 vs baseline 0.5705؛ ارزیابی کامل: skill −0.2%،
  پیش‌بینی ثابت → **بدون لبه** — دقیقاً انتظار مستند پروپوزال. حالا با عدد.
- `gold_trend_1d v1` (رنگ کندل — لبهٔ اثبات‌شدهٔ اپراتور): kept epoch 12 →
  val_acc **55.7%** vs baseline 54.3% (+1.4pp)؛ اوج گذرا 57.7-59.4%؛
  overfit بعد از ~epoch 12. سازگار با +3.8% خود اپراتور.
- پیش‌بینی زنده برای 2026-09-07: score +0.0008 (بی‌رون) | رنگ: sell 50.8% (غیرقابل‌اقدام).
- مسیر `/data` (inspector.forecast_at) با هر دو آرتیفکت تأیید شد.

**تست/کیفیت:** ruff/black/mypy (همان ۹ خطای pre-existing TF) · کل suite
سبز جز ۲ خطای env-dependent مستندشدهٔ `test_threshold_recorded` (روی HEAD هم هست).

```
تست‌ها: 1452+ passed · 2 failed (env-dependent مستند) · skipped
```

**گام بعد:** بازآموزی روی MT5 توسط اپراتور · فیچر رژیم‌محور برای score
(DOW/vol-regime — پروپوزال جدا) · مجوز ۵/۶ در بکتست تریپل · بازآموزی
trend_signal_5m با مانع روزانه.


## 2026-08-26 — گزارش جداگانهٔ تعادل لیبل train/validation در شروع آموزش

**درخواست کاربر:** اولِ لاگِ آموزش برای دیتای آموزش و دیتای اعتبارسنجی جدا بنویس
چند لیبل BUY و چند لیبل SELL دارد.

**مشکل:** فقط یک خط `label balance` با تعادلِ کلِ دیتاست چاپ می‌شد؛ معلوم نبود
کدام تعادل به train و کدام به validation تعلق دارد.

**تغییر (`scripts/run_dual_models.py`):**
- تابع `signal_label_split_balance(dataset, role, max_folds)` اضافه شد:
  لیبل هر نمونهٔ مدل سیگنال را از ستون هدفِ `sample_ends` می‌خواند، همان هندسهٔ
  expanding roll-forward که trainer استفاده می‌کند را بازسازی می‌کند، و تعادل
  BUY/SELL **آخرین فولد** (همان که مدل نهایی از آن ساخته می‌شود) را جدا
  برمی‌گرداند.
- در `train_one` بعد از `label balance` دو خط جدید چاپ می‌شود:
  ```
  label balance  : {'sell': 3524, 'buy': 3568}   ← کل
  train labels   : {'sell': 2867, 'buy': 2902}   ← تعادلِ train (آخرین فولد)
  val labels     : {'sell': ..., 'buy': ...}     ← تعادلِ validation (آخرین فولد)
  ```
- برای مدل range (رگرسیون) خط جدید چاپ نمی‌شود چون لیبل BUY/SELL ندارد.

**تست:** `tests/unit/ai/test_signal_label_split.py` (۳ تست) اضافه شد.

```
قبل:  1449 passed · 0 failed · 49 skipped
بعد:  1452 passed · 0 failed · 49 skipped
```

---

## 2026-08-26 — رفع ۲۹ تستِ کهنه → گیت تست سبز (1449 passed, 0 failed)

**مشکل:** کد در فازهای ۵۲–۵۸ جلو رفته بود ولی تست‌ها عقب مانده بودند؛ ۲۹ تست شکست
می‌خوردند (همه «تستِ کهنه»، نه باگِ واقعی). در ممیزیِ `STATUS_AUDIT_2026-08-26` ثبت شد.

**روش:** تست‌ها را با رفتارِ **عمدیِ جدیدِ** کد هماهنگ کردم (نه تضعیف، نه حذف ضمانت).

### دسته‌بندی و اصلاحات
| علت شکست | فایل(ها) | اصلاح |
|---|---|---|
| فیچرها ۱۰۹ → ۲۲۷ | `test_feature_cache`, `test_feature_pipeline`, `test_feature_visibility`, `test_stored_matrix_identity`, `test_training_dataset`, `test_invariance_audit`, `test_commands`, `test_evaluate_and_inspect` | اعداد 109→227، width 123→241، causal 70→177/188 |
| Range 1H → 1D | `test_dual_models` | timeframe 1H→1D، horizon 5→1، نام ستون seq2seq `_1` |
| گیت R/R به Bracket منتقل شد | `test_dual_model_strategy`, `test_live_decision` | تست را با طراحی جدید هماهنگ کردم + **تست واحد جدید** در `tests/unit/simulation/test_bracket.py` که ردِ R/R ضعیف در `TradeBracket` را تضمین می‌کند |
| فرمت progress تغییر کرد (فاز ۵۲/۵۳) | `test_training_progress`, `test_progress_visibility`, `test_training_visibility`, `test_training_pace` | هماهنگ با خروجی جدید (`key=value`، `epoch   1/2`، ۳ خط batch، ETA در checkpoint) |

### نتیجه
```
قبل:  1415 passed · 29 failed · 49 skipped
بعد:  1449 passed ·  0 failed · 49 skipped   (49 skip = تست‌های TensorFlow)
ruff:  All checks passed!   |   black: clean
```

### فایل جدید
- `tests/unit/simulation/test_bracket.py` — تست‌های براکت TP/SL (ر/ر، اسپرد، same-bar policy).

---

## 2026-08-26 — همگام‌سازی مستندات: ثبت فازهای ۵۰–۵۸ (که قبلاً فقط در گزارش‌ها/کد بودند)

**خلأ:** کد در فاز ۵۸ بود ولی `WORKLOG` فقط تا فاز ۴۹ داشت؛ فازهای ۵۰–۵۶ فقط
در `docs/Report/PHASE50..56` بودند و فازهای ۵۷–۵۸ فقط در کامنت‌های کد. این
ورودی آن‌ها را یکجا ثبت می‌کند تا وضعیت از روی «کد + گیت + مستندات» قابل بازیابی
باشد (مطابق `AGENTOPERATINGRULE`). جزئیات کامل در `docs/STATUS_AUDIT_2026-08-26.md`.

### فازهای ۵۰–۵۶ (تاریخ 2026-08-25) — خلاصه
| فاز | کار |
|---|---|
| ۵۰ | تحلیل range v1 (val_mae→دلار) + رفع باگ `loss_function` در `save_model`؛ سلول‌های Colab برای بررسی/ادامهٔ آموزش |
| ۵۱ | `--resume` — ادامهٔ آموزش از checkpoint بعد از قطعی Colab/اینترنت (warm-start آخرین fold) |
| ۵۲ | فیلتر Session (ساعت‌های خوب UTC) + حداقل فاصلهٔ SL — WR از ۳۳.۵٪ به ~۵۵٪ |
| ۵۳ | بهبود Progress Reporter (نمایش val_mae و معادل دلاری، جداسازی range/signal) |
| ۵۴ | Loss سه‌گانه Huber+MAE+MSE + AdamW + ReduceLROnPlateau (برگرفته از legacy) |
| ۵۵ | **Range Model Seq2Seq** `[batch, window, horizon*2]` برای رفع collapse |
| ۵۶ | **Range: horizon=1 روی 1D** (پیش‌بینی high/low فردا) + سیگنال 5M |

گزارش‌ها: `docs/Report/PHASE50..56_REPORT.md`.

### فاز ۵۷ — پایداری بکتست + ورود واقع‌بینانه (ثبت‌شده اینجا برای اولین بار)
- **گسترش SL به‌اندازهٔ اسپرد** در `bracket.py` (`spread` در `from_model_levels`) تا اسپرد باعث توقف زودهنگام ضرر نشود.
- عبور `spread`/`spread_pct` در `dual_model_prediction_source` و `dual_model_backtest_service`.
- **ورود با typical price** `(O+H+L+C)/4` به‌جای open تنها در `backtest_engine.py`.
- **EarlyStopping** + **ReduceLROnPlateau** برای هر دو مدل.
- **Resume از همهٔ foldها** (همه warm-start) در `wavenet_trainer.py`.
- **AdamW برای هر دو regression و classification** (weight_decay متفاوت).

### فاز ۵۸ — معماری Signal (ثبت‌شده اینجا برای اولین بار)
- مدل سیگنال: `window=300` (۲۵ ساعت)، `n_layers_per_block=5`, `n_blocks=2` → RF=249 ≈ ۸۳٪.

### یافتهٔ مهم ممیزی
- کد ۳۱۶ ماژول سالم import می‌شود؛ **۲۹ تست شکسته‌اند ولی همه تستِ کهنه‌اند** (با
  تغییرات عمدیِ فازهای ۵۲–۵۸ همگام نشده‌اند)، نه باگ واقعی.
- **کاتالوگ فیچر از ۱۰۹ به ۲۲۷** گسترش یافته (مدیریت با `model_scope`؛ range≈182، signal≈177).
- GUI (`handlers.py`) با فازهای جدید هماهنگ است؛ فقط `scripts/run_backtest.py` هنوز
  پیش‌فرض `1H`/`gold_range_1h` دارد (کهنه).
- `project_state/generated/*` کهنه است (تا فاز ۵۰).

---

## 2026-08-20 — جست‌وجوی خودکار Learning Rate در داشبورد

دکمهٔ `Find best learning rate` اضافه شد. برای Signal معیار انتخاب `val_loss` و برای Range معیار `val_mae` است. چند candidate روی pilot walk-forward اجرا می‌شوند، بهترین مقدار انتخاب می‌شود و سپس مدل نهایی با همان Learning Rate آموزش و ذخیره می‌شود. هیچ script جدیدی اضافه نشده و از `run_dual_models.py` موجود استفاده می‌شود.


## 2026-08-19 — Signal binary: فقط BUY / SELL

مدل سیگنال از سه‌کلاسهٔ `SELL/HOLD/BUY` به طبقه‌بندی binary تغییر کرد. خروجی شبکه و labelها فقط `SELL` و `BUY` هستند؛ threshold آموزش، اولین barrier قیمتی مثبت/منفی را تعیین می‌کند و جست‌وجو تا رسیدن به barrier ادامه دارد. اگر probability از آستانهٔ بک‌تست پایین‌تر باشد، strategy تصمیم `no_trade/HOLD` می‌سازد؛ این تصمیم مدل نیست. مدل‌های قدیمی سه‌خروجی باید دوباره آموزش داده شوند.


## 2026-08-19 — بک‌تست دومدلی سیگنال → رنج → TP/SL

درخواست کاربر برای بک‌تست causal پیاده شد:

- مدل signal روی 5M، با پنجره و horizon قابل‌خواندن از training metadata؛
- آستانهٔ احتمال BUY/SELL قابل تنظیم، با HOLD واقعی و بدون فراخوانی مدل range؛
- مدل range روی 1H فقط بعد از عبور signal از آستانه؛
- تعیین TP/SL از high/low پیش‌بینی‌شده؛ BUY = high/low و SELL = low/high؛
- ورود پیش‌فرض روی open کندل 5M بعدی؛
- خروج candle-by-candle، با قانون پیش‌فرض stop-first برای لمس هم‌زمان؛
- نادیده‌گرفتن سیگنال‌های جدید تا بسته‌شدن bracket؛
- گزارش جداگانهٔ تعداد take-profit و stop-loss؛
- ماتریس feature هر تایم‌فریم یک بار ساخته و برای roll-forward slice می‌شود.

مسیرهای اصلی: `dual_model_backtest_service.py`، `dual_model_prediction_source.py`، `domain/simulation/bracket.py` و `docs/DUAL_MODEL_BACKTEST.md`.


**هدف:** هر تغییر معنادار اینجا ثبت می‌شود تا اگر گفت‌وگو عوض شد، ایجنت دیگری
آمد، یا چند هفته بعد برگشتیم، بشود ادامه داد.

قاعدهٔ ثبت (طبق `AGENTOPERATINGRULE.md` § CHAT HANDOFF RULE): پروژه باید فقط
از روی «کد + گیت + مستندات وضعیت» قابل بازیابی باشد.

**فرمت هر ورودی:** تاریخ · چه شد · چرا · کجا · تست · وضعیت گیت

---

## 2026-08-18 — فاز ۴۹: آستانه با مدل سفر می‌کند

**درخواست کاربر:** «باشه ترشولد رو اعمال کن»

**مشکل:** `ModelEvaluationService._score_signal` لیبل‌ها را با
`threshold = 0.0008` ثابت می‌ساخت. مدلی که با ۰.۲۵٪ آموزش دیده بود با کلید
سؤالِ ۰.۰۸٪ تصحیح می‌شد؛ روی دیتای واقعی ۵ دقیقه‌ای سهم HOLD بین این دو
آستانه از ۴۱٪ به ۸۳٪ می‌رود، پس دقت به‌شدت کمتر از واقع گزارش می‌شد.

### تغییرات

| فایل | چه شد |
|---|---|
| `infrastructure/ai/model_catalogue.py` | `ModelRecord.threshold` + `.horizon` + `threshold_percent` |
| `scripts/run_dual_models.py` | هر دو مسیر ذخیره (چک‌پوینت epoch و ذخیرهٔ نهایی) آستانه را می‌نویسند |
| `application/services/model_evaluation_service.py` | آستانه از رکورد خوانده می‌شود؛ `DEFAULT_THRESHOLD` فقط برای مدل‌های قدیمی و با اعلام `ASSUMED` |
| `presentation/commands/handlers.py` | فیلد `threshold_pct` در Retrain خالی شد؛ خالی = ارث‌بری از خود مدل |
| `tests/integration/test_threshold_recorded.py` | ۱۷ تست جدید، از جمله یک تست `ast` که برگشت hard-code را می‌گیرد |
| `tests/integration/test_best_model_kept.py` | استاب `Role` فیلد `target` گرفت (باگ `AttributeError` که همین‌جا پیدا شد) |

**تست:** ۱٬۴۵۸ passed · ۱۲ skipped. Quality gate کامل سبز، شامل هر سه بخش
`RUN_TF=1`.

**اجرای واقعی:** آموزش signal روی `TESTSYM` 1H با آستانهٔ ۰.۲۵٪ →
`v1_training.json` حاوی `"threshold": 0.0025` → ارزیابی همان ۰.۲۵٪ را
گزارش کرد.

**گزارش:** `PHASE49_REPORT.md`

---

## 2026-08-16 — Backtest Replay (پخش زندهٔ کندل و معاملات)

**درخواست کاربر:** «اجرای بک تست رو میتونی یکاری کنی که به صورت لایو کندلا
نمایش داده بشن و نشون بده کجاها معامله کرده و نتیجه معامله چی بود؟»

**مجوز معماری:** فاز ۱۶ §۲۳ صراحتاً می‌گوید شبیه‌سازی باید step-by-step قابل
بازرسی باشد؛ فاز ۱۹ §۸ نقش View را «فقط رندر» تعریف می‌کند. پس این کار داخل
معماری منجمد است، نه تغییر آن.

### ساخته شد

| فایل | نقش |
|---|---|
| `domain/simulation/replay.py` | `TradeMarker`, `ReplayBar`, `ReplayTape`, `ReplayRecorder` |
| `infrastructure/simulation/console_replay.py` | `ConsoleReplayPlayer`, `summarise_tape` |
| `presentation/web/replay_renderer.py` | پخش‌کنندهٔ HTML مستقل (canvas + JS درون‌خطی) |
| `scripts/run_replay.py` | اسکریپت دمو |
| `tests/unit/simulation/test_replay.py` | ۱۲ تست |
| `tests/integration/test_backtest_replay.py` | ۱۶ تست |

### تغییر کرد

- `infrastructure/simulation/backtest_engine.py` — پارامتر `record_replay`، پراپرتی `tape`،
  و `_capture_trade` حالا `(realized_delta, fee_delta)` برمی‌گرداند
- `application/services/backtest_service.py` — عبور `record_replay`
- `backtest_cli.py` — دستور `replay`
- `presentation/commands/` — `CommandKind.RECORD_REPLAY` + هندلر
- `presentation/web/server.py` — مسیر `GET /replay`
- `presentation/web/renderer.py` — لینک ریپلی در هدر
- `dashboard_cli.py` — آپشن `--replay`
- `project/builders/{snapshot,context}_builder.py` — فاز جاری و فاز بعدی

### دو تصمیم طراحی که باید یادت بماند

1. **ورودِ باز نتیجه ندارد:** `realized_pnl` یک entry برابر `None` است نه صفر.
   صفر یعنی «سربه‌سر بست» که دروغ است.
2. **پوزیشن باز در پایان دیتا معامله شمرده نمی‌شود.** جدا با عنوان
   «Still open at the end» گزارش می‌شود.
3. **ضبط، ناظر منفعل است:** پیش‌فرض خاموش تا sweep هزینه ندهد. تستی هست که
   ثابت می‌کند نتیجهٔ اجرا با و بدون ضبط یکسان است.

### تأیید

- خروجی ریپلی دقیقاً با `run_backtest.py` یکی است: ۵۱ معامله، `-2.7946`
- هر دو اسکریپت دو بار اجرا شدند → خروجی بایت‌به‌بایت یکسان
- دکمهٔ داشبورد به‌صورت زنده تست شد (POST /run → ۳۰۰ بار ضبط شد)
- `672 passed, 6 skipped` · `RUN_TF=1 → 678 passed`

**گزارش کامل:** `REPLAY_REPORT.md`

---

## 2026-08-16 — ممیزی مستندات و ساخت اسناد وضعیت

**درخواست کاربر:** «طبق نقشه هم داریم پیش میریم دیگ؟ / فایلای docs رو یادت
نره ک همشوباید پیاده سازی کنیما / هرکاری هم ک میکنی توی docs ثبت کن»

**انجام شد:**
- خواندن `docs/AGENTOPERATINGRULE.md` (قبلاً در جریان کار خوانده نشده بود)
- ممیزی فاز ۱ تا ۲۸ در برابر کد واقعی
- ساخت `docs/IMPLEMENTATION_STATUS.md` — جدول وضعیت هر ۲۸ فاز
- ساخت `docs/WORKLOG.md` — همین فایل

**یافتهٔ مهم ممیزی:** ۲۲ فاز از ۲۸ کامل‌اند. سه فاز حداقلی‌اند (۹ Plugin،
۲۱ Config، ۲۲ Logging)، یکی صفر است (۲۴ Deployment)، یکی جزئی (۲۵ PowerShell)،
و فاز ۲۸ در حال انجام است. فاز ۲۰ با انحراف تأییدشده (SQLite) کامل است.

**نکتهٔ صادقانه:** `docs/PROJECT_STATE.md` و `docs/CURRENT_STATE.md` اسناد
اصلی و منجمد معماری‌اند و می‌گویند «هنوز چیزی پیاده نشده» — که دیگر درست
نیست. به‌جای دستکاری آنها (که خلاف قاعدهٔ freeze فاز ۲۶ است)،
`IMPLEMENTATION_STATUS.md` به‌عنوان لایهٔ وضعیت زنده اضافه شد و از هر دو به
آن ارجاع داده شد.

---

## 2026-08-16 — آماده‌سازی دیتای واقعی MT5 (گزینهٔ C)

**درخواست کاربر:** «باشه بریم» (تأیید قدم C).

### 🐞 باگ #۱۴ — دکمهٔ «Update features» داشبورد هرگز کار نمی‌کرد

**شدت: بالا.** حین تست مسیر واقعی کشف شد.

`presentation/commands/handlers.py::compute_features` این‌ها را صدا می‌زد:

| صدا زده می‌شد | واقعیت |
|---|---|
| `service.compute(symbol, timeframe)` | متد وجود ندارد → `compute_set(...)` |
| `outcome.results` | `outcome.outcomes` |
| `result.definition` | وجود ندارد؛ تعاریف از `feature_set.definitions` |
| `outcome.feature_set.name` | `outcome.set_name` |

**پیام خطای واقعی:**
```
FAILED: Feature computation failed
'FeatureComputationService' object has no attribute 'compute'
```

**چرا تست‌ها نگرفتند:** تست موجود فقط شاخهٔ «کندلی ذخیره نشده» را می‌آزمود که
*قبل* از رسیدن به کد خراب return می‌کند. کلاسیک‌ترین نوع نقطهٔ کور تست.

**رفع:** فراخوانی درست `compute_set(...)` با `standard_feature_set_v1()`.
حالا: `Computed 109 features over 300 candles`.

**تست رگرسیون:** ۳ تست در `TestComputeFeaturesCommand` — یکی‌شان
(`test_the_service_contract_the_handler_relies_on_exists`) دقیقاً همان عدم
تطابق امضا را قفل می‌کند.

**اقدام پیشگیرانه:** هر ۷ دکمهٔ داشبورد با دیتای واقعی اجرا شدند. نتیجه:
```
fetch_market_data   OK    compute_features   OK (رفع شد)
run_backtest        OK    record_replay      OK
run_optimisation    OK    run_trading_cycle  OK
refresh_project_state OK  train_model        SKIP (کند، نیاز TF)
```

### ✅ شکل واقعی بازار اعتبارسنجی شد

نگرانی اصلی: دیتای واقعی **گپ آخر هفته** دارد (بازار جمعه شب تا یکشنبه بسته
است). آیا pipeline آن را «دیتای خراب» تلقی و قرنطینه می‌کند؟

**پاسخ: نه.** با ۳ هفته دیتای ۵ دقیقه‌ای واقعی‌شکل (۴۳۲۰ کندل) آزمایش شد:
```
quarantined   : False
overall score : 99.99
issues        : [warning] GAP_DETECTED: 2 gap(s)
```
گپ گزارش می‌شود (درست) ولی باعث دور ریختن دیتا نمی‌شود (هم درست).

۴ تست جدید در `test_mt5_ingestion.py`: گپ آخر هفته، بک‌تست کامل روی سری
گپ‌دار (ترتیب زمانی equity curve حفظ می‌شود)، حفظ اسپرد متغیر rollover
(۱۰ و ۴۵)، و جهش قیمتی یکشنبه.

### ✅ حل‌کنندهٔ نام نماد — `mt5_symbol_resolver.py`

**چرا:** شایع‌ترین دلیل شکست اولین اجرای واقعی. بروکرها طلا را
`XAUUSD` / `XAUUSD.i` / `XAUUSDm` / `GOLD` / `GOLDmicro` صدا می‌زنند.

```
XAUUSD.i  → XAUUSD      GOLDmicro → XAUUSD (alias)
XAUUSDm   → XAUUSD      XAUUSD.pro.ecn → XAUUSD
USTEC     → USTEC (دست‌نخورده)   US30 → US30 (دست‌نخورده)
```

**دو محافظ مهم:**
1. `USTEC` به `UST` تبدیل نمی‌شود (پسوند `C` کورکورانه کنده نمی‌شود)
2. `GOLD` به `GOL` تبدیل نمی‌شود (`_PROTECTED`)
3. پسوند ناشناخته → نام دست‌نخورده می‌ماند. **بهتر است نماد پیدا نشود تا
   اینکه نماد اشتباه معامله شود.**

امتیازدهی شفاف است (۱۰۰ دقیق / ۹۰ پسوند بروکر / ۸۰ alias / ۶۰ شامل) و هر
پیشنهاد **دلیلش** را همراه دارد.

**اضافه شد:**
- `shadbot-data mt5-resolve --symbol XAUUSD` — دستور جدید
- `mt5-ingest` هنگام شکست خودش پیشنهاد می‌دهد (`_suggest_symbol`)
- `run_real_data.py --auto-symbol` — نزدیک‌ترین نماد را می‌پذیرد، ولی
  **هرگز بی‌صدا**؛ همیشه چاپ می‌کند چه چیزی را جایگزین کرد

**۱۸ تست** در `tests/unit/dataset/test_mt5_symbol_resolver.py`.

### تأیید نهایی

کل سفر ویندوز با ترمینال ساختگی شبیه‌سازی شد (بروکری که طلا را `XAUUSD.i`
می‌نامد): اتصال → فهرست نمادها → تشخیص خودکار → ingest ۲۸۸۰ کندل → بدون قرنطینه.

```
black ✅  ruff ✅  mypy (253 files) ✅
pytest            697 passed, 6 skipped   (قبلاً 672)
RUN_TF=1 pytest   703 passed              (قبلاً 678)
```

**گزارش کامل:** `MT5_READINESS_REPORT.md`

---

## 2026-08-16 — فاز ۲۹: دو مدل پیش‌بینی (درخواست کاربر)

**درخواست:** یک مدل که high/low تا ۵ کندل آینده را پیش‌بینی کند، و یک مدل که
سیگنال را با درصد احتمال بدهد. هر دو roll-forward، با همهٔ فیچرها.
رنج روی ۱H، سیگنال روی ۵M.

### ممیزی اول — کد این قابلیت را نداشت

| نیاز | وضعیت قبل |
|---|---|
| رگرسیون high/low | ❌ `_build_compiled` فقط `SparseCategoricalCrossentropy` |
| سیگنال با احتمال | ⚠️ softmax بود ولی `predict()` به یک float فشرده می‌کرد |
| ۱۰۹ فیچر | ❌ `build_direction_series` فقط **۴** فیچر می‌ساخت |
| تایم‌فریم per-model | ❌ وجود نداشت |
| roll-forward | ✅ بود و درست |

پس فاز جدید لازم بود. `docs/Phases/Phase29.md` نوشته شد.

### ساخته شد

```
domain/ai/prediction_target.py          PredictionTarget, RangeForecast,
                                        SignalForecast, SignalClass
infrastructure/ai/target_builder.py     برچسب‌گذاری آینده + محافظ نشت
infrastructure/ai/feature_matrix.py     ۱۰۹ فیچر + OHLCV -> ماتریس
infrastructure/ai/model_roles.py        نقش رنج (۱H) و سیگنال (۵M)
infrastructure/ai/dual_predictor.py     حفظ کامل بردار احتمال
application/services/dual_model_service.py
scripts/run_dual_models.py
```

### سه تصمیم طراحی که باید یادت بماند

۱. **هدف‌ها نسبت به close، نه قیمت مطلق.** طلا در ۲۰۰۰ و ۳۰۰۰ نباید دو مسئلهٔ
   جدا باشد. مدلی که روی قیمت مطلق آموزش ببیند، بیرون از بازهٔ آموزشش
   بی‌صدا از کار می‌افتد.
۲. **کلاس HOLD.** مدل دوکلاسه مجبور است هر کندل یک طرف را بگیرد، حتی وقتی
   هیچ اتفاقی نمی‌افتد. «معامله نکن» ارزشمندترین خروجی یک مدل معاملاتی است.
۳. **`is_coherent` به‌جای تعمیر خودکار.** اگر مدل سقف را زیر کف پیش‌بینی کند،
   گزارش می‌شود نه اینکه جایشان عوض شود. جابه‌جایی بی‌صدا، مدل خراب را پنهان
   می‌کند.

### 🐞 باگ #۱۵ — آموزش بازتولیدپذیر نبود

حین تست idempotency پیدا شد: دو اجرای یکسان پیش‌بینی متفاوت می‌داد.

**علت:** `_build_compiled` پارامتر `seed` می‌گرفت و **هرگز استفاده‌اش
نمی‌کرد**. در Keras 3 هر لایه وزن اولیه را از مولد خودش می‌گیرد، پس
`tf.random.set_seed` به‌تنهایی کافی نیست.

**نقض مستقیم فاز ۱۳ §۳۴** که بازتولیدپذیری را الزام می‌کند.

**رفع:** `keras.utils.set_random_seed(seed)`. حالا دو اجرا دقیقاً یکی است
(`fold losses [0.117292]` هر بار). دو تست رگرسیون اضافه شد.

### تأیید عملی

```
RANGE MODEL (1H, ۵ کندل جلوتر) — با ۱۰۹ فیچر
  usable rows: 497 | feature columns: 115 | dropped warmup: 51
  current close 1990.69 -> high 2001.80 (+0.558%) low 1990.36 (-0.016%)

SIGNAL MODEL (5M, ۵ کندل جلوتر) — با ۱۰۹ فیچر
  label balance: {'sell': 61, 'hold': 170, 'buy': 64}
  sell 33.6% | hold 34.1% | buy 32.3%  -> hold 34.1%  actionable=False
```

**۱۱۵ ستون** = ۶ خام + ۱۰۹ کاتالوگ. کاتالوگ فاز ۱۲ بالاخره به AI وصل شد.

```
pytest 759 passed, 12 skipped  |  RUN_TF=1 → 771 passed   (قبلاً 703)
```

**۶۸ تست جدید** — ۲۱ هدف‌ها، ۱۷ برچسب‌گذاری (شامل ۳ تست نشت داده)،
۱۱ ماتریس فیچر، ۱۹ یکپارچه (شامل ۲ بازتولیدپذیری).

**گزارش کامل:** `PHASE29_REPORT.md`

---

## 2026-08-16 — فاز ۳۰: دیتاست آموزش و بافر زندهٔ بازار

**درخواست کاربر:** دیتاست ۱۰۰٬۰۰۰ کندلی (۵M و ۱H) با فیچرهای ذخیره‌شده،
پنجرهٔ ورودی ۵۰۰×۱۲۳، roll-forward با گام یک کندل، آپدیت هفتگی با محاسبهٔ
مجدد کامل فیچرها، بافر زندهٔ ۸۰۰ کندلی، و بک‌تست روی همان دیتاست ۱۰۰k.

### تصمیم‌های کلیدی

۱. **۱۲۳ ستون.** کاربر درست گفت که قیمت خام در ورودی نبود — کاتالوگ فقط
   `*_filter` داشت که قیمت **هموارشده با موجک** است. ۸ ستون خام اضافه شد
   (`open_rel`…`ohlc4_rel`, `volume_raw_log`)، همه نسبت به close.
   ۸ خام + ۶ مشتق + ۱۰۹ کاتالوگ = **۱۲۳**.

۲. **ژنراتور به‌جای ماتریس.** ۹۹٬۴۹۶ پنجرهٔ ۵۰۰×۱۲۳ = **۲۴.۵ گیگابایت**.
   ماتریس تخت فقط ۵۰ مگابایت است. پنجره‌ها لحظه‌ای ساخته می‌شوند. این
   بهینه‌سازی نیست — بدون آن قابلیت اصلاً اجرا نمی‌شود.

۳. **محاسبهٔ مجدد کامل، نه افزایشی.** EMA/MACD/ATR بازگشتی‌اند؛ مقدار
   محاسبه‌شده از تاریخچهٔ ناقص به‌شکلی نامحسوس غلط است. ~۲ دقیقه برای
   ۱۰۰k در برابر فیچرهای بی‌صدا خراب، معاملهٔ خوبی است.

۴. **بافر: جایگزینی نه تکرار.** کندل ۱H جاری قبل از بسته‌شدن ۱۲ بار گرفته
   می‌شود؛ append کردنش ۱۲ ساعت تاریخ جعلی می‌سازد. کندل با timestamp
   موجود **جایگزین** می‌شود، و کندل قدیمی ناشناخته **رد** می‌شود.

۵. **۸۰۰ به‌جای ۵۰۰.** warm-up فیچرها ۵۱ ردیف می‌خورد → ۷۴۹ باقی می‌ماند.
   بافر این را در زمان اجرا **بررسی** می‌کند و اگر کم بیاورد پنجرهٔ کوتاه
   نمی‌دهد، چون ورودی کوتاه یعنی مدل زباله می‌خواند.

### 🐞 باگ #۱۶ — digest دیتاست هرگز تطبیق نمی‌کرد

تست round-trip گرفتش: digest روی float64 حساب می‌شد ولی ماتریس float32
ذخیره می‌شد، پس بعد از reload **همیشه** فرق داشت — یعنی به‌عنوان بررسی
صحت کاملاً بی‌فایده بود.

گرد کردن به ۴ و ۶ رقم جواب نداد؛ اندازه‌گیری نشان داد خطا **نسبی** است
(~6e-8) و هر دقت ثابتی برای بعضی مقادیر روی مرز گرد کردن می‌افتد.
رفع: هش روی شکل ذخیره‌شدهٔ float32 با `struct.pack("<f", …)` — دقیقاً
همان بایت‌هایی که روی دیسک می‌روند.

### تأیید عملی

```
BUILD 6,000 candles/timeframe -> 15.0s
  5M: 6,000 -> 5,897 rows x 123 cols | stride-1 windows: 5,393
  1H: 6,000 -> 5,897 rows x 123 cols | stride-1 windows: 5,393

generator (100k): 99,496 windows of (500 x 123), stride 1
                  lazy 50 MB vs materialised 24.5 GB

dual models: input_shape=(500, 123) — both range and signal
LIVE BUFFER: 900 primed -> holds 800 -> model input 500 x 123
```

```
pytest 819 passed, 12 skipped  |  RUN_TF=1 → 831 passed   (قبلاً 771)
```

**۶۰ تست جدید** — ۲۱ ژنراتور پنجره، ۱۷ بافر زنده، ۲۱ یکپارچه دیتاست،
به‌علاوهٔ ۲ تست به‌روزشدهٔ فاز ۲۹ (۶ ستون → ۱۴ ستون).

**گزارش کامل:** `PHASE30_REPORT.md`

---

## 2026-08-16 — فاز ۳۱: حلقهٔ زندهٔ تصمیم‌گیری + بک‌تست با مدل واقعی

**درخواست کاربر:** «به همون ترتیبی ک خودت میدونی بهترینه انجام بده» →
ترتیب انتخابی: **A (حلقهٔ زنده) بعد B (وصل مدل به بک‌تست)**.

### شکافی که پر شد

فازهای ۲۹-۳۰ مدل‌ها و داده را ساختند، ولی هیچ چیز آن‌ها را به معامله وصل
نمی‌کرد. بافر ۸۰۰ کندلی خوانده نمی‌شد، ماتریس ۵۰۰×۱۲۳ مصرف نمی‌شد، و
`MomentumPredictionSource` هنوز پیش‌بینی‌کنندهٔ بک‌تست بود.

### الف) حلقهٔ زنده

`DualModelStrategy` — شش دروازه، هر کدام با دلیل:
۱) هر دو forecast موجود · ۲) مدل HOLD نگوید · ۳) اطمینان کافی ·
۴) رنج منسجم · ۵) reward/risk کافی · ۶) حرکت بزرگ‌تر از هزینه.

`LiveDecisionService` — یک tick کامل: بافر → فیچر → ۵۰۰×۱۲۳ → دو مدل →
استراتژی → گیت ریسک → اجرا.

**قاعدهٔ سخت: tick هرگز exception نمی‌دهد.** حلقهٔ بدون نظارت که با یک
اختلال بروکر بمیرد، یعنی قطعی سرویس. هر خطا به `TickResult` با
`status` و `reason` تبدیل می‌شود.

### ب) بک‌تست با مدل

`ModelPredictionSource` پورت موجود را پیاده می‌کند، پس موتور دست‌نخورده
ماند. دو تضمین علیت:
- منبع پنجرهٔ **خودش** را نگه می‌دارد و فقط باری را که موتور تحویل داده
  اضافه می‌کند — چیز دیگری در دسترس نیست
- تا پر شدن پنجره `None` برمی‌گرداند (خودداری)، نه padding

سه کلاس روی یک محور: از **directional confidence** استفاده می‌شود، پس
۰.۴۵/۰.۱۰/۰.۴۵ برابر ۰.۵ خوانده می‌شود (بلاتکلیف) نه خرید ضعیف.

### 🐞 ناسازگاری گزارش reward/risk

برای **فروش**، reward و risk جا عوض می‌کنند. `RangeForecast.reward_risk()`
دید long-oriented است، پس چاپ آن با دروازه‌ای که تازه معامله را تأیید کرده
تناقض داشت: `r/r 0.25` نمایش داده می‌شد در حالی که دروازه ۴.۰ حساب کرده بود.
رفع: استراتژی نسبت جهت‌آگاه خودش را گزارش می‌کند.

**mypy هم سایه‌افتادن متغیر گرفت** — نام `forecast` برای دو نوع مختلف در یک
scope استفاده شده بود.

### تأیید عملی

```
LIVE LOOP (سه tick، هر سه مسیر):
  tick 1  [no_trade] signal model says hold (65.0%)
  tick 2  [no_trade] reward/risk 0.30 < 1.20
  tick 3  [traded]   signal buy 90.0%, target 2046.85, r/r 3.33
                     filled : 0.01 @ 2028.58

MODEL-DRIVEN BACKTEST (مدل واقعاً آموزش‌دیده):
  bars 700 | model calls 59 | trades 7 | return +12.35%
```

> ⚠️ آن +۱۲.۳۵٪ روی یک **موج سینوسی** است که ذاتاً قابل پیش‌بینی است.
> عدد معناداری نیست — فقط ثابت می‌کند زنجیره کامل کار می‌کند.

```
pytest 866 passed, 12 skipped  |  RUN_TF=1 → 878 passed   (قبلاً 831)
```

**۴۷ تست جدید** — ۱۶ استراتژی دومدلی، ۱۵ حلقهٔ زنده (شامل تاب‌آوری در
برابر مدل خراب)، ۱۶ بک‌تست مدل (بیشترشان دربارهٔ علیت).

**گزارش کامل:** `PHASE31_REPORT.md`

---

## 2026-08-16 — فاز ۲۴: Deployment (تنها فاز کاملاً صفر)

**درخواست کاربر:** «فاز ۲۴ رو اجرا کن»

### ساخته شد

| فایل | نقش |
|---|---|
| `domain/deployment/health.py` | liveness / readiness / health با دسته‌بندی وابستگی |
| `domain/deployment/release.py` | نسخه، محیط، manifest، shutdown امن |
| `infrastructure/deployment/backup.py` | بکاپ + تأیید + بازیابی + prune |
| `infrastructure/deployment/health_checks.py` | probe های واقعی |
| `application/services/runner_service.py` | اجرای مداوم با نظارت |
| `deploy_cli.py` | `health`, `manifest`, `backup`, `restore`, `preflight` |
| `deploy/install_service.ps1` | ثبت در Task Scheduler ویندوز |
| `scripts/run_service.py`, `scripts/run_weekly_update.py` | اجرا |

### چهار تصمیم که باید یادت بماند

۱. **liveness ≠ readiness ≠ health.** سیستمی که تازه بالا آمده زنده است ولی
   آماده نیست. جمع‌کردن این سه در یک boolean دقیقاً همان چیزی است که باعث
   می‌شود پلتفرم روی سیستم نیمه‌آماده معامله کند.

۲. **وابستگی بحرانی از اختیاری جدا شد.** نبودن MT5 یا TensorFlow سیستم را
   `degraded` می‌کند نه `unhealthy` — داشبورد باید کار کند.

۳. **بکاپی که هرگز بازیابی نشده، بکاپ نیست** (§۸۰). هر بکاپ بلافاصله باز،
   integrity-check و row-count می‌شود. از SQLite backup API استفاده شد نه
   کپی فایل: کپی‌کردن دیتابیس وسط یک تراکنش فایلی می‌سازد که سالم به‌نظر
   می‌رسد و خراب restore می‌شود — بدترین حالت ممکن.

۴. **Task Scheduler نه Windows Service.** سرویس واقعی در session 0 اجرا
   می‌شود و آنجا ترمینال MT5 **در دسترس نیست** (IPC محلی در session کاربر).
   این محدودیت است، نه میان‌بر — در خود اسکریپت مستند شد.

### 🐞 باگ #۱۷ — ترتیب لیست بکاپ‌ها غلط بود

تست گرفتش: مرتب‌سازی بر اساس **نام فایل** بود، ولی دو بکاپ در یک ثانیه فقط
با پسوند عددی فرق دارند و `live-...-1.db` از `live-...db` **جلوتر** مرتب
می‌شود. یعنی `latest()` بکاپ **قدیمی‌تر** را برمی‌گرداند — و یک restore
می‌توانست بی‌صدا دیتای اشتباه را برگرداند.

رفع: مرتب‌سازی بر اساس زمان ثبت‌شده، با mtime به‌عنوان tie-breaker.

### 🐞 نقض معماری که تست گرفت

`default_monitor` در لایهٔ **domain** بود ولی از `infrastructure.data` import
می‌کرد. `test_dependency_direction` شکست. به `infrastructure/deployment/
health_checks.py` منتقل شد — دامنه باید از SQLite و TensorFlow و MT5 بی‌خبر
بماند.

### تأیید عملی

```
health      : degraded (MT5 optional missing) | ready=True | exit 0
backup      : 128 KB | schema v1 | 9 rows | verified=True
preflight   : READY. production requires explicit confirmation
service     : 3 cycles, 1 trade, backup at cycle 2
shutdown    : stopped accepting work -> in-flight completed -> persisted -> stopped
weekly      : revision 1, 2,897 rows x 123 cols, 9.1s
restore     : بدون --yes رد می‌شود ✓ | فایل خراب قبل از overwrite رد می‌شود ✓
```

```
pytest 932 passed, 12 skipped   (قبلاً 866)
```

**۶۶ تست جدید** — ۳۹ واحد (health/release)، ۲۷ یکپارچه (backup/runner).

**گزارش کامل:** `PHASE24_REPORT.md`

---

## 2026-08-16 — تکمیل فازهای ۹، ۲۱، ۲۲ (سه فاز حداقلی)

**درخواست کاربر:** «بررسی کن کامل اگ فاز ۲۴ تکمیل شده، برو سراغ ۹ و ۲۱ و ۲۲»

### اول: تأیید فاز ۲۴

فایل‌ها (هر ۱۰ تا) + عملکرد + ۶۶ تست → **کامل تأیید شد** ✅

### فاز ۹ — معماری پلاگین (۳۷ → ۵۹۵ خط)

`registry.py` + `manager.py`. خط جداکننده‌ای که سند می‌کشد رعایت شد:
Registry می‌گوید «چه چیزی ثبت شده»، Manager می‌گوید «وضعیت عملیاتی چیست».

- state machine واقعی با ۹ حالت؛ انتقال غیرمجاز **رد** می‌شود
- پلاگین شکست‌خورده **دلیلش را نگه می‌دارد** (§۱۸)
- کشف **قطعی**: هرگز پوشه اسکن نمی‌شود — آن اجرای کد دلخواه است
- گراف وابستگی + تشخیص چرخه؛ اگر وابستگی fail شود، dependent اجرا نمی‌شود
- یک پلاگین خراب کل استارتاپ را نمی‌خواباند

### فاز ۲۱ — پیکربندی لایه‌ای (۱۲۰ → ۴۵۰ خط)

شش لایه با اولویت قطعی. mapping ها بازگشتی merge، لیست‌ها جایگزین.

**محافظت از secret** مهم‌ترین بخش: تشخیص خودکار بر اساس نام کلید، و
redaction در `as_dict`, `to_json` **و `__repr__`**. یک traceback که شیء
config را چاپ کند نباید رمز بروکر را لو بدهد. قاعده در **یک نقطه** اعمال
شد نه در هر call site.

اعتبارسنجی همهٔ خطاها را یکجا گزارش می‌کند (§۲۸).

### فاز ۲۲ — لاگینگ ساختاریافته (۲۴ → ۴۰۰ خط)

JSON، correlation id که خودش منتشر می‌شود، bound logger، چرخش فایل.

از `contextvars` استفاده شد نه global: command bus و runner threaded هستند
و تستی ثابت می‌کند context بین thread ها نشت نمی‌کند.

secret ها **داخل logger** پنهان می‌شوند — قبل از رسیدن به هر sink.

### 🐞 هشداری که ruff گرفت

`ContextVar("...", default={})` — آن dict بین هر context ای که مقدار ست
نکرده **مشترک** است. یک mutation درجا فیلدها را بین عملیات‌های نامرتبط نشت
می‌داد. با `default=None` رفع شد. نکتهٔ ظریفی بود.

### کیفیت

```
black ✅ ruff ✅ mypy (279 files) ✅
pytest 1034 passed, 12 skipped     (قبلاً 932)
```

**۱۰۲ تست جدید:** ۲۹ پلاگین · ۴۲ پیکربندی · ۳۱ لاگینگ

🎉 **هر ۲۸ فاز اصلی + ۳ فاز جدید کامل شدند.**

**گزارش:** `PHASE_9_21_22_REPORT.md`

---

## 2026-08-17 — فاز ۳۲: پروفایل اکانت و کنترل کامل از GUI

**MT5 وصل شد!** Alpari-MT5-Demo، لاگین 53102853، ۸۸۲ نماد، `XAUUSD` تطابق
دقیق. روی ویندوز **۱۰۴۶ تست سبز** (هر دو اجرا).

**درخواست کاربر:** تعویض اکانت از داخل GUI، نگاشت نام نماد per-broker، و
اجرای همهٔ ران‌ها فقط از رابط کاربری.

### ممیزی: ۱۸ اسکریپت، ۸ دکمه

ده عملیات فقط از ترمینال قابل اجرا بودند. حالا **۲۱ دکمه در ۶ گروه**.

### پروفایل اکانت

`AccountProfile` = name + login + server + terminal_path + symbol_map + is_demo

**رمز هرگز ذخیره نمی‌شود.** پروفایل فقط نام متغیر محیطی را نگه می‌دارد
(`SHADBOT_MT5_PASSWORD_{PROFILE}`). یک credential در فایل JSON کنار کد، یک
screenshot با عمومی‌شدن فاصله دارد. اگر هم ست نشود، از session خودِ ترمینال
استفاده می‌شود — که حالت عادی است.

### نگاشت نماد per-broker

پلتفرم داخلاً **یک** نام می‌شناسد و هر پروفایل ترجمه می‌کند:
`XAUUSD` → Alpari: `XAUUSD` · Broker B: `XAUUSD_i` · Broker C: `GOLD`

بدون این، یک ابزار سه دیتاست و سه مدل جدا می‌ساخت که قابل مقایسه نیستند —
عوض‌کردن بروکر بی‌صدا تاریخچهٔ یادگیری را از نو شروع می‌کرد.

«Detect symbol names» پیشنهاد می‌دهد ولی **فقط با تأیید** ذخیره می‌کند.

### 🐞 نقصی که تست گرفت

`health_check` هنگام شکست جزئیات را در `detail` می‌گذاشت نه `lines` — یعنی
GUI دقیقاً وقتی که اپراتور بیشتر از همیشه به دیدن نیاز دارد، کادر خالی نشان
می‌داد. رفع شد.

### تأیید زنده

```
۲۱ دکمه در ۶ گروه رندر شد
add_account    → SUCCEEDED (متغیر رمز اعلام شد)
map_symbol     → XAUUSD -> XAUUSD.i
activate       → symbols: {'XAUUSD': 'XAUUSD.i'}
health_check   → degraded — ready=True
```

```
pytest 1097 passed, 12 skipped   (قبلاً 1034)
```

**۶۳ تست جدید** — ۳۹ پروفایل/نگاشت، ۲۴ پوشش GUI (شامل تستی که تضمین می‌کند
هر اسکریپت یا دکمه دارد یا استثنای مستند).

**گزارش:** `PHASE32_REPORT.md`

---

## 2026-08-17 — رفع بن‌بست اولین اجرا (باگ #۱۸)

**گزارش کاربر:**
```
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
Database not found: shadbot.db
Create one first, for example:
    python scripts/run_persistence.py --keep --db shadbot.db
```

**تناقضی که خودم ساختم:** قرار شد همه‌چیز از GUI اجرا شود، ولی داشبورد برای
شروع یک دستور ترمینالی می‌خواست — آن هم اسکریپتی که در فاز ۳۲ عمداً از GUI
حذفش کرده بودم («جایش را ران‌های واقعی گرفتند»). یعنی کاربر به دستوری هدایت
می‌شد که خودم بی‌اهمیت اعلامش کرده بودم.

**علت:** `cmd_serve` وجود فایل را چک می‌کرد و خارج می‌شد — در حالی که
`Database()` خودش migration را اجرا می‌کند و ساختن دیتابیس خالی یک خط است.

**رفع:**
- `cmd_serve` اگر دیتابیس نباشد، خودش می‌سازد و شروع می‌کند
- صفحهٔ خالی داشبورد حالا **پنج قدم با نام دکمه** نشان می‌دهد، نه دستور شل

```
No database at shadbot.db — creating it ...
  created with schema v1
=== ShadBotTrader dashboard ===
  actions  : 21 buttons enabled
```

**۴ تست رگرسیون** + دو تست قدیمی که رفتار قبلی را الزام می‌کردند به‌روز شدند
(به‌درستی شکستند: قرارداد عوض شده بود).

```
pytest 1101 passed, 12 skipped
```

---

## 2026-08-17 — فاز ۳۳: پیوستگی و آپدیت افزایشی دیتاست (باگ #۱۹)

**سؤال کاربر:** «هربار Fetch بزنم دیتا اضافه می‌شود؟ سقف ۱۰۰k رعایت می‌شود؟
ترتیب کندل‌ها پشت سر هم چک می‌شود؟»

**جواب پس از آزمایش واقعی: هر سه ❌**

```
ingest #1 : v1  candles stored=200
ingest #2 : v2  candles stored=50     ← تاریخچه نابود شد
```

`save_normalized` نسخهٔ جدید می‌نوشت و `query` فقط **آخرین نسخه** را
می‌خواند. `QualityAnalyzer` هم گپ را فقط **داخل یک نسخه** می‌دید.

### سخت‌ترین بخش: گپ همیشه گپ نیست

بازار تعطیل می‌شود. «شنبه کندل نیست» عادی است؛ «سه‌شنبه کندل نیست» یعنی
دیتای گم‌شده.

**تقویم یاد گرفته می‌شود، نه اعلام.** از تاریخچهٔ موجود:
```
Mon (10,10) ... Fri (10,10)  |  Sat (0,10) Sun (0,10)  → closed on Sat, Sun
```
تقویم هاردکد برای کریپتو غلط است، برای بروکر در timezone دیگر غلط است، و
ظرف یک سال کهنه می‌شود. تقویم یادگرفته‌شده خودش وفق می‌دهد و **شواهدش قابل
بازرسی است**.

نتیجه (آخرین کندل سه‌شنبه ۹ ژوئیه):
- روز کاری بعدی → می‌چسبد ✅
- ۳ روز بعد → ۲ کندل گم
- یک ماه بعد → **۲۱** کندل گم (نه ۳۰ — آخر هفته‌ها شمرده نشدند)

### تصمیم‌های کاربر

- شکاف واقعی → **backfill خودکار از بروکر**، و اگر نشد رد کند
- تعطیلی → **از خود دیتا یاد بگیرد**

### سه قاعدهٔ سخت

۱. **تأیید قبل از نوشتن.** آپدیت ناموفق باید دیتاست قبلی را دست‌نخورده
   بگذارد، نه نصفه‌جایگزین.
۲. **کندل جدید در تصادم برنده است.** کندل ۱H جاری قبل از بسته‌شدن بارها
   خوانده می‌شود؛ آخرین خواندن درست‌ترین است.
۳. **رد کردن پیش‌فرض است.** چسباندن دو سر یک حفره، به مدل حرکت قیمتی یاد
   می‌دهد که هرگز رخ نداده — و هیچ تستی بعدش نمی‌گیردش.

### 🐞 باگ فرعی که تست خودم گرفت

`next_version` دایرکتوری **raw** را می‌شمرد ولی سرویس در **normalized**
می‌نوشت → `FileExistsError` در دومین آپدیت. رفع شد.

### تأیید عملی

```
۱) اول: 50 کندل
۲) append: +20 → 60 (۱۰ قدیمی حذف) ✅ سقف رعایت شد
۳) تکراری: +0، آپدیت 20 ✅ بدون duplicate
۴) پرش یک‌ماهه: REFUSED — دیتاست دست‌نخورده ✅
۵) با backfill: 21 کندل وصله شد → پیوسته ✅
```

```
pytest 1155 passed, 12 skipped   (قبلاً 1101)
```

**۵۴ تست جدید** — ۳۳ پیوستگی/تقویم، ۲۱ آپدیت افزایشی.

**گزارش:** `PHASE33_REPORT.md`

---

## 2026-08-17 — فاز ۳۴: چارت شمعی و بازرسی دیتاست

**درخواست کاربر:** چارت کندلی + اطلاعات دیتاست (تعداد کندل و ستون‌ها) برای
هر سهٔ Fetch / Update features / Build dataset.

**ساخته شد:** یک صفحهٔ واحد `/data` (به‌علاوهٔ `/api/data`) با سه بخش که از
سه انبار مختلف می‌خوانند: `ParquetCandleStore`، `ParquetFeatureStore`،
`TrainingDataService`.

### دو تصمیم که مهم‌اند

۱. **چارت ۳۰۰ کندل می‌کشد، ولی تعداد کل را کامل گزارش می‌کند.** دیتاست
   ۱۰۰k نباید صفحهٔ وب ۱۰۰k نقطه‌ای شود — ولی کوتاه‌کردن نمودار و دروغ‌گفتن
   دربارهٔ تعداد، از هر دو بدتر بود.

۲. **ستون ثابت علامت می‌خورد.** `close_rel` طبق ساختار صفر است و به مدل
   چیزی یاد نمی‌دهد؛ صفحه این را می‌گوید به‌جای اینکه مثل ورودی واقعی
   به‌نظر برسد. تست هم همین را قفل می‌کند.

### فقط می‌خواند

`DataInspector` یک Gateway است: هر عددی روی صفحه از storage خوانده شده، نه
محاسبه‌شده. انبار خالی → نتیجهٔ خالی، نه exception (داشبوردی که چون چیزی
fetch نشده crash کند، دقیقاً وقتی بی‌فایده است که می‌خواهی همین را بفهمی).

### تأیید

```
CANDLES : 1,500 stored | chart 300 pts | continuous=True
MATRIX  : 1,397 rows x 123 cols | {'raw price': 8, 'candle shape': 6, 'feature': 109}
          constant: ['close_rel']
FEATURES: 109 stored
```
JS چارت با Node اجرا و اعتبارسنجی شد.

```
pytest 1182 passed, 12 skipped   (قبلاً 1155)
```
**۲۷ تست جدید.**

**گزارش:** `PHASE34_REPORT.md`

---

## 2026-08-17 — فاز ۳۵: دو دیتاست مجزا + فقط دیتای واقعی (باگ‌های ۲۰–۲۳)

**سؤال کاربر:** «چرا Build training dataset براش تایم فریم فرقی نداره؟ مگه
نباید دوتا دیتاست داشته باشیم برای آموزش یکی ۵ دقیقه یکی ۱ ساعته؟»

**پاسخ کوتاه:** دو دیتاست از فاز ۳۰ وجود داشت (`DatasetSpec.timeframes =
("5M","1H")` و `build()` روی هر دو حلقه می‌زند و دو فایل `.npz` می‌نویسد)،
ولی سه ایراد باعث می‌شد در عمل درست کار نکند. کاربر بعد از توضیح، چهار
دستور صریح داد و هر چهار اجرا شد.

### چهار باگ

| # | باگ | چرا مهم بود |
|---|---|---|
| ۲۰ | `Fetch market data` فقط **یک** تایم‌فریم می‌گرفت (پیش‌فرض `5M`) | ولی build هر دو را لازم داشت → مستقیماً به باگ ۲۱ می‌رسید |
| ۲۱ | نبود دیتا → **کندل نمونهٔ سینوسی** ساخته و زیر نماد واقعی ingest می‌شد | مدل رنج روی دیتای جعلی آموزش می‌دید و آموزش‌دیده به‌نظر می‌رسید. یک اجرا بعد، تشخیص‌ناپذیر. نقض مستقیم `DEVELOPMENT_RULES.md` |
| ۲۲ | `build_feature_matrix` سطر را از **هر جای** سری حذف می‌کرد | یک `NaN` در سطر ۴٬۰۰۰ آن را حذف می‌کرد و ۳٬۹۹۹ به ۴٬۰۰۱ می‌چسبید. roll-forward از روی بازار ندیده رد می‌شد و هیچ تستی نمی‌گرفت |
| ۲۳ | کندل زیر نام بروکر (`XAUUSD_i`) ذخیره، ولی بقیه canonical (`XAUUSD`) می‌خواندند | یک نماد، دو دیتاست بی‌ارتباط |

### چهار قاعدهٔ جدید

**۱. تایم‌فریم‌های آموزش با هم سفر می‌کنند.** `TRAINING_TIMEFRAMES = ("5M","1H")`.
فیلد Timeframes حالا لیست می‌گیرد و پیش‌فرضش `5M,1H` است. هر تایم‌فریم مستقل
merge می‌شود؛ رد شدن یکی، دیگری را برنمی‌گرداند.

**۲. هیچ کندل ساختگی‌ای زیر نماد واقعی ذخیره نمی‌شود.** نبود دیتا حالا خطای
`NoRealData` با دستور دقیق است. اسکریپت‌های دمو همچنان کندل می‌سازند — چون
کارشان همین است — ولی زیر `DEMOXAU` که alias هیچ چیز واقعی‌ای نیست. تستی
این را اجبار می‌کند: هر اسکریپتی که `generate_sample()` صدا می‌زند حق ندارد
نام نماد طلا داشته باشد.

**۳. سطر فقط از دو سرِ سری حذف می‌شود.** خواستهٔ صریح کاربر:
«این کار فقط برای ابتدای دیتاست، اونم بخاطر اندیکاتورایی مثل SMA».

| کجا | مثال | کار |
|---|---|---|
| ابتدا | `SMA 200` | حذف سطر → `dropped_warmup` |
| انتها | `chikou`، `*_target_p1` | حذف سطر → `dropped_tail` |
| **وسط** | `NaN` وسط سری | حذف **ستون** → `holed_features` |

`FeatureMatrix.is_contiguous` این تضمین را صریح می‌کند و
`TimeframeSlice.contiguous` آن را در manifest ثبت.

**۴. زیر نام بروکر بگیر، زیر نام canonical ذخیره کن.**
`fetch_and_update(..., store_as=...)` قبل از merge برچسب می‌زند. backfill
هنوز با نام بروکر از MT5 می‌پرسد (تنها نامی که MT5 می‌شناسد) و جوابش را
canonical ذخیره می‌کند. دیتای قدیمی زیر alias هنوز پیدا می‌شود ولی
`symbol_scope.py` **می‌گوید** که از alias استفاده کرده — سکوت، تکرار همان
اشتباه بود.

### ساخته شد

| فایل | نقش |
|---|---|
| `infrastructure/data/symbol_scope.py` | `StoredSymbol`، `alias_candidates`، `resolve_stored_symbol`، `stored_symbols` |
| `tests/integration/test_dual_timeframe_datasets.py` | ۲۳ تست، یک کلاس برای هر باگ |
| `docs/Phases/Phase35.md` | سند فاز |

### تغییر کرد

- `infrastructure/ai/feature_matrix.py` — برش دو سر، `holed_features`، `dropped_tail`، `is_contiguous`
- `domain/dataset/training_dataset.py` — سه فیلد و سه هشدار جدید در slice
- `application/services/training_data_service.py` — عبور فیلدها
- `application/services/dataset_update_service.py` — `store_as`، `_relabel`، backfill آگاه از بروکر
- `presentation/commands/handlers.py` — `parse_timeframes`، fetch چندتایم‌فریمی، `missing_timeframes`، حذف fallback نمونه
- `scripts/run_{training_dataset,dual_models,weekly_update,live_loop}.py` — `NoRealData`
- ده اسکریپت دمو + شش CLI — نماد `XAUUSD_i` → `DEMOXAU` یا `XAUUSD`

### تصمیمی که گرفته نشد

**به «Build training dataset» فیلد timeframe اضافه نشد.** اگر اضافه می‌شد،
اپراتور می‌توانست 5M را روی 1H کهنه بسازد و دو مدل روی تاریخچه‌هایی که در دو
لحظهٔ متفاوت تمام می‌شوند آموزش ببینند. **جفت، واحد کار است.**

### تأیید

```
black --check .                 ✅ 407 files
ruff check .                    ✅
mypy src --python-version 3.12  ✅ 288 files
pytest                          ✅ 1205 passed, 12 skipped   (قبلاً 1182)
RUN_TF=1                        ✅ 278 + 344 + 592
```
**۲۳ تست جدید.**

اجرای دمو دو بار: بار دوم `added 0` و digest هر دو slice بایت‌به‌بایت یکسان.

```
5M: 1,000 candles -> 897 rows x 123 cols | front 77 | tail 26 | contiguous True
1H: 1,000 candles -> 897 rows x 123 cols | front 77 | tail 26 | contiguous True
symbols on disk: ['XAUUSD']        ← گرچه از XAUUSD_i گرفته شد
```

**گزارش:** `PHASE35_REPORT.md`

---

## 2026-08-17 — فاز ۳۶: دیدن روند آموزش در همان لحظه (باگ‌های ۲۴–۲۷)

**گزارش کاربر:** «الان موقعی ک توی Train both models ران رو میزنم، نه توی
پاورشل نه توی صفحه وب چیزی از روند آموزش بهم نشون نمیده که دقت و درصدو این
چیزا رو ببینم»

سه علت جدا داشت، نه یکی — و یک باگ چهارم موقع تست زندهٔ همین فاز پیدا شد.

### چهار باگ

| # | باگ | ریشه |
|---|---|---|
| ۲۴ | خروجی تا **پایان** کار buffer می‌شد | `subprocess.run(capture_output=True)` تا exit پروسه برنمی‌گردد. آموزش ۲۰ دقیقه‌ای = ۲۰ دقیقه سکوت. صفحهٔ وب می‌گفت «reload کن» ولی reload همان هیچ را نشان می‌داد |
| ۲۵ | `ConsoleProgressReporter` از فاز ۱۳ ساخته شده بود و **هیچ‌کس صدایش نمی‌زد** | `progress or NullProgressReporter()` و هیچ فراخوانی‌ای `progress=` پاس نمی‌داد. به‌علاوهٔ `verbose=0` کراس |
| ۲۶ | accuracy محاسبه و **دور ریخته** می‌شد | trainer فقط `val_loss` را نگه می‌داشت. «مدل چقدر خوبه؟» در کل سیستم جواب نداشت |
| ۲۷ | `--storage-root` داشبورد به اسکریپت‌ها **نمی‌رسید** | چهار دکمهٔ اسکریپتی آن را پاس نمی‌دادند → اسکریپت سراغ `datasets/` پیش‌فرض می‌رفت. کاربر در `/data` هزاران کندل می‌دید و آموزش می‌گفت «کندلی نیست» |

باگ ۲۷ را موقع تست زندهٔ فاز ۳۶ گرفتم: داشبورد را با `--storage-root
/tmp/live36` بالا آوردم و آموزش گفت `symbols on disk: P24DEMO, P24WK,
P30TEST, P31DEMO, XAUUSD_I` — یعنی ریشهٔ اشتباه.

### چه چیزی حالا هست

**پاورشل:** لاگ هر epoch با loss/accuracy/lr، نوار پیشرفت، ETA و
`s/fold`. با `--quiet` خاموش می‌شود.

**صفحهٔ وب:** بنر Running حالا یک `<pre>` زنده دارد که از `/api/log` هر ۲
ثانیه می‌خواند. اسکرول هوشمند: اگر پایین باشی دنبال لاگ می‌آید، اگر بالا
رفته باشی جایت را نگه می‌دارد. در پایان یک‌بار reload می‌کند تا پنل نتیجه
بیاید.

سه جزئیات که «زنده» بودن را ممکن کرد:
- `Popen` + خواندن خط‌به‌خط به‌جای `subprocess.run`
- `PYTHONUNBUFFERED=1` — وگرنه پایتون وقتی مقصد pipe است ۸KB بافر می‌کند و
  لاگ دسته‌ای و با تأخیر می‌رسد
- `bufsize=1` با `text=True` برای بافر خط سمت خودمان

**سنجهٔ کیفیت با معیار مقایسه:** `fold_metrics` آخرین مقدار هر سنجه را
به‌ازای هر fold نگه می‌دارد و اسکریپت تفسیرش می‌کند. مهم‌تر از خود عدد،
مقایسه با baseline است: در مسئلهٔ ۳ کلاسه که ۷۰٪ نمونه‌ها HOLD‌اند، مدلی که
همیشه HOLD بگوید ۷۰٪ دقت می‌گیرد و هیچ یاد نگرفته. اگر baseline زده نشده
باشد صریح می‌گوید `NO BETTER than`. برای مدل رنج، `val_mae` به دلار ترجمه
می‌شود.

### تغییر کرد

- `presentation/commands/handlers.py` — `_run_script` با `Popen` و استریم؛
  `RUN_LOG_DIR`/`run_log_path`/`read_run_log`؛ `--storage-root` به هر چهار دکمه
- `presentation/web/server.py` — مسیر `GET /api/log`
- `presentation/web/renderer.py` — پنل لاگ زنده + JS polling + `.runlog`
- `infrastructure/ai/wavenet/wavenet_trainer.py` — `fold_metrics`
- `application/services/dual_model_service.py` — عبور `fold_metrics`
- `scripts/run_dual_models.py` — `ConsoleProgressReporter`، `--quiet`، `print_quality()`
- `.gitignore` — `run_logs/`

### تأیید

```
black ✅  ruff ✅  mypy (288 files) ✅
pytest 1228 passed, 12 skipped   (قبلاً 1205)
RUN_TF=1  278 + 370 + 592
```
**۲۳ تست جدید.**

تست زندهٔ داشبورد روی پورت ۸۰۹۹ — لاگ **حین اجرا** رشد کرد:
```
[8s] busy=True lines=32 → [24s] lines=63 → [32s] lines=77 → [40s] busy=False
```

### هشدار صادقانه دربارهٔ اعداد این تست

`val_accuracy 100%` روی **۴ نمونهٔ اعتبارسنجی** و دیتای سینوسی ساختگی
به‌دست آمده. این عدد کیفیت مدل را نشان نمی‌دهد، فقط ثابت می‌کند مسیر
گزارش‌دهی کار می‌کند. روی دیتای واقعی انتظار عدد خیلی پایین‌تر داشته باش؛
اگر آنجا هم ۱۰۰٪ دیدی، نشانهٔ **نشت داده** است نه موفقیت.

**گزارش:** `PHASE36_REPORT.md`

---

## 2026-08-17 — فاز ۳۷: پیشرفت زندهٔ ویژگی‌ها + انبار جدا برای هر سری (باگ ۲۸)

**دو درخواست کاربر:** نمایش زندهٔ اینکه کدام ویژگی دارد حساب می‌شود و چندتا
مانده؛ و بررسی اینکه آیا ویژگی‌ها برای ۵ دقیقه و ۱ ساعته جدا محاسبه و ذخیره
می‌شوند.

سؤال دوم یک باگ جدی را لو داد. جواب صادقانه بود: محاسبه بله، **ذخیره نه**.

### باگ ۲۸ — ویژگی‌های دو تایم‌فریم روی هم می‌افتادند

مسیر ذخیره‌سازی `features/{feature_id}/v{version}.parquet` بود — نه نماد، نه
تایم‌فریم. یعنی `atr_14` برای 5M می‌شد `v1` و همان ویژگی برای 1H می‌شد `v2`
در **همان پوشه**. دو کمیت کاملاً متفاوت، بدون هیچ چیزی که از هم جدایشان کند.
در مخزن خودمان ۲۲ نسخهٔ بی‌هویت زیر `datasets/features/atr_14/` بود.

**چرا تا حالا فاجعه نشده بود:** مدل‌ها این انبار را نمی‌خوانند —
`build_feature_matrix` همه را در حافظه از نو حساب می‌کند. پس آموزش سالم بود.
ولی هر مصرف‌کنندهٔ دیگری (بازرسی `/data` و هر چیز آینده) دیتای اشتباه
می‌گرفت. بمب ساعتی بود نه انفجار.

**رفع:** `features/{symbol}/{timeframe}/{feature_id}/v{n}.parquet`. هر سری
شمارندهٔ نسخهٔ مستقل خودش را دارد. `for_series()` نمونهٔ **جدید** برمی‌گرداند
(نه mutate) تا سرویسی که store دارد زیر پایش عوض نشود.

**پورت `FeatureRepository` دست نخورد** — طبق فریز فاز ۲۶ امضای متدها همان
ماند و scope به نمونه بسته شد، نه به امضا.

اثبات بعد از رفع: `5M/atr_14/v1 = 2.7312` و `1H/atr_14/v1 = 6.5696` — دو
عدد متفاوت، هرکدام در `v1` خودش.

### پیشرفت زنده

```
[#---------------------------]   1.8% |   3/109 | low_filter
      stored v1 | 1,000 values | quality 98.69
...
  109/109 stored | 0 quarantined | 32 research-only
```

هر خط: کدام ویژگی، چندتا از چندتا، چند درصد، چند مقدار تولید شد، کیفیتش
چقدر. قرارداد `FeatureProgressReporter` عمداً شبیه `TrainingProgressReporter`
فاز ۳۶ است — دو عملیات طولانی در یک محصول نباید دو شکل گزارش بدهند.

دکمهٔ داشبورد در همان پنل لاگ زندهٔ فاز ۳۶ می‌نویسد. چون این هندلر داخل خود
پروسه اجرا می‌شود (نه زیرپروسه)، مستقیم در `run_logs/compute_features.log`
می‌نویسد.

فیلد Timeframes هم مثل فاز ۳۵ لیست‌پذیر شد با پیش‌فرض `5M,1H`.

### ساخته شد

| فایل | نقش |
|---|---|
| `infrastructure/feature/feature_progress.py` | `FeatureProgressReporter`، `NullFeatureProgress`، `ConsoleFeatureProgress` |
| `tests/integration/test_feature_visibility.py` | ۱۹ تست |

### تغییر کرد

- `infrastructure/feature/parquet_feature_store.py` — چیدمان جدید، `for_series()`، `scope`، پاک‌سازی نام مسیر
- `application/services/feature_computation_service.py` — `progress`، scope خودکار repository
- `presentation/commands/handlers.py` — `compute_features` چندتایم‌فریمی با لاگ زنده
- `presentation/gateway/data_inspector.py` + `web/data_renderer.py` — ستون Series، برچسب legacy
- دو تست موجود با قرارداد جدید تطبیق داده شدند (نه تضعیف)

### تأیید

```
black ✅  ruff ✅  mypy (289 files) ✅
pytest 1247 passed, 12 skipped   (قبلاً 1228)
RUN_TF=1  278 + 389 + 592
```
**۱۹ تست جدید.**

تست زندهٔ داشبورد: `5M: 109/109` و `1H: 109/109`، روی دیسک دو درخت جدا، و
۲۱۸ خط `stored v1` در لاگ (۱۰۹ × ۲).

یک تست ثابت می‌کند **reporter نتیجه را عوض نمی‌کند** — اجرای با و بدون
گزارشگر دقیقاً یک خروجی می‌دهد. ناظری که چیزی را که می‌بیند تغییر بدهد باگ
است نه امکانات.

### دیتای قدیمی مخزن پاک نشد

`datasets/features/` فعلی (۲۲ نسخهٔ بی‌هویت) دست‌نخورده ماند: حذف دیتای
کاربر بدون اجازه درست نیست، هویتشان قابل بازیابی نیست (حدس‌زدن همان اشتباهی
است که این فاز رفعش کرد)، و `/data` با برچسب `legacy` نشانشان می‌دهد.

**گزارش:** `PHASE37_REPORT.md`

---

## 2026-08-17 — فاز ۳۸: کش ویژگی‌ها + رفع سوءتفاهمی که خودم ساختم

**کاربر عصبانی و به‌حق:** «حتما از ویژگی ها توی دیتایی که قراره بدیم ب مدل
برای آموزش استفاده چرا تا الان استفاده نکردی پس؟ قبلا گفته بودم که!!!! پس
الان چ ماترسیو داری برای آموزش ب مدل میدی؟؟؟؟؟»

### اول: جواب، با عدد

**۱۰۹ ویژگی کاتالوگ از فاز ۲۹ در ماتریس آموزش بوده‌اند.** اندازه‌گیری:

```
matrix given to the model: 297 rows x 123 cols
  candle-derived : 14
  CATALOGUE      : 109
```

دکمهٔ Train both models هم `--with-features` پاس می‌دهد.

### سوءتفاهم تقصیر من بود

در گزارش فاز ۳۷ نوشتم «ویژگی‌های ذخیره‌شده هنوز توسط هیچ‌کس خوانده
نمی‌شوند». جمله **درست ولی گمراه‌کننده** بود: منظورم فایل‌های پارکت روی
دیسک بود، نه خود ویژگی‌ها.

| | واقعیت |
|---|---|
| ویژگی‌ها در ماتریس آموزش | ✅ بله، ۱۰۹ تا |
| از **فایل پارکت** خوانده می‌شد | ❌ نه، هر بار در حافظه از نو |

مدل همیشه ویژگی‌ها را می‌گرفت؛ فقط دوباره‌کاری می‌شد. باید می‌نوشتم «انبار
پارکت مصرف‌کننده ندارد، ولی ماتریس آموزش ۱۲۳ ستونه است». درس: وقتی می‌نویسم
«X استفاده نمی‌شود»، باید دقیقاً بگویم کدام X.

حالا ۶ تست این را قفل می‌کنند تا نه من مبهم بنویسم نه کد بی‌صدا به ۱۴ ستون
برگردد. خروجی build هم صریح می‌گوید:
`columns = 14 candle-derived + 109 catalogue features`

### قاعدهٔ کش

خواستهٔ کاربر: تا دیتاست عوض نشده از انبار بخوان؛ عوض که شد **از اول** حساب
کن و دوباره ذخیره کن.

**چرا append ممنوع است:** EMA/MACD/ATR بازگشتی‌اند و حالت را از کندل اول
حمل می‌کنند. مقدار روی ۱۰۰k کندل با ادامه‌دادن از کندل ۹۹k یکی نیست، تفاوتش
نامرئی است و هیچ تستی نمی‌گیردش.

**تشخیص با اثر انگشت، نه تاریخ فایل** (تاریخ دروغ می‌گوید: بازنویسی با
محتوای یکسان، یا ویرایش درجا). `FeatureFingerprint` پوشش می‌دهد: تعداد
کندل، اولین/آخرین زمان، **digest همهٔ مقادیر OHLCV**، نام و نسخهٔ feature
set، و فهرست ۱۰۹ شناسه.

اندازه‌گیری:
```
1. اولین اجرا (1000 کندل)     reused=  0/109  1.54s
2. همان کندل‌ها               reused=109/109  0.53s
3. بار سوم                    reused=109/109  0.52s
4. بعد از آپدیت (1100)        reused=  0/109  1.63s
5. همان 1100                  reused=109/109  0.53s
versions on disk: ['v1', 'v2']   ← نه پنج نسخه
```

در داشبورد `REUSED from the store — the dataset has not changed` و بعد از
آپدیت، در لاگ زنده دلیلش:
`recompute : candle count changed: 1,000 -> 1,200 (the dataset was updated)`

اثر انگشت خراب همیشه به محاسبهٔ کامل منجر می‌شود — به دیتایی که نمی‌توانیم
تأییدش کنیم اعتماد نمی‌کنیم. فیلد `Force recompute` هم اضافه شد.

### ساخته شد

| فایل | نقش |
|---|---|
| `infrastructure/feature/feature_cache.py` | `FeatureFingerprint`، `FeatureCache`، `candles_digest` |
| `tests/integration/test_feature_cache.py` | ۲۱ تست |

### تغییر کرد

- `application/services/feature_computation_service.py` — `force`، بررسی کش، `from_cache`/`reused_count`
- `infrastructure/feature/feature_progress.py` — `on_cache_hit`، `reason`
- `presentation/commands/handlers.py` — گزارش REUSED، فیلد Force recompute
- `scripts/run_training_dataset.py` — چاپ تفکیک ۱۴+۱۰۹
- یک تست فاز ۳۷ با قاعدهٔ جدید تطبیق داده شد (نه تضعیف)

### تأیید

```
black ✅  ruff ✅  mypy (290 files) ✅
pytest 1267 passed, 13 skipped   (قبلاً 1247)
RUN_TF=1  278 + 410 + 592
```
**۲۱ تست جدید.** یکی‌شان ثابت می‌کند مقادیر کش‌شده دقیقاً با محاسبهٔ مجدد
یکی‌اند — کشی که عدد متفاوت بدهد بدتر از نبودن کش است.

### بدهی صریح

**ماتریس آموزش هنوز از انبار پارکت نمی‌خواند.** کش لایهٔ
`FeatureComputationService` را پوشش می‌دهد (دکمهٔ Update features)، ولی
`build_feature_matrix` مستقل و در حافظه حساب می‌کند.

**چرا وصلش نکردم:** ماتریس مدل ویژگی‌های قیمتی را نسبت به close همان سطر
نرمال می‌کند (`is_price_scaled`)، انبار مقدار خام دارد. وصل‌کردن یعنی انتقال
منطق نرمال‌سازی و اگر اشتباه شود مدل روی مقیاس غلط آموزش می‌بیند — بی‌صدا.
فاز مستقل با تست تطابق بیت‌به‌بیت می‌خواهد.

**گزارش:** `PHASE38_REPORT.md`

---

## 2026-08-17 — فاز ۳۹: خواندن از انبار، تایم‌فریم روزانه، انتخاب مدل (باگ‌های ۲۹–۳۰)

**ورک‌اسپیس پاک و از گیت‌هاب کلون شد** (`f8bf0a9 Real Dataset`). دیتای واقعی
کاربر: XAUUSD 5M ۵۰٬۰۰۰ کندل (2025-11..2026-08) و 1H ۵۰٬۰۰۰ کندل
(2017-11..2026-08). **از این پس دیتا در zip تحویلی نیست.**

### ۱. خواندن از انبار + اثبات بایت‌به‌بایت

`build_feature_matrix` حالا پارامتر `source` دارد. فقط **از کجا** ستون‌ها
می‌آیند عوض می‌شود؛ مقیاس‌بندی نسبت به close، برش warm-up و tail در یک جا
می‌مانند و مشترک‌اند — همین ادعای «یکسان» را تست‌پذیر می‌کند.

روی دیتای واقعی 1H:
```
computed: 2897 x 123  in 3.31s
loaded  : 2897 x 123  in 1.59s   (2.1x)
BYTES identical : True   (2,850,648 bytes each)
```

**باگی که سر راه پیدا شد:** انبار `warmup` را ذخیره نمی‌کرد. `warmup` مقدار
نیست، تعداد سطرهای ابتدایی بدون مقدار صادقانه است، و ماتریس با آن تصمیم
می‌گیرد از کجا شروع شود. بدون آن، ماتریسِ خوانده‌شده **بی‌صدا** فرق می‌کرد.
حالا در metadata پارکت ذخیره می‌شود.

محافظ‌ها: اثر انگشت فاز ۳۸ · طول نامساوی · **timestamp جابه‌جا** (طول یکی،
کندل‌ها متفاوت — خطرناک‌ترین حالت) · کش ناقص → کل ماتریس دوباره حساب می‌شود
نه ستون کمتر.

### ۲. تایم‌فریم یک روزه

`domain/market/resample.py` + دکمهٔ **Build a higher timeframe**:
```
XAUUSD: 2,255 1D candles from 50,000 1H
  dropped: 2 incomplete buckets | continuity OK
  2017-11-16 O=1277.04 .. 2026-08-14 C=4376.25
```

دو قاعده: سطل ناقص دور ریخته می‌شود (آخرین «روز» معمولاً شش‌ساعته است و
high/low آن، high/low روز نیست)؛ سطل‌بندی بر تاریخ تقویمی UTC است نه شمارش،
پس آخر هفته جمعه را به دوشنبه نمی‌چسباند.

ویژگی‌ها: `1D: 109/109 over 2,255 candles`. دیتاست: `2152 rows x 123 cols`,
`source used: stored`.

**هر تایم‌فریم شناسهٔ مدل خودش را دارد** (`gold_range_1h` / `gold_range_1d`).
مشترک بودن یعنی آموزش دوم اولی را بازنویسی کند.

مدل رنج روزانه، آموزش واقعی:
```
val_mae 0.016225 → ~32.45 USD per bound on gold at 2,000
PREDICTION: close 4376.25 | high 4458.30 (+1.875%) | low 4315.72 (-1.383%) | R/R 1.36
```
**اولین مدل آموزش‌دیده روی قیمت واقعی طلا.**

### ۳. انتخاب مدل و دیتاست

فیلدهای `Model` (`all|range_1h|range_1d|signal|range|both`)،
`Range dataset(s)`، `Signal dataset`. خروجی صریح: `model id : gold_range_1d`
و `dataset : XAUUSD 1D`.

### ۴. چرا پاورشل چیزی چاپ نمی‌کرد — دو علت

روی دیتای واقعی بازتولید شد: **۲۰۸ ثانیه، صفر خط.**

**باگ ۲۹ — ۲۴٬۹۷۶ فولد.** `val_size=4, step=2` برای سری دموی چندصد سطری بود.
روی ۵۰k کندل هر فولد یک fit کامل است؛ این «کند» نیست، تمام نمی‌شود. حالا
هندسه با اندازهٔ دیتا مقیاس می‌گیرد: `val=999 step=999 → 49 فولد`.

**باگ ۳۰ — ۱۰ ثانیه سکوت قبل از اولین خط.** ساخت ۵۰k پنجره **قبل** از
`on_train_begin` بود. حالا اعلام می‌شود.

**پیشرفت درون epoch:** یک epoch روی ۵۰k نمونه هزاران batch است؛ حالا خط
batch با loss/mae/درصد در جا به‌روز می‌شود (`\r`).

**سازگاری:** قرارداد reporter بزرگ‌تر شد؛ reporter قدیمی هنوز معتبر است و
hook غایب رد می‌شود نه اینکه خطا بدهد — مشاهده نباید آموزش را بشکند.

### تأیید

```
black ✅ ruff ✅ mypy (292 files) ✅
pytest 1300 passed, 12 skipped   (قبلاً 1268)
RUN_TF=1  110 + 168 + 592 + 442
```
**۳۲ تست جدید.** سه تست قدیمی با دنیای سه‌تایم‌فریمی تطبیق داده شدند.

### بدهی صریح

مدل سیگنال 5M روی ۵۰k هنوز کند است (۴۹ فولد × ~۶٬۲۰۰ batch). مدل 1D فقط
۲٬۱۲۱ پنجره دارد و زیر-برازش می‌کند — `val_mae` ~۳۲ دلار روی طلای ۲۰۰۰ برای
معامله بزرگ است. صادقانه گزارش شده.

**گزارش:** `PHASE39_REPORT.md`

---

## 2026-08-17 — فاز ۴۰: منوهای کرکره‌ای + ذخیرهٔ واقعی مدل (باگ‌های ۳۱–۳۲)

**درخواست کاربر:** نوع مدل کرکره‌ای باشد؛ `Signal dataset` و
`Range dataset(s)` حذف شوند؛ یک منوی کرکره‌ای برای دیتاست‌های موجود؛ مدل با
نقش و دیتاستش ذخیره شود؛ Retrain از لیست مدل‌های ذخیره‌شده انتخاب کند. و:
ورک‌اسپیس از دیتای واقعی خالی شود.

### باگ ۳۱ — مدل هیچ‌وقت ذخیره نمی‌شد (بحرانی)

`run_dual_models.py` شبکه را آموزش می‌داد، پیش‌بینی چاپ می‌کرد و خارج
می‌شد. `datasets/models/` اصلاً وجود نداشت و هیچ `.bin`ی در پروژه نبود.
یعنی **هر اجرای آموزشی از فاز ۲۹ تا الان دور ریخته می‌شد** — از جمله همان
مدل رنج روزانه که روی دیتای واقعی `val_mae 0.0164` گرفت.

این را درخواست چهارم لو داد: لیست مدل‌های ذخیره‌شده همیشه خالی می‌ماند.

**رفع:** `save_model()` در اسکریپت + `ModelCatalogue` که کنار هر artifact
یک رکورد می‌نویسد (نقش، نماد، تایم‌فریم، سطرها، پنجره‌ها، سنجه‌ها، زمان).
`ModelArtifact.with_version()` هم اضافه شد تا آموزش مجدد نسخهٔ جدید بسازد
و قبلی را نگه دارد — artifactها تغییرناپذیرند.

### باگ ۳۲ — دکمهٔ Retrain در لحظهٔ فشردن کرش می‌کرد

`train_model` روی `CommandHandlers` بود ولی `_run_script` فقط روی
`AccountCommandHandlers`. یعنی `AttributeError` تضمینی. حالا
`AccountCommandHandlers` از `CommandHandlers` **ارث می‌برد** — تکرار مشکل
غیرممکن شد نه فقط رفع.

### منوهای کرکره‌ای

`CommandField` حالا `kind="select"` + `options` دارد و رندرر `<select>`
واقعی می‌سازد. `is_select` وقتی options خالی باشد False است — منوی خالی
انتخاب نیست، بن‌بست است، پس به text برمی‌گردد.

| منو | مقادیر |
|---|---|
| Model type | all · range · signal |
| Dataset | فقط آنچه در `processed/` هست |
| Saved model | فقط آنچه در `models/` هست |

`Signal dataset` و `Range dataset(s)` حذف شدند؛ تست جلوی برگشتشان را
می‌گیرد.

### رفتارهای عمدی در Retrain

نقش از **رکورد مدل** خوانده می‌شود نه از اسم فایل. اگر دیتاست انتخابی با
دیتاست اصلی فرق کند، **اجازه هست ولی هشدار می‌دهد** — عوض‌کردن ریتم بازاری
که مدل یاد گرفته، تصمیم کاربر است نه اشتباه.

### ورک‌اسپیس تمیز

دیتای واقعی پاک شد (روی گیت‌هاب امن است: `3b10dca 1D Features`). جایش
`scripts/make_test_data.py` که ۶۰۰ کندل مصنوعی زیر **`TESTSYM`** می‌سازد —
نه XAUUSD و نه هیچ alias آن. تست ثابت می‌کند `TESTSYM` در
`alias_candidates("XAUUSD", profile)` نیست، و تست دیگری کد اسکریپت را
(نه docstringش را) از نام نماد واقعی پاک نگه می‌دارد.

### تأیید

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1330 passed, 12 skipped   (قبلاً 1300)
RUN_TF=1  278 + 472 + 592
```
**۳۰ تست جدید.** سه تست قدیمی با نام‌های جدید تطبیق داده شدند.

زنده: آموزش → `SAVED gold_range_1d v1` → Retrain از داشبورد → `v3` با v1 و
v2 دست‌نخورده. `data files in zip: 0`.

### بدهی صریح

`model_id` نماد را در بر نمی‌گیرد، پس آموزش یک مدل روی TESTSYM و بعد روی
XAUUSD دو **نسخه** می‌سازد نه دو مدل. برای چند-نمادی شدن باید اصلاح شود.

**گزارش:** `PHASE40_REPORT.md`

---

## 2026-08-17 — فاز ۴۱: رفع OOM آموزش (باگ ۳۳)

**گزارش کاربر:** «Running: train_dual_models 492s / waiting for the first
line ... رم سیستمم تا خرخره پر میشه، هیچ مدلی هم ذخیره نشد.»

هر سه علامت **یک علت** داشتند.

### باگ ۳۳ — ۱۲.۲ گیگابایت تخصیص قبل از اولین batch

```
49,393 windows × 500 rows × 123 cols × 4 bytes = 12.2 GB
ماتریس تخت اصلی                                 =   25 MB
```

`build_multi_target_samples` همهٔ پنجره‌ها را در ابتدای `train()` می‌ساخت —
قبل از اولین batch و قبل از اولین `print`. ماشین در همان فاصله می‌مرد، که
توضیح می‌دهد چرا رم پر می‌شد **و** لاگ خالی می‌ماند **و** مدلی ذخیره
نمی‌شد: `save_model()` هرگز اجرا نمی‌شد.

در سندباکس با OOM killer اثبات شد (`EXIT=137`).

**نکتهٔ تلخ:** فاز ۳۰ `WindowGenerator` تنبل را دقیقاً برای همین ساخت، با
تست و مستندات، و هیچ‌وقت به trainer وصل نشد.

### رفع

فولدهای بالای ۵۱۲ MB از همان ماتریس ۲۵ مگابایتی استریم می‌شوند
(`tf.data`). وقتی استریم فعال است لیست نمونه‌ها **اصلاً ساخته نمی‌شود**؛
`_LazySampleCount` جایش می‌نشیند که فقط تعداد را می‌دهد و ایندکس‌شدن را رد
می‌کند — مسیری که هنوز استریم را نمی‌شناسد ساکت نمی‌ماند.

اندازه‌گیری: **۴.۸ GB → ۹۶۶ MB peak** روی ۲۰٬۰۰۰ سطر، دو epoch.

**باگ فرعی:** `from_generator` بعد از یک pass تمام می‌شود، پس epoch دوم
خالی بود. با `repeat()` + `steps_per_epoch` رفع شد.

### گزارش هزینه قبل از شروع

```
  windows        : 429 of 64 x 123
  if materialised: 0.0 GB  (streamed instead when large)
```

و پنجرهٔ بزرگ‌تر از دیتا فوراً رد می‌شود نه بعد از هشت دقیقه:
`[X] Not enough data: 497 rows cannot make a single 500-row window.`

### تأیید

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1340 passed, 12 skipped   (قبلاً 1330)
RUN_TF=1  110 + 168 + 482 + 592
```
**۱۰ تست جدید.** ذخیرهٔ مدل زنده تأیید شد: `SAVED gold_range_1d v1`.

### بدهی

استریم کندتر از حافظه است وقتی هر دو جا می‌شوند؛ آستانهٔ ۵۱۲ MB
محافظه‌کارانه است. و پنجرهٔ ۵۰۰ روی 5M هنوز ساعت‌ها طول می‌کشد — حافظه حل
شد، زمان نه.

**گزارش:** `PHASE41_REPORT.md`

---

## 2026-08-17 — فاز ۴۲: خطوط epoch بالاخره به مرورگر می‌رسند (باگ‌های ۳۴–۳۵)

**کاربر برای سومین بار:** «نه توی پاورشل نه توی وب هیچی از روند آموزش
نمی‌بینم که هر epoch دقت و خطا چقدر تغییر کرده.»

این بار خطوط **تولید می‌شدند** و به فایل لاگ **می‌رسیدند** — و در آخرین قدم
دور ریخته می‌شدند.

### باگ ۳۴ — سیل batch نتایج را بیرون می‌انداخت

هر batch یک خط. داشبورد فقط ۲۰۰ خط آخر را می‌خواند. اندازه‌گیری روی یک
اجرای کوچک: ۳۱۶ خط batch در لاگ، و از ۲۰۰ خط قابل نمایش، **۱۵۸ تا batch**
بودند و فقط ۳ خط epoch. روی دیتای بزرگ‌تر کاربر، ۲۰۰ خط آخر کلاً batch
بودند و هیچ epoch‌ای باقی نمی‌ماند.

### باگ ۳۵ — `\r` از داخل pipe رد نمی‌شود

خط پیشرفت با `\r` نوشته می‌شد تا در جا به‌روز شود؛ این فقط روی ترمینال
کار می‌کند. از داخل pipe به فایل، `\r` فقط یک کاراکتر است، پس هر
به‌روزرسانی یک خط دائمی جدید می‌شد — که سیل باگ ۳۴ را چند برابر کرد.

### رفع

حداکثر **۸ خط پیشرفت در هر epoch** (`BATCH_LINES_PER_EPOCH`)، با فاصلهٔ
یکنواخت و همیشه خط ۱۰۰٪ — چون تمام‌شدن روی ۹۴٪ شبیه گیرکردن است.
`316 → 60` خط.

`\r` حذف شد. و `read_run_log` هوشمند شد: وقتی لاگ از پنجره بزرگ‌تر است،
اول خطوط نتیجه (epoch/fold/val_loss/SAVED/خطاها) نگه داشته می‌شوند و
batchها رقیق می‌شوند. تازه‌ترین خطوط همیشه می‌مانند.

### تأیید زنده از HTTP داشبورد

```
[12s] busy=True lines=46  epochs=1
[24s] busy=True lines=81  epochs=4
[36s] busy=True lines=148 epochs=7
```

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1354 passed, 12 skipped   (قبلاً 1340)
```
**۱۴ تست جدید**، یکی‌شان ثابت می‌کند با ۲٬۴۰۰ خط batch هر شش خط epoch
دیده می‌شوند.

**گزارش:** `PHASE42_REPORT.md`

---

## 2026-08-18 — فاز ۴۳: رفع کرش «The dataset is infinite» (باگ ۳۶)

**کرش کاربر** روی دیتاست واقعی 5M (۴۷٬۸۸۶ پنجره)، بعد از ۱۴۵ ثانیه:
`TypeError: The dataset is infinite.` در `len(train_x)`.

### باگ ۳۶ — که خودم در فاز ۴۱ ساختم

زنجیره: فاز ۴۱ فولدهای بزرگ را استریم کرد → برای پرنشدن epoch دوم
`repeat()` شد → دیتاست بی‌نهایت شد → ولی callback پیشرفت هنوز
`len(train_x)` می‌پرسید → کرش.

**چرا ندیدمش:** مسیر استریم را با `NullProgressReporter` تست کردم که این
callback را اصلاً نمی‌سازد. یعنی مسیری که کاربر واقعاً اجرا می‌کند تست
نشده بود. تست جدید عمداً با `ConsoleProgressReporter` اجرا می‌شود.

**رفع:** تعداد batch از هندسهٔ fold می‌آید نه از دیتاست —
`train_steps` از قبل محاسبه شده بود و فقط استفاده نمی‌شد.
`len(train_x)` و `len(val_x)` حذف شدند.

### تأیید

بازتولید روی همان مسیر استریم (۲۰k سطر، پنجرهٔ ۵۰۰):
```
[####################] 100.0% | batch 594/594 | loss 0.0052 | mae 0.0022
epoch 1/1 | loss 0.0052 | val_loss 0.0033
NO CRASH. peak RSS 966 MB
```
و از داشبورد: `succeeded | Trained range on 1D` + مدل ذخیره شد.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1361 passed, 12 skipped   (قبلاً 1354)
```
**۷ تست جدید**، یکی‌شان با `ast` پارس می‌کند تا `len()` هرگز روی متغیر
دیتاست صدا زده نشود.

**گزارش:** `PHASE43_REPORT.md`

---

## 2026-08-18 — فاز ۴۴: سرعت و خوانایی آموزش (باگ‌های ۳۷–۳۸)

**لاگ کاربر** نشان داد کرش فاز ۴۳ رفع شده و آموزش شروع شده — ولی همان یک
خط دو مشکل را لو داد:
`[----] 0.0% | batch 1/5,986 | loss 1.5662`

### باگ ۳۷ — batch_size=8 روی ۴۷٬۸۸۶ پنجره

عدد ۸ برای سری دموی چندصد سطری بود. روی دیتای واقعی یعنی **۵٬۹۸۶ قدم
گرادیان** برای یک epoch، هرکدام forward+backward روی ورودی ۵۰۰×۱۲۳.

رفع: مقیاس‌گیری با حجم دیتا (مثل کاری که فاز ۳۹ با foldها کرد) —
۲۰k+ سطر → bs=64، یعنی **۷۴۸ قدم به‌جای ۵٬۹۸۶** (۸ برابر کمتر).

### باگ ۳۸ — ۱۱ دقیقه سکوت بین دو خط پیشرفت

۸ خط در هر epoch ÷ ۵٬۹۸۶ batch = خطی هر ۷۴۸ batch ≈ ۱۱ دقیقه. یازده
دقیقه سکوت همان «هنگ کرده» است — دقیقاً شکایتی که این گزارشگر برای رفعش
ساخته شد.

رفع: کف زمانی `MAX_SECONDS_BETWEEN_LINES = 30`. حداقل هر ۳۰ ثانیه یک خط،
فارغ از تعداد batch. به‌علاوه ETA اضافه شد (روی batch اول چاپ نمی‌شود چون
هنوز چیزی برای برون‌یابی نیست).

### نکتهٔ صادقانه دربارهٔ سرعت

در سندباکس: bs=8 → 511s، bs=64 → 542s. **تقریباً یکسان**، چون CPU سندباکس
AVX2/FMA ندارد. لاگ کاربر می‌گوید CPU او دارد، پس انتظار ۳-۶ برابر می‌رود
— ولی **اندازه‌گیری نشده و تضمین نمی‌شود**. آنچه قطعی است: قدم‌ها
۵٬۹۸۶→۷۴۸، خطوط ۸→۲۰، سکوت ۱۱دقیقه→۳۰ثانیه.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1373 passed, 12 skipped   (قبلاً 1361)
```
**۱۲ تست جدید.**

**گزارش:** `PHASE44_REPORT.md`

---

## 2026-08-18 — فاز ۴۵: آستانهٔ سیگنال در فرم + اسپرد واقعی (باگ ۳۹)

**درخواست کاربر:** آستانه را در گزینه‌ها بگذار با واحد درصد؛ و اسپرد را در
ترید آنلاین از خود متاتریدر بگیر چون شناور است.

### باگ ۳۹ — اسپرد ۴ دلاری hard-code شده، ضررده

`live_decision_service.py` مقدار `spread=Decimal("4")` داشت. روی طلای
۴٬۳۷۶ این ۰.۰۹۱٪ است، ولی آستانهٔ پیش‌فرض سیگنال ۰.۰۸٪:

```
سیگنال BUY = +3.50 USD  |  اسپرد = -4.00 USD  |  خالص = -0.50 USD
```

یعنی مدل آموزش می‌دید حرکت‌هایی را شکار کند که قبل از شروع ضررده بودند.
سؤال کاربر دربارهٔ شناوربودن اسپرد این را لو داد.

**رفع:** `Mt5MarketDataProvider.live_quote(symbol)` که `ask - bid` را از
تیک زنده می‌خواند — نه `symbol_info.spread` که عدد صحیح در واحد point و
فقط snapshot است. عدد صحیح برای تشخیص کنارش برگردانده می‌شود.

شکست هرگز تیک را نمی‌شکند: نبود تیک / بازار بسته / اسپرد ≤۰ همه به
fallback ۰.۳۵ دلاری می‌روند و `last_spread_source` علت را ثبت می‌کند.
نبود اسپرد مشکل داده است نه دلیل توقف منطق معاملاتی.

### آستانه به درصد

`Signal threshold %` در هر دو دکمهٔ Train و Retrain. فرم درصد می‌گوید
(`0.08`)، کد کسر می‌خواهد (`0.0008`)، تبدیل یک‌جا در
`percent_to_fraction`. ورودی غلط به پیش‌فرض برمی‌گردد نه خطا.

خروجی آموزش حالا قاعده را صریح می‌گوید:
`label rule: a move of more than 0.1500% over 5 candles is BUY/SELL`

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1395 passed, 12 skipped   (قبلاً 1373)
```
**۲۲ تست جدید**، یکی‌شان مطمئن می‌شود `spread=Decimal("4")` برنگردد.

### بدهی

اسپرد فقط در حلقهٔ زنده استفاده می‌شود نه بک‌تست (`run_backtest.py` هنوز
`--spread 4.0` دارد). آستانه در `ModelRecord` ذخیره نمی‌شود. و
`live_quote` روی متاتریدر واقعی تست نشده — فقط با MT5 قلابی.

**گزارش:** `PHASE45_REPORT.md`

---

## 2026-08-18 — فاز ۴۶: نجات کار آموزش از timeout (باگ‌های ۴۰–۴۲)

**گزارش کاربر:** `FAILED · 7205.5s · Timed out after 120 minutes` بعد از
۱۸ epoch کامل — و هیچ مدلی ذخیره نشده بود.

مهم: `val_acc` از ۰.۷۹۵۴ به ۰.۷۹۹۴ و `val_loss` از ۰.۵۳۱۴ به ۰.۵۲۷۹ رفته
بود. مدل **هنوز در حال یادگیری بود**، نه بیش‌برازش. آموزش درست کار می‌کرد
و فقط وقت کم آورد.

### باگ ۴۰ — هیچ چیز تا پایان train() ذخیره نمی‌شد (بحرانی)

`save_model()` بعد از بازگشت `train()` اجرا می‌شد، پس هر وقفه‌ای همه‌چیز را
دور می‌ریخت. رفع: checkpoint بعد از **هر epoch**.

اثبات با کشتن عمدی اجرا: `KILLED (exit=124)` و مدل روی دیسک ماند با
`"note": "checkpoint after epoch 8/20"`.

checkpoint عمداً یک نسخه را بازنویسی می‌کند نه بیست‌تا — طناب نجات است نه
تاریخچه. و اگر خودش شکست بخورد آموزش را قطع نمی‌کند.

### باگ ۴۱ — ETA حدود ۴۵ برابر غلط

`eta 2:58:40` وقتی ۴ دقیقه مانده بود. زمان کل **fold** بر batchهای **epoch
جاری** تقسیم می‌شد؛ در epoch نوزدهم fold دو ساعت کار کرده بود. ETA‌ای
این‌قدر غلط بدتر از نبودنش است. رفع: اندازه‌گیری از ابتدای همان epoch.

### باگ ۴۲ — timeout دو ساعتهٔ ثابت

`timeout=7200` در کد. اجرای کاربر ۲.۲ ساعت لازم داشت. رفع: فیلد
`Give up after (minutes)` با پیش‌فرض ۴۸۰، و پیام timeout که می‌گوید
`(any completed epoch was checkpointed)`.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1407 passed, 12 skipped   (قبلاً 1395)
```
**۱۲ تست جدید**، از جمله کشتن واقعی یک اجرا و بررسی بقای مدل.

### بدهی

checkpoint وزن‌ها را نگه می‌دارد نه وضعیت optimizer، پس ادامه از epoch ۱۸
ممکن نیست — فقط Retrain از مدل ذخیره‌شده.

**گزارش:** `PHASE46_REPORT.md`

---

## 2026-08-18 — فاز ۴۷: بهترین مدل نگه داشته می‌شود نه آخرین (باگ ۴۳)

**سؤال کاربر:** «مدلای آموزشی آخرین مدل رو ذخیره میکنن یا بهترین مدل رو؟»

جواب صادقانه: **آخرین**. و این یک ضعف واقعی بود.

### باگ ۴۳ — بیش‌برازش‌شده‌ترین وزن‌ها ذخیره می‌شد

```python
last_model = model                    # هر fold، بدون شرط
payload = _serialize_model(last_model)
```

`loss` آموزش تقریباً همیشه کاهش می‌یابد ولی `val_loss` پایین می‌آید، به کف
می‌رسد و بعد بالا می‌رود. پس «هرچه آخر اجرا شد» یعنی بیش‌برازش‌شده‌ترین
وزن‌های اجرا.

اندازه‌گیری روی دیتای تست:
```
epoch  5: val_loss 0.8055 | val_acc 72.7%   ← بهترین
epoch 12: val_loss 0.8969 | val_acc 63.6%   ← قبلاً این ذخیره می‌شد
```
**۹ واحد دقت دور ریخته‌شده به‌خاطر یک انتساب متغیر.**

### رفع

checkpoint فقط وقتی می‌نویسد که `val_loss` بهبود یافته باشد، و هر epoch
می‌گوید چه شد:
```
[BEST so far] epoch 5/12 val_loss 0.805476 — saved as v1
[epoch 6/12] val_loss 0.894731 — no better than 0.805476 (best is epoch 5)
```

`val_loss` داور است نه `val_accuracy`: دقت روی مسئلهٔ سه‌کلاسه پله‌ای است و
مدام مساوی می‌شود (سه بار ۶۳.۶٪ پشت‌هم)، ولی loss هر بهبود کوچک در اطمینان
را ثبت می‌کند. مدل رنج از `val_mae` استفاده می‌کند.

و `save_model()` نهایی دیگر وزن‌های آخرین epoch را به‌عنوان نسخهٔ **جدید**
نمی‌نویسد — قبلاً دو مدل روی دیسک می‌ماند و بدتره بالای منوی کرکره‌ای
می‌نشست:
```
KEPT gold_signal_5m v1 from epoch 5 (val_loss 0.805476)
  the final epoch scored 0.896911 — worse, so it was NOT written over the best
```

### دربارهٔ اجرای دو ساعتهٔ کاربر

چیزی از دست نرفت: `val_loss` از ۰.۵۳۱۴ به ۰.۵۲۷۹ هنوز در حال بهبود بود،
پس «آخرین» همان «بهترین» بود. ولی اگر از epoch ۱۹ بدتر می‌شد، با کد قدیم
مدل بدتر می‌ماند.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1415 passed, 12 skipped   (قبلاً 1407)
```
**۸ تست جدید** از جمله منحنی کلاسیک بیش‌برازش. یک تست فاز ۴۶ هم به‌روز شد
(فقط متن یادداشت عوض شده، رفتار سالم است).

### تأیید هر دو نقش

کاربر پرسید آیا برای هر دو مدل انجام شده. هر دو از یک `train_one`
استفاده می‌کنند، ولی با همان منحنی بیش‌برازش هر دو آزموده شدند:
signal با `val_loss` و range با `val_mae` — هر دو epoch ۳ را نگه داشتند
و ۴–۶ را رد کردند.

**نقصی که همین آزمون لو داد:** برچسب لاگ همیشه `val_loss` می‌گفت حتی
برای مدل رنج. رفع شد؛ حالا `metric_name` نام درست را می‌برد.

### بدهی

توقف زودهنگام نداریم: ۲۰ epoch بدهی هر ۲۰ اجرا می‌شود حتی اگر از ۵ به بعد
بدتر شود — بهترین نگه داشته می‌شود ولی وقت تلف می‌شود.

**گزارش:** `PHASE47_REPORT.md`

---

## 2026-08-18 — فاز ۴۸: تست مدل، بازرسی دیتاست، نقشهٔ شبکه (باگ ۴۴)

**سه درخواست کاربر:** بخشی برای تست مدل انتخابی روی دیتاست انتخابی با
ذخیرهٔ نتیجه در لاگ؛ بخشی برای دیدن ساختار دیتاست و ابعاد ماتریس؛ و نمایش
ابعاد ماتریس + ذخیرهٔ PNG معماری در ابتدای هر آموزش. به‌علاوه: تمیزکاری
ورک‌اسپیس.

### تمیزکاری: 129M → 73M

### باگ ۴۴ — آرشیو اسنپ‌شات بی‌نهایت رشد می‌کرد

`_archive_previous()` هر اجرا یک اسنپ‌شات می‌ساخت و هیچ‌وقت پاک نمی‌کرد.
بعد از ۱۵۸ اجرا: ۴۸ مگابایت، یک‌سوم کل ورک‌اسپیس، از فایل‌های تقریباً
یکسانی که کسی نخوانده بود. رفع: `ARCHIVE_KEEP = 5`.

دیتای واقعی XAUUSD دست نخورد — با `git status` تأیید شد هیچ فایل
track‌شده‌ای حذف نشده. فقط untracked‌ها (مدل و دیتای مصنوعی TESTSYM،
`shadbot.db`، `out.html`، کش‌ها) پاک شدند.

### ۱. تست مدل (`ModelEvaluationService`)

دکمهٔ **Test a model on a dataset**: منوی مدل‌های ذخیره‌شده + منوی
دیتاست‌های موجود. سه تصمیم عمدی: آموزش اتفاق نمی‌افتد (وزن‌ها منجمد)؛
پنجره‌ها دقیقاً مثل آموزش ساخته می‌شوند (وگرنه عدد مدلی را توصیف می‌کند که
وجود ندارد)؛ و اگر روی همان تایم‌فریمِ آموزش تست شود صریح هشدار می‌دهد.

نتیجه در `run_logs/evaluations.jsonl` **append** می‌شود نه overwrite —
مقایسه بی‌ارزش است اگر عدد دیروز پاک شده باشد. مدل سیگنال `accuracy`
به‌همراه baseline کلاس غالب می‌دهد.

### ۲. بازرسی دیتاست

دکمهٔ **Inspect a dataset**: تعداد کندل، بازهٔ زمانی و قیمتی، ابعاد
ماتریس، شکل تانسور ورودی، تفکیک ستون‌ها (۸ خام + ۶ شکل + ۱۰۹ فیچر)،
digest و ستون‌های ثابت.

### ۳. ماتریس و PNG در هر آموزش

`describe_input_matrix()` اول هر اجرا چاپ می‌شود، و
`save_model_diagram()` یک بار در هر اجرا PNG می‌سازد. سه‌مرحله‌ای چون
graphviz معمولاً روی ویندوز نیست: `plot_model` → Pillow → فایل متنی. هر
کدام که شد آموزش ادامه می‌یابد و منبعش اعلام می‌شود.

**باگ ریز:** کراس جدولش را با box-drawing می‌کشد و فونت پیش‌فرض Pillow
آنها را مربع خالی نشان می‌داد؛ به ASCII تبدیل شد.

```
black ✅ ruff ✅ mypy (295 files) ✅
pytest 1441 passed, 12 skipped   (قبلاً 1419)
```
**۲۲ تست جدید.** تست زندهٔ داشبورد: هر چهار دکمه رندر و اجرا شدند.

### بدهی

ارزیابی سیگنال آستانه را از رکورد مدل نمی‌خواند (۰.۰۸٪ ثابت فرض می‌شود)،
پس مدلی که با ۰.۱۵٪ آموزش دیده دقتش کمتر از واقع گزارش می‌شود.

**گزارش:** `PHASE48_REPORT.md`

---

## قدم بعدی توافق‌شده

**C — اتصال به دیتای واقعی MetaTrader 5.**

کاربر گفت «باشه بریم». کار سمت سندباکس (لینوکس) تمام است؛ ادامه‌اش نیازمند
اجرای کاربر روی ویندوز است:

```powershell
pip install -r requirements-mt5.txt
shadbot-data mt5-check
shadbot-data mt5-symbols --pattern XAU
python scripts\run_real_data.py --symbol XAUUSD
```

⚠️ نام نماد بین بروکرها فرق دارد: `XAUUSD`, `XAUUSD.i`, `XAUUSDm`, `GOLD`.
اگر فهرست خالی بود: در MT5 → Market Watch → راست‌کلیک → **Show All**.

**بعد از آن:** A (وصل‌کردن WaveNet به بک‌تست) سپس B (فاز ۲۴ Deployment).

---

## 2026-08-26 — فاز ۵۹: اصلاح هندسهٔ اعتبارسنجی (val ۲٪ → ۱۰٪ استخر + گارد)

**گزارش کاربر:** «اشتباهی توی ساخت دیتای ولید داری» — با train-ratio 80%
لیبل ولید ۱۴۰ تا می‌شد؛ با 20% فقط ۳۴ تا. علت: `val_size = max(4, min(2000,
rows // 50))` روی **استخر لیبل‌دار** حساب می‌شد (۲٪) و استخر هم تابع
train-ratio است → val همیشه کوچک و وابسته.

### رفع

- `build_trainer`: پیش‌فرض `rows // 10` (۱۰٪ استخر، کف ۴، سقف 2000) + گارد
  `max(4, min(val, rows - min_train - purge - 4))` که اولین fold را روی
  سری‌های کوچک زنده نگه می‌دارد.
- `DualModelService.train()`: پارامتر جدید `val_size` (0 = auto) به
  `build_trainer` پاس می‌شود.
- `run_dual_models.py`: آپشن‌های `--val-size` / `--val-ratio` + خط چاپ
  `val fold size : N samples per fold (X% of M labelled windows)`؛ تابع
  آینهٔ label-balance همان هندسه را اعمال می‌کند.
- اثر روی اجراهای واقعی: 140→~700 (80%) · 123→615 (70%) · 34→~174 (20%).

### چرا

گیت انتخاب بهترین مدل (فاز ۴۷) با val=34-123 عملاً روی نویز تصمیم
می‌گرفت؛ با ~615 نمونه، val_acc به ±1.9% معنادار می‌شود.

### پیامد آگاهانه

چند صد نمونهٔ کمتر برای train (Expanding): ~۱۶٪ در اجرای ۷۰٪ — برای
اعتبارِ انتخابِ بهترین، قابل قبول. `--val-size` برای کنترل دستی.

### تست

`tests/unit/ai/test_validation_geometry.py` — ۴ تست جدید (۱۰٪ پیش‌فرض،
عبور val صریح، گارد سری کوچک، امضای train).

```
ruff ✅ black ✅ mypy (فایل تغییر یافته ✅؛ ۳ خطای TF-محیطی در wavenet_trainer به‌خاطر نبود TF در سندباکس)
pytest 1456 passed, 49 skipped (قبلاً 1449 + ۴ تست جدید)
```

**گزارش:** `Report/PHASE59_REPORT.md`

---

## 2026-08-26 — فاز ۶۰: اتصال ReduceLR + EarlyStopping به مدل سیگنال (باگ سیم‌کشی) + baseline صحیح

**کشف از اجرای ۱۰.۵ ساعتهٔ signal v1 کاربر:** بهترین epoch همهٔ فولدها
10/13/16/19 بود ولی هر ۴ فولد تا epoch 60 کامل اجرا شد → ~۷ ساعت epochهای
نامنتخاب‌پذیر. علت: `build_trainer` برای classification `loss=None` می‌فرستاد
و گیتِ `if self._loss in (…)` در trainer هرگز match نمی‌شد → ReduceLROnPlateau
(فاز ۵۴) و EarlyStopping (فاز ۵۷) فقط به range وصل بودند، هرچند گزارش‌ها
«هر دو مدل» را ادعا می‌کردند.

### رفع

- `dual_model_service.build_trainer`: `loss=role.loss, metric=role.metric`
  همیشه (کامپایل مدل بدون تغییر — شاخهٔ classification همان loss را
  hard-code دارد؛ فقط گیت callbacks حالا match می‌شود).
- `run_dual_models.print_quality`: پارامتر `val_baseline` — حکم با
  baselineِ **فولد آخرِ ولید** (در اجرای مذکور 65.2% sell در برابر 50.3%
  استخر!) + اعلام صریح رژیم‌جابه‌جایی فولد.

### تست

۲ تست جدید در `test_validation_geometry.py`: سیم‌کشی loss سیگنال +
حفظ huber برای range.

```
ruff ✅ black ✅
pytest 1458 passed, 49 skipped   (قبلاً 1456)
```

**اثر مورد انتظار:** با ES patience=12، اجرای signal حدود نصف زمان قبلی؛
ReduceLR احتمالاً کالیبراسیون را بهتر می‌کند.

**گزارش‌ها:** `Report/PHASE60_REPORT.md` · `Report/SIGNAL_V1_FULLRUN_REVIEW_2026-08-26.md`

---

## 2026-08-27 — فاز ۶۱: پیچ‌های معماری (--n-layers/--n-blocks) + چاپ RF

**پرسش کاربر** «window=150 اوکیه؟» لو داد که `--window` فقط اندازهٔ پنجره
را عوض می‌کند و RF پیش‌فرض فاز ۵۸ (249) بزرگ‌تر از پنجره می‌شد (166%).

### رفع

- factoryهای `signal_model_role`/`range_model_role`: پارامترهای اختیاری
  `n_layers_per_block`/`n_blocks` (None = پیش‌فرض).
- تابع `receptive_field()` — فرمول RF با تست (249/121/125/57).
- CLI: `--n-layers` / `--n-blocks` + خط چاپ `architecture : window=… · L×B · RF=… (X% of window)`
  + هشدار صریح وقتی RF > window.

### تست

۶ تست جدید (`test_model_roles_knobs.py`). پیش‌فرض‌های فاز ۵۸ قفل شدند.

```
ruff ✅ black ✅
pytest 1464 passed, 49 skipped   (قبلاً 1458)
```

**گزارش:** `Report/PHASE61_REPORT.md`

---

## 2026-08-27 — فاز ۶۲: پیچ‌های ۵۹/۶۱ در GUI

سه مسیر داشبورد (Train a model · Retrain · Find best LR) حالا
`--n-layers`/`--n-blocks`/`--val-size` را می‌فرستند؛ 0 = پیش‌فرض/auto و
فلگ ارسال نمی‌شود. فرم‌ها hint فارسی RF دارند. ۷ تست جدید.

```
ruff ✅ (۱۰ خطای قدیمی handlers.py جدا شده) black ✅
pytest 1471 passed, 49 skipped   (قبلاً 1464)
```

**گزارش:** `Report/PHASE62_REPORT.md`

---

## 2026-08-27 — فاز ۶۳: باگ ۴۷/۴۸ — برچسب‌های seq2seq رنج خراب بودند

**کشف از لاگ کاربر (range 1D):** val_mae 0.000081 (±$0.16!) هم‌زمان با
per-bound 0.0024/0.0058 و bias≡±MAE (هر ۴۴۸ خطا هم‌علامت). ردیابی کد:
`WindowedSample.target_index` = شماره ستون (182) ولی
`_build_seq2seq_targets` آن را اندیس سطر می‌خواند → y همهٔ نمونه‌ها از
سطرهای ثابت ۳۳..۱۸۲ → collapse + metric جعلی. توضیح val_maeهای تاریخی
غیرواقعی (0.000010 فاز ۵۷) و بی‌فایده بودن بکتست‌های رنج.

### رفع

- سه سازندهٔ sample: `target_index=end` (سطر پایان پنجره)
- `_range_validation_metrics`: شاخهٔ seq2seq → آخرین timestep
- ۴ تست رگرسیون + تمیزکاری lint trainer

```
ruff ✅ black ✅  pytest 1475 passed, 49 skipped
```

**پیامد:** همهٔ آرتیفکت‌های range (تاریخی v1-v3 و این اجرا) باطل — retrain
بعد از این فیکس لازم است. signal آسیب ندیده (مسیرش target_index نمی‌خواند).

**گزارش:** `Report/PHASE63_REPORT.md`

---

## 2026-08-27 — فاز ۶۴: باگ ۴۹ — برش last_n، رنج را گرسنه می‌کرد (trades=0)

اولین بکتست دومدلیِ واقعی: مدل‌ها سالم، trades=0. ریشه: handler کندل‌های
1D را با cutoff پنجرهٔ 5M می‌برید (۹٬۰۰۰×5M ≈ ۳۱ روز → ~۳۰ کندل 1D <
window=150 → abstain همیشگی). علیت را خود prediction source enforce
می‌کند؛ برش حذف شد + خط «range candles: N (1D)» به گزارش + ۳ تست.

```
pytest 1478 passed, 49 skipped
```

**گزارش:** `Report/PHASE64_REPORT.md`

---

## 2026-08-27 — فاز ۶۵: نقاط انتخاب سیگنال روی ریپلی (درخواست اپراتور)

SignalMarker جدید (candidate/filled/rejected · BUY ▲ سبز / SELL ▼ قرمز ·
توپر=ترید شد، توخالی=رد شد) + resolution claim-based در build() + خط
legend با شمارش. engine فقط actionableها را ثبت می‌کند و ردِ براکت در
next-open را با دلیل به rejected تبدیل می‌کند. + cleanup lint (F821/E741 قدیمی).

```
ruff ✅ black ✅  pytest 1483 passed, 49 skipped
```

**گزارش:** `Report/PHASE65_REPORT.md`

---

## 2026-08-27 — فاز ۶۶: TP/SL مدل کنار نقاط سیگنال ریپلی

SignalMarker +tp/sl (سطح مطلق) · engine از range forecast (BUY: high/low،
SELL برعکس) · بعد از fill واقعی next-open، سطوح براکت (با spread) جایگزین ·
رندر: خط‌چین سبز/قرمز + اتصال نقطه‌دار + قیمت در زوم · legend +۲ · ۳ تست.

```
pytest 1485 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۶۷: باگ ۵۰ — بافر 1D از تاریخچه پیش‌پر نمی‌شد

گزارش اپراتور: مثلث‌ها هستن، TP/SL رسم نمیشه. ردیابی با شبیه‌سازی:
بافر 1D فقط با observe پر می‌شد → برای اولین رنج باید ۱۵۰ روز *داخل*
replay می‌گذشت (۹٬۰۰۰×5M=۳۱ روز → هرگز). رفع: pre-fill کندل‌های 1D
بسته‌شده قبل از اولین 5M از همان تاریخچه (cursor جلو تا observe تکرار
نکند). عددی تأیید شد: 0 → 151 پیش‌بینی رنج. ۲ تست جدید.

```
pytest 1487 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۶۸: برچسب build در گزارش بکتست (درسِ اجرای با کد قدیمی)

بکتست کاربر هنوز «range candles: n/a» چاپ می‌کرد = با کد قدیمی اجرا شده بود
(زیپ جدید جایگزین نشده بود یا سرور ری‌استارت نشده بود). رفعِ ریشه‌ایِ ابهام:
خط `build : phase-67 (…)` به گزارش بکتست اضافه شد — اپراتور با یک نگاه
می‌بیند با کد چندم اجرا می‌کند.

```
pytest 1487 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۶۹: شمارش سیگنال/رنج/خطاها در گزارش بکتست

بعد از فازهای ۶۵-۶۷ هنوز نمی‌شد فهمید در بکتست واقعی: چند سیگنال
actionable بوده؟ رنج چند بار اجرا شده؟ خطای خاموشی بوده؟ سه تغییر:
1. `BacktestResult.source_stats` — stats منبع پیش‌بینی روی نتیجه
2. شمارش خطاها با type+پیام در source (`error_counts`) + `errors` در stats
3. گزارش بکتست: خط جدید `signals seen: N · range ran: M · abstains: K`
   + هر خطای تکرارشده با `[err xN]`
+ رفع: `_last_range_feed` در مسیر dual هم ست می‌شد (قبلاً فقط legacy →
  «range candles» همیشه n/a می‌ماند)

```
pytest 1487 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۷۰: باگ ۵۱ — کلاس‌های _RangeLoss/_Seq2SeqMAE ماژول‌سطح شدند

**گزارش اپراتور (ابزار فاز ۶۹ کار کرد):**
`signals seen: 811 · range ran: 0 · [err x811] range: TypeError: Could not
locate class '_RangeLoss'` — رنج هرگز اجرا نشده بود؛ خطاها خاموش بودند.

### ریشه

کلاس‌های `_RangeLoss` و `_Seq2SeqMAE` **داخل تابع** `_build_compiled`
تعریف می‌شدند (local class). `@register_keras_serializable` آنها را در
registry keras ثبت می‌کرد ولی `custom_objects()` با `getattr(ماژول, نام)`
هرگز نمی‌توانست ببیندشان → `load_model` هر مدل رنج شکست می‌خورد. signal
مستقل از این مسیر است (SparseCategoricalCrossentropy استاندارد) — برای
همین سیگنال کار می‌کرد و فقط رنج می‌شکست.

### رفع

- کلاس‌ها به سطح ماژول منتقل شدند (lazy build با `_build_range_classes`).
- `range_custom_objects()`: همهٔ نام‌های تاریخی (`RangeLoss`،
  `_RangeLoss`، `ShadBotTrader>…`، …) را یک‌جا می‌دهد.
- `wavenet.custom_objects()` حالا آن‌ها را include می‌کند.
- get_config/from_config کامل (seq2seq، وزن‌ها، delta) — round-trip تأیید شد.
- تست انتها-به-انتها: build → serialize → deserialize مدل seq2seq ✓
- تست‌های TF-دار integration که در سندباکس با نصب TF نمایان شدند:
  mock کلاس Role در `test_best_model_kept`/`test_epoch_checkpoints` بدون
  `loss/metric` بود → تکمیل شد (این‌ها با TF واقعی کرش می‌کردند).
- ۲ تست `test_threshold_recorded` در سندباکس fail می‌مانند (به MT5 store
  محلی نیاز دارند — روی سیستم اپراتور سبزند).

```
ruff ✅ black ✅
pytest 1526 passed, 2 failed (محیطی: TESTSYM/MT5 store), 12 skipped
```

---

## 2026-08-27 — فاز ۷۲: گزارش «شرایط شروع» کامل در بکتست

**پرسش اپراتور:** «توی لاگ تمام شرایط شروع بک‌تست رو می‌نویسه؟ همهٔ
شرایطی که توی GUI تنظیم می‌کنم؟» — جواب قبلاً «نه» بود؛ چند فیلد فرم
(symbol، مدل‌ها، confidence، windows، same-bar، test-ratio، commission،
capital) در گزارش غایب بودند و commission ثابت 0.0001 چاپ می‌شد.

### رفع

بلاک گزارش بازنویسی شد — بخش «شرایط شروع» حالا شامل:
engine · build · run id · symbol/timeframes · models · confidence gate ·
windows · R/R mult · same-bar policy · test ratio · session filter ·
min SL dist · filter 0-bar · capital/quantity · spread type+value ·
commission (واقعی، نه ثابت) · slippage · entry · range candles fed ·
last N bars — بعدش نتایج.

```
pytest 1526 passed, 2 failed (محیطی: TESTSYM/MT5 — روی سیستم اپراتور سبز), 12 skipped
```

---

## 2026-08-27 — فاز ۷۴: patienceهای قابل تنظیم برای EarlyStopping و ReduceLR

**تحلیل اجرای کاربر (range retrain 75 epoch):** بهترین epoch 50 (val_loss
0.002102) ولی EarlyStopping در ~65 قطع کرد → ReduceLR (patience=7) فقط
۱-۲ پله فرصت کاهش داشت. حدس اپراتور درست بود.

### رفع (پارامتر جدید در کل زنجیره)

- `WavenetTrainer(early_stopping_patience=0, reduce_lr_patience=0)` —
  0 = auto (ES=epochs/5، ReduceLR=epochs/10)
- `DualModelService.build_trainer/train()` پاس می‌دهند
- CLI: `--es-patience N` / `--rlr-patience N` + چاپ در سربرگ
  (`callbacks : EarlyStopping patience=… · ReduceLR patience=…`)
- GUI: دو فیلد در Train a model و Retrain a model

### پیشنهاد عددی برای range 1D با epochs=75-100

`--es-patience 30 --rlr-patience 10` — به ReduceLR اجازه ۳-۴ پله کاهش
(0.85³≈0.61) قبل از قطع.

```
pytest 1491 passed, 53 skipped · ruff ✅ black ✅
```

---

## 2026-08-27 — یادداشت فاز ۷۴-ب: باگ NameError متعلق به کامیت ۸۴d4851 بود

کاربر هنگام run_backtest خطای `NameError: symbol_text` گرفت — traceback به
خط ۲۱۲۳ از کامیت **۸۴d4851 (فاز ۷۲)** اشاره داشت که بخش «شرایط شروع» را با
متغیرهای محلیِ `_run_simulation` در `run_backtest` نوشته بود. در فاز ۷۴
(کامیت `5188801`) همین بخش با bridge `_last_run_context` بازنویسی و فیکس
شده بود. کاربر فقط zip میانی (۸۴d4851) را گرفته بود.

**اقدام:** بدون تغییر کد — کاربر به آخرین zip (۵۱۸۸۸۰۱) ارتقا داده شد.
تأیید: compile ✅ · تست‌های presentation/simulation سبز.

---

## 2026-08-29 — فاز ۷۵: بازسازی براکت حول entry (به‌جای reject)

**درخواست اپراتور:** براکت‌های وارونه رد نشوند؛ باز شوند با SL زیر
قیمت ورود و TP بالای آن (برای BUY)، با استفاده از عرض رنج مدل.

### رفع

`from_model_levels`: گیت rejectِ باگ ۵۲ → منطق recenter:
`width = high − low` · BUY: `SL=entry−width, TP=entry+mult×width` ·
SELL برعکس · پرچم `recentered` در metadata/to_dict · رنج عرض‌صفر رد.

### تست

۵ تست جدید/به‌روز در `test_bracket.py` (کل ۱۲).

```
ruff ✅ black ✅  pytest 1494 passed, 53 skipped
```

---

## 2026-08-29 — فاز ۷۶: SL بازسازی · TP ادعای مدل — رد اگر سمت غلط

**اصلاح فاز ۷۵ به‌درخواست اپراتور:** «این کار رو فقط باید برای حد ضرر
می‌کردی؛ معامله‌ای که حد سودش توی رنج نیست (مثلاً TP خرید زیر قیمت
ورود) نباید اصلاً باز بشه.»

### منطق نهایی

- **SL** = محافظ محلی → اگر وارونه بود، بازسازی: `SL = entry ± width`
  (width = عرض رنج مدل) + پرچم `recentered`
- **TP** = ادعای واقعی مدل دربارهٔ آینده → هرگز جعل نمی‌شود:
  - BUY با TP ≤ entry → `ValidationError` (رد)
  - SELL با TP ≥ entry → `ValidationError` (رد)

### تست‌ها

۶ تست: recenter SL برای BUY/SHORT با TP مدل دست‌نخورده · رد BUY با TP
زیر ورود · رد SHORT با TP بالای ورود · براکت سالم بدون پرچم · رنج صفر.

```
ruff ✅ black ✅  pytest 1495 passed, 53 skipped
```

---

## 2026-08-29 — فاز ۷۸: رفع باگ «unexpected keyword argument early_stopping_patience»

**گزارش کاربر:** آموزش range 1H با `DualModelService.train()` کرش کرد —
`build_trainer` فاز ۷۴ پارامترهای patience را دریافت نمی‌کرد (فقط train()
آن‌ها را داشت و پاس نمی‌داد).

### رفع

- `build_trainer(..., early_stopping_patience=0, reduce_lr_patience=0)`
- پاس به `WavenetTrainer(...)` constructor

```
pytest 1496 passed, 53 skipped · ruff ✅ black ✅
```

---

## 2026-08-29 — فاز ۷۹: باگ ۵۵ — مسیر streamed مدل رنج seq2seq برچسب درست نمی‌داد

**گزارش کاربر:** آموزش range 1H (39,773 پنجره = 4.3GB > آستانهٔ استریم
512MB) کرش کرد: `Index out of range using input dim 2; input has only 2 dims`
در RangeLoss.

### ریشه

مدل رنج seq2seq دو مسیر دارد:
- in-memory (<512MB): `_build_seq2seq_targets` → y=[batch,150,2] ✓ (1D قبلاً از این مسیر بود)
- **streamed (>512MB): `WindowGenerator` برچسب را فقط برای «سطر آخر» می‌ساخت
  → y=[batch,2] → RangeLoss با `y[:, -1:, :]` روی آرایهٔ ۲بعدی کرش**

یعنی seq2seq در مسیر استریم هرگز پیاده نشده بود — 1D قبلاً کوچک‌تر از
آستانه بود و مخفی مانده بود.

### رفع

- `WindowGenerator(..., seq2seq=True)`: `window_at` برچسبِ **هر سطر
  پنجره** را می‌دهد (برچسب فردای همان سطر، که prepare قبلاً به سطرها
  چسبانده)؛ `to_tf_dataset` spec سه‌بعدی `[batch, window, n_targets]`
- `WavenetTrainer._generator()` فلگ `seq2seq=self._seq2seq` را پاس می‌دهد
- ۴ تست جدید (window_at، مسیر قبلی دست‌نخورده، آرایه‌ها، tf.data)

```
pytest 1539 passed, 2 env-failed, 12 skipped · ruff ✅ black ✅
```

---

## 2026-08-29 — فاز ۸۰: horizon رنج در GUI

**درخواست اپراتور:** horizon قابل تنظیم در داشبورد باشد (برای آزمایش‌های
1H با horizonهای ۱۲/۲۴/۶/۱).

### رفع

- فرم **Train a model** و **Retrain a model**: فیلد
  «Range horizon (candles)» (پیش‌فرض 1 = رفتار فعلی)
- مسیرهای train_dual_models و retrain_model:
  `--horizon N` فقط وقتی ≠1 و فقط برای role=range پاس می‌شود
  (سیگنال first-passage بی‌کران است — horizon معنا ندارد)
- hint: «1H: 12 (نیم‌روز) یا 24 (یک روز) برای براکت معنادار»
- ۵ تست جدید (descriptorها، پاس 12، حذف وقتی 1، نادیده‌گرفتن برای signal)

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۱: زوم قیمت و زمان در ریپلی (درخواست اپراتور)

**درخواست:** «مثل متاتریدر بتونم هم توی زمان و هم توی قیمت زوم کنم تا
مقادیر خط‌چین TP/SL رو بهتر ببینم.»

### رفع (replay_renderer.py — خروجی HTML ریپلی)

- **زوم قیمت با wheel موس:** wheel به بالا = بزرگ‌نمایی (تا ۳۰×)؛
  مرکز زوم روی قیمتی که موس زیرش است می‌ماند (anchor) — مثل متاتریدر
- **پن زمان با درگ:** کلیک و کشیدن افقی = جابجایی پنجرهٔ دید
- **دکمهٔ «Reset zoom»** + hint فارسی زیر چارت
- `viewStart`: وقتی کاربر درگ/زوم زمانی کرد، پنجره دستی می‌ماند تا reset
- سازگار با Play/scrub: پس از هر paint دوباره همان zoom اعمال می‌شود
- windowSel (select تعداد کندل) → تغییرش زوم را reset می‌کند

### بدون تغییر رفتار

- بدون zoom (پیش‌فرض) رسم دقیقاً مثل قبل است
- بقیهٔ دکمه‌ها و legend و log دست‌نخورده

```
ruff ✅ black ✅  pytest 1544 passed, 2 env-failed (TESTSYM/MT5), 12 skipped
```

---

## 2026-08-29 — فاز ۸۲: زوم قیمت و پن زمان در چارت دیتای داشبورد (/data)

**پرسش اپراتور:** «روی نمودار قیمت هم قابلیت زوم داره؟» — نه نداشت.
همان زوم متاتریدریِ ریپلی (فاز ۸۱) به چارت کندلی `/data` هم اضافه شد:

- wheel = زوم قیمت (تا ۳۰×، مرکز روی قیمتِ زیر موس)
- درگ افقی = پن زمان
- دکمهٔ «Reset zoom» + hint فارسی
- تغییر select «تعداد کندل» → ریست پن
- برخلاف ریپلی (که cursor دارد)، اینجا کل سری در دسترس است و پن
  در محدودهٔ [0, len-visible] کلمپ می‌شود.

```
ruff ✅ black ✅  pytest 1544 passed, 2 env-failed, 12 skipped
```

---

## 2026-08-29 — فاز ۸۳: wheel = اسکرول زمان (متاتریدری) + Ctrl+wheel = زوم قیمت

**درخواست اپراتور:** اسکرول کندل‌به‌کندل جلو/عقب با موس مثل متاتریدر.
انتخاب اپراتور از بین گزینه‌ها: «هر دو — wheel زمان + Ctrl زوم».

### تغییر در هر دو چارت (ریپلی + /data)

- **wheel**: اسکرول زمان — هر نچ ≈ visible/15 کندل (حداقل ۱)؛ بالا = عقب،
  پایین = جلو؛ کلمپ در محدودهٔ دیتا. در ریپلی، اسکرول `viewStart` را
  می‌کارد (پخش/scrub از همان نما ادامه می‌دهد)
- **Ctrl+wheel**: زوم قیمت حول قیمت زیر موس (رفتار قبلی wheel)
- درگ = پن (قبلی) · دکمهٔ Reset zoom (قبلی)
- hint هر دو چارت: «wheel = اسکرول زمان · Ctrl+wheel = زوم قیمت · درگ = جابجایی»

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۴: نمای سیگنال در /data (درخواست اپراتور)

**درخواست:** «توی /data بتونم دیتاست سیگنال رو ببینم — threshold رو تعیین
کنم و نقاط خرید/فروش نشون داده بشه.»

### رفع

- `/data` فرم جدید: تیک «Show signals» + فیلد «threshold %» (پیش‌فرض 0.6)
- JS: محاسبهٔ **first-passage روی همان کندل‌های چارت** با همان قانون
  آموزش (اولین close که ±barrier بزند؛ گارد OHLC: LONG اگر Low زیر
  Lowِ شروع برود نامعتبر؛ SELL قرینه) — بدون سمت سرور
- رسم: ▲ سبز زیر کندل = BUY · ▼ قرمز بالا = SELL
- خلاصهٔ زنده: «N signals · X buy · Y sell (th …%)»
- debounce تایپ threshold (250ms) تا compute spams نشود
- `DataInspector.candles` حالا `i` (اندیس سراسری) هم برمی‌گرداند
  تا JS نقاط را به کندل‌های پنجره match کند
- تست integration به‌روز شد (فیلد +i)

### نکتهٔ عملکرد

computeSignals روی تغییر threshold اجرا می‌شود (O(n²) در بدترین حالت
روی ۵۰۰ کندل چارت = ~۲۵۰k مقایسه — فوری). اگر بعداً چارت بزرگ‌تر شد
(>۲۰۰۰ کندل)، می‌توان کار را به web-worker منتقل کرد — ثبت به‌عنوان
یادداشت، نه نیاز فعلی.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۵: پیش‌بینی رنج برای هر کندل روی /data (درخواست اپراتور)

**درخواست:** «مدل و دیتاست را انتخاب کنم، روی هر کندل کلیک کنم،
پیش‌بینی قیمتی بعدش نمایش داده شود — مثلاً مدل 1H-h12 → ۱۲ کندل بعد.»

### رفع

- **`presentation/gateway/range_forecast_inspector.py` (جدید):**
  `available_models(timeframe)` (رکوردهای range) و
  `forecast_at(symbol, timeframe, model_id, bar_index)` — پنجرهٔ
  `[bar-149 .. bar]` با همان feature_matrix (causal_only، role=range)
  به مدل می‌رود و **کل مسیر horizon نقطه‌ای** برمی‌گردد:
  `points: [{k, high, low, high_offset, low_offset} …]`
  (بدون خلاصه‌سازی worst-case — هر کندلِ آینده جدا دیده می‌شود)
- **server.py:** `GET /api/range-forecast?symbol&timeframe&model&bar`
  + دادهٔ مدل‌های رنج موجود به صفحهٔ /data
- **data_renderer:** پنل «Range model forecast» — dropdown مدل‌ها،
  کلیک روی کندل → fetch → جدول high/low به‌ازای هر k با درصد آفست

### علیت

پنجره فقط کندل‌های `≤ bar` را می‌بیند؛ هیچ برچسب آینده‌ای ساخته نمی‌شود.
فیچرها همان build مسیر آموزش است (causal_only=True، role-filtered).

### نکتهٔ عملکرد

اولین کلیک: آموزش فیچرها (~۱۰-۲۰ ثانیه). کلیک‌های بعدی: فیچر کش شده،
فقط inference (~۱ ثانیه). اگر کندل انتخابی <۱۵۰ کندل قبلی داشته باشد
→ خطای صریح.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۵-ب: مسیر پیش‌بینی به‌صورت گرافیکی روی چارت

**پرسش اپراتور:** «به صورت گرافیکی هم پیش‌بینی‌ها رو نمایش دادی؟» — نه،
فقط جدول بود. الان رسم هم اضافه شد.

### اضافه شد

- **مسیر TP/SL روی چارت اصلی:** بعد از کلیک روی کندل، خط‌چین سبز (high)
  و قرمز (low) به‌سمت جلو کشیده می‌شود + نقاط کوچک + ناحیهٔ بین‌شان با
  شفافیت کم + قیمتِ نقطهٔ آخر (اگر جا باشد)
- **خط عمودی** روی کندلِ anchor (نقطهٔ کلیک)
- **اسلات‌های اضافی:** اگر anchor+horizon از آخرین کندل رد شود، محور X
  به‌اندازهٔ horizon گسترش می‌یابد
- تغییر مدل یا تغییر select کندل‌ها → forecast پاک می‌شود
- خطای forecast → مسیر پاک و پیام خطا

### بدون تغییر

- جدول متنی قبلی سر جایش است (پنل پایین)
- زوم قیمت و پن زمان کار می‌کنند — می‌توان روی مسیر zoom کرد

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۶: ابزارهای ترسیم + محور زمان (ریپلی + /data)

**درخواست اپراتور:** خط روند، افقی، عمودی + تاریخ/ساعت روی محور X هر دو چارت.

### اضافه شد

**/data (data_renderer.py):**
- خطوط ترسیم: Trend (دو کلیک) · H-Line (یک کلیک) · V-Line (یک کلیک)
- دکمه‌های ╱Trend · ─H-Line · │V-Line · ✕Clear
- خط افقی: قیمت $ کنار خط چاپ می‌شود
- خط عمودی: زمان MM-DD HH:MM
- محور X: تاریخ/ساعت (MM-DD HH:MM) هر N کندل
- سه دکمه toggle می‌شوند (کلیک دوباره = خاموش)

**replay (replay_renderer.py):**
- همان سه ابزار + دکمه‌ها
- محور X: تاریخ/ساعت هر N کندل
- خطوط در draw رسم می‌شوند (مقاوم به زوم/پن — مختصات پیکسلی ذخیره می‌شوند)

### محدودیت شناخته‌شده

خطوط به‌صورت پیکسلی ذخیره می‌شوند نه قیمتی/زمانی — اگر زوم قیمت یا
پن زمانی تغییر کند، خطوط جابجا به نظر می‌رسند. این یک trade-off ساده‌سازی
است (خطوط ذخیره‌شده پایدار ماندن حتی بعد از reset zoom). اگر بعداً
خواستی خطوط مقاوم به zoom باشند، باید به‌صورت قیمت/زمان ذخیره شوند.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۷: رفع باگ — کد سیگنال /data در فاز ۸۶ حذف شده بود

**گزارش اپراتور:** تیک Show signals هیچ نقاطی نمایش نمی‌دهد و dropdown
مدل رنج خالی است.

### ریشه

فاز ۸۶ (ابزارهای ترسیم + محور زمان) کل تابع draw() را بازنویسی کرد و
در این بازنویسی، کد سیگنال‌های فاز ۸۴ حذف شد:
- `computeSignals()` و `renderSignals()` و `currentSignals`
- مثلث‌های ▲/▼ رسم روی چارت
- dropdown مدل‌های رنج هم فقط هم‌تایم‌فریم نشان می‌داد (1D فقط 1D)

### رفع

- همهٔ کد سیگنال از کامیت 2d0fd0c بازگردانده شد
- مثلث‌ها برگشتند
- dropdown حالا مدل‌های 1D **و** 1H را نشان می‌دهد

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۸: رفع باگ عدم‌نمایش مثلث‌های سیگنال روی /data

**گزارش اپراتور:** «۲۶۴ سیگنال می‌شمارد ولی هیچ مثلثی رسم نمی‌شود.»

### ریشه

`computeSignals` اندیس `i` را **محلی** (0..n-1 نسبت به CANDLES) می‌داد،
ولی `indexOf` در draw از `c.i` (سراسری، 49500+) پر می‌شد. هیچ match ای
رخ نمی‌داد → مثلث‌ها skip می‌شدند.

### رفع

- `computeSignals` حالا `s.i = base + start` (اندیس سراسری از
  `CANDLES[0].i`) تولید می‌کند تا با `c.i` هم‌مقیاس باشد
- `indexOf` fallback هم دارد اگر `c.i` undefined باشد

### مسئلهٔ مدل رنج هم علت مشابه دارد

`available_models(timeframe)` فقط مدل‌های همان timeframe چارت را می‌داد.
اگر چارت 5M است و مدل‌های رنج 1D/1H ذخیره شده‌اند → خالی.
حالا همهٔ رنج‌ها (1D+1H) در dropdown هستند (رفع در فاز قبلی).

---

## 2026-08-29 — فاز ۸۹: رفع باگ dropdown مدل رنج + افزایش کندل‌های نمایش

**گزارش اپراتور:** dropdown مدل رنج خالی است · تعداد کندل‌ها را ببر تا ۵۰۰۰.

### ریشهٔ dropdown خالی

کد JS مربوط به پر کردن dropdown (از `RANGE_MODELS` و fetchForecast و
کلیک کندل) در فاز ۸۶ هم مثل کد فاز ۸۴ حذف شده بود. بازگردانی شد.

### رفع

1. بازگردانی JS dropdown مدل + fetchForecast + کلیک روی کندل
2. select تعداد کندل: 60/120/200/300 → **120/300/500/1000/2000/5000**
3. `DEFAULT_CHART_CANDLES` = 300 → **5000**
4. کامیت فاز ۸۷ (رفع باگ سیگنال) را هم همراه دارد

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۰: باگ ۵۶ (warmup pad) + باگ ۵۷ (wheel روی محور قیمت)

**گزارش اپراتور:**
۱. «tوی محور قیمت نمی‌تونم اسکرول کنم»
۲. «Feature matrix has 73 rows; model needs 150» در کلیک روی /data

### باگ ۵۶ — warmup pad برای پیش‌بینی روی /data

`build_feature_matrix` سطرهای warm-up را حذف می‌کند (EMA200=200,
ATR=77, …). وقتی فقط window_size=150 کندل به آن می‌دادیم، بعد از
حذف warmup فقط ۷۳ سطر باقی می‌ماند → خطا.

**رفع:** پنجرهٔ ورودی = `window_size + 400` کندل (پوشش کامل warmup)
، بعد از build آخرین ۱۵۰ سطر برای مدل.

### باگ ۵۷ — wheel روی محور قیمت = زوم قیمت

قبلاً wheel فقط اسکرول زمان بود. حالا:
- **موس روی محور قیمت (۶۶px سمت راست چارت) + wheel** → زوم قیمت
- **موس روی چارت + wheel** → اسکرول زمان
- **Ctrl+wheel** → زوم قیمت (هر جا)

در هر دو چارت (/data و replay) اعمال شد.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۱: پن عمودی روی محور قیمت (درخواست اپراتور)

**درخواست:** «اسکرول روی محور قیمت هم نیازه — زوم که می‌کنیم کندل‌ها می‌رن
بالای صفحه و دیگه نمی‌شه دید. باید بشه روی محور قیمت بالا و پایین رفت.»

### رفع

وقتی `priceZoom > 1.0` و موس روی **محور قیمت** (۶۶px سمت راست) wheel شود:
- بالا (deltaY<0) → چارت **بالا** می‌رود (پن عمودی)
- پایین (deltaY>0) → چارت **پایین** می‌رود

هر نچ = ۲۵٪ از باند فعلی جابجایی. `priceAnchor` هم آپدیت می‌شود تا
مرکز زوم واقع‌بینانه بماند. `Reset zoom` پن را هم صفر می‌کند.

در **هر دو چارت** (/data و replay) اعمال شد. بدون Ctrl — چون محور
قیمت است و زوم هم از قبل فعال است.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۲: رفع باگ — مسیر پیش‌بینی روی چارت /data رسم نمی‌شد

**گزارش اپراتور:** «مقادیر قیمت پیش‌بینی می‌شوند ولی توی چارت نشونشان
نمی‌دهد» — خطای `ConnectionAbortedError` هم در سرور (چون مرورگر timeout
کرده بود در حال انتظار).

### ریشه

`renderForecast()` هیچ‌وقت `forecastPath` را نمی‌ساخت — فاز ۸۵-ب این
متغیر را تعریف کرد ولی خود تابع render را آپدیت نکرد. نتیجه: داده
برمی‌گشت و جدول پر می‌شد ولی `draw()` هیچ مسیری نداشت که رسم کند.

### رفع

- `renderForecast(f, localIdx, …)`: بعد از پر کردن جدول، `forecastPath`
  را از `f.points` می‌سازد
- `fetchForecast(..., localIdx)` و کلیک کندل `_clickedLocalIdx` را پاس
  می‌دهد
- سرور `ConnectionAbortedError` را هم بلعیده باشد تا لاگ کثیف نشود

### تکمیلی — symbolTf تعریف‌نشده حذف شد

---

## 2026-08-30 — فاز ۹۳: رفع SyntaxError — تعریف تکراری plotW/step/yP/xOf در draw

**گزارش اپراتور:** چارت /data کاملاً سیاه — هیچ کندلی نمایش داده نمی‌شود.

### ریشه

فاز ۸۶ (بازنویسی draw) و فاز ۷۹ (استریم) هر دو `plotW/step/yP/xOf` را
تعریف کرده بودند. تعریف دوم با `const` = SyntaxError در مرورگر → کل
اسکریپت چارت کرش می‌کرد.

### رفع

تعریف تکراری حذف شد؛ نسخهٔ درست `plotW / Math.max(1, totalSlots)`
(که اسلات‌های future را هم حساب می‌کند) نگه داشته شد.

---

## 2026-08-30 — فاز ۹۴: رفع چارت سیاه + شفافیت قیمت پایه در forecast

### چارت سیاه

علت: SyntaxError در JS (تعریف تکراری plotW/step/yP/xOf در فاز ۸۶) — رفع شد در فاز ۹۳.

### ConnectionAbortedError در سرور

مرورگر وقتی fetch timeout می‌شود اتصال را قطع می‌کند → سرور خطا می‌دهد.
حالا `_send_json`/`_send_html` در خطای `{ConnectionAborted,BrokenPipe}Error`
را بی‌صدا عبور می‌دهند (لاگ تمیز).

### Base price در جدول forecast

جدول حالا «Base price» هم نشان می‌دهد تا کاربر بداند آفست‌ها نسبت به
کدام قیمت محاسبه شده‌اند (close کندل انتخابی).

---

## 2026-08-30 — فاز ۹۴: باگ ۵۸ — statsHtml const ولی += داشت

**گزارش اپراتور:** «[X] Assignment to constant variable» در rf-status
و مسیر پیش‌بینی روی چارت رسم نمی‌شد.

### ریشه

`renderForecast` در فاز ۸۵-ب اضافه شد ولی `statsHtml` را `const` تعریف
کرده بود و بعداً با `+=` مقدار Base price را اضافه می‌کرد → TypeError
در مرورگر → کل تابع abort می‌شد → `forecastPath` هرگز ست نمی‌شد →
چارت هیچ مسیری رسم نمی‌کرد.

### رفع

`const statsHtml` → `let statsHtml`

### تأیید

`forecastPath` بعد از `renderForecast` مقدار دارد:
`{"localIdx":0,"points":[{"high":101,"low":99}]}` ✓

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۵: تارگت مدل رنج ATR-نرمال‌شده + تبدیل قیمت در همه‌جای مصرف

**درخواست اپراتور:** «تارگت رو با ATR اصلاح کن؛ بعد توی بکتست و هرجایی که
قراره قیمت پیش‌بینی بشه، نحوهٔ محاسبهٔ قیمت پیش‌بینی رو هم اصلاح کن.»

### ریشه (از تحلیل فاز ۹۴)

تارگت قبلی `(high[t+k] − close[t]) / close[t]` درصدِ خام بود؛ ورودی هم
minmax روی [-2,+2]. مدل نه مقیاس قیمت می‌دید نه مقیاس نوسان → بهینه‌ترین
جواب = میانگین ثابت دیتاست (±0.06% در 1H، ±0.60% در 1D) برای همهٔ کندل‌ها.

### تعریف تارگت جدید

```
high_seq[t,k] = (high[t+k] − close[t]) / ATR14[t]
low_seq[t,k]  = (low[t+k]  − close[t]) / ATR14[t]
```

ATR با `wilder_atr_series` (علوی، تعریف expand-seed + هموارسازی Wilder)
محاسبه می‌شود — همان تعریف در لیبل‌سازیِ آموزش و de-normalize در پیش‌بینی.

### معماری تبدیل (یک‌باره، در مرز پیش‌بینی‌کننده)

- `RangePredictor(target_units="atr")` خروجی مدل را «ضریب ATR» می‌داند؛
  با `atr_reference = ATR14(کندل مرجع)` قیمت‌ها می‌شوند
  `close + mult × ATR` و معادلِ کسریِ close هم در `high_offset` ذخیره
  می‌شود تا همهٔ نمایش‌های درصدی قدیمی درست بمانند.
- `RangeForecast` فیلدهای `target_units / atr_reference /
  high_atr_mult / low_atr_mult` گرفت؛ `predicted_high/low` در حالت atr
  با فرمول ATR محاسبه می‌شوند → براکت، بکتست، استراتژی و GUI بدون تغییر
  قیمتِ درست می‌گیرند.
- مدل‌های قدیمی: `ModelRecord.target_units` (پیش‌فرض "pct") مسیر قدیمی را
  حفظ می‌کند — هیچ مدل ذخیره‌شده‌ای خراب نمی‌شود.

### سیم‌کشی atr_reference (فقط مصرف‌کنندهٔ واقعی)

| مسیر | منبع ATR |
|------|----------|
| بکتست (`DualModelPredictionSource`) | کندل‌های رنجِ تحویل‌شده تا آخرین کندل بسته (memoized per bar) |
| GUI /data (`RangeForecastInspector`) | کندل‌ها تا کندل کلیک‌شده |
| زنده (`LiveMatrixBuilder` → `LiveWindow.atr_reference`) | بافر ۱H |
| sanity-check آموزش (`run_dual_models`) | کل سری کندل‌ها |

پارامتر `atr_reference` فقط به پیش‌بینی‌کننده‌های ATR-unit پاس می‌شود تا
استاب‌ها/امضاهای قدیمی نشکنند؛ مدل ATR بدون ATR با خطای واضح رد می‌شود
(هرگز قیمت غلط خاموش).

### گزارش و رکورد

- `ModelRecord.target_units` + نمایش `range units` در خلاصهٔ بکتست و
  `target units` در سربرگ آموزش رنج.
- جدول forecast در /data برای مدل ATR ستون `×ATR` نشان می‌دهد.

### بدهی قدیمی که در همین فاز پرداخت شد

تست‌های شمارندهٔ کاتالوگ فیچر (227→229، 188→190، 241→243، 177→179،
174→176) از فاز ۹۴ آپدیت نشده بودند — حالا سبز شدند. ۳ خطای ruff قدیمی
در target_builder هم رفع شد.

### تأیید

```
ruff ✅ (فایل‌های فاز ۹۵ پاک؛ نویز کل‌ریپو کمتر از baseline)
black ✅
pytest 1532 passed, 54 skipped  (+28 تست جدید فاز ۹۵)
```

تست‌های جدید: `test_atr_range_target.py` (13)،
`test_range_predictor_atr.py` (9)، `test_range_atr_wiring.py` (6).

---

## 2026-08-30 — فاز ۹۵-ب: گزارش آموزش ATR-آگاه + baseline «پیش‌بینی ثابت»

**گزارش اپراتور از اولین ران با تارگت ATR (1D, horizon=5):** «توی بک تست
قیمت‌ها متفاوت بود، مثل قبل یه درصد ثابت نمی‌داد» ✓ — هدف فاز ۹۵ محقق شد.

### مشکل پیدا‌شده در همان لاگ

خط epoch هنوز `~+-1984.27$` چاپ می‌کرد — ریاضیِ قدیمی pct
(`val_mae × قیمت ۲۶۵۰`). با تارگت ATR این عدد بی‌معنی است.

### رفع

- `ConsoleProgressReporter(target_units, atr_reference)` — تبدیل دلاری
  فقط با واحد درست: ATR → `mult × ATR14` (نمایش `~+-23.59$
  (ATR14=31.50)`)؛ pct قدیمی → رفتار قبل؛ بدون مرجع → هیچ عدد جعلی.
- `print_quality` هم همین‌طور: پیام «ATR multiples» + تبدیل با ATR.
- اسکریپت گزارشگر را با واحد/ATR دیتاست می‌سازد.

### baseline جدید: «پیش‌بینی ثابت»

سربرگ آموزش حالا MAE یک پیش‌بینی‌کنندهٔ ثابت (میانهٔ train) روی آخرین
فولد ولید را چاپ می‌کند (`constant base`) و QUALITY حکم می‌دهد:

```
vs constant baseline 0.7521: the model BEATS ... by 0.0033
vs constant baseline 0.7480: NO BETTER than a constant prediction
```

این دقیقاً سنجهٔ ریشه‌یابی مشکل آفست ثابت است.

### نکتهٔ عملی برای اپراتور (ران 300×4)

val_loss بعد از epoch ~90 فقط با دقت 1e-6 «بهبود» می‌یافت →
ReduceLROnPlateau (min_delta=1e-6) هرگز decay نمی‌کند و ES هم نه.
بهترین checkpoint بعد از هر epoch ذخیره می‌شود؛ قطع کردن ران امن است.
پیشنهاد: `--epochs 60..80`.

### تأیید

```
ruff ✅ black ✅  pytest full suite green (+4 تست جدید گزارشگر)
```

---

## 2026-08-30 — فاز ۹۵-ج: حکم QUALITY روی final-step + جلوگیری از مرگ LR

**ران اپراتور (1D, horizon=5, 300×3, RLR patience=3):** حکم چاپ‌شده
«NO BETTER than constant» بود ولی اعداد خلافش را می‌گفتند.

### ریشه: مقایسهٔ سیب با پرتقال

- `val_mae` (کراس) = میانگین روی **هر ۱۵۰ موقعیت پنجره** — موقعیت‌های
  اولِ پنجره عمداً کمتر آموزش دیده‌اند (وزن loss: 40% کل، 60% آخرین)
  → 0.8301
- `val_high/low_mae` (باگ ۴۸) = **آخرین timestep** = دقیقاً همان که
  inference مصرف می‌کند → (0.3678 + 0.3208)/2 = **0.3443**
- baseline ثابت (0.7587) هم روی همان ردیف‌های final-step است.

**نتیجهٔ درست: مدل 0.3443 در برابر 0.7587 → 55% بهتر از پیش‌بینی ثابت.**
مدل skill واقعی دارد؛ حکم قبلی اشتباه بود.

### رفع ۱ — حکم درست

`print_quality` حالا final-step MAE را جدا چاپ می‌کند و حکم را با همان
می‌دهد؛ val_mae تمام-سکانس فقط اطلاعاتی است.

### رفع ۲ — کاسکید مرگ LR

RLR با min_delta=1e-6 بهبودهای ±3e-7 را «بدتر شدن» می‌شمرد → با
patience=3، LR در 280 epoch از 8e-4 به **1e-6** سقوط کرد (فولد آخر
عملاً یخ زده — val_loss 0.6717 نتیجهٔ مدل نیمه‌آموزش‌دیده است، نه سخت
بودن داده). رفع:

- RLR: min_delta 1e-6 → **1e-4**، min_lr از lr×1e-3 → **lr×0.02**
- ES: min_delta 1e-6 → **1e-4** (با این تغییر ES واقعاً fire می‌شود)

### تفسیر برای اپراتور

- biasها: high −0.26 / low +0.18 → بازهٔ پیش‌بینی به‌طور سیستماتیک
  ~0.2 ATR باریک‌تر از واقعیت است (انقباض به میانگین). کالیبراسیون
  bias (گسترش با biasِ train) گام بعدی احتمالی است — فعلاً فقط ثبت شد.
- fold losses 0.615 / 0.574 / 0.672 — فولد آخر (تازه‌ترین داده) سخت‌تر
  است + LR مرده. با رفع ۲ انتظار می‌رود فولد آخر بهتر شود.

### تأیید

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-د: پروفایل لیبل بر حسب k + خطای per-step

**گزارش اپراتور از /data (gold_range_1h h12):** خروجی دیگر ثابت نیست ✓
ولی روی هر انکر، گام +1 بزرگ‌ترین درصد را دارد و به سمت +12 نزولی
کم می‌شود. سؤال: این منحنی «حقیقت داده»ست یا artifact مدل؟

### نکتهٔ معنایی مهم (ثبت برای همیشه)

تارگت seq2seq عطف به closeِ **انکر** است و high/low «یک کندلِ خاص»،
نه running-max افق:
`high_seq[t,k] = (high[t+k] − close[t]) / ATR14[t]`
= رانشِ k کندله + فتیلهٔ همان کندل. میانهٔ رانش ~۰ است → پروفایل
میانهٔ نظری تقریباً **تخت** است (برخلاف شهود مخروطِ گسترش‌یونده که
مال running-max است). پس انحراف از تخت یعنی رانشِ یادگرفته‌شده.

### تشخیص جدید (این فاز)

- **سربرگ آموزش — `label profile`**: میانهٔ لیبل هر گام k، جدا برای
  train و ردیف‌های آخر (recent) → منحنیِ اقلیم داده. مدل بی‌مهارت
  دقیقاً به همین منحنی می‌رسد.
- **QUALITY — `per-step MAE`**: `_range_validation_metrics` حالا
  `val_step{k}_mae` برای هر گام تولید می‌کند (روی آخرین timestep =
  همان خروجی inference).

تفسیر بعد از ران بعدی:
- پروفایل داده تخت/صعودی ولی مدل نزولی → artifact (زیربرازش پروفایل)
- پروفایل داده هم نزولی → مدل درست یاد گرفته (اقلیمِ آن دوره همین است)

### نکتهٔ عملی برای براکت

`RangePredictor` برای horizon>1 worst-case می‌گیرد (max/min روی k)؛
با پروفایل نزولی، بدترین حالت همیشه k=1 است → عملاً باند براکت ≈ باند
گام اول. اگر تشخیص دادیم پروفایل واقعی داده با k رشد می‌کند، این یعنی
مدل افق را دست‌کم می‌گیرد و باید loss وزن‌دهی per-step شود.

### تست‌ها

`test_label_profile_and_step_mae.py` (6) — پروفایل train/recent،
گارد ورودی خالی/فرد، per-step روی شکل seq2seq و flat (بدون TF).

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-ه: رسم مسیر forecast روی چارت /data

**گزارش اپراتور:** «توی /data پیش‌بینی‌ها روی کندل‌ها نمایش داده نمی‌شه؛
فقط عددها رو پرینت می‌کنه.»

### ریشه — دو باگ مستقل

1. **`renderForecast` هرگز `draw()` صدا نمی‌زد.** forecastPath ست می‌شد
   ولی چارت تا بلور بعدی (اسکرول/زوم/تغییر مدل) دوباره رسم نمی‌شد →
   اپراتور فقط جدول عددی می‌دید.
2. **click handler اندیس گلوبال را به‌جای لوکال می‌فرستاد.**
   `idx = base + rel*visible` گلوبال است؛ پاس‌دادنش به‌عنوان localIdx
   یعنی draw() بعدی انکر را جای دور فرض می‌کرد → totalSlots منفجر
   (base+5000+12 اسلات) → step زیرپیکسلی → چارت له و مسیر بیرون بوم.
   باگ ۲ با باگ ۱ ماسک شده بود (draw اصلاً صدا زده نمی‌شد).

### رفع

- `renderForecast`: بعد از ست کردن forecastPath → `draw()` فوری.
- کلیک: `const localIdx = idx - base;` → پاس به fetchForecast و
  `_clickedLocalIdx` (کامنت غلط هم اصلاح شد).

### تأیید

```
node --check روی _CHART_SCRIPT ✅
assert دو فیکس در اسکریپت ✅
pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-و: sanity prediction با مدل ذخیره‌شده + رفع پیام‌های h1

**ران اپراتور (1D, horizon=1, 100×3):** حکم درست بود — h1 مقابل ثابت
بد نیست (0.3317 در برابر 0.3132). این یافتهٔ واقعی است، نه باگ:
اندازهٔ فتیلهٔ روزانه در واحدهای ATR تقریباً غیرقابل‌پیش‌بینی است و
میانهٔ ثابت همان‌جا نزدیکِ بهینه است (پروفایل لیبل هم مؤیدش: train
+0.401/−0.381 ≈ recent +0.392/−0.353؛ پیش‌بینی sanity مدل +0.38/−0.37
دقیقاً همان اقلیم است).

### باگ گزارش‌گیری که در همین ران پیدا شد

`PREDICTION for the next ...` با `outcome["artifact"]` (مدل خامِ
آخرین فولد، val 0.2345) ساخته می‌شد، نه با مدلی که ذخیره شده
(best checkpoint epoch 50، val 0.2147). رفع: `save_model` حالا
آرتیفکتِ واقعاً ذخیره‌شده را برمی‌گرداند و sanity prediction با همان
اجرا می‌شود (`sanity_artifact`).

### ریزه‌کاری‌های دیگر

- در h1 پیام «full-sequence is NOT the trading number» گمراه‌کننده بود
  (دو عدد یکی‌اند) → حالا وقتی برابرند پیام ساده چاپ می‌شود.
- حکم NO BETTER حالا hint عمومی دارد: مهارت در افق‌های بلندتر (رانش)
  ظاهر می‌شود، نه در اندازهٔ فتیلهٔ تک‌کندل.

### جدول مهارت (از سه ران اپراتور — 1D، ATR units)

| horizon | ثابت | final-step | حکم |
|---------|-------|-----------|------|
| 1 | 0.3132 | 0.3317 | NO BETTER (−6%) |
| 2 | 0.4531 | 0.3200 | BEATS (+29%) |
| 5 | 0.7587 | 0.3443 | BEATS (+55%) |

خطای مطلق مدل تقریباً ثابت (~0.32-0.34) است؛ ثابت با افق رشد می‌کند
(عدم‌قطعیت رانش) → لبهٔ مدل از رانش است، نه فتیله.

### نکتهٔ ثبت‌شده (بدون تغییر — NO REDESIGN)

مدل KEPT = best val_loss کل ران (epoch 50 فولد ۲) — آخرین بخش داده را
ندیده. طراحی فعلی عمدی است (Phase 47)؛ در صورت نیاز گزینهٔ
`--keep last-fold` بعداً اضافه می‌شود.

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-ز: حکم سطح-براکت (worst-case vs worst-case)

**ران اپراتور (1D, horizon=2, 50×3، کال‌بک‌های فیکس‌شده):**
- پروفایل لیبل: high با k رشد می‌کند (+0.401→+0.499)، low ~ثابت →
  فرضیهٔ فاز ۹۵-د تأیید: منحنی 1Hِ GUI ترکیبی از اقلیم + artifact بود.
- per-step MAE: k1=0.336 (خوب، ~۱۵٪ بهتر از اقلیمش) ولی
  **k2=0.649 (خیلی بدتر از اقلیمِ ~0.44)** → مدل گام ۲ را نمی‌بیند
  (وزن‌دهی 40/60 loss + پخشِ بزرگ‌ترِ k2).
- LR فولد آخر 0.000218 → زنده؛ کاسکید مرگ رفع شده ✓.

### باگی که حکم این ران آشکار کرد

حکم «BEATS 28%» با خطای k1 (0.3355) در برابر baselineای که میانگین
ستون‌های k1+k2 بود (0.4654) داده شد — در حالی که براکتِ واقعی از
worst-case روی k مصرف می‌کند (RangePredictor: max/min روی گام‌ها).
k1 خوب، k2 خراب را پنهان می‌کند.

### رفع (فاز ۹۵-ز)

1. `_range_validation_metrics`: + `val_bracket_{high,low,}_mae` —
   MAEِ (max_k high، min_k low) پیش‌بینی در برابر (max_k، min_k) واقعی.
   برای h1 برابر step1.
2. برش قدیمی `[:, :2]` در شاخهٔ 2D حذف شد (ورودی تختِ [N, H*2] را به
   k1 محدود می‌کرد — فقط legacy [N,2]/[N,H*2] کامل نگه داشته می‌شود).
3. سربرگ: + `climate/step` (MAE ثابتِ هر گام) و + `bracket base`
   (constant worst-case vs actual worst-case — مقایسهٔ منصفانه).
4. `print_quality`: برای h>1 حکم با bracket MAE در برابر bracket base
   (`VERDICT (bracket level)`)؛ پیام step-1 دیگر ادعای «what inference
   uses» را برای h>1 ندارد.

### پیامد برای اپراتور

ران بعدی h2/h5 حکم جدید را نشان می‌دهد: اگر VERDICT (bracket level)
NO BETTER بود، یعنی باندِ worst-case مدل از اقلیم بدتر است (k2 خراب
براکت را مسموم می‌کند) → یا h2 با مصرفِ فقط-گام-۱، یا وزن‌دهی per-step
loss. تصمیم با دادهٔ ران بعدی.

```
ruff ✅ black ✅  pytest full suite green (+1 تست براکت)
```

---

## 2026-09-01 — فاز ۹۶: انتخاب نسخهٔ مدل در بکتست + هشدار مدلِ قبل از فاز ۹۵

**بکتست اپراتور (72 ترید، −5.11%):** لاگ می‌گفت gold_range_1d **v2**
(trained=2026-08-27) لود شده — CSV هم تأیید: هر ۷۲ ترید دقیقاً همان
آفست ثابت +0.6239%/−0.5985% (امضای مدل pct قدیمی). **مدل ATR فاز ۹۵
اصلاً در بکتست نبود.**

### ریشه

- مدل‌های ATR جدید در کاتالوگ به‌عنوان **v1** ذخیره شده‌اند؛ مدل قدیمی
  pct **v2** است → ``latest_version`` (بزرگ‌ترین شماره) همیشه مدل
  قدیمی را برمی‌دارد.
- فرم بکتست اصلاً فیلد انتخاب مدل/نسخه ندارد.

### رفع (فاز ۹۶)

1. فرم بکتست: + فیلدهای «Signal model» و «Range model» — خالی = جدیدترین
   نسخه؛ «id:vN» نسخهٔ صریح (مثلا `gold_range_1d:v1`).
2. هندلر: `_split_model_spec` (tolerant به v/V و فاصله) →
   `signal_version`/`range_version` به `from_storage` (که از قبل
   پارامتر نسخه داشت، فقط UI نداشت).
3. هشدار بلند در خروجی: وقتی مدل رنجِ لودشده pct است:
   `range units : pct ‼️ PRE-Phase95 model — ... results are not comparable.`
4. models_line حالا نسخهٔ واقعی لودشده را نشان می‌دهد (`id:latest` یا `id:vN`).

### تحلیل همان ۷۲ ترید (مدل قدیمی — ارزش مرجع)

| طول ترید (کندل 5M) | n | WR | PnL |
|---|---|---|---|
| 0 | 5 | 0% | −0.19 |
| 1–20 | 18 | 6% | −3.53 |
| 21–100 | 13 | 15% | −3.97 |
| 101–300 | 19 | 32% | −2.39 |
| >300 (~>25h) | 17 | **59%** | **+5.29** |

→ براکت پهنِ ثابت (±$25، عرض ~1.22%) فقط با رانش چندروزه سود می‌شود؛
تریدهای کوتاه ورود-نویز + اسپرد می‌خورند. اسپرد فقط 0.7% فاصلهٔ SL —
مشکل نیست. ۵ ترید 0-bars (نقد همزمان با ورود) هم ۵ تا ضرر.

### گام بعدی اپراتور

بکتست A/B با مدل ATR: در فرم، Range model = `gold_range_1d:v1`
(نسخه‌ای که فاز ۹۵ train کرده؛ با `vs constant baseline` سربرگ آموزش
تطبیق بده) — و هشدار pct دیگر نباید ظاهر شود.

```
ruff ✅ black ✅  pytest full suite green (+6 تست پارسر)
```

---

## 2026-09-01 — فاز ۹۶-ب: فیلتر ترند EMA50 روزانه + تحلیل بکتست ATR

**بکتست اپراتور با مدل ATR (175 ترید، 50k bars، −9.01%، WR 27.4%)** —
اولین ران واقعی با فاز ۹۵:

| مشاهده | عدد |
|---|---|
| آفست‌های یکتا | 91 high / 90 low ✓ (دیگه ثابت نیست) |
| پهنای براکت | ‏$49–$164 (med $81) — متغیر با رژیم نوسان ✓ |
| short / long | **142 / 33** (!) |
| ترید <100 کندل | 84 ترید، WR ≤19%، **−13.9$** |
| ترید >600 کندل (~>2 روز) | 22 ترید، **WR 59%**، **+6.79$** |
| بدترین ساعت‌ها UTC | 15 (WR 1/8)، 3 (0/8)، 1، 23 |
| بهترین ساعت‌ها UTC | 17 (+6.09، 7/9)، 18 (+4.80)، 2، 14 |
| 0-bar | 19 ترید، WR 0% |

→ همان الگوی دو ران قبل، قوی‌تر: **کل سود استراتژی از رانش چندروزه
می‌آید؛ ضرر اصلی ورودِ خلاف ترند روزانه است** (بازار صعودیِ بزرگِ دورهٔ
آزمون + اکثریت SHORT). اسکیوِ باند هم 100% با جهت هم‌راستاست — چون
گیتِ R/R=1 فقط ورود در نیمهٔ درستِ باند را می‌پذیرد (by construction).

### رفع: فاز ۹۶-ب — فیلتر ترند EMA50 (پیشنهاد قدیمی، حالا داده‌پشتیبان)

- `DualModelPredictionSource(trend_filter="ema50")`: بعد از گیت
  actionable و **قبل از مصرف مدل رنج**، EMA50 علوی از کندل‌های رنجِ
  تحویل‌شده: SHORT ممنوع وقتی close > EMA50، LONG ممنوع وقتی < EMA50.
  تاریخچهٔ <50 کندل → فیلتر بی‌اثر (اجازه). بلوک‌ها در
  `stats()["trend_blocked"]`.
- `DualModelBacktestService`/`from_storage`: پاس‌دادن `trend_filter`.
- فرم بکتست: + فیلد «Daily trend filter» (none/ema50) + خط
  `trend filt :` در سربرگ + خط `trend blocks: n` در نتیجه.

### گام بعدی اپراتور — سه ران کنار هم

1. `trend_filter=ema50` با همین تنظیمات (50k، conf 70، R/R 1) → مقایسه
   مستقیم با این ران (−9.01%)
2. `filter_zero_bar=1` هم روشن (19 ترید 0-bar همگی باخته بودند)
3. بعد اگر لازم بود session hours جدید (17,18,2,14 خوب؛ 15,3,1,23 بد)

خطر overfitting ساعات بالاست؛ فیلتر ترند اصولی‌تر و مقاوم‌تر است.

```
ruff ✅ black ✅  pytest full suite green (+6 تست فیلتر ترند)
```

---

## 2026-09-01 — فاز ۹۶-ج: تحلیل پیلوت فیلتر ترند — سیستم به لبه رسید

**ران پیلوت اپراتور:** trend=off، zero-bar=on، conf 60 → 154 ترید،
WR 29.2%، **−9.42%** (تقریباً برابر ران قبل: −9.01%). 0-bar حذف شد
ولی فرقی نکرد — خونریزی کوتاه‌مدت جای دیگری است.

### آناتومی دقیق 154 ترید (CSV)

| برش | یافته |
|------|-------|
| مدت | <100 کندل: n=70، WR≤12%، **−19.4$** • >600: WR 59%، **+8.97$** |
| confidence | تفاوت معنادار ندارد (0.60-0.70: −1.85، 0.70+: −6.3) |
| جهت | 115 short / 39 long — هنوز اکثریت short |
| ساعت UTC | بدترین: 15، 21، 3، 7، 1، 4 ‏• بهترین: 17، 14، 2، 18 |

### شبیه‌سازی آنتی‌سیتروتیک روی همین CSV (با دادهٔ خودش)

| سناریو | n | WR | PnL |
|--------|---|----|-----|
| کل ران | 154 | 29% | −8.16 |
| فقط فیلتر ترند (proxy 5-day) | 76 | — | **+1.72** (تریدهای حذف‌شده: −9.88!) |
| فقط حذف ۶ ساعت بد (15,21,3,7,1,4) | 100 | 36% | **+11.75** |
| ساعت‌های خوب (2,6,14,17,18) | 37 | 49% | +14.11 |

→ هر دو لایه مستقلاً سیستم را به سمت مثبت می‌برند؛ روی‌هم (ن=۲۰)
+7.74 با WR 45% — نمونهٔ کوچک ولی جهت‌دار.

### هشدار Overfitting (ثبت رسمی)

- ساعت‌ها روی **همین ران** انتخاب شده‌اند — حکم نهایی فقط با ران
  out-of-sample معتبر است.
- proxy 5-day با خودِ تریدها ساخته شده (near-lookahead خفیف)؛
  فیلتر واقعی EMA50 که فاز ۹۶-ب ساخت سخت‌گیرتر/علوی‌تر است و عددش
  کمی متفاوت خواهد بود.

### اقدام

چیز جدیدی کد نشد — ابزار هر دو لایه از قبل هست:
`trend_filter=ema50` + `session_filter` (ساعت‌های فرم فعلی
2,5,6,10,14,15,16,18 باید به 2,6,14,17,18 تغییر کند — فاز ۵۲ قدیمی
بوده) → ران‌های A/B اپراتور. تغییر لیست ساعت‌ها با تأیید اپراتور.

---

## 2026-09-01 — فاز ۹۶-د: symbol_select قبل از هر fetch + پیام خطای قابل‌رفع

**گزارش اپراتور:** fetch 4H با `XAUUSD_I` → `MT5 returned no data:
(-1, 'Terminal: Call failed')` در حالی که ترمینال لاگین است.

### دو ریشهٔ عملیاتی (بدون کد)

1. **حروف بزرگ/کوچک:** پسوند آلپاری با i کوچک است — `XAUUSD_i` نه
   `XAUUSD_I`. MT5 اسم‌ها را case-sensitive می‌شناسد.
2. **نام canonical اشتباه:** فیلد symbol فرم باید `XAUUSD` باشد (نام
   پلتفرم)؛ `XAUUSD_I` به‌عنوان canonical جدید ذخیره می‌شد و تاریخچه
   تکه‌تکه می‌شد. چون fetch رد شد چیزی ذخیره نشد — فقط فرم را درست کن.

### ریشهٔ نرم‌افزاری (رفع شد)

پراوایدر MT5 هرگز `symbol_select` صدا نمی‌زد — اگر نمونه در Market
Watch نبود (یا املایش غلط بود)، copy_rates همان (-1) مبهم را می‌داد.

رفع: `_select_symbol` قبل از هر `copy_rates_from_pos/range`:
- `symbol_info` هست → `symbol_select` و ادامه
- نیست → ValidationError با نزدیک‌ترین اسم‌های واقعی بروکر
  (`symbols_get("*XAUUSD*")`) و یادآوری صریح i کوچک آلپاری.

### تست‌ها

- جدید: `test_mt5_symbol_select.py` (3) — select-before-fetch،
  خطای قابل‌رفع برای case غلط، مسیر range.
- `FakeMt5` در test_mt5_provider سطح `symbol_info/symbol_select` گرفت.

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-09-01 — فاز ۹۶-ه: session-first برای اتصال MT5 (اکانت‌های OTP/گواهی‌دار)

**گزارش اپراتور:** بعد از درست شدن mapping (‏XAUUSD -> XAUUSD_i ✓)،
‏-7 برگشت: `Unsupported authorization mode, OTP or certificate password needed`
در حالی که ترمینال لاگین است.

### ریشه

پراوایدر اگر پروفایل login/password/server داشته باشد، **همیشه** با
credential لاگین برنامه‌ای می‌زند. اکانت جدید آلپاری لاگین پسوردیِ
برنامه‌ای را رد می‌کند (-7) حتی وقتی ترمینالِ لاگین‌شده آماده است.
ران قبل (-1) از مسیر بدون-credential رفته بود؛ بعد از ذخیرهٔ پروفایل،
مسیر credential فعال شد و -7 برگشت.

### رفع — session-first

`_ensure_initialized` دو مرحله‌ای شد:
1. `initialize()` بدون credential (اتصال به نشست ترمینال). ترمینال
   لاگین باشد → همان استفاده می‌شود؛ credential هرگز ارسال نمی‌شود.
2. نشست زنده نبود → shutdown + `initialize(login, password, server)`.
   رد شد → ConnectionError با راهنمای صریح OTP («ترمینال را دستی لاگین کن»).

بدون credential: رفتار قدیمی حفظ شد.

### تست‌ها

`test_mt5_session_first.py` (4): نشست زنده credential نمی‌فرستد؛
fallback به credential با shutdown بین دو تلاش؛ ردِ لاگین → پیام OTP؛
بدون credential رفتار قدیمی. تست‌های lifecycle به قرارداد جدید
آپدیت شدند (`test_live_session_beats_saved_credentials`).

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-09-02 — فاز ۹۶-و: لیست مدل‌های رنج /data از همهٔ تایم‌فریم‌ها

**گزارش اپراتور:** مدل رنج 4H ذخیره شده ولی در دراپ‌داون /data نیست.

### ریشه

سرور /data لیست مدل را از `available_models("1D") + available_models("1H")`
می‌ساخت — **هاردکد از فاز ۸۶-ب**. هر تایم‌فریم جدید (4H) نامرئی می‌ماند.

### رفع

- `RangeForecastInspector.all_range_models()`: همهٔ مدل‌های رنج
  ذخیره‌شده از هر تایم‌فریمی (یک رکورد per model_id، آخرین نسخه) +
  فیلد `timeframe` در هر آیتم.
- سرور: لیست از همان متد — بدون هاردکد؛ تایم‌فریم جدید بدون تغییر کد ظاهر می‌شود.
- دراپ‌داون: `gold_range_4h v1 · h5 · 4H · 2026-09-01` — تایم‌فریم مدل دیده می‌شود.

نکتهٔ مصرف: پیش‌بینیِ یک مدل رنج باید روی دیتاست **هم‌تایم‌فریمِ**
خودش اجرا شود (۴H مدل با سری 4H) — چون ATR14 و window بر حسب کندلِ
آن تایم‌فریم آموزش دیده‌اند. /data سری 4H را از قبل دارد (fetch 4H).

### تست‌ها

`test_all_range_models.py` (3) — همهٔ تایم‌فریم‌ها، حذف signal،
کاتالوگ خالی. کل تست‌سوت سبز.

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-09-02 — فاز ۹۷: استراتژی سه‌تایم‌فریمی (5M سیگنال · 4H براکت · 1D ترند)

**طرح اپراتور** — بکتست دقیقاً این شکلی بشه (بعد از A/B سؤالات، پاسخ‌ها):
- **مجوز ۱:** سیگنال 5M با احتمال > آستانهٔ GUI (موجود).
- **مجوز ۲:** از 150 کندل روزانه تا D0 → مدل رنج 1D → High/Low پیش‌بینی D1؛
  شیب High و Low نسبت به D0 واقعی. خرید: شیب‌ها ≥ ۰؛ فروش ≤ ۰.
  **حالت شیب در GUI انتخابی:** both / either / high / low (برای A/B).
- **مجوز ۳:** سمت TP (خرید: TP > ورود).
- **براکت از مدل 4H** (150 کندل 4H تا H0 → پیش‌بینی کندل بعدی):
  خرید TP=High، SL=Low؛ فروش برعکس.
- **fallback SL (خرید):** اگر SL ≥ ورود → SL = Low(D0)؛ اگر هنوز ≥ ورود →
  کمترین Low **زیر ورود** از کندل‌های 5M امروز − اسپرد؛ نبود → رد.
  فروش آینه‌ای (+اسپرد روی High).
- **R/R:** طبق خواستهٔ اپراتور اعمال می‌ماند (فیلد GUI).
- **اسپرد درصدی GUI** — برخورد TP/SL روی BID/ASK: موتور در حالت pct
  حالا اسپرد per-candle را به `bracket.trigger` هم می‌دهد (قبلاً فقط
  در خروج اعمال می‌شد، نه در چک لمس).

### پیاده‌سازی

- `DualModelPredictionSource`: مدل روزانه دوم (artifact/predictor/1D
  candles/matrix) + خوراک علوی 1D در observe + گیت شیب در predict
  (قبل از اجرای 4H) + `_triple_bracket` در bracket_for + آمار جدید
  (`daily_predictions/blocked`, `sl_fallback_d0/today`,
  `license3_refused`, `rr_refused`, `no_sl_found`).
- `DualModelBacktestService`: `strategy="classic|triple"`,
  `slope_mode`, `daily_model_id/version` → from_storage رکورد/آرتیفکت
  1D را لود و `run(daily_candles=...)` ماتریس روزانه می‌سازد.
- فرم‌های بکتست/replay: فیلدهای Strategy (triple/classic) و Slope mode؛
  در triple باید Range timeframe = 4H و دیتاست 1D موجود باشد (وگرنه
  پیام واضح). سربرگ: `strategy:` و `slope mode:`؛ نتیجه: `daily gate`,
  `sl fallback`, `lic-3/rr` خطوط.
- پیش‌فرض فرم = triple؛ فراخوانی بدون پارامتر (تست‌ها) = classic.

### تست‌ها

`test_triple_strategy.py` (14): مجوز ۲ در ۴ حالت شیب، براکت استاندارد،
fallback D0، fallback 5M-امروز−اسپرد، ردِ بدون-SL، مجوز ۳، R/R، فروش
آینه‌ای. کل تست‌سوت سبز.

### گام اپراتور

1. بکتست: `strategy=triple`، `range_timeframe=4H`، `range_model=gold_range_4h`،
   `slope_mode=both` (بعداً حالت‌های دیگر برای A/B)، R/R=1، conf 60-70.
2. خروجی باید `range units: atr` (مدل 4H) + خطوط `daily gate / sl
   fallback / lic-3/rr` را نشان دهد.
3. A/B پیشنهادی: slope_mode ∈ {both, either, high} — همان دیتاست.

```
ruff ✅ black ✅  pytest full suite green (+14)
```

---

## 2026-09-02 — فاز ۹۷-ب: مجوز ۴ — نزدیکی ورود به سطح روزانه

**تحلیل ران triple اول (186 ترید، WR 9.7%، −8.42%):** ۴۹% تریدها
0-bar و 100% بازنده (SL داخل نویز اسپرد — fallback-5M چاقو می‌ساخت)؛
spread cost $4.8 از ضرر $8.4؛ ‏165 short در بازار صعودی.

**داده برای آستانهٔ «نزدیکی» (از CSV اپراتور):**
- برندگان: فاصلهٔ ورود تا close روز med **+$1.7** (تا p75 = $9.3)
- بازندگان: med **+$9.3** (تا p75 = $12.5) — یعنی شکارِ جهش از بالای روز
- → آستانهٔ پیشنهادی: **0.25×ATR14(1D)** ≈ $9-10 در آن دوره.

### پیاده‌سازی — مجوز ۴ (پیش از اجرای مدل 4H)

`max_entry_distance_atr` (GUI، پیش‌فرض 0.25؛ 0 = خاموش):
- خرید: `entry − Low_pred(D1) ≤ 0.25×ATR14(1D)`
- فروش: `High_pred(D1) − entry ≤ 0.25×ATR14(1D)`
- فاصلهٔ منفی (ورود فراتر از سطح) مجاز — «داخل ناحیه» است.
- `proximity_blocked` در آمار + خط `proximity:` در نتیجه + آستانه در
  سربرگ strategy.

عمداً **کد اضافه نشد برای min-SL-6**: فیلد موجود `min_sl_distance`
همین کار را می‌کند (گیت استراتژی، قبل از fallback ها) — فقط مقدار
GUI را 6 بگذار.

### تست‌ها

+5 (بلاک دور/پاس نزدیک/فروش آینه‌ای/خاموش/منفی-رد). کل تست‌سوت سبز.

### ران پیشنهادی بعدی

```
min SL dist = 6 | max entry dist = 0.25 | slope both | R/R 1 | conf 60
```

```
ruff ✅ black ✅  pytest full suite green (+5)
```

---

## 2026-09-02 — فاز ۹۷-ج: کالبدشکافی ران triple کامل — دو باگ جایگاه گیت + تحلیل WR پایه

**ران اپراتور (triple، همهٔ تاریخچه، min SL=$6):** 941 ترید، WR 13.4%،
**−43.85%** — بدترین ران، پرآموزنده‌ترین ران.

### کشف ۱ — گیت min_sl_distance در triple بی‌اثر بود (باگ جایگاه)

گیت ۷ روی SL «پیش‌بینی 4H» چک می‌شود که همیشه بزرگ است (~$23). ولی در
triple بعد از گیت، fallback ها SL را به Low(D0)/5M-امروز بازنویسی
می‌کنند → **474 ترید با SL نهایی < $6** (پیش‌فرض گیت!) از در رفتند.
آن ۴۷۴ تا: WR **1.5%**، PnL **−17.29**.

رفع (فاز ۹۷-د، بعدی): چک حداقل فاصله باید **بعد از fallback نهایی**
در `_triple_bracket` هم اجرا شود.

### کشف ۲ — ریز-ضرر از ریز-اسپرد

‏437 ترید 0-bar همگی باخته؛ ‏805 از 815 باخت ≤ $0.4 (SL ~$6 + اسپرد
~$2.65×2). اسپرد کل $25.1 = ۵۷% خالص ضرر. با SL=$6 و اسپرد ~$2.6،
نوار واقعی SL فقط ~$0.7+نویز — تقریباً مارکت‌استاپ.

### آنچه بعد از حذف چاقوها می‌ماند

فقط تریدهای SL≥6: ‏WR 25.5%، −26.56 ‏• SL≥10: ‏WR 28.6%، −19.07 ‏•
TP med $21-23 — هنوز منفی، چون EV = 0.26×21 − 0.74×10 ≈ −2 بعد از
اسپرد. **WR پایهٔ سیگنال 5M در جهت شیب روزانه زیرِ سربه‌سر است.**

### نتیجه‌گیری معماری (برای بحث با اپراتور)

لایه‌های فیلتر (شیب/نزدیکی/R-R) درست کار می‌کنند (27823 بلاک!) ولی
«چه بخریم» را هنوز سیگنال 77.1%-دقیقِ آموزش‌ندیده با threshold 60%
تعیین می‌کند. گزینه‌ها:
- A: سیگنال 5M با داده/epoch کامل ریترین شود (فقط 10 epoch دارد!)
- B: جهت از خود مدل 4H (شرط TP-side که 2530 رد کرده — نرخ موفقش
  اندازه‌گیری شود)
- C: ترکیبی — سیگنال فقط timing، جهت = توافق 1D+4H

### اقدام کد — فاز ۹۷-د

`_triple_bracket`: بعد از fallback نهایی، `sl_dist ≥ min_sl_distance`
(و حداقل 2×spread) وگرنه رد؛ شمارندهٔ `final_sl_refused`.

### فاز ۹۷-د (تکمیلی — همان روز)

`_triple_bracket` حالا بعد از fallback نهایی چک می‌کند:
`sl_dist ≥ max(min_sl_distance, 2×spread)` وگرنه رد
(`final_sl_refused`). این بستنِ حفرهٔ «گیت استراتژی روی SL پیش‌بینی
چک می‌کرد و fallback چاقو می‌ساخت» است — همان ریشهٔ 474 ترید WR 1.5%
در ران 941-تایی. از `min_sl_distance` همان فیلد GUI دوباره‌استفاده
شد (کد جدید برای اپراتور: هیچ). +3 تست؛ کل تست‌سوت سبز.

---

## 2026-09-03 — فاز ۹۸ (قسمت ۱): مدل TREND — رنگ کندل بعدی (GREEN/RED)

**ایدهٔ اپراتور:** «بفهمیم کندل بعدی قرمزه (فروش‌پسند) یا سبز
(خریدپسند).» تصمیم بعد از تحلیل: مدل **طبقه‌بندی** جدید با نقش
`signal` (reuse: softmax + cross-entropy + Predictor مشترک) ولی
model_id متمایز — رگرسیون O/C رد شد (loss random-walk را به پیش‌بینی
«بدنه ≈ صفر» می‌رساند؛ علامتش نویز).

### پیاده‌شده (قسمت ۱ — آموزش)

- `trend_model_id/timeframe` در model_roles: `gold_trend_4h`،
  window=150، softmax دودسته‌ای، dropout 0.15.
- `build_trend_labels` در target_builder: GREEN=1 وقتی
  `close[t+1] ≥ close[t]`؛ بدون first-passage؛ آخرین کندل بی‌برچسب.
- `PredictionTarget`: threshold=0 حالا مجاز (برچسب رنگ به آستانه
  نیاز ندارد) — اعتبارسنجی از `<= 0` به `< 0`.
- `DualModelService.prepare`: شاخهٔ `gold_trend_*` — همهٔ ردیف‌های
  کامل، sample_ends استاندارد؛ definition: `label_style="color"`,
  `target_name="candle_color"`.
- `run_dual_models.py`: `--model trend_4h` + پیام label rule مخصوص.

### باقی‌مانده (قسمت ۲ — مصرف)

- SignalPredictor برای gold_trend کار می‌کند (2-softmax) ✓ ولی باید
  در backtest سیم کشیده شود: `TrendPredictor` با احتمال GREEN/RED +
  «مجوز ۵» در triple: خرید فقط وقتی P(GREEN) > آستانه؛ فروش فقط وقتی
  P(RED) > آستانه. (فیلد GUI: trend confidence %)

### وضعیت

```
ruff ✅ black ✅  pytest full suite green
دستور آموزش (روی سیستم اپراتور):
  python scripts/run_dual_models.py --with-features --symbol XAUUSD \
    --model trend_4h --epochs 60 --folds 2 --window 150 \
    --learning-rate 0.0008 --es-patience 15 --rlr-patience 5 \
    --storage-root datasets
```

## فاز ۹۸ (قسمت ۱-ب): trend در GUI آموزش + نمایش رنگ در /data

- **Train a model / Retrain / LR-sweep:** گزینهٔ `trend_4h` اضافه شد؛
  dataset پیشنهادی خودکار 4H؛ threshold=0 برای trend؛ Retrain مدل‌های
  gold_trend_* به درستی به role=trend_4h نقشه می‌خورد.
- **/data:** کلیک روی هر کندل → بالای جدول forecast، رنگ کندل بعدی از
  `gold_trend_4h` (▲ سبز / ▼ قرمز + درصد اطمینان + «روند پیش‌بینی
  صعودی/نزولی»). endpoint جدید `/api/trend-forecast` (علوی: پنجرهٔ
  فقط تا کندل انتخابی + warmup pad). اگر مدل ترند ذخیره نشده باشد
  پیام راهنما می‌دهد.
- JS با node --check تأیید؛ ruff/black پاک؛ کل تست‌سوت سبز.

### فاز ۹۸ (تصحیح اپراتور): trend برای هر تایم‌فریمی — نه فقط 4H

«قرار نیست فقط 4H باشه؛ اصلیش روزانه‌ست، شاید 4H هم بسازم» — درست.
`trend_4h` نامگذاری اشتباه بود:

- CLI: `--model trend` + تایم‌فریم از `--signal-timeframe`
  (پیش‌فرض 1D). مثال: `--model trend --signal-timeframe 1D`
  → `gold_trend_1d`؛ با 4H → `gold_trend_4h`.
- GUI (Train/Retrain/LR-sweep): گزینهٔ `trend`؛ دیتاست دلخواه
  (پیشنهاد 1D)؛ Retrain مدل‌های gold_trend_* → role=trend.
- /data: کلیک روی کندل، مدل ترند **هم‌تایم‌فریمِ سری فعال** را صدا
  می‌زند (`gold_trend_${tf}`) — سری 1D → gold_trend_1d، سری 4H →
  gold_trend_4h؛ اگر آن مدل ذخیره نشده پیام راهنما می‌دهد.
- `trend_model_role` پیش‌فرض timeframe="1D".

همهٔ تست‌سوت سبز؛ node --check روی اسکریپت چارت OK.

### فاز ۹۸ (رفع ابهام اپراتور): «دیتاست 1D انتخاب کردم ولی مدل 5M آموزش دید»

دو مسیر برای تایم‌فریمِ trend وجود داشت و GUI مسیر اشتباه را می‌فرستاد:
- اسکریپت trend را از `--signal-timeframe` می‌خواند (پیش‌فرض 5M)؛
- GUI مقدار Dataset را فقط در `--range-timeframes` می‌فرستاد.

رفع: اسکریپت برای trend اول `--range-timeframes` (همان Dataset) را
می‌خواند بعد signal-timeframe؛ GUI هم برای trend دیتاست انتخابی را در
هر دو فلگ می‌فرستد. سربرگ `training:` حالا `trend(1D)` را نشان می‌دهد
(قبلاً «nothing» چاپ می‌شد). + کل تست‌سوت سبز.

### فاز ۹۸ (رفع باگ اپراتور): «sample_end_indices and label_end_indices must be supplied together»

شاخهٔ trend در prepare صریحاً sample_ends می‌ساخت بدون
sample_label_ends → trainer جفتِ ناقص را رد می‌کرد. برچسب trend
ثابتِ یک‌کندله است — حالا مثل range دیتاستِ stride-1 ساده می‌سازد
(sample_ends=None) و purge ویژه لازم ندارد.
تأیید سرتاسری در سندباکس (TF نصب شد): prepare → train (1 epoch،
2 فولد) → val_accuracy 55.6% روی دادهٔ تصادفی → SignalPredictor
P(GREEN)=0.505. + کل tests/unit سبز (1034) — دو تست
test_threshold_recorded محیط‌اند (در HEAD هم fail؛ در WORKLOG فاز ۵۲ ثبت شده).

### فاز ۹۸ (تکمیلی): مدل ترند در /data

آپراتور: «مدل ترند توی /data نمیاد که انتخابش کنم» — درست بود:
`all_range_models` فقط role=range را برمی‌گرداند و gold_trend_1d
(role=signal) حذف می‌شد.

- inspector: gold_trend_* با `kind='trend'` در لیست می‌آید (signalهای
  خام همچنان حذف)؛ + تست به‌روزشده.
- دراپ‌داون /data: برچسب `[trend: color]` برای مدل‌های ترند.
- کلیک روی کندل وقتی مدل ترند انتخاب است → فقط رنگ کندل بعدی
  (▲/▼ + درصد) نمایش داده می‌شود و مسیر High/Low رسم نمی‌شود
  (مدل ترند براکت ندارد).
- تأیید: node --check، +تست به‌روزشده، کل تست‌سوت سبز
  (دو تست test_threshold_recorded محیطی — روی HEAD هم fail).

### فاز ۹۸ (رفع هنگ /data): کش مدل و فیچر برای endpoint ترند

**گزارش اپراتور:** کلیک روی کندل → فقط «predicting…» بی‌پایان + هشدار
tf.function retracing در PowerShell.

**ریشه:** `_trend_forecast_payload` در **هر کلیک**: (1) مدل TF را
دوباره deserialize می‌کرد (چند ثانیه) و (2) هر مدلِ جدید با ورودی
هم‌شکل → tf.function retrace کامل؛ (3) ساخت فیچرِ 530+ کندل با
229 فیچر هم چند ثانیه. روی ویندوز جمعاً ده‌ها ثانیه تا دقیقه —
مرورگر فقط waiting می‌دید.

**رفع:** کش سطح کلاس روی DashboardHandler:
- `_model_cache[key = id:version:checksum]` — deserialize یک بار؛
- `_feature_cache[key = symbol:tf:bar:window]` — فیچر هر کندل یک بار
  (سقف 512 و clear).

**اندازه‌گیری واقعی (سندباکس، مدل واقعی keras + دیتای parquet):**
cold 4.2s → warm same-bar 0.07s → bar جدید 1.2s. رفع هنگ ✓

### فاز ۹۸ (رفع باگ دوم اپراتور): پنل ترند هرگز نمایش داده نمی‌شد

**گزارش:** «predicting…» می‌نویسد و هیچ خروجی نمی‌آید (سه GET).
سرور در واقع پاسخ می‌دهد (تست thread در سندباکس سبز، کش هم کار می‌کند)
— مشکل سمت مرورگر بود:

شاخهٔ trend در fetchForecast پنل را `display='none'` می‌کرد و هرگز
نشان نمی‌داد؛ باکس `trend-color` هم **داخل همان پنل مخفی** است →
خروجی سرور به جایی رندر نمی‌شد.

**رفع:** پنل قبل از await نمایش داده می‌شود؛ «predicting…» بعد از
دریافت پاسخ پاک می‌شود؛ مسیر High/Low هم پاک می‌شود (مدل ترند
براکت ندارد). node --check ✓، کل تست‌سوت سبز (دو تست محیطی همان).

---

## 2026-09-03 — فاز ۹۹: مدل سیگنال ترند — سه‌کلاسه BUY/HOLD/SELL (roll-forward)

**طرح اپراتور (پس از A/B):** پنجرهٔ rolling 288 کندل 5M → پیش‌بینی
سه‌کلاسه برای 288 کندل بعدی: BUY اگر حرکت صعودی، SELL اگر نزولی،
HOLD اگر هیچ. تعریف «صعودی/نزولی» (پیشنهاد من، تأیید اپراتور):
**اولین عبور ±X×ATR14 از close** در افق — X پیش‌فرض 0.5 (GUI).
نام مدل داینامیک با تایم‌فریم: `gold_trend_signal_<tf>`.

### پیاده‌سازی

- `build_trend_signal_labels(candles, horizon=288, atr_mult=0.5)`:
  برچسب 0=SELL / 1=HOLD / 2=BUY؛ برخورد دو مانع در یک کندل → نمونهٔ
  مبهم حذف؛ sample_label_ends برای purge درست (برچسب تا 288 کندل
  جلوتر می‌رود).
- `trend_signal_model_role` → `gold_trend_signal_<tf>`، window=288،
  `PredictionTarget.num_classes=3` (output_units=3)، نقش signal
  (softmax سه‌کلاسه + sparse CE + accuracy).
- `DualModelService.prepare`: شاخهٔ trend_signal **قبل از** شاخهٔ
  gold_trend_ (prefix مشترک بود!) با sample_ends + label_ends.
- CLI: `--model trend_signal` + ‏`--atr-mult` (0.5) + ‏`--label-horizon`
  (288)؛ سربرگ label rule مخصوص؛ sanity prediction سه‌کلاسه؛
  signal_label_split_balance سه‌کلاسه ({sell,hold,buy}).
- GUI: Train/Retrain/LR-sweep گزینهٔ `trend_signal` + فیلدهای
  «Trend-signal barrier (×ATR14)» و «Trend-signal horizon»؛
  دیتاست پیشنهادی 5M؛ threshold برای trend_signal = X (نه درصد).
- `PredictionTarget.num_classes` (2/3) با اعتبارسنجی.

### تأیید سرتاسری

- ۹ سناریوی دستی برچسب (BUY/SELL/HOLD/مبهم/علیت) ✓
- CLI کامل روی 800 کندل 5M مصنوعی: آموزش → ذخیره → حکم QUALITY →
  پیش‌بینی سه‌کلاسه (SELL/HOLD/BUY با argmax) ✓
- +۹ تست واحد؛ کل تست‌سوت سبز (دو تست محیطی همیشگی مستثنا)

### گام بعدی (قسمت ۲ — بکتست)

مجوز ۶ در triple: خرید فقط P(BUY)>آستانه و >P(HOLD)؛ فروش مشابه
(فیلد GUI). آماده‌سازی بعد از تأیید اپراتور.

## 2026-09-04 — تحلیل ران gold_trend_1d (400×3، بدون ES مؤثر)

اپراتور ران 1:47h را کامل کرد: ‏val_acc 57.0% vs baseline 53.2% →
BETTER (پیش از این 50 epochs هم همین بود). نکات:
- ES patience=400 عملاً خاموش — 1200 epoch کامل اجرا شد؛ اما checkpoint
  per-epoch بهترین را نگه داشت؛ KEPT=epoch آخر فولد ۳.
- val_acc از fold 1 (50.1%) به fold 3 (57.0%) بهبود — ولی دقت بهبود
  عمدتاً از decay LR (0.0008→0.00007) و حرکت ملایم مدل به سمت کلاس
  اکثریت (green 53.2%) است؛ bias «سیگنال ترند» هنوز ضعیف.
- val_loss 0.6866 نزدیک ln(2)=0.693 → مدل فقط کمی بهتر از سکه.
- کاهش LR خودکار کار کرد (learning_rate: 0.00007).

### جمع‌بندی برای تصمیم بعدی
لبهٔ 3.8% (57.0 vs 53.2) نازک است؛ برای گیت ورود باید آستانهٔ
احتمال را بالاتر از 53% نگذاشت و بهتر است با confidence 55-57% تست شود.
مدل trend_signal (سه‌کلاسه) شانس بیشتری برای لبهٔ واقعی دارد چون
HOLD راه فرار از روزهای بی‌رون می‌دهد.

### فاز ۹۹ (تکمیلی): trend_signal در GUI آموزش

- MODEL_ROLE_CHOICES + دراپ‌داون Train/Retrain/LR-sweep: گزینهٔ
  `trend_signal` اضافه شد؛ دیتاست پیشنهادی خودکار 5M؛ threshold برای
  trend_signal = X برحسب ATR14 (فیلد atr_mult، پیش‌فرض 0.5)؛
  label_horizon (288) هم به هر سه فرم اضافه شد.
- Retrain: مدل‌های gold_trend_signal_* به role=trend_signal نقشه
  می‌خورند و threshold ذخیره‌شده را ارث می‌برند.
- تأیید: descriptorهای TRAIN/RETRAIN/LR-sweep فیلدها و گزینه‌ها را
  دارند؛ lint پاک؛ tests/unit سبز.

---

## 2026-09-05 — فاز ۹۸-ب: مدل trend_score + رفع باگ HOLD + GUI

**درخواست اپراتور:** سه کار: (۱) ATR مانع trend_signal از تایم‌فریم
روزانه، (۲) مدل Trend-Score در GUI، (۳) تارگت score روند.

### رفع ۱: ATR مانع trend_signal → بازهٔ 288 کندلی

مانع قبلی از ATR14(5M)≈$2 بود → HOLD=0%. حالا مانع =
0.5×بازهٔ 288 کندل عقب‌تر (max(high)−min(low)) که ~$30-40 است.
تأیید: label balance روی 2200 کندل → sell 17.7% · hold 26.4% · buy 55.9% ✓

### رفع ۲: trend_score مدل جدید (رگرسیون score روند)

- `build_trend_score_labels`: score = (close−open)/(high−low) روی
  کندل تجمعی از horizon کندل آینده → پیوسته در (−1,+1)
- `trend_score_model_role`: name="range" (reuse رگرسیون+Huber+MAE)،
  kind=PRICE_RANGE، model_id=`gold_trend_score_<tf>`
- prepare: شاخهٔ trend_score **قبل از** PRICE_RANGE generic
  (در غیر این صورت range branches it را می‌ربود)
- CLI: `--model trend_score` + سربرگ label rule مخصوص
- GUI: همهٔ فرم‌ها (Train/Retrain/LR-sweep) گزینهٔ `trend_score`
  + فیلدهای label_horizon پاس داده می‌شوند

### تأیید سرتاسری

CLI کامل روی 800 کندل: train → val_mae 0.239 → **BEATS baseline 61%** ✓
```
ruff ✅ black ✅  tests/unit سبز
```

### فاز ۹۸-ب (تصحیح اپراتور): trend_score در دراپ‌داون Train

اپراتور درست گفت — `trend_score` در dropdown نبود. اضافه شد:
`('all', 'range', 'signal', 'trend', 'trend_signal', 'trend_score')`

### فاز ۹۸-ب (رفع): رنگ ترند هنگام انتخاب مدل رنج هم fetch می‌شد

**گزارش:** روی سری 5M وقتی مدل رنج (غیر-trend) انتخاب شده بود،
پیام «مدل gold_trend_5m ذخیره نشده» ظاهر می‌شد — چون
`fetchForecast` در **پایان** خودش (صرف‌نظر از انتخاب مدل) همیشه
`fetchTrendColor` را صدا می‌زد.

**رفع:** `fetchTrendColor` فقط داخل شاخهٔ trend (وقتی کاربر صریحاً
مدل ترند انتخاب کرده) صدا زده می‌شود. برای مدل‌های رنج رنگ ترند
نمایش داده نمی‌شود.

node --check ✓ · کل تست‌سوت سبز ✓

### فاز ۹۸-ب (رفع): «trend: color is not defined» در /data

**ریشه:** در `fetchTrendColor` متغیر `color` standalone استفاده شده بود
(`${color === 'GREEN' ? '▲' : '▼'}`) ولی این متغیر تعریف نشده بود —
فقط `green` (boolean) و `data.color` موجود بودند.

**رفع:** `${color === 'GREEN' ? '▲' : '▼'}` → `${green ? '▲' : '▼'}`
node --check ✓ · کل تست‌سوت سبز ✓

### فاز ۹۸-ب (رفع دوم): fetchTrendColor پارامتر modelOverride نداشت

فراخوانی `fetchTrendColor(barIndex, symbol, timeframe, modelId)` پارامتر
چهارم را می‌فرستاد ولی تعریف تابع فقط ۳ پارامتر داشت → modelOverride
همیشه undefined → همیشه `gold_trend_${tf}` fallback می‌شد → «مدل ذخیره
نشده». رفع: پارامتر modelOverride به امضای تابع اضافه شد.

### فاز ۹۸-ب (رفع): /data فقط مدل‌های هم‌تایم‌فریم نمایش می‌دهد

**گزارش اپراتور:** gold_trend_score_5m روی سری 1D کار می‌کند و «روند
ثابت با درصد ثابت» می‌دهد — بی‌معنا چون مدل روی 5M آموزش دیده و
فیچرهای 1D کاملاً متفاوت‌اند.

**رفع:** `all_range_models(timeframe)` — وقتی timeframe پاس داده شود
فقط مدل‌های هم‌تایم‌فریم با سری فعال برمی‌گردد. سرور این را با
`timeframe` فعلی صدا می‌زند. کاربر دیگر مدل 5M را روی سری 1D نمی‌بیند.
hint زیر دراپ‌داون هم اضافه شد.

تأیید: فیلتر 5M → فقط trend_score_5m؛ فیلتر 1D → فقط range_1d؛
بدون فیلتر → هر دو. کل تست‌سوت سبز ✓

### فاز ۹۸-ب (رفع نهایی): fetchTrendColor modelOverride استفاده نمی‌کرد

**ریشهٔ واقعی که سه بار رد شد:** تابع `fetchTrendColor` پارامتر
`modelOverride` را می‌پذیرفت ولی **هیچ‌جا از آن استفاده نمی‌کرد** —
به‌جایش `gold_trend_${tf}` می‌ساخت که برای سری 5M یعنی gold_trend_5m
(وجود ندارد).

**رفع نهایی:** `const trendModelId = modelOverride || gold_trend_${tf}`
— وقتی کاربر مدل ترند انتخاب کرده، از همان استفاده می‌شود.

تأیید end-to-end با مدل واقعی TF + دیتای parquet: ✅

### فاز ۹۸-ب (نهایی — ریشهٔ واقعی): modelOverride استفاده نمی‌شد

**تحلیل عمیق:** سرور endpoint کامل و سالم است (تست سرتاسری سندباکس
با مدل keras واقعی + parquet: ✅ GREEN 68.3%). مشکل فقط سمت مرورگر:
`fetchTrendColor` پارامتر `modelOverride` را می‌پذیرفت ولی هیچ‌جا
استفاده نمی‌کرد — همیشه `gold_trend_${tf}` fallback می‌شد.

رفع: `trendModelId = modelOverride || gold_trend_${tf}` + حذف
فراخوانی خودکار برای مدل‌های غیر-trend. اندازه‌گیری سندباکس: ✅

### فاز ۹۸-ب (رفع نهایی-۲): پیام خطای هاردکد جایگزین پیام واقعی سرور شده بود

fetchTrendColor وقتی data.error داشت، **همیشه** متن «ذخیره نشده» را
نمایش می‌داد — حتی اگر خطای سرور چیز دیگری بود (مثل فیچر ناموجود یا
کندل ناکافی). این باعث می‌شد دیباگ غیرممکن شود چون پیام واقعی مخفی
می‌شد. حالا پیام واقعی سرور + لیست مدل‌های ذخیره‌شده نمایش داده می‌شود.

### فاز ۹۸-ب (رفع نهایی-۳): model_role mismatch — 179 vs 184 فیچر

**خطای اپراتور:** `expected shape=(None, 288, 184), found shape=(1, 288, 179)`

**ریشه:** /data endpoint همیشه `model_role="signal"` (179 فیچر) می‌فرستاد،
ولی gold_trend_score_5m با name="range" آموزش دیده → 184 فیچر
(شامل range-scope فیچرها). ۵ فیچر کمتر = shape mismatch.

**رفع:** model_role بر اساس model_id انتخاب می‌شود:
`"range" if model_id.startswith("gold_trend_score_") else "signal"`

### فاز ۹۹ (رفع): gold_trend_score/signal مسیر range را طی کنند نه trend color

fetchForecast هر مدل با prefix gold_trend_ را به fetchTrendColor (فقط
رنگ) می‌فرستاد — برای gold_trend_score_5m و gold_trend_signal_5m
اشتباه بود چون این‌ها score رگرسیونی و سه‌کلاسه‌اند نه رنگ.

رفع: فقط gold_trend_1d/4h (رنگ‌محور) به fetchTrendColor می‌روند؛
score و signal مسیر range معمولی (JSON High/Low یا سه‌کلاسه).
همچنین range_forecast_inspector model_role پویا شد: trend_signal →
"signal"، بقیه → "range".

### فاز ۹۹ (رفع): /data برای trend_score و trend_signal خروجی مخصوص

**مشکل:** forecast_at مسیر High/Low رنج را برای همه مدل‌ها اجرا می‌کرد
→ برای trend_score (خروجی 1عددی) و trend_signal (خروجی 3عددی) خطای
shape mismatch می‌داد.

**رفع:** forecast_at شاخه‌های مخصوص دارد:
- gold_trend_score_* → خروجی score پیوسته + direction
- gold_trend_signal_* → خروجی سه‌احتمالی SELL/HOLD/BUY
- بقیه (رنج) → مسیر High/Low معمولی

/data JS: `renderTrendModel(data)` برای نمایش خروجی‌های جدید
(توی جدول، به‌جای High/Low، score یا احتمالات را نشان می‌دهد).

+ `_deserialize_model` import fix در شاخهٔ trend_score.

### فاز ۹۹ (UI): header جدول forecast پویا برای score/signal

### فاز ۹۸-ب (رفع): خروجی trend_score — Dense(2)→Dense(1) + tanh

**ریشه:** trend_score از range_model_role ارث برد → num_classes=2
→ Dense(2, linear). ولی score فقط ۱عدد است نه ۲عدد.

**رفع:**
- num_classes=1 برای trend_score (validated: 1/2/3)
- activation: linear → tanh (خروجی bounded −1..+1)
- Dense باقی ماند (بعد از GlobalAvgPool داده flat است — Conv1D معادل است)

### فاز ۹۸-ب (رفع): /data برای همهٔ ۳ نوع مدل ترند خروجی مخصوص

endpoint `/api/trend-forecast` و `fetchTrendColor` بازنویسی شدند تا
سه نوع مدل ترند را تشخیص داده و خروجی مخصوص هر کدام را برگردانند:

| مدل | target_units | خروجی |
|-----|-------------|-------|
| gold_trend_score_* | score | Score + direction + strength |
| gold_trend_signal_* | trend_signal | SELL/HOLD/BUY احتمالات |
| gold_trend_<tf> | color | GREEN/RED + درصد |

### فاز ۹۸-ب (تأیید): معماری trend_score — Dense(1, tanh) تأیید شد

تأیید برنامه‌نویسی: build_wavenet با output_units=1, activation='tanh',
is_regression=True → output shape=(None, 1), activation=tanh ✓
total params: 417,169 (4×3 blocks, 288×184, n_filters=48)

معماری: range pipeline کامل (WaveNet blocks + Huber + MAE) با فقط
یک خروجی score به‌جای دو خروجی High/Low — دقیقاً همان چیزی که
اپراتور خواسته بود.

### فاز ۹۸-ب (معماری): trend_score از معماری کامل range (seq2seq) استفاده می‌کند

**درخواست اپراتور:** معماری trend_score باید مثل range باشد — با WaveNet
blocks کامل + seq2seq head، فقط با 1 خروجی به‌جای 2.

**قبلی (غلط):** seq2seq=False → Dense head (فقط آخرین timestep + GlobalAvg)
**جدید (درست):** seq2seq=True → همهٔ WaveNet blocks + seq2seq_pre + seq2seq_out

**تغییرات:**
- build_wavenet: output_channels param (None = horizon×2 مثل قبل، 1 = score)
- trend_score: seq2seq=True + output_channels=1 → خروجی (None, 288, 1) با tanh
- range: خروجی (None, 150, 2) با linear — بدون تغییر
- trainer + service: output_channels پاس داده می‌شود

تأیید: build_wavenet OK برای هر دو مدل ✓

### فاز ۹۸-ب (رفع): /data inspector model_role → "range" برای trend_score

تست سرتاسری: forecast_at با مدل 184-فیچری و 1-خروجی tanh → ✅
inspector model_role از signal به range تغییر کرد (trend_score = 184 فیچر).

### فاز ۹۸-ب (رفع): آمار کامل تارگت score قبل از آموزش

قبلاً فقط `{'mean_score': 0.031}` چاپ می‌شد — بدون هیچ اطلاعی از
توزیع. حالا آمار کامل چاپ می‌شود:
- min / p25 / median / p75 / max
- توزیع BUY (>+0.1) / SELL (<−0.1) / HOLD

این به اپراتور نشان می‌دهد که تارگت واقعی چه شکلی است و آیا
قابل‌پیش‌بینی هست یا نه.

## تحلیل: score ثابت برای همه کندل‌ها — مسئله مدل، نه کد

**گزارش اپراتور:** score برای همه کندل‌ها یکسان می‌آید.

**تشخیص:** سرور و cache درست کار می‌کنند (feature_key شامل bar_index).
مشکل از خود مدل است:
- تارگت score نزدیک صفر (median +0.014)
- رانش یک‌روزه ذاتاً غیرقابل پیش‌بینی (autocorr ≈ −0.02)
- Huber loss بهینه = median ≈ 0
- tanh خروجی را به وسط فشار می‌دهد
- مدل converge به score ≈ 0 → برای همه کندل‌ها تقریباً یکسان

این مدلِ بی‌لبه است نه باگ نرم‌افزاری. برای لبه واقعی:
- فیچرهای رژیم‌محور (session، day-of-week، volatility regime)
- بکتست با score آستانه‌بندی‌شده (score > 0.2 فقط خرید)
- ترکیب با فیلترهای EMA50/session که قبلاً WR 36-49% نشان دادند

## 2026-09-08 — Phase 116/119 roadmap refresh and GUI cleanup

در پاسخ به درخواست اپراتور برای بررسی عمیق‌تر مدل‌ها/معماری‌ها و خلوت‌کردن GUI:

- گزارش جدید اضافه شد:
  - `docs/Report/PHASE116_DEEP_MODEL_ARCHITECTURE_RESEARCH_AND_ROADMAP.md`
- فازهای جدید اضافه شدند:
  - `docs/Phases/Phase116.md` — Hybrid Range-Aware Decision Engine
  - `docs/Phases/Phase117.md` — Advanced Neural Architecture Benchmarks
  - `docs/Phases/Phase118.md` — Tick/Order-book optional branch
  - `docs/Phases/Phase119.md` — GUI cleanup completed
- `docs/Phases/README_PHASE100_115.md` تا فاز ۱۱۹ به‌روزرسانی شد.
- فازهای ۱۱۱/۱۱۳/۱۱۴/۱۱۵ با نقش مدل‌های range موجود و مسیر ensemble تکمیل شدند.
- `docs/CURRENT_STATE.md` با نقشهٔ جدید مدل ترکیبی آپدیت شد.
- GUI بدون حذف قابلیت‌ها خلوت شد:
  - `CommandField.advanced` اضافه شد.
  - fieldهای کم‌مصرف/حرفه‌ای در Train/Retrain/Optimise/Backtest/Replay/Audit/Calibration زیر `Advanced options` رفتند.
  - handlerها و defaults تغییر رفتاری ندارند؛ fieldها همچنان submit می‌شوند.
- تست GUI اضافه شد که وجود `Advanced options` و fieldهای معماری مثل `n_layers/n_blocks` را تضمین می‌کند.

تصمیم فنی ثبت‌شده:

```text
مدل نهایی نباید یک مدل تنها باشد؛ مسیر درست:
WaveNet trend_signal + Booster branch + BUY/SELL specialists + range_1d envelope + range_4h TP/SL + meta/conformal no-trade gate.
```

### Quality gate — 2026-09-08

Targeted checks for touched GUI/code files:

```text
python3 -m ruff check src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/web/renderer.py tests/integration/test_gui_coverage.py  ✅
python3 -m black --check src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/web/renderer.py tests/integration/test_gui_coverage.py  ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py tests/unit/presentation/test_commands.py  ✅
PYTHONPATH=src python3 -m pytest -q  ✅
```

Full gate state remains honest:

```text
python3 -m ruff check .      ❌ 219 pre-existing errors, mainly notebook/import formatting and long lines in feature catalogue/scripts.
python3 -m black --check .   ❌ 21 pre-existing files would be reformatted.
PYTHONPATH=src python3 -m mypy src ❌ 28 pre-existing errors in 10 files.
python3 -m pytest -q         ✅ passed.
```

## 2026-09-08 — Runtime status clarification for Phase108/Phase109

اپراتور یادآوری کرد که روی سیستم خودش هنوز training فاز ۱۰۸ (`trend_signal` با class weights/F1 metrics) در حال اجراست و نتیجهٔ نهایی ارسال نشده است. بنابراین Docs شفاف‌تر شد:

```text
Phase108 = کد/GUI کامل، اجرای واقعی روی سیستم اپراتور هنوز in progress
Phase109 = کد/GUI calibration کامل، اجرای عملیاتی فقط بعد از پایان train و ذخیره مدل جدید
```

فایل‌های به‌روزرسانی‌شده:

```text
docs/Phases/README_PHASE100_115.md
docs/Phases/Phase109.md
docs/CURRENT_STATE.md
docs/Report/PHASE116_DEEP_MODEL_ARCHITECTURE_RESEARCH_AND_ROADMAP.md
docs/SESSION_HANDOFF_2026-09-07.md
```

## 2026-09-08 — GUI monitor metric for trend_signal pilots

اپراتور گفت training را از GUI اجرا می‌کند و برای تست trend_signal نیاز دارد `--monitor-metric val_buy_sell_f1` را از داشبورد تنظیم کند. GUI قبلاً این knob را نشان نمی‌داد.

تغییرات:

```text
- گزینهٔ Monitor metric به Train a model / Retrain a saved model / Find best learning rate اضافه شد.
- گزینه زیر Advanced options نمایش داده می‌شود تا GUI شلوغ نشود.
- مقدارهای مجاز: auto, val_loss, val_mae, val_macro_f1, val_buy_sell_f1
- برای trend_signal می‌توان val_buy_sell_f1 را پاس داد.
- role-gate اضافه شد تا metricهای classification-only اشتباهی به range/trend_score پاس نشوند.
```

تست‌ها:

```text
python3 -m ruff check src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
python3 -m black --check src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py::TestDashboardPage::test_advanced_command_fields_are_collapsed ✅
```

## 2026-09-08 — Phase 120/121 anti-collapse metrics and booster branch

بعد از pilotهای WaveNet روی `trend_signal` مشخص شد مدل یا uniform collapse می‌کند یا فقط یک کلاس مثل BUY/SELL را predict می‌کند. بنابراین قبل از ادامهٔ آموزش‌های سنگین، زیرساخت ضد-collapse و branch بوستر اضافه شد.

### Phase120 — anti-collapse metrics

اضافه شد:

```text
val_sell_predicted / val_hold_predicted / val_buy_predicted
val_predicted_class_count
val_single_class_collapse
val_action_min_f1
val_action_min_recall
val_action_min_f1_supported
val_action_min_recall_supported
val_action_supported_class_count
val_action_predicted_supported_count
val_action_collapse
```

`--monitor-metric` حالا این‌ها را هم می‌پذیرد:

```text
val_action_min_f1
val_action_min_f1_supported
```

### Phase121 — trend_signal booster branch

فایل‌های جدید:

```text
src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py
scripts/train_trend_signal_boosters.py
requirements-boosters.txt
docs/Phases/Phase120.md
docs/Phases/Phase121.md
```

GUI command جدید:

```text
Train trend-signal booster
```

پشتیبانی:

```text
--booster auto|lightgbm|xgboost|catboost
--output-mode multiclass|buy|sell
--summary-mode last|basic|multi_scale
```

نکته: dependencyهای بوستر optional هستند و برای اجرا باید نصب شوند:

```text
pip install -r requirements-boosters.txt
```

### Quality gate — Phase120/121

Targeted checks:

```text
python3 -m ruff check scripts/run_dual_models.py scripts/train_trend_signal_boosters.py src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py src/ShadBotTrader/infrastructure/ai/model_catalogue.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_classification_weights_metrics.py tests/unit/ai/test_tabular_window_summary.py tests/unit/ai/test_trend_signal_booster_script.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
python3 -m black --check scripts/run_dual_models.py scripts/train_trend_signal_boosters.py src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py src/ShadBotTrader/infrastructure/ai/model_catalogue.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_classification_weights_metrics.py tests/unit/ai/test_tabular_window_summary.py tests/unit/ai/test_trend_signal_booster_script.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
PYTHONPATH=src python3 -m mypy src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py src/ShadBotTrader/infrastructure/ai/model_catalogue.py ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/ai/test_classification_weights_metrics.py tests/unit/ai/test_tabular_window_summary.py tests/unit/ai/test_trend_signal_booster_script.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered ✅
PYTHONPATH=src python3 -m pytest -q ✅
```

Full gate state remains:

```text
python3 -m ruff check .      ❌ 219 pre-existing errors outside the touched files.
python3 -m black --check .   ❌ 21 pre-existing files would be reformatted.
PYTHONPATH=src python3 -m mypy src ❌ 28 pre-existing errors in 10 files.
python3 -m pytest -q         ✅ passed.
```

## 2026-09-08 — Phase 122 booster specialist threshold calibration

بعد از اجرای اپراتور برای BUY و SELL specialist، هر دو مدل LightGBM ذخیره شدند:

```text
gold_buy_lightgbm_basic_5m  v1
gold_sell_lightgbm_basic_5m v1
```

نتایج specialistها نشان دادند مسیر booster از WaveNet سالم‌تر است، ولی برای تصمیم معاملاتی باید threshold مشترک BUY/SELL پیدا شود.

اضافه شد:

```text
scripts/calibrate_trend_signal_boosters.py
CommandKind.CALIBRATE_TREND_SIGNAL_BOOSTERS
GUI card: Calibrate booster specialists
docs/Phases/Phase122.md
tests/unit/ai/test_trend_signal_booster_calibration.py
```

منطق تصمیم:

```text
BUY  اگر buy_prob >= buy_threshold و buy_prob - sell_prob >= min_margin
SELL اگر sell_prob >= sell_threshold و sell_prob - buy_prob >= min_margin
هر دو یا هیچکدام → no trade
```

خروجی:

```text
run_logs/trend_signal_booster_thresholds/latest.csv
run_logs/trend_signal_booster_thresholds/latest.html
run_logs/trend_signal_booster_thresholds/latest.json
```

### Quality gate — Phase122

Targeted checks:

```text
python3 -m ruff check scripts/calibrate_trend_signal_boosters.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_trend_signal_booster_calibration.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
python3 -m black --check scripts/calibrate_trend_signal_boosters.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_trend_signal_booster_calibration.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/ai/test_trend_signal_booster_calibration.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered ✅
PYTHONPATH=src python3 -m pytest -q ✅
```

Full gate remains pre-existing red except pytest:

```text
python3 -m ruff check .      ❌ 219 pre-existing errors.
python3 -m black --check .   ❌ 21 pre-existing files would be reformatted.
PYTHONPATH=src python3 -m mypy src ❌ 28 pre-existing errors in 10 files.
python3 -m pytest -q         ✅ passed.
```

## 2026-09-08 — Phase 123 hybrid XGBoost matrix with WaveNet and range outputs

در پاسخ به ایدهٔ اپراتور که به جای ensemble ساده، خروجی مدل‌ها به یک ماتریس داده شود تا XGBoost تصمیم نهایی را یاد بگیرد، فاز ۱۲۳ اضافه شد.

اضافه شد:

```text
scripts/build_hybrid_xgboost_matrix.py
CommandKind.BUILD_HYBRID_XGBOOST_MATRIX
GUI card: Build hybrid XGBoost matrix
docs/Phases/Phase123.md
tests/unit/ai/test_hybrid_xgboost_matrix.py
```

ماتریس خروجی شامل این خانواده featureهاست:

```text
BUY/SELL specialist probabilities
multiclass booster probabilities
optional WaveNet trend_signal probabilities
range_1d room/features
range_4h room/features
true label
```

خروجی:

```text
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_v1.parquet
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
run_logs/hybrid_xgboost_matrix/latest.json
```

اصل علیت range:

```text
برای هر سیگنال 5M فقط آخرین کندل بسته‌شدهٔ 1D/4H استفاده می‌شود:
range_open_time + range_delta <= signal_time
```

### Quality gate — Phase123

Targeted checks:

```text
python3 -m ruff check scripts/build_hybrid_xgboost_matrix.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_xgboost_matrix.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
python3 -m black --check scripts/build_hybrid_xgboost_matrix.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_xgboost_matrix.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/ai/test_hybrid_xgboost_matrix.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered ✅
PYTHONPATH=src python3 -m pytest -q ✅
PYTHONPATH=src python3 -m py_compile scripts/build_hybrid_xgboost_matrix.py ✅
```

Full ruff/black/mypy state remains the same pre-existing red state documented earlier; full pytest is green.

## 2026-09-08 — Phase 124 hybrid XGBoost head trainer

بعد از ساخت ماتریس فاز ۱۲۳، CLI آموزش head نهایی اضافه شد:

```text
scripts/train_hybrid_xgboost_head.py
```

این اسکریپت ماتریس زیر را می‌خواند:

```text
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
```

و یک مدل نهایی LightGBM/XGBoost/CatBoost روی featureهای خروجی مدل‌ها و range می‌سازد. خروجی فعلی سه‌کلاسه است:

```text
SELL / HOLD / BUY
```

که در decision نهایی، HOLD یعنی NO_TRADE.

پیش‌فرض، price-levelهای مستقیم مثل `close` و `*_price` را حذف می‌کند تا وابستگی خام به سطح قیمت کمتر شود، ولی room/pct/probabilityها باقی می‌مانند.

### Quality gate — Phase124

Targeted checks:

```text
python3 -m ruff check scripts/train_hybrid_xgboost_head.py tests/unit/ai/test_hybrid_xgboost_head.py scripts/build_hybrid_xgboost_matrix.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_xgboost_matrix.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
python3 -m black --check scripts/train_hybrid_xgboost_head.py tests/unit/ai/test_hybrid_xgboost_head.py ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/ai/test_hybrid_xgboost_head.py tests/unit/ai/test_hybrid_xgboost_matrix.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered ✅
PYTHONPATH=src python3 -m py_compile scripts/train_hybrid_xgboost_head.py scripts/build_hybrid_xgboost_matrix.py ✅
PYTHONPATH=src python3 -m pytest -q ✅
```

## 2026-09-08 — Operational status after Phase123 matrix build

اپراتور خروجی اجرای Phase123 را ارسال کرد و وضعیت عملیاتی در `docs/CURRENT_STATE.md` به‌روزرسانی شد.

نتیجهٔ ماتریس hybrid:

```text
path latest : datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
rows        : 8000
columns     : 45
scope       : holdout
labels      : sell=2687, hold=1789, buy=3524
warnings    : []
```

وضعیت مسیر:

```text
WaveNet trend_signal خام = no-edge/collapse، optional only
Booster multiclass + BUY/SELL specialists = مسیر فعال
Phase122 calibration = انجام شده، precision خام 48.65% و aggressive coverage 97.39%
Phase123 matrix = ساخته شد و آمادهٔ Phase124
Next = train_hybrid_xgboost_head.py و ارسال run_logs/hybrid_xgboost_head/latest.json
```

## 2026-09-08 — Phase124 hybrid head real run received

اپراتور خروجی اجرای واقعی `scripts/train_hybrid_xgboost_head.py` را ارسال کرد.

مدل ذخیره‌شده:

```text
gold_hybrid_lightgbm_head_5m v1
record: datasets/models/gold_hybrid_lightgbm_head_5m/v1_training.json
matrix: datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
rows/features: 8000 / 36
train/val: 5600 / 2400
```

نتیجهٔ validation:

```text
val_accuracy              = 43.79%
val_balanced_accuracy     = 46.23%
val_macro_f1              = 0.4380
val_buy_sell_f1           = 0.4570
val_action_min_f1         = 0.4517
val_action_min_f1_supported = 0.4517
val_action_collapse       = 0
predicted_class_count     = 3
```

Per-class:

```text
SELL P/R/F1 = 48.68% / 44.02% / 0.4623
HOLD P/R/F1 = 30.93% / 56.59% / 0.4000
BUY  P/R/F1 = 55.49% / 38.09% / 0.4517
```

برداشت فنی:

```text
- head نهایی collapse نکرده و هر سه کلاس را predict کرده است.
- نسبت به booster-only strict score قبلی (0.4367)، action_min_f1 به 0.4517 رسید؛ بهبود کوچک ولی واقعی در معیار ضد-collapse.
- accuracy از majority خام validation پایین‌تر است، ولی balanced/macro/action metrics مهم‌ترند چون کلاس‌ها skew هستند.
- action precision تقریبی روی BUY/SELL ≈ 52.8% است و coverage اکشن ≈ 58.9%؛ نسبت به calibration خام فاز 122 که precision=48.65% و coverage=97.39% داشت، محافظه‌کارتر و تمیزتر است.
```

قدم بعدی پیشنهادی:

```text
Phase125 — calibrate hybrid head thresholds and run range-aware TP/SL backtest.
```

## 2026-09-09 — Phase125 hybrid head range TP/SL backtest

فاز ۱۲۵ پیاده‌سازی شد تا مدل `gold_hybrid_lightgbm_head_5m` از حالت classification-only وارد تست معاملاتی شود.

اضافه شد:

```text
scripts/backtest_hybrid_xgboost_head.py
CommandKind.BACKTEST_HYBRID_XGBOOST_HEAD
GUI card: Backtest hybrid XGBoost head
docs/Phases/Phase125.md
tests/unit/ai/test_hybrid_head_backtest.py
```

منطق:

```text
hybrid probabilities → threshold grid → BUY/SELL/NO_TRADE
BUY:  TP=min(range_4h_high, range_1d_high), SL=range_4h_low
SELL: TP=max(range_4h_low, range_1d_low),  SL=range_4h_high
entry = next 5M open with spread/slippage
future path scanned for max_hold_bars (default 48 = 4h)
```

خروجی:

```text
run_logs/hybrid_head_backtest/latest.csv
run_logs/hybrid_head_backtest/latest.json
```

### Quality gate — Phase125

Targeted checks:

```text
python3 -m ruff check scripts/backtest_hybrid_xgboost_head.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_head_backtest.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
python3 -m black --check scripts/backtest_hybrid_xgboost_head.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_head_backtest.py tests/unit/presentation/test_architecture_knobs_gui.py ✅
PYTHONPATH=src python3 -m pytest -q tests/unit/ai/test_hybrid_head_backtest.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered ✅
PYTHONPATH=src python3 -m py_compile scripts/backtest_hybrid_xgboost_head.py ✅
PYTHONPATH=src python3 -m pytest -q ✅
```

Full gate remains pre-existing red except pytest:

```text
python3 -m ruff check .      ❌ 219 pre-existing errors outside touched files.
python3 -m black --check .   ❌ 21 pre-existing files would be reformatted.
PYTHONPATH=src python3 -m mypy src ❌ 28 pre-existing errors in 10 files.
python3 -m pytest -q         ✅ passed.
```

## 2026-09-09 — Phase125 real backtest results received

اپراتور دو اجرای واقعی از `scripts/backtest_hybrid_xgboost_head.py` ارسال کرد.

### اجرای ۱ — score_metric=total_pnl، بدون فیلتر room سخت‌گیرانه

```text
model      : gold_hybrid_lightgbm_head_5m v1
samples    : 2400
best th    : buy=0.80 sell=0.65 margin=0.00
trades     : 344 (coverage=14.33%)
buy/sell   : 170 / 174
wins/losses: 172 / 172
label_precision: 66.57%
total_pnl  : +266.03
avg_pnl    : +0.7733
profit_factor: 1.2199
max_drawdown : 355.58
```

### اجرای ۲ — conservative filters، score_metric=precision_then_pnl، save_record=0

تنظیمات مهم:

```text
min_margin=0.05
min_4h_room=2
min_1d_room=5
min_tp_distance=2
min_sl_distance=2
precision_floor=0.55
score_metric=precision_then_pnl
```

خروجی منتخب توسط score precision-first:

```text
best th    : buy=0.95 sell=0.75 margin=0.05
trades     : 90 (coverage=3.75%)
label_precision: 83.33%
total_pnl  : -8.52
profit_factor: 0.9719
max_drawdown : 135.29
```

اما در همان grid، بهترین نتیجهٔ معاملاتی مثبت‌تر با فیلترهای محافظه‌کارانه:

```text
buy=0.80 sell=0.65 margin=0.05
trades=325
buy/sell=160/165
win_rate=51.69%
label_precision=65.85%
total_pnl=+291.15
avg_pnl=+0.8959
profit_factor=1.2472
max_drawdown=347.04
coverage=13.54%
```

برداشت:

```text
- فاز ۱۲۵ edge معاملاتی اولیه نشان داد؛ برخلاف classification-only، PnL هم مثبت شد.
- threshold پایدار فعلی نزدیک buy=0.80 / sell=0.65 است.
- فیلترهای room محافظه‌کارانه نتیجه را کمی بهتر کردند (+291 vs +266) و PF را بالا بردند.
- score_metric=precision_then_pnl می‌تواند threshold با precision بالا ولی PnL منفی را انتخاب کند؛ برای ذخیرهٔ production فعلاً بهتر است total_pnl با precision_floor/min_profit_factor استفاده شود.
```

پیشنهاد بعدی:

```text
rerun Phase125 with:
score_metric=total_pnl
min_margin=0.05
min_4h_room=2
min_1d_room=5
min_tp_distance=2
min_sl_distance=2
precision_floor=0.60
min_profit_factor=1.05
save_record=1
```

سپس Phase113 significance/random baseline قبل از live integration.

## 2026-09-09 — Phase 125B saved profitable hybrid-head threshold

کاربر rerun فاز ۱۲۵ را با قیود سخت‌تر و `save_record=1` اجرا کرد:

```text
score_metric=total_pnl
min_margin=0.05
min_trades=100
precision_floor=0.60
min_profit_factor=1.05
min_4h_room=2
min_1d_room=5
min_tp_distance=2
min_sl_distance=2
max_hold_bars=48
spread_mode=pct
spread_value=0.06
same_bar_policy=stop_first
```

نتیجهٔ انتخاب‌شده و ذخیره‌شده:

```text
model_version : 1
matrix_rows   : 8000
eval_rows     : 2400
best th       : buy=0.80 sell=0.65 margin=0.05
trades        : 325 / 2400 (coverage=13.5417%)
buy/sell      : 160 / 165
wins/losses   : 168 / 157
timeouts      : 44
label_correct : 214
false_positive: 111
win_rate      : 51.6923%
label_precision: 65.8462%
total_pnl     : +291.154987683185
avg_pnl       : +0.8958615005636462
profit_factor : 1.2471739846573604
max_drawdown  : 347.044035279524
record_path   : datasets\models\gold_hybrid_lightgbm_head_5m\v1_training.json
```

برداشت دقیق:

```text
- قیود سخت‌تر همان candidate عملی مطلوب را انتخاب کرد.
- threshold حالا طبق خروجی کاربر در رکورد مدل ذخیره شده است.
- این هنوز مجوز live نیست؛ چون چندین grid/model تست شده و باید significance/random baseline اجرا شود.
```

## 2026-09-09 — Phase 113 implementation: hybrid-head random significance check

فاز ۱۱۳ از حالت پیشنهاد به پیاده‌سازی عملی برای مسیر hybrid-head/range-aware رسید.

فایل‌های اضافه/تغییرکرده:

```text
scripts/backtest_significance_check.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_significance_check.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase113.md
```

قابلیت‌ها:

```text
- بارگذاری threshold از decision_thresholds رکورد مدل یا از CLI/Phase125 JSON
- اجرای دوباره observed hybrid-head backtest با همان منطق فاز ۱۲۵
- ساخت BUY/SELL random trade pool فقط از candidateهایی که با همان range filters و TP/SL قابل اجرا هستند
- match کردن تعداد BUY و SELL random با مدل مشاهده‌شده
- Monte Carlo p-value با فرمول plus-one
- White Reality-style max check روی ردیف‌های معتبر threshold grid فاز ۱۲۵
- خروجی run_logs/significance_checks/latest.json و latest.csv
```

دستور پیشنهادی کاربر:

```powershell
python -u scripts/backtest_significance_check.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --trials 1000 `
  --seed 42 `
  --white-check 1 `
  --candidate-rows-path run_logs/hybrid_head_backtest/latest.json `
  --storage-root datasets
```

Quality gate اجراشده برای فایل‌های touched:

```text
python -m ruff check scripts/backtest_significance_check.py tests/unit/ai/test_significance_check.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/backtest_significance_check.py tests/unit/ai/test_significance_check.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_significance_check.py tests/unit/ai/test_hybrid_head_backtest.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 62 passed
```

Full gate هنوز به‌علت بدهی‌های قدیمی repo قرمز است و جداگانه ثبت می‌شود.

Full quality gate بعد از Phase113 implementation:

```text
python -m pytest
# 1669 passed, 54 skipped in 263.92s

python -m ruff check .
# FAIL: 219 pre-existing lint errors
# examples:
#   ShadBotTrader_Colab.ipynb:cell 5 E401/I001/F541
#   scripts/fetch_1d_gold_yahoo.py:65 E501
#   scripts/find_best_lr.py:123 F401
#   src/ShadBotTrader/infrastructure/feature/standard_catalog.py:770-787 E501

python -m black --check .
# FAIL: 21 pre-existing files would be reformatted
# examples:
#   scripts/fetch_1d_gold_yahoo.py
#   scripts/find_best_lr.py
#   src/ShadBotTrader/infrastructure/ai/feature_matrix.py
#   src/ShadBotTrader/infrastructure/feature/standard_catalog.py
#   tests/integration/test_data_inspector.py

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
# examples:
#   domain/simulation/replay.py object comparison
#   infrastructure/ai/target_builder.py optional list indexing
#   infrastructure/simulation/dual_model_prediction_source.py Candle | None
#   infrastructure/feature/calculators/price_context.py FeatureResult/FeatureDefinition mismatch
#   infrastructure/ai/window_generator.py seq2seq return types
#   infrastructure/ai/wavenet/wavenet_trainer.py tf.keras type names
#   application/services/dual_model_service.py dict float/int
#   presentation/commands/handlers.py existing tuple[int,str]|None issue
#   presentation/web/server.py missing returns
```

## 2026-09-09 — Phase 113 significance result: passed strongly

کاربر خروجی `run_logs/significance_checks/latest.json` را ارسال کرد. فاز ۱۱۳ روی threshold ذخیره‌شدهٔ فاز ۱۲۵ اجرا شد:

```text
threshold_source: model_record:gold_hybrid_lightgbm_head_5m:v1
buy_threshold  : 0.80
sell_threshold : 0.65
min_margin     : 0.05
matrix_rows    : 8000
eval_rows      : 2400
trials         : 1000
seed           : 42
white_check    : 1
```

Observed hybrid-head/range-aware result:

```text
trades         : 325
buy/sell       : 160 / 165
wins/losses    : 168 / 157
timeouts       : 44
win_rate       : 51.6923%
label_precision: 65.8462%
total_pnl      : +291.154987683185
avg_pnl        : +0.8958615005636462
profit_factor  : 1.2471739846573604
max_drawdown   : 347.044035279524
coverage       : 13.5417%
```

Random same-count/same-filter baseline:

```text
trade_pool.buy_candidates : 960
trade_pool.sell_candidates: 1175
random_mean               : -944.2369557544658
random_stdev              : 174.3501617266993
random_p95                : -665.0864972670641
random_p99                : -529.5757005996354
random_max                : -317.02241025066814
random_probability_positive: 0.0
random_better_or_equal    : 0 / 1000
random_p_value            : 0.000999000999000999
```

White Reality-style max check over valid Phase125 candidates:

```text
white_candidate_count     : 23
white_mean_max            : -346.06975128145194
white_p95                 : -193.67326141904985
white_p99                 : -128.05536537052174
white_max                 : -28.658925889975762
white_probability_positive: 0.0
white_better_or_equal     : 0 / 1000
white_p_value             : 0.000999000999000999
```

برداشت:

```text
- observed +291.15 نه‌تنها از میانگین random بهتر است، بلکه از بهترین random trial هم حدود +608.18 دلار بالاتر است.
- در White-style max check هم حتی بهترین max تصادفی بین 23 candidate معتبر به مثبت نرسید.
- p-value با 1000 trial به حداقل قابل مشاهده رسید: 1/(1000+1)=0.000999.
- بنابراین Phase113 برای این holdout و همین هزینه/TP/SL با قدرت پاس شد.
```

محدودیت باقی‌مانده:

```text
این هنوز فقط یک holdout تاریخی است. قبل از live واقعی باید Phase116 integration و سپس Phase115 live decision audit/paper validation انجام شود.
```

## 2026-09-09 — Phase 116 implementation: hybrid range-aware decision integration

Phase116 v1 پیاده‌سازی شد تا خروجی research فازهای ۱۲۵/۱۱۳ وارد مسیر استاندارد decision پروژه شود، بدون redesign.

فایل‌های جدید/تغییرکرده:

```text
src/ShadBotTrader/domain/ai/prediction_target.py
src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py
src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py
src/ShadBotTrader/infrastructure/trading/__init__.py
scripts/audit_hybrid_range_aware_decisions.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_prediction_target.py
tests/unit/ai/test_hybrid_head_predictor.py
tests/unit/strategy/test_hybrid_range_aware_strategy.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase116.md
docs/Phases/README_PHASE100_115.md
```

اجزای اصلی:

```text
HybridHeadForecast:
  سه کلاس sell/hold/buy با ترتیب 0/1/2 و marginهای buy/sell.

HybridHeadPredictor:
  artifact pickled فاز ۱۲۴ را load می‌کند و predict_proba را به ترتیب sell/hold/buy align می‌کند.

HybridRangeAwareStrategy:
  threshold ذخیره‌شدهٔ Phase125 را با range_1d و range_4h اعمال می‌کند و یک TradingSignal استاندارد می‌دهد.

Audit CLI:
  scripts/audit_hybrid_range_aware_decisions.py
  HybridRangeAwareStrategy -> PositionAwareDecisionEngine -> PolicyRiskGate -> DefaultIntentFactory
```

قانون اجرایی Phase116 v1:

```text
BUY:
  buy_prob >= 0.80
  buy_prob - sell_prob >= 0.05
  buy_prob - hold_prob >= 0.05
  4H up room >= 2
  1D up room >= 5
  TP = min(range_4h_high, range_1d_high)
  SL = range_4h_low

SELL:
  sell_prob >= 0.65
  sell_prob - buy_prob >= 0.05
  sell_prob - hold_prob >= 0.05
  4H down room >= 2
  1D down room >= 5
  TP = max(range_4h_low, range_1d_low)
  SL = range_4h_high
```

خروجی audit:

```text
run_logs/hybrid_decision_audit/latest.json
run_logs/hybrid_decision_audit/latest.csv
```

دستور پیشنهادی روی ماشین کاربر:

```powershell
python -u scripts/audit_hybrid_range_aware_decisions.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-windows 0 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --capital 10000 `
  --base-quantity 1 `
  --storage-root datasets
```

انتظار sanity-check:

```text
trade_intents ≈ 325
buy_intents ≈ 160
sell_intents ≈ 165
label_precision ≈ 65.85%
coverage ≈ 13.54%
```

اگر audit با Phase125 اختلاف بزرگ داشته باشد، قبل از Phase115 باید debug شود.

Quality gate بعد از Phase116:

```text
python -m ruff check src/ShadBotTrader/domain/ai/prediction_target.py src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py src/ShadBotTrader/infrastructure/trading/__init__.py scripts/audit_hybrid_range_aware_decisions.py tests/unit/ai/test_prediction_target.py tests/unit/ai/test_hybrid_head_predictor.py tests/unit/strategy/test_hybrid_range_aware_strategy.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check src/ShadBotTrader/domain/ai/prediction_target.py src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py src/ShadBotTrader/infrastructure/trading/__init__.py scripts/audit_hybrid_range_aware_decisions.py tests/unit/ai/test_prediction_target.py tests/unit/ai/test_hybrid_head_predictor.py tests/unit/strategy/test_hybrid_range_aware_strategy.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_prediction_target.py tests/unit/ai/test_hybrid_head_predictor.py tests/unit/strategy/test_hybrid_range_aware_strategy.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 91 passed

python -m pytest
# 1685 passed, 54 skipped in 193.75s

python -m mypy src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py
# PASS
```

Full gate وضعیت صادقانه:

```text
python -m ruff check .
# FAIL: 219 خطای قدیمی، نمونه‌ها همان ShadBotTrader_Colab.ipynb، scripts/find_best_lr.py، scripts/fetch_1d_gold_yahoo.py و standard_catalog.py هستند.

python -m black --check .
# FAIL: 21 فایل قدیمی would be reformatted.

python -m mypy src
# FAIL: 28 خطای قدیمی در 10 فایل؛ فایل جدید hybrid_head_predictor دیگر خطای mypy ندارد.
```

گزارش فاز ۱۱۶ نیز اضافه شد:

```text
docs/Report/PHASE116_HYBRID_RANGE_AWARE_INTEGRATION_REPORT.md
```

## 2026-09-09 — Phase 116 audit result: runtime integration matched Phase125

کاربر خروجی `run_logs/hybrid_decision_audit/latest.json` را ارسال کرد. مسیر runtime فاز ۱۱۶ با threshold ذخیره‌شدهٔ فاز ۱۲۵ اجرا شد:

```text
model_id       : gold_hybrid_lightgbm_head_5m
model_version  : 1
threshold_src  : model_record:gold_hybrid_lightgbm_head_5m:v1
threshold      : buy=0.80 sell=0.65 margin=0.05
matrix_rows    : 8000
eval_rows      : 2400
config         : min_4h_room=2, min_1d_room=5, min_tp_distance=2, min_sl_distance=2, spread_mode=pct, spread_value=0.06, slippage=0
```

Summary:

```text
rows           : 2400
trade_intents  : 325
no_trade       : 2075
buy_intents    : 160
sell_intents   : 165
label_correct  : 214
label_precision: 0.6584615384615384
coverage       : 0.13541666666666666
```

مقایسه با Phase125 best:

```text
Phase125 trades       : 325
Phase116 trade_intents: 325
Phase125 buy/sell     : 160 / 165
Phase116 buy/sell     : 160 / 165
Phase125 precision    : 0.6584615384615384
Phase116 precision    : 0.6584615384615384
Phase125 coverage     : 0.13541666666666666
Phase116 coverage     : 0.13541666666666666
```

نتیجه:

```text
Phase116 integration sanity-check PASS.
Runtime Strategy -> DecisionEngine -> RiskGate -> IntentFactory دقیقاً همان تصمیم‌های Phase125 را تولید کرد.
گام بعدی مجاز: Phase115 live decision audit / paper shadow. live واقعی هنوز ممنوع است.
```

Quality re-check بعد از ثبت نتیجهٔ audit کاربر:

```text
python -m ruff check <Phase116 touched files>
# PASS

python -m black --check <Phase116 touched files>
# PASS

python -m pytest tests/unit/ai/test_prediction_target.py tests/unit/ai/test_hybrid_head_predictor.py tests/unit/strategy/test_hybrid_range_aware_strategy.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 91 passed

python -m pytest
# 1685 passed, 54 skipped in 200.80s
```

## 2026-09-09 — Workspace cleanup + full 5M hybrid backtest report GUI

کاربر خواست workspace خلوت شود و قبل از Phase115 یک backtest کامل‌تر روی دیتای 5M با نمایش GUI/HTML داشته باشیم.

Cleanup انجام‌شده در workspace:

```text
قبل از cleanup: /home/user حدود 158M، شامل 14 فایل zip قدیمی
بعد از cleanup: /home/user حدود 50M
حذف شد: /home/user/ShadBotTrader_Phase*.zip های قدیمی و cacheهای pytest/ruff/mypy
```

پیاده‌سازی اضافه‌شده:

```text
scripts/report_hybrid_full_backtest.py
GUI command: Full hybrid 5M backtest report
tests/unit/ai/test_hybrid_full_backtest_report.py
```

این report برخلاف Phase125 threshold search انجام نمی‌دهد؛ threshold ذخیره‌شدهٔ مدل را می‌خواند و همان rule را fixed روی کل matrix انتخاب‌شده اجرا می‌کند:

```text
threshold source: datasets/models/gold_hybrid_lightgbm_head_5m/v1_training.json
BUY/SELL gates  : buy=0.80 sell=0.65 margin=0.05
TP/SL logic     : همان Phase125
outputs         : run_logs/hybrid_full_backtest/latest.html, latest.json, latest.csv
```

برای full واقعی کل دیتای 5M، ابتدا باید matrix با scope=all ساخته شود:

```powershell
python -u scripts/build_hybrid_xgboost_matrix.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --scope all `
  --max-windows 0 `
  --summary-mode basic `
  --booster lightgbm `
  --include-specialists 1 `
  --include-multiclass-booster 1 `
  --include-wavenet 1 `
  --require-wavenet 0 `
  --include-range 1 `
  --require-range 1 `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --output-name hybrid_xgboost_matrix_all_5m `
  --storage-root datasets
```

سپس report:

```powershell
python -u scripts/report_hybrid_full_backtest.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --matrix-path datasets\processed\XAUUSD\5M\hybrid_xgboost_matrix_all_5m.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --storage-root datasets
```

هشدار: این full-history diagnostic ممکن است شامل دورهٔ train مدل‌ها باشد و جایگزین holdout/significance نیست. هدفش دیدن equity curve، توزیع tradeها و رفتار کل تاریخ در GUI است.

Quality gate بعد از اضافه‌شدن full 5M report:

```text
python -m ruff check <Phase116 + full-report touched files>
# PASS

python -m black --check <Phase116 + full-report touched files>
# PASS

python -m pytest tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/ai/test_prediction_target.py tests/unit/ai/test_hybrid_head_predictor.py tests/unit/strategy/test_hybrid_range_aware_strategy.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 96 passed

python -m pytest
# 1690 passed, 54 skipped in 200.14s
```

Full gate هنوز به‌خاطر بدهی‌های قدیمی repo قرمز است:

```text
python -m ruff check .
# FAIL: 219 errors

python -m black --check .
# FAIL: 21 old files would be reformatted

python -m mypy src
# FAIL: 28 old errors in 10 files
```

## 2026-09-09 — Full hybrid report upgraded to candle replay + $100 balance view

کاربر پرسید آیا report جدید مثل replay قدیمی امکان حرکت دونه‌دونه روی کندل‌ها، دیدن نقطهٔ ورود، TP/SL و محاسبهٔ خروجی با سرمایهٔ 100 دلار را دارد یا نه. پاسخ دقیق: نسخهٔ اول فقط report/summary بود، نه replay کندل‌به‌کندل. بنابراین همان ابزار full report ارتقا داده شد.

تغییرات:

```text
scripts/report_hybrid_full_backtest.py
  + --initial-capital default 100
  + --units default 1
  + account summary: final_balance, return_percent, max_drawdown_cash, would_breach_zero
  + embedded candle-by-candle replay inside latest.html
  + slider برای حرکت کندل‌به‌کندل
  + markers: entry circle, exit square, TP/SL/entry horizontal lines

GUI: Full hybrid 5M backtest report
  + Initial capital ($)
  + PnL units
```

معنی capital:

```text
final_balance = initial_capital + total_pnl * units
```

هشدار مهم:

```text
با units=1 و initial_capital=100، اگر max_drawdown_cash از 100 بیشتر شود، گزارش flag would_breach_zero=true می‌دهد. این margin-call/broker liquidation واقعی نیست؛ فقط نشان می‌دهد sizing برای اکانت 100 دلاری زیادی بزرگ است.
```

دستور امن برای دیدن همان holdout معتبر Phase125/116 با 325 trade:

```powershell
python -u scripts/report_hybrid_full_backtest.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 1 `
  --storage-root datasets
```

برای اکانت 100 دلاری، `--units 1` احتمالاً بزرگ است چون در Phase125 max_drawdown حدود 347 بود. برای sanity sizing بهتر:

```text
--units 0.1  → maxDD حدود 34.7 دلار، final balance روی holdout حدود 129.12 دلار
--units 0.2  → maxDD حدود 69.4 دلار، final balance روی holdout حدود 158.23 دلار
```

Quality re-check:

```text
python -m ruff check scripts/report_hybrid_full_backtest.py tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
# PASS

python -m black --check scripts/report_hybrid_full_backtest.py tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/ai/test_prediction_target.py tests/unit/ai/test_hybrid_head_predictor.py tests/unit/strategy/test_hybrid_range_aware_strategy.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 97 passed

python -m pytest
# 1691 passed, 54 skipped in 175.84s
```

## 2026-09-09 — Hybrid candle replay report result on validated holdout

کاربر خروجی `run_logs/hybrid_full_backtest/latest.json` را برای report/replay جدید ارسال کرد. این اجرا روی matrix موجود 8000 ردیفی و `eval_frac=0.30` انجام شده؛ یعنی همان holdout معتبر 2400 ردیفی، نه کل تاریخ 5M.

تنظیمات:

```text
model_id       : gold_hybrid_lightgbm_head_5m
model_version  : 1
matrix_rows    : 8000
evaluated_rows : 2400
threshold_src  : model_record:gold_hybrid_lightgbm_head_5m:v1
threshold      : buy=0.80 sell=0.65 margin=0.05
max_hold_bars  : 48
min_4h_room    : 2
min_1d_room    : 5
min_tp_distance: 2
min_sl_distance: 2
spread_mode    : pct
spread_value   : 0.06
slippage       : 0
initial_capital: 100
units          : 0.1
```

Trading result:

```text
samples        : 2400
trades         : 325
buy/sell       : 160 / 165
wins/losses    : 168 / 157
timeouts       : 44
label_correct  : 214
false_positive : 111
win_rate       : 51.6923%
label_precision: 65.8462%
total_pnl      : +291.154987683185
avg_pnl        : +0.8958615005636462
profit_factor  : 1.2471739846573604
max_drawdown   : 347.044035279524
coverage       : 13.5417%
```

Account sizing view:

```text
initial_capital    : 100.0
units              : 0.1
final_balance      : 129.1154987683185
net_profit         : +29.115498768318503
return_percent     : +29.115498768318504%
max_drawdown_cash  : 34.7044035279524
would_breach_zero  : false
```

Replay output:

```text
run_logs\hybrid_full_backtest\latest.html
candles in replay: 2440
trades in replay : 325
```

برداشت:

```text
- report/replay جدید با Phase125/Phase116 دقیقاً هم‌خوان است.
- با سایز units=0.1، سناریوی $100 روی این holdout از $100 به $129.12 می‌رسد و drawdown cash حدود $34.70 است.
- این نتیجه خوب است ولی فقط برای holdout ماه 2026-08 است؛ چون monthly فقط 2026-08 را نشان می‌دهد.
- برای «کل دیتای 5M» هنوز باید نسخهٔ memory-safe/chunked matrix/backtest ساخته شود. دستور --scope all --max-windows 0 بدون chunk برای سیستم کاربر RAM را پر کرد و نباید تکرار شود.
```

## 2026-09-09 — Fix hybrid replay black chart + add memory-safe streamed full 5M mode

کاربر گزارش داد که بخش کندل/ورود/خروج در HTML replay صفحهٔ سیاه است و همچنین خواست قبل از Phase115 بک‌تست کامل گرفته شود. علت chart سیاه در report قبلی این بود که JSON replay داخل `<script type="application/json">` با `html.escape` نوشته می‌شد؛ در script raw-text، `&quot;` به quote تبدیل نمی‌شود و `JSON.parse` fail می‌کند، بنابراین chart رندر نمی‌شد.

رفع UI replay:

```text
scripts/report_hybrid_full_backtest.py
  + script_json(): safe raw JSON for script block without &quot;
  + fallback SVG text if JSON parse fails
  + no optional chaining in replay buttons
  + loading/error text instead of empty black panel
```

برای بک‌تست کامل 5M بدون ساخت matrix عظیم و بدون RAM spike، همان script به mode جدید مجهز شد:

```text
--source-mode stream
--stream-scope all
--stream-chunk-size 2000
--stream-wavenet neutral|batch
```

رفتار stream:

```text
- دیگر لازم نیست build_hybrid_xgboost_matrix.py --scope all --max-windows 0 اجرا شود.
- rowهای hybrid در chunk ساخته و همان‌جا scoring/backtest می‌شوند.
- خروجی نهایی همان latest.html/latest.json/latest.csv است.
- پیش‌فرض stream_wavenet=neutral است تا tensor عظیم WaveNet ساخته نشود؛ چون WaveNet در فازهای قبل no-edge/collapsed بود.
- اگر اجرای دقیق‌تر با WaveNet لازم شد: --stream-wavenet batch با chunk کوچک، ولی ممکن است کندتر/سنگین‌تر باشد.
```

GUI نیز update شد:

```text
Full hybrid 5M backtest report
  Source mode: matrix|stream
  Stream scope: all|holdout|last-fold|auto
  Stream chunk rows
  Stream WaveNet: neutral|batch
  Initial capital
  PnL units
```

دستور پیشنهادی full memory-safe:

```powershell
python -u scripts/report_hybrid_full_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 1000 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Quality re-check:

```text
python -m ruff check scripts/report_hybrid_full_backtest.py tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
# PASS

python -m black --check scripts/report_hybrid_full_backtest.py tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 64 passed

python -m pytest
# 1691 passed, 54 skipped in 248.01s
```

## 2026-09-09 — Streamed full 5M hybrid replay result: failed robustness test

کاربر full 5M streamed report را با mode memory-safe اجرا کرد:

```text
source_mode       : stream
stream_scope      : all
stream_chunk_size : 500
stream_wavenet    : neutral
symbol/timeframe  : XAUUSD 5M
model             : gold_hybrid_lightgbm_head_5m v1
threshold_source  : model_record:gold_hybrid_lightgbm_head_5m:v1
threshold         : buy=0.80 sell=0.65 margin=0.05
initial_capital   : 100
units             : 0.1
```

Full streamed result:

```text
matrix_rows/evaluated_rows: 52832 / 52832
trades        : 13757
buy/sell      : 8583 / 5174
wins/losses   : 5677 / 8080
timeouts      : 1358
label_correct : 7031
false_positive: 6726
win_rate      : 41.2663%
label_precision: 51.1085%
total_pnl     : -43309.811277104236
avg_pnl       : -3.1482017356330765
profit_factor : 0.6215092452818565
max_drawdown  : 45887.011698256094
coverage      : 26.0391%
```

Account view:

```text
initial_capital   : 100.0
units             : 0.1
final_balance     : -4230.981127710424
net_profit        : -4330.981127710424
return_percent    : -4330.981127710424%
max_drawdown_cash : 4588.701169825609
would_breach_zero : true
```

Monthly breakdown:

```text
2025-12: trades=2035 pnl=-3469.92  PF=0.6467
2026-01: trades=1310 pnl=-2812.86  PF=0.7087
2026-02: trades=1945 pnl=-21573.37 PF=0.3872
2026-03: trades=2080 pnl=-9142.95  PF=0.6049
2026-04: trades=1267 pnl=-2902.95  PF=0.7307
2026-05: trades=1552 pnl=-3055.75  PF=0.6699
2026-06: trades=979  pnl=-2129.33  PF=0.6599
2026-07: trades=1697 pnl=+2319.21  PF=1.3863
2026-08: trades=885  pnl=-522.19   PF=0.8778
2026-09: trades=7    pnl=-19.72    PF=0.4591
```

برداشت فنی:

```text
- این یک robustness/stress test روی کل تاریخ بود، نه یک walk-forward صحیح.
- نتیجهٔ fixed-threshold single-head روی کل تاریخ شکست خورد.
- coverage از 13.54% در holdout معتبر به 26.04% در کل تاریخ رسیده؛ یعنی مدل/threshold خارج از پنجرهٔ انتخاب‌شده بیش از حد trade می‌کند.
- تنها ماه مثبت 2026-07 بود؛ بقیه ماه‌ها منفی‌اند. این نشانهٔ regime sensitivity یا overfit/selection bias در threshold/head است.
- اجرای full stream با stream_wavenet=neutral انجام شده، پس دقیقاً همان feature distribution ماتریس Phase123 نیست؛ اما بزرگی شکست نشان می‌دهد نمی‌توانیم با همین ثابت‌ها وارد live شویم.
```

پاسخ به سؤال کاربر درباره train روی کل دیتاست:

```text
برای بک‌تست معتبر نباید مدل را روی کل دیتاست train کنیم و بعد روی همان کل دیتاست backtest بگیریم؛ این leakage/in-sample است.
کار درست برای «کل تاریخ» walk-forward/out-of-time است:
  train فقط روی گذشته
  calibrate threshold فقط روی گذشته/validation
  test روی ماه/بلاک بعدی که مدل ندیده
برای production نهایی، بعد از پاس شدن walk-forward، می‌توان مدل final را روی کل دادهٔ گذشته train کرد و سپس فقط روی آینده/paper/live ارزیابی کرد.
```

نتیجهٔ تصمیمی:

```text
Phase115/live حتی paper جدی با trade واقعی هنوز زود است.
گام بعدی باید Phase126 walk-forward hybrid validation باشد، نه train-all-then-backtest-same-data.
```

## 2026-09-09 — Phase126A implementation: chronological single-position hybrid replay

بعد از شکست full streamed independent-trade test، Phase126A ساخته شد تا replay واقعی‌تر حساب انجام شود: کندل‌به‌کندل، فقط یک پوزیشن هم‌زمان، و skip کردن سیگنال‌های جدید تا وقتی معاملهٔ قبلی بسته نشده است.

فایل‌های جدید/تغییرکرده:

```text
scripts/replay_hybrid_chronological_backtest.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_chronological_replay.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase126.md
docs/Phases/README_PHASE100_115.md
docs/WORKLOG.md
docs/CURRENT_STATE.md
```

قانون جدید:

```text
for each signal row chronologically:
  if source_index <= open_until_index:
      skipped_while_open += 1
      continue
  else:
      evaluate hybrid probability thresholds
      evaluate range_1d/range_4h filters
      simulate TP/SL/timeout up to max_hold_bars
      open_until_index = trade.exit_index
```

خروجی‌ها:

```text
run_logs/hybrid_chronological_backtest/latest.html
run_logs/hybrid_chronological_backtest/latest.json
run_logs/hybrid_chronological_backtest/latest.csv
```

دستور پیشنهادی کاربر:

```powershell
python -u scripts/replay_hybrid_chronological_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 500 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Quality check اجراشده:

```text
python -m ruff check scripts/replay_hybrid_chronological_backtest.py tests/unit/ai/test_hybrid_chronological_replay.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py scripts/report_hybrid_full_backtest.py
# PASS

python -m black --check scripts/replay_hybrid_chronological_backtest.py tests/unit/ai/test_hybrid_chronological_replay.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py scripts/report_hybrid_full_backtest.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_chronological_replay.py tests/unit/ai/test_hybrid_full_backtest_report.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 68 passed
```

گزارش فاز ۱۲۶A اضافه شد:

```text
docs/Report/PHASE126A_CHRONOLOGICAL_HYBRID_REPLAY_REPORT.md
```

Full quality gate بعد از Phase126A:

```text
python -m pytest
# 1695 passed, 54 skipped in 245.80s

python -m ruff check .
# FAIL: 219 pre-existing lint errors
# examples include ShadBotTrader_Colab.ipynb, scripts/find_best_lr.py,
# scripts/fetch_1d_gold_yahoo.py, standard_catalog.py.

python -m black --check .
# FAIL: 21 old files would be reformatted; 497 files unchanged.

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files.
```

## 2026-09-09 — Phase127-134 telemetry/model/production roadmap documented

کاربر ایدهٔ جدید را مطرح کرد: ساخت ماتریس/تنسور جدید از خروجی‌های backtest و مدل‌های فعلی، با Target C و امکان استفادهٔ online. همچنین نگرانی دربارهٔ پیچیده‌شدن code و نیاز به جمع‌کردن مسیر robot online مطرح شد.

مدل‌های کاربردی که باید محور بمانند:

```text
gold_range_1d
gold_range_4h
gold_buy_lightgbm_basic_5m
gold_sell_lightgbm_basic_5m
gold_trend_signal_lightgbm_basic_5m
gold_hybrid_lightgbm_head_5m
```

تصمیم‌های ثبت‌شده:

```text
safe_lag = 48 bars  # چون range_4h افق 4 ساعته دارد و 48 کندل 5M است
Target C:
  target_trade_win
  target_trade_score_r
  target_trade_pnl
3D tensor shape:
  X = [samples, tensor_window, channels]
4H/1D context:
  به‌عنوان aligned feature channels وارد بعد سوم شود، فقط از آخرین کندل بسته‌شده
```

فازهای جداگانه ثبت‌شده:

```text
Phase127 — Causal 3D Hybrid Telemetry Tensor
Phase128 — LightGBM/CatBoost Meta-Labeler Baseline
Phase129 — WaveNet/TCN on 3D Hybrid Telemetry Tensor
Phase130 — TSMixer Benchmark
Phase131 — PatchTST Benchmark
Phase132 — Meta-Filtered Hybrid Chronological Backtest
Phase133 — Walk-Forward Out-of-Time Hybrid Validation
Phase134 — Production Consolidation / Online Bot Assembly
```

نکته درباره WaveNet:

```text
WaveNet قدیمی `gold_trend_signal_5m` collapse/no-edge بود، اما Phase129 یک WaveNet/TCN جدید روی telemetry tensor و Target C است، نه تکرار همان مدل قبلی.
```

نکته درباره پیچیدگی:

```text
Phase134 مخصوص جمع‌کردن complexity است. اگر validation پاس شود، production path باید فقط یک stack منتخب، یک config، یک online feature builder، یک decision service و یک MT5 execution path guarded داشته باشد. Research scripts نباید وارد live order submission شوند.
```

فایل‌های مستند جدید:

```text
docs/Phases/Phase127.md
docs/Phases/Phase128.md
docs/Phases/Phase129.md
docs/Phases/Phase130.md
docs/Phases/Phase131.md
docs/Phases/Phase132.md
docs/Phases/Phase133.md
docs/Phases/Phase134.md
docs/Report/PHASE127_134_TELEMETRY_AND_PRODUCTION_ROADMAP.md
```

## 2026-09-09 — GUI execution rule added to future phases

کاربر تأکید کرد از این به بعد هر چیزی که ساخته می‌شود و نیاز به اجرای اپراتور دارد باید در GUI/Dashboard هم command داشته باشد؛ CLI تنها کافی نیست.

این قانون در فازهای زیر ثبت شد:

```text
Phase115
Phase126
Phase127
Phase128
Phase129
Phase130
Phase131
Phase132
Phase133
Phase134
```

قاعدهٔ اجرایی:

```text
هر script/train/backtest/replay/audit که اپراتور باید اجرا کند، باید همزمان داشته باشد:
  CommandKind
  CommandDescriptor
  Handler
  فیلدهای GUI، با advanced برای knobهای تخصصی
  تست descriptor و arg pass-through
  dashboard coverage
```

هدف:

```text
اپراتور هیچ دستور بلند و شکننده‌ای را دستی نسازد؛ هر مرحلهٔ قابل اجرا از Dashboard قابل اجرا باشد.
```

## 2026-09-09 — Phase127A implementation: causal 3D telemetry tensor builder

ساخت Phase127A انجام شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/build_hybrid_telemetry_tensor.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_telemetry_tensor.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase127.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

GUI command:

```text
Build hybrid telemetry tensor
```

قابلیت‌های پیاده‌سازی‌شده:

```text
- ساخت flat telemetry parquet
- ساخت 3D tensor NPZ: X=[samples, tensor_window, channels]
- Target C:
  target_trade_win
  target_trade_score_r
  target_trade_pnl
- safe_lag_bars default=48
- telemetry_lag_mode=fixed|exit_closed
- 5M compact candle features
- hybrid/booster/range model-output features
- candidate bracket features
- lagged virtual-backtest telemetry
- optional aligned 4H/1D closed-candle context
- source-mode=matrix برای اجرای امن اول
- source-mode=stream برای ساخت chunked بدون matrix عظیم
- max_tensor_mb guard برای جلوگیری از RAM spike
```

دستور امن اول برای کاربر:

```powershell
python -u scripts/build_hybrid_telemetry_tensor.py `
  --source-mode matrix `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --tensor-window 150 `
  --safe-lag-bars 48 `
  --telemetry-lag-mode fixed `
  --sample-stride 1 `
  --max-samples 0 `
  --candidate-samples-only 0 `
  --dtype float16 `
  --max-tensor-mb 512 `
  --include-htf-context 1 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --storage-root datasets
```

دستور full stream بعد از تأیید run اول:

```powershell
python -u scripts/build_hybrid_telemetry_tensor.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 500 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --tensor-window 150 `
  --safe-lag-bars 48 `
  --telemetry-lag-mode fixed `
  --sample-stride 5 `
  --max-samples 12000 `
  --candidate-samples-only 0 `
  --dtype float16 `
  --max-tensor-mb 512 `
  --include-htf-context 1 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --storage-root datasets
```

خروجی‌هایی که کاربر باید بفرستد:

```text
run_logs\hybrid_telemetry_tensor\latest.json
```

Quality gate بعد از Phase127A:

```text
python -m ruff check scripts/build_hybrid_telemetry_tensor.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/build_hybrid_telemetry_tensor.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 67 passed

python -m pytest
# 1700 passed, 54 skipped in 249.15s
```

Full gate هنوز به‌علت بدهی‌های قدیمی repo قرمز است:

```text
python -m ruff check .
# FAIL: 219 errors

python -m black --check .
# FAIL: 21 old files would be reformatted; 499 files unchanged

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase128A implementation: LightGBM/CatBoost meta-labeler train/backtest

Phase128A ساخته شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/train_hybrid_meta_labeler.py
scripts/backtest_hybrid_meta_labeler.py
scripts/build_hybrid_telemetry_tensor.py  # اضافه شدن target_exit_index/target_outcome_code برای backtest متا
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_meta_labeler.py
tests/unit/ai/test_hybrid_telemetry_tensor.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase128.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

GUI commands:

```text
Train hybrid meta-labeler
Backtest hybrid meta-labeler
```

قابلیت train:

```text
- task=classifier روی target_trade_win
- task=regressor روی target_trade_score_r
- candidate_only=1 پیش‌فرض
- chronological train/val/test split
- booster: lightgbm/xgboost/catboost/auto
- ذخیره model artifact و ModelRecord
```

قابلیت backtest:

```text
- بارگذاری meta model
- اعمال meta_threshold یا score_threshold
- chronological single-position replay روی candidateهای telemetry
- استفاده از target_exit_index برای skip کردن سیگنال‌های while-open
- HTML/JSON/CSV report
```

دستور اجرای Phase128 بعد از Phase127:

```powershell
python -u scripts/train_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --class-weight auto `
  --n-estimators 500 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets

python -u scripts/backtest_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --meta-model-id gold_hybrid_meta_lightgbm_5m `
  --meta-model-version 0 `
  --meta-threshold -1 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Quality check:

```text
python -m ruff check scripts/train_hybrid_meta_labeler.py scripts/backtest_hybrid_meta_labeler.py scripts/build_hybrid_telemetry_tensor.py tests/unit/ai/test_hybrid_meta_labeler.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/train_hybrid_meta_labeler.py scripts/backtest_hybrid_meta_labeler.py scripts/build_hybrid_telemetry_tensor.py tests/unit/ai/test_hybrid_meta_labeler.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_meta_labeler.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 75 passed
```

گزارش Phase128A اضافه شد:

```text
docs/Report/PHASE128A_HYBRID_META_LABELER_REPORT.md
```

Full quality gate بعد از Phase128A:

```text
python -m pytest
# 1708 passed, 54 skipped in 247.68s

python -m ruff check .
# FAIL: 219 pre-existing lint errors

python -m black --check .
# FAIL: 21 old files would be reformatted; 502 files unchanged

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase129A implementation: telemetry WaveNet/TCN train/backtest

Phase129A ساخته شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_telemetry_wavenet.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase129.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/Report/PHASE129A_TELEMETRY_WAVENET_REPORT.md
```

GUI commands:

```text
Train telemetry WaveNet/TCN
Backtest telemetry WaveNet/TCN
```

قابلیت train:

```text
- ورودی: hybrid_telemetry_tensor_latest.npz از Phase127A
- task=classifier|regressor|multihead
- causal dilated Conv1D / TCN blocks
- gated tanh/sigmoid activations
- residual + skip connections
- train-only normalization
- chronological train/val/test split
- purge_gap default=336 = tensor_window 288 + safe_lag 48
- anti-collapse metrics: prediction stdev, selected/positive rates
- ذخیره artifact به format pickle_keras همراه scaler_mean/scaler_std/channel_names
```

قابلیت backtest:

```text
- بارگذاری WaveNet/TCN artifact
- اعمال scaler ذخیره‌شده
- decision_mode=meta|score|both
- meta_threshold/score_threshold
- chronological one-position replay با flat telemetry targets
- خروجی HTML/JSON/CSV
```

پیش‌نیاز کاربر:

```powershell
python -m pip install -r requirements-ai.txt
```

دستور train پیشنهادی:

```powershell
python -u scripts/train_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_wavenet_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --score-threshold 0 `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --save-record 1 `
  --storage-root datasets
```

دستور backtest پیشنهادی:

```powershell
python -u scripts/backtest_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_wavenet_5m `
  --model-version 0 `
  --decision-mode meta `
  --meta-threshold -1 `
  --score-threshold 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Quality check اجراشده:

```text
python -m ruff check scripts/train_hybrid_telemetry_wavenet.py scripts/backtest_hybrid_telemetry_wavenet.py tests/unit/ai/test_hybrid_telemetry_wavenet.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/train_hybrid_telemetry_wavenet.py scripts/backtest_hybrid_telemetry_wavenet.py tests/unit/ai/test_hybrid_telemetry_wavenet.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_telemetry_wavenet.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 77 passed
```

Full quality gate بعد از Phase129A:

```text
python -m pytest
# 1717 passed, 54 skipped in 233.53s

python -m ruff check .
# FAIL: 219 pre-existing lint errors

python -m black --check .
# FAIL: 21 old files would be reformatted; 505 files unchanged

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase130A implementation: telemetry TSMixer train/backtest

Phase130A ساخته شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/train_hybrid_telemetry_tsmixer.py
scripts/backtest_hybrid_telemetry_tsmixer.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_telemetry_tsmixer.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase130.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/Report/PHASE130A_TELEMETRY_TSMIXER_REPORT.md
```

GUI commands:

```text
Train telemetry TSMixer
Backtest telemetry TSMixer
```

قابلیت train:

```text
- ورودی: hybrid_telemetry_tensor_latest.npz از Phase127A
- task=classifier|regressor|multihead
- TSMixer residual blocks: time mixing + feature mixing
- train-only normalization
- chronological train/val/test split
- purge_gap default=336
- artifact format=pickle_keras با scaler/channel metadata
```

قابلیت backtest:

```text
- load saved TSMixer artifact
- decision_mode=meta|score|both
- chronological single-position replay با flat telemetry targets
- HTML/JSON/CSV report
```

دستور train پیشنهادی:

```powershell
python -u scripts/train_hybrid_telemetry_tsmixer.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_tsmixer_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --mixer-layers 4 `
  --time-hidden-units 64 `
  --feature-hidden-units 128 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --score-threshold 0 `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --save-record 1 `
  --storage-root datasets
```

دستور backtest پیشنهادی:

```powershell
python -u scripts/backtest_hybrid_telemetry_tsmixer.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_tsmixer_5m `
  --model-version 0 `
  --decision-mode meta `
  --meta-threshold -1 `
  --score-threshold 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Quality check اجراشده:

```text
python -m ruff check scripts/train_hybrid_telemetry_tsmixer.py scripts/backtest_hybrid_telemetry_tsmixer.py tests/unit/ai/test_hybrid_telemetry_tsmixer.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/train_hybrid_telemetry_tsmixer.py scripts/backtest_hybrid_telemetry_tsmixer.py tests/unit/ai/test_hybrid_telemetry_tsmixer.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_telemetry_tsmixer.py tests/unit/ai/test_hybrid_telemetry_wavenet.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 86 passed
```

Full quality gate بعد از Phase130A:

```text
python -m pytest
# 1726 passed, 54 skipped in 226.02s

python -m ruff check .
# FAIL: 219 pre-existing lint errors

python -m black --check .
# FAIL: 21 old files would be reformatted; 508 files unchanged

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase131A implementation: telemetry PatchTST train/backtest

Phase131A ساخته شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/train_hybrid_telemetry_patchtst.py
scripts/backtest_hybrid_telemetry_patchtst.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_telemetry_patchtst.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase131.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/Report/PHASE131A_TELEMETRY_PATCHTST_REPORT.md
```

GUI commands:

```text
Train telemetry PatchTST
Backtest telemetry PatchTST
```

قابلیت train:

```text
- ورودی: hybrid_telemetry_tensor_latest.npz از Phase127A
- task=classifier|regressor|multihead
- Conv1D patch projection با patch_len/stride
- trainable positional embedding
- Transformer encoder blocks با MultiHeadAttention
- train-only normalization
- chronological train/val/test split
- purge_gap default=336
- artifact format=pickle_keras با scaler/channel metadata
```

قابلیت backtest:

```text
- load saved PatchTST artifact
- decision_mode=meta|score|both
- chronological single-position replay با flat telemetry targets
- HTML/JSON/CSV report
```

دستور train پیشنهادی:

```powershell
python -u scripts/train_hybrid_telemetry_patchtst.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_patchtst_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --patch-len 16 `
  --stride 8 `
  --d-model 64 `
  --layers 3 `
  --heads 4 `
  --ff-units 128 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --score-threshold 0 `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --save-record 1 `
  --storage-root datasets
```

دستور backtest پیشنهادی:

```powershell
python -u scripts/backtest_hybrid_telemetry_patchtst.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_patchtst_5m `
  --model-version 0 `
  --decision-mode meta `
  --meta-threshold -1 `
  --score-threshold 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Quality check اجراشده:

```text
python -m ruff check scripts/train_hybrid_telemetry_patchtst.py scripts/backtest_hybrid_telemetry_patchtst.py tests/unit/ai/test_hybrid_telemetry_patchtst.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/train_hybrid_telemetry_patchtst.py scripts/backtest_hybrid_telemetry_patchtst.py tests/unit/ai/test_hybrid_telemetry_patchtst.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_telemetry_patchtst.py tests/unit/ai/test_hybrid_telemetry_tsmixer.py tests/unit/ai/test_hybrid_telemetry_wavenet.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 95 passed
```

Full quality gate بعد از Phase131A:

```text
python -m pytest
# 1735 passed, 54 skipped in 204.64s

python -m ruff check .
# FAIL: 219 pre-existing lint errors

python -m black --check .
# FAIL: 21 old files would be reformatted; 511 files unchanged

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase132A implementation: meta-filtered hybrid comparison

Phase132A ساخته شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/backtest_meta_filtered_hybrid.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_meta_filtered_hybrid_comparison.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase132.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/Report/PHASE132A_META_FILTERED_COMPARISON_REPORT.md
```

GUI command:

```text
Backtest meta-filtered hybrid
```

قابلیت‌ها:

```text
- مقایسه base hybrid candidates با meta-filterهای train شده
- پشتیبانی flat modelهای Phase128 با payload['model']
- پشتیبانی tensor modelهای Phase129/130/131 با payload['model_bytes']
- candidate list comma-separated
- threshold grid: record و thresholdهای explicit
- decision_mode=meta|score|both برای tensor models
- skip_missing=1 پیش‌فرض برای اجرا حتی وقتی بعضی مدل‌ها هنوز train نشده‌اند
- خروجی comparison CSV/JSON/HTML
- خروجی best_replay.html برای بهترین candidate انتخاب‌شده
```

دستور پیشنهادی:

```powershell
python -u scripts/backtest_meta_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --candidates base,gold_hybrid_meta_lightgbm_5m,gold_hybrid_telemetry_wavenet_5m,gold_hybrid_telemetry_tsmixer_5m,gold_hybrid_telemetry_patchtst_5m `
  --candidate-versions 0 `
  --decision-modes meta,both `
  --meta-thresholds record,0.55,0.60,0.65 `
  --score-thresholds 0,0.05,0.10 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --min-trades 10 `
  --score-metric total_pnl `
  --initial-capital 100 `
  --units 0.1 `
  --skip-missing 1 `
  --storage-root datasets
```

Quality check:

```text
python -m ruff check scripts/backtest_meta_filtered_hybrid.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/backtest_meta_filtered_hybrid.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_meta_filtered_hybrid_comparison.py tests/unit/ai/test_hybrid_telemetry_patchtst.py tests/unit/ai/test_hybrid_telemetry_tsmixer.py tests/unit/ai/test_hybrid_telemetry_wavenet.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 101 passed
```

Full quality gate بعد از Phase132A:

```text
python -m pytest
# 1741 passed, 54 skipped in 196.75s

python -m ruff check .
# FAIL: 219 pre-existing lint errors

python -m black --check .
# FAIL: 21 old files would be reformatted; 513 files unchanged

python -m mypy src
# FAIL: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase133A implementation: walk-forward validation

Phase133A ساخته شد.

فایل‌های جدید/تغییرکرده:

```text
scripts/run_hybrid_walk_forward_validation.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_walk_forward_validation.py
tests/unit/presentation/test_architecture_knobs_gui.py
tests/integration/test_gui_coverage.py
docs/Phases/Phase133.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/Report/PHASE133A_WALK_FORWARD_VALIDATION_REPORT.md
```

GUI command:

```text
Run hybrid walk-forward validation
```

Scope پیاده‌سازی‌شده:

```text
Phase133A فعلاً flat Phase128 booster meta-labeler را walk-forward می‌کند.
برای هر test month، مدل جدید فقط روی ماه‌های گذشته train می‌شود، threshold فقط روی validation گذشته انتخاب می‌شود، و سپس ماه آینده تست می‌شود.
```

پروتکل:

```text
train_months      = all months before validation block
validation_months = immediate previous month(s)
test_month        = next unseen month
purge_gap_bars    = 336 default
threshold_grid    = meta_thresholds or score_thresholds
```

دستور پیشنهادی:

```powershell
python -u scripts/run_hybrid_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --meta-thresholds 0.45,0.50,0.55,0.60,0.65,0.70 `
  --min-trades 10 `
  --score-metric total_pnl `
  --class-weight auto `
  --n-estimators 400 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

خروجی‌ها:

```text
run_logs/hybrid_walk_forward_validation/latest.json
run_logs/hybrid_walk_forward_validation/latest.csv
run_logs/hybrid_walk_forward_validation/latest.html
```

Quality check اجراشده:

```text
python -m ruff check scripts/run_hybrid_walk_forward_validation.py tests/unit/ai/test_hybrid_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/run_hybrid_walk_forward_validation.py tests/unit/ai/test_hybrid_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 88 passed

python -m pytest
# 1747 passed, 54 skipped in 196.60s
```

Full gate همچنان به‌علت بدهی‌های قدیمی repo قرمز است:

```text
ruff full: 219 errors
black full: 21 old files would be reformatted; 513 files unchanged
mypy full: 28 pre-existing errors in 10 files
```

## 2026-09-09 — Phase134A implementation: production validation + paper shadow scaffold

Phase134A ساخته شد تا research complexity به یک production-style config و paper/shadow مسیر محدود جمع شود، بدون فعال‌کردن order واقعی.

فایل‌های جدید/تغییرکرده:

```text
src/ShadBotTrader/application/services/hybrid_production_service.py
scripts/validate_production_hybrid_stack.py
scripts/run_hybrid_paper_shadow.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/services/test_hybrid_production_service.py
tests/unit/ai/test_hybrid_production_scripts.py
tests/unit/presentation/test_architecture_knobs_gui.py
tests/integration/test_gui_coverage.py
docs/Phases/Phase134.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/Report/PHASE134A_PRODUCTION_CONSOLIDATION_REPORT.md
```

GUI commands:

```text
Validate production hybrid stack
Run hybrid paper shadow
```

Safety gates پیاده‌سازی‌شده:

```text
mode_supported
base_model_selected
range_models_selected
position_size_positive
initial_capital_positive
risk_limits_present
kill_switch_enabled
schema_hash_known
schema_hash_matches_config اگر hash مورد انتظار داده شده باشد
```

Live mode additionally requires:

```text
paper_shadow_passed
account_profile_confirmed
symbol_mapping_confirmed
explicit_live_confirm == ENABLE_REAL_HYBRID_TRADING
```

نکتهٔ ایمنی:

```text
scripts/run_hybrid_paper_shadow.py هرگز live mode اجرا نمی‌کند و هیچ order واقعی ارسال نمی‌کند.
```

دستور validation:

```powershell
python -u scripts/validate_production_hybrid_stack.py `
  --mode paper_shadow `
  --symbol XAUUSD `
  --timeframe 5M `
  --base-model-id gold_hybrid_lightgbm_head_5m `
  --base-model-version 0 `
  --meta-model-type none `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --position-size-units 0.1 `
  --initial-capital 100 `
  --kill-switch-enabled 1 `
  --write-config 1 `
  --require-models 0 `
  --storage-root datasets
```

دستور paper shadow:

```powershell
python -u scripts/run_hybrid_paper_shadow.py `
  --config-path configs\hybrid_production_stack.json `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allow-validation-fail 0 `
  --storage-root datasets
```

Quality check:

```text
python -m ruff check scripts/validate_production_hybrid_stack.py scripts/run_hybrid_paper_shadow.py src/ShadBotTrader/application/services/hybrid_production_service.py tests/unit/services/test_hybrid_production_service.py tests/unit/ai/test_hybrid_production_scripts.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m black --check scripts/validate_production_hybrid_stack.py scripts/run_hybrid_paper_shadow.py src/ShadBotTrader/application/services/hybrid_production_service.py tests/unit/services/test_hybrid_production_service.py tests/unit/ai/test_hybrid_production_scripts.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
# PASS

python -m pytest tests/unit/services/test_hybrid_production_service.py tests/unit/ai/test_hybrid_production_scripts.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 96 passed

python -m pytest
# 1759 passed, 54 skipped in 194.31s
```

Full gate همچنان به‌خاطر بدهی‌های قدیمی repo قرمز است:

```text
ruff full: 219 errors
black full: 21 old files would be reformatted; 520 files unchanged
mypy full: 28 pre-existing errors in 10 files
```

## 2026-09-10 — Phase126A full chronological result and Phase127 timestamp fix

کاربر Phase126A chronological single-position replay را روی کل 5M اجرا کرد:

```text
source_mode       : stream
stream_scope      : all
stream_chunk_size : 500
stream_wavenet    : neutral
source_rows       : 52832
evaluated_rows    : 52832
threshold         : buy=0.80 sell=0.65 margin=0.05
initial_capital   : 100
units             : 0.1
```

نتیجه:

```text
trades          : 1693
buy/sell        : 1118 / 575
wins/losses     : 512 / 1181
timeouts        : 77
win_rate        : 30.2422%
label_precision : 47.6669%
total_pnl       : -4590.797210656048
avg_pnl         : -2.7116345012735077
profit_factor   : 0.5787103197097719
max_drawdown    : 4590.797210656047
coverage        : 3.2045%
```

Chronological counters:

```text
no_trade_probability: 21949
skipped_while_open  : 17299
invalid_range       : 5357
invalid_bracket     : 6534
```

Account view با `units=0.1`:

```text
final_balance     : -359.0797210656049
net_profit        : -459.0797210656049
max_drawdown_cash : 459.07972106560476
would_breach_zero : true
```

برداشت:

```text
حتی با فقط یک پوزیشن هم‌زمان، base hybrid fixed-threshold روی کل تاریخ شکست خورد. بنابراین Phase128/132/133 meta-filter و walk-forward validation ضروری هستند و live/paper جدی هنوز مجاز نیست.
```

سپس کاربر Phase127A matrix-mode را اجرا کرد و خطا گرفت:

```text
[X] TypeError: '<' not supported between instances of 'str' and 'datetime.datetime'
```

علت:

```text
در scripts/build_hybrid_telemetry_tensor.py، timestampهای matrix به صورت string بودند ولی latest_closed برای 4H/1D context آن‌ها را با datetime end_times مقایسه می‌کرد.
```

رفع انجام‌شده:

```text
build_htf_lookup اکنون end_times را به pandas Timestamp UTC تبدیل می‌کند.
latest_closed اکنون timestamp ورودی را با comparable_timestamp به pandas Timestamp UTC تبدیل می‌کند.
اگر timestamp نامعتبر باشد None برمی‌گردد، نه crash.
```

تست اضافه‌شده:

```text
tests/unit/ai/test_hybrid_telemetry_tensor.py::test_latest_closed_accepts_iso_timestamp_strings
```

Quality check بعد از fix:

```text
python -m ruff check scripts/build_hybrid_telemetry_tensor.py tests/unit/ai/test_hybrid_telemetry_tensor.py
# PASS

python -m black --check scripts/build_hybrid_telemetry_tensor.py tests/unit/ai/test_hybrid_telemetry_tensor.py
# PASS

python -m pytest tests/unit/ai/test_hybrid_telemetry_tensor.py
# 4 passed

python -m pytest
# 1760 passed, 54 skipped in 257.05s
```

Full gate همچنان به‌خاطر بدهی‌های قدیمی repo قرمز است:

```text
ruff full: 219 errors
black full: 21 old files would be reformatted; 520 files unchanged
mypy full: 28 pre-existing errors in 10 files
```

## 2026-09-10 — Phase127A matrix-mode execution result: telemetry tensor built successfully

کاربر Phase127A را بعد از timestamp fix با `source_mode=matrix` اجرا کرد و tensor با موفقیت ساخته شد.

تنظیمات مهم:

```text
source_mode       : matrix
matrix_path       : default = datasets\processed\XAUUSD\5M\hybrid_xgboost_matrix_latest.parquet
model             : gold_hybrid_lightgbm_head_5m v1
threshold         : buy=0.80 sell=0.65 margin=0.05
tensor_window     : 150
safe_lag_bars     : 48
telemetry_lag_mode: fixed
sample_stride     : 1
dtype             : float16
include_htf_context: 1
max_tensor_mb     : 512
```

نتیجه:

```text
rows              : 8000
tensor_samples    : 7851
tensor_shape      : [7851, 150, 94]
channels          : 94
candidate_rows    : 2307
candidate_rate    : 28.8375%
target_win_rate   : 57.2605%
target_score_r_mean: +0.07910706847906113
target_pnl_sum    : +3714.10546875
safe_lag_bars     : 48
warnings          : []
```

خروجی‌ها:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_v1.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
run_logs\hybrid_telemetry_tensor\latest.json
```

برداشت:

```text
- Phase127A از نظر ساختار PASS شد: tensor سه‌بعدی، Target C، safe_lag=48، 4H/1D aligned context و lagged telemetry بدون warning ساخته شدند.
- این اجرا فقط روی matrix موجود 8000-row است، نه کل تاریخ 52832-row.
- target_pnl_sum مثبت اینجا validation معاملاتی نیست؛ چون این dataset برای آموزش/feature engineering است و شامل کل matrix 8000-row می‌شود. معیار معتبر بعدی Phase128/132/133 است.
```

گام بعدی:

```text
Phase128A train hybrid meta-labeler روی:
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

## 2026-09-10 — Phase128A train result: LightGBM meta-labeler v1

کاربر Phase128A train را روی خروجی Phase127A matrix-mode اجرا کرد.

تنظیمات:

```text
flat_path      : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
task           : classifier
target         : target_trade_win
booster        : lightgbm
candidate_only : 1
rows           : 2307
features       : 94
train/val/test : 1614 / 346 / 347
meta_threshold : 0.55
record_path    : datasets\models\gold_hybrid_meta_lightgbm_5m\v1_training.json
```

Validation:

```text
val_accuracy      : 0.6445086705202312
val_base_rate     : 0.6445086705202312
val_precision     : 0.6572327044025157
val_recall        : 0.9372197309417041
val_f1            : 0.7726432532347505
val_ap            : 0.7864284978741574
val_positive_rate : 0.9190751445086706
val_tp/fp/tn/fn   : 209 / 109 / 14 / 14
```

Test:

```text
test_accuracy      : 0.5072046109510087
test_base_rate     : 0.484149855907781
test_precision     : 0.49554896142433236
test_recall        : 0.9940476190476191
test_f1            : 0.6613861386138613
test_ap            : 0.619043571505885
test_positive_rate : 0.9711815561959655
test_tp/fp/tn/fn   : 167 / 170 / 9 / 1
```

برداشت:

```text
- مدل کاملاً collapse نکرده چون AP از base_rate بهتر است، مخصوصاً validation AP=0.786 و test AP=0.619.
- اما threshold ذخیره‌شدهٔ 0.55 بیش از حد permissive است:
  validation positive_rate=91.91%
  test positive_rate=97.12%
- در test تقریباً همهٔ candidateها را approve می‌کند؛ بنابراین به‌عنوان trade filter در threshold=0.55 هنوز مناسب نیست.
- اول باید backtest با threshold ذخیره‌شده دیده شود، سپس Phase132 threshold grid با 0.60/0.65/0.70/0.75/0.80 اجرا شود.
```

گام بعدی پیشنهادی:

```text
1) Phase128A backtest با meta_threshold=-1 برای baseline ذخیره‌شده.
2) Phase132A comparison با meta_thresholds=record,0.60,0.65,0.70,0.75,0.80 و فعلاً فقط base + gold_hybrid_meta_lightgbm_5m.
3) اگر هیچ threshold بهتر نشد، مستقیم Phase133A walk-forward برای رد/تأیید out-of-time.
```

## 2026-09-10 — Phase128A meta-filter backtest result: positive on 8000-row telemetry matrix

کاربر Phase128A backtest را با مدل `gold_hybrid_meta_lightgbm_5m v1` و threshold ذخیره‌شده اجرا کرد.

تنظیمات:

```text
flat_path          : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
meta_model_id      : gold_hybrid_meta_lightgbm_5m
meta_model_version : 1
meta_task          : classifier
meta_threshold     : 0.55
threshold_source   : model_record:gold_hybrid_meta_lightgbm_5m:v1
rows/evaluated     : 8000 / 8000
initial_capital    : 100
units              : 0.1
```

نتیجهٔ معاملاتی:

```text
samples        : 8000
trades         : 143
buy/sell       : 74 / 69
wins/losses    : 94 / 49
timeouts       : 7
win_rate       : 65.7343%
label_precision: 65.7343%
total_pnl      : +509.5359231829643
avg_pnl        : +3.5631882740067433
profit_factor  : 2.608242691826868
max_drawdown   : 91.44515466690063
coverage       : 1.7875%
```

Meta counters:

```text
skipped_by_meta    : 619
skipped_no_candidate: 5199
skipped_while_open : 2039
missing_outcome    : 0
```

Account view با `initial_capital=100`, `units=0.1`:

```text
final_balance     : 150.95359231829644
net_profit        : +50.953592318296444
return_percent    : +50.95359231829645%
max_drawdown_cash : 9.144515466690065
would_breach_zero : false
```

Monthly:

```text
2026-07: trades=60 wins=60 losses=0 total_pnl=+526.1065428555012 PF=999.0
2026-08: trades=83 wins=34 losses=49 total_pnl=-16.57061967253685 PF=0.9477
```

برداشت:

```text
- Meta-filter نسبت به base hybrid روی همین 8000-row telemetry matrix یک جهش جدی نشان داد: trades کم‌تر، PF=2.61، DD cash فقط $9.14 با units=0.1.
- اما profit تقریباً کامل از 2026-07 آمده و 2026-08 کمی منفی است؛ بنابراین هنوز نباید نتیجه را robust فرض کرد.
- این اجرا full history یا walk-forward نیست؛ فقط روی همان 8000-row matrix انجام شده است.
- گام بعدی باید Phase132A threshold grid باشد تا بفهمیم 0.55 بهترین است یا thresholdهای سخت‌تر پایدارترند.
- بعد از آن Phase133A walk-forward اجباری است.
```

گام بعدی پیشنهادی:

```text
Run Phase132A with candidates=base,gold_hybrid_meta_lightgbm_5m and thresholds record,0.55,0.60,0.65,0.70,0.75,0.80.
```

## 2026-09-10 — Phase132A comparison bugfix: best replay summary

کاربر Phase132A comparison را اجرا کرد و بعد از شروع report با خطای زیر شکست خورد:

```text
[X] AttributeError: 'ComparisonRow' object has no attribute 'label_correct'
```

علت:

```text
scripts/backtest_meta_filtered_hybrid.py برای ساخت best_replay.html سعی می‌کرد FixedBacktestSummary را از ComparisonRow بازسازی کند، اما ComparisonRow همهٔ فیلدهای summary مثل label_correct/gross_profit/gross_loss/no_trade را ندارد.
```

رفع:

```text
BestReplay اکنون summary اصلی FixedBacktestSummary را همراه row/trades/source_indices/threshold نگه می‌دارد.
best_replay.html اکنون از replay.summary استفاده می‌کند، نه از بازسازی ناقص از ComparisonRow.
```

تست اضافه/به‌روزرسانی:

```text
tests/unit/ai/test_meta_filtered_hybrid_comparison.py::test_best_replay_keeps_original_summary_for_html_rendering
```

Quality check:

```text
python -m ruff check scripts/backtest_meta_filtered_hybrid.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py
# PASS

python -m black --check scripts/backtest_meta_filtered_hybrid.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py
# PASS

python -m pytest tests/unit/ai/test_meta_filtered_hybrid_comparison.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
# 93 passed

python -m pytest
# 1761 passed, 54 skipped in 258.58s
```

Full gate همچنان به‌علت بدهی‌های قدیمی repo قرمز است:

```text
ruff full: 219 errors
black full: 21 old files would be reformatted; 520 files unchanged
mypy full: 28 pre-existing errors in 10 files
```

گام بعدی کاربر:

```text
همان دستور Phase132A comparison را دوباره اجرا کند و run_logs\hybrid_meta_comparison\latest.json را ارسال کند.
```

## 2026-09-10 — Phase132A threshold-grid result: LightGBM meta-filter beats base on 8000-row matrix

کاربر Phase132A comparison را با candidates زیر اجرا کرد:

```text
base
gold_hybrid_meta_lightgbm_5m
```

تنظیمات:

```text
flat_path       : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
tensor_path     : datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
samples         : 7851
meta_thresholds : record,0.55,0.60,0.65,0.70,0.75,0.80
score_metric    : total_pnl
initial_capital : 100
units           : 0.1
```

Base result:

```text
trades        : 219
buy/sell      : 116 / 103
wins/losses   : 93 / 126
win_rate      : 42.4658%
total_pnl     : +55.14647939801216
profit_factor : 1.0677528759144055
max_drawdown  : 98.2512731552124
coverage      : 2.7895%
final_balance : 105.51464793980122
```

Best meta-filter result:

```text
candidate      : gold_hybrid_meta_lightgbm_5m:meta:meta=record:score=0.0
version        : 1
meta_threshold : 0.55
trades         : 142
buy/sell       : 74 / 68
wins/losses    : 93 / 49
win_rate       : 65.49295774647887%
total_pnl      : +502.82915729284286
avg_pnl        : +3.541050403470724
profit_factor  : 2.5870741996012305
max_drawdown   : 91.44515466690063
coverage       : 1.8087%
final_balance  : 150.2829157292843
would_breach_zero: false
```

Threshold grid:

```text
0.55/record : +502.8292 PF=2.5871 trades=142 DD=91.4452
0.60        : +488.5258 PF=2.5521 trades=140 DD=91.4452
0.65        : +481.7925 PF=2.5413 trades=138 DD=89.2924
0.70        : +467.5121 PF=2.5073 trades=136 DD=89.2924
0.75        : +446.6142 PF=2.4499 trades=131 DD=89.2924
0.80        : +420.5321 PF=2.3652 trades=130 DD=89.2924
```

برداشت:

```text
- روی همین 8000-row telemetry matrix، meta-filter نسبت به base بسیار بهتر است:
  +502.83 در برابر +55.15 و PF=2.59 در برابر 1.07.
- threshold ذخیره‌شدهٔ 0.55 در این grid با score_metric=total_pnl بهترین بود.
- thresholdهای سخت‌تر drawdown را کمی پایین‌تر می‌آورند اما total_pnl را کم می‌کنند.
- این هنوز validation نهایی نیست، چون این comparison روی همان 8000-row dataset انجام شده و شامل بخش‌هایی از training/validation خود meta-model است.
- برای اعتبار واقعی باید Phase127A را در stream/full mode بسازیم و بعد Phase133A walk-forward را اجرا کنیم.
```

گام بعدی لازم:

```text
1) Build Phase127A full telemetry with source_mode=stream so flat_latest covers ~52832 rows / all months.
2) Retrain Phase128A on full flat.
3) Run Phase132A again.
4) Run Phase133A walk-forward as final research gate before production/paper.
```

## 2026-09-12 — Phase127A stream telemetry same-bar-policy fix

**Operator run result:** full stream telemetry build stopped after the first 500 streamed rows with:

```text
[X] AttributeError: 'Namespace' object has no attribute 'same_bar_policy'
```

**Root cause:** `scripts/build_hybrid_telemetry_tensor.py` reuses `simulate_trade()` from
`backtest_hybrid_xgboost_head.py`; that simulator expects `args.same_bar_policy`, but the
Phase127 telemetry tensor CLI did not expose or default this argument.

**Implementation:**
- Added `--same-bar-policy {stop_first,tp_first}` to `scripts/build_hybrid_telemetry_tensor.py` with default `stop_first`.
- Added the same field to the Dashboard command `Build hybrid telemetry tensor`.
- Updated GUI command argument forwarding so Dashboard runs pass `--same-bar-policy` to the script.
- Fixed stream-mode lagged telemetry consistency: after all chunks are concatenated, lagged trade telemetry is recomputed globally across the full streamed frame instead of being reset at every `--stream-chunk-size` boundary.

**Files changed:**
```text
scripts/build_hybrid_telemetry_tensor.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_telemetry_tensor.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

**Verification:**
```text
python -m ruff check scripts/build_hybrid_telemetry_tensor.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/build_hybrid_telemetry_tensor.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_telemetry_tensor.py tests/unit/presentation/test_architecture_knobs_gui.py -q
→ 65 passed

python -m pytest -q
→ 1760 passed, 54 skipped
```

**Full quality gate status:**
```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

**Next operator action:** rerun Phase127A full stream telemetry using the same command. The explicit default is now equivalent to adding:

```powershell
--same-bar-policy stop_first
```

## 2026-09-12 — Full stream Phase127A, Phase128A v2, and Phase133A walk-forward result recorded

**Phase127A full stream telemetry:**

```text
rows                : 52832
tensor_samples      : 10537
tensor_window       : 150
channels            : 94
tensor_shape        : [10537, 150, 94]
candidate_rows      : 13757
candidate_rate      : 26.0391429436705%
target_win_rate     : 41.266265511512756%
target_score_r_mean : -0.23007889091968536
target_pnl_sum      : -43309.8125
safe_lag_bars       : 48
source_mode         : stream
sample_stride       : 5
warnings            : []
```

Interpretation:

```text
Phase127A now passes as a full-history data-build step. The full candidate universe confirms the base hybrid is weak: 13,757 candidate rows with 41.27% target win rate and -43,309.81 raw PnL.
```

**Phase128A full-stream LightGBM training:**

```text
model_id          : gold_hybrid_meta_lightgbm_5m
version           : 2
rows              : 13757
feature_columns   : 94
train_rows        : 9629
val_rows          : 2064
test_rows         : 2064
candidate_only    : 1
booster           : lightgbm
record_path       : datasets\models\gold_hybrid_meta_lightgbm_5m\v2_training.json
```

Validation/test summary:

```text
val_ap/base       : 0.6117950637217242 / 0.4806201550387597
val_precision     : 0.5464733025708636
val_recall        : 0.8356854838709677
test_ap/base      : 0.7147311817866087 / 0.5184108527131783
test_precision    : 0.6214614878209348
test_recall       : 0.8822429906542056
```

Interpretation:

```text
The full-stream classifier has ranking signal, but acceptance depends on walk-forward trading validation, not classification metrics.
```

**Phase133A walk-forward validation:**

```text
folds                  : 6
positive_months        : 1
negative_months        : 4
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : -387.9482191801071
meta_gross_profit      : 1258.938264489174
meta_gross_loss        : 1646.886483669281
meta_profit_factor     : 0.764435361497561
meta_max_drawdown      : 460.49957263469696
meta_trades            : 288
meta_avg_pnl           : -1.3470424277087052
meta_final_balance     : 61.20517808198929
meta_return_percent    : -38.79482191801071%
meta_would_breach_zero : false
```

Fold detail:

```text
2026-04: threshold=0.70, meta= +25.1883, PF=1.1654, trades=24,  base=-228.3295
2026-05: threshold=0.60, meta=-122.8658, PF=0.4854, trades=35,  base=-465.0026
2026-06: threshold=0.70, meta=-210.3758, PF=0.6922, trades=100, base=-381.2333
2026-07: threshold=0.70, meta= -59.0373, PF=0.8710, trades=100, base=  +3.7473
2026-08: threshold=0.70, meta= -20.8577, PF=0.8181, trades=29,  base=-202.4170
2026-09: threshold=0.70, meta=  +0.0000, PF=0.0000, trades=0,   base= -15.6105
```

Decision:

```text
FAIL — Phase133A did not pass the production/paper gate.
The meta-filter reduces damage compared with the base hybrid, but it remains negative out-of-time and unstable by month.
No Phase134 paper shadow or live trading should be run with this candidate.
```

Recommended next actions:

```text
1) Run full-stream Phase132A comparison for gold_hybrid_meta_lightgbm_5m v2.
2) Run stricter Phase133A variants: thresholds 0.70-0.95, class_weight=off, and score_metric=drawdown_adjusted.
3) If flat meta remains negative, evaluate Phase129/130/131 tensor models only through walk-forward validation.
```

## 2026-09-12 — Phase133A negative score-threshold CLI parsing fix

**Operator run result:** the regressor walk-forward command failed before execution:

```text
run_hybrid_walk_forward_validation.py: error: argument --score-thresholds: expected one argument
```

Command fragment that triggered it:

```powershell
--score-thresholds -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
```

**Root cause:** this is an argparse edge case. A comma-separated value starting with a negative number, such as `-0.25,-0.10,0`, is interpreted as an option-like token when passed as the separate argument after `--score-thresholds`.

**Implementation:**
- Added threshold-argument normalization to `scripts/run_hybrid_walk_forward_validation.py`.
- Added the same normalization to `scripts/backtest_meta_filtered_hybrid.py`, because Phase132 also has `--score-thresholds` and can be used with score/regressor thresholds.
- The scripts now accept both forms:

```powershell
--score-thresholds -0.25,-0.10,0
--score-thresholds=-0.25,-0.10,0
```

**Verification:**

```text
python -m ruff check scripts/run_hybrid_walk_forward_validation.py scripts/backtest_meta_filtered_hybrid.py tests/unit/ai/test_hybrid_walk_forward_validation.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py
→ passed

python -m black --check scripts/run_hybrid_walk_forward_validation.py scripts/backtest_meta_filtered_hybrid.py tests/unit/ai/test_hybrid_walk_forward_validation.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_walk_forward_validation.py tests/unit/ai/test_meta_filtered_hybrid_comparison.py -q
→ 11 passed
```

**Immediate operator workaround without updating code:** use equals syntax:

```powershell
--score-thresholds=-0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
```

Full gate after this parser patch:

```text
python -m pytest -q
→ 1762 passed, 54 skipped

python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-12 — Phase133A regressor result and owner graphical map

**Operator request:** the project flow had become hard to follow; create a graphical/tree HTML page that explains architecture, documents, pipeline, and current decision state, and keep it updated every time.

**New owner-facing document:**

```text
docs/PROJECT_OWNER_MAP.html
```

The page includes:

```text
- Clean Architecture tree: Domain → Application → Infrastructure → Presentation
- Research pipeline graph from MT5/parquet data to Phase133 validation
- Decision tree showing pass/fail/blocked branches
- Model responsibility map
- Phase127-134 GUI command tree
- Latest result dashboard
- Artifact/log paths
- Maintenance checklist for future agents
```

**Permanent maintenance rule added:**

```text
docs/AGENTOPERATINGRULE.md now requires docs/PROJECT_OWNER_MAP.html to be updated after every meaningful code/result/phase/model-status/decision-gate change.
```

**Phase133A regressor result recorded:**

```text
task                  : regressor
target                : target_trade_score_r
score_thresholds      : -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
folds                 : 6
positive_months       : 2
negative_months       : 3
base_total_pnl        : -1288.8456037938595
meta_total_pnl        : +8.10892242193222
meta_profit_factor    : 1.0127550914970576
meta_max_drawdown     : 183.82112050056458
meta_trades           : 120
meta_avg_pnl          : +0.06757435351610183
meta_final_balance    : 100.81089224219322
meta_return_percent   : +0.8108922421932221%
```

Fold detail:

```text
2026-04: +81.4463 PF=1.8400 trades=20 threshold=0.10
2026-05: -37.0843 PF=0.5225 trades=11 threshold=0.10
2026-06: -43.2650 PF=0.8105 trades=29 threshold=0.50
2026-07: +27.1263 PF=1.1854 trades=39 threshold=0.50
2026-08: -20.1143 PF=0.7675 trades=21 threshold=0.05
2026-09:  +0.0000 PF=0.0000 trades=0  threshold=0.50
```

Decision:

```text
Near break-even but not accepted. The regressor is a better direction than the classifier, but PF=1.0128 and 2 positive vs 3 negative months do not pass the Phase133 gate. Phase134 paper/live remains blocked.
```

Verification for owner-map documentation update:

```text
HTML parse check for docs/PROJECT_OWNER_MAP.html
→ passed

python -m pytest -q
→ 1762 passed, 54 skipped

python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-12 — Owner map clarification for the 3D hybrid telemetry tensor

**Operator concern:** the owner asked where the promised 3D combined matrix/tensor is in the project, whether it was actually built, and what it is made from.

**Documentation update:** added a dedicated section to:

```text
docs/PROJECT_OWNER_MAP.html
```

The new section explicitly states:

```text
- The 3D tensor exists and is produced by Phase127A.
- Tensor artifact: datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
- Flat source matrix: datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
- Current full-stream shape: [10537, 150, 94]
- Axis 0 = samples, Axis 1 = 150-candle time window, Axis 2 = 94 feature channels.
- Recent LightGBM Phase128/133 runs used the 2D flat telemetry; the 3D tensor is intended for Phase129/130/131 sequence models.
```

No code changed in this entry.

## 2026-09-12 — Phase127A tensor visual inspector implemented

**Operator request:** make the 3D hybrid telemetry tensor tangible/visible and clarify how to build it for every 5M rolling window, not just the sampled tensor windows.

**Implementation:**

```text
scripts/inspect_hybrid_telemetry_tensor.py
GUI command: Inspect hybrid telemetry tensor
```

The inspector reads:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
```

and writes:

```text
run_logs\hybrid_tensor_inspector\latest.html
run_logs\hybrid_tensor_inspector\latest.json
```

It renders selected tensor samples as HTML heatmaps:

```text
X axis concept: [sample_index, time_inside_150_candle_window, feature_channel]
Rows in heatmap: feature channels
Columns in heatmap: time buckets from older candles to newer candles
```

**GUI/Dashboard:**

```text
CommandKind.INSPECT_HYBRID_TELEMETRY_TENSOR
Dashboard label: Inspect hybrid telemetry tensor
```

**Full-window tensor clarification:**

```text
The previous Phase127A stream tensor covered all source rows but used sample_stride=5 and max_samples=12000, producing 10537 samples.
For every possible 150-bar rolling window on 52832 rows, use sample_stride=1 and max_samples=0.
Expected full tensor shape: [52683, 150, 94]
Estimated float16 X size before compression: about 1417 MiB.
```

Verification for tensor inspector implementation:

```text
python -m ruff check scripts/inspect_hybrid_telemetry_tensor.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_tensor_inspector.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/inspect_hybrid_telemetry_tensor.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_tensor_inspector.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_tensor_inspector.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ 93 passed

python -m pytest -q
→ 1765 passed, 54 skipped
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-12 — Full tensor confirmed and WaveNet target clarified

**Operator result:** the every-window 3D tensor was successfully built and inspected.

```text
source rows              : 52832
tensor shape             : [52683, 150, 94]
dtype                    : float16
sample_stride            : 1
max_samples              : 0
estimated X size          : 1416.8363571166992 MiB
warnings                 : []
inspector selected samples: 0, 26341, 52682
inspector output          : run_logs\hybrid_tensor_inspector\latest.html
```

**Clarification recorded:** the WaveNet model that consumes this tensor is Phase129A:

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
GUI: Train telemetry WaveNet/TCN
GUI: Backtest telemetry WaveNet/TCN
model_id: gold_hybrid_telemetry_wavenet_5m
```

**Target decision:** first WaveNet run should be `--task multihead`:

```text
meta_win head -> target_trade_win
score_r head  -> target_trade_score_r
```

Rationale:

```text
The win-only classifier failed Phase133A; score_r regression was materially better and near break-even. Therefore score_r is the primary trading-quality target, while win probability can be kept as an auxiliary head.
```

## 2026-09-12 — Clarified Phase129A WaveNet training split vs walk-forward

**Operator concern:** while Phase129A WaveNet/TCN training was running, the operator asked whether it was mistakenly not doing roll-forward.

Clarification:

```text
scripts/train_hybrid_telemetry_wavenet.py does not run monthly expanding walk-forward.
It runs one chronological train/validation/test split with purge_gap.
```

Current observed run:

```text
full tensor shape before candidate filter : [52683, 150, 94]
candidate_only                            : 1
training input shape after candidate filter: [13692, 150, 94]
split                                      : 9584 / 1718 / 1718
purge_gap                                  : 336
monitor                                    : val_loss
epochs requested                           : 500
early_stopping_patience                    : 8
```

Assessment:

```text
This is correct for initial Phase129A artifact training and not a random/leaky split.
It is not final walk-forward validation. If the artifact/backtest is promising, a tensor-model walk-forward validation phase/command is still required before production/paper.
```

## 2026-09-12 — Phase129A WaveNet/TCN v1 training and initial score-mode replay

**Operator result:** Phase129A WaveNet/TCN was trained on the full 3D tensor.

Training:

```text
model_id       : gold_hybrid_telemetry_wavenet_5m
version        : 1
task           : multihead
candidate_only : 1
rows           : 13692
tensor_window  : 150
channels       : 94
train_rows     : 9584
val_rows       : 1718
test_rows      : 1718
purge_gap      : 336
record_path    : datasets\models\gold_hybrid_telemetry_wavenet_5m\v1_training.json
```

Key metrics:

```text
val_meta_ap                      : 0.5189458439202039
test_meta_ap                     : 0.5377916962550442
val_meta_prob_stdev              : 0.2892801567904343
test_meta_prob_stdev             : 0.2399177476745701
val_meta_collapse                : 0.0
test_meta_collapse               : 0.0
val_score_mae                    : 0.8421052456884921
test_score_mae                   : 0.8726781023827808
val_score_pred_stdev             : 0.47359669000282073
test_score_pred_stdev            : 0.37248512880185
val_score_collapse               : 0.0
test_score_collapse              : 0.0
test_score_selected_rate         : 0.27648428405122233
test_score_selected_target_mean  : +0.1913444548845291
```

Initial backtest:

```text
script           : scripts/backtest_hybrid_telemetry_wavenet.py
decision_mode    : score
score_threshold  : 0
eval_frac        : 1.0
rows             : 52683 / 52683
trades           : 384
coverage         : 0.73%
skipped_nn       : 9520
total_pnl        : +1914.66
profit_factor    : 2.604
final_balance    : 291.47 with initial=100 and units=0.1
```

Assessment:

```text
Promising but not final. This is a full-history replay of a model trained on an earlier portion of the same candidate tensor set; eval_frac=1.0 includes training-era windows. It indicates the 3D tensor/WaveNet path has real potential, but production/paper remains blocked until out-of-time and tensor walk-forward validation pass.
```

## 2026-09-12 — WaveNet v1 full JSON and last-15% replay reviewed

**Full score-mode replay:**

```text
eval_frac      : 1.0
rows/evaluated : 52683 / 52683
trades         : 384
buy/sell       : 215 / 169
wins/losses    : 242 / 142
win_rate       : 63.0208%
total_pnl      : +1914.6646151691675
avg_pnl        : +4.986105768669707
profit_factor  : 2.603926956615171
max_drawdown   : 192.19346404075623
coverage       : 0.7289%
final_balance  : 291.46646151691675
```

Full replay monthly:

```text
2025-12 +205.61 PF=4.4145 trades=51
2026-01 +257.99 PF=3.5067 trades=44
2026-02 +463.73 PF=2.5933 trades=46
2026-03 +668.79 PF=7.0685 trades=49
2026-04 +328.46 PF=9.8534 trades=36
2026-05  -4.30 PF=0.9819 trades=63
2026-06 -49.71 PF=0.6996 trades=38
2026-07 +78.63 PF=1.5753 trades=48
2026-08 -34.54 PF=0.3365 trades=9
```

**Last-15% score-mode replay:**

```text
eval_frac      : 0.15
rows/evaluated : 52683 / 7902
trades         : 29
buy/sell       : 6 / 23
wins/losses    : 16 / 13
win_rate       : 55.1724%
total_pnl      : +29.590763092041016
avg_pnl        : +1.0203711411048626
profit_factor  : 1.316544651614474
max_drawdown   : 52.06632328033447
coverage       : 0.3670%
final_balance  : 102.95907630920411
```

Last-15% monthly:

```text
2026-07 +64.1343 PF=2.5486 trades=20
2026-08 -34.5435 PF=0.3365 trades=9
```

Assessment:

```text
WaveNet v1 is the strongest tensor-path signal so far and the last-15% proxy remains positive. However, only 29 trades in the out-of-time proxy and a negative August mean the result is fragile. Production/paper remains blocked. Next recommended actions are threshold robustness and/or a score-focused longer WaveNet v2 run, followed by tensor walk-forward validation.
```

## 2026-09-13 — Phase129A WaveNet v2 long-train result reviewed

**Operator result:** long score-focused WaveNet/TCN training produced `gold_hybrid_telemetry_wavenet_5m v2`.

Configuration:

```text
task              : multihead
rows              : 13692
train/val/test    : 9584 / 1718 / 1718
filters           : 64
n_layers          : 6
n_blocks          : 2
dense_units       : 96
dropout           : 0.25
learning_rate     : 0.0005
score_loss_weight : 1.0
monitor_metric    : val_score_r_mae
patience          : 25
```

v2 metrics:

```text
val_meta_ap                     : 0.6418573203049249
test_meta_ap                    : 0.4581884952337111
val_score_mae                   : 0.7433294282298605
test_score_mae                  : 0.9537305706318867
val_score_selected_rate         : 0.35681024447031434
test_score_selected_rate        : 0.459837019790454
val_score_selected_target_mean  : +0.12646526098251343
test_score_selected_target_mean : -0.13298217952251434
val_score_collapse              : 0.0
test_score_collapse             : 0.0
```

Comparison with v1:

```text
v1 test_meta_ap                     : 0.5377916962550442
v2 test_meta_ap                     : 0.4581884952337111
v1 test_score_mae                   : 0.8726781023827808
v2 test_score_mae                   : 0.9537305706318867
v1 test_score_selected_target_mean  : +0.1913444548845291
v2 test_score_selected_target_mean  : -0.13298217952251434
```

Decision:

```text
v2 is worse than v1 on the test split. Do not treat v2 as the preferred candidate. The result shows validation overfit/regime mismatch: validation improved, but test score-selected candidates became negative.
```

Operator backtest command error:

```text
unrecognized arguments: -u scripts/backtest_hybrid_telemetry_wavenet.py
```

Cause and fix:

```text
A second python command was accidentally concatenated after --storage-root datasets.
Run one command at a time. Since model-version 0 now resolves to latest=v2, use --model-version 1 for v1 and --model-version 2 for explicit v2 audit.
```

## 2026-09-13 — Phase129A WaveNet v2 last-15% backtest rejected

**Operator result:** explicit last-15% backtest for `gold_hybrid_telemetry_wavenet_5m v2`.

```text
model_version  : 2
decision_mode  : score
score_threshold: 0.0
eval_frac      : 0.15
rows/evaluated : 52683 / 7902
```

Summary:

```text
trades          : 89
buy/sell        : 58 / 31
wins/losses     : 29 / 60
timeouts        : 2
win_rate        : 32.5843%
total_pnl       : -178.49363827705383
avg_pnl         : -2.005546497494987
profit_factor   : 0.5542918793438448
max_drawdown    : 212.62753653526306
coverage        : 1.1263%
final_balance   : 82.15063617229461
```

Monthly:

```text
2026-07:   -3.3839 PF=0.9646 trades=31
2026-08: -168.3904 PF=0.4355 trades=56
2026-09:   -6.7193 PF=0.0000 trades=2
```

Comparison against v1 last-15%:

```text
v1: +29.5908 raw PnL, PF=1.3165, trades=29, maxDD=52.0663
v2: -178.4936 raw PnL, PF=0.5543, trades=89, maxDD=212.6275
```

Decision:

```text
REJECT v2. It overtrades and fails the out-of-time proxy. v1 remains the preferred WaveNet tensor candidate, but it is still research-only until threshold robustness and tensor walk-forward validation pass.
```

## 2026-09-13 — Phase132A WaveNet v1 last-15% threshold grid

**Operator result:** Phase132A compared base vs `gold_hybrid_telemetry_wavenet_5m v1` on the last 15% tensor universe.

Configuration:

```text
candidates         : base,gold_hybrid_telemetry_wavenet_5m
candidate_versions : 0,1
decision_modes     : score,both
meta_thresholds    : record,0.55,0.60,0.65,0.70
score_thresholds   : -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50,0.75,1.00
eval_frac          : 0.15
samples            : 7902
min_trades         : 10
```

Base row:

```text
trades        : 195
wins/losses   : 67 / 128
win_rate      : 34.3590%
total_pnl     : -247.1424761712551
profit_factor : 0.70282875694799
max_drawdown  : 272.11317190527916
final_balance : 75.28575238287449
```

Best WaveNet v1 row:

```text
candidate       : gold_hybrid_telemetry_wavenet_5m:score:meta=record:score=0.05
decision_mode   : score
score_threshold : 0.05
trades          : 22
buy/sell        : 5 / 17
wins/losses     : 14 / 8
win_rate        : 63.6364%
total_pnl       : +42.78727626800537
avg_pnl         : +1.9448761940002441
profit_factor   : 1.6478747062665267
max_drawdown    : 32.968711853027344
coverage        : 0.2784%
final_balance   : 104.27872762680053
```

Threshold pattern:

```text
score=-0.25 : -117.3837 PF=0.6991 trades=91
score=-0.10 :  -55.0679 PF=0.7756 trades=56
score= 0.00 :  +29.5908 PF=1.3165 trades=29
score= 0.05 :  +42.7873 PF=1.6479 trades=22  BEST
score= 0.10 :  +35.4562 PF=1.7217 trades=18
score= 0.20 :   +8.3745 PF=2.2427 trades=5 below min_trades
```

Assessment:

```text
This confirms v1 has a useful score threshold region on the last-15% diagnostic slice. score_threshold=0.05 beats both base and the previous score_threshold=0.00 replay. However, threshold selection happened on the evaluation slice, so this is not production validation. Next required step: tensor-model walk-forward validation with threshold selection only on past validation windows.
```

Implementation note:

```text
In decision_mode=score, meta_threshold is ignored by design. Duplicate score-mode rows across different meta_thresholds are expected.
```

## 2026-09-13 — Phase133B tensor-model walk-forward validation implemented

**Operator request:** build Phase133B for true tensor-model walk-forward validation after WaveNet v1 showed promising diagnostic threshold-grid results.

**Implemented:**

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
GUI: Run tensor walk-forward validation
```

**Current implemented model family:**

```text
model_family=wavenet
```

The script trains a fresh Phase129A WaveNet/TCN in memory for every test month. It does not reuse the previously saved v1/v2 model, because real walk-forward validation must train only on data available before each fold.

**Protocol:**

```text
for each eligible test_month:
  train_months      = all months before validation block
  validation_months = immediate month(s) before test
  test_month        = next unseen month

  purge validation rows near test boundary
  purge train rows near validation boundary
  train WaveNet/TCN only on the training window
  early-stop using candidate validation rows
  predict validation/test tensor rows
  choose decision_mode + thresholds only on validation replay
  run test replay with that selected threshold
  record base vs tensor metrics
```

**Key controls:**

```text
--decision-modes score,both
--meta-thresholds 0.55,0.60,0.65,0.70
--score-thresholds -0.10,0,0.05,0.10,0.20
--purge-gap-bars 336
--candidate-only 1
```

**Outputs:**

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
run_logs\hybrid_tensor_walk_forward_validation\latest.csv
run_logs\hybrid_tensor_walk_forward_validation\latest.html
```

**GUI additions:**

```text
CommandKind.RUN_HYBRID_TENSOR_WALK_FORWARD_VALIDATION
Descriptor: Run tensor walk-forward validation
Handler: AccountCommandHandlers.run_hybrid_tensor_walk_forward_validation
```

**Acceptance:** Phase134 paper/live remains blocked until Phase133B passes out-of-time stability gates.

Verification for Phase133B implementation:

```text
python -m ruff check scripts/run_hybrid_tensor_walk_forward_validation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_tensor_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m black --check scripts/run_hybrid_tensor_walk_forward_validation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_tensor_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_tensor_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ 97 passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1831 tests collected
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-13 — Phase133B tensor WaveNet walk-forward result failed

**Operator result:** Phase133B tensor-model walk-forward validation was run on the full 3D tensor using the WaveNet/TCN family.

Configuration:

```text
model_family      : wavenet
task              : multihead
candidate_only    : 1
train_months_min  : 3
validation_months : 1
purge_gap_bars    : 336
decision_modes    : score,both
score_thresholds  : -0.10,0,0.05,0.10,0.20
score_metric      : total_pnl
epochs            : 500
architecture      : filters=48, n_layers=5, n_blocks=2, dense_units=64, dropout=0.20
```

Aggregate:

```text
folds                    : 6
positive_months          : 2
negative_months          : 3
base_total_pnl           : -1288.8456037938595
tensor_total_pnl         : -409.51990616321564
tensor_gross_profit      : 608.841717839241
tensor_gross_loss        : 1018.3616240024567
tensor_profit_factor     : 0.5978639645181408
tensor_max_drawdown      : 464.1122056245804
tensor_trades            : 200
tensor_avg_pnl           : -2.047599530816078
tensor_final_balance     : 59.04800938367843
tensor_return_percent    : -40.951990616321565%
```

Fold detail:

```text
2026-04: val=-102.5548, tensor=-144.8683, PF=0.3253, trades=35,  selected score=0.05
2026-05: val= -42.2108, tensor=-270.3103, PF=0.5553, trades=115, selected score=-0.10
2026-06: val=-107.0676, tensor=  +7.8459, PF=1.0769, trades=25,  selected both meta=0.70 score=0.20
2026-07: val= +26.0419, tensor= -23.4140, PF=0.4207, trades=8,   selected both meta=0.65 score=0.05
2026-08: val= +44.9376, tensor= +21.2268, PF=1.3981, trades=17,  selected both meta=0.65 score=-0.10
2026-09: val= +44.3921, tensor=  +0.0000, PF=0.0000, trades=0,   selected score=0.20
```

Decision:

```text
FAIL. The tensor WaveNet path does not pass production/paper validation. It reduced base loss but remained strongly negative and worse than the flat LightGBM score_r walk-forward result.
```

Interpretation:

```text
The earlier WaveNet v1 last-15% threshold grid was promising but not robust. True fold-by-fold retraining and validation-selected thresholds did not generalize. Several folds selected a threshold even when validation PnL was negative, suggesting the next research improvement should be a validation no-trade/risk gate rather than a bigger model.
```

Operational rule remains:

```text
No Phase134 paper shadow, no live trading, no production acceptance.
```

## 2026-09-13 — Phase133C validation no-trade/risk gate implemented

**Operator instruction:** proceed with the proposed validation no-trade/risk gate after Phase133B failed.

**Implemented as extension of:**

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
GUI: Run tensor walk-forward validation
```

**New flags:**

```text
--allow-no-trade {0,1}
--min-validation-score FLOAT
--min-validation-profit-factor FLOAT
--max-validation-drawdown FLOAT
```

**New output fields:**

```text
selected_validation_profit_factor
selected_validation_max_drawdown
no_trade_selected
aggregate.no_trade_months
```

**Behavior:**

```text
When allow_no_trade=1, a fold can select selected_decision_mode=no_trade if the best validation threshold fails the configured validation gates. The test fold then records zero trades and zero PnL instead of forcing a weak threshold.
```

**Recommended first Phase133C settings:**

```text
allow_no_trade               : 1
min_validation_score         : 0
min_validation_profit_factor : 1.10
max_validation_drawdown      : 120
```

Verification for Phase133C implementation:

```text
python -m ruff check scripts/run_hybrid_tensor_walk_forward_validation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_tensor_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m black --check scripts/run_hybrid_tensor_walk_forward_validation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_tensor_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_tensor_walk_forward_validation.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1833 tests collected
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-13 — Phase133C validation no-trade gate result reviewed

**Operator result:** Phase133C tensor walk-forward was run with no-trade/risk gates enabled.

Configuration:

```text
allow_no_trade               : 1
min_validation_score         : 0.0
min_validation_profit_factor : 1.10
max_validation_drawdown      : 120.0
```

Aggregate:

```text
folds                    : 6
positive_months          : 0
negative_months          : 1
no_trade_months          : 3
base_total_pnl           : -1288.8456037938595
tensor_total_pnl         : -32.83297738432884
tensor_profit_factor     : 0.7655299301860462
tensor_max_drawdown      : 86.88896641135216
tensor_trades            : 35
tensor_avg_pnl           : -0.9380850681236812
tensor_final_balance     : 96.71670226156712
```

Fold decisions:

```text
2026-04: validation OK, selected both meta=0.55 score=0.05, test trades=0, pnl=0
2026-05: NO_TRADE, validation_score=-36.3806 below 0, pnl=0
2026-06: NO_TRADE, validation_score=-107.9652 below 0, pnl=0
2026-07: NO_TRADE, validation PF=1.0427 below 1.10, pnl=0
2026-08: traded 35, tensor=-32.8330, PF=0.7655
2026-09: validation OK, selected score=-0.10, test trades=0, pnl=0
```

Comparison:

```text
Base WF        : -1288.8456
Phase133B WF   :  -409.5199
Phase133C WF   :   -32.8330
```

Assessment:

```text
Phase133C is useful as damage control but failed as an alpha strategy. It cut most losses, but PnL is still negative, PF is below 1, and the only active trading month lost money. Phase134 remains blocked.
```

Recommended next step:

```text
Do not train larger WaveNet models. Build failure/regime diagnostics to identify validation-to-test transfer failure by month, side, session, range context, and candidate quality.
```

## 2026-09-14 — Phase136A tensor failure/regime diagnostics implemented

**Operator request:** build Phase136A to diagnose why Phase133B/C failed instead of continuing blind training.

**Implemented:**

```text
scripts/analyze_tensor_failure_regimes.py
GUI: Analyze tensor failure regimes
```

**Purpose:**

```text
Explain validation-to-test transfer failures and candidate-regime weaknesses after Phase133C reduced losses but still failed as a strategy.
```

**Inputs:**

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
run_logs\hybrid_tensor_walk_forward_validation\latest.json
```

**Outputs:**

```text
run_logs\tensor_failure_regimes\latest.json
run_logs\tensor_failure_regimes\latest.html
run_logs\tensor_failure_regimes\latest_regimes.csv
run_logs\tensor_failure_regimes\latest_transfer.csv
```

**GUI additions:**

```text
CommandKind.ANALYZE_TENSOR_FAILURE_REGIMES
Dashboard label: Analyze tensor failure regimes
Handler: AccountCommandHandlers.analyze_tensor_failure_regimes
```

**Diagnostics included:**

```text
month, side, month_side, hour, side_hour, outcome,
specialist_conflict, candidate confidence, reward/risk,
TP/SL distance, side-aware 4H/1D room, booster entropy/margin,
validation-to-test transfer status.
```

**Important limitation:**

```text
Regime rows are candidate-outcome diagnostics, not chronological replay. They generate hypotheses for a future filter; they do not approve production/paper.
```

Verification for Phase136A implementation:

```text
python -m ruff check scripts/analyze_tensor_failure_regimes.py tests/unit/ai/test_tensor_failure_regimes.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/analyze_tensor_failure_regimes.py tests/unit/ai/test_tensor_failure_regimes.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_tensor_failure_regimes.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1839 tests collected
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-14 — Phase136A tensor failure/regime diagnostics result reviewed

**Operator result:** Phase136A was run on full candidate telemetry and the latest Phase133C walk-forward JSON.

Top-level candidate distribution:

```text
candidate_rows : 13757
months         : 10
total_pnl      : -43309.811259036884
win_rate       : 41.2663%
profit_factor  : 0.6215092452270718
worst_month    : 2026-02
best_month     : 2026-07
```

Transfer summary:

```text
transfer_rows          : 6
transfer_total_pnl     : -32.83297738432884
transfer_profit_factor : 0.7655299301860462
no_trade_months        : 3
```

Risk flags:

```text
1 fold had positive validation quality but negative test PnL.
3 folds were blocked by validation no-trade gates.
1 active trading fold still lost money after gates.
BUY side is negative: -39003.71 raw PnL.
SELL side is negative: -4306.10 raw PnL.
```

Worst regimes:

```text
stop_loss outcome: rows=7256, share=52.7441%, total_pnl=-106988.0392
BUY side: rows=8583, win_rate=35.7917%, total_pnl=-39003.7073, PF=0.5106
2026-02: rows=1945, total_pnl=-21573.3665, PF=0.3872
large SL-distance bin: total_pnl=-22248.0623
wide 1D/4H range bins: strongly negative
high candidate_confidence bin: total_pnl=-14063.6031
```

Positive diagnostic pockets:

```text
2026-04 / SELL: +2682.8371 PF=2.1863 rows=568
2026-03 / SELL: +2308.4453 PF=1.8384 rows=398
2026-07 / SELL: +1963.2321 PF=1.4834 rows=1185
2026-06 / SELL: +669.4895 PF=1.2756 rows=571
2026-08 / SELL: +469.5280 PF=1.6627 rows=256
SELL / hour=9: +901.0482 PF=1.8986 rows=235
SELL / hour=8: +640.0451 PF=1.3392 rows=348
```

Conclusion:

```text
Phase136A provides a clear next hypothesis: BUY candidates are structurally harmful, while SELL has possible live-safe pockets. The next phase should not train a larger model; it should test SELL-only and regime-filtered chronological replay/walk-forward.
```

## 2026-09-14 — Phase137A regime-filtered hybrid replay implemented

**Operator instruction:** build the next phase, but do not permanently remove BUY.

**Implemented:**

```text
scripts/backtest_regime_filtered_hybrid.py
GUI: Backtest regime-filtered hybrid
```

**Purpose:**

```text
Convert Phase136A failure/regime hypotheses into chronological replay tests.
```

**Key design decision:**

```text
BUY is not deleted. The default filter is allowed_sides=BUY,SELL.
SELL-only is available only as a diagnostic test.
Side-specific BUY/SELL filters can test strict BUY gates without removing BUY from the architecture.
```

**Supported filters include:**

```text
allowed_sides
allowed_hours / buy_allowed_hours / sell_allowed_hours
candidate confidence and reward/risk
BUY/SELL-specific confidence and reward/risk
SL distance and BUY/SELL-specific SL distance
side-aware 4H/1D room
range width
specialist conflict
booster entropy/action margin
specialist max probability
```

**Outputs:**

```text
run_logs\regime_filtered_hybrid\latest.json
run_logs\regime_filtered_hybrid\latest.html
run_logs\regime_filtered_hybrid\latest.csv
```

Verification for Phase137A implementation:

```text
python -m ruff check scripts/backtest_regime_filtered_hybrid.py tests/unit/ai/test_regime_filtered_hybrid.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/backtest_regime_filtered_hybrid.py tests/unit/ai/test_regime_filtered_hybrid.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_regime_filtered_hybrid.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1845 tests collected
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-14 — Phase137A initial regime-filtered replay results

**Operator result 1: SELL-only diagnostic replay**

```text
allowed_sides          : SELL
source_candidates      : 13757
kept_candidates        : 5174
removed_candidates     : 8583
base_total_pnl         : -4590.797205492854
filtered_total_pnl     : -848.8386568725109
filtered_profit_factor : 0.7290926647116155
filtered_max_drawdown  : 1040.8391872644424
filtered_trades        : 581
filtered_win_rate      : 35.2840%
filtered_final_balance : 15.116134312748898
would_breach_zero      : true
```

Monthly:

```text
2026-01   -0.8822 PF=0.9943 trades=20
2026-02 -430.7218 PF=0.3631 trades=62
2026-03  -53.4108 PF=0.8580 trades=61
2026-04  +40.9952 PF=1.1149 trades=83
2026-05 -423.1884 PF=0.5078 trades=162
2026-06  -16.2552 PF=0.9340 trades=61
2026-07  +87.4448 PF=1.2510 trades=103
2026-08  -52.8203 PF=0.5398 trades=29
```

Assessment:

```text
SELL-only reduces base damage but fails as a strategy. It is not enough to block BUY.
```

**Operator result 2: mixed BUY,SELL with initial strict BUY gates**

```text
allowed_sides          : BUY,SELL
buy_min_confidence     : 0.98
buy_min_side_4h_room   : 5
buy_min_side_1d_room   : 10
buy_max_sl_distance    : 20
kept_candidates        : 6360
filtered_total_pnl     : -2018.1994965970516
filtered_profit_factor : 0.585046282276268
filtered_trades        : 883
filtered_final_balance : -101.81994965970517
```

Assessment:

```text
The first strict-BUY filter is worse than SELL-only. BUY remains part of the architecture, but current BUY gates are not adequate. Next diagnostic should test narrower SELL pockets such as SELL hours 8/9 and then design BUY-specific diagnostics separately.
```

## 2026-09-14 — Phase137A focused SELL h8/9 replay result

**Operator result:** focused SELL-hours replay.

Configuration:

```text
allowed_sides      : SELL
sell_allowed_hours : 8,9
eval_frac          : 1.0
```

Result:

```text
source_candidates       : 13757
kept_candidates         : 583
removed_candidates      : 13174
kept_rate               : 4.2378%
base_total_pnl          : -4590.797205492854
filtered_total_pnl      : +16.920441061258316
filtered_profit_factor  : 1.037288325923403
filtered_max_drawdown   : 89.34972810745239
filtered_trades         : 77
filtered_win_rate       : 38.9610%
filtered_final_balance  : 101.69204410612583
would_breach_zero       : false
```

Monthly:

```text
2026-01 +18.0882 PF=2.1592 trades=5
2026-02 -44.2072 PF=0.5853 trades=7
2026-03 +38.7940 PF=1.7817 trades=8
2026-04 +52.3129 PF=2.5081 trades=9
2026-05 -71.4458 PF=0.5502 trades=24
2026-06 +21.1881 PF=1.5779 trades=11
2026-07  +0.1820 PF=1.0035 trades=11
2026-08  +2.0082 PF=6.8089 trades=2
```

Assessment:

```text
Weak positive but not a pass. SELL h8/9 is the first manual regime filter to turn full-history replay positive, but PF=1.037 is below the acceptance guideline and PnL is small. Continue with live-safe filters to reduce 2026-02/05 losses. Do not use month exclusion as a production rule.
```

## 2026-09-14 — Phase137A SELL h8/9 + max SL distance result

**Operator result:** SELL h8/9 replay with `sell_max_sl_distance=23.56`.

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
eval_frac            : 1.0
```

Result:

```text
source_candidates       : 13757
kept_candidates         : 503
removed_candidates      : 13254
kept_rate               : 3.6563%
base_total_pnl          : -4590.797205492854
filtered_total_pnl      : +23.147499471902847
filtered_profit_factor  : 1.0608648649692447
filtered_max_drawdown   : 89.64815473556519
filtered_trades         : 73
filtered_win_rate       : 36.9863%
filtered_final_balance  : 102.31474994719028
would_breach_zero       : false
```

Monthly:

```text
2026-01 +18.0882 PF=2.1592 trades=5
2026-02 -51.4716 PF=0.0000 trades=5
2026-03 +53.9956 PF=2.4144 trades=7
2026-04 +46.0941 PF=2.4267 trades=8
2026-05 -66.9372 PF=0.5663 trades=24
2026-06 +21.1881 PF=1.5779 trades=11
2026-07  +0.1820 PF=1.0035 trades=11
2026-08  +2.0082 PF=6.8089 trades=2
```

Assessment:

```text
This improves the previous SELL h8/9 replay from +16.92/PF=1.037 to +23.15/PF=1.061, but still fails acceptance. Next diagnostic should keep SELL h8/9 and SL<=23.56, then add a 4H range-width cap.
```

## 2026-09-14 — Phase137A SELL h8/9 + SL + 4H width cap result

**Operator result:** tested broad 4H width cap on top of the current weak-positive SELL h8/9 + SL filter.

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
max_range_4h_width   : 33.305
```

Result:

```text
source_candidates       : 13757
kept_candidates         : 428
removed_candidates      : 13329
kept_rate               : 3.1111%
base_total_pnl          : -4590.797205492854
filtered_total_pnl      : -26.330932468175888
filtered_profit_factor  : 0.8915300951853891
filtered_max_drawdown   : 89.88325047492981
filtered_trades         : 50
filtered_win_rate       : 42.0%
filtered_final_balance  : 97.3669067531824
```

Monthly:

```text
2026-04 +34.4846 PF=999.0 trades=3
2026-05 -66.9372 PF=0.5663 trades=24
2026-06  +3.9314 PF=1.1072 trades=10
2026-07  +0.1820 PF=1.0035 trades=11
2026-08  +2.0082 PF=6.8089 trades=2
```

Assessment:

```text
Rejected. The broad 4H width cap made the filter negative. It removed January/March positive contribution but did not remove the May loss. The current best remains SELL h8/9 + SL<=23.56, still weak and not accepted.
```

## 2026-09-14 — Phase137A exact 4H width pocket result

**Operator result:** tested exact positive 4H width pocket with the current SELL h8/9 + SL cap filter.

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
min_range_4h_width   : 21.741
max_range_4h_width   : 26.928
eval_frac            : 1.0
```

Result:

```text
source_candidates      : 13757
kept_candidates        : 166
removed_candidates     : 13591
kept_rate              : 1.2067%
base_total_pnl         : -4590.797205492854
filtered_total_pnl     : +11.376214891672134
filtered_profit_factor : 1.1828907946231388
filtered_max_drawdown  : 19.283453941345215
filtered_trades        : 14
filtered_win_rate      : 57.1429%
filtered_final_balance : 101.13762148916722
```

Monthly:

```text
2026-04  +6.8169 trades=1
2026-05  +6.6403 trades=3
2026-06 +12.7187 trades=4
2026-07 -16.8079 trades=4
2026-08  +2.0082 trades=2
```

Assessment:

```text
This is the first Phase137A regime with PF > 1.10 and materially lower drawdown, but it is a tiny micro-regime with only 14 trades and low total PnL. It is not deployable. Next step: run the exact same filter with eval_frac=0.15 to test recent robustness.
```

## 2026-09-14 — Phase137A exact 4H pocket recent holdout failed

**Operator result:** exact 4H width pocket tested on recent 15%.

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
min_range_4h_width   : 21.741
max_range_4h_width   : 26.928
eval_frac            : 0.15
```

Result:

```text
evaluated_rows         : 7924
source_candidates      : 1445
kept_candidates        : 70
filtered_trades        : 4
filtered_total_pnl     : -17.275230020284653
filtered_profit_factor : 0.11992036742639664
filtered_max_drawdown  : 19.283453941345215
filtered_final_balance : 98.27247699797154
```

Monthly:

```text
2026-07 -19.2835 PF=0.0 trades=2
2026-08  +2.0082 PF=6.8089 trades=2
```

Assessment:

```text
The exact 4H pocket failed recent holdout. Reject it as robust. The current best manual full-history filter remains SELL h8/9 + SL<=23.56, but it also needs recent-holdout validation.
```

## 2026-09-14 — Phase137A current-best manual SELL filter recent holdout failed

**Operator result:** current-best full-history manual filter tested on recent 15%.

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
eval_frac            : 0.15
```

Result:

```text
evaluated_rows         : 7924
source_candidates      : 1445
kept_candidates        : 104
kept_rate              : 7.1972%
base_total_pnl         : -241.5674167573452
filtered_total_pnl     : -22.4049571454525
filtered_profit_factor : 0.40983705655862596
filtered_max_drawdown  : 37.618305921554565
filtered_trades        : 8
filtered_win_rate      : 25.0%
filtered_final_balance : 97.75950428545475
```

Monthly:

```text
2026-07 -24.4132 PF=0.3510 trades=6
2026-08  +2.0082 PF=6.8089 trades=2
```

Assessment:

```text
This rejects the current-best manual SELL filter as robust. It was weakly positive on full history (+23.15 raw, PF=1.061) but failed recent holdout (-22.40 raw, PF=0.410). Manual filtering should pause. Next work should inspect trade anatomy, TP/SL design, BUY-side damage and stop-loss concentration.
```

## 2026-09-14 — Phase138A trade anatomy / TP-SL failure analysis implemented

**Operator instruction:** start the next phase after Phase137A manual filters failed recent holdout.

**Implemented:**

```text
scripts/analyze_trade_anatomy.py
GUI: Analyze trade anatomy
```

**Purpose:**

```text
Analyze trade construction and TP/SL failure anatomy rather than adding more manual filters or training larger models.
```

**Diagnostics:**

```text
side, outcome, side_outcome, month, month_side, hour, side_hour,
TP distance bins, SL distance bins, reward/risk bins,
hold bars, side-aware 4H/1D room, range width, candidate confidence,
take-profit rate, stop-loss rate, timeout rate.
```

**Outputs:**

```text
run_logs\trade_anatomy\latest.json
run_logs\trade_anatomy\latest.html
run_logs\trade_anatomy\latest_anatomy.csv
```

Verification for Phase138A implementation:

```text
python -m ruff check scripts/analyze_trade_anatomy.py tests/unit/ai/test_trade_anatomy.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/analyze_trade_anatomy.py tests/unit/ai/test_trade_anatomy.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_trade_anatomy.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1852 tests collected
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-15 — Phase138A trade anatomy result reviewed

**Operator result:** Phase138A was run on the full candidate telemetry matrix.

Top-level:

```text
candidate_rows : 13757
total_pnl      : -43309.811259036884
win_rate       : 41.2663%
profit_factor  : 0.6215092452270718
max_drawdown   : 45887.01167863794
take_profit    : 37.3846%
stop_loss      : 52.7441%
timeout        : 9.8713%
```

Side anatomy:

```text
BUY rows              : 8583
BUY total_pnl         : -39003.70734734554
BUY PF                : 0.5106436955011304
BUY stop_loss_rate    : 59.0703%
BUY avg_sl_distance   : 17.6224

SELL rows             : 5174
SELL total_pnl        : -4306.103911691345
SELL PF               : 0.8760
SELL stop_loss_rate   : 42.2497%
SELL avg_sl_distance  : 17.5396
```

Worst anatomy:

```text
stop_loss total_pnl       : -106988.0392 over 7256 rows
BUY / stop_loss total_pnl : -75934.2056 over 5070 rows
SELL / stop_loss total_pnl: -31053.8336 over 2186 rows
SL distance high bin      : -22248.0623 for (23.56,124.647]
2026-02 month             : -21573.3665, stop_loss_rate=66.4267%
```

Key TP/SL insight:

```text
stop_loss candidates: avg_tp_distance=22.5691, avg_sl_distance=14.7448, avg_reward_risk=2.8001, avg_hold_bars=12.2172
take_profit candidates: avg_tp_distance=13.0167, avg_sl_distance=20.5877, avg_reward_risk=0.8209, avg_hold_bars=16.2364
```

Assessment:

```text
High nominal reward/risk / far TP is not a quality signal in the current bracket construction. It often corresponds to fast stop-losses. BUY remains the largest damage source but should not be deleted; it needs side-specific TP/SL/bracket recalibration.
```

Recommended next phase:

```text
Phase139A — TP/SL Bracket Recalibration Replay
```

## 2026-09-15 — Phase139A TP/SL bracket recalibration replay implemented

**Operator instruction:** build the next phase after Phase138A showed TP/SL and bracket anatomy problems.

**Implemented:**

```text
scripts/backtest_bracket_recalibration.py
GUI: Backtest bracket recalibration
```

**Purpose:**

```text
Replay alternative TP/SL caps and reward/risk caps on the existing hybrid candidates without model training.
```

**Policy grid controls:**

```text
max_tp_distances
max_sl_distances
max_reward_risks
BUY-specific max TP/SL/RR overrides
SELL-specific max TP/SL/RR overrides
same_bar_policy
spread settings
```

**Outputs:**

```text
run_logs\bracket_recalibration\latest.json
run_logs\bracket_recalibration\latest.html
run_logs\bracket_recalibration\latest.csv
run_logs\bracket_recalibration\best_trades.csv
```

**Important:** BUY is not deleted. Phase139A can test BUY and SELL together or side-specific bracket overrides.

Verification for Phase139A implementation:

```text
python -m ruff check scripts/backtest_bracket_recalibration.py tests/unit/ai/test_bracket_recalibration.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/backtest_bracket_recalibration.py tests/unit/ai/test_bracket_recalibration.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_bracket_recalibration.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1859 tests collected
```

Full quality gate remains red from pre-existing repository debt:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## 2026-09-15 — Phase139A global bracket recalibration result failed

**Operator result:** Phase139A global TP/SL/RR cap grid.

Configuration:

```text
allowed_sides      : BUY,SELL
max_tp_distances   : original,12,14,16,18
max_sl_distances   : original,20,23.56,30
max_reward_risks   : original,1,1.5,2
eval_frac          : 1.0
same_bar_policy    : stop_first
```

Best policy:

```text
policy            : tp=original:sl=original:rr=original
trades            : 1693
buy/sell          : 1118 / 575
wins/losses       : 512 / 1181
win_rate          : 30.2422%
total_pnl         : -4590.797210656048
profit_factor     : 0.5787103197097719
max_drawdown      : 4590.797210656047
final_balance     : -359.0797210656049
would_breach_zero : true
```

Assessment:

```text
FAIL. Every tested global TP/SL/RR cap policy was worse than the original bracket. Original is only least-bad, not acceptable. This suggests naive global bracket caps do not solve the system. Further TP/SL investigation should be side-specific, or else the project should return to candidate-generation and target-definition rework.
```

## 2026-09-15 — Phase139A side-specific bracket grids failed

**Operator result:** ran separate SELL-only and BUY-only Phase139A bracket recalibration grids.

SELL-only best policy:

```text
policy            : tp=14:sl=original:rr=original
trades            : 633
wins/losses       : 262 / 371
win_rate          : 41.3902%
total_pnl         : -664.0531247957406
profit_factor     : 0.7939690496760271
max_drawdown      : 846.2230220278584
final_balance     : 33.594687520425936
```

SELL comparison:

```text
original SELL-only : -848.8387 raw, PF=0.7291
best SELL policy   : -664.0531 raw, PF=0.7940
```

BUY-only best policy:

```text
policy            : tp=original:sl=16:rr=original
trades            : 1253
wins/losses       : 305 / 948
win_rate          : 24.3416%
total_pnl         : -3667.8429958516326
profit_factor     : 0.5476443218994678
max_drawdown      : 3668.8183342898155
final_balance     : -266.7842995851633
```

BUY comparison:

```text
original BUY-only : -3838.3925 raw, PF=0.5142
best BUY policy   : -3667.8430 raw, PF=0.5476
```

Assessment:

```text
Phase139A failed. SELL bracket caps reduce damage but remain far from profitable. BUY bracket caps do not rescue BUY; every reported BUY month remains negative. BUY is not removed from the project, but current BUY candidate generation/entry direction is not tradeable.
```

Next recommended phase:

```text
Phase140A — Candidate Direction / Counterfactual Entry Audit
```

## 2026-09-16 — Phase140A candidate direction / counterfactual entry audit implemented

**Operator instruction:** «باشه بریم فاز بعدی» after Phase139A global and side-specific TP/SL bracket grids failed.

**Implemented:**

```text
scripts/audit_candidate_direction_entry.py
GUI: Audit candidate direction/entry
```

**Purpose:**

```text
Determine whether the current hybrid candidate stream is failing because direction is inverted/contrarian, entry is too early, or the candidate generation itself has no stable edge.
```

**Audit matrix:**

```text
side_mode        : original, flipped
entry_delay_bars : 0,1,2,3
execution_mode   : independent, chronological
```

`independent` evaluates every candidate for direction quality.
`chronological` uses one-position-at-a-time replay for executable strategy impact.

**Outputs:**

```text
run_logs\candidate_direction_entry_audit\latest.json
run_logs\candidate_direction_entry_audit\latest.html
run_logs\candidate_direction_entry_audit\latest.csv
run_logs\candidate_direction_entry_audit\latest_groups.csv
run_logs\candidate_direction_entry_audit\best_chronological_trades.csv
```

**GUI / Clean Architecture note:**

```text
CommandKind.AUDIT_CANDIDATE_DIRECTION_ENTRY added.
Descriptor and handler added in presentation command layer.
Dashboard can run Phase140A; it is not CLI-only.
```

**Docs updated:**

```text
docs/Phases/Phase140.md
docs/Report/PHASE140A_CANDIDATE_DIRECTION_ENTRY_AUDIT_REPORT.md
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
docs/CURRENT_STATE.md
docs/PROJECT_OWNER_MAP.html
```

**First command for operator:**

```powershell
python -u scripts/audit_candidate_direction_entry.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --entry-delays 0,1,2,3 `
  --side-modes original,flipped `
  --execution-modes independent,chronological `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

**Verification:**

```text
python -m ruff check scripts/audit_candidate_direction_entry.py tests/unit/ai/test_candidate_direction_entry_audit.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/audit_candidate_direction_entry.py tests/unit/ai/test_candidate_direction_entry_audit.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_candidate_direction_entry_audit.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1867 tests collected
```

**Full quality gate honesty:**

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

**Production status:**

```text
No Phase134.
No paper shadow.
No live trading.
Phase140A is diagnostic only and awaits the operator's real XAUUSD latest.json result.
```

## 2026-09-16 — Phase140A direction/entry audit result recorded

**Operator result:** provided `run_logs\candidate_direction_entry_audit\latest.json` after running Phase140A.

Configuration:

```text
evaluated_rows  : 52,832
candidate_rows  : 13,757
side_modes      : original,flipped
entry_delays    : 0,1,2,3
execution_modes : independent,chronological
```

Top-level result:

```text
best_independent_scenario        : independent:flipped:delay=0
best_independent_total_pnl       : -37,742.8296
best_independent_profit_factor   : 0.6561

best_chronological_scenario      : chronological:original:delay=3
best_chronological_total_pnl     : -3,123.7836
best_chronological_profit_factor : 0.6512
```

Important comparisons:

```text
independent original delay=0    : -43,309.8113 PF=0.6215
independent flipped delay=0     : -37,742.8296 PF=0.6561
chronological original delay=0  : -4,590.7972  PF=0.5787
chronological original delay=3  : -3,123.7836  PF=0.6512
chronological flipped delay=0   : -4,113.8428  PF=0.6542
```

Side diagnosis:

```text
BUY original      : -39,003.7074 PF=0.5106
BUY flipped→SELL  : -15,831.0041 PF=0.7545
SELL original     : -4,306.1039  PF=0.8760
SELL flipped→BUY  : -21,911.8255 PF=0.5157
```

Assessment:

```text
Phase140A fails as a strategy. It does not permit production/paper/live.
```

Useful diagnosis:

```text
Global side flip is not the fix.
BUY candidates are partially contrarian/inverted, but flipped BUY is still negative.
SELL direction is not inverted; SELL→BUY is destructive.
Entry delay helps materially, especially delay=3, but still does not create edge.
```

Recommended next phase:

```text
Phase141A — Side-Transform / Delay Policy Grid
```

Purpose:

```text
Chronologically test combinations of BUY action original/flip/skip and SELL action original/flip/skip with side-specific delays 0/1/2/3.
```

## 2026-09-16 — Phase141A pivot/top-bottom pattern-recognition model implemented and executed

**Owner request:** build a Pattern Recognition model that can learn approximate top/bottom reversal zones and use 5M/4H/1D data to decide BUY/SELL/HOLD with TP/SL and walk-forward backtest.

**Implemented:**

```text
scripts/train_pivot_pattern_recognition.py
GUI: Train pivot pattern recognition
tests/unit/ai/test_pivot_pattern_recognition.py
```

**Dependency update:**

```text
requirements-boosters.txt now includes scikit-learn>=1.4
```

The script can use `sklearn_hgb` when sklearn exists and falls back to a dependency-free `CentroidPatternModel` otherwise.

**Target design:**

```text
SELL = top_zone reversal pattern
HOLD = no actionable pivot zone
BUY  = bottom_zone reversal pattern
```

Default pivot label settings:

```text
lookahead_bars     = 48
pivot_move_atr     = 0.75
pivot_zone_atr     = 0.35
recent_window_bars = 48
min_direction_edge = 1.10
```

**Feature families:**

```text
5M pattern features: returns, candle body/wicks/range, ATR distance, RSI, EMA distances, local-range position, distance from local high/low, volatility, z-score.
4H context: previous closed 4H returns, candle shape, ATR, EMA distances, RSI, room-up/down.
1D context: previous closed 1D returns, candle shape, ATR, EMA distances, RSI, room-up/down.
Session/time: hour and day-of-week cycles.
```

**Real execution:**

```text
source_mode    : yahoo
market_symbol  : GC=F
1D rows        : 1,258
4H rows        : 3,721
5M rows        : 13,509
model_kind     : sklearn_hgb
feature columns: 57
selected/fold  : 38
target counts  : SELL=1,368 / HOLD=10,764 / BUY=1,376
```

Walk-forward result:

```text
folds             : 6
trades            : 102
BUY / SELL trades : 40 / 62
wins / losses     : 45 / 57
win_rate          : 44.1176%
initial_balance   : $100.00
final_balance     : $86.7906
net_profit        : -$13.2094
return            : -13.2094%
profit_factor     : 0.6738
max_drawdown_cash : $15.0879
positive_folds    : 0
negative_folds    : 6
```

Fold test results:

```text
Fold 1: net=-2.6643 PF=0.5531 trades=11
Fold 2: net=-0.3089 PF=0.9124 trades=11
Fold 3: net=-3.1170 PF=0.5913 trades=12
Fold 4: net=-2.7775 PF=0.6993 trades=34
Fold 5: net=-4.1545 PF=0.1518 trades=12
Fold 6: net=-0.1872 PF=0.9797 trades=22
```

Top selected features were sensible for pattern recognition:

```text
m5_pos_in_range_48
m5_dist_high_48_atr
m5_dist_low_48_atr
m5_fast_mid_dist_atr
m5_price_z_96
m5_pos_in_range_24
m5_ret48
m5_close_mid_dist_atr
m5_ret24
m5_dist_high_24_atr
```

**Decision:**

```text
Phase141A implementation succeeded, but the first real public-data walk-forward failed as a trading strategy. $100 became $86.79. No production/paper/live permission.
```

**Artifacts:**

```text
run_logs\pivot_pattern_recognition\latest.json
run_logs\pivot_pattern_recognition\latest.html
run_logs\pivot_pattern_recognition\latest_folds.csv
run_logs\pivot_pattern_recognition\latest_trades.csv
run_logs\pivot_pattern_recognition\latest_features.csv

datasets\models\gold_pivot_pattern_recognition_5m\v1_model.pkl
datasets\models\gold_pivot_pattern_recognition_5m\v1_training.json
```

**Phase141A verification:**

```text
python -m ruff check scripts/train_pivot_pattern_recognition.py tests/unit/ai/test_pivot_pattern_recognition.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/train_pivot_pattern_recognition.py tests/unit/ai/test_pivot_pattern_recognition.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_recognition.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1874 tests collected
```

Full gate status remains red from known repository debt:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## 2026-09-16 — Operator rerun confirms Phase141A Yahoo/GC=F failure; files-mode path missing

**Operator rerun:** Phase141A was run from Windows with `source_mode=yahoo` and `yahoo_symbol=GC=F`.

Result:

```text
1D rows           : 1,258
4H rows           : 3,722
5M rows           : 13,555
features          : 57
selected features : 38
target counts     : SELL=1,385 / HOLD=10,782 / BUY=1,387
model_kind_used   : sklearn_hgb
folds             : 6
trades            : 92
BUY / SELL trades : 39 / 53
wins / losses     : 33 / 59
win_rate          : 35.8696%
initial_balance   : $100.00
final_balance     : $79.0053
net_profit        : -$20.9947
return            : -20.9947%
profit_factor     : 0.5344
max_drawdown_cash : $23.1522
positive_folds    : 0
negative_folds    : 6
```

Fold test results:

```text
Fold 1: net=-2.5993 PF=0.5655 trades=11
Fold 2: net=-0.0843 PF=0.9679 trades=10
Fold 3: net=-3.9539 PF=0.3038 trades=11
Fold 4: net=-9.1807 PF=0.4637 trades=30
Fold 5: net=-1.8003 PF=0.2853 trades=6
Fold 6: net=-3.3761 PF=0.6976 trades=24
```

Assessment:

```text
Confirmed failure. Phase141A remains research-only and is not tradeable.
```

**Files-mode attempt:** operator then ran the Alpari/XAUUSD files command and got:

```text
[X] RuntimeError: Input file does not exist: datasets\external\XAUUSD_1D.csv
```

Assessment:

```text
The script is not failing logically; the external files do not exist at the requested paths.
Next action is to export/copy XAUUSD_1D.csv, XAUUSD_1H.csv and XAUUSD_5M.csv into datasets\external, or adjust command paths to real filenames.
```

## 2026-09-16 — Phase141A storage-mode correction after owner objection

**Owner objection:** the project already has datasets; Phase141A should not require changing data location/type to `datasets\external` CSV files.

**Assessment:** correct. The earlier files-mode command was a poor default/UX for this project.

**Fix implemented:**

```text
scripts/train_pivot_pattern_recognition.py
--source-mode storage
```

Storage mode now reads the latest versioned parquet files from project storage:

```text
datasets\processed\<SYMBOL>\5M\v*.parquet
datasets\processed\<SYMBOL>\1D\v*.parquet
datasets\processed\<SYMBOL>\4H\v*.parquet if available
otherwise datasets\processed\<SYMBOL>\1H\v*.parquet -> resample to 4H
```

Supported project schema:

```text
open_time -> timestamp
```

GUI correction:

```text
Train pivot pattern recognition default source_mode changed from yahoo to storage.
```

**Verification:**

```text
python -m ruff check scripts/train_pivot_pattern_recognition.py tests/unit/ai/test_pivot_pattern_recognition.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/train_pivot_pattern_recognition.py tests/unit/ai/test_pivot_pattern_recognition.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_recognition.py tests/unit/presentation/test_architecture_knobs_gui.py::test_train_pivot_pattern_recognition_descriptor_exists tests/unit/presentation/test_architecture_knobs_gui.py::test_train_pivot_pattern_recognition_passes_gui_args tests/unit/presentation/test_architecture_knobs_gui.py::test_train_pivot_pattern_recognition_defaults_to_storage tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_handler tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_descriptor tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1876 tests collected
```

Known full-repository debt remains:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## 2026-09-16 — Phase142A/142B true 3D pivot TensorFlow/Keras WaveNet implemented

**Owner correction:** the model must be a true 3D tensor WaveNet/Keras model, not the previous flat sklearn Phase141A baseline.

**Shape clarification:**

```text
Stored tensor X shape       : [samples, 288, channels]
Keras runtime batch X shape : [batch, 288, channels]
```

**Implemented scripts:**

```text
scripts/build_pivot_pattern_tensor.py
scripts/train_pivot_pattern_wavenet.py
scripts/backtest_pivot_pattern_wavenet.py
scripts/run_pivot_pattern_wavenet_walk_forward.py
```

**GUI commands:**

```text
Build pivot pattern tensor
Train pivot WaveNet pattern model
Backtest pivot WaveNet pattern model
Run pivot WaveNet walk-forward
```

**Architecture:**

```text
Project storage XAUUSD datasets
→ Phase141 causal pivot features/labels
→ 3D tensor [samples, 288, channels]
→ Keras WaveNet/TCN multi-head model
→ saved .keras artifact
→ backtest replay
→ walk-forward validation
```

**WaveNet heads:**

```text
action softmax: SELL/HOLD/BUY
top sigmoid
bottom sigmoid
buy_r regression
sell_r regression
```

**Tests added:**

```text
tests/unit/ai/test_pivot_pattern_tensor.py
tests/unit/ai/test_pivot_wavenet_helpers.py
tests/unit/presentation/test_phase142_pivot_wavenet_gui.py
```

**Verification:**

```text
python -m ruff check scripts/build_pivot_pattern_tensor.py scripts/train_pivot_pattern_wavenet.py scripts/backtest_pivot_pattern_wavenet.py scripts/run_pivot_pattern_wavenet_walk_forward.py tests/unit/ai/test_pivot_pattern_tensor.py tests/unit/ai/test_pivot_wavenet_helpers.py tests/unit/presentation/test_phase142_pivot_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m black --check scripts/build_pivot_pattern_tensor.py scripts/train_pivot_pattern_wavenet.py scripts/backtest_pivot_pattern_wavenet.py scripts/run_pivot_pattern_wavenet_walk_forward.py tests/unit/ai/test_pivot_pattern_tensor.py tests/unit/ai/test_pivot_wavenet_helpers.py tests/unit/presentation/test_phase142_pivot_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_tensor.py tests/unit/ai/test_pivot_wavenet_helpers.py tests/unit/presentation/test_phase142_pivot_wavenet_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_handler tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_descriptor tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered -q
→ passed
```

**Execution note:** full real XAUUSD WaveNet training was not executed in this sandbox because the complete project-storage XAUUSD 5M/1H data and TensorFlow runtime are on the operator machine. The operator should run the Phase142 command chain.

**Production status:**

```text
No Phase134.
No paper shadow.
No live trading.
```

**Full gate after Phase142A/B:**

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1890 tests collected
```

Known full-repository debt remains:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## 2026-09-16 — Phase143A 4D Pivot Image Tensor + Conv2D/Conv3D implemented

**Owner correction:** intended dataset is 4D for Conv2D/Conv3D:

```text
[samples, WindowSize, Features_5M, Features_4H_1D]
```

**Implemented:**

```text
scripts/build_pivot_pattern_image_tensor.py
scripts/train_pivot_pattern_image_cnn.py
GUI: Build pivot image tensor
GUI: Train pivot image CNN
```

**Shape semantics:**

```text
Stored X      : [samples, WindowSize, Features_5M, Features_4H_1D]
Conv2D batch  : [batch, WindowSize, Features_5M, Features_4H_1D]
Conv3D batch  : [batch, WindowSize, Features_5M, Features_4H_1D, 1]
```

**Cell semantics:**

```text
X[t, f5, htf] = feature_5M[t, f5] * feature_4H_1D[t, htf]
```

Bias terms preserve pure 5M and pure HTF features.

**Smoke:**

```text
TESTSYM X shape     : [160, 20, 5, 4]
Conv2D batch shape  : [batch, 20, 5, 4]
Conv3D batch shape  : [batch, 20, 5, 4, 1]
```

**Verification:**

```text
Phase143 targeted ruff/black/tests
→ passed
```

**Full gate after Phase143A:**

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1898 tests collected
```

Known full-repository debt remains:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## 2026-09-17 — Phase143A feature-axis defaults increased after owner feedback

**Owner feedback:** `13 × 9` feature axes are too small for the intended Conv2D/Conv3D Pattern Recognition model.

**Fix:** increased defaults in `scripts/build_pivot_pattern_image_tensor.py` and GUI:

```text
max_5m_features  : 12 -> 24
max_htf_features : 8  -> 16
max_tensor_mb    : 4096 -> 8192
```

Effective axis sizes after bias:

```text
5M axis  : 25
HTF axis : 17
```

Estimated full XAUUSD tensor:

```text
[53,099, 100, 25, 17] float16 ≈ 4.3 GB
```

**Feature-axis correction verification:**

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1898 tests collected

Full ruff/black/mypy
→ still red from known pre-existing debt: 219 ruff, 21 black files, 28 mypy errors
```

## 2026-09-17 — Phase143A Conv2D sanity training result recorded

**Operator result:** trained Phase143A Conv2D image CNN on 12,000 samples.

Configuration:

```text
X shape         : [12,000, 100, 32, 23]
keras batch     : [batch, 100, 32, 23]
train/val/test  : 8,400 / 1,464 / 1,464
epochs          : 10
model_kind      : conv2d
```

Metrics:

```text
val_action_accuracy  : 0.1441
test_action_accuracy : 0.3743
val_top_ap           : 0.1158
test_top_ap          : 0.1217
val_bottom_ap        : 0.0777
test_bottom_ap       : 0.1012
val_selected_rate    : 0.0000
test_selected_rate   : 0.0000
```

Assessment:

```text
Training executed successfully, but the model is not actionable. selected_rate=0 means the current threshold gate opens no trades. This is a failed sanity model, not a strategy.
```

Next recommended diagnostic:

```text
Run lower-threshold/probability-spread diagnostics before full 120-epoch training.
```

## 2026-09-17 — Phase143A overflow/NaN scaler and architecture artifact fix

**Operator finding:** `v1_training.json` had `Infinity` in `scaler_mean` and `NaN` in `scaler_std`. The saved model architecture was also not separately visible.

**Root cause:** raw feature interaction products were cast to `float16` before normalization. Some 5M × HTF products exceeded float16 range and became Infinity. The trainer then computed scaler statistics on poisoned input.

**Decision:** reject `gold_pivot_pattern_image_cnn_5m v1`. It is not a valid model artifact.

**Fix:**

```text
scripts/build_pivot_pattern_image_tensor.py
  added --axis-normalization robust|standard|none
  added --feature-clip
  added --interaction-clip
  sanitizes NaN/Inf before interaction
  clips before float16 cast
  records nonfinite_feature_values and nonfinite_interaction_values

scripts/train_pivot_pattern_image_cnn.py
  sanitizes nonfinite tensor values before scaler fitting
  forces scaler_mean/scaler_std finite
  saves architecture JSON and model summary TXT
```

**New architecture artifact paths:**

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_architecture.json
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_summary.txt
run_logs\pivot_pattern_image_cnn\latest_architecture.json
run_logs\pivot_pattern_image_cnn\latest_summary.txt
```

**Sanitization/architecture fix verification:**

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1899 tests collected

Full ruff/black/mypy
→ still red from known pre-existing debt: 219 ruff, 21 black files, 28 mypy errors
```

## 2026-09-17 — Phase143A official tensor-health audit added

**Owner request:** add the dataset-health check as project code.

**Implemented:**

```text
scripts/audit_pivot_pattern_image_tensor.py
GUI: Audit pivot image tensor health
```

**Checks:**

```text
4D tensor rank/shape
metadata alignment
sample index monotonicity
timestamp monotonicity
target finite checks
axis scaler finite checks
full tensor finite scan
max_abs vs interaction_clip
builder nonfinite diagnostics
```

**Operator note:** the dataset health test was run and reported healthy.

**Next:** train a new sanitized Conv2D model version; v1 remains rejected due to Infinity/NaN scaler values.

## 2026-09-17 — Phase143A image CNN epoch checkpointing added

**Operator issue:** one epoch completed but no model directory/model file appeared.

**Root cause:** final model save happened only after all epochs/early-stopping completed.

**Fix:** added epoch checkpointing to `scripts/train_pivot_pattern_image_cnn.py`:

```text
--checkpoint-each-epoch 1
```

Now the trainer creates these before/during training:

```text
vN_architecture.json
vN_summary.txt
vN_epoch_checkpoint.keras
latest_training_log.csv
```

Final successful completion still creates:

```text
vN_model.keras
vN_training.json
```

GUI `Train pivot image CNN` now passes `--checkpoint-each-epoch`.

**Epoch-checkpoint verification:**

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1904 tests collected

Full ruff/black/mypy
→ still red from known pre-existing debt: 219 ruff, 21 black files, 28 mypy errors
```

## 2026-09-17 — Phase144A advanced 4D Pivot Image WaveNet implemented

**Owner request:** do not use simple Conv2D baseline; implement professional architecture with residual, SE/attention, temporal dilations, separate branches, temporal attention, multi-scale kernels, and tanh activation.

**Implemented:**

```text
scripts/train_pivot_pattern_image_wavenet.py
GUI: Train advanced pivot image WaveNet
```

**Architecture components:**

```text
separate pure 5M branch
separate pure HTF branch
TimeDistributed spatial multi-scale Conv2D interaction branch
gated tanh-sigmoid dilated temporal Conv1D WaveNet blocks
residual connections
skip connections
squeeze-excitation channel attention
temporal MultiHeadAttention
multi-head outputs
```

**Activation decision:** implemented WaveNet-style `tanh(filter) * sigmoid(gate)`, with configurable `--activation tanh|swish|gelu` and default `tanh`.

**Verification:** targeted ruff/black/tests passed.

**Phase144A verification:**

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1908 tests collected

Full ruff/black/mypy
→ still red from known pre-existing debt: 219 ruff, 21 black files, 28 mypy errors
```

## 2026-09-17 — RAM-safe stream loader added for 4D image trainers

**Operator issue:** training used about 27GB RAM on a 32GB machine.

**Root cause:** trainer loaded the selected 4D tensor into RAM and then created a normalized copy.

**Fix:** added streaming loader:

```text
--loader-mode stream
--stream-chunk-size 256
```

Affected scripts:

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
```

This keeps model and dataset size unchanged while reducing RAM pressure by reading/normalizing batches on demand from the `.npy` memmap.

## 2026-09-17 — Stream loader verification completed

**Implemented:** stream-mode training for both 4D image trainers:

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
```

**Default:**

```text
--loader-mode stream
--stream-chunk-size 256
```

**Verification:**

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1909 tests collected
```

Known full-repository debt remains unchanged:

```text
ruff=219 old errors
black=21 old files
mypy=28 old errors
```

## 2026-09-17 — batch-level training logger added for long 4D training

**Operator request:** show batch output during training because waiting for an epoch is too long.

**Implemented:**

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
--batch-log-every N
--batch-log-file PATH
```

Default logs:

```text
run_logs\pivot_pattern_image_cnn\latest_batch_log.jsonl
run_logs\pivot_pattern_image_wavenet\latest_batch_log.jsonl
```

Set `--batch-log-every 1` to print and store every batch. Larger values reduce console/log noise.

**Verification:**

```text
Targeted ruff/black/tests → passed
python -m pytest -q → passed
python -m pytest --collect-only → 1909 tests collected
```

Known full-repository debt remains:

```text
ruff=219 old errors
black=21 old files
mypy=28 old errors
```

## 2026-09-17 — Phase145A Pivot Sequence Tensor + Advanced Conv1D WaveNet implemented

**Owner request:** build Option A: reduce tensor dimensionality to `[samples, WindowSize, Features]`, concatenate 5M/4H/1D features on the feature axis, keep the same pivot targets, and build the model architecture like the advanced 4D model but adapted to Conv1D/WaveNet.

**Implemented:**

```text
scripts/build_pivot_pattern_sequence_tensor.py
scripts/train_pivot_pattern_sequence_wavenet.py
GUI: Build pivot sequence tensor
GUI: Train pivot sequence WaveNet
```

**Tensor layout:**

```text
Stored X    : [samples, WindowSize, Features]
Keras batch : [batch, WindowSize, Features]
```

**Feature handling:**

```text
generated 5M features
closed 4H context
closed 1D context
session/time
source 5M numeric columns from project parquet with prefix src5m_
```

**Architecture:**

```text
separate 5M branch
separate HTF branch
all-feature branch
multi-scale causal Conv1D
gated tanh-sigmoid dilated WaveNet
residual/skip connections
SE channel attention
temporal self-attention
multi-head outputs
stream loader
batch-level logs
epoch checkpoints
```

**Smoke:**

```text
TESTSYM X shape     : [160, 20, 57]
TESTSYM Keras batch : [batch, 20, 57]
```

**Verification:** targeted ruff/black/tests passed.

**Phase145A full gate:**

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1919 tests collected

Full ruff/black/mypy
→ still red from known pre-existing debt: 219 ruff, 21 black files, 28 mypy errors
```

## Phase144A operator result — advanced 4D Image WaveNet v1 — 2026-09-19

The owner supplied `run_logs\pivot_pattern_image_wavenet\latest.json` for the first full operator-machine run of the advanced 4D Image WaveNet.

Run configuration summary:

```text
model_id          : gold_pivot_pattern_image_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
stored_x_shape    : [12000, 100, 32, 23]
keras_batch_shape : [batch, 100, 32, 23]
loader_mode       : stream
batch_size        : 8
epochs requested  : 20
learning_rate     : 0.0005
nonfinite_input_values : 0
```

Validation metrics:

```text
val_action_accuracy : 0.5628415301
val_top_ap          : 0.2038051024
val_bottom_ap       : 0.1501470022
val_buy_r_mae       : 0.6300964952
val_sell_r_mae      : 0.6807333231
val_selected_rate   : 0.4187158470
```

Test metrics:

```text
test_action_accuracy : 0.5969945355
test_top_ap          : 0.2327647696
test_bottom_ap       : 0.2356605000
test_buy_r_mae       : 0.6400972009
test_sell_r_mae      : 0.6506559253
test_selected_rate   : 0.4009562842
```

Interpretation:

```text
GOOD:
- The sanitized/streamed 4D pipeline is numerically healthy: nonfinite_input_values=0.
- The advanced WaveNet is not a dead/no-trade model: selected_rate is ~41.87% validation and ~40.10% test.
- Action/top/bottom heads materially improved versus the rejected simple Conv2D sanity run.

LIMITS:
- This is still a research classifier/pattern model, not a trading system.
- No PnL, spread/slippage, TP/SL, max-hold, or walk-forward trading validation is present in this report.
- The gate is intentionally loose: buy_threshold=0.34, sell_threshold=0.34, min_margin=0, min_buy_r=-999, min_sell_r=-999.
- R-head MAE did not materially improve; buy_r/sell_r heads are not yet reliable as trading filters.
- The run uses max_samples=12000, not the full tensor.
```

Decision:

```text
Phase144A v1 is a useful research improvement over the simple Conv2D baseline, but production remains BLOCKED.
Next required evidence is backtest/walk-forward or comparison against Phase145A Option A sequence WaveNet.
No Phase134. No paper shadow. No live trading.
```

## Phase145A operator result — Option A sequence WaveNet v1 — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet\latest.json` for the first operator-machine run of Phase145A Option A.

Run configuration summary:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [24000, 100, 57]
keras_batch_shape : [batch, 100, 57]
feature_count     : 57
m5_feature_count  : 35
htf_feature_count : 22
other_feature_count : 0
loader_mode       : stream
batch_size        : 16
epochs requested  : 80
learning_rate     : 0.0005
nonfinite_input_values : 0
```

Validation metrics:

```text
val_action_accuracy : 0.4604779412
val_top_ap          : 0.2414809241
val_bottom_ap       : 0.1344216114
val_buy_r_mae       : 0.6942731142
val_sell_r_mae      : 0.6847920418
val_selected_rate   : 0.5836397059
```

Test metrics:

```text
test_action_accuracy : 0.4791666667
test_top_ap          : 0.2453369099
test_bottom_ap       : 0.1816515898
test_buy_r_mae       : 0.6652074456
test_sell_r_mae      : 0.6756162643
test_selected_rate   : 0.5719975490
```

Comparison against Phase144A 4D Image WaveNet v1 supplied earlier:

```text
Action accuracy:
  4D Image WaveNet      : val=0.5628, test=0.5970
  Option A Sequence     : val=0.4605, test=0.4792
  Current read          : 4D is stronger on action classification.

Top AP:
  4D Image WaveNet      : val=0.2038, test=0.2328
  Option A Sequence     : val=0.2415, test=0.2453
  Current read          : Option A is slightly stronger on top-zone ranking.

Bottom AP:
  4D Image WaveNet      : val=0.1501, test=0.2357
  Option A Sequence     : val=0.1344, test=0.1817
  Current read          : 4D is stronger on bottom-zone ranking.

Selected rate:
  4D Image WaveNet      : val=0.4187, test=0.4010
  Option A Sequence     : val=0.5836, test=0.5720
  Current read          : Option A is much more aggressive and may over-select.
```

Interpretation:

```text
GOOD:
- Numerically healthy: nonfinite_input_values=0.
- Option A built the intended WaveNet-native tensor: [samples, WindowSize, Features].
- Memory pressure is lower than the 4D interaction tensor.
- Top-zone ranking is slightly better than 4D in this run.

LIMITS:
- Action accuracy is materially lower than the Phase144A 4D Image WaveNet result.
- Bottom-zone AP is lower than 4D.
- selected_rate around 57% is high under the loose diagnostic gate.
- buy_r/sell_r MAE did not improve; R-heads are not yet reliable trading gates.
- The report has no PnL, profit factor, drawdown, spread/slippage, or walk-forward trading validation.
- This is not an apples-to-apples comparison because Phase144A used 12000 samples while Phase145A used 24000 samples and a different feature layout/capacity.
- Feature count is 57. If the owner expected the large historical 5M feature set, the Phase145A tensor build report must be checked for `source_5m_feature_count`.
```

Decision:

```text
Phase145A Option A v1 is technically healthy but not better overall than Phase144A 4D v1 on classifier metrics.
It remains useful as a lower-dimensional research lane, especially for top-zone ranking and RAM efficiency.
Production remains BLOCKED until backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Phase145A source-feature discovery fix — 2026-09-19

The owner supplied the Phase145A sequence tensor build report. It confirmed:

```text
features                  : 57
generated_feature_count   : 57
source_5m_feature_count   : 0
source_5m_feature_path    : not previously reported
```

Interpretation:

```text
The first Option A tensor was technically valid, but it did not include the larger historical 5M feature set.
It was therefore an Option A generated-feature run, not the intended full-source-feature Option A run.
```

Root cause fixed in the builder:

```text
scripts/build_pivot_pattern_sequence_tensor.py
```

New behavior:

```text
--include-source-5m-features 1
```

now auto-probes, in storage mode, before falling back to the plain OHLCV `v*.parquet` file:

```text
datasets\processed\<SYMBOL>\<TF>\hybrid_telemetry_flat_latest.parquet
datasets\processed\<SYMBOL>\<TF>\hybrid_xgboost_matrix_latest.parquet
datasets\processed\<SYMBOL>\<TF>\hybrid_xgboost_matrix_all_5m.parquet
hybrid_*flat*.parquet
hybrid_*matrix*.parquet
plain storage OHLCV v*.parquet
```

Added explicit override:

```text
--source-5m-feature-path PATH
```

GUI update:

```text
Build pivot sequence tensor → Optional source 5M feature parquet/csv
```

Leakage/metadata safeguards:

```text
Blocked source columns include OHLCV identifiers, source_index/tensor_index/sample_index/row_id, target_*, future_*, candidate_*, prediction_*, pred_*, prob_*.
```

The build report now records:

```text
source_5m_feature_path
source_5m_total_columns
source_5m_numeric_candidate_count
source_5m_feature_count
```

Required rerun:

```powershell
python -u scripts\build_pivot_pattern_sequence_tensor.py `
  --source-mode storage `
  --symbol XAUUSD `
  --five-timeframe 5M `
  --hourly-timeframe 1H `
  --h4-timeframe 4H `
  --daily-timeframe 1D `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --window-size 100 `
  --sample-stride 1 `
  --max-samples 0 `
  --include-source-5m-features 1 `
  --max-features 0 `
  --dtype float16 `
  --axis-normalization robust `
  --feature-clip 8 `
  --chunk-size 512 `
  --max-tensor-mb 8192 `
  --output-name pivot_pattern_sequence_tensor_latest `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_tensor
```

If `source_5m_feature_count` remains `0`, then the large 5M feature file is not in the auto-probed project-storage locations and the operator must provide its exact path through the new GUI field or `--source-5m-feature-path`.

Decision:

```text
The previous Phase145A v1 model result should be treated as underfed / generated-feature-only.
Do not compare it as the final full-feature Option A result until the tensor is rebuilt with source_5m_feature_count > 0.
Production remains BLOCKED.
```

Verification in sandbox:

```text
python -m py_compile scripts/build_pivot_pattern_sequence_tensor.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 41 passed

python -m pytest -q
→ blocked in sandbox collection because optional dependencies pyarrow/pywt are not installed here.

python -m ruff / python -m black
→ unavailable in this sandbox image.
```

## Phase145A PowerShell empty optional path fix — 2026-09-19

The owner ran the new Phase145A tensor build command in PowerShell with:

```text
--source-5m-feature-path "" `
```

PowerShell/native argv handling dropped the empty string, so `argparse` saw `--source-5m-feature-path` without a value and failed:

```text
build_pivot_pattern_sequence_tensor.py: error: argument --source-5m-feature-path: expected one argument
```

Fix implemented:

```text
scripts/build_pivot_pattern_sequence_tensor.py
```

The argument now uses:

```text
nargs="?"
const=""
default=""
```

So both forms are safe:

```powershell
# recommended: omit the optional path for auto-probe
--include-source-5m-features 1

# also accepted now if a shell drops the empty value
--source-5m-feature-path
```

Documentation command snippets were updated to omit `--source-5m-feature-path ""` unless an explicit path is actually needed.

Recommended rerun is the same tensor build command, but without the empty path line. If auto-probe still reports `source_5m_feature_count=0`, rerun with an actual feature parquet/csv path.

## Phase143A 4D image tensor health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_image_tensor_health\latest.json` after running the official tensor health audit for the rebuilt 4D pivot image tensor.

Audit command inputs:

```text
tensor_path    : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
meta_path      : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
flat_path      : datasets\processed\XAUUSD\5M\pivot_pattern_image_flat_latest.parquet
builder_report : run_logs\pivot_pattern_image_tensor\latest.json
full_scan      : 1
chunk_size     : 256
```

Result:

```text
status       : PASS
tensor_shape : [53098, 100, 32, 23]
dtype        : float16
flat_rows    : 53197
sample index : min=99 max=53196 step=1
first time   : 2025-11-28 17:05:00+00:00
last time    : 2026-09-02 10:25:00+00:00
```

Full tensor scan:

```text
scanned_cells     : 3,908,012,800
chunks            : 208
nonfinite_cells   : 0
min_value         : -32.0
max_value         : 32.0
max_abs           : 32.0
interaction_clip  : 32.0
warnings          : []
errors            : []
```

Target counts on sampled windows:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Interpretation:

```text
- The 4D image tensor is structurally healthy.
- The full tensor scan found no NaN/Inf cells.
- max_abs equals interaction_clip, so clipping is active and within the configured bound.
- sample_indices are strictly contiguous with stride=1 from 99 to 53196.
- feature_5m_names length matches axis 2: 32.
- feature_htf_names length matches axis 3: 23.
```

Note on target-count difference versus builder report:

```text
Builder target_counts were computed on the flat frame after target availability.
Health-audit target_counts are computed on the sampled tensor windows.
Because window_size=100, the first 99 flat rows are not tensor samples, so small count differences are expected and not an error.
```

Decision:

```text
Phase143A rebuilt 4D pivot image tensor is accepted as healthy for research training.
It is safe to train Phase144A advanced 4D Image WaveNet on this tensor.
Production remains BLOCKED until model backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Phase145A full-source sequence tensor build + health audit command — 2026-09-19

The owner rebuilt the Option A sequence tensor after the source-feature discovery fix. The new build report confirms the intended 3D tensor layout:

```text
stored_x_shape      : [53098, 100, 140]
keras_batch_shape   : [batch, 100, 140]
dtype               : float16
estimated_size_mb   : 1417.8696
samples             : 53098
window_size         : 100
features            : 140
generated_features  : 57
source_5m_features  : 83
source_5m_path      : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
source_total_cols   : 105
source_numeric_candidates : 83
nonfinite_feature_values  : 0
```

Target counts on the flat target-available frame:

```text
SELL : 5,392
HOLD : 43,342
BUY  : 4,463
```

Interpretation:

```text
- This is the intended Option A tensor: [X, Y, Z] = [samples, WindowSize, Features].
- Source 5M features are now included: source_5m_feature_count=83.
- Total feature count is 140 = 57 generated/context features + 83 source 5M features.
- The tensor is much smaller than the 4D interaction tensor: about 1.42 GB float16 versus about 7.45 GB for [53098,100,32,23].
```

Implemented official health audit for the Option A tensor:

```text
scripts/audit_pivot_pattern_sequence_tensor.py
GUI: Audit pivot sequence tensor health
```

The audit checks:

```text
3D rank/shape: [samples, window, features]
metadata/sample alignment
sample_indices monotonicity
timestamp monotonicity
target array presence/length/finite values
feature_names and feature_groups alignment
source_5m feature count consistency
feature scaler finite checks
full tensor NaN/Inf scan
max_abs <= feature_clip
builder report shape/count consistency
```

Command to run on the operator machine:

```powershell
python -u scripts\audit_pivot_pattern_sequence_tensor.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --builder-report run_logs\pivot_pattern_sequence_tensor\latest.json `
  --chunk-size 512 `
  --full-scan 1 `
  --max-scan-samples 0 `
  --fail-on-reported-feature-nonfinite 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_tensor_health
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_tensor_health\latest.json
run_logs\pivot_pattern_sequence_tensor_health\latest.html
```

Verification in sandbox:

```text
python -m py_compile scripts/audit_pivot_pattern_sequence_tensor.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 45 passed
```

Decision:

```text
The full-source Option A sequence tensor build is structurally correct from the builder report.
Run the new health audit before retraining gold_pivot_pattern_sequence_wavenet_5m.
Previous Sequence WaveNet v1 trained on [24000,100,57] remains underfed and should not be treated as final Option A.
Production remains BLOCKED.
No Phase134. No paper shadow. No live trading.
```

## Phase145A full-source sequence tensor health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_tensor_health\latest.json` after running the official Phase145A Option A sequence tensor health audit.

Audit command inputs:

```text
tensor_path    : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta_path      : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
flat_path      : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
builder_report : run_logs\pivot_pattern_sequence_tensor\latest.json
full_scan      : 1
chunk_size     : 512
```

Result:

```text
status            : PASS
tensor_shape      : [53098, 100, 140]
keras_batch_shape : [batch, 100, 140]
dtype             : float16
samples           : 53098
window_size       : 100
features          : 140
flat_rows         : 53197
sample index      : min=99 max=53196 step=1
first time        : 2025-11-28 17:05:00+00:00
last time         : 2026-09-02 10:25:00+00:00
```

Feature composition:

```text
generated_5m_feature_count : 31
source_5m_feature_count    : 83
session_feature_count      : 4
htf_feature_count          : 22
other_feature_count        : 0
source_5m_feature_path     : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
source_5m_numeric_candidates : 83
```

Full tensor scan:

```text
scanned_cells   : 743,372,000
chunks          : 104
nonfinite_cells : 0
min_value       : -8.0
max_value       : 8.0
max_abs         : 8.0
feature_clip    : 8.0
warnings        : []
errors          : []
```

Target counts on sampled tensor windows:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Interpretation:

```text
- This is the intended Option A tensor layout: [X, Y, Z] = [samples, WindowSize, Features].
- The full-source tensor is healthy: rank=3, shape=[53098,100,140], source_5m=83, no NaN/Inf cells.
- max_abs equals feature_clip, so robust normalization/clipping is active and within configured bounds.
- sample_indices are contiguous with stride=1 from 99 to 53196.
- The previous Sequence WaveNet v1 trained on [24000,100,57] is underfed and should not be treated as the final Option A result.
```

Decision:

```text
Phase145A full-source sequence tensor is accepted as healthy for research training.
Next valid training should use this tensor [samples,100,140], not the old [samples,100,57] tensor.
Production remains BLOCKED until backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Gitignore heavy artifact guard — 2026-09-19

The owner asked to prevent heavy local research artifacts from entering git. `.gitignore` was updated and the malformed `config.inirun_logs/` line was corrected to `config.ini`.

New/confirmed ignore coverage includes:

```text
*.npy
*.keras
*.ckpt
*.weights.h5
*.pkl / *.pickle / *.joblib
*.onnx / *.pb / *.tflite
*.feather / *.arrow / *.orc / *.avro / *.zarr/
*.zip / *.7z / *.rar / *.tar / *.tar.gz / *.tgz / *.xz
datasets/raw/
datasets/external/
datasets/processed/
datasets/models/
run_logs/
logs/
```

Verification examples:

```text
datasets/processed/XAUUSD/5M/pivot_pattern_sequence_tensor_latest.npy → ignored
datasets/models/gold_pivot_pattern_sequence_wavenet_5m/v1_model.keras → ignored
run_logs/pivot_pattern_sequence_wavenet/latest.json → ignored
*.zip project snapshots → ignored
```

Note:

```text
Already-tracked small legacy artifacts are not automatically removed by .gitignore.
New heavy tensors/models/run logs will stay out of git.
```

## Phase145A full-source sequence WaveNet training result — 2026-09-19

The owner supplied the completed `run_logs\pivot_pattern_sequence_wavenet\latest.json`, model summary, and batch/epoch logs for the first full-source Option A training run.

Training input:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [24000, 100, 140]
keras_batch_shape : [batch, 100, 140]
feature_count     : 140
m5_feature_count  : 118
htf_feature_count : 22
other_feature_count : 0
loader_mode       : stream
batch_size        : 16
epochs requested  : 80
early_stopping_patience : 8
nonfinite_input_values  : 0
```

Final report metrics, after Keras restored the best `val_loss` weights:

```text
val_action_accuracy : 0.7239583333
val_top_ap          : 0.3654971900
val_bottom_ap       : 0.3324869559
val_buy_r_mae       : 0.6672694683
val_sell_r_mae      : 0.6664603949
val_selected_rate   : 0.2821691176

test_action_accuracy : 0.6200980392
test_top_ap          : 0.2709324875
test_bottom_ap       : 0.3336111266
test_buy_r_mae       : 0.7359182239
test_sell_r_mae      : 0.7348573208
test_selected_rate   : 0.3609068627
```

Important epoch-end observations from `latest_batch_log.jsonl`:

```text
epoch 1 : val_loss=1.9548627, val_action_acc=0.4316789
epoch 2 : val_loss=1.6995431, val_action_acc=0.5508578
epoch 3 : val_loss=1.8116363, val_action_acc=0.5713848
epoch 4 : val_loss=1.6853775, val_action_acc=0.6583946
epoch 5 : val_loss=1.4642649, val_action_acc=0.7239583  ← best val_loss / restored final weights
epoch 6 : val_loss=1.5603150, val_action_acc=0.7110907
epoch 7 : val_loss=1.8318611, val_action_acc=0.6522672
epoch 8 : val_loss=2.0280118, val_action_acc=0.6197917
epoch 9 : val_loss=1.9110000, val_action_acc=0.6666667
epoch 10: val_loss=1.8384161, val_action_acc=0.6727941
epoch 11: val_loss=1.8083678, val_action_acc=0.7086397
epoch 12: val_loss=1.7787350, val_action_acc=0.7037377
epoch 13: val_loss=1.6534641, val_action_acc=0.7414216
```

Architecture confirmation from the model summary:

```text
Input                  : [batch, 100, 140]
5M branch              : [batch, 100, 118]
HTF branch             : [batch, 100, 22]
All-feature branch     : [batch, 100, 140]
Branch fusion          : [batch, 100, 432]
WaveNet temporal core  : 2 residual blocks × dilations 1,2,4,8,16,32
Attention              : temporal_self_attention
Pooling                : avg + max + last
Heads                  : action/top/bottom/buy_r/sell_r
Trainable params       : 1,256,435
Total params reported  : 3,769,307 including optimizer slots
```

Comparison to the underfed Sequence WaveNet v1 `[24000,100,57]`:

```text
Action accuracy:
  underfed sequence : val=0.4605, test=0.4792
  full-source seq   : val=0.7240, test=0.6201

Top AP:
  underfed sequence : val=0.2415, test=0.2453
  full-source seq   : val=0.3655, test=0.2709

Bottom AP:
  underfed sequence : val=0.1344, test=0.1817
  full-source seq   : val=0.3325, test=0.3336

Selected rate:
  underfed sequence : val=0.5836, test=0.5720
  full-source seq   : val=0.2822, test=0.3609
```

Comparison to Phase144A 4D Image WaveNet v1 `[12000,100,32,23]`:

```text
Action accuracy:
  4D image WaveNet  : val=0.5628, test=0.5970
  full-source seq   : val=0.7240, test=0.6201

Top AP:
  4D image WaveNet  : val=0.2038, test=0.2328
  full-source seq   : val=0.3655, test=0.2709

Bottom AP:
  4D image WaveNet  : val=0.1501, test=0.2357
  full-source seq   : val=0.3325, test=0.3336
```

Interpretation:

```text
GOOD:
- Full-source Option A is a material improvement over the underfed 57-feature sequence run.
- It also beats the earlier 4D Image WaveNet classification/AP metrics in this non-identical comparison.
- selected_rate is lower and more controlled than the underfed run.
- No NaN/Inf was reported.
- The architecture is the intended advanced Conv1D/WaveNet adaptation of the 4D model.

LIMITS:
- Training loss kept improving while validation loss bottomed at epoch 5; overfitting after epoch 5 is visible.
- R-head test MAE is still weak: buy_r≈0.736, sell_r≈0.735.
- This is still a classifier/pattern report, not a trading proof.
- No PnL, profit factor, drawdown, spread/slippage, or walk-forward trading validation is present.
- 4D and sequence runs used different sample counts and layouts, so comparison is directional, not final proof.
```

Decision:

```text
Phase145A full-source sequence WaveNet is the strongest pivot-pattern research model so far by classification/AP diagnostics.
It is NOT production-approved.
Next required phase: backtest/PnL audit on sequence WaveNet predictions, followed by walk-forward if backtest is promising.
No Phase134. No paper shadow. No live trading.
```

## Phase146A sequence WaveNet PnL audit implemented — 2026-09-19

Implemented the first research-only PnL audit/backtest for the Phase145A full-source sequence WaveNet.

Implemented files:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
docs/Phases/Phase146.md
docs/Report/PHASE146A_SEQUENCE_WAVENET_BACKTEST_REPORT.md
tests/unit/ai/test_pivot_sequence_wavenet_backtest.py
```

GUI command:

```text
Backtest pivot sequence WaveNet PnL
```

Purpose:

```text
Convert action/top/bottom/buy_r/sell_r predictions into BUY/SELL candidates and run a research-only ATR TP/SL replay with spread, same-bar policy, max-hold, initial capital, and risk-per-trade.
```

Recommended first audit command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_backtest `
  --report-title "Phase146A sequence WaveNet PnL audit"
```

Outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_backtest\latest.json
run_logs\pivot_pattern_sequence_wavenet_backtest\latest.html
run_logs\pivot_pattern_sequence_wavenet_backtest\latest_trades.csv
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 49 passed
```

Production remains blocked until PnL/walk-forward prove edge.

## Phase146A Lambda deserialization fix — 2026-09-19

The owner's first Phase146A run failed while loading the trained Keras model:

```text
ValueError: Requested the deserialization of a `Lambda` layer whose `function` is a Python lambda.
Keras disallowed it by default; use safe_mode=False or enable unsafe deserialization.
```

Root cause:

```text
The Phase145A sequence WaveNet architecture intentionally uses Keras Lambda layers for feature slicing:
- gather_5m_features
- gather_htf_features
- gather_all_features
- last_temporal_state
```

Fix implemented in:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
```

The Phase146A loader now explicitly trusts local project-generated research artifacts:

```python
tf.keras.models.load_model(model_path, safe_mode=False)
```

with a fallback for older tf.keras versions:

```python
tf.keras.config.enable_unsafe_deserialization()
tf.keras.models.load_model(model_path)
```

Scope:

```text
Research-only local artifacts generated by this project.
Do not use this loader for untrusted downloaded Keras models.
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 50 passed
```

The same Phase146A PowerShell command can be rerun after replacing the project with the fixed zip.

## Phase146A Lambda shape-load fallback — 2026-09-19

The owner reran Phase146A after `safe_mode=False`. Keras then passed Lambda security but failed shape inference while deserializing the project-owned Lambda layers:

```text
NotImplementedError: We could not automatically infer the shape of the Lambda's output.
Please specify the output_shape argument for this Lambda layer.
```

Fix implemented:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/train_pivot_pattern_sequence_wavenet.py
```

Changes:

```text
1. Future Phase145A models now save Lambda layers with explicit output_shape for:
   - gather_5m_features
   - gather_htf_features
   - gather_all_features
   - last_temporal_state

2. Phase146A backtest now has a fallback loader for existing saved models:
   - first tries load_model(..., safe_mode=False, compile=False)
   - if Lambda shape inference still fails, rebuilds the architecture from vN_training.json + meta
   - extracts and loads weights from the .keras archive
```

This preserves the architecture while avoiding a retrain just to make the current v1 model loadable.

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```

The same Phase146A PowerShell command should now load the existing v1 model through the fallback path and proceed to prediction/backtest.

## Phase146A sequence WaveNet PnL audit result — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_backtest\latest.json` for the first Phase146A research PnL audit of the Phase145A full-source sequence WaveNet.

Backtest configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
model_version     : 1
tensor_shape      : [53098, 100, 140]
selected_samples  : 24000
eval_split        : test
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
buy_threshold     : 0.34
sell_threshold    : 0.34
min_margin        : 0
top_threshold     : 0
bottom_threshold  : 0
min_buy_r         : -999
min_sell_r        : -999
tp_multiplier     : 0.75
sl_multiplier     : 0.75
hold_bars         : 48
spread_mode/value : pct / 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Aggregate result:

```text
trades             : 135
BUY / SELL trades  : 44 / 91
wins / losses      : 68 / 67
win_rate           : 50.3704%
final_balance      : 100.8955889685
return_percent     : +0.8955889685%
total_cash_pnl     : +0.8955889685
gross_profit       : 49.4868161194
gross_loss         : 48.5912271509
profit_factor      : 1.0184310836
max_drawdown_cash  : 7.2327237246
take_profit        : 36
stop_loss          : 43
timeout            : 56
```

Side breakdown:

```text
BUY cash PnL  : +1.7578227452
SELL cash PnL : -0.8622337767
```

Monthly result:

```text
2026-07 : +0.6597453995 / 110 trades
2026-08 : +0.2358435690 / 25 trades
positive_months : 2
negative_months : 0
```

Operational counters:

```text
skipped_by_model   : 941
skipped_while_open : 2188
invalid_trade      : 0
```

Interpretation:

```text
GOOD:
- First PnL audit is positive on the purged test split.
- Both evaluated months are positive.
- BUY side is positive, unlike older hybrid diagnostics where BUY was the main damage source.
- No invalid trades were produced.

LIMITS:
- Edge is very thin: PF=1.018 and return is less than +1% on $100.
- Max drawdown (~$7.23) is much larger than net profit (~$0.90).
- SELL side is negative despite more trades than BUY.
- 56/135 trades are timeouts, so TP/SL/hold calibration likely matters.
- This is a single test split, not walk-forward.
- Loose thresholds were used; no robustness/threshold grid has been performed.
```

Decision:

```text
Phase146A first PnL audit is a weak positive research result, not a production pass.
It is the first pivot-lane result that is both classifier-strong and PnL-positive on the purged test split, but the edge is too small and fragile for paper/live.
Next required step: Phase146B threshold / TP-SL / side-specific grid on validation, then test confirmation; later walk-forward if robust.
No Phase134. No paper shadow. No live trading.
```

## Phase147A Option B grouped sequence WaveNet implemented — 2026-09-19

The owner reminded that the agreed roadmap must proceed in this order:

```text
Step 1 — Option B بسازیم
Step 2 — A/B benchmark منصفانه
Step 3 — آموزش بزرگ‌تر / full dataset
Step 4 — ذخیره کامل prediction/backtest archive
Step 5 — فیلترسازی، ولی با قانون ضد overfit
```

Phase147A implements Step 1.

Implemented:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
GUI: Train pivot sequence WaveNet Option B
```

Option B uses the existing healthy Phase145A tensor:

```text
stored X = [53098, 100, 140]
```

but feeds the model as grouped Keras inputs:

```text
m5_context_input  = [batch, 100, 35]   # generated_5m + session
source_5m_input   = [batch, 100, 83]   # source_5m telemetry
htf_context_input = [batch, 100, 22]   # closed 4H + closed 1D
```

Architecture:

```text
separate grouped branches
multi-scale causal Conv1D kernels 3,5,9
late fusion
gated tanh-sigmoid dilated WaveNet
residual/skip connections
SE/channel attention
temporal self-attention
avg/max/last pooling
multi-task heads
```

Command for owner:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --temporal-filters 96 `
  --temporal-kernels 3,5,9 `
  --dilations 1,2,4,8,16,32 `
  --residual-blocks 2 `
  --attention-heads 4 `
  --attention-key-dim 16 `
  --se-ratio 8 `
  --dense-units 128 `
  --dropout 0.25 `
  --activation tanh `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --early-stopping-patience 8 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 10 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b `
  --report-title "Option B Pivot Sequence WaveNet training"
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_option_b\latest.json
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_summary.txt
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_training_log.csv
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_batch_log.jsonl
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 54 passed
```

Next after owner runs Option B training:

```text
Step 2 — A/B benchmark منصفانه
```

## Phase147A Option B training result and Step2 backtest support — 2026-09-19

The owner supplied the first Phase147A Option B training result.

Training input:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
version           : 1
stored_x_shape    : [24000, 100, 140]
inputs:
  m5_context_input  : [batch, 100, 35]
  source_5m_input   : [batch, 100, 83]
  htf_context_input : [batch, 100, 22]
nonfinite_input_values : 0
```

Final restored metrics:

```text
val_action_accuracy : 0.7273284314
val_top_ap          : 0.4791975234
val_bottom_ap       : 0.2816134870
val_buy_r_mae       : 0.6719624400
val_sell_r_mae      : 0.6719951034
val_selected_rate   : 0.2846200980

test_action_accuracy : 0.6544117647
test_top_ap          : 0.2636572717
test_bottom_ap       : 0.2550490406
test_buy_r_mae       : 0.8204818964
test_sell_r_mae      : 0.8204245567
test_selected_rate   : 0.3134191176
```

A/B diagnostic comparison so far:

```text
Option A full-source [24000,100,140]
  test_action_accuracy : 0.6201
  test_top_ap          : 0.2709
  test_bottom_ap       : 0.3336
  test_buy/sell_r_mae  : ~0.736 / ~0.735
  test_selected_rate   : 0.3609
  test PnL             : +0.8956, PF=1.0184, maxDD=7.2327

Option B grouped inputs [24000,100,140]
  test_action_accuracy : 0.6544  ← better
  test_top_ap          : 0.2637  ← slightly worse
  test_bottom_ap       : 0.2550  ← worse
  test_buy/sell_r_mae  : ~0.820 / ~0.820  ← worse
  test_selected_rate   : 0.3134  ← more selective
  test PnL             : not yet run
```

Interpretation:

```text
Option B improved action classification but weakened bottom-zone AP and R-head MAE.
Because Phase146A showed PnL is very sensitive and weak, the next decision cannot be made from classifier metrics only.
Step 2 now requires a fair Option B PnL audit with the same rules used for Option A.
```

Implemented Step 2 support:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
```

now detects Option B records and feeds grouped prediction inputs automatically. The same GUI command can be used:

```text
Backtest pivot sequence WaveNet PnL
```

Recommended Option B backtest command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_backtest `
  --report-title "Phase147B Option B sequence WaveNet PnL audit"
```

Verification after adding Option B backtest support:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 56 passed
```

Decision:

```text
Step 1 is complete: Option B is built and trained.
Step 2 is now active: run Option B PnL audit and compare against Option A using the same replay rules.
No Phase134. No paper shadow. No live trading.
```

## Phase147B Option B PnL audit result / Step2 A-B benchmark — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_backtest\latest.json`, completing Step 2's first fair PnL comparison between Option A and Option B under the same Phase146 replay rules.

Option B backtest configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version     : 1
tensor_shape      : [53098, 100, 140]
selected_samples  : 24000
eval_split        : test
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
buy_threshold     : 0.34
sell_threshold    : 0.34
min_margin        : 0
top_threshold     : 0
bottom_threshold  : 0
min_buy_r         : -999
min_sell_r        : -999
tp_multiplier     : 0.75
sl_multiplier     : 0.75
hold_bars         : 48
spread_mode/value : pct / 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Option B aggregate result:

```text
trades             : 134
BUY / SELL trades  : 44 / 90
wins / losses      : 65 / 69
win_rate           : 48.5075%
final_balance      : 101.8764768367
return_percent     : +1.8764768367%
total_cash_pnl     : +1.8764768367
gross_profit       : 51.6444079174
gross_loss         : 49.7679310808
profit_factor      : 1.0377045378
max_drawdown_cash  : 7.7910373699
take_profit        : 41
stop_loss          : 41
timeout            : 52
```

Option B side breakdown:

```text
BUY cash PnL  : +1.9372472043
SELL cash PnL : -0.0607703677
```

Option B monthly result:

```text
2026-07 : +4.1183724559 / 106 trades
2026-08 : -2.2418956192 / 28 trades
positive_months : 1
negative_months : 1
```

Fair comparison against Option A under the same replay settings:

```text
Option A:
  trades        : 135
  final_balance : 100.8955889685
  return        : +0.8956%
  PF            : 1.0184
  maxDD         : 7.2327
  BUY PnL       : +1.7578
  SELL PnL      : -0.8622
  monthly       : Jul +0.6597, Aug +0.2358

Option B:
  trades        : 134
  final_balance : 101.8764768367
  return        : +1.8765%
  PF            : 1.0377
  maxDD         : 7.7910
  BUY PnL       : +1.9372
  SELL PnL      : -0.0608
  monthly       : Jul +4.1184, Aug -2.2419
```

Interpretation:

```text
GOOD:
- Option B improves net PnL and profit factor versus Option A.
- Option B nearly neutralizes the SELL-side loss seen in Option A.
- Option B has fewer timeouts and more take-profits than Option A.
- BUY remains positive.

LIMITS:
- Option B drawdown is slightly worse than Option A.
- Option B has one negative month: August -2.2419.
- PF=1.0377 is still thin; this is not production-grade.
- The result is still only one purged test split, not walk-forward.
```

Decision:

```text
Step 2 preliminary A/B benchmark: Option B is the current research winner by PnL/PF, but not by stability.
Proceed to Step 3 with Option B first: larger/full-dataset training with max_samples=0, still using chronological train/validation/test and early stopping.
Option A can be kept as a robustness comparison, but Option B gets priority.
No Phase134. No paper shadow. No live trading.
```

Recommended next Step 3 command:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 160 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --temporal-filters 96 `
  --temporal-kernels 3,5,9 `
  --dilations 1,2,4,8,16,32 `
  --residual-blocks 2 `
  --attention-heads 4 `
  --attention-key-dim 16 `
  --se-ratio 8 `
  --dense-units 128 `
  --dropout 0.25 `
  --activation tanh `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --early-stopping-patience 12 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 25 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_full `
  --report-title "Option B Pivot Sequence WaveNet full-dataset training"
```

## Phase148A range-aware sequence archive implemented — 2026-09-19

Implemented Step 4 requested by the owner while Step 3 full Option B training is running.

Implemented:

```text
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
GUI: Backtest sequence WaveNet range-aware archive
```

Purpose:

```text
Create a full prediction/backtest archive and calculate TP/SL from range forecasts rather than fixed ATR brackets.
```

Range source modes:

```text
--range-source auto    # use flat range columns when available, otherwise range models
--range-source flat    # use range columns from sequence flat parquet
--range-source models  # compute forecasts from gold_range_4h / gold_range_1d
```

Supported flat columns include both raw and source-prefixed names:

```text
range_4h_high_price / src5m_range_4h_high_price
range_4h_low_price  / src5m_range_4h_low_price
range_1d_high_price / src5m_range_1d_high_price
range_1d_low_price  / src5m_range_1d_low_price
```

Bracket logic:

```text
BUY : TP from range high, SL from range low
SELL: TP from range low,  SL from range high
```

with:

```text
--range-bracket-mode range|range_capped|atr
--use-1d-tp-cap 1
--max-tp-atr 2.0
--max-sl-atr 1.25
--min-tp-distance 0.5
--min-sl-distance 0.5
```

Full archive outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest.json
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest.html
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_predictions.parquet
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_predictions.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_trades.parquet
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_trades.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_monthly.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_side.csv
```

Recommended command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet_range.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 0 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --range-source auto `
  --range-bracket-mode range_capped `
  --range-fallback skip `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --range-1d-version 0 `
  --range-4h-version 0 `
  --use-1d-tp-cap 1 `
  --min-range-4h-room 0 `
  --min-range-1d-room 0 `
  --min-tp-distance 0.5 `
  --min-sl-distance 0.5 `
  --max-tp-atr 2.0 `
  --max-sl-atr 1.25 `
  --atr-tp-multiplier 0.75 `
  --atr-sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_range_archive `
  --report-title "Phase148A range-aware sequence WaveNet archive"
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 60 passed
```

Production remains blocked.

## Phase147C Option B branch feature expansion to 180 — 2026-09-19

The owner asked whether the small grouped raw input sizes could contribute to overfitting and requested each Option B branch input to support 180 useful features:

```text
m5_context_input  : [batch, 100, 180]
source_5m_input   : [batch, 100, 180]
htf_context_input : [batch, 100, 180]
```

Decision:

```text
We should not pad branches with arbitrary dummy columns or duplicate raw features.
More raw columns do not automatically reduce overfitting; irrelevant columns can make it worse.
```

Implemented a controlled optional causal feature expansion for Option B:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
```

New flags:

```text
--branch-target-features 180
--feature-augmentation-mode causal
--feature-augmentation-clip 8
```

When enabled, each branch is expanded with deterministic causal transforms of its own normalized feature stream:

```text
original values
lag-1 delta
lag-3 delta
lag-6 delta
causal rolling mean 3
causal rolling mean 6
causal rolling mean 12
abs lag-1 delta
abs lag-3 delta
```

Then the channel axis is clipped/truncated to the requested target count. For the current tensor:

```text
m5_context raw 35  → expanded 180
source_5m raw 83   → expanded 180
htf_context raw 22 → expanded 180
```

The expansion is causal within each 100-candle window and uses only data already inside the input window. It does not add future information beyond the endpoint.

Backtest/prediction support updated:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
```

The model record stores augmentation settings, and prediction loaders reproduce the same grouped 180-channel inputs.

GUI update:

```text
Train pivot sequence WaveNet Option B
  Expanded features per branch
  Feature augmentation
  Augmentation clip
```

Recommended command after the current full run finishes, only if owner wants the 180-channel experiment:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_180_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --branch-target-features 180 `
  --feature-augmentation-mode causal `
  --feature-augmentation-clip 8 `
  --temporal-filters 96 `
  --temporal-kernels 3,5,9 `
  --dilations 1,2,4,8,16,32 `
  --residual-blocks 2 `
  --attention-heads 4 `
  --attention-key-dim 16 `
  --se-ratio 8 `
  --dense-units 128 `
  --dropout 0.25 `
  --activation tanh `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --early-stopping-patience 8 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 10 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_180 `
  --report-title "Option B Pivot Sequence WaveNet 180-channel training"
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py -q
→ 17 passed
```

Caution:

```text
This is an experiment. The existing overfit symptoms are not necessarily caused by too few input features. More channels may help representation, but may also overfit harder. Compare by validation/test PnL, not training accuracy.
```

## Phase147C Option B 180-channel input health audit completed — 2026-09-19

Completed the owner-requested pre-training dataset/input health step for the Option B 180-channel experiment.

Implemented:

```text
scripts/audit_pivot_pattern_sequence_option_b_inputs.py
GUI: Audit pivot sequence Option B input health
```

Purpose:

```text
Before training, verify the exact training-time Option B expanded inputs:
  m5_context_input  = [batch, 100, 180]
  source_5m_input   = [batch, 100, 180]
  htf_context_input = [batch, 100, 180]
```

The audit does not duplicate the dataset on disk. It:

```text
1. Loads the healthy source tensor [53098,100,140] as memmap.
2. Rebuilds Option B groups from feature metadata.
3. Selects the same sample universe as training.
4. Reconstructs chronological train/validation/test split.
5. Fits the same train-only scaler as training.
6. Builds expanded 180-channel batches exactly like the trainer.
7. Scans each branch for NaN/Inf and clip violations.
8. Confirms the intended Keras input shapes.
```

Recommended health command before 180-channel training:

```powershell
python -u scripts\audit_pivot_pattern_sequence_option_b_inputs.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --stream-chunk-size 512 `
  --scan-chunk-size 256 `
  --full-scan 1 `
  --max-scan-samples 0 `
  --branch-target-features 180 `
  --feature-augmentation-mode causal `
  --feature-augmentation-clip 8 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_option_b_input_health
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_option_b_input_health\latest.json
run_logs\pivot_pattern_sequence_option_b_input_health\latest.html
```

Only after `status=PASS` should the owner run the 180-channel training command.

Verification:

```text
python -m py_compile scripts/audit_pivot_pattern_sequence_option_b_inputs.py scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 64 passed
```

## Phase147C Option B 180-channel input health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_option_b_input_health\latest.json` after running the official Phase147C 180-channel Option B input audit.

Audit input:

```text
stored_x_shape      : [53098, 100, 140]
selected_x_shape    : [53098, 100, 140]
branch_target       : 180
augmentation_mode   : causal
augmentation_clip   : 8.0
```

Chronological split rebuilt by the audit:

```text
train_rows      : 37168
validation_rows : 7629
test_rows       : 7629
purge_gap       : 336
```

Raw branch counts:

```text
m5_context raw  : 35
source_5m raw   : 83
htf_context raw : 22
```

Expanded Keras inputs:

```text
m5_context_input  : [batch, 100, 180]
source_5m_input   : [batch, 100, 180]
htf_context_input : [batch, 100, 180]
```

Full expanded-input scan:

```text
m5_context_input:
  scanned_cells   : 955,764,000
  nonfinite_cells : 0
  min/max/max_abs : -8.0 / 8.0 / 8.0
  chunks          : 208

source_5m_input:
  scanned_cells   : 955,764,000
  nonfinite_cells : 0
  min/max/max_abs : -8.0 / 8.0 / 8.0
  chunks          : 208

htf_context_input:
  scanned_cells   : 955,764,000
  nonfinite_cells : 0
  min/max/max_abs : -6.2252612114 / 8.0 / 8.0
  chunks          : 208
```

Total scanned expanded cells:

```text
2,867,292,000
```

Targets over selected samples:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Result:

```text
status   : PASS
warnings : []
errors   : []
```

Decision:

```text
The actual 180-channel Option B training-time inputs are accepted as healthy.
The owner can proceed with full-dataset 180-channel Option B training.
This remains research-only; no production/paper/live permission.
```

## Phase147C Option B 180-channel full-dataset training result — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_180_full\latest.json` for the full-dataset 180-channel Option B training run.

Training configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_180_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [53098, 100, 140]
keras inputs:
  m5_context_input  : [batch, 100, 180]
  source_5m_input   : [batch, 100, 180]
  htf_context_input : [batch, 100, 180]
samples           : 53098
train_rows        : 37168
validation_rows   : 7629
test_rows         : 7629
branch_target_features      : 180
feature_augmentation_mode   : causal
feature_augmentation_clip   : 8.0
nonfinite_input_values      : 0
```

Metrics:

```text
val_action_accuracy : 0.5585266745
val_top_ap          : 0.2717308013
val_bottom_ap       : 0.2202253973
val_buy_r_mae       : 0.6357029080
val_sell_r_mae      : 0.6304646134
val_selected_rate   : 0.4700484991

test_action_accuracy : 0.5168436230
test_top_ap          : 0.2486227103
test_bottom_ap       : 0.2121224816
test_buy_r_mae       : 0.7210720181
test_sell_r_mae      : 0.7024750710
test_selected_rate   : 0.4856468738
```

Comparison to the 24k raw-branch Option B run:

```text
Option B raw branches [24000,100,140]
  test_action_accuracy : 0.6544
  test_top_ap          : 0.2637
  test_bottom_ap       : 0.2550
  test_selected_rate   : 0.3134
  PnL/PF               : +1.8765%, PF=1.0377

Option B 180-channel full universe [53098,100,140 → grouped 180]
  test_action_accuracy : 0.5168
  test_top_ap          : 0.2486
  test_bottom_ap       : 0.2121
  test_selected_rate   : 0.4856
  PnL/PF               : not run yet
```

Interpretation:

```text
- The 180-channel input health was PASS, so this is not a NaN/Inf problem.
- The 180-channel causal augmentation did not improve diagnostic metrics in this full-universe run.
- test_selected_rate rose to ~48.6%, suggesting the model became more aggressive.
- Action accuracy and bottom AP are materially worse than the 24k raw-branch Option B run.
- This supports the earlier caution: more channels/features do not automatically reduce overfit; they can add noisy degrees of freedom.
```

Decision:

```text
Do not promote the 180-channel full-dataset model based on current classifier/AP diagnostics.
Keep the raw-branch Option B 24k model as the current preliminary PnL/PF winner until a better full-dataset run proves otherwise.
If testing this 180 model further, run range-aware archive/backtest only as a diagnostic, not as a preferred candidate.
Next recommended route: train raw-branch Option B full dataset or proceed with Step 4 archive on the current best Option B model, then Step 5 anti-overfit filtering.
No Phase134. No paper shadow. No live trading.
```

## Phase149A sequence feature impact audit implemented — 2026-09-19

Implemented validation-only feature/group ablation diagnostics to answer which raw sequence features are useful, neutral, or drop candidates.

Implemented:

```text
scripts/audit_pivot_sequence_feature_impact.py
GUI: Audit pivot sequence feature impact
```

Method:

```text
- Load trained Option A or Option B sequence WaveNet.
- Evaluate a chronological split, default validation.
- Compute baseline metrics.
- Zero-ablate groups/features at inference time.
- Compute metric deltas and composite score deltas.
- Mark features as KEEP_IMPORTANT / NEUTRAL / DROP_CANDIDATE.
```

Composite score:

```text
composite = action_accuracy + 0.5*top_ap + 0.5*bottom_ap - 0.25*buy_r_mae - 0.25*sell_r_mae
```

Outputs:

```text
run_logs\pivot_sequence_feature_impact\latest.json
run_logs\pivot_sequence_feature_impact\latest.html
run_logs\pivot_sequence_feature_impact\latest_features.csv
run_logs\pivot_sequence_feature_impact\latest_groups.csv
```

Recommended command:

```powershell
python -u scripts\audit_pivot_sequence_feature_impact.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split validation `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 1500 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --check-groups 1 `
  --check-features 1 `
  --feature-group-filter all `
  --max-features-to-check 0 `
  --harmful-threshold 0.005 `
  --useful-threshold 0.005 `
  --storage-root datasets `
  --output-dir run_logs\pivot_sequence_feature_impact `
  --report-title "Phase149A sequence feature impact audit"
```

Verification:

```text
python -m py_compile scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 68 passed
```

Anti-overfit rule:

```text
Use validation for discovery. Do not drop based on final test only.
Retrain/confirm on test and later walk-forward before adopting filters.
```

## Phase149A feature impact result — 2026-09-19

The owner supplied `run_logs\pivot_sequence_feature_impact\latest.json` for the validation-only feature/group ablation audit.

Audit target/model:

```text
model_id        : gold_pivot_pattern_sequence_wavenet_option_b_180_5m
model_version   : 1
eval_split      : validation
max_samples     : 24000
max_windows     : 1500
evaluated period: 2026-05-28 09:20:00+00:00 → 2026-06-29 10:35:00+00:00
option_b_model  : true
branch_target_features : 180
augmentation    : causal, clip=8
```

Baseline validation metrics on the audit subset:

```text
action_accuracy : 0.6466666667
top_ap          : 0.6543383331
bottom_ap       : 0.4293868145
buy_r_mae       : 0.5251473784
sell_r_mae      : 0.5323911309
selected_rate   : 0.4813333333
composite       : 0.9241446131
```

Group ablation result:

```text
KEEP_IMPORTANT:
- generated_5m   Δcomposite=-0.39947
- source_5m      Δcomposite=-0.45480
- session        Δcomposite=-0.04034
- closed_1d      Δcomposite=-0.04649
- m5_context     Δcomposite=-0.42006
- htf_context    Δcomposite=-0.01588
- all_features   Δcomposite=-1.16648

DROP_CANDIDATE:
- closed_4h      Δcomposite=+0.02278
```

Feature-level summary:

```text
feature_count       : 140
checked_feature_count : 140
DROP_CANDIDATE      : 26
KEEP_IMPORTANT      : 31
NEUTRAL             : 83
```

Strongest DROP_CANDIDATE examples from validation-only ablation:

```text
src5m_rolling_12_trades_timeout_rate_lag
m5_pos_in_range_48
src5m_specialist_max_prob
src5m_rolling_12_trades_profit_factor_lag
src5m_rolling_48_trades_profit_factor_lag
src5m_rolling_48_trades_timeout_rate_lag
m5_pos_in_range_96
src5m_rolling_24_trades_avg_pnl_lag
m5_mid_slow_dist_atr
d1_ret3
src5m_lagged_trade_count
h4_ret3
h4_rsi14
src5m_last_closed_trade_pnl_lag
src5m_rolling_12_trades_avg_pnl_lag
m5_fast_mid_dist_atr
m5_dist_low_48_atr
src5m_range_1d_up_room_pct
src5m_range_1d_down_room_pct
m5_ret48
m5_pos_in_range_24
h4_room_down_atr
src5m_5m_body_pct
h4_close_mid_dist_atr
m5_ret24
src5m_rolling_48_trades_avg_pnl_lag
```

Strongest KEEP_IMPORTANT examples:

```text
src5m_rolling_24_trades_profit_factor_lag
src5m_specialist_buy_minus_sell
src5m_booster_buy_prob
src5m_specialist_sell_minus_buy
src5m_buy_specialist_prob
src5m_booster_sell_prob
session_dow_sin
session_hour_cos
src5m_sell_specialist_prob
d1_mid_slow_dist_atr
d1_room_down_atr
m5_ema_fast
m5_atr
m5_dist_high_48_atr
m5_ema_slow
m5_volatility_24
src5m_4h_last_closed_age_5m
m5_dist_low_24_atr
h4_range_pct
d1_fast_mid_dist_atr
d1_close_mid_dist_atr
src5m_session_hour_cos
m5_dist_high_96_atr
src5m_1d_return_1
src5m_booster_action_margin
session_dow_cos
m5_ret1
m5_upper_wick_pct
src5m_session_dow_cos
m5_ema_mid
src5m_1d_body_pct
```

Interpretation:

```text
- source_5m and generated_5m are strongly important as groups.
- session/time is useful despite only four raw columns.
- closed_1d is useful.
- closed_4h as a group is suspicious in this 180-channel model and should become a controlled ablation candidate.
- Individual DROP_CANDIDATE labels are not delete commands; they are validation-discovered hypotheses.
```

Anti-overfit rule:

```text
Do not delete features solely from this audit.
Use this result to define controlled pruning experiments, then retrain and confirm on test/walk-forward.
```

Recommended controlled pruning experiments:

```text
P0 baseline: current raw-branch Option B winner
P1 remove closed_4h group only
P2 remove top 10 validation DROP_CANDIDATE features
P3 remove all 26 validation DROP_CANDIDATE features
P4 remove closed_4h + top 10 DROP_CANDIDATE features
```

## Phase149B pruned-feature training support — 2026-09-19

After the Phase149A validation feature-impact result, training and prediction loaders were extended to support controlled feature-zeroing experiments.

Implemented in:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
```

New trainer flags:

```text
--zero-feature-names "name1,name2,..."
--zero-feature-file configs/phase149a_option_b_180_validation_drop_candidates.txt
--zero-feature-groups "closed_4h"
```

Tracked drop-list file:

```text
configs/phase149a_option_b_180_validation_drop_candidates.txt
```

It contains the 26 validation-discovered DROP_CANDIDATE features from Phase149A.

Behavior:

```text
The original tensor is not rewritten.
Selected features are zeroed after train-only normalization and before Option B grouping/causal augmentation.
Model records store the feature_selection payload.
Backtest/range archive loaders apply the same zero mask at prediction time.
```

Recommended controlled experiment command:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --branch-target-features 180 `
  --feature-augmentation-mode causal `
  --feature-augmentation-clip 8 `
  --zero-feature-file configs\phase149a_option_b_180_validation_drop_candidates.txt `
  --temporal-filters 96 `
  --temporal-kernels 3,5,9 `
  --dilations 1,2,4,8,16,32 `
  --residual-blocks 2 `
  --attention-heads 4 `
  --attention-key-dim 16 `
  --se-ratio 8 `
  --dense-units 128 `
  --dropout 0.25 `
  --activation tanh `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --early-stopping-patience 8 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 25 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_180_pruned `
  --report-title "Option B 180 pruned validation-drop-candidate training"
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 69 passed
```

Anti-overfit reminder:

```text
This model is a controlled experiment using validation-discovered drop candidates.
If it improves validation, confirm with test PnL and then walk-forward before adopting.
```

## Phase149B pruned 180-channel training result — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_180_pruned\latest.json` and late batch/epoch logs for the controlled pruned 180-channel Option B experiment.

Training configuration:

```text
model_id              : gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m
version               : 1
stored_x_shape        : [24000, 100, 140]
keras inputs          : [batch,100,180] × 3 branches
max_samples           : 24000
branch_target_features: 180
augmentation          : causal, clip=8
zero_feature_file     : configs\phase149a_option_b_180_validation_drop_candidates.txt
zeroed_feature_count  : 26
epochs                : 200
early_stopping_patience: 200
nonfinite_input_values: 0
```

Zeroed validation-discovered DROP_CANDIDATE features included:

```text
m5_fast_mid_dist_atr
m5_mid_slow_dist_atr
m5_pos_in_range_24
m5_pos_in_range_48
m5_dist_low_48_atr
m5_pos_in_range_96
m5_ret24
m5_ret48
h4_ret3
h4_close_mid_dist_atr
h4_rsi14
h4_room_down_atr
d1_ret3
src5m_5m_body_pct
src5m_specialist_max_prob
src5m_range_1d_up_room_pct
src5m_range_1d_down_room_pct
src5m_lagged_trade_count
src5m_last_closed_trade_pnl_lag
src5m_rolling_12_trades_avg_pnl_lag
src5m_rolling_12_trades_profit_factor_lag
src5m_rolling_12_trades_timeout_rate_lag
src5m_rolling_24_trades_avg_pnl_lag
src5m_rolling_48_trades_avg_pnl_lag
src5m_rolling_48_trades_profit_factor_lag
src5m_rolling_48_trades_timeout_rate_lag
```

Final report metrics:

```text
val_action_accuracy : 0.6875000000
val_top_ap          : 0.3458503914
val_bottom_ap       : 0.2774233380
val_buy_r_mae       : 0.6454545856
val_sell_r_mae      : 0.6455140710
val_selected_rate   : 0.3026960784

test_action_accuracy : 0.6611519608
test_top_ap          : 0.2793102151
test_bottom_ap       : 0.2795754914
test_buy_r_mae       : 0.7160413861
test_sell_r_mae      : 0.7160999179
test_selected_rate   : 0.3060661765
```

Late training log showed strong train/validation divergence:

```text
epoch 198 train_acc≈0.9917, val_loss≈3.0868
epoch 199 train_acc≈0.9933, val_loss≈2.7145
epoch 200 train_acc≈0.9945, val_loss≈2.9824
```

Interpretation:

```text
- The model heavily overfit by late epochs.
- The final report metrics are still useful only if restored/best validation weights were used; in any case, the late logs confirm that patience=200 is too large for future runs.
- Despite overfit risk, the pruned 180-channel model improved test diagnostics versus raw Option B on this 24k benchmark.
```

Comparison to raw Option B 24k:

```text
Raw Option B:
  test_action_accuracy : 0.6544
  test_top_ap          : 0.2637
  test_bottom_ap       : 0.2550
  test_buy/sell_r_mae  : ~0.820 / ~0.820
  test_selected_rate   : 0.3134
  PnL/PF               : +1.8765%, PF=1.0377

Pruned 180 Option B:
  test_action_accuracy : 0.6612
  test_top_ap          : 0.2793
  test_bottom_ap       : 0.2796
  test_buy/sell_r_mae  : ~0.716 / ~0.716
  test_selected_rate   : 0.3061
  PnL/PF               : pending
```

Decision:

```text
The pruned 180-channel model is now the strongest classifier/ranking diagnostic among the 24k sequence models.
It must not be promoted until PnL audit and range-aware archive confirm it.
Next action: run fair Phase146A ATR PnL audit for gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m, then Phase148A range-aware archive if promising.
No Phase134. No paper shadow. No live trading.
```

## Phase149B pruned 180 PnL audit failure — 2026-09-20

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_180_pruned_backtest\latest.json` for the ATR-based PnL audit of the pruned 180-channel Option B model.

Backtest configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m
model_version     : 1
eval_split        : test
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
buy/sell threshold: 0.34 / 0.34
min_margin        : 0
tp/sl multiplier  : 0.75 / 0.75
hold_bars         : 48
spread            : pct 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Result:

```text
trades             : 120
BUY / SELL trades  : 41 / 79
wins / losses      : 57 / 63
win_rate           : 47.50%
final_balance      : 91.6591309299
return_percent     : -8.3408690701%
total_cash_pnl     : -8.3408690701
gross_profit       : 36.3334344612
gross_loss         : 44.6743035313
profit_factor      : 0.8132960469
max_drawdown_cash  : 10.2459750447
take_profit        : 26
stop_loss          : 38
timeout            : 56
```

Side breakdown:

```text
BUY cash PnL  : +0.1146579499
SELL cash PnL : -8.4555270200
```

Monthly result:

```text
2026-07 : -5.3828214745 / 99 trades
2026-08 : -2.9580475956 / 21 trades
positive_months : 0
negative_months : 2
```

Comparison to raw Option B 24k benchmark:

```text
Raw Option B:
  final_balance : 101.8764768367
  return        : +1.8765%
  PF            : 1.0377
  maxDD         : 7.7910
  BUY PnL       : +1.9372
  SELL PnL      : -0.0608
  months        : July +4.1184, August -2.2419

Pruned 180 Option B:
  final_balance : 91.6591309299
  return        : -8.3409%
  PF            : 0.8133
  maxDD         : 10.2460
  BUY PnL       : +0.1147
  SELL PnL      : -8.4555
  months        : July -5.3828, August -2.9580
```

Interpretation:

```text
- The pruned 180-channel model improved classifier/ranking diagnostics but failed trading replay badly.
- The validation-discovered DROP_CANDIDATE pruning did not transfer to PnL.
- SELL side became the dominant damage source again.
- Both evaluated months are negative.
- This confirms the anti-overfit warning: feature ablation improvements on validation classification metrics are not sufficient for trade profitability.
```

Decision:

```text
Reject gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m as a trading candidate.
Do not continue range-aware archive or full training for this pruned 180 model.
Current best research candidate reverts to raw Option B 24k: gold_pivot_pattern_sequence_wavenet_option_b_5m.
Next steps should focus on raw Option B range-aware archive and/or validation-based TP/SL/side-specific filtering.
No Phase134. No paper shadow. No live trading.
```

## Phase147D raw Option B full-dataset training/backtest result — 2026-09-20

The owner retrained the raw Option B grouped sequence WaveNet on the full available tensor after the previous `gold_pivot_pattern_sequence_wavenet_option_b_5m` model artifact had been deleted.

Training configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_full_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [53098, 100, 140]
samples           : 53098
train_rows        : 37168
validation_rows   : 7629
test_rows         : 7629
keras inputs:
  m5_context_input  : [batch, 100, 35]
  source_5m_input   : [batch, 100, 83]
  htf_context_input : [batch, 100, 22]
branch_target_features    : 0
feature_augmentation_mode : off
zeroed_feature_count      : 0
nonfinite_input_values    : 0
```

Classifier/ranking metrics:

```text
val_action_accuracy  : 0.6051907196
val_top_ap           : 0.3279156938
val_bottom_ap        : 0.2115178335
val_buy_r_mae        : 0.6564043164
val_sell_r_mae       : 0.6502464414
val_selected_rate    : 0.4475029493

test_action_accuracy : 0.5586577533
test_top_ap          : 0.2518729500
test_bottom_ap       : 0.2330887866
test_buy_r_mae       : 0.7078536153
test_sell_r_mae      : 0.7026057839
test_selected_rate   : 0.4570717001
```

ATR PnL check on the same full-universe split:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_full_5m
eval_split        : test
selected_samples  : 53098
evaluated_samples : 7629
evaluated period  : 2026-07-24 14:05:00+00:00 → 2026-09-02 10:25:00+00:00
trades            : 174
BUY / SELL trades : 93 / 81
wins / losses     : 86 / 88
win_rate          : 49.4253%
final_balance     : 96.1853978886
return_percent    : -3.8146021114%
total_cash_pnl    : -3.8146021114
gross_profit      : 59.9770903102
gross_loss        : 63.7916924216
profit_factor     : 0.9402022118
max_drawdown_cash : 15.1989241036
take_profit       : 44
stop_loss         : 51
timeout           : 79
```

Side and monthly breakdown:

```text
BUY cash PnL  : +1.0795518044
SELL cash PnL : -4.8941539158

2026-07 : +4.9827258346 / 36 trades
2026-08 : -9.2146695014 / 127 trades
2026-09 : +0.4173415553 / 11 trades
positive_months : 2
negative_months : 1
```

Dataset/feature verdict:

```text
The dataset and features used for this run are structurally OK:
- stored tensor shape is the intended [53098,100,140]
- Option B group counts match metadata: 35 / 83 / 22
- source_5m telemetry features are present: 83 source features
- nonfinite_input_values=0
- previous official tensor health audit passed with nonfinite_cells=0 and max_abs=8.0
- chronological split with purge_gap=336 was used
```

Trading verdict:

```text
The full-dataset raw Option B model is NOT promoted as a trading candidate.
It is a clean/healthy-data training run, but the PnL check is negative: final_balance=96.1854, PF=0.9402, maxDD=15.1989.
SELL side and August are the main damage sources in this full run.
```

Comparison to previous raw Option B 24k benchmark:

```text
Raw Option B 24k historical benchmark:
  final_balance : 101.8764768367
  return        : +1.8765%
  PF            : 1.0377
  maxDD         : 7.7910
  period        : 2026-07-03 → 2026-08-06

Raw Option B full-dataset rebuild:
  final_balance : 96.1853978886
  return        : -3.8146%
  PF            : 0.9402
  maxDD         : 15.1989
  period        : 2026-07-24 → 2026-09-02
```

Decision:

```text
Accept the dataset/features as healthy.
Reject this full-dataset raw Option B run as a trading candidate until a validation/range-aware/walk-forward process proves otherwise.
Do not interpret the negative result as data corruption; interpret it as weak model generalization/regime sensitivity.
Current best historical research result remains the deleted/raw 24k Option B benchmark, but it must be rebuilt if more archive/backtest work is required.
No Phase134. No paper shadow. No live trading.
```

## Phase149B/147D PowerShell empty zero-feature flag fix — 2026-09-20

The owner reran raw Option B 24k rebuild with explicit empty zero-feature flags:

```text
--zero-feature-names ""
--zero-feature-file ""
--zero-feature-groups ""
```

PowerShell/native argv handling dropped the empty strings, so argparse saw `--zero-feature-names` without a value and failed:

```text
train_pivot_pattern_sequence_wavenet_option_b.py: error: argument --zero-feature-names: expected one argument
```

Fix implemented in:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
```

The three optional zero-feature flags now use:

```text
nargs="?"
const=""
default=""
```

Safe forms now include both:

```powershell
# recommended for no pruning: omit these flags entirely

# also accepted now if a shell drops the empty value
--zero-feature-names
--zero-feature-file
--zero-feature-groups
```

Immediate operator workaround on older checkouts:

```text
Remove the three empty zero-feature lines from the raw Option B rebuild command.
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py -q
→ 4 passed
```

## Phase147E raw Option B 24k rebuild result — previous weak-positive result did not reproduce — 2026-09-20

The owner rebuilt the raw Option B 24k model after the earlier historical current-best artifact had been deleted.

Training configuration:

```text
model_id              : gold_pivot_pattern_sequence_wavenet_option_b_5m
version               : 1
max_samples           : 24000
stored_x_shape        : [24000, 100, 140]
keras inputs          : [batch,100,35] / [batch,100,83] / [batch,100,22]
branch_target_features: 0
augmentation          : off
zeroed_feature_count  : 0
nonfinite_input_values: 0
```

Training diagnostics:

```text
val_action_accuracy  : 0.6875000000
val_top_ap           : 0.4298344451
val_bottom_ap        : 0.3018743404
val_buy_r_mae        : 0.6229432821
val_sell_r_mae       : 0.6397787333
val_selected_rate    : 0.3452818627

test_action_accuracy : 0.6151960784
test_top_ap          : 0.2843775626
test_bottom_ap       : 0.3673007788
test_buy_r_mae       : 0.6919192076
test_sell_r_mae      : 0.6780540347
test_selected_rate   : 0.4056372549
```

ATR PnL check:

```text
eval_split        : test
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
trades            : 135
BUY / SELL trades : 46 / 89
wins / losses     : 60 / 75
win_rate          : 44.4444%
final_balance     : 90.7052413035
return_percent    : -9.2947586965%
total_cash_pnl    : -9.2947586965
profit_factor     : 0.8270058072
max_drawdown_cash : 10.7624722054
take_profit       : 34
stop_loss         : 46
timeout           : 55
BUY PnL           : -5.3900375011
SELL PnL          : -3.9047211954
monthly           : 2026-07 -3.6628516601, 2026-08 -5.6319070363
positive_months   : 0
negative_months   : 2
```

Comparison with the deleted historical raw Option B 24k benchmark:

```text
Historical raw B 24k:
  test_action_accuracy : 0.6544
  test_selected_rate   : 0.3134
  final_balance        : 101.8765
  return               : +1.8765%
  PF                   : 1.0377
  maxDD                : 7.7910
  BUY PnL              : +1.9372
  SELL PnL             : -0.0608

Rebuilt raw B 24k:
  test_action_accuracy : 0.6152
  test_selected_rate   : 0.4056
  final_balance        : 90.7052
  return               : -9.2948%
  PF                   : 0.8270
  maxDD                : 10.7625
  BUY PnL              : -5.3900
  SELL PnL             : -3.9047
```

Interpretation:

```text
The dataset/features are still healthy. This is not a tensor-shape or NaN/Inf issue.
The old weak-positive Option B artifact was not reproducible after deletion and retraining.
The new run selected a different local solution: lower action accuracy, higher selected_rate, and materially worse trade timing.
Both BUY and SELL are negative, and both evaluated months are negative.
```

Important root cause / correction:

```text
The Option B trainer did not previously expose a run seed. The batch Sequence shuffle used a fixed RNG, but TensorFlow/Keras initialization, dropout, and some backend operations were not under an explicit recorded seed.
Deleting the old model artifact made exact recovery impossible.
```

Fix implemented:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
--random-seed 20260919
```

The trainer now calls Python/NumPy/TensorFlow seed setters before model creation and records the seed in the training record/report. The GUI command `Train pivot sequence WaveNet Option B` now has a `Random seed` field and forwards `--random-seed`.

Caution:

```text
A seed improves controlled reruns but does not guarantee byte-identical output across every GPU/TF backend. It also cannot recover the deleted old artifact.
```

Decision:

```text
Reject this rebuilt raw Option B 24k model as a trading candidate.
Do not run Phase148A range-aware archive on this rebuilt v1 as if it were the old winner.
The previous weak-positive raw Option B result is now treated as fragile/non-reproducible until a seeded validation/test process can reproduce it.
Next valid research step is not blind retraining; it is a controlled repeatability/seed audit selected on validation and confirmed on test.
No Phase134. No paper shadow. No live trading.
```

Verification for reproducibility-seed support:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py src/ShadBotTrader/presentation/commands/handlers.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 43 passed
```

## Phase147F raw Option B 24k rebuild validation-vs-test transfer failure — 2026-09-20

The owner ran the validation ATR PnL check for the rebuilt raw Option B 24k model after its test PnL failed.

Validation replay configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version     : 1
eval_split        : validation
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-05-28 09:20:00+00:00 → 2026-07-01 09:05:00+00:00
buy/sell threshold: 0.34 / 0.34
min_margin        : 0
tp/sl multiplier  : 0.75 / 0.75
hold_bars         : 48
spread            : pct 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Validation result:

```text
trades             : 110
BUY / SELL trades  : 70 / 40
wins / losses      : 62 / 48
win_rate           : 56.3636%
final_balance      : 108.7914207603
return_percent     : +8.7914207603%
total_cash_pnl     : +8.7914207603
gross_profit       : 43.2124907078
gross_loss         : 34.4210699475
profit_factor      : 1.2554081199
max_drawdown_cash  : 5.9715931205
take_profit        : 33
stop_loss          : 25
timeout            : 52
BUY PnL            : -1.8550476298
SELL PnL           : +10.6464683900
monthly            : 2026-05 +1.1865238507, 2026-06 +7.6048969096
positive_months    : 2
negative_months    : 0
```

Same rebuilt model on test:

```text
trades             : 135
final_balance      : 90.7052413035
return_percent     : -9.2947586965%
profit_factor      : 0.8270058072
max_drawdown_cash  : 10.7624722054
BUY PnL            : -5.3900375011
SELL PnL           : -3.9047211954
monthly            : 2026-07 -3.6628516601, 2026-08 -5.6319070363
positive_months    : 0
negative_months    : 2
```

Interpretation:

```text
This is a clear validation-to-test transfer failure.
The model has strong validation PnL, but that edge is almost entirely SELL-side and does not survive the later test regime.
Validation: BUY is negative, SELL is strongly positive.
Test: both BUY and SELL are negative.
```

Decision:

```text
Do not promote the rebuilt raw Option B 24k model.
Do not run Step 4/range-aware archive on this model as if it is the historical winner.
The correct next phase is a controlled anti-overfit validation-to-test audit: discover only on validation, confirm on test, and later walk-forward.
No Phase134. No paper shadow. No live trading.
```

Recommended next research phase:

```text
Phase150A — Option B validation-to-test transfer / seed-threshold audit
```

Required anti-overfit rules for Phase150A:

```text
- validation is for discovery only
- test is confirmation only
- no threshold/filter chosen from test
- if validation-selected candidate fails test, reject it
- if test passes, still require walk-forward before paper/live
```

## Phase148B range-aware archive now supports train/validation splits — 2026-09-20

The owner proposed the correct next direction after the raw Option B rebuild showed validation-to-test transfer failure:

```text
Build/run a more realistic simulation backtest where TP and SL are derived from range forecasts.
Run it fully on train and validation first.
Then perform anti-overfit filtering/selection from those archive outputs before any test confirmation.
```

Assessment:

```text
This is the correct direction. The previous ATR-only PnL checks may be too crude for exit geometry, and test must be held back for confirmation rather than used for discovery.
```

Implementation update:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
GUI: Backtest pivot sequence WaveNet PnL
GUI: Backtest sequence WaveNet range-aware archive
```

Both backtest scripts now support:

```text
--eval-split train
```

Previously Phase148A range-aware archive supported only:

```text
test, validation, all, tail
```

Now the realistic range-aware archive can be generated separately for:

```text
train      → in-sample anatomy / diagnostics only
validation → discovery / filter selection
test       → confirmation only, not tuning
```

Anti-overfit rule:

```text
Do not use test for discovery.
Run train + validation range-aware archives first.
Discover candidate thresholds/filters from train/validation only.
Then run exactly one unchanged confirmation on test.
If test fails, reject.
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/handlers.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase148C range-aware train/validation archive result — range-model TP/SL failed badly — 2026-09-20

The owner ran the Phase148B range-aware archive on the rebuilt raw Option B 24k model using range-derived TP/SL from range models.

Common configuration:

```text
model_id            : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version       : 1
max_samples         : 24000
range_source        : auto → models
range_bracket_mode  : range_capped
range_fallback      : skip
range_1d_model_id   : gold_range_1d
range_4h_model_id   : gold_range_4h
use_1d_tp_cap       : 1
max_tp_atr          : 2.0
max_sl_atr          : 1.25
min_tp_distance     : 0.5
min_sl_distance     : 0.5
hold_bars           : 48
spread              : pct 0.06
same_bar_policy     : stop_first
```

Train archive result:

```text
eval_split        : train
evaluated period  : 2025-11-28 17:05:00+00:00 → 2026-05-25 19:15:00+00:00
evaluated_samples : 16800
trades            : 1176
BUY / SELL        : 547 / 629
wins / losses     : 392 / 784
win_rate          : 33.3333%
final_balance     : 6.5162807311
return_percent    : -93.4837192689%
total_cash_pnl    : -93.4837192689
profit_factor     : 0.6073804291
max_drawdown_cash : 93.5008911264
take_profit       : 356
stop_loss         : 769
timeout           : 51
invalid_bracket   : 1410
BUY PnL           : -28.2722708191
SELL PnL          : -65.2114484498
positive_months   : 0
negative_months   : 7
```

Train monthly summary:

```text
2025-11 :  -4.9010 / 5 trades
2025-12 : -45.9841 / 233 trades
2026-01 : -24.8121 / 215 trades
2026-02 :  -2.3687 / 167 trades
2026-03 :  -1.3067 / 176 trades
2026-04 :  -9.3004 / 215 trades
2026-05 :  -4.8107 / 165 trades
```

Validation archive result:

```text
eval_split        : validation
evaluated period  : 2026-05-28 09:20:00+00:00 → 2026-07-01 09:05:00+00:00
evaluated_samples : 3264
trades            : 250
BUY / SELL        : 151 / 99
wins / losses     : 53 / 197
win_rate          : 21.2000%
final_balance     : 27.1922217861
return_percent    : -72.8077782139%
total_cash_pnl    : -72.8077782139
profit_factor     : 0.3114226665
max_drawdown_cash : 76.6329350539
take_profit       : 49
stop_loss         : 194
timeout           : 7
invalid_bracket   : 392
BUY PnL           : -50.9467117142
SELL PnL          : -21.8610664997
positive_months   : 0
negative_months   : 2
```

Validation monthly summary:

```text
2026-05 :  -5.5864 / 16 trades
2026-06 : -67.2213 / 234 trades
```

Comparison to ATR validation for the same rebuilt model:

```text
ATR validation:
  final_balance : 108.7914
  PF            : 1.2554
  maxDD         : 5.9716
  BUY PnL       : -1.8550
  SELL PnL      : +10.6465

Range-aware validation:
  final_balance : 27.1922
  PF            : 0.3114
  maxDD         : 76.6329
  BUY PnL       : -50.9467
  SELL PnL      : -21.8611
```

Interpretation:

```text
The owner’s proposed workflow was correct: build/run realistic range-aware TP/SL archive before filtering.
The result shows the current range-model TP/SL geometry is unusable with this sequence model.
This is not a model-entry improvement; it is a bracket failure.
```

Key failure signatures:

```text
- range_source resolved to models, not flat cached range columns.
- Train and validation both collapse, so this is not only out-of-time overfit.
- Stop-loss rate is extremely high: train 769/1176, validation 194/250.
- Timeouts nearly disappear under range brackets, meaning trades are being resolved by TP/SL quickly, mostly by SL.
- Many invalid brackets occur: train 1410, validation 392.
- BUY and SELL are both negative under range-aware validation.
- Many preview trades show very tight stop distances, sometimes near min_sl_distance=0.5, combined with fixed risk sizing and stop_first same-bar policy.
```

Decision:

```text
Reject current Phase148 range-model TP/SL configuration as a viable simulation rule.
Do not use these range-aware train/validation archives for strategy filter selection yet; their base bracket geometry fails before filtering.
Do not run test range-aware confirmation for this configuration.
The next research should be bracket diagnostics/calibration, not signal filtering.
No Phase134. No paper shadow. No live trading.
```

Recommended next phase:

```text
Phase150A — Range bracket geometry audit for pivot sequence archive
```

Recommended controls for Phase150A:

```text
1. ATR mode control inside the same archive script:
   --range-bracket-mode atr
   This should roughly reproduce the ATR baseline and proves the archive/prediction path is not the source of damage.

2. Range model diagnostics:
   distribution of tp_distance/sl_distance, min-distance hits, same-bar stop rate, invalid bracket rate, side/month breakdown.

3. Validation-only bracket grid:
   min_sl_distance: 0.5, 2, 5, 10, 15
   min_tp_distance: 0.5, 2, 5
   max_tp_atr/max_sl_atr alternatives
   use_1d_tp_cap 0/1
   range_fallback skip/atr
   same_bar_policy stop_first/tp_first as sensitivity only

4. Test remains untouched until a validation-selected bracket policy exists.
```

## Phase150A range bracket geometry audit implemented — 2026-09-20

Implemented the next diagnostic phase after Phase148C showed catastrophic range-model TP/SL results on train and validation.

Implemented:

```text
scripts/audit_pivot_sequence_range_bracket_geometry.py
GUI: Audit sequence range bracket geometry
```

Purpose:

```text
Replay already-archived Phase148 predictions under alternative bracket policies without retraining and without changing model predictions.
```

This phase includes an ATR-control policy inside the same archive replay path:

```text
range_bracket_mode=atr
```

and range policies over:

```text
range_bracket_modes
range_fallbacks
use_1d_tp_cap
min_tp_distance
min_sl_distance
max_tp_atr
max_sl_atr
same_bar_policy
allowed_sides
```

Outputs:

```text
run_logs\pivot_sequence_range_bracket_geometry\latest.json
run_logs\pivot_sequence_range_bracket_geometry\latest.html
run_logs\pivot_sequence_range_bracket_geometry\latest_grid.csv
run_logs\pivot_sequence_range_bracket_geometry\latest_best_trades.csv
```

Anti-overfit rule:

```text
Run on validation first.
Select bracket policy only from validation.
Test remains confirmation-only.
No paper/live/Phase134.
```

Verification:

```text
python -m py_compile scripts/audit_pivot_sequence_range_bracket_geometry.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_range_bracket_geometry.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Phase150A range bracket geometry audit result — ATR control wins, range adds no edge — 2026-09-20

The owner ran Phase150A on the validation Phase148 prediction archive.

Input:

```text
predictions_path : run_logs\pivot_pattern_sequence_wavenet_range_archive_validation\latest_predictions.parquet
flat_path        : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
split_name       : validation
evaluated_rows   : 3264
policies         : 735
score_metric     : drawdown_adjusted
min_trades       : 30
```

Best policy:

```text
policy_key        : mode=atr|fallback=skip|use1d=0|min_tp=0.5|min_sl=0.5|max_tp_atr=0|max_sl_atr=0|min4h=0|min1d=0|same=stop_first
range_bracket_mode: atr
trades            : 110
BUY / SELL        : 70 / 40
wins / losses     : 62 / 48
win_rate          : 56.3636%
final_balance     : 108.7914207603
return_percent    : +8.7914207603%
total_cash_pnl    : +8.7914207603
profit_factor     : 1.2554081199
max_drawdown_cash : 5.9715931205
BUY PnL           : -1.8550476298
SELL PnL          : +10.6464683900
positive_months   : 2
negative_months   : 0
pass_gate         : 1
```

Baseline ATR policy is identical to the best policy:

```text
baseline_atr_policy.rank = 1
baseline_atr_policy.PF   = 1.2554081199
```

Top-15 policies were all ATR variants. The `min_tp_distance` / `min_sl_distance` values did not change the ATR result because actual ATR distances were already larger than those minima:

```text
avg_tp_distance    : 31.0171
avg_sl_distance    : 31.0171
median_tp_distance : 31.6098
median_sl_distance : 31.6098
min_sl_hits        : 0
min_tp_hits        : 0
```

Best non-ATR range-enhanced policy in top list:

```text
policy_key        : mode=range_capped|fallback=atr|use1d=0|min_tp=0.5|min_sl=15|max_tp_atr=2|max_sl_atr=1.25|min4h=0|min1d=0|same=stop_first
rank              : 16
trades            : 124
BUY / SELL        : 77 / 47
wins / losses     : 66 / 58
final_balance     : 106.7674592914
return_percent    : +6.7674592914%
profit_factor     : 1.1439634226
max_drawdown_cash : 9.7927443251
BUY PnL           : -5.2818947734
SELL PnL          : +12.0493540648
positive_months   : 1
negative_months   : 1
pass_gate         : 1
```

Interpretation:

```text
- The Phase148 prediction/archive replay path is healthy because ATR-control exactly reproduces the earlier positive validation ATR result.
- Current range-model TP/SL does not add edge on validation; the best overall policy is pure ATR, not range.
- A range_capped+ATR-fallback policy with min_sl=15 is less catastrophic than raw range, but it is still worse than ATR and still depends on SELL while BUY is negative.
- Since ATR-control is the validation-selected best policy and that same ATR policy already failed test, the candidate fails validation→test confirmation.
```

Existing test confirmation for the same ATR policy:

```text
ATR test for rebuilt raw Option B 24k:
  final_balance : 90.7052413035
  return        : -9.2947586965%
  PF            : 0.8270058072
  maxDD         : 10.7624722054
  BUY PnL       : -5.3900375011
  SELL PnL      : -3.9047211954
```

Decision:

```text
Reject the rebuilt raw Option B 24k candidate.
Reject current range-model TP/SL as an improvement over ATR.
Do not run paper/live/Phase134.
Do not proceed to signal-filtering on the failed range archive as if it were a viable base.
```

Allowed diagnostic if the owner wants to continue investigating range:

```text
Confirm the best non-ATR validation policy on test exactly once:
mode=range_capped, fallback=atr, use1d=0, min_tp=0.5, min_sl=15, max_tp_atr=2, max_sl_atr=1.25, same=stop_first.
This is diagnostic only because it was rank 16, not the best validation policy.
```

Recommended strategic next phase:

```text
Phase151A — Pivot sequence walk-forward / seed-repeatability validation
```

Rationale:

```text
The model shows validation-only edge and test failure. The next proof must be walk-forward/repeated-seed validation, not more test-aware tuning.
```

## Phase151A Option B seed transfer validation implemented — 2026-09-20

Implemented the repeatability/transfer audit requested after Phase150A.

Implemented:

```text
scripts/run_pivot_sequence_option_b_seed_transfer_validation.py
GUI: Run Option B seed transfer validation
```

Protocol:

```text
For each seed:
  train raw Option B with explicit --random-seed
  run validation ATR PnL backtest
  run test ATR PnL backtest
  select only by validation score
  report test confirmation/pass-fail
```

Default seeds:

```text
20260919,20260920,20260921
```

Outputs:

```text
run_logs\pivot_sequence_option_b_seed_transfer\latest.json
run_logs\pivot_sequence_option_b_seed_transfer\latest.html
run_logs\pivot_sequence_option_b_seed_transfer\latest.csv
```

Verification:

```text
python -m py_compile scripts/run_pivot_sequence_option_b_seed_transfer_validation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_option_b_seed_transfer.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase151A trainer report bug fixed / resume existing seed models — 2026-09-20

The owner started Phase151A. The first seed model (`20260919`) trained and saved its model artifacts, but the trainer crashed while building the JSON report:

```text
[X] TypeError: OptionBReport.__init__() missing 1 required positional argument: 'random_seed'
```

Root cause:

```text
Phase147E added `random_seed` to the OptionBReport dataclass, but one report construction path did not pass `random_seed=int(args.random_seed)`.
```

Important state:

```text
The model artifact was saved before the report crash:
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m_seed_20260919\v1_model.keras
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m_seed_20260919\v1_training.json
```

Fixes implemented:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
  - OptionBReport construction now includes random_seed.

scripts/run_pivot_sequence_option_b_seed_transfer_validation.py
  - added --skip-existing-models {0,1}, default=1.
  - If a seed model already has v*_training.json, Phase151A skips retraining that seed and runs validation/test backtests.
```

GUI update:

```text
Run Option B seed transfer validation
  Skip existing models = 1/0
```

Recommended recovery action:

```text
Replace with the fixed zip and rerun the same Phase151A command.
The script should detect the existing seed_20260919 model and continue without retraining it.
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/run_pivot_sequence_option_b_seed_transfer_validation.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_seed_transfer.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Phase151A execution result — seed transfer failed — 2026-09-21

The owner ran Phase151A with three explicit seeds:

```text
20260919
20260920
20260921
```

The validation-selected seed was:

```text
selected_seed     : 20260921
selected_model_id : gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m_seed_20260921
selection_metric  : drawdown_adjusted
```

Selected seed validation result:

```text
validation_trades          : 103
validation_final_balance   : 107.4354957611
validation_return_percent  : +7.4354957611%
validation_profit_factor   : 1.2310390020
validation_max_drawdown    : 5.5600713875
validation_total_cash_pnl  : +7.4354957611
validation_buy_cash_pnl    : +0.1865227161
validation_sell_cash_pnl   : +7.2489730450
validation_positive_months : 1
validation_negative_months : 2
validation_pass_gate       : 1
```

Selected seed test result:

```text
test_trades          : 104
test_final_balance   : 93.2596575995
test_return_percent  : -6.7403424005%
test_profit_factor   : 0.8213467893
test_max_drawdown    : 10.0037166505
test_total_cash_pnl  : -6.7403424005
test_buy_cash_pnl    : -1.3009957153
test_sell_cash_pnl   : -5.4393466852
test_positive_months : 1
test_negative_months : 1
test_pass_gate       : 0
transfer_pass_gate   : 0
```

All seed results:

```text
seed 20260921:
  validation PF/final : 1.2310 / 107.4355
  test PF/final       : 0.8213 / 93.2597
  transfer_pass       : 0

seed 20260920:
  validation PF/final : 1.0051 / 100.2053
  test PF/final       : 0.9510 / 97.7156
  transfer_pass       : 0

seed 20260919:
  validation PF/final : 0.9919 / 99.6772
  test PF/final       : 0.8707 / 93.9395
  transfer_pass       : 0
```

Interpretation:

```text
Phase151A failed. The best validation seed did not transfer to test.
The only seed with validation pass gate (20260921) failed test badly.
No seed passed transfer_pass_gate.
```

Decision:

```text
Reject raw Option B 24k seed-repeatability route as a trading candidate.
Do not continue with Step 4 archive/filtering for this Option B family as a production path.
Any future pivot-sequence work needs target/label/architecture or walk-forward redesign, not more blind seed retrains.
No Phase134. No paper shadow. No live trading.
```

## Phase150A best non-ATR test confirmation failed — 2026-09-21

The owner ran the optional diagnostic test confirmation for the best non-ATR validation policy from Phase150A.

Policy:

```text
range_bracket_mode : range_capped
range_fallback     : atr
use_1d_tp_cap      : 0
min_tp_distance    : 0.5
min_sl_distance    : 15
max_tp_atr         : 2.0
max_sl_atr         : 1.25
same_bar_policy    : stop_first
```

Validation rank-16 result was:

```text
validation_final_balance : 106.7675
validation_PF            : 1.1440
validation_maxDD         : 9.7927
```

Test confirmation result:

```text
eval_split        : test
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
trades            : 157
BUY / SELL trades : 50 / 107
wins / losses     : 74 / 83
win_rate          : 47.1338%
final_balance     : 88.0744190317
return_percent    : -11.9255809683%
total_cash_pnl    : -11.9255809683
profit_factor     : 0.8215049757
max_drawdown_cash : 15.8457758848
BUY PnL           : -5.7357534232
SELL PnL          : -6.1898275451
monthly           : 2026-07 -8.6762935082, 2026-08 -3.2492874601
positive_months   : 0
negative_months   : 2
```

Comparison to ATR test for rebuilt raw Option B:

```text
ATR test:
  final_balance : 90.7052
  PF            : 0.8270
  maxDD         : 10.7625

Best non-ATR test:
  final_balance : 88.0744
  PF            : 0.8215
  maxDD         : 15.8458
```

Interpretation:

```text
The best non-ATR validation policy failed test and was slightly worse than ATR test.
This closes the current range-rescue attempt for the rebuilt Option B candidate.
```

Decision:

```text
Reject current range_capped + fallback=atr policy.
Range TP/SL is not a rescue path for this candidate.
No Phase134. No paper shadow. No live trading.
```

## Phase152A pivot label/target stability audit implemented — 2026-09-21

Implemented the requested Phase152A after Phase151A showed seed-transfer failure.

Implemented:

```text
scripts/audit_pivot_label_target_stability.py
GUI: Audit pivot label/target stability
```

The audit consumes the pivot sequence flat file and optional tensor meta file so it can inspect the exact sampled universe used by Option B models.

It reports:

```text
- SELL/HOLD/BUY action distribution by split and month
- top_zone and bottom_zone rates
- future_up_r / future_down_r distribution
- target_buy_r / target_sell_r distribution
- PSI drift vs train
- monthly worst drift
- sensitivity to lookahead_bars, pivot_move_atr, pivot_zone_atr, min_direction_edge
```

Outputs:

```text
run_logs\pivot_label_target_stability\latest.json
run_logs\pivot_label_target_stability\latest.html
run_logs\pivot_label_target_stability\latest_splits.csv
run_logs\pivot_label_target_stability\latest_monthly.csv
run_logs\pivot_label_target_stability\latest_sensitivity.csv
```

Verification:

```text
python -m py_compile scripts/audit_pivot_label_target_stability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_label_target_stability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase152A result — action labels stable, payoff targets drift by regime — 2026-09-21

The owner ran Phase152A on the exact Option B 24k sampled universe from `pivot_pattern_sequence_tensor_latest_meta.npz`.

Input/universe:

```text
flat_path        : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
meta_path        : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
sampled_universe : meta_sample_indices
flat_rows        : 53197
sampled_rows     : 24000
train/val/test   : 16800 / 3264 / 3264
period           : 2025-11-28 17:05:00+00:00 → 2026-08-06 19:20:00+00:00
```

Current label config:

```text
lookahead_bars     : 48
pivot_move_atr     : 0.75
pivot_zone_atr     : 0.35
recent_window_bars : 48
min_direction_edge : 1.10
```

Current target counts:

```text
SELL : 2411
HOLD : 19605
BUY  : 1984
```

Action-label distribution by split:

```text
Train      SELL=10.1369%  HOLD=82.0357%  BUY=7.8274%
Validation SELL= 9.1299%  HOLD=82.9044%  BUY=7.9657%
Test       SELL=10.7537%  HOLD=78.6765%  BUY=10.5699%
```

Action-label drift:

```text
validation_psi_vs_train = 0.0011693337
test_psi_vs_train       = 0.0100065951
```

Interpretation:

```text
The action labels themselves are not showing severe split-level drift. SELL/HOLD/BUY proportions are broadly stable from train to validation/test. The very high `max_monthly_psi_vs_train=2.0860` comes from 2025-11, which is only a tiny partial month at the start of the sampled window and should not be overinterpreted alone.
```

The important target drift is in the payoff targets:

```text
Top sensitivity rows show:
train_buy_r_mean      ≈ -0.0352
validation_buy_r_mean ≈ -0.0586
test_buy_r_mean       ≈ +0.0167

train_sell_r_mean      ≈ +0.0352
validation_sell_r_mean ≈ +0.0586
test_sell_r_mean       ≈ -0.0167
```

Interpretation:

```text
The market regime flips from train/validation being slightly SELL-favorable to test being slightly BUY-favorable in the continuous R targets, even though categorical label counts look stable. This explains the repeated pattern:
validation SELL edge looks good, then test SELL edge fails.
```

Sensitivity result:

```text
Most stable label configs are dominated by lookahead_bars=24 rather than the current 48.
The lowest drift row:
  lookahead_bars      : 24
  pivot_move_atr      : 0.75
  pivot_zone_atr      : 0.25
  min_direction_edge  : 1.0
  train actionable    : 6.6845%
  validation actionable: 6.8627%
  test actionable      : 7.6593%
  drift_score          : 0.1591275985

A denser but still stable candidate:
  lookahead_bars      : 24
  pivot_move_atr      : 0.5
  pivot_zone_atr      : 0.5
  min_direction_edge  : 1.25
  train actionable    : 23.7381%
  validation actionable: 23.0392%
  test actionable      : 26.8689%
  drift_score          : 0.1592708572
```

Decision:

```text
Phase152A does not approve any strategy.
It shows the current label counts are reasonably stable, but the payoff/R-target regime changes sign between validation and test.
More blind training of the same target is not justified.
```

Recommended next phase:

```text
Phase153A — Pivot Target Redesign Candidate Build/Audit
```

Recommended target candidates:

```text
Candidate C1 conservative:
  lookahead_bars     = 24
  pivot_move_atr     = 0.75
  pivot_zone_atr     = 0.25
  min_direction_edge = 1.0
  Expected: fewer but more stable actionable labels.

Candidate C2 denser stable:
  lookahead_bars     = 24
  pivot_move_atr     = 0.5
  pivot_zone_atr     = 0.5
  min_direction_edge = 1.25
  Expected: more actionable labels while keeping low drift.
```

Required anti-overfit rule:

```text
Build tensors for C1/C2, run health audits, train only as diagnostic, and evaluate validation/test transfer. Do not tune on test. No Phase134/paper/live.
```

## Phase153A pivot target redesign candidate build/audit implemented — 2026-09-21

The owner approved the next diagnostic step after Phase152A showed stable categorical labels but validation-to-test payoff/R-target regime drift.

Implemented:

```text
scripts/run_pivot_target_redesign_candidate_audit.py
GUI: Build/audit pivot target redesign candidates
```

Default target candidates are the two Phase152A recommendations:

```text
C1 stable:
  lookahead_bars     : 24
  pivot_move_atr     : 0.75
  pivot_zone_atr     : 0.25
  min_direction_edge : 1.0

C2 dense:
  lookahead_bars     : 24
  pivot_move_atr     : 0.5
  pivot_zone_atr     : 0.5
  min_direction_edge : 1.25
```

Phase153A now does the full candidate build/audit chain from one dashboard command:

```text
1. Build candidate sequence tensors with candidate-specific output names:
   pivot_pattern_sequence_tensor_c1_stable_latest
   pivot_pattern_sequence_tensor_c2_dense_latest

2. Run official Phase145A sequence tensor health audit on each candidate tensor.

3. Run Phase152A label/target stability audit on each candidate flat/meta universe.

4. Write an aggregate Phase153A report:
   run_logs\pivot_target_redesign_candidates\latest.json
   run_logs\pivot_target_redesign_candidates\latest.html
   run_logs\pivot_target_redesign_candidates\latest.csv
```

Important diagnostic gate:

```text
candidate_ready_for_training_gate =
  tensor_health == PASS
  and validation/test label PSI <= threshold
  and no validation-to-test payoff sign flip in target_buy_r/target_sell_r means
```

This is intentionally stricter than a label-count audit. C1/C2 may stabilize action-label density, but `target_buy_r` / `target_sell_r` are still continuous payoff targets and can still flip regime. Phase153A reports that explicitly instead of hiding it behind better class balance.

GUI command added:

```text
Build/audit pivot target redesign candidates
```

Key GUI fields:

```text
Candidates                 : C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25
Build max samples          : 0      # full tensor build
Audit max samples          : 24000  # same diagnostic sampled universe as Phase152A
Health full scan           : 1
Skip existing tensors      : 0
Output dir                 : run_logs/pivot_target_redesign_candidates
```

Recommended GUI execution:

```text
Dashboard → AI → Build/audit pivot target redesign candidates → Run
```

Equivalent PowerShell command:

```powershell
python -u scripts\run_pivot_target_redesign_candidate_audit.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --source-mode storage `
  --candidates "C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25" `
  --recent-window-bars 48 `
  --window-size 100 `
  --sample-stride 1 `
  --build-max-samples 0 `
  --audit-max-samples 24000 `
  --include-source-5m-features 1 `
  --max-features 0 `
  --dtype float16 `
  --axis-normalization robust `
  --feature-clip 8 `
  --chunk-size 512 `
  --max-tensor-mb 8192 `
  --health-full-scan 1 `
  --health-max-scan-samples 0 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --psi-warning-threshold 0.20 `
  --storage-root datasets `
  --output-dir run_logs\pivot_target_redesign_candidates `
  --report-title "Phase153A pivot target redesign candidate build/audit"
```

Verification in sandbox:

```text
python -m py_compile scripts/run_pivot_target_redesign_candidate_audit.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_target_redesign_candidate_audit.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_target_redesign_candidate_audit.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 45 passed
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
No training approval until C1/C2 tensor health and stability are reviewed.
```

## Phase153A result — C1/C2 tensors healthy, labels stable, payoff sign-flip remained — 2026-09-21

The owner ran Phase153A for the two target redesign candidates from Phase152A.

Candidates:

```text
C1 stable:
  lookahead_bars     : 24
  pivot_move_atr     : 0.75
  pivot_zone_atr     : 0.25
  min_direction_edge : 1.0

C2 dense:
  lookahead_bars     : 24
  pivot_move_atr     : 0.5
  pivot_zone_atr     : 0.5
  min_direction_edge : 1.25
```

Both candidate tensors were built and passed health:

```text
C1 tensor shape  : [53098, 100, 140]
C2 tensor shape  : [53098, 100, 140]
health_status    : PASS for both
nonfinite_cells  : 0 for both
health_max_abs   : 8.0 for both
health_errors    : []
health_warnings  : []
```

Both candidates passed label-count stability:

```text
C1 validation/test PSI : 0.0010691657 / 0.0073619577
C2 validation/test PSI : 0.0014521958 / 0.0071221864
label_stability_pass_gate : 1 for both
```

Actionable density:

```text
C1 train/validation/test actionable : 6.6845% / 6.8627% / 7.6593%
C2 train/validation/test actionable : 23.7381% / 23.0392% / 26.8689%
```

Critical result:

```text
Both candidates still have the same payoff/R sign flip:

train_buy_r_mean      = -0.0352140814
validation_buy_r_mean = -0.0586298741
test_buy_r_mean       = +0.0167183634

train_sell_r_mean      = +0.0352140814
validation_sell_r_mean = +0.0586298741
test_sell_r_mean       = -0.0167183634

buy_r_sign_flip  = 1
sell_r_sign_flip = 1
```

Final gates:

```text
C1 candidate_ready_for_training_gate = 0
C2 candidate_ready_for_training_gate = 0
training_ready_candidates            = 0
```

Interpretation:

```text
Phase153A confirms that the C1/C2 label definitions improve/maintain label-count stability, but do not solve the actual payoff-target regime drift.
The problem is no longer categorical label distribution. It is continuous payoff/R target instability.
```

Decision:

```text
Do not train Option B on C1/C2 as the next step.
Do not proceed with C1/C2 model training just because tensor health and label PSI passed.
The next research phase should redesign the tradable payoff/first-hit target itself.
```

Recommended next phase:

```text
Phase154A — Pivot Payoff/Trade-Outcome Target Redesign Audit
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase154A pivot payoff / trade-outcome target redesign audit implemented — 2026-09-21

After Phase153A showed that C1/C2 were label-stable but not payoff-stable, Phase154A was implemented to audit tradable first-hit/barrier payoff targets before any new training.

Implemented:

```text
scripts/audit_pivot_payoff_target_redesign.py
GUI: Audit pivot payoff target redesign
```

Purpose:

```text
Find a more reliable pivot target by auditing trade-outcome definitions:
BUY wins if upside TP barrier hits before downside SL barrier.
SELL wins if downside TP barrier hits before upside SL barrier.
HOLD otherwise.
```

Default candidate grid:

```text
B1:balanced_24_rr1:24:0.35:0.75:0.75:0.0
B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1
B3:dense_24_half_atr:24:0.50:0.50:0.50:0.0
B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1
B5:short_12_rr1:12:0.35:0.75:0.75:0.0
B6:wide_36_rr1:36:0.35:0.75:0.75:0.0
```

The audit reports:

```text
label_stability_pass_gate
payoff_stability_pass_gate
candidate_ready_for_tensor_gate
buy_score_sign_flip
sell_score_sign_flip
split/month action distributions
split/month buy/sell trade-outcome score means
```

Outputs:

```text
run_logs\pivot_payoff_target_redesign\latest.json
run_logs\pivot_payoff_target_redesign\latest.html
run_logs\pivot_payoff_target_redesign\latest_candidates.csv
run_logs\pivot_payoff_target_redesign\latest_splits.csv
run_logs\pivot_payoff_target_redesign\latest_monthly.csv
```

Verification:

```text
python -m py_compile scripts/audit_pivot_payoff_target_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 48 passed
```

Full ruff/black were unavailable in this sandbox image:

```text
python -m ruff ... → No module named ruff
python -m black ... → No module named black
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```
