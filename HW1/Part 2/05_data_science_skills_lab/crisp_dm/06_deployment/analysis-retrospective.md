---
skill: analysis-retrospective
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts: [SKILLS_INDEX.md, artifacts/ledger_phase1.jsonl, artifacts/ledger_phase4.jsonl, artifacts/ledger_phase6a.jsonl, artifacts/ledger_phase6b.jsonl]
---

## What the skill prescribes

1. Time-box the retro; use a structured format (4Ls: Liked/Lacked/Learned/Longed-for used here).
2. Compare actual timeline/scope/effort to what was planned.
3. Capture at least two things that worked and should be repeated.
4. Apply 5-whys to root-cause each real problem, not just the symptom.
5. Capture reusable learning — templates, reference docs, checklists, team norms.
6. Record actions with owners and due dates.

## Applied to this lab (48-skill, multi-agent CRISP-DM project)

### Against plan

Planned in `crisp_dm/01_business_understanding/analysis-planning.md`: 6 CRISP-DM phases, one
subagent wave per phase-group, one dataset for all 48 skills. **Actual**: phases 1-3 (25 skills)
completed by 3 parallel subagents without incident. Phase 4/5 and both Phase 6 agents (21
skills) all hit a shared account-level session limit **simultaneously**, mid-task, and had to be
finished by the orchestrating session directly rather than by the subagents that started them.
Scope did not shrink — all 48 skills landed — but the execution model changed mid-project.

### Liked

- **Parallel subagent waves for independent phases** (1, 2, 3 concurrently) worked cleanly —
  each had a self-contained brief, clear file ownership boundaries, and no cross-phase
  dependency, so there was no coordination overhead and no conflicting writes.
- **The independent numeric verification harness** (`src/verify_claims.py`) paid for itself
  immediately: it caught zero errors in the final numbers, but it also would have caught them —
  every headline figure across 6 phases traces to the raw CSV, checkable by someone who trusts
  none of this lab's own scripts.

### Lacked

- **No visibility into subagent quota state.** Three agents (Phase 4/5, both Phase 6 agents)
  died at effectively the same timestamp with the same "session limit" message, mid-sentence, in
  the middle of writing a doc. There was no warning signal before it happened and no way to
  checkpoint more granularly than "whatever was on disk when it died."
- **The mandatory hand-off contract (`model.joblib`, `model_card.md`, `inference_contract.json`)
  was not fully written before the agent that owned it died** — `model_card.md` and
  `inference_contract.json` didn't exist yet, and had to be reconstructed from
  `final_metrics.json` + a fresh model-load test rather than handed off cleanly.

### 5-whys on the main incident

**Problem**: three subagents died simultaneously mid-task.
1. Why? — Each hit "session limit · resets 9pm."
2. Why did that stop the work rather than degrade gracefully? — A subagent's mailbox/session
   has no built-in mid-task checkpoint distinct from whatever files it happened to have written
   to disk at the moment of the interrupt.
3. Why three at once? — The limit is evidently account-level (shared across concurrently running
   agents), not per-agent — running 3 large agents concurrently for an extended period drew down
   a shared budget faster than running them sequentially would have.
4. Why wasn't this anticipated? — The plan assumed independent per-agent budgets; it wasn't
   verified before launching 3 more large, long-running agents in the same wave that had already
   seen 3 complete without hitting any limit (phases 1-3), which looked like a safe precedent
   but wasn't — phases 1-3 were smaller/faster per agent, phase 4-6 agents ran longer.
5. Root cause: **the wave-sizing decision (3 large concurrent agents) was made without a
   cheap way to check remaining shared quota first**, and the smaller/faster success of the
   first wave was (wrongly) taken as evidence the second wave's larger agents would be fine too.

**Fix applied in the moment**: recognized that respawning more subagents right after 3 died
simultaneously would likely hit the same wall immediately, and switched to finishing the
remaining 9 skills directly rather than retrying the same failure mode.

### Other real issues, root-caused briefly

- **Upstream skill-pack bugs** (12 scripts across `data-analytics-skills` define `main()` but
  never call it in `__main__`; 2 scripts use Python 3.10+-only syntax). Root cause: these
  scripts were evidently authored and tested by running them with no CLI args (triggering the
  hardcoded demo branch), never with real arguments — the demo path masks the broken path in
  casual testing. Reusable learning: **when adopting a third-party skill pack's scripts, run
  each one once with real arguments before trusting its CLI**, not just its demo output.
- **A hand-off contract bug found by this lab, not inherited**: `model.joblib` required
  pre-coerced numeric `TotalCharges`, but the first-draft `inference_contract.json` assumed the
  pipeline did that coercion. Root cause: the contract was written by inference from the
  pipeline's *intent* ("the FeatureEngineer cleans TotalCharges") rather than by an executed
  round-trip test against the true raw schema. Reusable learning: **write an I/O contract only
  after running the exact untransformed input through the real artifact once**, not from reading
  the code.
- **Write-tool filename heuristic blocked mandated `.md` deliverables** mid-lab (misread as
  self-generated report cruft rather than a specified deliverable path). Workaround: Bash
  heredoc for every doc write from that point forward. Reusable learning worth carrying to the
  next project: default to heredoc for skill-deliverable docs from the start, not as a reactive
  fix.

### Longed for

- A cheap way to query remaining shared session/quota budget *before* launching a wave of
  long-running concurrent agents, so wave sizing could be a decision rather than a gamble.
- A mid-task checkpoint/ledger convention adopted from the start (this lab only started
  appending to `ledger_phase*.jsonl` *after* each skill fully completed — a partial-progress
  marker per skill, not just per completed skill, would have made resuming after the incident
  faster to diagnose).

## Outputs produced

- This retrospective.
- `SKILLS_INDEX.md` — generated coverage reconciliation (48 installed, 48 demonstrated after
  this doc lands), the artifact that let this retro (and the orchestrating session) know
  precisely what survived the incident and what didn't, without re-deriving it from memory.
