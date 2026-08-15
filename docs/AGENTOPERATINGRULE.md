====================================================================

SHADBOTTRADER — AGENT OPERATING RULE

====================================================================



The documentation files define the intended architecture,

contracts, roadmap, engineering rules, and implementation direction.



However, the actual source code and current workspace state are

the authoritative implementation reality.



Before implementing ANY task:



1\. Inspect the current workspace.

2\. Inspect the relevant source files.

3\. Inspect existing tests.

4\. Inspect project configuration.

5\. Inspect Git status and recent history when relevant.

6\. Compare the current implementation against the documentation.

7\. NEVER assume that a documented component already exists.

8\. NEVER recreate an existing component without inspecting it first.

9\. NEVER redesign the architecture unless explicitly instructed.

10\. NEVER replace existing working architecture with a different design

&#x20;   merely because another design appears preferable.



When documentation and implementation disagree:



&#x20;   DO NOT silently choose one.



Identify the discrepancy.



Determine whether:



&#x20;   documentation is outdated

&#x20;   implementation is incomplete

&#x20;   implementation contains a defect

&#x20;   architecture was intentionally changed



Then resolve the discrepancy according to the latest explicit

project decision.



====================================================================

IMPLEMENTATION LOOP

====================================================================



INSPECT

&#x20;   ↓

UNDERSTAND

&#x20;   ↓

PLAN

&#x20;   ↓

IMPLEMENT

&#x20;   ↓

TEST

&#x20;   ↓

QUALITY GATE

&#x20;   ↓

UPDATE PROJECT STATE

&#x20;   ↓

VERIFY ARCHITECTURE

&#x20;   ↓

COMMIT



====================================================================

NO PLACEHOLDER RULE

====================================================================



Do not create:



&#x20;   TODO implementations

&#x20;   fake production logic

&#x20;   placeholder classes

&#x20;   empty methods

&#x20;   pass-only implementations

&#x20;   temporary architecture

&#x20;   duplicated systems



Unless explicitly requested.



====================================================================

NO REDESIGN RULE

====================================================================



The existing ShadBotTrader architecture is intentional.



Do not redesign:



&#x20;   architecture

&#x20;   dependency direction

&#x20;   domain boundaries

&#x20;   project structure

&#x20;   data flow

&#x20;   contracts

&#x20;   lifecycle



without explicit authorization.



====================================================================

QUALITY GATE

====================================================================



Before declaring a task complete:



&#x20;   python -m ruff check .

&#x20;   python -m black --check .

&#x20;   python -m mypy src

&#x20;   python -m pytest



ALL MUST PASS.



====================================================================

STATE UPDATE RULE

====================================================================



After every meaningful architectural or implementation change,

update the appropriate project-state documentation.



The project must always be recoverable from:



&#x20;   source code

&#x20;   Git history

&#x20;   project-state documentation

&#x20;   architecture documentation



====================================================================

CHAT HANDOFF RULE

====================================================================



The project must remain understandable even if:



&#x20;   the current AI conversation ends

&#x20;   a new AI conversation starts

&#x20;   another coding agent takes over

&#x20;   the original developer is unavailable



A new agent must be able to continue the project by reading the

canonical documentation and inspecting the workspace.



====================================================================

END

====================================================================

