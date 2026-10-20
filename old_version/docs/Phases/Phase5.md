\# SHADBOTTRADER ENTERPRISE AI TRADING PLATFORM

\# PHASE 05 — FRAMEWORK DESIGN



Document ID:

SHADBOTTRADER-ARCH-P05



Phase:

05 / 26



Status:

FINAL BASELINE



Architecture Style:

Enterprise

Clean Architecture

Domain-Driven Design

Dependency Inversion

Modular Monolith

Desktop Runtime

Framework-Isolated Core





\# 1. PURPOSE



این Phase تکنولوژی‌ها، Frameworkها، Libraryها، Runtimeها و Technology Boundaryهای رسمی ShadBotTrader را تعیین می‌کند.



هدف:



&#x20;   1. تعیین Python Runtime

&#x20;   2. تعیین ML Stack

&#x20;   3. تعیین Data Processing Stack

&#x20;   4. تعیین Dataset Storage Format

&#x20;   5. تعیین Database Strategy

&#x20;   6. تعیین Broker/Data Provider Boundary

&#x20;   7. تعیین Configuration Technology

&#x20;   8. تعیین Logging Technology

&#x20;   9. تعیین Testing Stack

&#x20;   10. تعیین Code Quality Stack

&#x20;   11. تعیین Desktop GUI Technology

&#x20;   12. تعیین Serialization Formats

&#x20;   13. تعیین Technology Isolation Rules

&#x20;   14. جلوگیری از Framework Leakage

&#x20;   15. Freeze کردن Technology Baseline





\# 2. CORE DECISION



ShadBotTrader یک Python-based Enterprise Desktop Application است.



Frameworkها ابزار اجرای Architecture هستند، نه خود Architecture.



بنابراین:



&#x20;   Domain

&#x20;   Application

&#x20;   Core



باید تا حد ممکن Framework-independent باقی بمانند.





\# 3. PYTHON



Primary Language:



&#x20;   Python



Python Runtime:



&#x20;   Python 3.14+



نسخه دقیق Runtime در Environment/Project Configuration ثبت می‌شود.



تمام توسعه Production باید روی یک Python Version مشخص و قابل Reproduce انجام شود.





\# 4. PYTHON VERSION POLICY



نسخه Python نباید به صورت آزاد و بدون کنترل تغییر کند.



Version باید در:



&#x20;   pyproject.toml

&#x20;   environment configuration

&#x20;   documentation



ثبت شود.



هر تغییر Major/Minor Python باید به عنوان:



&#x20;   Compatibility Decision



بررسی شود.





\# 5. PACKAGE MANAGEMENT



Package Management:



&#x20;   pip



Dependency declaration:



&#x20;   pyproject.toml



تمام Dependencyهای Production باید Explicit باشند.



Dependencyهای بدون استفاده نباید در Project باقی بمانند.





\# 6. BUILD / PROJECT CONFIGURATION



مرجع اصلی Python Project:



&#x20;   pyproject.toml



این فایل باید شامل:



&#x20;   project metadata

&#x20;   Python requirement

&#x20;   dependencies

&#x20;   development dependencies

&#x20;   tool configuration



باشد.





\# 7. CODE QUALITY STACK



Official Quality Gate:



&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy

&#x20;   Pytest





\# 8. RUFF



Ruff مسئول:



&#x20;   linting

&#x20;   import validation

&#x20;   code quality rules

&#x20;   static checks



است.



Ruff باید بخشی از Quality Gate رسمی باشد.





\# 9. BLACK



Black مسئول:



&#x20;   deterministic code formatting



است.



Formatting نباید توسط Developerها به صورت سلیقه‌ای تغییر کند.





\# 10. MYPY



Mypy مسئول:



&#x20;   Static Type Checking



است.



Production Code باید Type Annotation مناسب داشته باشد.



هدف:



&#x20;   Strong typing

&#x20;   Detect contract violations

&#x20;   Detect invalid interfaces

&#x20;   Reduce runtime errors





\# 11. PYTEST



Pytest Framework رسمی Testing است.



Testing Layers:



&#x20;   Unit

&#x20;   Integration

&#x20;   System

&#x20;   Architecture





\# 12. QUALITY GATE



هیچ تغییر Production نباید Final محسوب شود مگر اینکه:



&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy

&#x20;   Pytest



با موفقیت اجرا شوند.





\# 13. DATA PROCESSING



Primary Data Stack:



&#x20;   NumPy

&#x20;   pandas





NumPy برای:



&#x20;   numerical computation

&#x20;   arrays

&#x20;   vectorized operations



است.





pandas برای:



&#x20;   tabular data

&#x20;   candle datasets

&#x20;   feature datasets

&#x20;   preprocessing



است.





\# 14. DATA PROCESSING RULE



pandas/NumPy فقط باید در Layerهایی استفاده شوند که Data Processing responsibility دارند.



Domain نباید DataFrame را به عنوان مدل اصلی Business استفاده کند.





\# 15. DOMAIN DATA MODEL



Domain باید از:



&#x20;   Entity

&#x20;   Value Object

&#x20;   Aggregate

&#x20;   Domain Model



استفاده کند.



DataFrame نباید جایگزین:



&#x20;   Candle

&#x20;   Trade

&#x20;   Position

&#x20;   Order

&#x20;   Prediction



شود.





\# 16. DATASET STORAGE



Primary historical dataset format:



&#x20;   Parquet





دلیل:



&#x20;   Columnar Storage

&#x20;   Compression

&#x20;   Efficient Read

&#x20;   Efficient Write

&#x20;   Large Dataset Support

&#x20;   Feature Dataset Support





\# 17. PARQUET LIBRARY



Official implementation:



&#x20;   PyArrow





PyArrow مسئول:



&#x20;   Parquet I/O

&#x20;   Schema

&#x20;   Columnar Storage

&#x20;   Dataset Operations





\# 18. DATASET ARCHITECTURE



Historical Data:



&#x20;   Provider

&#x20;      ↓

&#x20;   Raw Parquet

&#x20;      ↓

&#x20;   Processed Parquet

&#x20;      ↓

&#x20;   Feature Parquet





Datasetها نباید به صورت CSV به عنوان Storage اصلی Production استفاده شوند.





\# 19. CSV POLICY



CSV فقط برای:



&#x20;   Import

&#x20;   Export

&#x20;   Debugging

&#x20;   Small datasets



مجاز است.



CSV Storage اصلی Dataset Pipeline نیست.





\# 20. DATASET PARTITIONING



Datasetهای بزرگ باید امکان Partitioning داشته باشند.



Partitionهای پیشنهادی:



&#x20;   symbol

&#x20;   timeframe

&#x20;   date





اما Partition Strategy نهایی در Data Platform Phase مشخص خواهد شد.



Framework این امکان را محدود نمی‌کند.





\# 21. LARGE DATA PROCESSING



سیستم نباید برای Datasetهای بزرگ مجبور باشد تمام Dataset را در RAM Load کند.



Pipeline باید بتواند:



&#x20;   Chunk

&#x20;   Partition

&#x20;   Incremental Processing



را پشتیبانی کند.





\# 22. HISTORICAL DATA



Historical Dataset برای:



&#x20;   Training

&#x20;   Backtesting

&#x20;   Research

&#x20;   Feature Engineering

&#x20;   Model Evaluation



است.





\# 23. LIVE DATA



Live Data برای:



&#x20;   Current Market State

&#x20;   Feature Calculation

&#x20;   Prediction

&#x20;   Decision

&#x20;   Execution



است.





\# 24. LIVE DATA STORAGE MODEL



Live Data به صورت Runtime Buffer مدیریت می‌شود.



دو مفهوم مستقل:



&#x20;   Calculation Window



و:



&#x20;   Inference Window





مثال:



&#x20;   Calculation Window = 1000 candles



&#x20;   Inference Window = 500 candles





\# 25. FEATURE ENGINEERING STACK



Feature Engineering با:



&#x20;   pandas

&#x20;   NumPy



و در صورت نیاز:



&#x20;   technical-analysis libraries



انجام می‌شود.



اما Feature Definition باید در Domain/Feature قابل مدل‌سازی باشد.





\# 26. FEATURE ENGINEERING RULE



Framework Feature Engineering نباید Business Rule را مالک شود.



Feature Engine:



&#x20;   calculates



Domain:



&#x20;   defines meaning





\# 27. MACHINE LEARNING STACK



Primary ML Framework:



&#x20;   TensorFlow / Keras





Keras برای:



&#x20;   Model Definition

&#x20;   Training

&#x20;   Evaluation

&#x20;   Serialization

&#x20;   Inference



استفاده می‌شود.





\# 28. ML ARCHITECTURE



Domain:



&#x20;   Model

&#x20;   ModelVersion

&#x20;   TrainingRun

&#x20;   Evaluation



را تعریف می‌کند.



AIEngine:



&#x20;   TensorFlow

&#x20;   Keras



را اجرا می‌کند.





یعنی:



&#x20;   Domain AI

&#x20;        ↓

&#x20;   AIEngine

&#x20;        ↓

&#x20;   Keras / TensorFlow





\# 29. ML FRAMEWORK ISOLATION



این موارد نباید وارد Domain شوند:



&#x20;   tensorflow

&#x20;   keras

&#x20;   torch

&#x20;   sklearn implementation details





Domain فقط Contract/Model مفهومی خود را می‌شناسد.





\# 30. NUMPY AND TENSORFLOW



NumPy و TensorFlow می‌توانند در:



&#x20;   AIEngine

&#x20;   FeatureEngineeringEngine

&#x20;   DataEngine



استفاده شوند.



اما Domain نباید Tensor/ndarray-specific API داشته باشد.





\# 31. MODEL STORAGE



Model Artifact باید خارج از Source Code ذخیره شود.



ساختار مفهومی:



&#x20;   models/

&#x20;       <model-family>/

&#x20;           <version>/





Model Version باید:



&#x20;   deterministic

&#x20;   identifiable

&#x20;   traceable



باشد.





\# 32. MODEL METADATA



هر Model Version باید Metadata داشته باشد.



حداقل:



&#x20;   model\_id

&#x20;   version

&#x20;   training\_dataset\_version

&#x20;   feature\_set\_version

&#x20;   training\_configuration

&#x20;   evaluation\_result

&#x20;   creation\_timestamp





\# 33. TRAINING DATA LINEAGE



هر Model باید مشخص کند با چه Dataset و Feature Set ساخته شده است.



رابطه:



&#x20;   DatasetVersion

&#x20;         ↓

&#x20;   FeatureSetVersion

&#x20;         ↓

&#x20;   TrainingRun

&#x20;         ↓

&#x20;   ModelVersion





این Lineage برای جلوگیری از Training غیرقابل‌ردیابی الزامی است.





\# 34. DATABASE



Primary relational database:



&#x20;   SQLite



در Desktop V1 به عنوان Local Operational Database استفاده می‌شود.





\# 35. SQLITE RESPONSIBILITY



SQLite برای:



&#x20;   metadata

&#x20;   configuration state

&#x20;   model registry

&#x20;   dataset registry

&#x20;   training runs

&#x20;   execution records

&#x20;   portfolio state

&#x20;   application state



است.





\# 36. SQLITE LIMITATION



SQLite محل نگهداری اصلی:



&#x20;   Large Historical Market Dataset



نیست.



Dataset بزرگ:



&#x20;   Parquet



است.





\# 37. DATABASE ABSTRACTION



Domain/Application نباید به SQLite وابسته باشند.



Database implementation در:



&#x20;   Infrastructure/Database/





قرار می‌گیرد.





\# 38. ORM POLICY



ORM در Domain استفاده نمی‌شود.



اگر ORM در Infrastructure مورد نیاز باشد، انتخاب آن در همان Layer محدود می‌شود.



Domain Entity نباید ORM Entity شود.





\# 39. SERIALIZATION



Primary structured serialization:



&#x20;   JSON





برای:



&#x20;   configuration

&#x20;   metadata

&#x20;   API payloads

&#x20;   small artifacts

&#x20;   state exchange



است.





\# 40. PYDANTIC



Pydantic برای:



&#x20;   configuration validation

&#x20;   DTO validation

&#x20;   external payload validation

&#x20;   structured settings



قابل استفاده است.



اما Domain Model اصلی نباید صرفاً به Pydantic وابسته شود.





\# 41. CONFIGURATION



Configuration stack:



&#x20;   pyproject.toml

&#x20;   YAML / TOML / JSON configuration files

&#x20;   Environment Variables





Configuration باید Layered باشد.





\# 42. CONFIGURATION PRIORITY



Configuration precedence:



&#x20;   Default

&#x20;      ↓

&#x20;   Config File

&#x20;      ↓

&#x20;   Environment

&#x20;      ↓

&#x20;   Runtime Override





Runtime Override باید Explicit باشد.





\# 43. SECRETS



Secrets نباید در:



&#x20;   source code

&#x20;   git

&#x20;   datasets

&#x20;   architecture documents



قرار بگیرند.



نمونه:



&#x20;   API keys

&#x20;   Broker credentials

&#x20;   passwords

&#x20;   tokens





\# 44. ENVIRONMENT VARIABLES



Secretهای Runtime ترجیحاً از Environment Variables خوانده شوند.



مثلاً:



&#x20;   SHADBOTTRADER\_BROKER\_API\_KEY

&#x20;   SHADBOTTRADER\_BROKER\_SECRET





نام‌گذاری نهایی در Configuration Phase تعیین می‌شود.





\# 45. LOGGING



Primary logging:



&#x20;   Python logging





Structured logging در مراحل بعدی قابل اضافه شدن است.



Logging باید از Business Logic جدا باشد.





\# 46. LOG LEVELS



حداقل:



&#x20;   DEBUG

&#x20;   INFO

&#x20;   WARNING

&#x20;   ERROR

&#x20;   CRITICAL





\# 47. LOGGING RULE



Production system نباید از:



&#x20;   print()



برای Operational Logging استفاده کند.



Print فقط برای CLI/UI-specific output مجاز است.





\# 48. HTTP CLIENT



برای External HTTP APIs:



&#x20;   httpx



به عنوان HTTP Client استاندارد انتخاب می‌شود.





\# 49. HTTP ABSTRACTION



External HTTP access باید در:



&#x20;   Infrastructure



باشد.



Domain/Application نباید مستقیماً:



&#x20;   httpx



را صدا بزند.





\# 50. BROKER INTEGRATION



Broker SDK یا API Client در:



&#x20;   Infrastructure/Broker/





قرار می‌گیرد.



Broker-specific implementation نباید وارد Domain شود.





\# 51. BROKER CONTRACT



Interface مربوط به Broker در:



&#x20;   Interfaces/



قرار می‌گیرد.



Implementation در:



&#x20;   Infrastructure/



قرار می‌گیرد.





الگوی:



&#x20;   Port

&#x20;     ↓

&#x20;   Adapter





است.





\# 52. MARKET DATA PROVIDER



Data Provider نیز با:



&#x20;   Interface

&#x20;      ↓

&#x20;   Adapter



مدل می‌شود.





این اجازه می‌دهد Provider در آینده بدون تغییر Domain عوض شود.





\# 53. MULTI-PROVIDER DESIGN



Architecture باید امکان داشتن چند Provider را داشته باشد.



مثلاً:



&#x20;   Provider A

&#x20;   Provider B

&#x20;   Provider C





اما در V1 لازم نیست همه Providerها پیاده‌سازی شوند.





\# 54. SCHEDULING



برای عملیات Scheduled:



&#x20;   Dataset Update

&#x20;   Training

&#x20;   Maintenance



Architecture باید Scheduler abstraction داشته باشد.



Implementation نهایی Scheduler در Phase مربوط به Runtime/Service تعیین می‌شود.





\# 55. ASYNC



Async فقط در جاهایی استفاده می‌شود که واقعاً ارزش معماری/Performance دارد.



موارد مناسب:



&#x20;   network I/O

&#x20;   multiple external requests

&#x20;   background tasks





Domain Business Logic نباید Async صرفاً برای مدرن بودن شود.





\# 56. CONCURRENCY



Concurrent execution باید Controlled باشد.



به خصوص در:



&#x20;   Broker execution

&#x20;   Dataset updates

&#x20;   Model training

&#x20;   Live market processing





Race Condition نباید باعث:



&#x20;   duplicate order

&#x20;   corrupted dataset

&#x20;   inconsistent portfolio



شود.





\# 57. DESKTOP GUI



GUI فقط Desktop است.



Web:



&#x20;   NOT REQUIRED



Mobile:



&#x20;   NOT REQUIRED





\# 58. GUI FRAMEWORK



Desktop GUI Technology:



&#x20;   PySide6





PySide6 برای:



&#x20;   Desktop Interface

&#x20;   Configuration UI

&#x20;   Monitoring

&#x20;   Visualization

&#x20;   Manual Controls



است.





\# 59. GUI ISOLATION



PySide6 فقط در:



&#x20;   GuiEngine

&#x20;   GUI-specific Infrastructure



مجاز است.



Domain نباید:



&#x20;   PySide6



را import کند.





\# 60. GUI RESPONSIBILITY



GUI می‌تواند:



&#x20;   Show Market State

&#x20;   Show Predictions

&#x20;   Show Portfolio

&#x20;   Show Logs

&#x20;   Show Training Status

&#x20;   Start/Stop Operations

&#x20;   Trigger Commands





اما نباید:



&#x20;   Trading Strategy

&#x20;   Risk Engine

&#x20;   Prediction Logic



را داخل UI پیاده کند.





\# 61. CHARTING



برای Visualizationهای Desktop:



&#x20;   matplotlib



به عنوان پایه Charting در نظر گرفته می‌شود.



Charting باید از Trading/Domain جدا باشد.





\# 62. MARKET VISUALIZATION



Market chart می‌تواند:



&#x20;   OHLC

&#x20;   Volume

&#x20;   Indicators

&#x20;   Signals



را نمایش دهد.



اما Chart Component نباید مالک Indicator Calculation باشد.





\# 63. TIME HANDLING



Time باید timezone-aware باشد.



UTC به عنوان Canonical Internal Time در نظر گرفته می‌شود.



نمایش Local Time می‌تواند در GUI انجام شود.





\# 64. MARKET TIME



Market Session و Exchange Timezone باید به صورت Domain/Configuration Concept مدل شوند.



نباید صرفاً با:



&#x20;   datetime.now()



مدیریت شوند.





\# 65. CLOCK ABSTRACTION



برای Testability:



&#x20;   Clock



باید abstraction داشته باشد.



Production:



&#x20;   System Clock



Testing:



&#x20;   Fake/Test Clock





\# 66. RANDOMNESS



Randomness در:



&#x20;   ML

&#x20;   Simulation

&#x20;   Optimization



باید قابل کنترل باشد.



Seed باید قابل ثبت باشد.





\# 67. REPRODUCIBILITY



Training/Simulation باید در حد امکان قابل Reproduce باشد.



حداقل باید قابل ثبت باشند:



&#x20;   Dataset Version

&#x20;   Feature Version

&#x20;   Model Version

&#x20;   Configuration

&#x20;   Random Seed

&#x20;   Runtime Version





\# 68. BACKTESTING



Backtesting Framework مستقل از Live Execution خواهد بود.



هر دو باید از Domain Trading concepts مشترک استفاده کنند.



اما:



&#x20;   SimulationEngine



مسئول اجرای Simulation است.





\# 69. PAPER TRADING



Paper Trading نیز باید از همان:



&#x20;   Signal

&#x20;   OrderIntent

&#x20;   Risk



استفاده کند.



اما Execution Adapter متفاوت خواهد بود.





\# 70. LIVE TRADING



Live Trading:



&#x20;   Strategy

&#x20;      ↓

&#x20;   Decision

&#x20;      ↓

&#x20;   Risk

&#x20;      ↓

&#x20;   OrderIntent

&#x20;      ↓

&#x20;   Broker Adapter

&#x20;      ↓

&#x20;   Broker





هیچ Shortcutی برای دور زدن Risk/Decision Layer مجاز نیست.





\# 71. DATA QUALITY



Historical و Live Data باید Validation داشته باشند.



موارد:



&#x20;   missing candles

&#x20;   duplicate candles

&#x20;   invalid OHLC

&#x20;   invalid timestamp

&#x20;   unexpected gaps

&#x20;   invalid volume





\# 72. DATA CONTRACT



Canonical Candle باید مشخص باشد.



حداقل:



&#x20;   timestamp

&#x20;   symbol

&#x20;   timeframe

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume





Provider-specific schema باید به Canonical Schema تبدیل شود.





\# 73. FEATURE CONTRACT



Feature Dataset باید:



&#x20;   symbol

&#x20;   timeframe

&#x20;   timestamp

&#x20;   feature values



و Metadata مربوط به Feature Set را داشته باشد.





\# 74. LOOKAHEAD BIAS



Feature Engineering و Training Pipeline باید از:



&#x20;   Lookahead Bias



جلوگیری کند.



هر Feature باید مشخص کند به چه داده‌ای دسترسی دارد.





\# 75. LIVE/HISTORICAL PARITY



Feature Engineering تاریخی و Live باید تا حد ممکن از یک Definition مشترک استفاده کنند.



نباید Feature در Training با یک منطق و Live با منطق متفاوت محاسبه شود.





\# 76. CALCULATION WINDOW



Feature ممکن است به بیشتر از Inference Window نیاز داشته باشد.



مثلاً:



&#x20;   Inference:

&#x20;       500 candles



&#x20;   Calculation:

&#x20;       1000 candles





این رفتار رسمی Architecture است.





\# 77. INFERENCE WINDOW



مدل فقط داده‌ای را دریافت می‌کند که برای Inference تعیین شده است.



مثلاً:



&#x20;   500 candles





Feature Engine ممکن است:



&#x20;   1000 candles



دریافت کند تا Featureهای موردنیاز را محاسبه کند.





\# 78. TRAINING WINDOW



Training Dataset Window باید ثابت و Versioned باشد.



مثلاً:



&#x20;   500 candles per sample





این مقدار باید بخشی از Training Configuration باشد.





\# 79. MODEL INPUT CONTRACT



Model Input باید دقیقاً تعریف کند:



&#x20;   sequence length

&#x20;   features

&#x20;   feature ordering

&#x20;   scaling

&#x20;   dtype

&#x20;   timeframe





Model نباید ورودی مبهم دریافت کند.





\# 80. SCALING



Scaling/Normalization باید Versioned باشد.



مثلاً:



&#x20;   StandardScaler

&#x20;   MinMaxScaler





Scaler باید همراه Model/Feature Version قابل بازیابی باشد.





\# 81. SCALER STORAGE



Scaler Artifact باید با:



&#x20;   Model Version

&#x20;   Feature Set Version



مرتبط باشد.





\# 82. MACHINE LEARNING ARTIFACTS



ML Artifacts:



&#x20;   model

&#x20;   scaler

&#x20;   feature metadata

&#x20;   training metadata

&#x20;   evaluation results



باید Traceable باشند.





\# 83. ARTIFACT REGISTRY



Operational metadata مربوط به Artifactها در SQLite نگهداری می‌شود.



خود Artifactهای بزرگ در File Storage نگهداری می‌شوند.





\# 84. FILE STORAGE



File Storage برای:



&#x20;   models

&#x20;   scalers

&#x20;   datasets

&#x20;   reports

&#x20;   exported artifacts



است.



مسیر Storage باید Configuration-based باشد.





\# 85. CACHE



Cache در Architecture مجاز است.



اما Cache:



&#x20;   Source of Truth



نیست.



Cache باید قابل Rebuild باشد.





\# 86. SOURCE OF TRUTH



برای هر نوع Data باید Source of Truth مشخص باشد.



مثلاً:



&#x20;   Historical Dataset:

&#x20;       Parquet Dataset



&#x20;   Operational Metadata:

&#x20;       SQLite



&#x20;   Model Artifact:

&#x20;       File Storage



&#x20;   Runtime Live State:

&#x20;       Memory / Runtime State





\# 87. DEPENDENCY ISOLATION



Framework Dependencyها باید در outer layers قرار بگیرند.



مثال:



&#x20;   tensorflow

&#x20;       → AIEngine



&#x20;   PySide6

&#x20;       → GuiEngine



&#x20;   httpx

&#x20;       → Infrastructure



&#x20;   pyarrow

&#x20;       → Data/Storage Infrastructure



&#x20;   sqlite driver

&#x20;       → Infrastructure





\# 88. DOMAIN PURITY



Domain باید تا حد امکان:



&#x20;   Pure Python



باقی بماند.



Dependencyهای سنگین Frameworkی در Domain ممنوع هستند.





\# 89. APPLICATION PURITY



Application نیز باید تا حد ممکن:



&#x20;   Framework-light



باشد.



Application نباید به UI یا Provider-specific SDK وابسته شود.





\# 90. INFRASTRUCTURE FREEDOM



Infrastructure محل استفاده از:



&#x20;   SDK

&#x20;   Database Driver

&#x20;   HTTP Client

&#x20;   File System

&#x20;   ML Framework

&#x20;   OS APIs



است.





\# 91. CORE TECHNOLOGY STACK



Technology Baseline:



&#x20;   Python

&#x20;   NumPy

&#x20;   pandas

&#x20;   PyArrow

&#x20;   TensorFlow

&#x20;   Keras

&#x20;   Pydantic

&#x20;   httpx

&#x20;   SQLite

&#x20;   PySide6

&#x20;   matplotlib

&#x20;   pytest

&#x20;   ruff

&#x20;   black

&#x20;   mypy





\# 92. OPTIONAL DEPENDENCY POLICY



هیچ Library جدیدی فقط به دلیل:



&#x20;   convenience



اضافه نمی‌شود.



هر Dependency جدید باید حداقل یکی از این موارد را داشته باشد:



&#x20;   Performance Benefit

&#x20;   Architectural Benefit

&#x20;   Reliability Benefit

&#x20;   Maintainability Benefit

&#x20;   Required External Integration





\# 93. DEPENDENCY VERSIONING



Dependencyها باید:



&#x20;   Explicit

&#x20;   Reproducible

&#x20;   Version-controlled



باشند.



Production environment نباید بر اساس آخرین نسخه تصادفی Packageها ساخته شود.





\# 94. SECURITY



Security Boundary باید شامل:



&#x20;   secrets

&#x20;   credentials

&#x20;   broker keys

&#x20;   local permissions

&#x20;   artifact integrity



باشد.





\# 95. BROKER SAFETY



Broker Integration باید Fail-Safe باشد.



در صورت:



&#x20;   network failure

&#x20;   malformed response

&#x20;   duplicate response

&#x20;   timeout



سیستم نباید به صورت uncontrolled Order ایجاد کند.





\# 96. DATA SAFETY



Dataset Update باید:



&#x20;   atomic

&#x20;   validated

&#x20;   version-aware



باشد.



Dataset خراب نباید جای Dataset سالم را بگیرد.





\# 97. MODEL SAFETY



Model جدید نباید بلافاصله Production شود.



Flow:



&#x20;   Train

&#x20;     ↓

&#x20;   Evaluate

&#x20;     ↓

&#x20;   Validate

&#x20;     ↓

&#x20;   Approve

&#x20;     ↓

&#x20;   Promote





\# 98. MODEL ROLLBACK



Production Model باید امکان Rollback داشته باشد.



Model Registry باید حداقل:



&#x20;   current model

&#x20;   previous model



را قابل تشخیص کند.





\# 99. CONFIGURATION SAFETY



تغییرات Configuration مهم باید Traceable باشند.



موارد مهم:



&#x20;   timeframe

&#x20;   symbol

&#x20;   calculation window

&#x20;   inference window

&#x20;   training window

&#x20;   risk configuration

&#x20;   model version





\# 100. ARCHITECTURE TESTING



Architecture Test باید بررسی کند:



&#x20;   Domain isolation

&#x20;   Dependency direction

&#x20;   Forbidden imports

&#x20;   Circular dependencies

&#x20;   Framework leakage





\# 101. FORBIDDEN IMPORTS



نمونه:



&#x20;   Domain → TensorFlow

&#x20;   Domain → Keras

&#x20;   Domain → PySide6

&#x20;   Domain → httpx

&#x20;   Domain → SQLite

&#x20;   Domain → Broker SDK



همگی ممنوع.





\# 102. FORBIDDEN GUI DEPENDENCY



این موارد نباید به GUI وابسته باشند:



&#x20;   Domain

&#x20;   Application

&#x20;   DataEngine

&#x20;   AIEngine

&#x20;   Trading Logic





GUI مصرف‌کننده سیستم است، نه مرکز سیستم.





\# 103. FORBIDDEN BROKER DEPENDENCY



این موارد نباید Broker-specific باشند:



&#x20;   Domain Trading

&#x20;   Strategy

&#x20;   Prediction

&#x20;   Risk





Broker فقط Adapter است.





\# 104. FORBIDDEN ML DEPENDENCY



Strategy و Domain Prediction نباید:



&#x20;   TensorFlow Model object



را مستقیماً مصرف کنند.



باید از Model Contract استفاده کنند.





\# 105. ENVIRONMENT



Environmentهای اصلی:



&#x20;   Development

&#x20;   Testing

&#x20;   Production





در آینده می‌توان:



&#x20;   Research

&#x20;   Training



را نیز به صورت Configuration Profile تعریف کرد.





\# 106. DEVELOPMENT ENVIRONMENT



Development باید شامل:



&#x20;   Python

&#x20;   Dependencies

&#x20;   Quality Tools

&#x20;   Test Tools





باشد.





\# 107. TEST ENVIRONMENT



Test Environment باید:



&#x20;   deterministic

&#x20;   isolated

&#x20;   reproducible



باشد.





\# 108. PRODUCTION ENVIRONMENT



Production باید:



&#x20;   controlled dependencies

&#x20;   validated configuration

&#x20;   logging

&#x20;   monitoring

&#x20;   rollback capability



داشته باشد.





\# 109. LOCAL DESKTOP DEPLOYMENT



Deployment اولیه:



&#x20;   Local Windows Machine





Application باید بتواند به صورت:



&#x20;   CLI

&#x20;   Desktop GUI



اجرا شود.





\# 110. CLI



CLI برای:



&#x20;   dataset update

&#x20;   training

&#x20;   backtesting

&#x20;   maintenance

&#x20;   diagnostics



مجاز است.



CLI نباید Business Logic مستقل داشته باشد.





\# 111. DESKTOP APPLICATION



Desktop GUI فقط یک Interface به Application است.



معماری:



&#x20;   GUI

&#x20;     ↓

&#x20;   Application

&#x20;     ↓

&#x20;   Domain





نه:



&#x20;   GUI

&#x20;     ↓

&#x20;   Database

&#x20;     ↓

&#x20;   Broker





\# 112. DATA UPDATE COMMAND



Dataset Update باید یک Application Use Case باشد.



مثلاً مفهوم:



&#x20;   UpdateHistoricalDataset





نه یک Script با Business Logic مستقل.





\# 113. TRAINING COMMAND



Training نیز Application Use Case است.



مثلاً:



&#x20;   TrainModel





Script فقط آن را Invoke می‌کند.





\# 114. BACKTEST COMMAND



Backtest:



&#x20;   RunBacktest





به عنوان Application Use Case مدیریت می‌شود.





\# 115. LIVE TRADING COMMAND



Live Trading:



&#x20;   StartTradingSession





Application مسئول Orchestration است.



ExecutionEngine مسئول Execution است.





\# 116. FRAMEWORK FREEZE



بعد از تأیید Phase 05:



&#x20;   Technology Baseline = FROZEN





Frameworkها بدون Architecture Decision جدید تغییر نمی‌کنند.





\# 117. FRAMEWORK CHANGE POLICY



اگر در آینده Frameworkی تغییر کند، باید بررسی شود:



&#x20;   API compatibility

&#x20;   performance

&#x20;   data compatibility

&#x20;   model compatibility

&#x20;   architecture compatibility

&#x20;   deployment compatibility

&#x20;   test impact





تغییر Framework نباید باعث تغییر Domain Model شود مگر ضرورت واقعی وجود داشته باشد.





\# 118. TECHNOLOGY DECISION PRINCIPLE



Architecture باید از Frameworkها مستقل بماند.



Frameworkها قابل تعویض‌اند.



Domain Concepts قابل تعویض نیستند.





\# 119. FINAL TECHNOLOGY GRAPH



&#x20;   ┌─────────────────────────────┐

&#x20;   │          PySide6            │

&#x20;   │        Desktop GUI          │

&#x20;   └──────────────┬──────────────┘

&#x20;                  │

&#x20;                  ▼

&#x20;   ┌─────────────────────────────┐

&#x20;   │        Application          │

&#x20;   │        Use Cases             │

&#x20;   └──────────────┬──────────────┘

&#x20;                  │

&#x20;                  ▼

&#x20;   ┌─────────────────────────────┐

&#x20;   │           Domain            │

&#x20;   │      Pure Business Model    │

&#x20;   └─────────────────────────────┘



&#x20;   Infrastructure surrounds the core:



&#x20;   ┌────────────────────────────────────────┐

&#x20;   │             Infrastructure             │

&#x20;   │                                        │

&#x20;   │ Broker SDK    httpx    SQLite          │

&#x20;   │ PyArrow       TensorFlow               │

&#x20;   │ File System   External APIs             │

&#x20;   │                                        │

&#x20;   └────────────────────────────────────────┘





\# 120. FINAL DATA TECHNOLOGY FLOW



Historical:



&#x20;   Broker/API

&#x20;       ↓

&#x20;   httpx / Provider SDK

&#x20;       ↓

&#x20;   Data Adapter

&#x20;       ↓

&#x20;   pandas / NumPy

&#x20;       ↓

&#x20;   PyArrow

&#x20;       ↓

&#x20;   Parquet

&#x20;       ↓

&#x20;   Feature Engineering

&#x20;       ↓

&#x20;   Feature Parquet

&#x20;       ↓

&#x20;   TensorFlow / Keras

&#x20;       ↓

&#x20;   Model Artifact





Live:



&#x20;   Broker/API

&#x20;       ↓

&#x20;   Provider Adapter

&#x20;       ↓

&#x20;   Live Buffer

&#x20;       ↓

&#x20;   Calculation Window

&#x20;       ↓

&#x20;   Feature Engineering

&#x20;       ↓

&#x20;   Inference Window

&#x20;       ↓

&#x20;   TensorFlow / Keras

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Decision

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Broker Adapter





\# 121. FINAL DATABASE FLOW



&#x20;   Application

&#x20;        ↓

&#x20;   Repository Contract

&#x20;        ↓

&#x20;   Infrastructure Repository

&#x20;        ↓

&#x20;   SQLite





\# 122. FINAL MODEL FLOW



&#x20;   Domain Model Contract

&#x20;         ↓

&#x20;   AIEngine

&#x20;         ↓

&#x20;   TensorFlow / Keras





\# 123. FINAL GUI FLOW



&#x20;   PySide6

&#x20;       ↓

&#x20;   Application Command

&#x20;       ↓

&#x20;   Domain

&#x20;       ↓

&#x20;   Engine / Infrastructure





\# 124. FINAL QUALITY FLOW



&#x20;   Developer Change

&#x20;         ↓

&#x20;      Ruff

&#x20;         ↓

&#x20;      Black

&#x20;         ↓

&#x20;      Mypy

&#x20;         ↓

&#x20;      Pytest

&#x20;         ↓

&#x20;   Architecture Tests

&#x20;         ↓

&#x20;      Approved





\# 125. PHASE 05 ACCEPTANCE CRITERIA



\[x] Python Runtime defined

\[x] Package management defined

\[x] pyproject.toml defined

\[x] Ruff defined

\[x] Black defined

\[x] Mypy defined

\[x] Pytest defined

\[x] NumPy defined

\[x] pandas defined

\[x] PyArrow defined

\[x] Parquet defined

\[x] TensorFlow defined

\[x] Keras defined

\[x] SQLite defined

\[x] Pydantic defined

\[x] httpx defined

\[x] PySide6 defined

\[x] matplotlib defined

\[x] Configuration strategy defined

\[x] Secret strategy defined

\[x] Logging strategy defined

\[x] HTTP boundary defined

\[x] Broker boundary defined

\[x] Data Provider boundary defined

\[x] ML boundary defined

\[x] GUI boundary defined

\[x] Dataset technology defined

\[x] Live Data technology defined

\[x] Historical Data technology defined

\[x] Feature Engineering technology defined

\[x] Training technology defined

\[x] Model storage defined

\[x] Artifact lineage defined

\[x] Reproducibility defined

\[x] Backtesting boundary defined

\[x] Paper Trading boundary defined

\[x] Live Trading boundary defined

\[x] Dependency isolation defined

\[x] Forbidden imports defined

\[x] Desktop-only architecture confirmed

\[x] Web Dashboard excluded

\[x] Mobile Application excluded

\[x] Framework Freeze defined





\# 126. FINAL TECHNOLOGY BASELINE



Language:



&#x20;   Python



Data:



&#x20;   NumPy

&#x20;   pandas

&#x20;   PyArrow

&#x20;   Parquet



Machine Learning:



&#x20;   TensorFlow

&#x20;   Keras



Database:



&#x20;   SQLite



Validation / Configuration:



&#x20;   Pydantic



Networking:



&#x20;   httpx



Desktop:



&#x20;   PySide6



Visualization:



&#x20;   matplotlib



Testing:



&#x20;   Pytest



Quality:



&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy



Logging:



&#x20;   Python logging





\# 127. PHASE 05 FINAL STATUS



PHASE:



&#x20;   05 — FRAMEWORK DESIGN



STATUS:



&#x20;   FINAL BASELINE



TECHNOLOGY BASELINE:



&#x20;   FROZEN AFTER APPROVAL



NEXT PHASE:



&#x20;   PHASE 06 — PIPELINE DESIGN





IMPORTANT:



از Phase 06 به بعد، Frameworkها و Technology Stack تغییر نمی‌کنند مگر اینکه یک Architecture Decision رسمی ایجاد شود.



Phase 06 باید روی جریان واقعی سیستم تمرکز کند:



&#x20;   Data Acquisition

&#x20;   Dataset Update

&#x20;   Processing

&#x20;   Feature Engineering

&#x20;   Training

&#x20;   Live Data

&#x20;   Live Feature Engineering

&#x20;   Prediction

&#x20;   Decision

&#x20;   Risk

&#x20;   Execution

&#x20;   Feedback

&#x20;   Self-Learning

&#x20;   Project Intelligence



و نباید دوباره Phaseهای 01 تا 05 را از ابتدا طراحی کند.

