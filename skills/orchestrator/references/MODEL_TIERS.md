# Orchestrator Model Tiers

This file is the provider-specific model policy for the abstract tiers defined by the orchestrator protocol.

| Abstract tier | Codex worker | Model and effort | Claude worker | Model and effort |
| --- | --- | --- | --- | --- |
| `fast` | `fast-worker` | `gpt-5.6-luna`, `low` | `fast-worker` | `claude-sonnet-5`, `low` |
| `standard` | `standard-worker` | `gpt-5.6-terra`, `medium` | `standard-worker` | `claude-sonnet-5`, `medium` |
| `high` | `high-worker` | `gpt-5.6-sol`, `high` | `high-worker` | `claude-opus-5`, `high` |

## Dispatch

1. A fresh bounded assignment always selects `fast`.
2. A replacement attempt selects only the next tier in
   `fast` → `standard` → `high`, after the previous attempt and escalation
   rationale have been persisted.
3. At the actor-dispatch boundary, select the worker profile for the active runtime from the table.
4. Supply the lifecycle role, bounded assignment, mutation authority, inputs, and output contract in the delegation.
5. Record the assignment ID, attempt number, abstract tier, runtime, worker
   profile, concrete model, effort, dispatch mechanism, and enforcement status
   in the active invocation and lifecycle handoff.

Do not use aliases or inherited models for tier-selected work. The effort labels are provider-specific values and are not equivalent across providers.

## Runtime enforcement

Only the 3 tier profiles are valid orchestration agents. Lifecycle roles such
as planner, implementer, and reviewer are assignment fields. They are never
custom-agent names.

Use only each runtime's built-in subagent mechanism:

1. Resolve the abstract tier to the named profile in the table.
2. In Codex, spawn that custom agent by its `name`. Codex loads the matching
   TOML as the spawned session's configuration layer; its `model` and
   `model_reasoning_effort` take precedence over inherited values.
3. In Claude, spawn that custom agent by its `name`; its frontmatter pins the
   model and effort.
4. Make the visible agent thread name equal the selected profile.
5. Give the tier worker the lifecycle skill and complete bounded assignment.
   The worker performs the lifecycle work directly and does not spawn another
   lifecycle actor.
6. In the primary thread, announce the resolved lifecycle, tier, worker,
   concrete model, and effort immediately before spawning.
7. After native spawn succeeds, confirm in the primary thread that the named
   worker started with its pinned model and effort. Never claim it started when
   spawning failed.

Do not invoke `$codex-cli`, `$claude-cli`, or another external agent process.
If the runtime cannot select a named custom agent, do not dispatch lifecycle
work. A prompt or thread label that merely mentions the profile is not enough.

Use this human-visible receipt:

```text
Routing selected: REVIEW -> high -> high-worker (gpt-5.6-sol, high). Starting native subagent.
Started: high-worker for REVIEW using its pinned gpt-5.6-sol, high profile.
```

The receipt is a concise audit statement in the primary thread. The persisted
invocation and handoff remain the detailed machine-readable record.

## Selection rationale

Sources were checked on 2026-07-30.

- OpenAI positions [Luna for efficient high-volume work, Terra for a balance of
  intelligence and cost, and Sol for frontier capability](https://developers.openai.com/api/docs/guides/latest-model).
  The same guidance recommends `low` for latency-sensitive work, `medium` as a
  balanced starting point, and higher effort only after measured quality gains.
- OpenAI reports that all 3 GPT-5.6 sizes retain strong agentic coding
  performance, with Sol leading its published Coding Agent Index comparison and
  Terra and Luna completing the compared agent evaluations in substantially
  less time than the prior frontier baseline
  ([GPT-5.6 launch](https://openai.com/index/gpt-5-6/)).
- GPT-5.3-Codex-Spark is faster, but OpenAI describes it as a restricted,
  text-only research preview with a 128k context window. Those constraints make
  it unsuitable as the universal lifecycle default despite its speed
  ([Codex-Spark launch](https://openai.com/index/introducing-gpt-5-3-codex-spark/)).
- Anthropic positions [Sonnet 5 as its speed/intelligence balance and Opus 5
  for complex agentic coding](https://platform.claude.com/docs/en/about-claude/models/overview).
  Its [effort guidance](https://platform.claude.com/docs/en/build-with-claude/effort)
  recommends `low` for latency-sensitive subagents, `medium` for balanced
  agentic work, and `high` for difficult coding.
- Independent Artificial Analysis results support the high-tier choices:
  [GPT-5.6 Sol led its Coding Agent Index evaluation](https://artificialanalysis.ai/articles/gpt-5-6-has-landed/),
  while [Claude Opus 5 tied for the lead in its coding-agent evaluation and
  matched or exceeded Fable 5 on several agentic measures at lower cost per
  task](https://artificialanalysis.ai/articles/opus-5).

These results compare model-and-harness combinations, not isolated models.
Benchmark versions, provider infrastructure, effort semantics, and end-to-end
tool latency differ. Treat the mappings as evidence-based defaults and validate
them on orchestration telemetry rather than comparing scores across providers.

## Validation

Run:

```bash
python3 skills/orchestrator/scripts/validate_model_tiers.py
```

The validator checks the tier table against every Codex and Claude worker
profile, requires the agent directories to contain exactly the 3 tier profiles,
verifies the Fast-first and sequential-escalation contract, and rejects
role-specific agents, obsolete profiles, or tier identifiers.

On a configured workstation, also verify that both runtimes discover these
canonical directories:

```bash
python3 skills/orchestrator/scripts/validate_model_tiers.py --check-installation
```

The primary orchestrator is not a tier-selected worker. Its defaults are:

- Codex: `gpt-5.6-sol`, `medium`
- Claude: `claude-opus-5`, `high`
