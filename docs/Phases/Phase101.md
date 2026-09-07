# فاز ۱۰۱ — رفع live log آموزش از GUI روی Windows

**تاریخ:** 2026-09-07  
**وضعیت:** ✅ کامل  
**Commit:** `e5ca863`

---

## مشکل

اپراتور می‌خواست training از داخل GUI مثل قبل شروع شود و live log در Dashboard نمایش داده شود. اجرای مستقیم PowerShell با `python -u` خروجی داشت، اما GUI گاهی لاگ را نشان نمی‌داد یا فقط `waiting for first line` می‌ماند.

---

## مسیر واقعی GUI

```text
Dashboard POST /run
→ CommandBus.dispatch_async
→ AccountCommandHandlers.train_dual_models
→ CommandHandlers._run_script
→ scripts/run_dual_models.py
→ run_logs/train_dual_models.log
→ /api/log
→ پنل live output
```

---

## علت‌های پیدا شده

### 1) Race در `dispatch_async`

قبل از فاز ۱۰۱، وضعیت `_running` داخل thread پس‌زمینه set می‌شد. مرورگر بعد از POST سریع redirect می‌کرد؛ اگر GET بعد از redirect زودتر از thread اجرا می‌شد، صفحه فکر می‌کرد commandی running نیست و اصلاً پنل live-log را نمی‌ساخت.

### 2) مشکل Windows encoding/pipe

اسکریپت training متن فارسی و علامت‌های Unicode چاپ می‌کند:

```text
—  −  ·  فاز
```

`subprocess.Popen(..., text=True)` بدون `encoding` روی Windows می‌توانست با codepage legacy decode کند و log reader قبل از epoch اول fail شود.

### 3) write handle طولانی روی log file

در Windows خواندن همزمان فایلی که یک thread برای مدت طولانی با write handle باز نگه داشته، flaky است. `_run_script` فایل را تا پایان training باز نگه می‌داشت.

---

## تغییرات

### `src/ShadBotTrader/presentation/commands/bus.py`

- متد `_reserve()` اضافه شد.
- `dispatch_async()` قبل از برگشت، وضعیت running را synchronously set می‌کند.
- thread دیگر `dispatch()` را دوباره صدا نمی‌زند؛ handler رزروشده را در `_execute_reserved()` اجرا می‌کند.

### `src/ShadBotTrader/presentation/commands/handlers.py`

در `_run_script`:

```text
PYTHONUNBUFFERED=1
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
python -u scripts/run_dual_models.py
encoding='utf-8'
errors='replace'
```

و log file با appendهای کوتاه باز/بسته می‌شود تا `/api/log` بتواند وسط آموزش بخواند.

### `scripts/run_dual_models.py`

لاگ نمایشی score اصلاح شد:

```text
قبل: training: nothing / RANGE MODEL
بعد: training: trend_score(1D) / TREND_SCORE MODEL
```

همچنین target units برای score درست شد:

```text
score dimensionless -1..+1, NOT price offset
```

---

## تست‌ها

```text
tests/unit/presentation/test_commands.py
tests/integration/test_training_visibility.py
```

پوشش‌ها:

```text
- dispatch_async قبل از برگشت busy را set می‌کند
- _run_script UTF-8 و unbuffered است
- live log وسط run قابل خواندن است
```

---

## دستور اپراتور بعد از fix

Dashboard باید restart شود:

```powershell
Ctrl+C
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
```

بعد در GUI:

```text
Train a model
model=trend_score
dataset=1D
```

باید live output شامل `TRAINING`, `fold`, `batch`, `epoch` دیده شود.
