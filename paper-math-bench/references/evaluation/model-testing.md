# Model testing and grading

**Contents**

- [Scope and limits](#scope-and-limits)
- [Prepare a bundle](#prepare-a-bundle)
- [Review the private rubric](#review-the-private-rubric)
- [Statement review version gate](#statement-review-version-gate)
- [Select the run configuration](#select-the-run-configuration)
- [Independent solver execution](#independent-solver-execution)
- [Grade and report](#grade-and-report)
- [Screen authoring candidates](#screen-authoring-candidates)

Use this reference for bank evaluation and target-model trials during [authoring](../research/problem-design.md) or requested [elaboration](../research/problem-refinement.md), including formal screening evidence. The same export, runner, and scorer serve these workflows. Intermediate authoring-model diagnostics follow [their separate interpretation](../research/problem-design.md#anonymous-diagnostics); they do not use this document's target-model classification policy. Evaluation alone reports results without rewriting the source bank. Full authoring includes elaboration and screening; standalone elaboration includes formal trials only when requested.

## Scope and limits

The bundled implementation supports a local **instruction-only pilot** through the Codex CLI. It creates a fresh working directory for each task and requests no browsing or network use. A fresh directory does not prevent a process from reading other accessible files, and a no-network instruction is not a network firewall. Every report must preserve `strict_blind: false` and `network_enforced: false` for this mode. Do not call it strict blind, enforced offline, or contamination-free.

Model, tools, budget, and submission format are part of the test specification. Use the local [tier guide](difficulty-levels.md) for difficulty calibration and [evaluation settings](../execution/task-settings.md) for the missing-field intake and the default `gpt-5.6-sol / max` local-pilot configuration.

Use these materials and trial records in authoring decisions under [References in design](../research/problem-design.md#references-in-design).

The [Epoch snapshot](../../data/epoch-settings.json) is dated reference data. Check runtime support for the selected exact model and refresh missing or changed published settings. Verify CLI behavior from the local installation and, when necessary, [official Codex documentation](https://developers.openai.com/codex/noninteractive).

## Prepare a bundle

Resolve the local source, task selection, and cache through [intake](../execution/task-settings.md#startup-intake), following [required-material handling](../execution/task-settings.md#required-materials-and-interruptions). Apply [paths and write scope](../execution/task-settings.md#paths-and-write-scope) to all test artifacts. In the commands below, `<cache-task>` is the resolved task directory, not another output question. Create its evaluation parent, then run:

```sh
python3 <skill-dir>/scripts/prepare_eval.py <local-main.tex> <cache-task/evaluation/bundle>
```

Use `--ids <stable-label> ...` when preparing a subset. Read the command's help for exact argument grouping. The exporter accepts the canonical `T2`, `T3`, `T4`, `Solutions` sequence and the legacy `Problems`, `Solutions` sequence, never a mixture. Tier sections may be empty, but the selected export must contain a problem. It targets labelled `problem` environments and matching `Solution to Problem` subsections; all numbering remains global. It strips optional problem titles, labels, group headings and source material from public tasks. Private solution `Verbatim` certificate blocks are preserved as literal bytes of text and are never executed or copied to the public prompt. Inspect unusual macros or a different source structure before exporting. Unsupported structures require a faithful manual adaptation or a focused exporter change; a successful regular-expression match does not establish a complete problem.

The bundle separates solver material from author material:

```text
<cache-task>/evaluation/bundle/
  manifest.json
  public/task-0001/
    prompt.md
    task.json
  private/
    task-0001.json
```

The manifest records anonymous task IDs, source labels, statement and solution hashes, and public/private artifact locations. The public `task.json` contains only `schema_version`, the anonymous `id`, and `statement_sha256`. The private task file keeps the reference solution and rubric. Never send the manifest, private file, original TeX, source paper, bibliography, or authoring history to the solver.

Review the exported prompt itself. It must contain the entire mathematical task and required definitions, with no answer, citation, source title, hints imported from the solution, or dependence on another problem. Where relevant, define requested output structure and whether a derivation or proof is required. Inspect anonymous JSON metadata as well as the Markdown file. Source labels and hashes identify tasks for the evaluator; they need not reveal source content to a solver.

For a standalone local problem file outside the exporter's supported structure, stage a faithful TeX adaptation in the cache and verify it against the source. Leave the source unchanged. Changing a statement or answer requires a new bundle or explicitly tracked changed hashes; never overwrite earlier real-run records with a new problem version.

## Review the private rubric

Preparation creates an **unreviewed** rubric. Before real execution, a responsible evaluator must read the reference solution, verify it, and set the review fields and evidence. This is mathematical review, not a request to send private material to the solver.

Core rubric fields are:

```json
{
  "review_status": "reviewed",
  "reference_status": "verified",
  "answer_type": "manual",
  "accepted_answer": null,
  "requires_proof": false,
  "requirements": ["All parameter domains and exceptional cases are handled."],
  "verification_evidence": ["Exact substitution verifies the stated solution and endpoint conditions."]
}
```

Use concrete requirements and evidence for the actual problem. These example descriptions are not evidence that an arbitrary task has been checked. The review statuses do not establish tier, novelty, or external dataset acceptance.

Calculation questions default to `requires_proof=false`. Set it to true only when the statement explicitly requires a proof or substantive mathematical derivation as part of the answer. For this field, an explicit proof obligation includes such a required derivation. The JSON `derivation` field and ordinary supporting calculation alone do not create that obligation. Grade every requested value and parameter case, but do not add proof obligations beyond the question. A short calculation can support a correct answer. Box answers in previews and the manuscript; preserve the chosen machine-readable representation in raw JSON submissions.

Supported automatic answer types are `exact_integer`, `exact_rational`, `exact_json`, and `numeric`; use `manual` for symbolic formulas, variable-dependent identities, asymptotic expansions, roots, special functions, or answers that need a mathematical equivalence judgment. A numeric rubric must set both `absolute_tolerance` and `relative_tolerance` to nonnegative values. Do not lower the answer standard after seeing solver output.

Use `manual` mathematical review by default for candidate screening; Codex can perform it without a separate user approval step. Before export, put any automatic representation requirement in the public question: decimal integer, `p/q`, numeric literal, or the exact structured schema. Otherwise use `manual`, which can accept equivalent LaTeX or boxed answers. Formatting alone is not evidence that a calculation is hard.

An exact representation check can establish only what its contract says. `exact_json` compares a predetermined structured answer, not arbitrary mathematical equivalence. A rational answer should be reduced or compared by exact rational arithmetic. Numeric tolerance must be fixed before solving and appropriate to the requested accuracy. A sample of parameter values cannot establish an identity on a continuous domain.

If a proof or derivation is required, automatic answer agreement never establishes full-task correctness. A reviewer must check the argument against the requirements. Mark unresolved cases pending rather than forcing a pass or fail.

Keep stable tasks, public/private separation, raw submissions, and a deterministic acceptance contract. A family-specific feasibility checker does not grade general formulas or proofs. Prepared certificates and reference baselines are not model runs; do not transfer their scores to Codex capability claims.

## Statement review version gate

For real formal `operation=authoring` runs, including tested standalone elaboration, complete the automatic [statement review](../research/statement-review.md) before starting the final trial. The skill's main agent automatically coordinates the independent reader, editorial correction and semantic verification; the runner enforces their accepted-version record and does not itself invoke a reader model or edit a source bank. Review roles inherit the current authoring configuration; the formal solver retains the selected screening configuration.

After the initial exported reference and rubric are verified, freeze the baseline before any editorial change:

```sh
python3 <skill-dir>/scripts/statement_review.py prepare <initial-bundle> <cache-task/review-initial>
```

Preparation creates `packet.json`, anonymous per-task `reader/<task-id>/prompt.md` and `answer-schema.json`, and a pending `review-template.json`. The packet contains the private original statement, reference and rubric snapshots. Never give the packet, template, private reference, or directory-wide access instructions to the reader; provide only its anonymous prompt and public answer schema with the [reader role instructions](../execution/agent-prompts.md#statement-reader). Preserve the reader's original response and use it to complete a new `reviews.json`; a pending template is not an acceptance record. Preparation pins each stable task's first declared origin in the bundle's `.statement-review-origins/` directory. A later preparation of that stable task must explicitly supply `--baseline-packet`; a derived bundle inherits that declared origin rather than resetting it.

If no change is needed, use that packet. After meaning-preserving corrections, re-export the final bank into a new bundle. Recheck the matching final reference and fill its newly unreviewed rubric before preparing a new review directory that retains the original baseline:

```sh
python3 <skill-dir>/scripts/statement_review.py prepare <final-bundle> <cache-task/review-final> \
  --baseline-packet <cache-task/review-initial/packet.json>
```

Run a fresh reader on the final anonymous files and a distinct [semantic checker](../execution/agent-prompts.md#semantic-checker) on the original and final versions with their matching references. Record both decisions and concrete evidence in a new final `reviews.json`. Do not change the baseline to make a revision appear equivalent. An unresolved original meaning or a mathematical change returns to research; it cannot receive an editorial preservation pass.

Validate the completed record, then pass it to the runner with configuration bound to the final bundle:

```sh
python3 <skill-dir>/scripts/statement_review.py validate <final-bundle> <cache-task/review-final/reviews.json>
python3 <skill-dir>/scripts/run_eval.py <final-bundle> \
  --configuration <run-config.json> --invocation-id <current-operation-id> \
  --statement-reviews <cache-task/review-final/reviews.json> \
  --work-root <cache-task/tmp> --isolation instruction-only
```

Both preparation and validation accept `--ids <task-id> ...` for a selected subset. The gate requires an independent-reader pass, a distinct semantic-preservation pass with no hints, no unresolved blocking findings, and matching task identities and final prompt, reference/private rubric, answer-interface and baseline hashes. Missing, stale, incomplete or rejected records stop an authoring run before a solver starts. The validator also checks that the actual anonymous reader prompt and answer-schema copies match the packet. The run stores the accepted review and packet as both exact UTF-8 bytes and parsed values separately from solver inputs, with the answer-schema hash in run metadata. Before grading or classification, the scorer revalidates that frozen snapshot against its hash, manifest, schema and task bindings; replay does not depend on the external baseline files remaining in place. Hashes and origin markers preserve the declared bytes and lineage; they cannot prove that a baseline predates an unrecorded edit, mathematical equivalence, or actual reviewer independence. Retain the substantive review evidence and report those limits accurately.

`--trial-purpose` defaults to `formal`. Use `--trial-purpose diagnostic` only for a separately identified development diagnostic; it does not require this mandatory pre-final review and the classifier rejects it as formal screening evidence. This purpose field is not an additional intake question. A formal authoring dry run without reviews remains planned with review pending; it does not satisfy the gate. Supplied reviews are validated even for diagnostics, evaluation or dry runs. Evaluation-only runs remain read-only and do not require an authoring correction loop; supplied review records are still validated, and discovered defects never authorize a source rewrite. Changed statements require new applicable review, bundle/configuration bindings and formal evidence; keep historical records intact. An unchanged, already tested version does not need automatic resampling.

## Select the run configuration

Resolve [startup intake](../execution/task-settings.md#startup-intake) before dependent work, using its missing-material and path rules rather than a separate output questionnaire. Keep authoring and target-model execution distinct under [model roles](../execution/task-settings.md#model-roles). Pass the selected exact test model and effort to the independent solver process; unsupported settings stop the run without a substitute.

Use the selected [defaults and overrides](../execution/task-settings.md#defaults-and-model-selection). Evaluation's cache holds the bundle, runs, logs, and reports; it requires no problem-output path or separate results directory and grants no source-editing permission.

Bind the current user-instruction or Q&A record to the operation ID, bundle hashes, task set, and materialized settings. The explicitly selected Epoch profile additionally needs the user's acknowledgement of the CLI protocol differences and resolves the effort from its published snapshot rather than assuming the local default applies. A strict external-protocol request cannot run through this approximate backend.

For a simple initial pilot, three structurally different questions with one fresh attempt each are usually informative for checking the process. This is a suggested scope, not a compulsory limit. Expand to the requested bank or selected IDs after the workflow is sound. Never infer mathematical difficulty from a run that failed to start.

Python-assisted solving is the default policy for this skill. The Codex CLI provides shell access that can run Python and may expose additional core tools. The current runner does not implement a Python-only tool boundary, Epoch's stateless Python tool, or its `submit_answer` protocol. Record both requested tool policy and the actual available tool scope. Record the Python executable and useful libraries actually available to the solver. If tools are unavailable, either correct the environment before the run or state the resulting configuration clearly. A library-installation or network retrieval step inside an ostensibly offline trial changes the condition and must not pass unnoticed.

The runner requests the native rollout cap and remaining-token reminder, checks configuration acceptance, and records the accounting and forced-submission limitations. Optional wall timeouts are enforced. Record actual input-plus-output use without adding cached-input or reasoning subtotals twice; unavailable use stays unknown. Model self-identification is not independent runtime confirmation.

Example:

```sh
python3 <skill-dir>/scripts/run_eval.py <cache-task/evaluation/bundle> \
  --configuration <run-config.json> --invocation-id <current-operation-id> \
  --work-root <cache-task/tmp> --isolation instruction-only --dry-run
```

`--dry-run` validates and plans without a model call. With no configuration or explicit overrides, it shows the skill's local defaults; with a configuration, the runner uses that record's profile unless `--profile` is explicit. Use `--codex <executable>` to select the CLI installation and `--ids <task-id> ...` for a subset bound in the record. Remove `--dry-run` after the intake is resolved and references are reviewed. A software plan is not a model run. The authenticated local Codex runtime requires neither a new user-visible chat nor an API key.

`--work-root` places controller and per-task directories and their `TMPDIR`, `TMP`, and `TEMP` under the specified cache-local root. It must be disjoint from the bundle and must not contain the source file. An explicitly invalid or unwritable root fails before model execution without falling back to a system temporary directory. The runner records requested and resolved work roots and per-task paths. This location control does not enforce filesystem or network isolation.

## Independent solver execution

A failed Codex process stops the batch without retrying or substituting configuration. Remaining assigned tasks are recorded as execution errors that were not started. Token-budget exhaustion and operational timeout are recorded separately and do not by themselves prevent other tasks from running.

Each task gets a fresh process and workspace containing only its anonymous mathematical prompt and answer interface. This avoids deliberately supplying the authoring context; it is not filesystem isolation. Disable/request no web use in the runtime configuration as supported and instruct the solver to avoid source lookup. The pilot still reports network access as unenforced.

Keep authoring instructions and this skill out of the solver prompt. A solver is supposed to solve the single exported question, not curate the question bank or invoke this evaluation workflow. Instruct it not to load the skill, private solutions, manuscript, source papers, or authoring memories; these instructions remain unenforced by the filesystem. Do not send previous attempts or grading feedback into a nominally independent attempt. Multiple attempts require separately recorded trials, not invisible retries after errors.

Use one final submission per attempt. The final JSON object has exactly three fields: `answer` (string), `derivation` (string), and `complete` (boolean). Save the unmodified final submission and event log. Preserve malformed or operationally incomplete submissions and their execution state. Do not supply missing mathematics or repair raw submissions. Judge an existing valid final by its actual content and stated obligations; the self-report `complete=false` does not by itself prevent a pass.

For every attempt, retain enough metadata to identify the problem hashes, requested model, reasoning effort, effective configuration, tool policy, execution duration, exit state, and raw outputs. Record the actual model separately only if independently exposed by the runtime; otherwise leave it unknown. Do not infer it from the requested alias, the model's self-report, or an assumption about fallback behavior.

## Grade and report

Run:

```sh
python3 <skill-dir>/scripts/score_run.py <bundle-folder> <run-folder>
```

Use `--reviews <review-file>` for reviewed decisions. The review file is a JSON object with `schema_version: 1`, the `run_id`, and a `reviews` list. Each review contains:

| Field | Value |
|---|---|
| `id` | Anonymous task ID from this run. |
| `statement_sha256` | Exact statement hash recorded for the attempt. |
| `private_sha256` | Hash of the entire private task file recorded for the attempt. |
| `submission_sha256` | Hash of the frozen final submission recorded for the attempt. |
| `answer_correct` | Boolean decision, or `null` when still unresolved. |
| `derivation_correct` | Boolean decision, or `null` when still unresolved. |
| `reviewer` | Identifiable reviewer or review method. |
| `notes` | Specific mathematical grounds for the decisions. |

Keep reviewer decisions linked to the exact task, run, and underlying raw answer; any changed answer requires a new submission record. The runner freezes the final submission bytes after the process stops, and the scorer checks this hash and the preparation manifest hash before accepting a review. A review cannot override a fixed automatic answer rule. If the rule or reference is wrong, correct it and prepare a new identified bundle rather than altering the old run's meaning. The scorer rejects dry-run records and changed hashes, and writes `grading.json` and `report.md` inside the run folder.

Judge the following separately:

| Quantity | Meaning |
|---|---|
| Answer correctness | The final requested values or expressions satisfy the answer contract. |
| Full-task correctness | The answer and every required derivation, proof, domain, and remainder condition are satisfied. |
| Execution status | Completed, timed out, or failed to execute; independent of mathematical quality. |
| Review status | Automatically decided under a suitable exact contract, manually reviewed, or pending. |

`solver_complete` records the model's `complete` self-declaration separately; `complete=false` does not force mathematical failure. Judge full-task correctness from the actual statement obligations, using `requires_proof=true` only when a proof is explicitly requested. The scorer records `submission_valid` and preserves `execution_status`. A hash-valid final with the exact JSON schema can be graded when execution is `completed` or `token_limit`; a token limit without a valid final remains `TOKEN_LIMIT`, not a mathematical FAIL. Execution/configuration errors, unstarted tasks, and interruptions do not receive ordinary mathematical grading.

Mathematical review should state a concrete reason, such as a wrong constant, missing parameter case, or incorrect asymptotic term. Review proof completeness only when `requires_proof=true`. Preserve the reason for any unresolved judgment and identify model-assisted review as such.

Report task counts and denominators. Separate established successes, mathematical failures, pending reviews, token limits, operational timeouts, and infrastructure errors. Budget exhaustion is not a wrong formula and remains in the denominator. The scorer reports confirmed passes over all assigned tasks and displays separate status counts. Do not present the answer-only rate as the full-task rate.

Report the selected bank and statement hashes, model request and independently known actual model, effort, attempts, tools, limits, and isolation flags alongside performance. Preserve raw events and submissions so the result can be inspected. Software tests with a fake CLI and dry-run plans belong in implementation validation and never in model-performance tables.

Use a pilot to discover defects, estimate observed solve rates under its specified conditions, and prioritize further review. It cannot by itself certify a FrontierMath tier, establish contamination-free novelty, or measure general model ability. When a question changes after review, evaluate the changed version as a new version and keep earlier records identifiable.

## Screen authoring candidates

Every final Author question, and every final strengthened version when testing is in scope, must have a complete verified reference and one fresh independent formal target-model trial using the selected exact model, effort, tools and full configured limits. Do not substitute a depth forecast, an authoring-model diagnosis, a lightweight trial, fake CLI, or dry run. Record the trial purpose; the classifier does not itself authenticate that purpose. Lightweight trials are optional development evidence within authorized resources, never final formal evidence. A changed statement or answer needs a new identified version/reference and fresh formal test; an unchanged version with a completed formal test needs no automatic repeat.

After mathematical review, run:

```sh
python3 <skill-dir>/scripts/screen_candidates.py <bundle> <run> --reviews <reviews.json>
```

The classifier reuses the scorer's read-only `assess()` and its task, private-reference, submission and review hash checks. It assigns **local operational groups**, not official FrontierMath human-difficulty tiers or final-bank admission. Preserve correct and failed trial records. The AI's [post-trial research decisions](../research/problem-refinement.md#post-trial-research-decisions) may select, strengthen, or abandon a version without altering its recorded classification.

Let `U` be the frozen reported cumulative solver input plus output, `S` the frozen submission threshold and `B` the frozen budget. Current defaults are in [evaluation settings](../execution/task-settings.md#defaults-and-model-selection); the classifier reads `run.json`'s `budget.total_input_output_tokens_requested` and `budget.submit_after_tokens_requested` and never supplies missing historical defaults. With `B=1,000,000` and `S=660,000`, apply:

| Verified outcome of the formal trial | Group |
|---|---|
| Valid submitted answer is mathematically wrong, or an explicitly requested proof has been verified wrong | **T4**, `mathematical_fail`, even if U is unknown. |
| Full task correct and U > B | **T4**, `correct_above_budget`. |
| Actual token-budget exhaustion without a valid final submission | **T4**, `budget_exhausted_unsolved`; preserve `TOKEN_LIMIT`, not mathematical FAIL. |
| Full task correct and U ≤ S | **T2**. |
| Full task correct and S < U ≤ B | **T3**. |
| Mathematical review unresolved, including an unreviewed required proof | **pending**, no assigned tier. |
| Execution/configuration error, unstarted process, interruption, or operational timeout | **pending**, no assigned tier. |
| Correct final but unknown/inconsistent U or missing thresholds needed for its comparison | **pending**; do not assume zero use or insert defaults. |

A valid final at `token_limit` is still graded: a wrong final is a mathematical failure, while a correct final uses known U and the frozen thresholds. The self-report `complete=false` alone is not failure. Do not add proof obligations to a calculation question. A native exhaustion event is not proof that U exceeded B: its reason remains separate even though both outcomes are locally T4. A configured budget, a reminder, or a run that never started is not an exhaustion event.

Use the frozen attempt's `total_input_output_tokens`. If the field is absent and frozen `usage` contains complete valid input and output counts, sum those two counts and record this provenance. An explicitly null, invalid, or contradictory total stays unresolved. Cached input is already in input; reasoning output is already in output. Do not add either subtotal again. The classification basis is reported solver I/O; disclose unverified coverage of failed/retried backend requests and account billing, rather than calling it a complete billing total. Preserve any recorded usage scope/coverage and native-budget limitations.

Output uses `schema_version=2`, `policy=local_pilot_tiers`, `policy_version=1`, with `decision=classify` or `pending`, `tier=T2/T3/T4/null`, a reason code, frozen thresholds, usage provenance, evidence hashes and counts. The script writes `screening-v2.json`; if different content already exists there, it writes a content-hash-suffixed v2 file. Identical content can be reused. It returns the actual output path and does not overwrite historical `screening.json`, grading, submissions or source files.

Deliver the versions selected through [post-trial research decisions](../research/problem-refinement.md#post-trial-research-decisions) under the agreed [work goal](../execution/continuous-goals.md), using their actual assigned groups. Keep unselected versions, pending work, and raw evidence in the cache; classification does not automatically write a question into the final bank. Use [the canonical manuscript layout](../research/problem-design.md#present-and-write): T2, T3, T4, Solutions; continuous Problem numbering, no T1 or topic-title hints, and matching complete English solutions. Historical model results retain their original task IDs and hashes; display-number mappings live in the cache. Standalone evaluation still reports every assigned task and never curates or rewrites its source bank.
