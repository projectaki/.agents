# Software factory research and implementation assessment

Date: 8 September 2026.

**Selected design: reusable stages, evidence-based routing, and a small set of
completion prerequisites.** A brief repository assessment can take a clear task
directly from intake to implementation. Investigation and plan review apply
when the work needs them. Independent review and current proof remain required
for completion. Basic runtime recording is enabled through the execution helpers.

The implementation uses the existing Python standard-library tools and skills.
It adds no workflow framework, external service, or additional mandatory stage.
The supervised default and the existing correction allowance remain in place.

## Scope and evidence

This report compares nine public approaches. It focuses on Matt Pocock and Dex
Horthy. A software factory is a repeatable process that turns an accepted request
into an implemented and verified change. Skills describe work. Runtime helpers
validate records and control actions where they are integrated.

The original audit inspected the September 7 Factory revision
`a6b8d77639e67f524b8f386a74a833382bab2aae`. It covered all nine Factory skills,
their helpers, worker settings, and four saved tasks containing 63 checkpoints.
The [baseline audit evidence](evidence/2026-09-08-factory-audit.json) preserves
the original 69 passing tests and nine additional probes. Its failures describe
that baseline, not the current implementation.

The current changes are checked with deterministic tests and disposable Git
repositories. Saved product tasks remain unchanged. Historical records cannot
establish actual model cost, active time, or whether a missing event was never
attempted. Public sources establish documented designs, not comparative speed.

## How other software factories work

These approaches solve different problems. Some provide small skills. Some provide a complete workflow. Others describe infrastructure used inside one company. Their public claims are not comparable benchmark results.

| Approach | Setup and operating model | Useful lesson for this factory |
| --- | --- | --- |
| **Matt Pocock's skills** | Install editable skills or a managed bundle. Configure the repository's tracker and documentation locations. Small skills cover clarification, specifications, implementation, testing, and review. The developer composes the process. [Repository](https://github.com/mattpocock/skills) | Keep the skills small. Separate reusable engineering practices from task routing. |
| **Dex Horthy and HumanLayer** | The original process separates research, planning, and implementation. The current product also presents questions, design, and structure work. Artifacts preserve decisions across agent sessions. Humans examine important decisions before implementation. [Context engineering essay](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md), [current HumanLayer workflow](https://www.hlyr.dev/) | Give important design decisions a clear, reviewable form. Adjust planning depth to the task. |
| **Jesse Vincent's Superpowers** | Install a skill bundle with runtime integration. Its workflow covers design discussion, worktree setup, small implementation tasks, tests, and separate reviews for requirements and code quality. [Repository](https://github.com/obra/superpowers) | Test whether agents follow the skills. Separate behavioral correctness from maintainability during review. |
| **GSD Core** | Install its runtime-specific integration. Work repeats through discuss, plan, execute, verify, and ship. Heavy work uses fresh agent contexts. Persistent files carry decisions between phases. [Current repository](https://github.com/open-gsd/gsd-core) | Make work small enough for a bounded agent assignment. Preserve dependencies and explicit continuation state. |
| **GitHub Spec Kit** | Initialize repository tooling. Establish project principles, define a specification, plan, derive tasks, implement, and check convergence against the specification. Optional analysis checks consistency across artifacts. [Official README](https://github.com/github/spec-kit/blob/main/README.md) | Check that requirements, plans, and evidence agree before implementation and completion. |
| **BMad Method** | Install skills or plugins and configure the project. Clear small work can enter implementation directly. Larger work uses specifications, shared architecture, and separately implemented stories. [Repository](https://github.com/bmad-code-org/BMAD-METHOD), [planning guide](https://docs.bmad-method.org/plan/choose-a-planning-path/) | Use one implementation process at different scales. Add shared design only where tasks need it. |
| **StrongDM Software Factory and Attractor** | StrongDM describes agents iterating against behavioral scenarios and replicas of external services. Attractor publishes specifications for an engine that traverses a workflow graph, saves checkpoints, and supports conditional and human decisions. The public repository is a specification set, not a ready-made runtime implementation. [Factory account](https://factory.strongdm.ai/), [Attractor repository](https://github.com/strongdm/attractor) | Separate acceptance evaluation from implementation. Put mechanical workflow rules in executable code. |
| **Anthropic's long-running agent work** | The 2025 design uses an initializer, a feature list, environment startup instructions, incremental implementation, and handoffs. The March 2026 experiment adds planner, generator, and evaluator roles with agreed feature-level acceptance. [2025 article](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [2026 article](https://www.anthropic.com/engineering/harness-design-long-running-apps) | Make the test environment reproducible. Evaluate the running behavior. Calibrate reviewers against known failures. |
| **Geoffrey Huntley's Ralph technique** | Repeatedly invoke an agent with a specification and current plan. Select a bounded item, implement it, validate it, and carry the result into the next iteration. The prompt evolves from observed failures. [Creator's account](https://ghuntley.com/ralph/) | Keep continuation simple. Use explicit task boundaries and feedback. An indefinite loop does not itself establish correctness. |

The older `gsd-build/get-shit-done` repository is archived. Its README directs readers to Open GSD's GSD Core. Recommendations based only on the older repository can describe an obsolete setup. [Official redirect](https://github.com/gsd-build/get-shit-done)

Stripe's Minions provide an additional industrial reference. Stripe's public summary describes agent-written changes with human code review. However, the retrieved article pages did not expose their main bodies. I therefore do not use secondary descriptions of their internal workflow as verified architectural evidence. [Stripe's own summary](https://stripe.dev/blog/topic/developer%20productivity)

### What Matt Pocock contributes

The most relevant contribution is how work is divided. His ticket skill requires a small, independently verifiable path through the affected layers. It also names prerequisites. Broad mechanical refactors use an expansion, migration, and removal sequence when an ordinary feature slice cannot remain working. This is more useful here than copying a larger set of role names. [Ticket skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/to-tickets/SKILL.md)

His implementation skill is short. It calls for frequent focused tests and type checks, a final suite run, review, and a commit. His review skill evaluates requirements and coding standards separately. His domain-modeling skill distinguishes a glossary from architectural decisions. It creates decision records only for meaningful, costly tradeoffs. These boundaries keep each artifact understandable. [Implementation skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/implement/SKILL.md), [review skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md), [domain-modeling skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/SKILL.md)

Your factory already separates work skills from orchestration. Keep that separation. The work instructions support bounded implementation parts and preserve accepted decisions.

### What Dex Horthy contributes

Dex's early context-engineering essay treats research summaries and implementation plans as deliberate context reduction. It also describes failures caused by incomplete dependency research. Its numerical context targets are observations from that workflow, not universal limits for every model. [Context engineering essay](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md)

His later software-factory essay places more emphasis on maintainability and human understanding. It distinguishes product design, system architecture, program design, and small end-to-end changes. It explicitly says that small tasks do not need the whole process. Its account of autonomous failures is practitioner evidence, not proof that all autonomous development fails. [Why Software Factories Fail](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/wsff.md)

For this factory, the useful change is to make material choices visible inside triage. Adding four compulsory approval stages would conflict with your existing proportional process.

### Where the approaches disagree

StrongDM describes replacing human code review with independently maintained scenarios and behavioral evaluation. Dex argues that maintainability needs substantial human steering. These positions assume different environments and validation investment. StrongDM's service replicas are an important part of its account. They are not evidence that a normal unit-test suite can replace review. [StrongDM account](https://factory.strongdm.ai/), [Dex's assessment](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/wsff.md)

Anthropic also reports that useful context-management mechanisms changed between models. Its later experiment removed a reset mechanism that an earlier model needed. This supports testing the process with the actual models and tasks in use. It does not support permanent rules about a particular context percentage. [Anthropic's later experiment](https://www.anthropic.com/engineering/harness-design-long-running-apps)

My assessment is that your factory should retain independent review. It should use broader autonomous operation only where tests, environment isolation, and observed results support it.

## How the factory operates

The [orchestrator](../skills/factory-orchestrator/SKILL.md) selects the next useful
stage. It supplies a short reason. The [prerequisite checks](../skills/factory-handoff/scripts/prerequisites.py)
validate consequential actions. There is no universal allowed-transition table.

| Task condition | Example route |
| --- | --- |
| Clear, localized work with sufficient repository findings | Intake → implementation → independent review → completion |
| Unclear code or dependencies | Intake → triage → implementation → review → completion |
| Sensitive behavior or consequential plan | Intake and assessment → plan review → implementation → change review |
| New assumption found during implementation | Implementation → triage → implementation → review |
| Large coherent change | Intake and necessary preparation → bounded implementation parts → combined review |
| Authorized draft publication | Passing review → delivery and readback → completion |

These are examples. A skipped stage means its purpose is already sufficiently
covered. A short request is not evidence of low risk. New evidence can change
the route. It does not automatically require human input. Scope, authority,
and unresolved product decisions still determine when a person is needed.

An assignment can combine brief preparation and implementation after its
prerequisites pass. The implementer can retain useful context between bounded
parts. A fresh reviewer provides independence. Long histories and closed findings
stay in referenced artifacts. A small task does not require a separate plan
artifact, repeated setup, or a new worker for each conceptual responsibility.

## Implemented safeguards and efficiency changes

| Area | Current behavior | Why it matters |
| --- | --- | --- |
| Flexible routing | Checkpoints accept a proposed next stage and reason. Dispatch checks its prerequisites. | Allows short routes and returns to investigation without a general pipeline engine. |
| Repository assessment | Implementation requires recorded findings and mapped planned proof. | Prevents classification from request length alone. |
| Plan approval | Required approval is bound to the current plan and an independent worker. | Prevents an old or missing approval from authorizing sensitive implementation. |
| Independent review | Completion requires implementation and review records for the same head and base. A contributing implementer cannot approve the change. | A passing verdict field alone cannot establish completion. |
| Risk and change coverage | Material risks need proof or exact exceptions. Change groups cover the actual changed-file list. | Detects omitted risk mappings and unaccounted files. Semantic quality remains the reviewer's responsibility. |
| Checkpoint consistency | A task lock covers reading and publication. Prepared documents use a recoverable pending update. Retry identities avoid duplicate results. | Protects task state during concurrent or interrupted submissions. |
| Accepted requirements | A compact contract snapshot is preserved per task revision. Changed accepted scope requires a new revision. | Prevents silently weakening requirements to obtain a pass. |
| Task identity | Paths include digests of shared Git identity and the exact branch name. Legacy records stay in place. | Separates repositories and branches whose readable names collide. |
| Automatic limits | Run-bound duration and progress outcomes stop automatic continuation at the configured limits. Dispatch supplies the remaining timeout. | Makes repeated work and execution limits visible to the helpers. |
| Default telemetry | Dispatch emits run and assignment starts. Checkpointing emits results and closes observed assignments. Recording failures remain nonblocking. | Removes the need to remember a separate telemetry call at these boundaries. |
| Timed checks | A command helper records duration, exit status, source revisions, and a safe environment description. It enforces a timeout. | Gives review a compact execution receipt and preserves real failures. |
| Evidence reuse | Review identifies reusable results and missing checks. It needs a concrete reason for repeated execution. | Avoids repeating valid checks while retaining independent source review. |
| Large work | Implementation can return `in-progress` after a coherent part. The complete contract remains active. | Allows bounded work without restarting intake or claiming premature completion. |
| Review discipline | Blocking findings require a defect, missing requirement, material risk, or applicable rule. | Avoids correction cycles caused by harmless preferences. |

The implementation is in the [handoff helpers](../skills/factory-handoff/SKILL.md),
[timed check helper](../skills/factory-telemetry/scripts/run-check.py), and
[work skills](../skills/factory-implement/SKILL.md). The
[record contract](../skills/factory-handoff/references/records.md) describes fields
and compatibility. Existing records are not silently upgraded. Missing current
proof or reviewer identity must be established before consequential follow-up.

## Why telemetry was missing

The baseline described telemetry as optional. The orchestrator supplied optional
recording assignments. Checkpointing did not invoke the event writer. Work-skill
validation deliberately kept telemetry dependencies outside individual work
skills. A run could therefore follow the required process without recording it.

The current integration attempts basic recording by default. A recording failure
writes a concise warning where possible. It does not change product acceptance.
The final summary should mention incomplete telemetry once. Detailed operation
recording uses the supplied check helper or explicit events where needed.

Run elapsed time includes waits. The summary labels it accordingly. Historical
interruption gaps remain unknown. Worker model and reasoning settings are recorded
only when supplied from the actual execution configuration. Run starts record
the Factory Git revision and whether its working tree was modified.

## Validation and practical limits

Deterministic scenarios cover a short route, unresolved investigation, sensitive
plan approval, stale approval, self-review, unsupported completion, uncovered
risk, exact changed-file coverage, time and progress stops, repeated submissions,
concurrent checkpoints, interrupted publication, changed contracts, task identity,
and default recording. Check-command tests preserve failures and sanitize receipts.
The validation result for this implementation is recorded in
[evidence/factory-implementation-validation.json](evidence/factory-implementation-validation.json).

These tests exercise the helpers and real temporary Git repositories. They do
not establish how a model will behave in an unattended product task. The native
agent interface still dispatches and interrupts workers. The start helper checks
prerequisites and reports a timeout; it cannot terminate a native worker itself.
The orchestrator must apply that timeout. The check helper can terminate its own
command process group. Direct edits to task files remain outside the protected
prepared-document publication path.

The tools validate recorded provenance, references, and revisions. They cannot
prove that an agent told the truth or that a test establishes the intended
behavior. Independent source and behavior review remains necessary. A receipt
from a dirty tree needs explicit source verification before reuse at a commit.
External dependencies and service state also need relevant checks.

The pending update protects process-interrupted publication. This is a small
local-file design, not a claim of storage durability across every hardware or
filesystem failure. Telemetry can be incomplete after an abrupt process exit;
missing terminal events must remain visible rather than be reconstructed as
successful execution.

## How to keep the factory small

Evaluate changes to the factory on representative tasks: a clear fix, an ordinary
feature, an unclear bug, and a sensitive change. Compare accepted behavior,
completion time, coordination time, repeated checks, missed requirements, and
unnecessary review findings. These evaluations belong to factory maintenance.
They are not extra stages inside every product task.

Measure before changing model choices, adding parallel implementation, expanding
review panels, or adding new documents. The local fast and standard worker
configurations currently select the same model and reasoning setting. Their
names do not establish a speed difference. Preserve one active implementation
owner until dependencies and test resources justify parallel work.

Retain a process requirement when it prevents an observed failure or improves a
representative result. Remove duplication when existing evidence covers the same
need. No speedup percentage is claimed without measurements from comparable runs.

## What the saved tasks establish

| Task | Recorded outcome and useful evidence | Current interpretation |
| --- | --- | --- |
| Storage writer cutover | Plan review required corrections. Change review found missing document-library proof. A later review recorded mutation checks that showed the added tests detected the defect. Delivery was recorded. [History](/home/work/.agents-db/humanrisks-platform/feature--hum-2097-storage-migration-24-writer-cutover/history.jsonl:8) | Independent review added value. Older evidence entries lack fields required by the current format. That does not establish that the tests never ran. |
| Storage migration tool | Several plan corrections preceded implementation. Change review then required six corrections. Later records describe a rebase beyond the assured revision. [History](/home/work/.agents-db/2098/feature--hum-2098-storage-migration-34-migration-tool/history.jsonl:23) | A demanding task benefited from review. Its current assurance record is 367,063 bytes. Its older completion problem must not be reported as an unfixed current-router defect. |
| Storage retirement | The history records implementation, correction, local completion, and later draft delivery. It uses outcomes and assurance structures outside the current contract. [History](/home/work/.agents-db/2099/feature--hum-2099-storage-migration-44-retirement/history.jsonl:1) | The saved state cannot be treated as ready to resume under the current validator. The exact historical Factory version is not recorded. |
| Dashboard row links | Two task revisions reached recorded local completion. The follow-up integrated a changed base. The history records repeated suite execution and placeholder checkpoint corrections. [History](/home/work/.agents-db/humanrisks-platform/feature--hum-2122-tasks-dashboards-refinements-to-do-list-links-to-tasks/history.jsonl:15) | At the audit baseline, validation detected a changed base. Current resumption also requires recorded reviewer identity and repository assessment. These gaps do not establish a defect in the earlier implementation. |

At the audit baseline, none of these four task roots contained a telemetry event file. None of the 63 checkpoint entries recorded worker identity or active seconds. The histories therefore cannot support reliable claims about active runtime, model cost, or the relative quality of worker tiers.
