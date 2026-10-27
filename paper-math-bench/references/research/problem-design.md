# Calculation problem design

**Contents**

- [Intake and sources](#intake-and-sources)
- [References in design](#references-in-design)
- [Choose and formulate](#choose-and-formulate)
- [Explore and simulate](#explore-and-simulate)
- [Anonymous diagnostics](#anonymous-diagnostics)
- [Statement review before formal testing](#statement-review-before-formal-testing)
- [Screen and select](#screen-and-select)
- [Present and write](#present-and-write)

Aim for the greatest credible mathematical difficulty and as many necessary, connected discoveries as a compact problem can support. Apply the highest mathematical standards by default, without a startup tier-selection question; honor explicit user overrides. A usual batch has 0–3 final problems per starting paper or agreed topic; the [user's work goal](../execution/continuous-goals.md) and scope govern allocation, and actual main sources may come from the ensuing literature search. Read [elaboration](problem-refinement.md) for the construction loop, long-chain target selection, cross-literature synthesis, post-trial decisions, and continuation. It is integral to authoring and also has a standalone entry point.

## Intake and sources

Follow [startup intake and model roles](../execution/task-settings.md). Start from supplied paper URLs, arXiv identifiers or local documents, or reuse a [Find handoff](paper-search.md#report-and-handoff). A direct Author request with supplied papers does not require Find. Preserve supplied source, difficulty, screening settings, and output choices; ask only about unresolved fields. An explicitly untested preview makes no formal calls.

Treat supplied papers as research entry points within the established source pool. Follow important foundations, extensions, alternative approaches, and neighboring structures. A related paper may offer a stronger candidate and become its main or sole source only within the agreed source bounds; resolve any necessary date or paper-count change under [intake](../execution/task-settings.md#startup-intake) before expanding the pool or promoting supplementary reading. Combine sources when their mechanisms have a useful mathematical dependency. A contribution quota for an individual paper or a fixed citation count within each problem does not improve the target or replace the user's source-pool boundary.

Selected Find papers follow the [full-text reading requirement](paper-search.md#inspect-the-principal-mathematics). The AI decides which supplementary literature and results to read, how deeply to study them, and when to revisit or expand the investigation under [References in design](#references-in-design). Use the mathematics actually established to understand obstacles, representations, dependencies, and promising targets. Record actual source exposure and precise locations, verify the assumptions and connections relied on by the candidate, and distinguish established conclusions from unresolved steps.

The AI decides whether and when [cross-literature synthesis](problem-refinement.md#cross-literature-synthesis) can improve the target. When a connection is used, verify it and its effect on the candidate rather than merely listing related work. Useful discoveries may redirect the target. Calculation, review, or trial evidence can justify revisiting the synthesis; its breadth and timing are research judgments, not a citation quota or a separate survey-writing requirement.

Use existing working notes for exact titles, authors, versions, URLs/paths, page/equation/theorem locations, the dependency map, and a concise synthesis: `mechanism | source and hypotheses | connection or gap | effect on requested output`. Inspect rendered pages for ambiguous formulas. These are reviewable research notes, not a requirement to create a separate file for every step.

Use the [statement-style guidance](statement-style.md) under the reference policy below to assess statement economy, representations, necessary discoveries, structural choices, and complete solution arguments.

## References in design

Apply the [governing principles](../../SKILL.md) before every research judgment. The selected screening model, reasoning effort and budget, available solve trajectories and accounting, statement-style guidance, tier descriptions, and relevant literature inform that judgment. Beyond the selected-Find-paper reading requirement, decide what to examine, how deeply to study it, and how to use and weigh it for the current mathematical problem. Explain references that materially affect target selection, redesign, or a stopping decision. Their role follows the actual problem rather than a preset hierarchy of importance; a reference may reshape the mathematical core.

The selected model-and-budget configuration provides a concrete design reference; obtain its current values from [evaluation settings](../execution/task-settings.md#defaults-and-model-selection). Interpret observed use with its actual accounting and solution route: cumulative input includes repeated and cached input, and reasoning tokens are part of output. One observed rollout does not establish the minimum work needed, a linear distance to budget exhaustion, or a guarantee that another version will exceed the budget. Formal execution still follows the user's selected configuration. Statement-style guidance and tier descriptions likewise inform judgment without establishing an official tier or prescribing a particular construction.

## Choose and formulate

Select the target under [Choose an answer that needs the long chain](problem-refinement.md#choose-an-answer-that-needs-the-long-chain). The AI chooses which core comparisons, reductions, obstacles, and reference-feasibility checks are useful, and when to investigate them. Use the source understanding developed in research to judge the observable and its necessary dependencies; a map of an argument alone does not establish the resulting problem's depth.

A conceptual leap resolves a non-obvious obstruction: discovering a representation, hidden structure, interacting constraints, a construction, or a consequential choice. Explain the obstacle, why a standard local method does not settle it, and how the discovery restricts the next step or determines the answer. Seek additional such discoveries where they strengthen the actual mathematics. Do not pad the chain with routine steps or impose a numerical leap quota.

The anonymous solver receives no source lookup. Reconstructing a public result may require substantial discovery; public availability alone does not make it shallow. Include credible theorem recognition in shortcut review, without treating every source theorem as automatically known to a source-free solver. Record exposure separately from mathematical depth and do not claim novelty from rephrasing or changing parameters.

Use [construction and adversarial review](problem-refinement.md#construction-and-adversarial-review) to challenge the target and carry out structural reconstruction. For a calculation, assess the work needed to obtain its requested value separately from proving all analytic details. A difficult validity proof does not upgrade an easy answer. If a short route contains a profound discovery, assess that discovery rather than its length.

Write one coherent calculation target with few necessary definitions and plain, preferably elementary language. Apply the [statement-style guidance](statement-style.md) to keep the statement economical. Leave decisive representations and structural choices to the solver; omit source hints, unused background, redundant symbols, and leading subparts. If definitions overwhelm the question, improve the formulation or change the object. Missing information and obscurity do not supply difficulty.

Complete and verify the unabridged reference before model diagnosis or screening. Cover every requested parameter case, constant, structural choice, and explicit proof obligation. Precisely cited standard lemmas are acceptable after checking their hypotheses. Supply the decisive problem-specific argument and any required global step; a citation or assertion in its place leaves the reference unfinished. Numerical checks can detect errors, not close a proof gap. A concise displayed solution comes after this verification and identifies its omitted supporting detail.

Bind each model trial to its exact statement, answer contract, and verified reference. Use concise existing notes to support the AI's mathematical judgment; the following are useful considerations rather than mandatory fields or a fixed pre-trial procedure:

- **Target:** the exact quantity, domain, and answer contract.
- **Necessary discoveries:** the obstacles, their verified dependencies and locations in the calculation, source roles, and any useful deletion or replacement checks.
- **Shortest route:** the strongest shortcut found, its actual mathematical demands and any uncertainty or shortfall against the highest design ambition; a positive tier forecast is not required to test a valid final question.
- **Coverage:** the essential definitions, complete verification, and unresolved issues, if any.

Fix ill-posed statements and incomplete or incorrect references before testing. The AI may strengthen, redirect, or abandon a candidate during research; mathematical validity alone does not require spending a formal trial on an unselected candidate. Every final delivered question must nevertheless have the required exact-version test. Keep its recorded test-based group distinct from the decision to select it.

## Explore and simulate

Use the elaboration [research decision policy](problem-refinement.md#continue-freeze-or-stop) to choose whether to develop, redirect, test, or stop a branch. Execute the chosen justified action, integrate the result, and preserve the strongest verified version. The linked section is authoritative for sustained research, branch decisions, resource boundaries, and evidence for a report with no completed questions.

Apply the [coordination principle](../../SKILL.md#shared-standards), choosing useful roles:

- **Literature researcher:** read relevant arguments, test hypotheses and connections, and return precise sources and opportunities.
- **Constructor:** develop the target and complete reference, showing how necessary discoveries determine the result.
- **Reference checker:** see the reference and verify all graded obligations, assumptions, sharpness where applicable, and the claimed shortest route; challenge a stopping assessment when that review is needed. This is not an anonymous solver.
- **Anonymous solver:** use a fresh context with only the statement and answer interface, seeking the least work needed for correct outputs. Follow the diagnostic policy below or the formal execution policy as appropriate.

For these optional research roles, without delegation perform the checks directly and disclose that no independent simulation occurred; the required independent statement review below has its own pass conditions. Model roles follow [evaluation settings](../execution/task-settings.md#model-roles); mathematical interpretation follows [anonymous diagnostics](#anonymous-diagnostics).

Apply the [construction loop](problem-refinement.md#construction-and-adversarial-review) to revisions, recompute the reference, and obtain a fresh shortest-route assessment. Keep versions and their evidence identifiable rather than passing feedback into a supposedly fresh attempt.

## Anonymous diagnostics

Choose and record the purpose before the run. Unless the user specifies otherwise, use an **authoring-model diagnostic** in a fresh context, inheriting the current authoring model and effort. An optional **target-model trial** instead uses the exact selected screening configuration. Both require a verified reference; neither replaces final formal screening. This choice is an authoring decision within scope, not a mandatory extra intake question.

For an authoring-model diagnostic, interpret the actual route:

- A correct answer by a routine route can motivate structural improvement, a new target, or abandonment within scope; the AI chooses after revisiting the governing principles. If that verified version is delivered as final, it still receives formal testing and its test-based group.
- A correct answer requiring substantial discoveries may remain a candidate for the selected model's formal test. Success alone does not discard it, even if the authoring model is believed stronger.
- Refer to the actual trajectory, including time, token accounting, unsuccessful avenues, and decisive discoveries, under [References in design](#references-in-design). Explain the mathematical obstacle and strongest credible route; a long run or failure alone does not pass the mathematical gate.

Do not infer that one model will solve a task because another did. A reference checker who saw the answer is not evidence of anonymous difficulty. Short or incomplete exposition is not enough to classify the route; verify what was actually needed to obtain the answer.

For a target-model trial, including an optional lightweight trial, use the test-based grouping rules in [evaluation](../evaluation/model-testing.md#screen-authoring-candidates). Correct answers remain usable evidence and are not automatically discarded. Neither a correct nor a failed lightweight trial satisfies the final formal test. Do not use an authoring-model diagnostic to assign a final target-model group.

Every anonymous solver receives only the self-contained statement and answer interface, with no paper, bibliography, source hint, reference solution, authoring notes, previous attempt, or feedback. Use `fork_turns="none"` for subagents. In authoring mode, preserve the current configuration; in target mode, explicitly set the selected model and effort or use the configured runner. Check backend support and preserve any explicit user override; unsupported settings are not an invitation to substitute.

Keep the purpose, problem version/hash, model and effort requested or inherited, independently reported runtime settings when available, tools, limits, original response, correctness review, and shortest-route assessment. Unknown metadata stays unknown. Record the available log scope and isolation limits accurately. Target-model process events and frozen submissions follow the evaluation workflow; authoring diagnostics remain separately identified working evidence.

## Statement review before formal testing

After the reference is verified and a candidate is selected for final formal screening, automatically run the [statement review](statement-review.md). A fresh anonymous reader checks necessary definitions and ambiguities; a separate semantic checker verifies that editorial revisions preserve the frozen original meaning and matching reference exactly. Keep standard concepts unexpanded and prefer formulas where they improve clarity. These AI steps do not require per-question user approval.

Follow the linked review procedure and [executable version gate](../evaluation/model-testing.md#statement-review-version-gate) before launching the final trial. The optional research-role fallback above does not replace its independent review requirements.

## Screen and select

Use [evaluation](../evaluation/model-testing.md) after the mathematical gate and [independent statement review](#statement-review-before-formal-testing) pass. Stage statements and solutions in a working TeX file accepted by the exporter, inspect the anonymous prompt, and review the private rubric. Calculation tasks default to `requires_proof=false`; enable it only for an explicit proof requirement.

Run fresh formal attempts with the agreed exact screening model, effort, tools, and limits. Grade requested answers separately from full-task correctness and execution failures. Apply `scripts/screen_candidates.py` only to target-model runs with reviewed results. A version retained after a lightweight trial still needs the mathematical gate and a final formal trial. A completed final formal trial does not require an automatic repeat for the unchanged version; a revised question needs its own verified reference and fresh identified trial.

After each trial, apply [post-trial research decisions](problem-refinement.md#post-trial-research-decisions) and the [work goal](../execution/continuous-goals.md). The AI chooses whether to strengthen, reconstruct, abandon, change paper within the agreed source pool, continue testing a changed version, or select a final question. Preserve correct, incorrect, and over-budget records and their [local classification](../evaluation/model-testing.md#screen-authoring-candidates), including versions not selected for delivery. Identify actual main sources and any authorized change to the source pool. Pending cases remain in the cache until resolved. An explicitly authorized untested preview is a labelled working version, not a formally classified entry; standalone elaboration without requested trials likewise delivers unscreened working versions.

## Present and write

Provide the concise English statement, boxed answer, essential calculation, precise sources, discovery/shortest-route assessment, and screening status. Make the complete verified reference accessible so a short display cannot hide missing work. Deliver a full explanation when requested, rather than calling a sketch complete. Separate mathematical quality, source exposure, and model performance.

Honor the resolved preview/append/replacement/new-bank instruction. For a new bank use `scripts/init_project.py <folder>`. Preserve existing structure, macros, labels, and unrelated files; replace statements and matching solutions together, with recoverable copies. Default to `amsart` and BibTeX sources. Use exactly `\section{T2}`, `\section{T3}`, `\section{T4}`, then `\section{Solutions}`, with no T1 section. Empty tier sections are allowed. Order questions by T2, T3, T4, preserving stable relative order within each group, and number Problem 1 through N continuously without resetting the counter. Use plain `\begin{problem}` without an optional topic title. Place all complete English reference solutions in Solutions, in matching order with stable label-based references; remove source or method hints from problem headings. Record the display-number, stable-label, version/hash, and original trial-ID mapping in the cache. Formatting-only reordering must not rewrite historical trial hashes or pretend regenerated anonymous IDs are the old IDs. Add no spacing or pagination patches. Compile and inspect affected pages.
