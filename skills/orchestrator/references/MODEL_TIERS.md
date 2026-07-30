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
   profile, concrete model, effort, and enforcement status in the active
   invocation and lifecycle handoff.

Do not use aliases or inherited models for tier-selected work. The effort labels are provider-specific values and are not equivalent across providers.

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
profile, verifies the Fast-first and sequential-escalation contract, and rejects
obsolete 2-tier profiles or tier identifiers.

The primary orchestrator is not a tier-selected worker. Its defaults are:

- Codex: `gpt-5.6-sol`, `medium`
- Claude: `claude-opus-5`, `high`
