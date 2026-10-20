================================================================================

SHADBOTTRADER

ENTERPRISE AI TRADING PLATFORM

================================================================================



PHASE 9 — PLUGIN ARCHITECTURE

================================================================================



STATUS:

&#x20;   ARCHITECTURE DESIGN



ARCHITECTURE BASELINE:

&#x20;   PHASE 1 → PHASE 9



IMPLEMENTATION:

&#x20;   PHASE 28+



PRIMARY GOALS:



&#x20;   EXTENSIBILITY

&#x20;   MODULARITY

&#x20;   PLUGGABILITY

&#x20;   HOT-SWAPPABLE CAPABILITIES

&#x20;   PROVIDER INDEPENDENCE

&#x20;   VERSIONED CONTRACTS

&#x20;   ISOLATION

&#x20;   DISCOVERABILITY

&#x20;   SAFE LOADING

&#x20;   DEPENDENCY CONTROL



================================================================================

1\. PURPOSE

================================================================================



Plugin Architecture defines how external or optional capabilities become

part of ShadBotTrader without modifying the Core architecture.



A Plugin is an independently deployable/extensible capability that conforms

to a ShadBotTrader-defined contract.



Examples:



&#x20;   Market Data Provider

&#x20;   Broker

&#x20;   News Provider

&#x20;   AI Model Provider

&#x20;   Feature Provider

&#x20;   Strategy

&#x20;   Storage Provider

&#x20;   Notification Provider

&#x20;   Analytics Provider

&#x20;   Exchange Adapter

&#x20;   Portfolio Provider



Core principle:



&#x20;   CORE MUST NOT KNOW CONCRETE PLUGINS.



Core knows:



&#x20;   contracts

&#x20;   capabilities

&#x20;   metadata

&#x20;   lifecycle

&#x20;   dependency rules



Plugins provide:



&#x20;   implementations



================================================================================

2\. FUNDAMENTAL RULE

================================================================================



DEPEND ON CONTRACTS, NOT PLUGINS.



Correct:



&#x20;   Application

&#x20;       |

&#x20;       v

&#x20;   Plugin Contract

&#x20;       |

&#x20;       v

&#x20;   Plugin Implementation



Forbidden:



&#x20;   Application

&#x20;       |

&#x20;       v

&#x20;   BinancePlugin



or:



&#x20;   TradingService

&#x20;       |

&#x20;       v

&#x20;   MetaTrader5SDK



Instead:



&#x20;   TradingService

&#x20;       |

&#x20;       v

&#x20;   BrokerPort

&#x20;       |

&#x20;       v

&#x20;   BrokerPlugin



================================================================================

3\. PLUGIN ARCHITECTURE MODEL

================================================================================



&#x20;                       SHADBOTTRADER CORE

&#x20;                            |

&#x20;                   +--------+--------+

&#x20;                   |                 |

&#x20;             Plugin Contract     Plugin Registry

&#x20;                   |                 |

&#x20;                   +--------+--------+

&#x20;                            |

&#x20;                      Plugin Manager

&#x20;                            |

&#x20;                   +--------+--------+

&#x20;                   |        |        |

&#x20;                   v        v        v

&#x20;                Plugin A  Plugin B  Plugin C



================================================================================

4\. PLUGIN TYPES

================================================================================



ShadBotTrader supports multiple plugin categories.



&#x20;   DATA PLUGINS

&#x20;   BROKER PLUGINS

&#x20;   AI PLUGINS

&#x20;   MODEL PLUGINS

&#x20;   FEATURE PLUGINS

&#x20;   STRATEGY PLUGINS

&#x20;   NEWS PLUGINS

&#x20;   STORAGE PLUGINS

&#x20;   NOTIFICATION PLUGINS

&#x20;   ANALYTICS PLUGINS

&#x20;   OPTIMIZATION PLUGINS

&#x20;   PORTFOLIO PLUGINS

&#x20;   SIMULATION PLUGINS

&#x20;   GUI PLUGINS

&#x20;   PROJECT INTELLIGENCE PLUGINS



Additional plugin categories may be introduced later through architecture

extension.



================================================================================

5\. PLUGIN CONTRACT

================================================================================



Every plugin must expose a standard contract.



Conceptually:



&#x20;   Plugin

&#x20;       |

&#x20;       +--> identity

&#x20;       +--> metadata

&#x20;       +--> capabilities

&#x20;       +--> configuration

&#x20;       +--> lifecycle

&#x20;       +--> health

&#x20;       +--> dependencies



Minimum conceptual interface:



&#x20;   Plugin

&#x20;       initialize()

&#x20;       start()

&#x20;       stop()

&#x20;       health()

&#x20;       metadata()



================================================================================

6\. PLUGIN IDENTITY

================================================================================



Every plugin must have a globally unique Plugin ID.



Example:



&#x20;   market.oanda

&#x20;   market.yahoo

&#x20;   broker.ibkr

&#x20;   broker.mt5

&#x20;   news.reuters

&#x20;   ai.tensorflow

&#x20;   ai.pytorch

&#x20;   strategy.momentum

&#x20;   storage.sqlserver



Plugin ID must be:



&#x20;   stable

&#x20;   unique

&#x20;   machine-readable



Plugin ID must NOT depend on:



&#x20;   display name

&#x20;   filesystem path

&#x20;   Python class name



================================================================================

7\. PLUGIN METADATA

================================================================================



Plugin metadata should contain:



&#x20;   plugin\_id

&#x20;   name

&#x20;   version

&#x20;   author

&#x20;   description

&#x20;   plugin\_type

&#x20;   API version

&#x20;   supported capabilities

&#x20;   dependencies

&#x20;   compatibility

&#x20;   configuration schema

&#x20;   license metadata where required



Example conceptual:



&#x20;   PluginMetadata(

&#x20;       id="broker.example",

&#x20;       version="1.0.0",

&#x20;       api\_version="1",

&#x20;       type="broker"

&#x20;   )



================================================================================

8\. PLUGIN VERSIONING

================================================================================



Plugin versioning follows semantic versioning where appropriate:



&#x20;   MAJOR.MINOR.PATCH



Example:



&#x20;   1.0.0

&#x20;   1.1.0

&#x20;   1.1.1



Breaking contract:



&#x20;   MAJOR



Backward-compatible feature:



&#x20;   MINOR



Bug fix:



&#x20;   PATCH



================================================================================

9\. PLUGIN API VERSION

================================================================================



Plugin version and Plugin API version are different.



Example:



&#x20;   Plugin:

&#x20;       version = 4.2.1



&#x20;   ShadBotTrader Plugin API:

&#x20;       version = 2



A plugin can evolve internally while remaining compatible with the same

ShadBotTrader Plugin API.



================================================================================

10\. CAPABILITY MODEL

================================================================================



A Plugin exposes capabilities.



Example:



&#x20;   Broker Plugin



&#x20;       capabilities:

&#x20;           PLACE\_ORDER

&#x20;           CANCEL\_ORDER

&#x20;           GET\_ORDER

&#x20;           GET\_ACCOUNT

&#x20;           GET\_POSITIONS



A plugin may implement only a subset.



Core must inspect capabilities before invoking optional functionality.



================================================================================

11\. CAPABILITY CONTRACT

================================================================================



Capabilities should be explicit.



Example:



&#x20;   BrokerCapabilities



&#x20;       market\_orders

&#x20;       limit\_orders

&#x20;       stop\_orders

&#x20;       order\_cancel

&#x20;       position\_query

&#x20;       account\_query



Do not assume all brokers support every feature.



================================================================================

12\. PLUGIN REGISTRY

================================================================================



PluginRegistry maintains known plugins.



Responsibilities:



&#x20;   register()

&#x20;   unregister()

&#x20;   resolve()

&#x20;   find()

&#x20;   list()

&#x20;   has()

&#x20;   validate()



Registry must prevent duplicate Plugin IDs.



================================================================================

13\. PLUGIN MANAGER

================================================================================



PluginManager controls lifecycle and operational state.



Responsibilities:



&#x20;   discover

&#x20;   validate

&#x20;   load

&#x20;   initialize

&#x20;   start

&#x20;   stop

&#x20;   unload

&#x20;   health-check



PluginRegistry answers:



&#x20;   "What plugins are registered?"



PluginManager answers:



&#x20;   "What is the operational state of plugins?"



================================================================================

14\. PLUGIN DISCOVERY

================================================================================



Plugin discovery may use:



&#x20;   explicit configuration

&#x20;   Python package entry points

&#x20;   plugin directories

&#x20;   manifest files

&#x20;   built-in registration



Discovery must be deterministic.



Never load arbitrary Python files simply because they exist in a directory.



================================================================================

15\. PLUGIN MANIFEST

================================================================================



Every external plugin should have a manifest.



Conceptual:



&#x20;   plugin.yaml



or:



&#x20;   plugin.json



Example:



&#x20;   id:

&#x20;   name:

&#x20;   version:

&#x20;   api\_version:

&#x20;   type:

&#x20;   entrypoint:

&#x20;   capabilities:

&#x20;   dependencies:

&#x20;   configuration:



The manifest is metadata.



The actual plugin implementation remains code.



================================================================================

16\. ENTRYPOINT

================================================================================



The manifest identifies the plugin entrypoint.



Conceptual:



&#x20;   ShadBotTrader.plugins.example:ExamplePlugin



The Plugin Manager resolves the entrypoint.



The plugin must conform to the required Plugin contract.



================================================================================

17\. PLUGIN VALIDATION

================================================================================



Before loading:



&#x20;   manifest validation



After loading:



&#x20;   contract validation



Before activation:



&#x20;   dependency validation

&#x20;   configuration validation

&#x20;   compatibility validation

&#x20;   capability validation



Plugin must not become ACTIVE until validation succeeds.



================================================================================

18\. PLUGIN STATES

================================================================================



Plugin lifecycle:



&#x20;   DISCOVERED

&#x20;       |

&#x20;       v

&#x20;   VALIDATED

&#x20;       |

&#x20;       v

&#x20;   LOADED

&#x20;       |

&#x20;       v

&#x20;   INITIALIZED

&#x20;       |

&#x20;       v

&#x20;   STARTED

&#x20;       |

&#x20;       v

&#x20;   ACTIVE

&#x20;       |

&#x20;       v

&#x20;   STOPPING

&#x20;       |

&#x20;       v

&#x20;   STOPPED



Failure state:



&#x20;   FAILED



A failed plugin must expose failure reason.



================================================================================

19\. PLUGIN LIFECYCLE

================================================================================



Lifecycle methods:



&#x20;   discover

&#x20;   validate

&#x20;   load

&#x20;   initialize

&#x20;   start

&#x20;   stop

&#x20;   unload



Rules:



&#x20;   initialize() may allocate resources.



&#x20;   start() begins active operation.



&#x20;   stop() must safely stop active work.



&#x20;   unload() releases plugin resources where supported.



================================================================================

20\. PLUGIN INITIALIZATION

================================================================================



initialize() receives only explicit dependencies.



Forbidden:



&#x20;   plugin importing global application state

&#x20;   plugin accessing global database

&#x20;   plugin creating hidden EventBus

&#x20;   plugin creating hidden configuration



Preferred:



&#x20;   PluginContext



containing approved dependencies.



================================================================================

21\. PLUGIN CONTEXT

================================================================================



PluginContext may provide:



&#x20;   logger

&#x20;   configuration

&#x20;   event\_bus

&#x20;   clock

&#x20;   service access through approved ports

&#x20;   plugin metadata

&#x20;   storage abstraction

&#x20;   metrics



PluginContext must NOT expose unrestricted access to the entire application.



================================================================================

22\. PLUGIN ISOLATION

================================================================================



Plugins must be isolated logically.



A plugin must not:



&#x20;   modify another plugin's state

&#x20;   bypass contracts

&#x20;   access internal private modules

&#x20;   modify Core objects globally

&#x20;   replace registries directly



Communication should occur through:



&#x20;   contracts

&#x20;   events

&#x20;   approved services

&#x20;   ports



================================================================================

23\. PLUGIN DEPENDENCIES

================================================================================



Plugins may depend on:



&#x20;   Core API

&#x20;   Plugin API

&#x20;   other plugins

&#x20;   external packages



Dependencies must be declared explicitly.



Example:



&#x20;   strategy.momentum

&#x20;       depends\_on:

&#x20;           feature.technical

&#x20;           data.market



================================================================================

24\. PLUGIN DEPENDENCY GRAPH

================================================================================



Plugin dependencies form a directed graph.



Example:



&#x20;   strategy.momentum

&#x20;           |

&#x20;           v

&#x20;   feature.technical

&#x20;           |

&#x20;           v

&#x20;   data.market



The Plugin Manager must detect:



&#x20;   missing dependency

&#x20;   version conflict

&#x20;   circular dependency



================================================================================

25\. CIRCULAR DEPENDENCIES

================================================================================



Forbidden:



&#x20;   Plugin A -> Plugin B

&#x20;   Plugin B -> Plugin A



The dependency graph must be acyclic.



If two plugins need to communicate:



&#x20;   introduce a shared contract

&#x20;   or use Event Bus



================================================================================

26\. PLUGIN LOAD ORDER

================================================================================



Dependencies determine load order.



Example:



&#x20;   Core

&#x20;     |

&#x20;     v

&#x20;   Data Plugin

&#x20;     |

&#x20;     v

&#x20;   Feature Plugin

&#x20;     |

&#x20;     v

&#x20;   Strategy Plugin

&#x20;     |

&#x20;     v

&#x20;   Trading Plugin



Plugins cannot start before their dependencies are ACTIVE or otherwise

explicitly available according to the contract.



================================================================================

27\. PLUGIN PRIORITY

================================================================================



Optional plugin priority may determine:



&#x20;   discovery order

&#x20;   initialization order

&#x20;   provider preference



Priority must never override dependency requirements.



Dependency graph always wins.



================================================================================

28\. MULTIPLE PROVIDERS

================================================================================



ShadBotTrader may have multiple implementations of one contract.



Example:



&#x20;   MarketDataPort



&#x20;       OandaProvider

&#x20;       PolygonProvider

&#x20;       YahooProvider



Only one may be active for a specific role unless the application explicitly

supports multi-provider operation.



================================================================================

29\. PROVIDER SELECTION

================================================================================



Provider selection should use:



&#x20;   configuration

&#x20;   capability

&#x20;   compatibility

&#x20;   availability

&#x20;   explicit priority



Example:



&#x20;   market\_data.primary = oanda



Fallback may be configured:



&#x20;   primary -> secondary



Fallback must be explicit.



================================================================================

30\. PLUGIN CONFIGURATION

================================================================================



Each plugin owns its configuration schema.



Example:



&#x20;   broker.mt5:

&#x20;       server

&#x20;       account

&#x20;       timeout

&#x20;       environment



Core owns:



&#x20;   configuration lifecycle



Plugin owns:



&#x20;   configuration interpretation



Secrets must come from secure configuration/secret management.



================================================================================

31\. PLUGIN CONFIGURATION VALIDATION

================================================================================



Configuration lifecycle:



&#x20;   Load

&#x20;     |

&#x20;     v

&#x20;   Schema validation

&#x20;     |

&#x20;     v

&#x20;   Plugin validation

&#x20;     |

&#x20;     v

&#x20;   Initialize



Invalid configuration prevents activation.



================================================================================

32\. SECRET MANAGEMENT

================================================================================



Plugins must never hard-code:



&#x20;   API keys

&#x20;   passwords

&#x20;   tokens

&#x20;   private keys

&#x20;   broker credentials



Secrets must be injected through approved configuration/secret abstractions.



Never commit secrets to Git.



================================================================================

33\. PLUGIN EVENTS

================================================================================



Plugin lifecycle events:



&#x20;   PluginDiscovered

&#x20;   PluginLoaded

&#x20;   PluginInitialized

&#x20;   PluginStarted

&#x20;   PluginStopped

&#x20;   PluginFailed



These events allow:



&#x20;   monitoring

&#x20;   audit

&#x20;   GUI

&#x20;   diagnostics



================================================================================

34\. PLUGIN HEALTH

================================================================================



Every active plugin should expose health information.



Health states:



&#x20;   HEALTHY

&#x20;   DEGRADED

&#x20;   UNHEALTHY

&#x20;   UNKNOWN



Example:



&#x20;   Broker Plugin



&#x20;       connection = HEALTHY

&#x20;       trading = HEALTHY

&#x20;       market\_data = DEGRADED



================================================================================

35\. PLUGIN HEALTH CHECK

================================================================================



Health check must be:



&#x20;   lightweight

&#x20;   bounded

&#x20;   non-destructive



Do not execute an actual trade merely to test broker health.



================================================================================

36\. PLUGIN FAILURE

================================================================================



A plugin failure must not automatically crash the entire ShadBotTrader process.



The reaction depends on plugin criticality.



Example:



&#x20;   News Plugin fails



&#x20;       Trading may continue.



&#x20;   Primary Broker Plugin fails



&#x20;       Live trading may need to halt.



================================================================================

37\. PLUGIN CRITICALITY

================================================================================



Plugin metadata may define:



&#x20;   OPTIONAL

&#x20;   IMPORTANT

&#x20;   CRITICAL



Example:



&#x20;   NewsProvider:

&#x20;       OPTIONAL



&#x20;   PrimaryMarketData:

&#x20;       IMPORTANT



&#x20;   LiveBroker:

&#x20;       CRITICAL



Critical plugin failure may trigger:



&#x20;   Safe Mode

&#x20;   Trading Halt

&#x20;   Runtime Shutdown



depending on system policy.



================================================================================

38\. SAFE MODE

================================================================================



When critical dependencies fail:



&#x20;   ShadBotTrader may enter SAFE\_MODE.



SAFE\_MODE may disable:



&#x20;   live order execution

&#x20;   automatic trading

&#x20;   irreversible operations



while keeping available:



&#x20;   monitoring

&#x20;   diagnostics

&#x20;   simulation

&#x20;   read-only operations



================================================================================

39\. PLUGIN SECURITY

================================================================================



Plugins are executable code.



Therefore plugins are trusted components by default only when explicitly

installed/approved.



Plugin loading must verify:



&#x20;   source

&#x20;   package identity

&#x20;   version

&#x20;   compatibility

&#x20;   integrity where supported



Do not automatically execute untrusted downloaded code.



================================================================================

40\. PLUGIN PERMISSIONS

================================================================================



Future Plugin Permission Model:



&#x20;   READ\_MARKET\_DATA

&#x20;   WRITE\_DATA

&#x20;   EXECUTE\_TRADES

&#x20;   READ\_ACCOUNT

&#x20;   WRITE\_ACCOUNT

&#x20;   ACCESS\_NETWORK

&#x20;   ACCESS\_FILESYSTEM

&#x20;   ACCESS\_MODEL\_REGISTRY



A plugin must receive only permissions it requires.



================================================================================

41\. PLUGIN SANDBOXING

================================================================================



Full OS-level sandboxing is outside the basic Plugin Architecture.



However, the architecture must keep the boundary ready for future sandboxing.



Therefore:



&#x20;   plugin

&#x20;       |

&#x20;       v

&#x20;   Plugin API



rather than:



&#x20;   plugin

&#x20;       |

&#x20;       v

&#x20;   unrestricted Core internals



================================================================================

42\. PLUGIN API SURFACE

================================================================================



Only approved public APIs are plugin-facing.



Example:



&#x20;   ShadBotTrader.plugin\_api



Internal modules such as:



&#x20;   ShadBotTrader.\_internal



must not be considered stable plugin APIs.



================================================================================

43\. PLUGIN COMPATIBILITY

================================================================================



Compatibility must verify:



&#x20;   Python compatibility

&#x20;   ShadBotTrader Plugin API compatibility

&#x20;   capability compatibility

&#x20;   dependency compatibility

&#x20;   configuration schema compatibility



================================================================================

44\. PLUGIN MIGRATION

================================================================================



When a Plugin API changes:



&#x20;   old plugin

&#x20;       |

&#x20;       v

&#x20;   compatibility adapter



may temporarily support older plugins.



Breaking changes require:



&#x20;   new API version



================================================================================

45\. PLUGIN DEPRECATION

================================================================================



Plugins may be marked:



&#x20;   ACTIVE

&#x20;   DEPRECATED

&#x20;   DISABLED

&#x20;   REMOVED



Deprecation should provide:



&#x20;   replacement

&#x20;   migration path

&#x20;   removal version



================================================================================

46\. PLUGIN ENABLE/DISABLE

================================================================================



Plugins can be:



&#x20;   installed

&#x20;   enabled

&#x20;   disabled

&#x20;   removed



Disabled plugin:



&#x20;   remains known

&#x20;   is not initialized

&#x20;   is not active



Removing a plugin must not corrupt unrelated application state.



================================================================================

47\. PLUGIN REGISTRY STORAGE

================================================================================



Plugin metadata may be persisted.



Possible information:



&#x20;   plugin\_id

&#x20;   version

&#x20;   enabled

&#x20;   active

&#x20;   health

&#x20;   configuration hash

&#x20;   last startup

&#x20;   last failure



Runtime state must be distinguished from persistent configuration.



================================================================================

48\. PLUGIN INSTALLATION

================================================================================



Future Plugin Installer responsibilities:



&#x20;   validate package

&#x20;   inspect manifest

&#x20;   resolve dependencies

&#x20;   verify compatibility

&#x20;   install

&#x20;   register

&#x20;   configure

&#x20;   activate



Installation must not automatically activate an unsafe plugin without

explicit policy.



================================================================================

49\. PLUGIN UPDATE

================================================================================



Plugin update flow:



&#x20;   inspect new version

&#x20;       |

&#x20;       v

&#x20;   compatibility check

&#x20;       |

&#x20;       v

&#x20;   dependency resolution

&#x20;       |

&#x20;       v

&#x20;   backup/state preservation

&#x20;       |

&#x20;       v

&#x20;   update

&#x20;       |

&#x20;       v

&#x20;   validation

&#x20;       |

&#x20;       v

&#x20;   activation



For critical trading plugins, updates should normally require maintenance

mode or controlled restart.



================================================================================

50\. PLUGIN ROLLBACK

================================================================================



Failed plugin updates must support rollback where practical.



Example:



&#x20;   v1.4.0 ACTIVE

&#x20;        |

&#x20;        v

&#x20;   update to v1.5.0

&#x20;        |

&#x20;      FAIL

&#x20;        |

&#x20;        v

&#x20;   rollback to v1.4.0



Rollback strategy depends on plugin type and persistent state.



================================================================================

51\. PLUGIN STATE MIGRATION

================================================================================



If plugin updates change persistent state:



&#x20;   migration version



must be tracked.



Example:



&#x20;   plugin schema:

&#x20;       1

&#x20;       2

&#x20;       3



Migration must be explicit and reversible where possible.



================================================================================

52\. PLUGIN + EVENT BUS

================================================================================



Plugins communicate through Event Bus when loose coupling is required.



Example:



&#x20;   TradeExecutedEvent

&#x20;         |

&#x20;         +--> AnalyticsPlugin

&#x20;         +--> NotificationPlugin

&#x20;         +--> AuditPlugin



The publisher must not know all consumers.



================================================================================

53\. PLUGIN + SERVICES

================================================================================



Services interact with plugins through contracts.



Example:



&#x20;   ExecuteOrderService

&#x20;         |

&#x20;         v

&#x20;   BrokerPort

&#x20;         |

&#x20;         v

&#x20;   BrokerPlugin



Service does not need to know which broker implementation is active.



================================================================================

54\. PLUGIN + ENGINES

================================================================================



Plugins may provide Engine implementations.



Example:



&#x20;   AI Plugin

&#x20;       |

&#x20;       v

&#x20;   AIEngine implementation



or:



&#x20;   Feature Plugin

&#x20;       |

&#x20;       v

&#x20;   FeatureEngine implementation



The Engine contract remains owned by the platform architecture.



================================================================================

55\. PLUGIN + PIPELINES

================================================================================



Pipelines may select plugin capabilities.



Example:



&#x20;   Live Trading Pipeline

&#x20;           |

&#x20;           v

&#x20;      MarketDataPort

&#x20;           |

&#x20;           v

&#x20;      MarketDataPlugin



Pipeline defines workflow.



Plugin provides capability.



================================================================================

56\. PLUGIN + DOMAIN

================================================================================



Domain must remain independent from concrete plugins.



Forbidden:



&#x20;   Domain -> BrokerPlugin

&#x20;   Domain -> YahooPlugin

&#x20;   Domain -> TensorFlowPlugin



Domain may define:



&#x20;   interfaces

&#x20;   policies

&#x20;   domain concepts



but concrete plugin implementations belong outside Domain.



================================================================================

57\. PLUGIN + INFRASTRUCTURE

================================================================================



Infrastructure provides plugin loading and external integration mechanisms.



Example:



&#x20;   Infrastructure

&#x20;       |

&#x20;       +--> EntryPointLoader

&#x20;       +--> ManifestLoader

&#x20;       +--> PluginPackageLoader

&#x20;       +--> NetworkAdapter

&#x20;       +--> FileSystemAdapter



Plugin code must not bypass the architecture.



================================================================================

58\. PLUGIN + CONFIGURATION SYSTEM

================================================================================



Configuration system manages:



&#x20;   plugin enablement

&#x20;   plugin selection

&#x20;   plugin configuration

&#x20;   plugin priorities



Example:



&#x20;   plugins:

&#x20;       broker.primary: broker.mt5

&#x20;       market\_data.primary: market.oanda



================================================================================

59\. PLUGIN + LOGGING

================================================================================



Every plugin receives a namespaced logger.



Example:



&#x20;   ShadBotTrader.plugin.broker.mt5



Logs should include:



&#x20;   plugin\_id

&#x20;   plugin\_version

&#x20;   correlation\_id



Sensitive credentials must never be logged.



================================================================================

60\. PLUGIN + METRICS

================================================================================



Metrics should be namespaced.



Example:



&#x20;   ShadBotTrader\_plugin\_requests\_total



with safe dimensions:



&#x20;   plugin\_id

&#x20;   operation

&#x20;   result



Avoid unbounded labels.



================================================================================

61\. PLUGIN + PROJECT INTELLIGENCE

================================================================================



Project Intelligence must inspect plugins.



It should detect:



&#x20;   installed plugins

&#x20;   plugin versions

&#x20;   manifests

&#x20;   dependencies

&#x20;   capabilities

&#x20;   enabled/disabled state

&#x20;   plugin configuration references



This becomes part of:



&#x20;   ProjectSnapshot

&#x20;   ProjectContext

&#x20;   DependencyGraph

&#x20;   Architecture Report



================================================================================

62\. PLUGIN + SELF LEARNING

================================================================================



Self Learning may consume plugin capabilities.



Example:



&#x20;   strategy plugin

&#x20;        |

&#x20;        v

&#x20;   performance data

&#x20;        |

&#x20;        v

&#x20;   learning system



Learning must not dynamically install arbitrary executable plugins without

explicit security policy.



================================================================================

63\. PLUGIN + AI

================================================================================



AI plugins may provide:



&#x20;   model providers

&#x20;   inference engines

&#x20;   training backends

&#x20;   embedding providers

&#x20;   feature extraction



Example:



&#x20;   AIProvider

&#x20;      |

&#x20;      +--> TensorFlow

&#x20;      +--> PyTorch

&#x20;      +--> ONNX

&#x20;      +--> External API



The AI Platform remains provider-independent.



================================================================================

64\. PLUGIN + TRADING

================================================================================



Trading plugins may provide:



&#x20;   broker

&#x20;   exchange

&#x20;   execution adapter

&#x20;   market data



Example:



&#x20;   BrokerPort

&#x20;       |

&#x20;       +--> MT5Plugin

&#x20;       +--> InteractiveBrokersPlugin

&#x20;       +--> BinancePlugin



All must comply with the same trading contracts.



================================================================================

65\. PLUGIN + SIMULATION

================================================================================



Simulation plugins may provide:



&#x20;   market simulator

&#x20;   slippage model

&#x20;   transaction cost model

&#x20;   execution model



Backtest must be able to select simulation implementations without changing

the Backtest Pipeline itself.



================================================================================

66\. PLUGIN + STORAGE

================================================================================



Storage plugins may provide:



&#x20;   SQL Server

&#x20;   PostgreSQL

&#x20;   filesystem

&#x20;   object storage

&#x20;   cache



Repositories remain stable.



Storage implementation changes behind infrastructure/plugin boundaries.



================================================================================

67\. PLUGIN + GUI

================================================================================



GUI may display:



&#x20;   plugin list

&#x20;   status

&#x20;   health

&#x20;   version

&#x20;   capabilities

&#x20;   configuration state



GUI must use Application Services rather than directly manipulating plugins.



================================================================================

68\. PLUGIN ADMINISTRATION

================================================================================



Future Plugin Administration capabilities:



&#x20;   list plugins

&#x20;   inspect plugin

&#x20;   enable

&#x20;   disable

&#x20;   configure

&#x20;   start

&#x20;   stop

&#x20;   health

&#x20;   update

&#x20;   rollback



Critical operations require authorization.



================================================================================

69\. PLUGIN DISCOVERY SECURITY

================================================================================



Never implement:



&#x20;   "load every .py file from plugins directory"



Instead:



&#x20;   discover candidates

&#x20;       |

&#x20;       v

&#x20;   validate manifest

&#x20;       |

&#x20;       v

&#x20;   verify contract

&#x20;       |

&#x20;       v

&#x20;   verify compatibility

&#x20;       |

&#x20;       v

&#x20;   approve

&#x20;       |

&#x20;       v

&#x20;   load



================================================================================

70\. PLUGIN TESTING

================================================================================



Every plugin must pass:



&#x20;   contract tests

&#x20;   unit tests

&#x20;   integration tests

&#x20;   compatibility tests



Provider plugins additionally require:



&#x20;   provider integration tests



================================================================================

71\. CONTRACT TESTING

================================================================================



All implementations of a common contract must pass the same contract suite.



Example:



&#x20;   BrokerContractTests



must pass for:



&#x20;   MT5Plugin

&#x20;   IBKRPlugin

&#x20;   BinancePlugin



This ensures interchangeable implementations.



================================================================================

72\. PLUGIN FAILURE TESTING

================================================================================



Test:



&#x20;   initialization failure

&#x20;   dependency failure

&#x20;   network failure

&#x20;   timeout

&#x20;   authentication failure

&#x20;   malformed response

&#x20;   shutdown failure

&#x20;   version incompatibility



================================================================================

73\. PLUGIN TEST ISOLATION

================================================================================



A broken plugin test must not corrupt:



&#x20;   Core

&#x20;   other plugin tests

&#x20;   global state



Each plugin should have isolated fixtures/resources.



================================================================================

74\. PLUGIN PERFORMANCE

================================================================================



Plugin abstraction must not introduce unnecessary overhead in hot paths.



Especially:



&#x20;   market ticks

&#x20;   feature computation

&#x20;   inference

&#x20;   order execution



For high-frequency operations:



&#x20;   resolve plugin once



rather than:



&#x20;   registry lookup per tick



================================================================================

75\. PLUGIN CACHING

================================================================================



Resolved plugin instances may be cached by:



&#x20;   PluginRegistry

&#x20;   Dependency Container



Plugin resolution must remain deterministic.



================================================================================

76\. PLUGIN THREAD SAFETY

================================================================================



Plugins must declare concurrency expectations.



Possible model:



&#x20;   SINGLE\_THREAD

&#x20;   THREAD\_SAFE

&#x20;   PROCESS\_SAFE

&#x20;   ASYNC\_SAFE



Core must not assume thread safety unless contract guarantees it.



================================================================================

77\. ASYNC PLUGINS

================================================================================



Plugin API must support async capabilities where required.



Example:



&#x20;   async market data provider



The architecture must not force all external I/O into synchronous execution.



================================================================================

78\. PLUGIN RESOURCE MANAGEMENT

================================================================================



Plugins are responsible for resources acquired through approved interfaces.



Examples:



&#x20;   sockets

&#x20;   sessions

&#x20;   threads

&#x20;   subprocesses

&#x20;   GPU contexts

&#x20;   model handles



stop()/unload() must release resources safely.



================================================================================

79\. PLUGIN PROCESS ISOLATION

================================================================================



Some future plugins may run out-of-process.



Architecture should permit:



&#x20;   Core

&#x20;      |

&#x20;      v

&#x20;   Plugin Adapter

&#x20;      |

&#x20;      v

&#x20;   Plugin Process



This is useful for:



&#x20;   untrusted providers

&#x20;   crash isolation

&#x20;   heavy workloads

&#x20;   incompatible dependencies



This is an extension, not mandatory for V1.



================================================================================

80\. PLUGIN COMMUNICATION MODES

================================================================================



Supported conceptual communication modes:



&#x20;   IN\_PROCESS

&#x20;   OUT\_OF\_PROCESS

&#x20;   EVENT\_BASED

&#x20;   RPC



Plugin contracts must remain independent of the transport where practical.



================================================================================

81\. PLUGIN DEPENDENCY INJECTION

================================================================================



Plugins receive dependencies through PluginContext / DI.



Forbidden:



&#x20;   import global\_container



Preferred:



&#x20;   PluginContext(

&#x20;       logger=...,

&#x20;       event\_bus=...,

&#x20;       configuration=...

&#x20;   )



================================================================================

82\. PLUGIN REGISTRY VS SERVICE REGISTRY

================================================================================



SERVICE REGISTRY:



&#x20;   application services



PLUGIN REGISTRY:



&#x20;   plugins/capabilities



ENGINE REGISTRY:



&#x20;   engines



Do not merge them into one universal registry.



================================================================================

83\. PLUGIN REGISTRY VS PROVIDER REGISTRY

================================================================================



Plugin Registry:



&#x20;   "Which plugins exist?"



Provider Registry:



&#x20;   "Which implementation provides this capability?"



Example:



&#x20;   PluginRegistry:

&#x20;       broker.mt5

&#x20;       broker.ibkr



&#x20;   ProviderRegistry:

&#x20;       BrokerPort -> broker.mt5



These are separate concepts.



================================================================================

84\. PLUGIN SELECTION

================================================================================



Selection algorithm conceptually:



&#x20;   capability requested

&#x20;       |

&#x20;       v

&#x20;   compatible plugins

&#x20;       |

&#x20;       v

&#x20;   enabled plugins

&#x20;       |

&#x20;       v

&#x20;   healthy plugins

&#x20;       |

&#x20;       v

&#x20;   configured priority

&#x20;       |

&#x20;       v

&#x20;   selected provider



================================================================================

85\. PLUGIN FALLBACK

================================================================================



Fallback must be explicit.



Example:



&#x20;   MarketData:



&#x20;       PRIMARY = Provider A

&#x20;       SECONDARY = Provider B



If A fails:



&#x20;   system policy determines whether B can be activated.



Never silently switch a live trading broker without explicit policy.



================================================================================

86\. CRITICAL PLUGIN SWITCHING

================================================================================



For critical systems:



&#x20;   Broker A

&#x20;      |

&#x20;      v

&#x20;   failure

&#x20;      |

&#x20;      v

&#x20;   risk policy

&#x20;      |

&#x20;      +--> HALT

&#x20;      |

&#x20;      +--> FAILOVER

&#x20;      |

&#x20;      +--> SAFE MODE



The Plugin Manager must not independently decide trading risk policy.



================================================================================

87\. PLUGIN CONFIGURATION CHANGE

================================================================================



Configuration change flow:



&#x20;   Change Request

&#x20;        |

&#x20;        v

&#x20;   Validation

&#x20;        |

&#x20;        v

&#x20;   Dependency Check

&#x20;        |

&#x20;        v

&#x20;   Plugin Policy

&#x20;        |

&#x20;        v

&#x20;   Apply

&#x20;        |

&#x20;        v

&#x20;   Health Check

&#x20;        |

&#x20;        v

&#x20;   Confirm / Rollback



================================================================================

88\. HOT RELOAD

================================================================================



Hot reload is NOT universally supported.



Allowed only when:



&#x20;   plugin declares reload capability

&#x20;   dependencies allow it

&#x20;   state migration is safe

&#x20;   operation is not critical



Live broker plugin hot replacement should normally require controlled

transition.



================================================================================

89\. PLUGIN SHUTDOWN

================================================================================



Shutdown order must be reverse dependency order.



Example:



&#x20;   Strategy

&#x20;      |

&#x20;      v

&#x20;   Feature

&#x20;      |

&#x20;      v

&#x20;   Data



Shutdown:



&#x20;   Strategy

&#x20;      |

&#x20;      v

&#x20;   Feature

&#x20;      |

&#x20;      v

&#x20;   Data



No dependent plugin may continue running after its required dependency has

been stopped.



================================================================================

90\. PLUGIN OBSERVABILITY

================================================================================



Track:



&#x20;   load time

&#x20;   initialization time

&#x20;   startup time

&#x20;   health state

&#x20;   operation count

&#x20;   failures

&#x20;   latency

&#x20;   restart count

&#x20;   last failure

&#x20;   current version



================================================================================

91\. PLUGIN AUDIT

================================================================================



Audit events:



&#x20;   installed

&#x20;   enabled

&#x20;   disabled

&#x20;   started

&#x20;   stopped

&#x20;   configured

&#x20;   updated

&#x20;   rolled back

&#x20;   failed



Critical plugin actions require audit records.



================================================================================

92\. PLUGIN DOCUMENTATION

================================================================================



Every plugin should provide:



&#x20;   README

&#x20;   manifest

&#x20;   configuration schema

&#x20;   capabilities

&#x20;   dependency information

&#x20;   compatibility

&#x20;   operational instructions

&#x20;   failure behavior



================================================================================

93\. PLUGIN PACKAGE STRUCTURE

================================================================================



Conceptual external plugin:



&#x20;   ShadBotTrader\_plugin\_example/

&#x20;       pyproject.toml

&#x20;       README.md

&#x20;       plugin.yaml



&#x20;       src/

&#x20;           ShadBotTrader\_plugin\_example/

&#x20;               \_\_init\_\_.py

&#x20;               plugin.py

&#x20;               services/

&#x20;               adapters/

&#x20;               models/



&#x20;       tests/

&#x20;           unit/

&#x20;           integration/

&#x20;           contract/



================================================================================

94\. INTERNAL PLUGIN STRUCTURE

================================================================================



Built-in plugins may live under:



&#x20;   src/ShadBotTrader/plugins/



with categories:



&#x20;   data/

&#x20;   brokers/

&#x20;   ai/

&#x20;   features/

&#x20;   strategies/

&#x20;   news/

&#x20;   storage/

&#x20;   simulation/



But built-in plugins must still respect the same contracts as external

plugins.



================================================================================

95\. PLUGIN API PACKAGE

================================================================================



A stable plugin-facing API should eventually exist:



&#x20;   ShadBotTrader.plugin\_api



It contains only:



&#x20;   contracts

&#x20;   interfaces

&#x20;   DTOs

&#x20;   capability definitions

&#x20;   lifecycle definitions

&#x20;   exceptions

&#x20;   context definitions



It must remain lightweight.



================================================================================

96\. PLUGIN INTERNAL API

================================================================================



Plugin implementations may have private modules.



Those are not guaranteed stable.



Example:



&#x20;   plugin.internal.\*



Core must never depend on those internals.



================================================================================

97\. PLUGIN DEPENDENCY ON CORE

================================================================================



Allowed:



&#x20;   Plugin

&#x20;      |

&#x20;      v

&#x20;   Stable Core/Plugin API



Forbidden:



&#x20;   Plugin

&#x20;      |

&#x20;      v

&#x20;   Core private implementation details



This protects Core refactoring freedom.



================================================================================

98\. PLUGIN ARCHITECTURE DEPENDENCY RULE

================================================================================



The dependency direction is:



&#x20;   Core

&#x20;     ^

&#x20;     |

&#x20;   Plugin API

&#x20;     ^

&#x20;     |

&#x20;   Plugin Implementations



Concrete plugins are at the outer architectural boundary.



================================================================================

99\. COMPLETE PLUGIN FLOW

================================================================================



PLUGIN DISCOVERY



&#x20;   filesystem/package/config

&#x20;             |

&#x20;             v

&#x20;       Candidate Plugin

&#x20;             |

&#x20;             v

&#x20;         Manifest

&#x20;             |

&#x20;             v

&#x20;         Validation

&#x20;             |

&#x20;             v

&#x20;      Dependency Resolver

&#x20;             |

&#x20;             v

&#x20;       Plugin Loader

&#x20;             |

&#x20;             v

&#x20;      Plugin Instance

&#x20;             |

&#x20;             v

&#x20;       Initialization

&#x20;             |

&#x20;             v

&#x20;          Startup

&#x20;             |

&#x20;             v

&#x20;          Health

&#x20;             |

&#x20;             v

&#x20;           ACTIVE

&#x20;             |

&#x20;             v

&#x20;         Operations

&#x20;             |

&#x20;             v

&#x20;          Shutdown

&#x20;             |

&#x20;             v

&#x20;          Unload



================================================================================

100\. COMPLETE SHADBOTTRADER PLUGIN ARCHITECTURE

================================================================================



&#x20;                        SHADBOTTRADER CORE

&#x20;                             |

&#x20;              +--------------+--------------+

&#x20;              |              |              |

&#x20;              v              v              v

&#x20;         Plugin API      Registry       Plugin Manager

&#x20;              |              |              |

&#x20;              +--------------+--------------+

&#x20;                             |

&#x20;                   +---------+---------+

&#x20;                   |         |         |

&#x20;                   v         v         v

&#x20;                 Data     Broker      AI

&#x20;                Plugin    Plugin    Plugin

&#x20;                   |         |         |

&#x20;                   +---------+---------+

&#x20;                             |

&#x20;                             v

&#x20;                        Capabilities

&#x20;                             |

&#x20;                             v

&#x20;                          Services

&#x20;                             |

&#x20;                             v

&#x20;                          Pipelines

&#x20;                             |

&#x20;                             v

&#x20;                        Application

&#x20;                             |

&#x20;                             v

&#x20;                           Domain





================================================================================

101\. FINAL ARCHITECTURAL RULES

================================================================================



RULE 01:

&#x20;   Core never depends on concrete plugins.



RULE 02:

&#x20;   Plugins implement contracts.



RULE 03:

&#x20;   Every plugin has stable identity.



RULE 04:

&#x20;   Every plugin declares version and API compatibility.



RULE 05:

&#x20;   Dependencies are explicit.



RULE 06:

&#x20;   Dependency graph must be acyclic.



RULE 07:

&#x20;   Plugin lifecycle is controlled by PluginManager.



RULE 08:

&#x20;   Registry and Manager are separate responsibilities.



RULE 09:

&#x20;   Plugin capabilities are explicit.



RULE 10:

&#x20;   Provider selection is configuration/policy driven.



RULE 11:

&#x20;   Critical plugin failure must follow Risk/Safety policy.



RULE 12:

&#x20;   Plugins never receive unrestricted Core access.



RULE 13:

&#x20;   Secrets never live inside plugin source code.



RULE 14:

&#x20;   Plugin communication uses contracts, services or events.



RULE 15:

&#x20;   Concrete vendor SDKs stay inside plugin boundaries.



RULE 16:

&#x20;   All implementations of a contract must pass contract tests.



RULE 17:

&#x20;   Plugin updates must support compatibility checks.



RULE 18:

&#x20;   Critical plugins require controlled update/replacement.



RULE 19:

&#x20;   Plugin state must be observable and auditable.



RULE 20:

&#x20;   Plugin architecture must never compromise Domain isolation.



================================================================================

102\. PHASE 9 COMPLETION CRITERIA

================================================================================



&#x20;   \[OK] Plugin definition

&#x20;   \[OK] Plugin contract

&#x20;   \[OK] Plugin identity

&#x20;   \[OK] Plugin metadata

&#x20;   \[OK] Plugin versioning

&#x20;   \[OK] Plugin API versioning

&#x20;   \[OK] Capability model

&#x20;   \[OK] Plugin Registry

&#x20;   \[OK] Plugin Manager

&#x20;   \[OK] Discovery

&#x20;   \[OK] Manifest

&#x20;   \[OK] Entrypoint

&#x20;   \[OK] Validation

&#x20;   \[OK] Lifecycle

&#x20;   \[OK] Plugin Context

&#x20;   \[OK] Isolation

&#x20;   \[OK] Dependency graph

&#x20;   \[OK] Load order

&#x20;   \[OK] Provider selection

&#x20;   \[OK] Configuration

&#x20;   \[OK] Secrets

&#x20;   \[OK] Health

&#x20;   \[OK] Failure handling

&#x20;   \[OK] Criticality

&#x20;   \[OK] Safe Mode

&#x20;   \[OK] Security boundary

&#x20;   \[OK] Permissions

&#x20;   \[OK] Compatibility

&#x20;   \[OK] Deprecation

&#x20;   \[OK] Enable/Disable

&#x20;   \[OK] Installation

&#x20;   \[OK] Update

&#x20;   \[OK] Rollback

&#x20;   \[OK] State migration

&#x20;   \[OK] Event integration

&#x20;   \[OK] Service integration

&#x20;   \[OK] Engine integration

&#x20;   \[OK] Pipeline integration

&#x20;   \[OK] Domain isolation

&#x20;   \[OK] Infrastructure integration

&#x20;   \[OK] Project Intelligence integration

&#x20;   \[OK] AI integration

&#x20;   \[OK] Trading integration

&#x20;   \[OK] Simulation integration

&#x20;   \[OK] Storage integration

&#x20;   \[OK] GUI integration

&#x20;   \[OK] Testing

&#x20;   \[OK] Contract testing

&#x20;   \[OK] Failure testing

&#x20;   \[OK] Performance

&#x20;   \[OK] Concurrency

&#x20;   \[OK] Async support

&#x20;   \[OK] Resource management

&#x20;   \[OK] Future process isolation

&#x20;   \[OK] Plugin API boundary

&#x20;   \[OK] Final dependency rules



================================================================================

END OF PHASE 9 — PLUGIN ARCHITECTURE

================================================================================

