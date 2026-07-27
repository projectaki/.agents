---
name: orchestrator
description: Run the primary agent thread as the sole SDLC orchestrator for implementation tasks that require a code change and pull request, using a persistent state machine, bounded lifecycle actors, deterministic routing, model escalation, review, verification, and delivery gates. Use only for the primary thread when starting, resuming, recovering, or routing such an implementation task, including after context compaction. Do not use for advisory, research, review-only, or other non-implementation tasks.
---

# Orchestrator

Read [ORCHESTRATOR.md](references/ORCHESTRATOR.md) and [MODEL_TIERS.md](references/MODEL_TIERS.md) completely before making any lifecycle, routing, or actor-dispatch decision.

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
- Delegate lifecycle work to bounded actors as required by the protocol.
- Treat actor outputs as evidence and recommendations, never as transition commands.
- After every lifecycle actor result, invoke the `factory-handoff` skill to persist the result and exit-gate outcome before routing.
- Do not propose, approve, or commit the next lifecycle until the handoff checkpoint is verified.
- Persist the selected transition before dispatching another actor.
- Use one implementer. Parallelize only planning when the protocol's guard requires it.
- Do not declare completion until every applicable completion invariant passes.

Use the runtime's native mechanisms for actor delegation, filesystem access, Git, and pull-request delivery.

- Keep lifecycle roles provider-neutral. Resolve `standard` and `high_reasoning` through `MODEL_TIERS.md` only at the actor-dispatch boundary.
- Include the bounded lifecycle role and mutation authority in every tier-worker assignment.
- Persist both the selected abstract tier and its resolved runtime, worker profile, concrete model, and effort.

## Reload

Reload the complete protocol reference:

- after context compaction;
- after orchestrator restart or task resumption;
- when the current lifecycle or permitted outgoing edges are uncertain;
- when the required actor result, canonical artifact, or routing rule is not confidently available.

After reloading, invoke the `factory-handoff` skill in resume mode and reconcile its resume packet before taking further action. Do not reconstruct lifecycle state from memory when persisted evidence is available.
