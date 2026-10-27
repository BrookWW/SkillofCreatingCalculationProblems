# GPT-6 authoring and review prompts

**Contents**

- [Scope and prompt structure](#scope-and-prompt-structure)
- [Automatic review coordinator](#automatic-review-coordinator)
- [Statement reader](#statement-reader)
- [Semantic checker](#semantic-checker)

## Scope and prompt structure

These templates guide the authoring and review agents that inherit the current Codex model and effort. They do not change the formal screening model: keep the agreed `gpt-5.6-sol / max` or the user's explicit selected override. The [GPT-6 prompting guide](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices) recommends explicit task, constraints, completion criteria, tool and delegation instructions, and proportionate verification. Apply those principles to the concrete roles below; mathematical policy remains in [statement review](../research/statement-review.md).

State the role, exact allowed inputs, requested output, and conditions for returning a blocking finding. Keep instructions focused on the actual task and reader background. User instructions override skill defaults. Automatically complete authorized work and delegate the specified independent roles; do not insert a per-question user approval step. Use meaningful checks for the changed behavior and avoid repeating broad verification without new evidence, following the same [official prompting guidance](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices).

Apply the [question-language policy](task-settings.md#question-language) to any intake or clarification question and suggested option produced by these roles. Preserve supplied raw user evidence in its original language.

## Automatic review coordinator

Use this task shape when a verified candidate is ready for final formal testing:

```text
Freeze the verified statement, public answer schema, reference and rubric before editing.
Prepare the review packet. Automatically start a fresh independent statement reader
using only that task's anonymous prompt, public answer schema and reader instructions.
Preserve the original response. Make only minimal editorial corrections whose meaning
is established by the original verified task. Have a distinct semantic checker compare
the frozen original and final versions with their references. Give the final exported
prompt to a fresh reader. Resolve blocking findings; optional wording suggestions do
not require edits. If original meaning is uncertain or the proposal changes mathematics,
return the candidate to mathematical investigation rather than declaring equivalence.
Record actual role identities and findings. Validate the exact-version review before
starting the final screening trial. Never fabricate a pass or transfer old trial results
to changed inputs. Do not ask the user to review each question.
```

The skill's main agent performs this orchestration. `statement_review.py` prepares and validates evidence; `run_eval.py` checks the record before a formal authoring solver call. These scripts do not themselves launch the review agents.

## Statement reader

Start with `fork_turns="none"`. Supply only the task's exact anonymous `prompt.md`, public `answer-schema.json`, and these role instructions; do not supply the private packet or review template.

```text
Review whether this mathematical statement can be read unambiguously. Do not solve it
or assess its difficulty. You have only the anonymous prompt and public answer schema;
do not look up sources or read references, other attempts, authoring records or skills.
Assume undergraduate mathematical literacy and recognition of conventional terminology.
Do not expand standard L^p, Sobolev spaces, CP^n, convergence in distribution, standard
inner products or familiar special functions merely because a definition is possible.
Identify only missing problem-specific objects/notation or competing conventions that
affect the task. Prefer compact formulas when clearer, retaining necessary short text.
For each blocking issue quote the precise passage, state what cannot be determined or
which interpretations compete, and propose the smallest correction without solving it.
Briefly restate the given objects, requested target and answer requirements. Return
PASS only when no blocking issue remains; otherwise return NEEDS_REVISION. List optional
style suggestions separately. Your unfamiliarity with a standard term is not a defect.
```

Preserve the raw report. The coordinator fills the packet's final reader fields from the actual report: `agent_id`, `fresh_context`, `input_scope`, `status`, `restatement`, and `issues`. Final `issues` contains unresolved blocking findings; optional style notes can remain in the raw report. Only an actual `PASS` with no blocking findings can populate a passing record.

## Semantic checker

Use a distinct fresh-context independent agent with `fork_turns="none"`. Supply the frozen original and proposed final statements, answer interfaces, and matching private references/rubrics. This checker may see the answer; it is not the anonymous reader or formal solver.

```text
Determine whether this proposed editorial revision preserves the original verified
mathematical task exactly. Compare original and final objects, domains, quantifiers,
assumptions, conventions, calculation target and answer contract, using both references.
Record concrete before/after comparison evidence for each category, including unchanged
categories. Check effective mathematical conditions and parameter cases are unchanged,
including meaningful grouping and operation order. Explicitly stating an already fixed
implicit condition is allowed only if its exact equivalence follows from the verified
original; never introduce a new effective assumption. Check no target is narrowed,
no answer changed and no solution hint introduced. The same final
answer does not establish equivalent questions. Do not choose an interpretation when
the original intent is uncertain. A mathematical redesign must not pass as clarification.
Return PASS only if meaning preservation and absence of solution hints are established;
otherwise return NEEDS_REVISION with the exact discrepancy or unresolved original meaning.
```

Preserve the raw report and fill the final `semantic_check` from it, including `agent_id`, `status`, `meaning_preserved`, `no_solution_hints`, `evidence` for `objects`, `domains`, `quantifiers`, `assumptions`, `conventions`, `target`, `answer_contract`, and unresolved blocking `issues`. Author, reader and semantic-checker identities must be distinct. Metadata and hashes make the record auditable; they are not automatic proofs of equivalence or enforced isolation.
