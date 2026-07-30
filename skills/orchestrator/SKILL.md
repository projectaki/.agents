---
name: orchestrator
description: Run the primary agent thread as the sole SDLC orchestrator for implementation tasks that require a code change and pull request, using a persistent state machine, bounded lifecycle actors, deterministic routing, model escalation, review, verification, and delivery gates. Use only for the primary thread when starting, resuming, recovering, or routing such an implementation task, including after context compaction. Do not use for advisory, research, review-only, or other non-implementation tasks.
---

# Orchestrator

Read [ORCHESTRATOR.md](references/ORCHESTRATOR.md),
[HUMAN_REPORTS.md](references/HUMAN_REPORTS.md),
[CHANGE_ASSURANCE_REPORT.md](references/CHANGE_ASSURANCE_REPORT.md), and
[MODEL_TIERS.md](references/MODEL_TIERS.md) completely before making any
lifecycle, routing, or actor-dispatch decision.

Before dispatching `ANALYSIS` or consuming its result, also read [ANALYSIS_REPORT.md](references/ANALYSIS_REPORT.md) completely and give its contract to the analyst.

Treat the reference as the normative execution protocol. If another instruction conflicts with it, follow the higher-priority instruction and record the conflict before routing.

## Start or resume

1. Determine whether this is the primary thread. If it is a spawned worker thread, do not assume orchestration authority; perform only the delegated assignment and return a structured result to the parent.
2. Load the complete protocol reference.
3. Invoke the `factory-handoff` skill in resume mode to locate or initialize the deterministic task root under `~/.agents-db`.
4. Reconcile the persisted lifecycle, task revision, canonical artifacts, active invocation, last actor result, and last routing decision.
5. Continue only through an explicitly permitted transition.

## Operate

- Keep the root task in exactly one canonical lifecycle.
- Retain exclusive authority to invoke the router and commit state transitions.
- Delegate every lifecycle's work to bounded actors as required by the
  protocol. The primary thread performs orchestration only: routing, dispatch,
  checkpointing, reconciliation, and human reporting.
- Treat actor outputs as evidence and recommendations, never as transition commands.
- After every lifecycle actor result, invoke the `factory-handoff` skill to persist the result and exit-gate outcome before routing.
- Do not propose, approve, or commit the next lifecycle until the handoff checkpoint is verified.
- Persist the selected transition before dispatching another actor.
- Use one implementer. Parallelize only planning when the protocol's guard requires it.
- Do not declare completion until every applicable completion invariant passes.

Use the runtime's native mechanisms for filesystem access, Git, and pull-request
delivery. Actor delegation is stricter:

- Keep lifecycle roles provider-neutral. Resolve `fast`, `standard`, and `high`
  through `MODEL_TIERS.md` only at the actor-dispatch boundary.
- Use only the `fast-worker`, `standard-worker`, and `high-worker` profiles.
  Lifecycle roles belong in the assignment, not in separate agent profiles.
- Name every visible actor thread after its selected worker profile.
- Use only the runtime's built-in subagent mechanism. In Codex and Claude,
  select the named custom agent profile directly. Do not invoke `$codex-cli`,
  `$claude-cli`, or another external agent process for lifecycle work.
- Give the selected tier worker the lifecycle skill, bounded role, mutation
  authority, canonical inputs, and output contract. The worker executes the
  lifecycle skill directly and must not spawn a nested lifecycle actor.
- Write a concise dispatch receipt in the primary thread for every actor:
  1. Immediately before spawning, say
     `Routing selected: <lifecycle> -> <tier> -> <worker-profile> (<model>, <effort>). Starting native subagent.`
  2. Only after native spawn succeeds, say
     `Started: <worker-profile> for <lifecycle> using its pinned <model>, <effort> profile.`
  Do not write the second line when spawning fails. Do not include internal
  assignment, invocation, or agent IDs in either line.
- Include the bounded lifecycle role and mutation authority in every tier-worker assignment.
- Start every fresh bounded assignment at `fast`. Escalate a replacement attempt
  by exactly one tier only when the prior attempt has persisted evidence of
  model insufficiency.
- Persist the assignment ID, attempt number, selected abstract tier, resolved
  runtime, worker profile, concrete model, effort, enforcement status, and any
  escalation rationale.
- Record `runtime_enforcement: confirmed` only when native dispatch selected
  the named profile whose file pins the configured model and effort. If native
  custom-agent selection is unavailable, stop before lifecycle work.

## Reload

Reload the complete protocol reference:

- after context compaction;
- after orchestrator restart or task resumption;
- when the current lifecycle or permitted outgoing edges are uncertain;
- when the required actor result, canonical artifact, or routing rule is not confidently available.

After reloading, invoke the `factory-handoff` skill in resume mode and reconcile its resume packet before taking further action. Do not reconstruct lifecycle state from memory when persisted evidence is available.
