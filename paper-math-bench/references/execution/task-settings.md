# Task intake and execution settings

**Contents**

- [Startup intake](#startup-intake)
- [Question language](#question-language)
- [Required materials and interruptions](#required-materials-and-interruptions)
- [Model roles](#model-roles)
- [Paths and write scope](#paths-and-write-scope)
- [Question templates](#question-templates)
- [Defaults and model selection](#defaults-and-model-selection)
- [Epoch reference settings](#epoch-reference-settings)
- [Codex execution](#codex-execution)
- [Configuration record](#configuration-record)
- [Sources](#sources)

These settings govern Find, full authoring, standalone elaboration, and evaluation. Follow the [question-language policy](#question-language) for intake and clarification. Find selects literature; full authoring includes research, elaboration, and screening; standalone elaboration runs target-model trials only when requested; evaluation leaves its local source unchanged.

## Startup intake

Read the current request and established choices in the same batch before asking questions. Find, Author, Elaborator, and Evaluation are task entry points. The two sustained-work goal modes are continuous duration and accepted-question count; they do not replace the source scope. Resolve the applicable source/task scope first, then the work goal, paths, write scope, and test settings:

| Entry point | Required input and scope | Output | Cache | Test configuration |
| --- | --- | --- | --- | --- |
| Find | Supplied papers or a bounded arXiv discovery scope: start date, end date, principal-paper count, and subject scope selected by multi-select or free-text input | Selected papers and precise links; no problem-output path for Find-only | Separate working-cache root | None for Find-only |
| Author | Supplied papers or authorized arXiv discovery with start date, end date, principal-paper count, and subject scope; these scope fields are required in both duration and accepted-question-count modes. Resolve the separate work goal for full authoring | Final problem-bank folder/file and new, append, replacement, or explicitly untested preview scope | Separate from the final bank | Formal screening model/effort; use `gpt-5.6-sol / max` when unspecified |
| Standalone Elaborator | A local bank/problem-file path and selected problem numbers or labels; append or in-place modification scope | The same local bank/file; do not ask for another output path | Separate working-cache root, including recoverable backups | Resolve model/effort only when target-model trials are requested; construction inherits the current configuration |
| Standalone Evaluation | A local bank/problem-file path, all tasks or selected labels; model/effort overrides may be omitted to use the defaults | Test files, bundle, runs, logs, and reports all go in the cache; source stays read-only | The only output location; no separate problem-output or results-directory question | Use the same model/effort default when unspecified |

Standalone Elaborator and Evaluation accept local source paths; a remote URL or a problem supplied only in chat is not a substitute. Reuse reference solutions, paper references, and solve evidence already present. Ordinary bank evaluation does not need a new paper input. If source-paper review is also required, resolve only the missing required reference; papers never enter anonymous solver inputs.

The discovery platform is arXiv. Before any new principal-paper discovery, resolve its bounded source scope: the user's start date, end date, positive integer principal-paper count, and subject scope. Ask for every missing field in the current conversation under the [follow-up rule](#required-materials-and-interruptions). This applies to Find, search-and-author requests, and new principal-paper discovery during elaboration, in both sustained-work goal modes. A work duration, requested question count, or permission to choose sources never supplies or waives the paper-date interval or paper count. Supplied papers can establish a fixed source pool and its count directly; without additional principal-paper discovery, do not ask for search dates or repeat its known count.

When dates are missing, offer two choices: the default last 10 natural days including today, or a user-specified start/end interval. The default is a proposed choice that needs an actual user response, not permission to search silently. Resolve the accepted relative interval once using the message date and known timezone, record that anchor and the resulting dates, and reuse them without midnight drift. Use the first arXiv submission (v1) date, inclusive of both dates, with UTC query boundaries: start at 00:00 UTC and exclude 00:00 UTC on the day after the end date. Validate start ≤ end. Do not invent a paper count, category, or material topic restriction.

Subject scope may cover any arXiv group, archive, or category, including sources outside `math.*`; the existing substantive-calculation and verification standards still apply. Reuse a supplied discipline, subfield, category list, interdisciplinary scope, unrestricted scope, or explicit delegation of subject selection. Before new discovery, if none is established, ask using the subject-scope template below and wait for the actual choice. Do not silently restrict discovery to analysis or another unselected field. A selected broad group includes its subcategories; combine multiple selections as a union unless the user requests an intersection.

The paper count bounds the selected principal-paper pool from which problems may be constructed; it is neither the number of search hits nor the target number of final questions. Record the pool and respect its date and count boundaries when selecting or replacing principal sources. Supplementary reading does not authorize expanding that pool or promoting an out-of-scope reference into a principal source; resolve a necessary scope change with the user first. If the scope cannot supply enough suitable papers or questions, report the actual shortfall rather than silently widening it. If Find is followed by Author, also resolve the applicable Author fields. Do not launch dependent searches, paper-research subagents, a mathematical research Goal, or the continuous research clock until the applicable source scope and remaining required intake are resolved.

Ask focused missing-field questions together when useful, without repeating supplied values or adding a second “confirm everything” round. Preserve a specified model when only its effort is missing. An unsubmitted UI selection is not user evidence; an applicable declared skill default can be materialized without asking a mandatory model question. Reuse unambiguous same-batch choices; an unrelated old run does not configure a new request. User-authorized choices of a path are handled under [paths and write scope](#paths-and-write-scope).

Find, authoring, and elaboration default to the hardest credible calculations under the highest mathematical standards in this skill. Do not ask the user to choose T1/T2/T3/T4; honor an explicit narrower request. Final output groups are assigned after formal testing, not selected as an authoring ceiling. Ordinary Evaluation does not ask for an authoring tier. Find-only, an explicitly untested preview, or elaboration without target-model trials does not ask for a screening model. Mark untested working versions accordingly. Optional budget, timeout, and protocol customization do not become mandatory questions when the defaults suffice.

Once required intake is complete, briefly distinguish the current authoring configuration from the selected screening configuration when both apply, include the short [execution note](#defaults-and-model-selection), and proceed. Elaboration trials use operation `authoring` in the existing schema. Record the actual refinement request and trial scope; do not invent a new operation value or infer editing authority from a test-only request.

For full Author and sustained Elaborator work, also resolve the mode and its user-supplied value under [continuous work goals](continuous-goals.md#scope-and-intake), retaining that guide's bounded-preview and bounded-refinement scope. Infer the mode from an explicit duration or T4 count; ask only for missing or genuinely ambiguous goal parameters in the current conversation. A question-count goal includes the formal screening needed to establish that count. Find-only and standalone Evaluation do not acquire an authoring goal or editing scope from this rule.

## Question language

Write every skill-generated intake or clarification question in English, including questions about source scope, work goals, model settings, missing materials, paths, write scope, or an ambiguity discovered during research. Write every suggested option label and its explanatory text in English, whether presented in chat or through a question tool. This applies regardless of the conversation language and to questions composed by delegated agents.

Preserve actual user instructions and replies verbatim in configuration and research evidence, including their original language. Do not translate, fabricate, or reconstruct raw user evidence to make it English. An English summary may accompany the original when useful, but it must remain separately identified and must not replace the recorded evidence.

## Required materials and interruptions

Before starting the relevant work, check that required information and input materials are identified and readable. When a required item is missing, unreadable, or still unobtainable through authorized access, ask a concrete follow-up question in the current conversation: identify the missing item and what the user needs to supply or clarify. Use an available conversational question tool when supported; otherwise ask plainly in the chat. A missing-information notice or stop report does not substitute for a question.

Keep the task pending while awaiting the actual reply, and pause only work that depends on the missing item. Continue independent, already authorized work when useful. Do not guess required parameters, treat silence or an unsubmitted selection as an answer, or declare the task finished because input is missing. If no independent work remains, leave the concrete question awaiting the user's reply. Incorporate each reply into the established choices, ask only about any remaining gaps, and continue the original task once its prerequisites are resolved.

Allow up to six minutes for a needed user reply while continuing useful independent work where possible. At that threshold, an unanswered required choice remains pending: do not adopt the displayed default, invent the paper count, or infer approval. If no independent authorized work remains, preserve the work and report the missing input and actual interruption. This waiting allowance does not change a fixed work goal, reset its clock, or automatically extend its deadline; blocked waiting must not be reported as productive continuous work or goal completion.

Apply the same rule when a missing item is discovered during the work, preserving completed work in the agreed cache when available. This rule concerns necessary input materials and unresolved required intake, not ordinary mathematical difficulties, unsuccessful research directions, or optional literature.

## Model roles

| Role | Model and effort | Context |
| --- | --- | --- |
| Research, construction, and reference checking | Inherit the current Codex authoring model and effort unless the user overrides them | May inspect sources and references; reference checking is not anonymous solving |
| Authoring-model diagnostic | Inherit the current authoring configuration unless overridden | Fresh context; only anonymous statement and answer interface |
| Target-model trial, including formal screening | Explicitly request the selected model and effort from the runner; use the local default unless the user overrides it | Fresh independent solver with the configured tools and limits |

Selecting a screening model does not change the authoring model. The default intermediate mode and result interpretation are defined in [anonymous diagnostics](../research/problem-design.md#anonymous-diagnostics). Record the chosen purpose before execution; choosing it is not another mandatory user questionnaire. An authoring-model success is not a target-model result.

For an anonymous subagent, use `fork_turns="none"`. Authoring mode inherits the current configuration; target mode explicitly sets the selected model and reasoning effort. If an interface cannot preserve or request the intended configuration, use a supported execution path or report the limitation; do not silently inherit or substitute a different setting. Formal trials use the configured evaluation runner.

Preserve an explicitly chosen effort. When the user requests the highest effort without naming it, check the exact model and backend's supported levels rather than assuming that the literal value `max` is universally highest. Requested settings and independently exposed runtime settings remain distinct; unavailable actual-model or actual-effort metadata stays unknown.

## Paths and write scope

Resolve the cache independently of the final bank. If a required bank destination or cache root has not been supplied, ask for the missing path in the current conversation under the [follow-up rule](#required-materials-and-interruptions). If the user explicitly asks the agent to choose it, select a suitable fresh location, state the choice, and proceed without another approval question. An established same-batch path remains resolved.

An existing cache root is not a collision requiring approval: create a fresh task subdirectory, or reuse the identified directory when continuing that task. Put controlled downloads, extracts, research notes, calculations, scripts, candidate staging, backups, diagnostics, and evaluation artifacts there. Keep the final bank separate. Preserve meaningful versions and raw trials; cache is not permission to discard them. Use explicit paths and a cache-local temporary directory for task-controlled commands.

For Evaluation, the bundle belongs under the task cache, so its export staging, runs, grading, and reports also remain there. Pass a disjoint cache-local `--work-root` to the runner for its controller, solver, and controlled temporary environment. The path is not another user-selected output field. Do not promise that unrelated operating-system or external-tool storage is relocated by this setting.

Inspect a named final bank and its immediate bank folders before asking about an actual collision. Recognize TeX/BibTeX files or established bank structure and name concrete targets:

- **New Author destination:** use the supplied free folder; if only a parent is given, choose a free child consistent with its naming convention and state it.
- **Existing Author bank with unclear write scope:** ask whether to create a new folder, append, or replace a specifically named target. A path alone does not authorize replacement.
- **Elaborator:** its input bank/file is also its output. “Modify these labels” authorizes in-place changes to those statements and matching solutions; “append” preserves them and adds new labelled versions. If scope is unclear, ask only append versus modification and the affected labels, not another output path.
- **Clear append or replacement:** honor the specified target and scope without repeated confirmation. Back up replaced files in the task cache, preserve unrelated files, and replace each statement and matching solution together.
- **Replacement without an exact target:** ask for the missing bank/file or labels. Replacing specified problems and replacing a whole bank are different scopes; neither authorizes recursively deleting a folder.

State the actual affected files and scope before writing. Evaluation never rewrites the source; a faithful exporter adaptation belongs in the cache. New bundles and runs must preserve earlier raw trials and their hashes rather than overwrite them.

## Question templates

Adapt these English prompts to the actual request and available question tool. Keep all questions and suggested options in English under the [question-language policy](#question-language). Skip every already resolved field. Suggested options expose the default; the user can enter another model, effort, path, or folder name in free text.

**Model and effort**

State `gpt-5.6-sol / max` as the default and proceed when no override is supplied. Ask only to resolve an ambiguous or partial explicit override, preserving every supplied field. For example: “For your selected `<model>`, which reasoning effort should I use?”

**Missing source or selection**

> Author: for new arXiv discovery, use the subject-scope prompt below for a missing subject choice. Ask only about other necessary paper or source restrictions that remain unresolved; reuse supplied papers and established or explicitly delegated restrictions.
>
> Elaborator/Evaluation: give the local bank/problem-file path and the problem numbers or labels, or say all.

**Missing arXiv source scope**

> Which arXiv date interval should I use: the last 10 natural days including today (default), or a start and end date you specify? How many principal papers should form the source pool for this task?

Present the date choices as selectable options when supported, and state the anchored absolute dates for the proposed default. Ask the date and paper-count fields in both duration-based and question-count-based authoring. Reuse every supplied field and ask only for missing ones; a fixed list of supplied papers already establishes its count.

**Missing subject scope**

> Which subjects should supply the papers? Choose one or more broad groups or specific arXiv categories, or enter disciplines, subfields, or category codes yourself. You may also choose unrestricted subjects or explicitly delegate subject selection to the AI.

Present all broad groups together: mathematics (all branches, including algebra, number theory, geometry, topology, combinatorics, probability, logic, analysis, optimization, and numerical mathematics), physics (all archives, not only `physics.*`), computer science, statistics, quantitative biology, quantitative finance, economics, and electrical engineering and systems science. Let the user select subcategories from the [current official arXiv taxonomy](https://arxiv.org/category_taxonomy); examples are not a whitelist. Use a multi-select control when available. If the question tool supports only single selection or free text, provide a free-text answer field accepting several names or codes, with the choices shown in the question, rather than forcing a single subject. Record the selected subjects and any mapping from free text to categories or search terms; clarify only a genuinely ambiguous interpretation.

**Missing work goal**

> Should the sustained work run continuously for a duration you specify, or continue until a specified number of accepted local T4 questions is complete? Give the hours or question count.

Ask only when the applicable goal mode or value is missing or ambiguous. The paper count belongs to source scope and cannot answer this question. A supplied duration or accepted-question count already identifies its goal mode. When both are supplied, resolve an unclear stopping relationship. Find-only, standalone Evaluation, and agreed bounded previews/refinement do not acquire an extra sustained-work goal.

**Missing paths**

> Author: where should the final problem bank and the separate working cache be saved?
>
> Find-only/Elaborator/Evaluation: where should the working cache be saved?

Ask only for the missing path. Elaborator already outputs to its input bank; Evaluation stores every test artifact in the cache.

**Unclear write scope**

> For `<actual bank>` and `<actual labels>`, should I append strengthened versions or modify those problems in place?

For an Author destination collision, name the actual existing banks and offer a free new folder, append, or replacement of a specified target. Clear prior instructions need no repeated choice. Keep settings, paths, and scope questions concise rather than combining them into a long yes/no approval.

## Defaults and model selection

| Setting | Skill default |
| --- | --- |
| Test model | `gpt-5.6-sol` |
| Reasoning effort | `max` |
| Profile | `local-pilot` |
| Independent attempts | One per question |
| Per-question cumulative input plus output budget | 1,000,000 tokens |
| Budget and submission-preparation reminder | 660,000 tokens used; 340,000 remaining; unfinished work may continue within the full budget |
| Question-wide wall timeout | None unless selected |
| Requested tools | Python allowed; web/source lookup disabled |

Short execution note for intake/summary:

> Local Codex pilot: Python allowed, web search disabled; one attempt per question, nominal requested budget of 1,000,000 cumulative input/output tokens, budget reminder at 660,000, no additional wall timeout. The reminder does not end unfinished work; submit when finished or by the budget boundary. Native accounting does not guarantee a hard cutoff in full input/output units. Isolation and timely submission rely on instructions; this is not a strict Epoch protocol.

The local default is this skill's test policy, subject to explicit user overrides; matching a published effort does not make the local pilot equivalent to the Epoch protocol. Preserve explicit model/effort overrides and check runtime support; unsupported settings stop without substitution. Never silently change the requested model or reasoning effort.

The model, effort, and token-budget settings also serve as [references in design](../research/problem-design.md#references-in-design).

The per-question screening budget governs one model attempt, not total authoring effort or unlimited replacement candidates. Apply the [adaptive authoring resource decisions](../research/problem-design.md#explore-and-simulate) to the overall work and optional trials; this adds no mandatory intake field.

Use `epoch-tier4-v2` only when explicitly selected. For that profile, use the highest published effort for the exact model in the dated snapshot. Ordinary GPT-6.1, GPT-6, and GPT-5.6 entries use `max`; older models can use `xhigh` or `high`. Special labels such as `promax` need their own verified mapping. Refresh official data only when a requested entry is missing or an update is requested.

## Epoch reference settings

The [snapshot](../../data/epoch-settings.json), verified on 2026-10-19, records these Tier 4 v2 reference values:

| Setting | Reference value |
| --- | --- |
| Per-question cumulative budget | 1,000,000 input plus output tokens |
| Submission threshold | At 660,000 tokens, the next model action must submit |
| Python execution | Stateless calls, each at most 30 seconds |
| Answer execution | Parameterless `answer()`, at most 30 seconds |
| Question-wide wall limit | Not published |

Cached input remains input. Reasoning tokens are part of output; do not add either subtotal twice. An upper budget does not require consuming it; an early correct submission ends normally. Official temperature, attempt count, and per-generation output limits are not established by this snapshot.

## Codex execution

When a token budget is selected, the runner requests native rollout-budget tracking, input/output weights both 1.0, and a remaining-token reminder. In `local-pilot`, the reminder reserves attention for final submission without ending unfinished exploration before the full budget; a completed answer may be submitted earlier. Only the explicitly selected `epoch-tier4-v2` profile instructs immediate submission on that reminder under its reference protocol. The runner checks local configuration acceptance before a real trial. Unsupported settings stop without a substitute.

Native accounting is experimental and its equivalence to Epoch accounting is unverified. A reminder does not force tool selection. Codex also differs from Epoch's stateless Python and submission interface. Preserve `epoch_protocol_match=false` and `forced_submission_enforced=false`. An explicitly selected Epoch-profile run must acknowledge these differences; a request for strictly matching external execution remains unstarted if the backend cannot provide it.

An optional operational wall timeout belongs in the selected settings and user-instruction evidence. Token-budget exhaustion, operational timeout, and infrastructure failure are different outcomes.

## Configuration record

Materialize all selected settings, including defaults, before a real run. Record the current operation ID and actual user instructions and/or intake replies, with message references and UTC timestamps. Bind the record to the bundle path, manifest hash, benchmark hash, and task IDs. The record is configuration evidence, not authentication of the human.

The existing `qa` list stores actual asked questions and replies. Preserve the actual English question and the user's verbatim reply, even when that reply is in another language. A complete explicit prompt can instead use `user_instructions` entries with `text`, `user_message_ref`, and `provided_at`; preserve its original language and do not invent a confirmation dialogue. Both forms can coexist, and every supplied list must be valid and nonempty. Evidence timestamps must fall between operation start and record creation.

Example for an explicit instruction with no additional question:

```json
{
  "schema_version": 1,
  "invocation_id": "<current-operation-id>",
  "operation": "authoring",
  "invocation_started_at": "<operation start UTC>",
  "created_at": "<record creation UTC>",
  "binding": {
    "bundle": "<absolute bundle path>",
    "manifest_sha256": "<manifest hash>",
    "benchmark_sha256": "<benchmark hash>",
    "task_ids": ["task-0001"]
  },
  "user_instructions": [{
    "text": "<actual complete user instruction>",
    "user_message_ref": "<actual message reference>",
    "provided_at": "<message UTC>"
  }],
  "settings": {
    "profile": "local-pilot",
    "model": "gpt-5.6-sol",
    "effort": "max",
    "wall_seconds": null,
    "total_input_output_tokens": 1000000,
    "submit_after_tokens": 660000
  }
}
```

For intake replies, use `qa: [{"question": "<actual question>", "answer": "<actual reply>", "user_reply_ref": "<reply reference>", "answered_at": "<reply UTC>"}]` instead of, or alongside, direct instructions. Set `acknowledge_cli_differences=true` only when the user actually chooses the disclosed local approximation for an Epoch-profile request.

A bound record is single-use for a real run; dry runs do not consume it. A further authorized run needs a new bound record within the agreed scope, not an automatic repeated confirmation. Preserve earlier runs. Model/effort mismatches are configuration errors; missing actual runtime metadata stays unknown.

```sh
python3 <skill-dir>/scripts/run_eval.py <bundle> \
  --configuration <run-config.json> --invocation-id <current-operation-id> \
  --work-root <cache-task/tmp> --isolation instruction-only --dry-run
```

An omitted `--profile` uses the record's profile, or the local default when no record is supplied for a dry run. Remove `--dry-run` only after the intake and reference review are complete. Software planning alone authorizes no real trial.

## Sources

- [Epoch Tier 4 v2 methodology](https://epoch.ai/benchmarks/frontiermath-tier-4-v2).
- [Epoch model-result data](https://epoch.ai/data/benchmark_data.zip), member `frontiermath_tier_4_v2.csv`.
- [Epoch's linked implementation](https://gist.github.com/tadamcz/7b3a45d0d5d35f758bb6deb8000731bb).
- [Codex configuration](https://developers.openai.com/codex/config-reference) and [rollout-budget configuration source](https://github.com/openai/codex/blob/main/codex-rs/features/src/feature_configs.rs).

Epoch snapshot accessed 2026-10-19; attributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Local defaults are defined by this skill's configuration policy.
