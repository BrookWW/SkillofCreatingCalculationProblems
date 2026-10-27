# Problem refinement and research decisions

**Contents**

- [Scope and entry points](#scope-and-entry-points)
- [Choose an answer that needs the long chain](#choose-an-answer-that-needs-the-long-chain)
- [Cross-literature synthesis](#cross-literature-synthesis)
- [Construction and adversarial review](#construction-and-adversarial-review)
- [Current mathematical record](#current-mathematical-record)
- [Independent roles and diagnostic evidence](#independent-roles-and-diagnostic-evidence)
- [Post-trial research decisions](#post-trial-research-decisions)
- [Continue, freeze, or stop](#continue-freeze-or-stop)
- [Deliver the strengthened version](#deliver-the-strengthened-version)

## Scope and entry points

Elaboration develops a mathematical core into a stronger compact calculation. It applies during initial target selection, throughout full authoring, and as a standalone request to strengthen existing problems. Full authoring includes elaboration and final screening; screening feedback can reopen construction. Standalone elaboration includes construction, reference verification, and useful authoring-model diagnosis; target-model trials, including lightweight trials, require testing to be included in the user's request. Evaluation alone does not authorize rewriting the tested bank.

Resolve the standalone local source and selected problems under [intake](../execution/task-settings.md#startup-intake), with same-bank output and a separate cache under [paths and write scope](../execution/task-settings.md#paths-and-write-scope). Follow [required-material handling](../execution/task-settings.md#required-materials-and-interruptions) and [authoring standards](problem-design.md). Reuse the supplied literature, explicit difficulty overrides, model choices, source exposure, and solve evidence. Otherwise pursue the highest credible mathematical difficulty without a tier-selection question. Inspect an existing statement and its reference before changing either. When a reference is missing or incorrect, distinguish repairing validity from increasing depth. Preserve the strongest verified version while exploring a stronger one.

The outcome is a verified mathematical improvement or a supported decision about the remaining directions. Searches, longer derivations, rejection lists, and completed note fields are activities or evidence; they do not by themselves strengthen the problem. Before each intermediate research judgment, the AI actively revisits the [governing principles](../../SKILL.md), then chooses the action within the user's scope. Selected Find papers retain their [full-text reading requirement](paper-search.md#inspect-the-principal-mathematics); supplementary reading and the research considerations below are chosen by the AI. They are not a fixed scoring system, compulsory branch order, minimum number of revisions, or additional user questionnaire. Mathematical correctness, faithful evidence, and the user's explicit parameters remain binding.

## Choose an answer that needs the long chain

The AI decides how to investigate the available arguments, mechanisms, hypotheses, and connections when choosing an observable. Work backward from a candidate answer to judge which discoveries determine it and how they interact. Seek a compact calculation whose answer depends on substantial, connected mathematics, with the direction and depth of the investigation chosen by the AI.

An argument map can inform target selection; it is not evidence that the resulting question retains the paper's depth. If the answer reduces to one displayed constant, a local formula, or an uncoupled standard subproblem, use that evidence in deciding whether to reconstruct, replace, or abandon the target. Do not hide an easy quantity behind a long existence proof. Conversely, a short final formula can encode a difficult sequence of structural discoveries.

Keep the problem self-contained. The anonymous solver must reconstruct the necessary mathematical structure from the statement, without being told to read a paper or follow leading subparts. Preserve a compact statement rather than importing chapter summaries, proof scaffolding, or definitions that already settle the decisive choices. The goal is the essential connected argument, not mechanical coverage of every chapter or a fixed number of discoveries.

Support claimed dependencies with mathematical evidence. The AI chooses useful ways to investigate them, such as removing, replacing, or decoupling an asserted key structure and seeking a route to the original answer. Explain where a claimed necessary choice affects the next steps or a component of the result. A different numerical answer alone does not establish a deeper dependency. Alternative cores, depth potential, and reference feasibility inform target selection without imposing a mandatory comparison stage; immediate ease of verification is not the sole criterion.

## Cross-literature synthesis

The AI decides whether other papers can strengthen the mathematics, resolve an obstruction, change a representation, or expose a shortcut. A concrete weakness or opportunity can guide the search, while a neighboring core may offer a stronger target.

For a material connection, establish:

- The mathematical gap in the current core and the source mechanism addressing it.
- The hypotheses, objects, scales, and parameter ranges on both sides of the proposed connection.
- The bridge that must be proved or constructed; a resemblance of terminology is insufficient.
- How the resulting connection affects the same requested answer and why the solver cannot simply omit it.

Carry out the bridge calculation or proof, incorporate the verified conclusion into the construction, and reassess the strongest answer route. Search findings can redirect the observable or make another paper the main or sole source within the agreed date/count boundaries; a necessary source-pool expansion follows [intake](../execution/task-settings.md#startup-intake) before execution. Record actual source roles and exposure under [References in design](problem-design.md#references-in-design).

Do not equate a bibliography, several independent lemmas, or a count of papers with synthesis. Nor should every known theorem be treated as instantly recognizable by a source-free solver. Assess what is required to discover the applicable theorem, satisfy its hypotheses, and connect it to the target. A newly found theorem may instead collapse a supposedly hard route and require redesign. Within a construction, citation counts and starting-source contribution quotas are not mathematical goals.

## Construction and adversarial review

Maintain active mathematical work toward the agreed goal rather than treating a sequence of low-depth objections as a finished construction. The AI chooses a useful concrete action and uses its result to continue, redirect, or reject the route. The following are research options to select as useful, not compulsory stages, a fixed sequence, or a required number of rounds. Any version used for model testing or final delivery must still pass the mathematical gate.

**Establish the baseline.** Identify the exact requested quantity and domain, the verified reference, and the strongest credible route. For an existing problem, use actual solve evidence when available. Distinguish a routine method after a representation is known from the difficulty of discovering that representation.

**Attack the dependency.** Possible approaches include source theorems, alternative methods, symmetry, conservation, local reductions, numerical inference, and removal of apparent couplings; the AI chooses which to investigate. A claimed shortcut needs enough calculation to show its actual answer, assumptions, and bypassed discoveries. A statement that a method is standard is not a demonstrated shortcut.

**Reconstruct the target.** Focus on the weak dependency: change the observable, the core, the relation among constraints, or the compatibility problem so that consequential discoveries become necessary. Explain where the old reduction stops determining the new answer and what new obstacle replaces it. Pursue neighboring literature when it can supply a useful bridge. Increasing order, parameters, precision, or notation counts as strengthening only when it changes the necessary mathematical work.

**Close the stronger reference.** Compute the answer and verify every requested case and necessary global step under the [mathematical gate](problem-design.md#choose-and-formulate). A stationary point, numerical optimizer, unevaluated integral, or conjectured sharp inequality is not a completed stronger version. Preserve useful calculations as reference gaps without presenting them as established answers.

**Attack again and integrate feedback.** The AI chooses when a further route assessment, independent review, or anonymous diagnostic will help. A diagnostic requires a verified reference. Interpret actual discoveries and bypasses and use them in construction. A failed or successful model attempt does not by itself complete elaboration. Target-model trial decisions follow [evaluation](../evaluation/model-testing.md#screen-authoring-candidates); authoring-model diagnoses follow [their separate policy](problem-design.md#anonymous-diagnostics).

## Current mathematical record

Use the existing candidate notes rather than building a separate reporting system. Keep a concise current record of the target, principal literature mechanisms and verified bridges, necessary dependency chain, strongest answer route, vulnerable dependency, verification status, and the next concrete mathematical action. Update it when calculations change the assessment.

Explain a claimed improvement through the mathematical obstruction and its effect on the requested result. Keep identifiable statements, references, and trial hashes for meaningful versions so evidence remains attached to what was actually tested. Current project documentation describes the current approved mathematics; these records are not a narrative of AI editing or a substitute for construction.

## Independent roles and diagnostic evidence

Apply the [coordination principle](../../SKILL.md#shared-standards). A constructor seeks a stronger coherent target, a literature researcher investigates useful connections, a reference checker verifies correctness and global obligations, and an anonymous solver looks for the least work needed to obtain the answer. Useful roles may overlap, but their evidence is different.

A reviewer who sees the solution can verify it and challenge its depth; that exposure does not show how easily a fresh solver finds the representation. Do not downgrade a candidate solely because its completed solution uses familiar tools, or upgrade it because a reviewer needed a long calculation. Assess the necessary discovery chain and the actual strongest route, using the [statement-style guidance](statement-style.md) and tier guide as references.

For a verified version with materially uncertain depth or conflicting route assessments, consider a fresh authoring-model diagnostic rather than treating a solution-exposed intuition as decisive. This is a useful authoring choice, not a compulsory run for every obvious defect. Anonymous context, model roles, retained evidence, and result interpretation are defined in [Anonymous diagnostics](problem-design.md#anonymous-diagnostics). It does not replace the selected model's formal screening.

## Post-trial research decisions

Every trial returns to research judgment; a score or local tier is not an automatic final-bank decision. Interpret the actual answer route, mathematical validity, source mechanisms, and remaining opportunities together under [References in design](problem-design.md#references-in-design). A correct result at or below the submission threshold records T2 for that version. It does not by itself show shallow mathematics, complete the work goal, or require that version's delivery. Likewise, a model failure does not establish a sound problem or end useful research.

The AI may deepen the same core, reconstruct the observable or constraints, discard the current question, select a different core, or replace the starting paper and restart the literature-to-construction loop. Choose and execute the most useful next action without seeking approval for each research branch. Test evidence can justify abandoning an ineffective construction instead of repeatedly polishing it. Preserve its records in the cache, without promoting abandoned versions into the final bank or rewriting their classifications. Stay within user-specified source, time, count, and write scopes; resolve a necessary scope change in the conversation.

Revisit the principal result alongside foundations, extensions, alternative methods, and neighboring conclusions when this helps explain a shortcut or reveals a better target. Work out a material bridge and its effect on the answer under [cross-literature synthesis](#cross-literature-synthesis). No number of papers, conceptual leaps, reviewer votes, revision rounds, or token-use thresholds determines which research branch the AI must choose. Use independent review where it improves the mathematical judgment; it is not a mandatory approval stage for abandoning or changing direction.

When a changed version is worth testing, first close and verify its reference, then use a fresh identified trial. A rejected idea need not be tested, and an unchanged version with a completed formal trial need not be repeatedly sampled. Do not rerun until a favorable failure appears. All valid raw trials remain evidence whether or not their versions are selected.

Final selection follows the agreed [work goal](../execution/continuous-goals.md) and the AI's mathematical assessment. Distinguish deciding that a version is worth selecting from assigning its immutable test-based group. A demonstrated shortcut may motivate reconstruction or nonselection; a speculative difficulty label cannot alter the recorded trial result. Questions whose reference or execution remains unresolved are not completed final questions.

## Continue, freeze, or stop

Sustained research is an action obligation within the user's scope and resources. Before each choice to continue, freeze, redirect, or stop a branch, revisit the governing principles and remaining mathematical opportunities. The AI judges which direction and action offer the most useful progress, using actual grounds, feasibility, and the prospect of consequential discoveries; no one promising branch is compulsory merely because it remains imaginable.

A shortcut, failed coupling, reference gap, or solved version concerns that version or route. Consider alternative cores, representations, relationships among constraints, observables, and useful neighboring literature as the mathematics warrants. The AI may abandon an unpromising question or paper without exhausting every conceivable alternative. Preserve useful verified versions as working evidence; a correct reference, a provisional difficulty assessment, or model failure alone does not complete the overall goal.

Freeze a version for formal screening after its mathematical gate passes and the AI judges testing to be the useful next action. A completed trial feeds back into [post-trial decisions](#post-trial-research-decisions). Freezing for a test, classifying its result, and selecting final output are separate decisions; research may continue after any of them within the agreed goal and resources.

End or change a research branch when the AI judges that appropriate from the actual mathematics and remaining opportunities. The [global work goal](../execution/continuous-goals.md) governs ending the whole task: abandoning a branch does not satisfy a duration or question-count goal. At a user resource boundary, interruption, or material lack of progress, report the concrete mathematical state and whether the goal was achieved. Explain unresolved reference obligations and the assessment of remaining opportunities, without claiming that no stronger question exists in the subject. Independent challenge is useful when warranted, not an additional compulsory stopping test.

Honor user-selected paper counts and resource boundaries. Organize mathematical work by progress rather than imposing internal quotas of papers, directions, discoveries, rounds, minimum durations, or token consumption. A user-requested continuous duration is an explicit goal parameter, not an internally imposed minimum. A per-attempt screening allowance does not authorize unlimited replacement trials or define total research resources. More numerical scans are not a productive next step merely because they raise a nonsharp lower value without addressing the missing closure.

## Deliver the strengthened version

Provide the compact statement, boxed answer, essential calculation, accessible complete reference, precise sources and their roles, necessary dependency chain, strongest-route assessment, and verification/screening status. A substantive improvement must be visible in the mathematics, not only in the report.

For standalone elaboration, apply the resolved same-bank append or in-place modification scope under [paths and write scope](../execution/task-settings.md#paths-and-write-scope), preserving versions and evidence in the task cache. Standalone elaboration without formal trials delivers explicitly unscreened working versions; it does not imply formal admission. When screening is included, every selected final strengthened version needs its verified reference and one fresh independent formal trial. Use the existing runner with configuration operation `authoring`, preserve each tested version, and follow [test-based grouping](../evaluation/model-testing.md#screen-authoring-candidates), retaining correct as well as failed trial evidence. A changed statement or answer needs a new identified version and fresh test before final selection. Evaluation-only requests retain their source-bank scope and do not silently trigger edits.
