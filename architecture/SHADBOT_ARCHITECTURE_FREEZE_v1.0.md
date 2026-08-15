# ShadBot — Enterprise AI Trading Platform
## Architecture Freeze v1.0

> این سند، قرارداد معماری نهایی است. از Phase 27 به بعد، فقط Implementation انجام می‌شود.
> هر تغییری در این سند = تغییر در قرارداد و نیازمند تصمیم صریح مالک است.

---

## Phase 1 — Architecture Principles ✅
طراحی اصول پایه معماری:
- Enterprise First
- Clean Architecture
- DDD
- SOLID
- Event Driven
- Plugin Based
- Dependency Injection
- Testability
- Scalability
- Production Ready

## Phase 2 — Dependency Rules ✅
قوانین وابستگی بین لایه‌ها:
- جهت وابستگی‌ها
- ممنوعیت Circular Dependency
- قوانین Import
- Layer Isolation

## Phase 3 — Domain Model ✅
طراحی کامل Domain:
- Market
- Trading
- Portfolio
- Prediction
- Risk
- News
- Common

## Phase 4 — Project Tree ✅
طراحی ساختار پوشه‌ها:
- src
- tests
- docs
- configs
- datasets
- scripts
- architecture

===== Freeze =====

## Phase 5 — Framework Design ✅
طراحی Framework اصلی:
- Bootstrap
- Runtime
- Lifecycle
- Container
- Event Bus
- Plugin System

## Phase 6 — Pipeline Design ✅
طراحی Pipelineهای پروژه:
- Training Pipeline
- Live Pipeline
- Replay Pipeline
- Backtest Pipeline
- Optimization Pipeline
- Dataset Pipeline
- Feature Pipeline

## Phase 7 — Engine Design ✅
طراحی Engineها:
- Data Engine
- Feature Engine
- AI Engine
- Market Engine
- Decision Engine
- Execution Engine
- Portfolio Engine
- Simulation Engine
- Intelligence Engine
- Optimization Engine
- Storage Engine
- Context Engine
- GUI Engine

## Phase 8 — Service Design ✅
طراحی Service Layer:
- Business Services
- Runtime Services
- Infrastructure Services
- Registration
- Discovery

## Phase 9 — Plugin Architecture ✅
سیستم Plugin:
- Plugin Lifecycle
- Discovery
- Loading
- Registration
- Isolation

## Phase 10 — Event Bus ✅
طراحی Event Driven System:
- Event
- Publisher
- Subscriber
- Dispatcher
- Async Design

## Phase 11 — Data Platform ✅
طراحی Data Platform:
- Dataset
- Market Data
- Import
- Export
- Validation
- Cleaning
- Storage

## Phase 12 — Feature Platform ✅
طراحی Feature Engineering:
- Indicators
- Multi TimeFrame
- Feature Store
- Pipelines

## Phase 13 — AI Platform ✅
طراحی AI Platform:
- Training
- Prediction
- Models
- Registry
- Evaluation
- Versioning

## Phase 14 — Trading Platform ✅
طراحی Trading:
- Orders
- Execution
- MT5
- Broker
- Trade Manager

## Phase 15 — Portfolio Platform ✅
مدیریت سرمایه:
- Balance
- Equity
- Risk
- Position Size
- Money Management

## Phase 16 — Simulation Platform ✅
شبیه‌سازی:
- Replay
- Backtest
- Walk Forward
- Paper Trading

## Phase 17 — Self Learning Platform ✅
یادگیری خودکار:
- Evaluation
- Retraining
- Improvement
- Feedback Loop

## Phase 18 — Project Intelligence Platform ✅
طراحی کامل PIP:
- Project Analysis
- Documentation
- Context Builder
- Snapshot
- Reports

## Phase 19 — GUI Architecture ✅
طراحی GUI:
- Dashboard
- Charts
- Monitoring
- Settings

## Phase 20 — SQL Server Schema ✅
طراحی Database:
- Tables
- Relations
- Indexes
- Versioning

## Phase 21 — Configuration System ✅
Config System:
- YAML
- Environment
- Validation
- Secrets

## Phase 22 — Logging System ✅
Logging:
- File
- Console
- Levels
- Rotation

## Phase 23 — Testing Architecture ✅
Testing:
- Unit
- Integration
- End-to-End
- Coverage

## Phase 24 — Deployment Architecture ✅
Deployment:
- Production
- Docker
- Windows Service
- Update Strategy

## Phase 25 — PowerShell Project Generator ✅
Project Generator:
- Folder Generation
- File Generation
- Bootstrap Scripts

## Phase 26 — Freeze v1.0 ✅
تمام معماری قفل شد.

## Phase 27 — Final Architecture Freeze ✅
نسخه نهایی معماری.
از این مرحله به بعد فقط Implementation انجام می‌شود.

---

# Implementation Roadmap

```
Architecture (Phase 1-27)  →  Implementation (Phase 28+)  →  Future Work (After PIP)
```

## Phase 28 — ENTER IMPLEMENTATION

### 28.1 Repository Foundation
### 28.2 Core Foundation
- Dependency Container
- Event Bus
- Plugin Base
- Lifecycle Manager
- Base Service

### 28.3 Infrastructure Foundation
- Infrastructure Layer
- Configuration
- Runtime Base

### 28.4 Domain Core
- Market
- Trading
- Portfolio
- Prediction
- Risk

### 28.5 Application Runtime
- Application
- Bootstrap
- Runtime
- Startup
- Shutdown
- Service Registry
- Application State

## Sprint P0 — Project Intelligence Platform
- Project Scanner
- AST Scanner
- Git Scanner
- Package Scanner
- Dependency Scanner
- Statistics Scanner
- Roadmap Scanner
- Decision Scanner
- Todo Scanner
- Snapshot Builder
- Context Builder
- Documentation Builder
- Markdown Exporter
- JSON Exporter
- HTML Exporter
- PDF Exporter
- Intelligence Runtime

## Future Development (به ترتیب)
1. Data Platform (Implementation)
2. Feature Platform (Implementation)
3. AI Platform (Implementation)
4. Trading Platform (Implementation)
5. Portfolio Platform (Implementation)
6. Simulation Platform (Implementation)
7. Self Learning Platform (Implementation)
8. GUI Platform
9. Production Deployment
10. ShadBot v1.0

---

# وضعیت میراث (Legacy) — کد فعلی ریپو

کد فعلی (XAUUSD، واگرایی MACD/RSI/StochAstic، الگوریتم ژنتیک، مدل‌های TF، ربات MT5)
به‌عنوان **مرجع دانش دامنه (Domain Knowledge Reference)** در نظر گرفته می‌شود و قرار است
در پلتفرم جدید بازطراحی/پورت شود، نه اینکه به‌صورت مستقیم ادامه یابد.
