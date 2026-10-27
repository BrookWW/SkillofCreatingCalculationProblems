---
name: paper-math-bench
description: "Find papers with substantive calculation opportunities, author hard concise calculation benchmarks, strengthen local problems, or evaluate local TeX banks. Use for mathematical source discovery, benchmark construction, refinement, and evaluation management, not ordinary problem solving."
---

# Paper Math Bench

**Contents**

- [Find papers and opportunities](#find-papers-and-opportunities)
- [Author problems](#author-problems)
- [Elaborate existing problems](#elaborate-existing-problems)
- [Evaluate a bank](#evaluate-a-bank)
- [Shared standards](#shared-standards)

Develop the hardest well-posed calculation problems the mathematics and agreed resources can support, with compact, self-contained statements following the [statement-style guidance](references/research/statement-style.md). Make the principal literature's connected mechanisms necessary to obtaining the answer, and strengthen their dependencies through research, calculation, adversarial review, and redesign. Obscurity, extra steps, and longer notation do not add depth. Default to the highest credible mathematical difficulty without asking for a T1–T4 goal; honor explicit user overrides and prioritize a verified answer. Communicate in the user's language, except that every skill-generated intake or clarification question and every suggested option label must be in English regardless of conversation language; follow the [question-language policy](references/execution/task-settings.md#question-language). Keep problems, solutions, and evaluation interfaces in English. Explicit user instructions take precedence over skill defaults.

The benchmark objective is a verified, concise calculation that the agreed `gpt-5.6-sol / max` trial does not correctly complete within 1,000,000 cumulative input plus output tokens. The per-question criterion is the agreed token budget, not elapsed solving time; use the [formal-test policy](references/evaluation/model-testing.md#screen-authoring-candidates) and report the runtime's actual accounting limits. Before every research judgment, actively reconsider the greatest credible difficulty, compact self-contained formulation, verified correctness, this model-and-token objective, and the user's binding scope and resources. Choose the next action against these principles rather than treating a local score, convenient shortcut, or completed procedure as the goal. The AI makes the intermediate judgments; this repeated principle review does not require printing a checklist at every step.

Choose the requested task entry point. **Find** discovers and checks mathematical opportunities; it can stand alone or lead into authoring. **Authoring** uses supplied literature or Find results and includes research, construction, the [elaboration loop](references/research/problem-refinement.md), and formal screening. **Standalone elaboration** strengthens selected problems in their local bank and runs target-model trials only when testing is in scope. **Evaluation** tests a local bank without rewriting it. These entry points share mathematical standards and retain their own input, output, and write scopes. The two sustained-work goal modes are duration and accepted-question count.

Use the [workflow and data-flow map](references/workflow-map.md) for the entry points, research branches, and input/output destinations.

Apply [References in design](references/research/problem-design.md#references-in-design) to models and budgets, solve records, statement-style guidance, tier descriptions, and literature. Decide their use and depth from the task, and explain references that materially affect a mathematical decision.

Resolve the applicable [intake and working paths](references/execution/task-settings.md#startup-intake), including conversational follow-up for missing required information or material. Source discovery uses arXiv and requires both the user's date interval and principal-paper count before research starts, in both goal modes. Offer the last 10 natural days including today or a custom date interval, and wait for the actual choice. Source scope and work goal are separate requirements. Reuse established choices. Construction and elaboration inherit the current Codex configuration; [anonymous diagnostics](references/research/problem-design.md#anonymous-diagnostics) and selected-model trials have distinct decision rules. Find alone and explicitly untested working versions do not require a screening-model choice.

For full authoring and sustained elaboration, resolve a [continuous work goal](references/execution/continuous-goals.md): work continuously for the user's duration, or continue until the requested number of accepted local T4 questions is reached. Bounded untested previews and bounded standalone refinement retain their agreed scope; a supplied continuous duration still applies. User-specified parameters are binding; intermediate research decisions belong to the AI. These modes use Goal execution, not scheduled or heartbeat tasks. Find-only and standalone evaluation retain their existing scope.

## Find papers and opportunities

Read [paper search](references/research/paper-search.md). Accept a supplied paper pool by URL or local path, or discover papers within the user's resolved arXiv date interval and principal-paper count. Download and read each selected Find paper in full under [principal-paper reading](references/research/paper-search.md#inspect-the-principal-mathematics); supplementary literature is chosen by the AI within the source-scope rules. Prioritize main results whose substance is a calculation, then consider calculation cores within proof-oriented work. Check the mathematical opportunity, its strongest credible answer route, and reference feasibility before recommending it.

Return precise sources, main-result locations, proposed calculation targets, checked dependencies, and remaining gaps in the task cache. A search list is not a verified problem bank. Continue into authoring when requested; a Find-only request ends with its opportunity report and does not run model trials.

## Author problems

Read [problem design](references/research/problem-design.md), [problem refinement](references/research/problem-refinement.md), and the [difficulty guide](references/evaluation/difficulty-levels.md). Apply the [statement-style guidance](references/research/statement-style.md) under [References in design](references/research/problem-design.md#references-in-design).

1. Investigate the mathematics and source connections that can support a strong calculation. Observe the full-reading requirement for selected Find papers. Beyond that requirement, the AI chooses supplementary reading, results, foundations, extensions, alternative methods, and investigation order and depth. A related paper may become the main or sole mathematical source only within the agreed source pool or after an authorized scope change.
2. Select an observable that makes a broad, connected part of the principal mathematics necessary. The AI chooses useful core comparisons, reduction checks, and investigations of obstacles and reference feasibility through the [elaboration loop](references/research/problem-refinement.md#construction-and-adversarial-review), including [cross-literature synthesis](references/research/problem-refinement.md#cross-literature-synthesis) where useful. A dependency map or a list of rejected targets is not a completed construction.
3. Formulate one coherent calculation with few necessary definitions. Preserve the difficult discoveries in the work needed to obtain its answer, without revealing them through leading subparts or extending the statement to carry ornamental machinery.
4. Complete the reference and pass the [mathematical gate](references/research/problem-design.md#choose-and-formulate): the question is well-posed, essential discoveries affect the result, and all graded obligations are verified. Use depth and shortcut assessments to improve the construction; they cannot replace final testing or veto its test-based tier.
5. Choose useful next steps under the [research decision policy](references/research/problem-refinement.md#continue-freeze-or-stop), using [collaborative review](references/research/problem-design.md#explore-and-simulate) when it helps. Feed shortcut or trial evidence back into construction. Interpret any authoring-model diagnosis through its actual route, separately from target-model screening.
6. Stage verified candidates in TeX and export the anonymous inputs. Immediately before final formal testing, automatically run the [independent statement review](references/research/statement-review.md), including meaning-preserving editorial corrections and independent before/after verification. Use [evaluation](references/evaluation/model-testing.md) only after its exact-version gate passes for fresh trials of the selected screening model. Every final question must receive one fresh independent formal trial of its exact verified version. Preserve correct and failed trial evidence, assign local T2/T3/T4 groups with `scripts/screen_candidates.py`, and return to [post-trial research decisions](references/research/problem-refinement.md#post-trial-research-decisions) before selecting final output.

Deliver the selected, fully tested questions, identifying their actual main sources, or label an explicitly authorized untested working preview. The usual batch scale is 0–3 questions per starting paper or agreed topic; explicit user goals and scope govern the actual allocation. Trial classification does not automatically admit a question to the final bank. Provide the boxed answer, essential calculation, accessible complete verification, precise sources, difficulty rationale, and screening status. A report with no completed questions must meet the [continuation and stopping guidance](references/research/problem-refinement.md#continue-freeze-or-stop), distinguishing investigated alternatives, local reference gaps, and evidence about remaining opportunities; report goal completion separately.

The final bank uses `T2`, `T3`, `T4`, then `Solutions` sections, continuous global Problem numbering, and no optional topic titles; see [presentation](references/research/problem-design.md#present-and-write). For an authorized new bank, run `python3 <skill-dir>/scripts/init_project.py <destination-folder>`, then populate `main.tex` and `references.bib`. Inspect existing banks first; preserve class, macros, labels, spacing, and unrelated files. Replace a statement and solution together, with a recoverable copy. A path alone does not authorize replacement. Compile and inspect affected pages; add no pagination or spacing patches.

## Elaborate existing problems

Read [elaboration](references/research/problem-refinement.md) and the applicable [authoring standards](references/research/problem-design.md). Start from the selected problems in a local bank, their references, sources, and available solve evidence. Preserve the strongest verified version while identifying the core, strongest answer route, weak dependency, and concrete strengthening opportunity. Apply the same long-chain target selection and cross-literature synthesis used inside authoring.

Deliver the strengthened statement and matching reference in the same local bank, appending a version or replacing the selected entries as authorized. Keep backups and working evidence in the resolved cache under the [path contract](references/execution/task-settings.md). Include necessary discoveries, shortest-route assessment, source roles, and verification/screening status. Unscreened working versions are labeled accordingly. Requested trials use [evaluation](references/evaluation/model-testing.md), with configuration operation `authoring` and the same [pre-test statement review](references/research/statement-review.md).

## Evaluate a bank

Read [evaluation](references/evaluation/model-testing.md) before execution. The bundled runner provides instruction-only isolation, not enforced offline or strict blind testing.

1. Inspect the local source bank and selected tasks; export with `scripts/prepare_eval.py <main.tex> <cache-bundle-folder>`. Keep the source unchanged and the bundle, runs, and reports in the task cache.
2. Review anonymous prompts, complete references, and private rubrics. Bind actual current user instructions or intake replies to the bundle and task hashes. Calculation tasks default to `requires_proof=false`; enable it only for an explicit proof obligation.
3. Run the selected exact model/effort in fresh solver processes receiving only anonymous tasks and the answer interface. Unsupported settings stop without substitution. A dry run validates software only:

   ```sh
   python3 <skill-dir>/scripts/run_eval.py <bundle-folder> \
     --configuration <run-config.json> --invocation-id <current-operation-id> \
     --work-root <task-cache>/temp \
     --isolation instruction-only --dry-run
   ```

   Remove `--dry-run` after intake and reference review are complete.
4. Preserve raw submissions and events. Use `scripts/score_run.py <bundle> <run> --reviews <reviews.json>`; for authoring target-model trials, follow with `scripts/screen_candidates.py <bundle> <run> --reviews <reviews.json>`. Report answer correctness, full-task correctness, execution status, limits, and unresolved reviews separately.

## Shared standards

- The main agent should autonomously divide work and coordinate subagents when independent work can improve quality or efficiency. Integrate and verify their results. Role-specific context requirements are in [Explore and simulate](references/research/problem-design.md#explore-and-simulate); formal trials follow [evaluation](references/evaluation/model-testing.md#independent-solver-execution).
- Give each decision one authoritative instruction and link to its details. Keep generic mathematical roles in the skill; put subject-specific constructions in task-local candidate notes. Each Markdown document has a linked contents guide; Python files use concise navigation comments.
- Record source exposure and provisional difficulty without claiming novelty, official tier certification, or contamination-free testing. Templates are references, not new questions or solver inputs.
- Preserve current approved meaning in documentation. Keep evaluation artifacts outside manuscript sources where practical, with hashes identifying exactly what was tested. Distinguish requested model settings from independently confirmed runtime metadata.
