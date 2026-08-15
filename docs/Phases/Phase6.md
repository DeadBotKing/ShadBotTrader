================================================================================

SHADBOT

ENTERPRISE AI TRADING PLATFORM

================================================================================



PHASE 6 — PIPELINE DESIGN

================================================================================



DOCUMENT STATUS:

&#x20;   ARCHITECTURE DESIGN COMPLETE



ARCHITECTURE BASELINE:

&#x20;   PHASE 1 → PHASE 27 = FROZEN



IMPLEMENTATION BASELINE:

&#x20;   PHASE 28+



PRIMARY ARCHITECTURAL STYLE:

&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   SOLID

&#x20;   Dependency Inversion

&#x20;   Dependency Injection

&#x20;   Event-Driven Architecture

&#x20;   Plugin Architecture

&#x20;   Modular Architecture

&#x20;   Explicit Runtime Lifecycle

&#x20;   Strong Typing

&#x20;   Production-Grade Design



================================================================================

1\. PURPOSE

================================================================================



Phase 6 defines the Pipeline Architecture of ShadBot.



The Pipeline Layer is responsible for orchestrating complete workflows.



Pipeline determines:



&#x20;   WHAT executes

&#x20;   WHEN it executes

&#x20;   IN WHAT ORDER it executes

&#x20;   UNDER WHICH EXECUTION POLICY it executes

&#x20;   WHAT STATE the workflow is in

&#x20;   WHAT HAPPENS on failure

&#x20;   WHAT HAPPENS on cancellation

&#x20;   WHAT CAN BE RETRIED

&#x20;   WHAT CAN BE CHECKPOINTED

&#x20;   WHAT EVENTS MUST BE PUBLISHED

&#x20;   WHAT THE FINAL EXECUTION RESULT IS



Pipeline does NOT implement:



&#x20;   Trading Strategy Logic

&#x20;   Neural Network Logic

&#x20;   Broker API Logic

&#x20;   Database Logic

&#x20;   Feature Mathematics

&#x20;   Domain Business Rules

&#x20;   GUI Logic

&#x20;   Plugin Discovery

&#x20;   Event Transport



Those responsibilities belong to the appropriate architectural layers.



================================================================================

2\. CORE ARCHITECTURAL PRINCIPLE

================================================================================



THE FUNDAMENTAL RULE OF PHASE 6:



&#x20;   PIPELINE DEFINES THE WORKFLOW.

&#x20;   PIPELINE DOES NOT IMPLEMENT THE BUSINESS CAPABILITY.



Therefore:



&#x20;   Pipeline

&#x20;       |

&#x20;       +--> determines WHAT

&#x20;       +--> determines ORDER

&#x20;       +--> determines EXECUTION POLICY

&#x20;       +--> controls STATE

&#x20;       +--> controls FAILURE

&#x20;       +--> controls RETRY

&#x20;       +--> controls CANCELLATION

&#x20;       +--> controls CHECKPOINTING

&#x20;       +--> publishes LIFECYCLE EVENTS

&#x20;       |

&#x20;       v

&#x20;   Service / Engine

&#x20;       |

&#x20;       v

&#x20;   Domain / Infrastructure



Example:



&#x20;   Training Pipeline

&#x20;       |

&#x20;       +--> Dataset Validation

&#x20;       +--> Feature Preparation

&#x20;       +--> Training

&#x20;       +--> Evaluation

&#x20;       +--> Model Validation

&#x20;       +--> Model Registration



The Pipeline orchestrates these operations.



The AI Engine performs model computation.



The Feature Platform performs feature computation.



The Data Platform provides data.



The Model Registry stores model artifacts.



================================================================================

3\. ARCHITECTURAL POSITION

================================================================================



ShadBot global hierarchy:



&#x20;   SHADBOT

&#x20;      |

&#x20;      +--> PLATFORM

&#x20;             |

&#x20;             +--> MODULE

&#x20;                    |

&#x20;                    +--> SERVICE

&#x20;                           |

&#x20;                           +--> ENGINE





Pipeline exists as the workflow orchestration mechanism around these

capabilities.



Conceptually:



&#x20;   Presentation / CLI / GUI

&#x20;            |

&#x20;            v

&#x20;       Application

&#x20;            |

&#x20;            v

&#x20;    Pipeline Orchestration

&#x20;            |

&#x20;            v

&#x20;         Services

&#x20;            |

&#x20;            v

&#x20;         Engines

&#x20;            |

&#x20;            v

&#x20;          Domain





Infrastructure implementations are injected from outside the core workflow.



================================================================================

4\. PIPELINE VOCABULARY

================================================================================



4.1 PIPELINE



A named, versioned workflow consisting of ordered stages.



Examples:



&#x20;   Dataset Update Pipeline

&#x20;   Feature Pipeline

&#x20;   Training Pipeline

&#x20;   Prediction Pipeline

&#x20;   Decision Pipeline

&#x20;   Live Trading Pipeline

&#x20;   Backtest Pipeline

&#x20;   Replay Pipeline

&#x20;   Optimization Pipeline





4.2 PIPELINE DEFINITION



Immutable description of a pipeline.



Contains conceptually:



&#x20;   pipeline\_id

&#x20;   name

&#x20;   version

&#x20;   stages

&#x20;   execution\_policy

&#x20;   retry\_policy

&#x20;   timeout\_policy

&#x20;   cancellation\_policy

&#x20;   checkpoint\_policy

&#x20;   execution\_mode

&#x20;   metadata



Definition describes a workflow.



Definition does NOT execute the workflow.





4.3 PIPELINE STAGE



A single independently executable workflow unit.



Each Stage:



&#x20;   has an identity

&#x20;   has one responsibility

&#x20;   validates required input

&#x20;   executes its operation

&#x20;   produces controlled output

&#x20;   reports execution state



A Stage must not secretly execute unrelated stages.





4.4 PIPELINE CONTEXT



Controlled execution context shared by stages.



Conceptual contents:



&#x20;   execution\_id

&#x20;   pipeline\_id

&#x20;   pipeline\_version

&#x20;   run\_mode

&#x20;   created\_at

&#x20;   started\_at

&#x20;   current\_stage

&#x20;   execution\_state

&#x20;   inputs

&#x20;   outputs

&#x20;   artifacts

&#x20;   metrics

&#x20;   warnings

&#x20;   errors

&#x20;   metadata

&#x20;   cancellation\_state

&#x20;   checkpoint\_state



Pipeline Context MUST NOT become an uncontrolled global dictionary.



Typed models are preferred.





4.5 PIPELINE EXECUTION



One actual execution of one Pipeline Definition.



Every execution has:



&#x20;   execution\_id



Two executions of the same Pipeline Definition are two independent executions.





4.6 PIPELINE RESULT



Final result of a Pipeline Execution.



Conceptual states:



&#x20;   SUCCESS

&#x20;   FAILED

&#x20;   CANCELLED

&#x20;   PARTIAL

&#x20;   SKIPPED



Implementation must use typed states/enums rather than arbitrary strings.





4.7 PIPELINE RUNNER



Runtime component responsible for executing a Pipeline Definition.





4.8 PIPELINE REGISTRY



Responsible for discovering and resolving registered pipelines.



Must integrate with Plugin Architecture.



Must NOT duplicate Plugin discovery/loading.





4.9 PIPELINE EXECUTION STORE



Abstraction responsible for persistence of:



&#x20;   execution state

&#x20;   stage state

&#x20;   checkpoints

&#x20;   execution metadata

&#x20;   final results



Possible implementations:



&#x20;   InMemoryExecutionStore

&#x20;   SqlServerExecutionStore

&#x20;   DiagnosticExecutionStore



Pipeline depends only on the abstraction.



================================================================================

5\. PIPELINE ARCHITECTURE

================================================================================



Canonical structure:



&#x20;   Pipeline Definition

&#x20;           |

&#x20;           v

&#x20;     Pipeline Runner

&#x20;           |

&#x20;           v

&#x20;     Pipeline Execution

&#x20;           |

&#x20;           v

&#x20;      Pipeline Context

&#x20;           |

&#x20;           v

&#x20;   +-------+-------+-------+

&#x20;   |       |       |       |

&#x20;Stage 1  Stage 2  Stage 3  ...

&#x20;   |       |       |

&#x20;   +-------+-------+

&#x20;           |

&#x20;           v

&#x20;     Pipeline Result





Supporting infrastructure:



&#x20;   Dependency Container

&#x20;           |

&#x20;           +--> Pipeline Runner

&#x20;           +--> Pipeline Registry

&#x20;           +--> Execution Store

&#x20;           +--> Event Bus

&#x20;           +--> Logger

&#x20;           +--> Clock

&#x20;           +--> Configuration



================================================================================

6\. PIPELINE LIFECYCLE

================================================================================



NORMAL:



&#x20;   CREATED

&#x20;      |

&#x20;      v

&#x20;   VALIDATING

&#x20;      |

&#x20;      v

&#x20;   INITIALIZING

&#x20;      |

&#x20;      v

&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   COMPLETING

&#x20;      |

&#x20;      v

&#x20;   COMPLETED





FAILURE:



&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   FAILING

&#x20;      |

&#x20;      v

&#x20;   FAILED





CANCELLATION:



&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   CANCELLATION\_REQUESTED

&#x20;      |

&#x20;      v

&#x20;   CANCELLING

&#x20;      |

&#x20;      v

&#x20;   CANCELLED





Pipeline state must be represented by a dedicated typed state model.



================================================================================

7\. STAGE LIFECYCLE

================================================================================



NORMAL:



&#x20;   PENDING

&#x20;      |

&#x20;      v

&#x20;   VALIDATING

&#x20;      |

&#x20;      v

&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   COMPLETED





FAILURE:



&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   FAILED

&#x20;      |

&#x20;      v

&#x20;   RETRYING

&#x20;      |

&#x20;      +------> RUNNING





OTHER:



&#x20;   SKIPPED

&#x20;   CANCELLED





A Stage reports its state to the Pipeline Runner.



A Stage must not bypass Pipeline execution control.



================================================================================

8\. GENERIC PIPELINE EXECUTION

================================================================================



&#x20;   Request

&#x20;     |

&#x20;     v

&#x20;   Resolve Pipeline

&#x20;     |

&#x20;     v

&#x20;   Validate Definition

&#x20;     |

&#x20;     v

&#x20;   Create Execution

&#x20;     |

&#x20;     v

&#x20;   Create Context

&#x20;     |

&#x20;     v

&#x20;   Publish PipelineStarted

&#x20;     |

&#x20;     v

&#x20;   Initialize

&#x20;     |

&#x20;     v

&#x20;   Execute Stage 1

&#x20;     |

&#x20;     v

&#x20;   Execute Stage 2

&#x20;     |

&#x20;     v

&#x20;   Execute Stage N

&#x20;     |

&#x20;     v

&#x20;   Finalize

&#x20;     |

&#x20;     v

&#x20;   Persist Result

&#x20;     |

&#x20;     v

&#x20;   Publish PipelineCompleted

&#x20;     |

&#x20;     v

&#x20;   Return Result





FAILURE:



&#x20;   Stage Failure

&#x20;       |

&#x20;       v

&#x20;   Capture Error

&#x20;       |

&#x20;       v

&#x20;   Update Stage State

&#x20;       |

&#x20;       v

&#x20;   Evaluate Retry Policy

&#x20;       |

&#x20;       +--> RETRY

&#x20;       |

&#x20;       +--> NO RETRY

&#x20;               |

&#x20;               v

&#x20;            Pipeline Failed

&#x20;               |

&#x20;               v

&#x20;            Persist Failure

&#x20;               |

&#x20;               v

&#x20;            Publish Failure Event



================================================================================

9\. PIPELINE RUNNER RESPONSIBILITIES

================================================================================



PipelineRunner MUST:



&#x20;   1. Resolve Pipeline Definition.

&#x20;   2. Validate Pipeline Definition.

&#x20;   3. Validate Pipeline Request.

&#x20;   4. Create unique execution identity.

&#x20;   5. Create Pipeline Context.

&#x20;   6. Initialize execution state.

&#x20;   7. Publish lifecycle events.

&#x20;   8. Execute stages in declared order.

&#x20;   9. Validate stage prerequisites.

&#x20;   10. Update stage state.

&#x20;   11. Apply retry policy.

&#x20;   12. Monitor cancellation.

&#x20;   13. Create checkpoints where configured.

&#x20;   14. Persist execution state where required.

&#x20;   15. Finalize execution.

&#x20;   16. Publish completion/failure events.

&#x20;   17. Return PipelineResult.



PipelineRunner MUST NOT implement business logic.



================================================================================

10\. PIPELINE REGISTRY

================================================================================



PipelineRegistry responsibilities:



&#x20;   register pipeline

&#x20;   resolve pipeline

&#x20;   resolve pipeline version

&#x20;   validate duplicate registration

&#x20;   expose available pipelines



Integration:



&#x20;   Plugin

&#x20;      |

&#x20;      v

&#x20;   Plugin Loader

&#x20;      |

&#x20;      v

&#x20;   Pipeline Registration

&#x20;      |

&#x20;      v

&#x20;   Pipeline Registry

&#x20;      |

&#x20;      v

&#x20;   Pipeline Runner



PipelineRegistry must NOT become another Plugin Manager.



================================================================================

11\. EXECUTION STORE

================================================================================



ExecutionStore abstraction supports:



&#x20;   create execution

&#x20;   update execution state

&#x20;   update stage state

&#x20;   save checkpoint

&#x20;   retrieve execution

&#x20;   retrieve checkpoint

&#x20;   persist final result



Conceptual implementation:



&#x20;   PipelineRunner

&#x20;         |

&#x20;         v

&#x20;   ExecutionStore

&#x20;         |

&#x20;         +--> InMemory

&#x20;         +--> SQL Server

&#x20;         +--> Diagnostic Storage



Concrete persistence belongs to Infrastructure.



================================================================================

12\. EVENT BUS INTEGRATION

================================================================================



Pipeline uses the Event Bus defined by Phase 10.



Canonical lifecycle events:



&#x20;   PipelineCreated

&#x20;   PipelineStarted

&#x20;   PipelineStageStarted

&#x20;   PipelineStageCompleted

&#x20;   PipelineStageFailed

&#x20;   PipelineRetryRequested

&#x20;   PipelineCheckpointCreated

&#x20;   PipelineCancellationRequested

&#x20;   PipelineCancelled

&#x20;   PipelineCompleted

&#x20;   PipelineFailed



Events should contain:



&#x20;   execution\_id

&#x20;   pipeline\_id

&#x20;   pipeline\_version

&#x20;   stage\_id (when applicable)

&#x20;   timestamp



Business/domain events remain separate from pipeline lifecycle events.



================================================================================

13\. ERROR MODEL

================================================================================



Error categories:



&#x20;   ValidationError

&#x20;   ConfigurationError

&#x20;   DependencyError

&#x20;   DataError

&#x20;   StageError

&#x20;   ExecutionError

&#x20;   ExternalServiceError

&#x20;   CancellationError

&#x20;   SystemError



Failure information must preserve:



&#x20;   execution\_id

&#x20;   pipeline\_id

&#x20;   stage\_id

&#x20;   timestamp

&#x20;   error category

&#x20;   message

&#x20;   retry count

&#x20;   diagnostic metadata



Secrets MUST NEVER be included.



================================================================================

14\. RETRY POLICY

================================================================================



Retry is policy-driven.



Potentially retryable:



&#x20;   temporary network failure

&#x20;   transient database failure

&#x20;   temporary external service failure

&#x20;   temporary broker failure



Normally not retryable:



&#x20;   invalid configuration

&#x20;   invalid domain input

&#x20;   invalid dataset

&#x20;   model validation failure

&#x20;   permanent authentication failure

&#x20;   deterministic business-rule violation



Retry policy may contain:



&#x20;   maximum\_attempts

&#x20;   backoff\_strategy

&#x20;   delay

&#x20;   timeout

&#x20;   retryable\_error\_categories



================================================================================

15\. IDEMPOTENCY

================================================================================



Any Stage producing external side effects must define idempotency.



Examples:



&#x20;   Dataset ingestion

&#x20;       --> prevent duplicate records



&#x20;   Order creation

&#x20;       --> prevent duplicate orders



&#x20;   Model registration

&#x20;       --> prevent accidental version overwrite



&#x20;   Portfolio update

&#x20;       --> preserve transaction identity



Every execution receives a unique execution\_id.



External side effects should use correlation/idempotency identifiers.



================================================================================

16\. CANCELLATION

================================================================================



Long-running workflows must support controlled cancellation.



Flow:



&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   CANCELLATION\_REQUESTED

&#x20;      |

&#x20;      v

&#x20;   Stage observes cancellation

&#x20;      |

&#x20;      v

&#x20;   Controlled cleanup

&#x20;      |

&#x20;      v

&#x20;   CANCELLED



Cancellation must not corrupt execution state.



Resources must be released deterministically.



================================================================================

17\. CHECKPOINTING

================================================================================



Long-running pipelines may define checkpoints.



Example:



&#x20;   Stage 1

&#x20;      |

&#x20;      v

&#x20;   Checkpoint A

&#x20;      |

&#x20;      v

&#x20;   Stage 2

&#x20;      |

&#x20;      v

&#x20;   Checkpoint B

&#x20;      |

&#x20;      v

&#x20;   Stage 3



Checkpoint should identify:



&#x20;   pipeline\_id

&#x20;   pipeline\_version

&#x20;   execution\_id

&#x20;   completed\_stage

&#x20;   state/artifact references

&#x20;   version information

&#x20;   timestamp



Only pipelines explicitly supporting resume may resume.



Resume MUST validate version compatibility.



================================================================================

18\. DATASET UPDATE PIPELINE

================================================================================



PURPOSE:



Acquire, validate, normalize, deduplicate and persist market data.



FLOW:



&#x20;   External Source

&#x20;        |

&#x20;        v

&#x20;   Acquire

&#x20;        |

&#x20;        v

&#x20;   Validate

&#x20;        |

&#x20;        v

&#x20;   Normalize

&#x20;        |

&#x20;        v

&#x20;   Deduplicate

&#x20;        |

&#x20;        v

&#x20;   Data Quality Check

&#x20;        |

&#x20;        v

&#x20;   Persist Raw/Processed Data

&#x20;        |

&#x20;        v

&#x20;   Update Dataset Metadata

&#x20;        |

&#x20;        v

&#x20;   Publish DatasetUpdated



Data Platform owns actual data operations.



Pipeline owns orchestration.



================================================================================

19\. FEATURE PIPELINE

================================================================================



PURPOSE:



Transform validated market data into versioned model-ready features.



FLOW:



&#x20;   Dataset

&#x20;      |

&#x20;      v

&#x20;   Load

&#x20;      |

&#x20;      v

&#x20;   Validate

&#x20;      |

&#x20;      v

&#x20;   Feature Calculation

&#x20;      |

&#x20;      v

&#x20;   Multi-Timeframe Processing

&#x20;      |

&#x20;      v

&#x20;   Feature Validation

&#x20;      |

&#x20;      v

&#x20;   Feature Versioning

&#x20;      |

&#x20;      v

&#x20;   Feature Store / Persistence



Feature mathematics belongs to Feature Platform.



================================================================================

20\. TRAINING PIPELINE

================================================================================



PURPOSE:



Train, evaluate, validate, version and register models.



FLOW:



&#x20;   Dataset

&#x20;      |

&#x20;      v

&#x20;   Dataset Validation

&#x20;      |

&#x20;      v

&#x20;   Feature Preparation

&#x20;      |

&#x20;      v

&#x20;   Train/Validation/Test Split

&#x20;      |

&#x20;      v

&#x20;   Model Construction

&#x20;      |

&#x20;      v

&#x20;   Training

&#x20;      |

&#x20;      v

&#x20;   Evaluation

&#x20;      |

&#x20;      v

&#x20;   Model Quality Gate

&#x20;      |

&#x20;      +---- FAIL ----> Reject Model

&#x20;      |

&#x20;      v

&#x20;   Model Versioning

&#x20;      |

&#x20;      v

&#x20;   Model Registry

&#x20;      |

&#x20;      v

&#x20;   Training Report



AI Platform owns model computation.



Pipeline owns orchestration.



================================================================================

21\. PREDICTION PIPELINE

================================================================================



PURPOSE:



Generate a validated prediction from current market context.



FLOW:



&#x20;   Market Data

&#x20;      |

&#x20;      v

&#x20;   Context Construction

&#x20;      |

&#x20;      v

&#x20;   Feature Retrieval / Generation

&#x20;      |

&#x20;      v

&#x20;   Feature Validation

&#x20;      |

&#x20;      v

&#x20;   Model Resolution

&#x20;      |

&#x20;      v

&#x20;   Inference

&#x20;      |

&#x20;      v

&#x20;   Prediction Validation

&#x20;      |

&#x20;      v

&#x20;   Prediction Result

&#x20;      |

&#x20;      v

&#x20;   Prediction Event



================================================================================

22\. DECISION PIPELINE

================================================================================



PURPOSE:



Convert prediction and context into an actionable trading decision.



FLOW:



&#x20;   Prediction

&#x20;      |

&#x20;      v

&#x20;   Market Context

&#x20;      |

&#x20;      v

&#x20;   Strategy / Decision Logic

&#x20;      |

&#x20;      v

&#x20;   Risk Evaluation

&#x20;      |

&#x20;      v

&#x20;   Decision Validation

&#x20;      |

&#x20;      v

&#x20;   Trading Decision



Strategy logic does not belong to Pipeline.



================================================================================

23\. LIVE TRADING PIPELINE

================================================================================



PURPOSE:



Execute controlled real-time trading workflow.



FLOW:



&#x20;   Market Event

&#x20;       |

&#x20;       v

&#x20;   Market Data Validation

&#x20;       |

&#x20;       v

&#x20;   Context Construction

&#x20;       |

&#x20;       v

&#x20;   Feature Generation / Retrieval

&#x20;       |

&#x20;       v

&#x20;   AI Prediction

&#x20;       |

&#x20;       v

&#x20;   Decision

&#x20;       |

&#x20;       v

&#x20;   Risk Evaluation

&#x20;       |

&#x20;       +---- REJECT ----> No Execution

&#x20;       |

&#x20;       v

&#x20;   Order Creation

&#x20;       |

&#x20;       v

&#x20;   Order Validation

&#x20;       |

&#x20;       v

&#x20;   Broker Execution

&#x20;       |

&#x20;       v

&#x20;   Execution Result

&#x20;       |

&#x20;       v

&#x20;   Position Update

&#x20;       |

&#x20;       v

&#x20;   Portfolio Update

&#x20;       |

&#x20;       v

&#x20;   Events / Audit / Metrics





MANDATORY SAFETY REQUIREMENTS:



&#x20;   risk limits

&#x20;   duplicate-order protection

&#x20;   broker failure handling

&#x20;   execution tracking

&#x20;   auditability

&#x20;   emergency cancellation

&#x20;   live/simulation isolation



================================================================================

24\. BACKTEST PIPELINE

================================================================================



PURPOSE:



Evaluate strategy/model against historical data without look-ahead bias.



FLOW:



&#x20;   Historical Dataset

&#x20;         |

&#x20;         v

&#x20;   Dataset Validation

&#x20;         |

&#x20;         v

&#x20;   Simulation Initialization

&#x20;         |

&#x20;         v

&#x20;   Advance Time

&#x20;         |

&#x20;         v

&#x20;   Current Market State

&#x20;         |

&#x20;         v

&#x20;   Feature Calculation

&#x20;         |

&#x20;         v

&#x20;   Prediction

&#x20;         |

&#x20;         v

&#x20;   Decision

&#x20;         |

&#x20;         v

&#x20;   Risk

&#x20;         |

&#x20;         v

&#x20;   Simulated Execution

&#x20;         |

&#x20;         v

&#x20;   Portfolio Update

&#x20;         |

&#x20;         v

&#x20;   Metrics

&#x20;         |

&#x20;         +------> Next Time Step

&#x20;                        |

&#x20;                        v

&#x20;                     Complete

&#x20;                        |

&#x20;                        v

&#x20;                  Backtest Report





CRITICAL RULE:



&#x20;   NO FUTURE INFORMATION



The Pipeline must preserve temporal causality.



================================================================================

25\. REPLAY PIPELINE

================================================================================



PURPOSE:



Reproduce historical event flow.



FLOW:



&#x20;   Historical Events

&#x20;         |

&#x20;         v

&#x20;   Replay Scheduler

&#x20;         |

&#x20;         v

&#x20;   Event Injection

&#x20;         |

&#x20;         v

&#x20;   Normal Runtime Workflow

&#x20;         |

&#x20;         v

&#x20;   Observed Results

&#x20;         |

&#x20;         v

&#x20;   Replay Report



Replay should reuse normal runtime capabilities where possible.



================================================================================

26\. OPTIMIZATION PIPELINE

================================================================================



PURPOSE:



Search strategy/model/configuration parameter space.



FLOW:



&#x20;   Parameter Space

&#x20;        |

&#x20;        v

&#x20;   Candidate Generation

&#x20;        |

&#x20;        v

&#x20;   Experiment

&#x20;        |

&#x20;        v

&#x20;   Backtest / Simulation

&#x20;        |

&#x20;        v

&#x20;   Metrics

&#x20;        |

&#x20;        v

&#x20;   Evaluation

&#x20;        |

&#x20;        +---- More Candidates

&#x20;        |

&#x20;        v

&#x20;   Stop Condition

&#x20;        |

&#x20;        v

&#x20;   Best Candidate

&#x20;        |

&#x20;        v

&#x20;   Optimization Report



Optimization must be isolated from Live Production Execution.



================================================================================

27\. PORTFOLIO / RISK PIPELINE

================================================================================



Where portfolio-level orchestration is required:



&#x20;   Portfolio State

&#x20;        |

&#x20;        v

&#x20;   Exposure Analysis

&#x20;        |

&#x20;        v

&#x20;   Risk Limits

&#x20;        |

&#x20;        v

&#x20;   Position Sizing

&#x20;        |

&#x20;        v

&#x20;   Portfolio Decision



Risk rules remain Domain/Service responsibilities.



================================================================================

28\. PIPELINE COMPOSITION

================================================================================



Pipelines can compose capabilities.



Example:



&#x20;   Dataset Update

&#x20;        |

&#x20;        v

&#x20;   Feature Pipeline

&#x20;        |

&#x20;        v

&#x20;   Training Pipeline

&#x20;        |

&#x20;        v

&#x20;   Evaluation

&#x20;        |

&#x20;        v

&#x20;   Model Registration





Live:



&#x20;   Market Data

&#x20;        |

&#x20;        v

&#x20;   Prediction Pipeline

&#x20;        |

&#x20;        v

&#x20;   Decision Pipeline

&#x20;        |

&#x20;        v

&#x20;   Risk

&#x20;        |

&#x20;        v

&#x20;   Execution



Composition must use explicit contracts.



No pipeline may access another pipeline's private implementation.



================================================================================

29\. PIPELINE INPUT / OUTPUT CONTRACT

================================================================================



PipelineRequest conceptually contains:



&#x20;   execution configuration

&#x20;   symbols

&#x20;   timeframes

&#x20;   date/range

&#x20;   model identity

&#x20;   strategy identity

&#x20;   execution mode

&#x20;   runtime options





PipelineResult conceptually contains:



&#x20;   status

&#x20;   execution\_id

&#x20;   outputs

&#x20;   metrics

&#x20;   artifacts

&#x20;   warnings

&#x20;   errors



Internal mutable execution state must not become the public API.



================================================================================

30\. EXECUTION MODES

================================================================================



Supported conceptual modes:



&#x20;   LIVE

&#x20;   PAPER

&#x20;   BACKTEST

&#x20;   REPLAY

&#x20;   TRAINING

&#x20;   VALIDATION

&#x20;   OPTIMIZATION



Execution mode must be explicit.



Example:



&#x20;   LIVE

&#x20;      |

&#x20;      +--> LiveExecutionEngine



&#x20;   PAPER

&#x20;      |

&#x20;      +--> PaperExecutionEngine



&#x20;   BACKTEST

&#x20;      |

&#x20;      +--> SimulationExecutionEngine



The orchestration contract remains stable.



The concrete execution capability changes.



================================================================================

31\. CONCURRENCY

================================================================================



Pipelines may support:



&#x20;   sequential execution

&#x20;   asynchronous execution

&#x20;   controlled concurrent execution



Concurrency MUST be explicit.



The runtime supporting async does not mean every trading workflow should be concurrent.



Critical trading operations must preserve ordering and consistency.



Concurrency mechanics belong to Framework/Runtime.



Pipeline defines semantics.



================================================================================

32\. RESOURCE MANAGEMENT

================================================================================



Pipelines may use:



&#x20;   database sessions

&#x20;   network connections

&#x20;   files

&#x20;   model resources

&#x20;   broker sessions

&#x20;   large datasets

&#x20;   memory-heavy artifacts



Resources must be released on:



&#x20;   success

&#x20;   failure

&#x20;   cancellation



Cleanup must be deterministic.



================================================================================

33\. CONFIGURATION

================================================================================



Pipeline configuration comes from the Configuration System.



Possible configuration:



&#x20;   enabled

&#x20;   disabled

&#x20;   timeout

&#x20;   retry policy

&#x20;   checkpoint policy

&#x20;   execution mode

&#x20;   resource limits

&#x20;   pipeline version

&#x20;   stage configuration



Secrets MUST NOT be hardcoded.



================================================================================

34\. PLUGIN INTEGRATION

================================================================================



Plugins may provide:



&#x20;   new pipelines

&#x20;   new stages

&#x20;   new execution implementations



Flow:



&#x20;   Plugin

&#x20;      |

&#x20;      v

&#x20;   Plugin Loader

&#x20;      |

&#x20;      v

&#x20;   Registration

&#x20;      |

&#x20;      v

&#x20;   Pipeline Registry

&#x20;      |

&#x20;      v

&#x20;   Pipeline Runner



Pipeline code must not duplicate Plugin discovery/loading.



================================================================================

35\. DEPENDENCY INJECTION

================================================================================



Pipeline dependencies are resolved through Dependency Container.



Conceptual dependencies:



&#x20;   Dependency Container

&#x20;         |

&#x20;         +--> PipelineRunner

&#x20;         +--> PipelineRegistry

&#x20;         +--> ExecutionStore

&#x20;         +--> EventBus

&#x20;         +--> Logger

&#x20;         +--> Clock

&#x20;         +--> Configuration



No global service locator should be required by a Stage.



Concrete Infrastructure is injected at composition/bootstrap time.



================================================================================

36\. OBSERVABILITY

================================================================================



Every execution should expose:



&#x20;   execution\_id

&#x20;   pipeline\_id

&#x20;   pipeline\_version

&#x20;   stage\_id

&#x20;   status

&#x20;   duration

&#x20;   retry\_count

&#x20;   metrics

&#x20;   warnings

&#x20;   errors



Useful metrics:



&#x20;   total execution duration

&#x20;   stage duration

&#x20;   throughput

&#x20;   failure count

&#x20;   retry count

&#x20;   processed data volume

&#x20;   inference latency

&#x20;   training metrics

&#x20;   execution latency



Logging follows Phase 22.



================================================================================

37\. SECURITY

================================================================================



Pipeline execution must respect:



&#x20;   secret isolation

&#x20;   credential isolation

&#x20;   permission boundaries

&#x20;   audit logging

&#x20;   live-trading safeguards

&#x20;   configuration security



Secrets must NEVER appear in:



&#x20;   logs

&#x20;   events

&#x20;   errors

&#x20;   generated reports

&#x20;   pipeline context

&#x20;   source code



================================================================================

38\. TESTING ARCHITECTURE

================================================================================



Every Pipeline requires:



UNIT TESTS



&#x20;   Stage behavior

&#x20;   Dependency behavior

&#x20;   Input validation





PIPELINE TESTS



&#x20;   stage ordering

&#x20;   context propagation

&#x20;   success

&#x20;   failure

&#x20;   retry

&#x20;   cancellation

&#x20;   checkpointing





INTEGRATION TESTS



&#x20;   Data Platform

&#x20;   Feature Platform

&#x20;   AI Platform

&#x20;   Trading Platform

&#x20;   Portfolio Platform

&#x20;   Storage





END-TO-END TESTS



Example:



&#x20;   Dataset

&#x20;      |

&#x20;      v

&#x20;   Features

&#x20;      |

&#x20;      v

&#x20;   Model

&#x20;      |

&#x20;      v

&#x20;   Prediction

&#x20;      |

&#x20;      v

&#x20;   Decision

&#x20;      |

&#x20;      v

&#x20;   Risk

&#x20;      |

&#x20;      v

&#x20;   Simulated Execution



Real broker execution must remain isolated behind controlled tests.



================================================================================

39\. STRICT ARCHITECTURAL BOUNDARIES

================================================================================



MANDATORY:



&#x20;   Pipeline != Domain

&#x20;   Pipeline != Engine

&#x20;   Pipeline != Service

&#x20;   Pipeline != Repository

&#x20;   Pipeline != Plugin Loader

&#x20;   Pipeline != Event Bus

&#x20;   Pipeline != GUI

&#x20;   Pipeline != Database



RESPONSIBILITIES:



&#x20;   Pipeline

&#x20;       = workflow orchestration



&#x20;   Service

&#x20;       = application/domain operation



&#x20;   Engine

&#x20;       = specialized computation/execution



&#x20;   Domain

&#x20;       = business model and business rules



&#x20;   Infrastructure

&#x20;       = persistence and external technical access



&#x20;   Event Bus

&#x20;       = event transport and dispatch



&#x20;   Plugin System

&#x20;       = extension discovery and loading



================================================================================

40\. GLOBAL SHADBOT DATA FLOW

================================================================================



&#x20;   External Sources

&#x20;         |

&#x20;         v

&#x20;   Data Platform

&#x20;         |

&#x20;         v

&#x20;   Validated Market Data

&#x20;         |

&#x20;         v

&#x20;   Feature Platform

&#x20;         |

&#x20;         v

&#x20;   Feature Context

&#x20;         |

&#x20;         v

&#x20;   AI Platform

&#x20;         |

&#x20;         v

&#x20;   Prediction

&#x20;         |

&#x20;         v

&#x20;   Trading / Decision

&#x20;         |

&#x20;         v

&#x20;   Risk

&#x20;         |

&#x20;         v

&#x20;   Execution

&#x20;         |

&#x20;         v

&#x20;   Portfolio

&#x20;         |

&#x20;         v

&#x20;   Events / Storage / Analytics



Simulation changes execution implementation,

not the entire business workflow.



================================================================================

41\. CANONICAL LIVE TRADING CYCLE

================================================================================



&#x20;   Market Event

&#x20;       |

&#x20;       v

&#x20;   Market Data Validation

&#x20;       |

&#x20;       v

&#x20;   Context Construction

&#x20;       |

&#x20;       v

&#x20;   Feature Retrieval / Generation

&#x20;       |

&#x20;       v

&#x20;   Model Resolution

&#x20;       |

&#x20;       v

&#x20;   Inference

&#x20;       |

&#x20;       v

&#x20;   Prediction Validation

&#x20;       |

&#x20;       v

&#x20;   Decision

&#x20;       |

&#x20;       v

&#x20;   Risk Evaluation

&#x20;       |

&#x20;       +---- REJECT ----> No Execution

&#x20;       |

&#x20;       v

&#x20;   Order Creation

&#x20;       |

&#x20;       v

&#x20;   Order Validation

&#x20;       |

&#x20;       v

&#x20;   Execution

&#x20;       |

&#x20;       v

&#x20;   Portfolio Update

&#x20;       |

&#x20;       v

&#x20;   Audit + Metrics + Events



================================================================================

42\. NON-GOALS

================================================================================



Phase 6 MUST NOT:



&#x20;   implement trading strategy

&#x20;   implement neural networks

&#x20;   implement broker APIs

&#x20;   implement database queries

&#x20;   implement feature mathematics

&#x20;   own domain entities

&#x20;   replace Services

&#x20;   replace Engines

&#x20;   replace Event Bus

&#x20;   replace Plugin Architecture

&#x20;   contain GUI logic

&#x20;   contain secrets

&#x20;   create uncontrolled global state



================================================================================

43\. CONCEPTUAL IMPLEMENTATION TARGET

================================================================================



When Pipeline subsystem implementation begins,

the generic kernel should conceptually contain:



&#x20;   pipeline/

&#x20;       core/

&#x20;           definition

&#x20;           stage

&#x20;           context

&#x20;           execution

&#x20;           state

&#x20;           result

&#x20;           runner

&#x20;           registry

&#x20;           policies



&#x20;       storage/

&#x20;           execution\_store



&#x20;       events/

&#x20;           pipeline\_events



&#x20;       definitions/

&#x20;           dataset\_update

&#x20;           feature

&#x20;           training

&#x20;           prediction

&#x20;           decision

&#x20;           live\_trading

&#x20;           backtest

&#x20;           replay

&#x20;           optimization





IMPORTANT:



This is a responsibility map.



It is NOT permission to create empty placeholder files.



Production implementation must be created when the corresponding

implementation sprint reaches that subsystem.



================================================================================

44\. RELATION TO PHASE 1–27

================================================================================



&#x20;   Phase 1

&#x20;       Architecture Principles

&#x20;            |

&#x20;   Phase 2

&#x20;       Dependency Rules

&#x20;            |

&#x20;   Phase 3

&#x20;       Domain Model

&#x20;            |

&#x20;   Phase 4

&#x20;       Project Tree

&#x20;            |

&#x20;   Phase 5

&#x20;       Framework Design

&#x20;            |

&#x20;   Phase 6

&#x20;       Pipeline Design

&#x20;            |

&#x20;   Phase 7

&#x20;       Engine Design

&#x20;            |

&#x20;   Phase 8

&#x20;       Service Design

&#x20;            |

&#x20;   Phase 9

&#x20;       Plugin Architecture

&#x20;            |

&#x20;   Phase 10

&#x20;       Event Bus

&#x20;            |

&#x20;   Phase 11

&#x20;       Data Platform

&#x20;            |

&#x20;   Phase 12

&#x20;       Feature Platform

&#x20;            |

&#x20;   Phase 13

&#x20;       AI Platform

&#x20;            |

&#x20;   Phase 14

&#x20;       Trading Platform

&#x20;            |

&#x20;   Phase 15

&#x20;       Portfolio Platform

&#x20;            |

&#x20;   Phase 16

&#x20;       Simulation Platform

&#x20;            |

&#x20;   Phase 17

&#x20;       Self Learning Platform

&#x20;            |

&#x20;   Phase 18

&#x20;       Project Intelligence Platform

&#x20;            |

&#x20;   Phase 19

&#x20;       GUI Architecture

&#x20;            |

&#x20;   Phase 20

&#x20;       SQL Server Schema

&#x20;            |

&#x20;   Phase 21

&#x20;       Configuration System

&#x20;            |

&#x20;   Phase 22

&#x20;       Logging System

&#x20;            |

&#x20;   Phase 23

&#x20;       Testing Architecture

&#x20;            |

&#x20;   Phase 24

&#x20;       Deployment Architecture

&#x20;            |

&#x20;   Phase 25

&#x20;       PowerShell Project Generator

&#x20;            |

&#x20;   Phase 26

&#x20;       Freeze v1.0

&#x20;            |

&#x20;   Phase 27

&#x20;       Final Architecture Freeze

&#x20;            |

&#x20;   Phase 28+

&#x20;       Implementation



Phase 6 is therefore one component of the frozen master architecture.



================================================================================

45\. PHASE 6 COMPLETION CRITERIA

================================================================================



Phase 6 Architecture is complete when:



&#x20;   \[OK] Major workflows have explicit definitions.

&#x20;   \[OK] Stage boundaries are defined.

&#x20;   \[OK] Pipeline Context is defined.

&#x20;   \[OK] Pipeline Request/Result contracts are defined.

&#x20;   \[OK] Pipeline lifecycle is defined.

&#x20;   \[OK] Stage lifecycle is defined.

&#x20;   \[OK] Failure semantics are defined.

&#x20;   \[OK] Retry semantics are defined.

&#x20;   \[OK] Cancellation semantics are defined.

&#x20;   \[OK] Checkpoint/resume semantics are defined.

&#x20;   \[OK] Event Bus integration is defined.

&#x20;   \[OK] Dependency Injection integration is defined.

&#x20;   \[OK] Plugin integration is defined.

&#x20;   \[OK] Execution Store abstraction is defined.

&#x20;   \[OK] Live/Backtest/Paper/Replay separation is defined.

&#x20;   \[OK] Testing boundaries are defined.

&#x20;   \[OK] Observability requirements are defined.

&#x20;   \[OK] Security boundaries are defined.

&#x20;   \[OK] Pipeline/Domain/Service/Engine boundaries are defined.



================================================================================

46\. FINAL PHASE 6 RULE

================================================================================



THE MOST IMPORTANT RULE:



&#x20;   PIPELINE = ORCHESTRATION



Pipeline controls:



&#x20;   WHAT

&#x20;   ORDER

&#x20;   EXECUTION POLICY

&#x20;   STATE

&#x20;   FAILURE HANDLING

&#x20;   RETRY

&#x20;   CANCELLATION

&#x20;   CHECKPOINTING

&#x20;   OBSERVABILITY





Pipeline delegates:



&#x20;   BUSINESS RULES

&#x20;       --> DOMAIN



&#x20;   APPLICATION OPERATIONS

&#x20;       --> SERVICES



&#x20;   SPECIALIZED COMPUTATION

&#x20;       --> ENGINES



&#x20;   PERSISTENCE

&#x20;       --> INFRASTRUCTURE



&#x20;   EXTENSIONS

&#x20;       --> PLUGINS



&#x20;   EVENT TRANSPORT

&#x20;       --> EVENT BUS



&#x20;   CONFIGURATION

&#x20;       --> CONFIGURATION SYSTEM



&#x20;   LOGGING

&#x20;       --> LOGGING SYSTEM





================================================================================

47\. PHASE 6 STATUS

================================================================================



ARCHITECTURE:



&#x20;   COMPLETE / DESIGNED



IMPLEMENTATION:



&#x20;   NOT YET IMPLEMENTED AS A COMPLETE PIPELINE SUBSYSTEM



IMPORTANT:



&#x20;   Phase 1–27 were architecture/design work.



&#x20;   Phase 28+ is implementation.



&#x20;   Existing Phase 28 implementation must be preserved and extended.



&#x20;   Do NOT regenerate the project blindly.



&#x20;   Do NOT introduce temporary architecture.



&#x20;   Do NOT create placeholder implementations.



&#x20;   Do NOT redesign frozen architecture without explicit architectural review.



================================================================================

END OF PHASE 6 — PIPELINE DESIGN

================================================================================

