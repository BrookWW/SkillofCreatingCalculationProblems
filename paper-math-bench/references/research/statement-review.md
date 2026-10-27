# Statement review before formal testing

**Contents**

- [Trigger and independent reader](#trigger-and-independent-reader)
- [Necessary definitions and formula-first wording](#necessary-definitions-and-formula-first-wording)
- [Preserve mathematical meaning](#preserve-mathematical-meaning)
- [Automatic correction and acceptance](#automatic-correction-and-acceptance)
- [Version binding and limits](#version-binding-and-limits)

## Trigger and independent reader

For Author and tested Elaborator candidates, automatically start this review after the complete reference is verified and the AI chooses final formal screening, immediately before the agreed `gpt-5.6-sol / max` trial or explicit selected override. It is not an initial research stage, a solver diagnostic, or an additional user approval. The main agent coordinates the following AI roles and resolves their findings within the existing editing scope.

Start a fresh subagent with `fork_turns="none"`, inheriting the current authoring model and effort unless the user explicitly overrides them. Provide only the exact exported anonymous prompt, the public answer interface, and the review instructions. Do not provide sources, bibliography, reference solutions, authoring history, earlier trials, or feedback. Ask the reader to briefly restate the given objects, requested calculation and answer requirements, then identify concrete missing information or competing interpretations. It must not solve the question or estimate difficulty. Use the [reader prompt](../execution/agent-prompts.md#statement-reader). If independent delegation is unavailable, keep the review pending rather than substituting the author's own reading for an independent pass.

## Necessary definitions and formula-first wording

Use undergraduate mathematical literacy and recognition of conventional mathematical terminology as the reading baseline. Do not expand standard named concepts such as $L^p$, Sobolev spaces, $\mathbb{CP}^n$, convergence in distribution, standard inner products, or familiar special functions. The reader's unfamiliarity alone does not justify another definition. Supply only problem-specific objects or notation that cannot be reconstructed from the statement, and competing conventions that affect its meaning or answer. Check domains, quantifiers, assumptions, parameter cases, dependence of random objects, normalization, signs, branches, boundary or counting conventions, and the requested output where relevant; do not demand an explanation for every item when conventional usage already determines it.

Prefer formulas for sets, maps, distributions, operators, conditions and calculation targets. Keep short words such as “Define” and necessary geometric or combinatorial descriptions. Do not hide long prose in `\text{...}`, multiply aliases to reduce words, set a prose quota, or delete conditions for brevity. A useful review finding identifies the exact passage, missing information or competing readings, and the smallest necessary correction; distinguish blocking defects from optional stylistic suggestions.

## Preserve mathematical meaning

Before any editorial revision, freeze the verified original statement, answer interface, reference and rubric in the cache. Editorial revision must preserve their mathematical meaning exactly. An independent semantic checker uses the [semantic-checker prompt](../execution/agent-prompts.md#semantic-checker) to compare that baseline with the proposed final version and matching reference, checking objects and domains, quantifiers, assumptions, conventions, target and answer contract. It must verify that the effective mathematical conditions and parameter cases are unchanged, no target narrowed, no answer changed, and no solution hint introduced. Making an already fixed implicit condition explicit is allowed only when its exact equivalence is established from the original verified meaning; it cannot introduce a new effective assumption. Formula equivalence includes grouping and operation order where these affect meaning, not merely similar notation. Identical answers alone do not establish equivalent questions. If the original intent is uncertain or the proposal changes the mathematics, return to mathematical investigation; do not choose an interpretation or disguise reconstruction as clarification. A mathematical redesign starts a separately identified verified candidate, not a meaning-preserving editorial pass.

## Automatic correction and acceptance

The author makes minimal justified corrections, the semantic checker verifies equivalence and reference consistency, and a fresh reader reviews the actual final exported prompt. Repeat for unresolved blocking findings, not to chase a smaller word count. Reviewers record their independent identities, findings and evidence; preserve original responses. Only a reader pass, a semantic-preservation pass, and no unresolved blocking findings permit formal testing. These are AI actions, not requests for the user to edit or approve each question.

## Version binding and limits

Bind the accepted review to the final prompt, public answer interface, private reference/rubric and the frozen baseline by content hashes under the [testing interface](../evaluation/model-testing.md#statement-review-version-gate). A changed input needs a fresh applicable review and verified reference before testing; historical trials retain their original hashes and cannot certify a revised statement. An unchanged version with a completed formal trial needs no automatic repeat. Hash checks and origin markers preserve the declared reviewed bytes and baseline lineage; they do not prove that the baseline predates unrecorded edits, mathematical equivalence, reviewer independence, or enforced filesystem isolation. Those remain explicit review evidence and accurately reported limits. Evaluation-only tasks remain read-only and do not acquire editorial authority from a reader finding.

