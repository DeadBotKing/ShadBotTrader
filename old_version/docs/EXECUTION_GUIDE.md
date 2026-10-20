EXECUTION\_GUIDE

ShadBotTrader Enterprise AI Trading Platform

Execution Guide

Version: 1.0

Status: MASTER IMPLEMENTATION DOCUMENT

Purpose: اجرای کامل پروژه از صفر تا محصول نهایی

1\. هدف این سند



این سند مشخص می‌کند که یک تیم توسعه یا Agent Coding باید چگونه ShadBotTrader را از صفر تا محصول Enterprise نهایی پیاده‌سازی کند.



این سند صرفاً توضیح معماری نیست.



این سند مشخص می‌کند:



از کجا شروع شود

چه چیزی ابتدا ساخته شود

چه چیزی به چه چیزی وابسته است

ترتیب پیاده‌سازی چیست

هر فاز چه خروجی‌ای دارد

چه تست‌هایی باید نوشته شود

چه زمانی یک فاز Done محسوب می‌شود

چگونه از خراب شدن معماری جلوگیری شود

چگونه تغییرات Git مدیریت شوند

چگونه سیستم در نهایت اجرا و Deploy شود

2\. قانون اصلی اجرا



هیچ Developer یا Agent اجازه ندارد پروژه را به‌صورت آزادانه و بدون Roadmap پیاده‌سازی کند.



ترتیب اجرای پروژه:



Architecture

&#x20;   ↓

Core

&#x20;   ↓

Domain

&#x20;   ↓

Application

&#x20;   ↓

Pipeline

&#x20;   ↓

Engine

&#x20;   ↓

Service

&#x20;   ↓

Plugin

&#x20;   ↓

Event Bus

&#x20;   ↓

Data Platform

&#x20;   ↓

Feature Platform

&#x20;   ↓

AI Platform

&#x20;   ↓

Trading Platform

&#x20;   ↓

Portfolio Platform

&#x20;   ↓

Simulation Platform

&#x20;   ↓

Self Learning Platform

&#x20;   ↓

Project Intelligence Platform

&#x20;   ↓

GUI

&#x20;   ↓

SQL Server

&#x20;   ↓

Configuration

&#x20;   ↓

Logging

&#x20;   ↓

Testing

&#x20;   ↓

Deployment

&#x20;   ↓

Project Generator

&#x20;   ↓

Freeze

3\. وضعیت فعلی پروژه



هیچ پیاده‌سازی جدیدی هنوز انجام نشده است.



Git repository فعال است و شامل مستندات معماری (docs/) و کد مرجع

قدیمی (Legacy) می‌باشد.



Branch اصلی:



main



پروژه باید از این نقطه به بعد از صفر ساخته شود.



هدف، حفظ Architecture Contract است.



4\. قوانین مطلق

Rule 1 — No Placeholder



هیچ کدی با این هدف نوشته نشود:



pass



یا:



TODO



یا:



NotImplementedError



مگر اینکه واقعاً بخشی از یک abstraction رسمی باشد که implementation آن عمداً توسط معماری به لایه پایین‌تر واگذار شده است.



Rule 2 — No Fake Implementation



این موارد ممنوع هستند:



return True



برای شبیه‌سازی موفقیت.



یا:



return \[]



برای مخفی کردن نبود implementation.



یا:



print("implemented")



بدون implementation واقعی.



5\. قانون Dependency



Dependency باید همیشه از بیرون به داخل کنترل شود.



به‌صورت مفهومی:



Infrastructure

&#x20;      ↓

Application

&#x20;      ↓

Domain



Domain نباید به:



Database

Framework

HTTP

GUI

Filesystem

Broker

TensorFlow

PyTorch

SQLAlchemy



وابسته باشد.



6\. ترتیب پیاده‌سازی



هر مرحله باید این چرخه را طی کند:



Design

&#x20;↓

Contracts

&#x20;↓

Models

&#x20;↓

Interfaces

&#x20;↓

Implementation

&#x20;↓

Integration

&#x20;↓

Tests

&#x20;↓

Static Analysis

&#x20;↓

Runtime Test

&#x20;↓

Git Commit

7\. Phase 1–5



این پنج فاز Foundation معماری هستند.



شامل:



Phase 1

Architecture Principles





Phase 2

Dependency Rules





Phase 3

Domain Model





Phase 4

Project Tree





Phase 5

Framework Design



این بخش باید قبل از توسعه سیستم تثبیت شده باشد.



Framework نباید Domain را کنترل کند.



8\. Phase 6 — Pipeline Design



Pipeline مسئول orchestration جریان داده و پردازش است.



ساختار مفهومی:



Input

&#x20;↓

Validation

&#x20;↓

Normalization

&#x20;↓

Processing

&#x20;↓

Analysis

&#x20;↓

Decision

&#x20;↓

Output



Pipeline نباید business logic اصلی را داخل خود نگه دارد.



Pipeline فقط orchestrator است.



9\. Phase 7 — Engine Design



Engineها واحدهای computational اصلی هستند.



Engineهای اصلی:



DataEngine

FeatureEngineeringEngine

AIEngine

MarketEngine

NewsEngine

DecisionEngine

ExecutionEngine

PortfolioEngine

SimulationEngine

OptimizationEngine

ContextEngine

IntelligenceEngine

StorageEngine

GuiEngine



هر Engine باید:



contract مشخص

input مشخص

output مشخص

lifecycle مشخص

dependency مشخص

error handling

test suite



داشته باشد.



10\. Phase 8 — Service Design



Serviceها orchestration سطح application را انجام می‌دهند.



Service نباید جای Domain Model را بگیرد.



Service:



Receive Request

&#x20;↓

Validate

&#x20;↓

Load Domain Objects

&#x20;↓

Invoke Domain Logic

&#x20;↓

Persist

&#x20;↓

Publish Event

11\. Phase 9 — Plugin Architecture



Plugin system باید امکان اضافه کردن قابلیت بدون تغییر هسته را فراهم کند.



Plugin باید دارای:



Plugin Metadata

Plugin Contract

Plugin Lifecycle

Plugin Configuration

Plugin Dependencies

Plugin Registration

Plugin Discovery

Plugin Execution

Plugin Error Handling



باشد.



Plugin نباید مستقیماً implementation داخلی Core را دستکاری کند.



12\. Phase 10 — Event Bus



Event Bus مسئول ارتباط decoupled بین componentها است.



ساختار:



Publisher

&#x20;  ↓

Event Bus

&#x20;  ↓

Subscriber



Event باید immutable باشد.



Event باید دارای:



event\_id

event\_type

timestamp

source

payload

metadata



باشد.



13\. Phase 11 — Data Platform



Data Platform مسئول کل lifecycle داده است.



External Source

&#x20;↓

Collector

&#x20;↓

Raw Data

&#x20;↓

Validation

&#x20;↓

Normalization

&#x20;↓

Processed Data

&#x20;↓

Storage

&#x20;↓

Query



داده خام نباید overwrite شود.



14\. Phase 12 — Feature Platform



Feature Platform مسئول:



Feature Definition

Feature Calculation

Feature Validation

Feature Versioning

Feature Storage

Feature Retrieval



است.



Feature باید reproducible باشد.



Training و inference باید از feature definition یکسان استفاده کنند.



15\. Phase 13 — AI Platform



AI Platform شامل:



Dataset

&#x20;↓

Preprocessing

&#x20;↓

Feature Selection

&#x20;↓

Model

&#x20;↓

Training

&#x20;↓

Validation

&#x20;↓

Evaluation

&#x20;↓

Registry

&#x20;↓

Inference



است.



Model باید version داشته باشد.



Model بدون metadata معتبر نیست.



Metadata حداقل شامل:



model\_id

version

training\_dataset

features

target

algorithm

hyperparameters

metrics

created\_at



است.



16\. Phase 14 — Trading Platform



Trading Platform باید trading domain را پیاده کند.



شامل:



Market Data

&#x20;↓

Signal

&#x20;↓

Strategy

&#x20;↓

Risk Check

&#x20;↓

Order

&#x20;↓

Execution

&#x20;↓

Trade

&#x20;↓

Position



هیچ order نباید بدون risk validation وارد execution شود.



17\. Phase 15 — Portfolio Platform



Portfolio Platform مسئول:



Account

Balance

Positions

Exposure

PnL

Allocation

Risk

Performance



است.



Portfolio باید بتواند وضعیت تاریخی خود را reconstruct کند.



18\. Phase 16 — Simulation Platform



Simulation باید امکان اجرای سیستم بدون broker واقعی را فراهم کند.



Historical Data

&#x20;↓

Market Simulation

&#x20;↓

Strategy

&#x20;↓

Risk

&#x20;↓

Order Simulation

&#x20;↓

Execution Simulation

&#x20;↓

Portfolio

&#x20;↓

Metrics



Simulation نباید business logic متفاوتی نسبت به Live Trading داشته باشد.



تا حد امکان باید از همان interfaces استفاده شود.



19\. Phase 17 — Self Learning Platform



Self Learning شامل:



Performance Analysis

&#x20;↓

Error Analysis

&#x20;↓

Model Evaluation

&#x20;↓

Knowledge Extraction

&#x20;↓

Parameter Optimization

&#x20;↓

Experiment

&#x20;↓

Validation

&#x20;↓

Promotion



است.



هیچ model جدیدی نباید مستقیماً وارد production شود.



20\. Phase 18 — Project Intelligence Platform



این بخش یکی از مهم‌ترین اجزای ShadBotTrader است.



هدف:



ShadBotTrader باید بتواند خودش ساختار، کد، معماری، dependency و وضعیت پروژه را بفهمد.



Pipeline:



Workspace

&#x20;↓

Snapshot

&#x20;↓

Analysis

&#x20;↓

Evolution

&#x20;↓

Insight

&#x20;↓

Recommendation

&#x20;↓

Decision

21\. Project Intelligence — Scanner Layer



Scannerها:



ProjectScanner

ASTScanner

GitScanner

ConfigScanner

DependencyScanner

PackageScanner

StatisticsScanner

RoadmapScanner

DecisionScanner

TodoScanner



هر Scanner یک aspect مشخص از workspace را تحلیل می‌کند.



22\. Project Intelligence — Models



مدل‌های اصلی:



ProjectSnapshot

ProjectStatistics

ProjectContext

Roadmap

Decision

23\. Project Intelligence — Builders



Builderها:



SnapshotBuilder

ContextBuilder

RoadmapBuilder

StatisticsBuilder

DocumentationBuilder



هستند.



24\. Project Intelligence — Export



خروجی باید بتواند تولید کند:



Markdown

JSON

HTML

PDF

25\. Project Intelligence Runtime



Runtime مسئول اجرای intelligence pipeline است.



نباید scannerها را به‌صورت hard-coded و uncontrolled مدیریت کند.



باید orchestration کنترل‌شده داشته باشد.



26\. Project State



Project Intelligence باید state پایدار تولید کند.



ساختار:



project\_state/

&#x20;   generated/

&#x20;   archive/



Generated state شامل:



ProjectSnapshot.md

ProjectSnapshot.json

ChatGPT\_Context.md

Architecture.md

Roadmap.md

Decisions.md

Todo.md

Statistics.json

DependencyGraph.json



است.



27\. هدف ChatGPT\_Context



این فایل باید مهم‌ترین handoff artifact پروژه باشد.



باید بتواند وضعیت فعلی را توضیح دهد:



Project Identity

Current Architecture

Current Phase

Completed Phases

Current Implementation

Files

Dependencies

Decisions

Constraints

Known Issues

Roadmap

Next Action



هدف:



New Chat

&#x20;↓

Send ChatGPT\_Context.md

&#x20;↓

Immediate Project Understanding

&#x20;↓

Continue Development

28\. Phase 19 — GUI Architecture



GUI نباید business logic داشته باشد.



ساختار:



GUI

&#x20;↓

Application

&#x20;↓

Domain



GUI صرفاً presentation layer است.



29\. Phase 20 — SQL Server Schema



Database باید domain-driven طراحی شود.



Schema باید برای مواردی مثل:



Market

Trading

Portfolio

Orders

Trades

Positions

Models

Experiments

Features

Events

Audit

Configuration



طراحی شود.



Database schema نباید Domain Model را به ORM-specific design تبدیل کند.



30\. Phase 21 — Configuration System



Configuration باید متمرکز باشد.



منابع configuration:



Defaults

&#x20;↓

Config File

&#x20;↓

Environment Variables

&#x20;↓

Runtime Overrides



Secrets نباید داخل Git ذخیره شوند.



31\. Phase 22 — Logging System



Logging باید structured باشد.



حداقل:



DEBUG

INFO

WARNING

ERROR

CRITICAL



هر log مهم باید context داشته باشد.



مانند:



component

operation

request\_id

event\_id

timestamp

error

32\. Phase 23 — Testing Architecture



تست‌ها باید چند سطح داشته باشند:



Unit Tests

Integration Tests

Contract Tests

Pipeline Tests

Engine Tests

Service Tests

End-to-End Tests

Simulation Tests

Architecture Tests



هر feature جدید باید test داشته باشد.



33\. Quality Gate



هر تغییر باید حداقل:



python -m ruff check .

python -m black .

python -m mypy src

python -m pytest



را با موفقیت پشت سر بگذارد.



تا زمانی که green نشده:



Commit ممنوع

34\. Phase 24 — Deployment Architecture



Deployment باید reproducible باشد.



باید مشخص شود:



Environment

Configuration

Dependencies

Database

Storage

Models

Services

Monitoring

Logging

Backup

Recovery

35\. Phase 25 — PowerShell Project Generator



یک generator باید بتواند ساختار استاندارد پروژه را ایجاد کند.



هدف:



New Project

&#x20;↓

Standard Architecture

&#x20;↓

Standard Files

&#x20;↓

Standard Config

&#x20;↓

Standard Tests

&#x20;↓

Ready Workspace



Generator نباید state یا business logic production را تولید کند.



36\. Phase 26 — Integration Hardening



در این مرحله تمام platformها باید integration شوند.



بررسی:



Core

Domain

Application

Infrastructure

Pipeline

Engines

Services

Plugins

Events

Data

Features

AI

Trading

Portfolio

Simulation

Self Learning

Project Intelligence

GUI

Database

Config

Logging

Testing

Deployment



هیچ subsystem نباید isolated باقی بماند.



37\. Phase 27 — Production Readiness



قبل از Freeze:



Architecture Audit

Dependency Audit

Security Audit

Performance Audit

Data Integrity Audit

Testing Audit

Logging Audit

Configuration Audit

Deployment Audit

Documentation Audit



انجام شود.



38\. Phase 28 — Architecture Freeze



نسخه معماری باید freeze شود.



ShadBotTrader Architecture v1.0



پس از Freeze:



تغییر architecture فقط با:



Architecture Decision Record

&#x20;↓

Impact Analysis

&#x20;↓

Approval

&#x20;↓

Migration Plan

&#x20;↓

Implementation



مجاز است.



39\. Phase 28.x — Foundation Implementation



در وضعیت فعلی پروژه، هیچ implementation واقعی هنوز انجام نشده

است و Foundation قرار است از صفر ساخته شود.



ساختار هدف (Planned — هنوز موجود نیست):



src/ShadBotTrader/core/...

src/ShadBotTrader/domain/...

src/ShadBotTrader/application/...

src/ShadBotTrader/infrastructure/...



40\. Domain Core



ساختار هدف (Planned — هنوز موجود نیست):



domain/common/entity.py

domain/common/value_object.py

domain/market/candle.py

domain/market/symbol.py

domain/market/timeframe.py

domain/portfolio/account.py

domain/portfolio/balance.py

domain/prediction/prediction.py

domain/prediction/signal.py

domain/risk/risk_model.py

domain/trading/order.py

domain/trading/position.py

domain/trading/trade.py



41\. Application Runtime



ساختار هدف (Planned — هنوز موجود نیست):



application/app.py

application/application_state.py

application/bootstrap.py

application/runtime.py

application/service_registry.py

application/shutdown.py

application/startup.py



این فایل‌ها هنوز وجود ندارند و باید در Phase 28 پیاده‌سازی شوند.



42\. Infrastructure



Infrastructure باید مسئول implementationهای خارج از Domain باشد.



مانند:



Database

Filesystem

Network

External APIs

Broker

Message Transport

Model Storage

43\. Naming Convention



نام‌گذاری جدید باید یکدست شود.



ترجیح:



snake\_case



برای Python:



event\_bus.py

lifecycle\_manager.py

service\_registry.py

project\_snapshot.py



و:



PascalCase



برای classها.



44\. ممنوعیت Mixed Architecture



نباید همزمان این سبک‌ها را بدون دلیل استفاده کرد:



CamelCase filenames

snake\_case filenames

PascalCase filenames



از اینجا به بعد استاندارد Python حفظ شود.



45\. Git Workflow



هر Phase باید commit مشخص داشته باشد.



مثلاً:



Implement ShadBotTrader Core Foundation

Implement ShadBotTrader Domain Core

Implement Application Runtime Layer

Implement Pipeline Architecture

Implement Engine Layer

...



قبل از commit:



git status



بعد:



git add .

git commit -m "..."



و سپس:



git push

46\. Phase Completion Contract



هیچ Phase زمانی Complete نیست مگر اینکه:



\[ ] Architecture implemented

\[ ] Contracts implemented

\[ ] Models implemented

\[ ] Dependencies correct

\[ ] Integration complete

\[ ] Tests written

\[ ] Ruff green

\[ ] Black green

\[ ] Mypy green

\[ ] Pytest green

\[ ] Runtime verification successful

\[ ] Documentation updated

\[ ] Project state updated

\[ ] Git commit created

47\. توسعه با Agent



اگر Coding Agent پروژه را پیاده‌سازی می‌کند، Agent باید قبل از هر تغییر:



1\. Project State را بخواند

2\. Architecture را بخواند

3\. Current Phase را تشخیص دهد

4\. Existing Code را inspect کند

5\. Dependency Rules را بررسی کند

6\. تغییر حداقلی لازم را طراحی کند

7\. Implementation را انجام دهد

8\. Tests را اجرا کند

9\. Quality Gate را اجرا کند

10\. Project State را به‌روزرسانی کند

48\. Agent نباید حدس بزند



اگر Agent نداند:



این class برای چیست؟

این dependency چرا وجود دارد؟

این interface چه قراردادی دارد؟

این فایل بخشی از کدام subsystem است؟



نباید حدس بزند.



باید ابتدا:



Architecture

Project State

Code

Tests

Decisions



را بررسی کند.



49\. Self-Documentation



ShadBotTrader باید در طول development وضعیت خودش را به‌روزرسانی کند.



هر تغییر معماری مهم باید در:



Decisions.md

Architecture.md

Roadmap.md

Todo.md

ProjectSnapshot



ثبت شود.



50\. Evolution Model



Project Intelligence باید وضعیت پروژه را به شکل تاریخی نگه دارد.



Current State

&#x20;    ↓

Change

&#x20;    ↓

New State

&#x20;    ↓

Archive Previous State



بنابراین:



project\_state/archive/



نباید حذف شود.



51\. Recovery



اگر Chat جدید باز شد:



فایل زیر ارسال شود:



project\_state/generated/ChatGPT\_Context.md



و در صورت نیاز:



Architecture.md

Roadmap.md

Decisions.md

Todo.md

ProjectSnapshot.json



از روی این اطلاعات باید development ادامه پیدا کند.



52\. Definition of Done کل پروژه



ShadBotTrader زمانی نهایی محسوب می‌شود که:



Core                         DONE

Domain                       DONE

Application                  DONE

Infrastructure               DONE

Pipeline                     DONE

Engines                      DONE

Services                     DONE

Plugins                      DONE

Event Bus                    DONE

Data Platform                DONE

Feature Platform             DONE

AI Platform                  DONE

Trading Platform             DONE

Portfolio Platform           DONE

Simulation Platform          DONE

Self Learning Platform       DONE

Project Intelligence         DONE

GUI                          DONE

SQL Server                   DONE

Configuration                DONE

Logging                      DONE

Testing                      DONE

Deployment                   DONE

Project Generator            DONE

Documentation                DONE

Architecture Freeze          DONE

53\. Final Execution Order

STEP 01

Repository + Environment





STEP 02

Core Foundation





STEP 03

Domain





STEP 04

Application Runtime





STEP 05

Infrastructure





STEP 06

Pipeline





STEP 07

Engines





STEP 08

Services





STEP 09

Plugins





STEP 10

Event Bus





STEP 11

Data Platform





STEP 12

Feature Platform





STEP 13

AI Platform





STEP 14

Trading Platform





STEP 15

Portfolio Platform





STEP 16

Simulation





STEP 17

Self Learning





STEP 18

Project Intelligence





STEP 19

GUI





STEP 20

SQL Server





STEP 21

Configuration





STEP 22

Logging





STEP 23

Testing





STEP 24

Deployment





STEP 25

Project Generator





STEP 26

Integration Hardening





STEP 27

Production Readiness





STEP 28

Architecture Freeze

54\. مهم‌ترین دستور اجرای پروژه



Developer/Agent نباید از خودش تصمیم بگیرد که «حالا چه چیزی بسازم؟».



همیشه:



Read Architecture

&#x20;       ↓

Read Execution Guide

&#x20;       ↓

Read Current Project State

&#x20;       ↓

Identify Current Phase

&#x20;       ↓

Inspect Existing Implementation

&#x20;       ↓

Implement ONLY Current Scope

&#x20;       ↓

Run Quality Gate

&#x20;       ↓

Update Project State

&#x20;       ↓

Commit

&#x20;       ↓

Move To Next Phase

55\. وضعیت واقعی فعلی



در زمان ایجاد این سند، هیچ پیاده‌سازی جدیدی انجام نشده است:



Core Foundation              ✗

Domain Core                  ✗

Application Runtime          ✗

Project Intelligence         ✗



ریپو فعلی فقط شامل مستندات معماری (docs/) و کد مرجع قدیمی (Legacy)

است.



ساختار هدف Project Intelligence (Planned — هنوز موجود نیست):



src/ShadBotTrader/project/

&#x20;   core/

&#x20;   models/

&#x20;   builders/

&#x20;   exporters/

&#x20;   runtime/



project_state/

&#x20;   generated/

&#x20;   archive/



همه چیز باید از صفر پیاده‌سازی شود.



56\. قانون نهایی



هیچ‌کس نباید پروژه را از صفر دوباره طراحی کند.



اگر چیزی قبلاً در:



Architecture

Decision

Code

Tests

Project State



تعریف شده است، باید همان Contract حفظ شود.



اگر implementation با معماری فعلی ناسازگار بود:



Architecture wins.



اگر یک implementation قبلی اشتباه بود:



Detect

&#x20;↓

Document

&#x20;↓

Correct

&#x20;↓

Test

&#x20;↓

Record Decision



نه اینکه معماری جدید بدون بررسی ساخته شود.



END OF EXECUTION\_GUIDE

