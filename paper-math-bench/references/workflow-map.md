# Workflow and data flow

**Contents**

- [Entry points and outputs](#entry-points-and-outputs)
- [Research and testing loop](#research-and-testing-loop)
- [Inputs and retained artifacts](#inputs-and-retained-artifacts)

This map explains the workflow. The linked guides define its rules; the map does not add research thresholds or authorize execution by itself.

## Entry points and outputs

```mermaid
flowchart TD
    A["User request: task, scope, paths, established settings"] --> B{"Applicable intake resolved?"}
    B -- "No" --> Q["Ask a concrete question in the current conversation; preserve pending work"]
    Q -- "Actual reply" --> B
    B -- "Yes" --> C{"Requested entry point"}
    C -- "Find" --> F["AI investigates sources and calculation opportunities"]
    F --> FR["Download and read each selected principal paper in full"]
    FR --> FO["Cache: source/opportunity report and checked gaps"]
    FO -- "Authoring also authorized" --> R
    C -- "Author" --> R["Research and testing loop below"]
    C -- "Elaborate" --> E["Inspect selected local questions and matching references"]
    E --> R
    R --> RO["Selected verified versions in the authorized bank; research and all trial evidence in cache"]
    C -- "Evaluate" --> V["Read-only source export; anonymous trials; grading"]
    V --> VO["Cache: bundle, raw runs, status counts and report over all assigned tasks"]
```

[Task intake](execution/task-settings.md#startup-intake) determines which inputs are needed for each entry point. New source discovery uses arXiv and requires a date interval and principal-paper count before either work-goal mode starts. Missing input pauses only dependent work. Find alone produces an opportunity report. Evaluation does not acquire editing authority or an authoring goal. Standalone elaboration follows its same-bank write scope and includes target-model trials only when they are authorized.

## Research and testing loop

```mermaid
flowchart TD
    I["Source scope fixed: supplied pool, or arXiv dates and paper count; paths resolved"] --> W["Separate work goal: continuous H hours or accepted T4 count K when applicable"]
    W --> G["Record the authorized fixed Goal and source bounds; track its actual boundary"]
    G --> R["Review governing principles; AI chooses research and supplementary reading; selected Find papers are read in full"]
    R --> C["Construct a concise self-contained calculation and complete its reference"]
    C --> M{"Statement well-posed and reference verified?"}
    M -- "Not yet" --> D{"Review principles; AI research judgment"}
    M -- "Yes" --> N{"Review principles; AI chooses the useful next action"}
    N -- "Research or reconstruct" --> D
    N -- "Authorized untested delivery" --> P["Label working preview; no formal tier or accepted T4 count"]
    N -- "Formal test" --> SR["Freeze baseline; automatically start independent statement reader"]
    SR --> SE{"Reader and independent meaning-preservation checks pass?"}
    SE -- "Editorial defects" --> ER["Minimal corrections; verify unchanged mathematics; fresh reader"]
    ER --> SE
    SE -- "Uncertain meaning or mathematical change" --> D
    SE -- "Yes" --> VG["Validate final prompt, answer interface, reference and baseline hashes"]
    VG --> T["Fresh exact-version anonymous trial: agreed model and token budget"]
    T --> L["Preserve raw outputs, hashes, actual use and execution state; grade and classify"]
    L --> D
    D -- "Strengthen or reconstruct" --> C
    D -- "Abandon core or change paper within scope" --> R
    D -- "Select a qualified tested version" --> S["Stage selected version; count distinct accepted T4 questions only"]
    S --> Z{"Agreed research stopping condition met?"}
    Z -- "No" --> R
    Z -- "Yes" --> O["Authorized bank write; matching solutions; compile and inspect; deliver actual results"]
    G -. "H boundary applies throughout the loop" .-> H["Stop new research/trials; preserve interrupted work as pending"]
    H --> O
    P --> O
    O --> END["Report actual goal completion after delivery checks"]
```

The benchmark target is defined in the [main skill](../SKILL.md): the agreed `gpt-5.6-sol / max` trial fails to complete the task correctly within 1,000,000 cumulative input plus output tokens. [Formal testing](evaluation/model-testing.md#screen-authoring-candidates) defines the local groups and accounting limits. A whole-task duration interruption or execution error is pending; it is not evidence of token exhaustion or mathematical failure.

Before each research judgment, revisit the [governing principles](../SKILL.md). The AI chooses supplementary reading, synthesis, investigation, reconstruction, abandonment, paper replacement, and final selection under [research decisions](research/problem-refinement.md#post-trial-research-decisions). Selected Find papers must be downloaded and read in full under [principal-paper reading](research/paper-search.md#inspect-the-principal-mathematics). Trial classification never automatically admits a question. Useful mathematical work can continue after a T4 result; a cheap correct result can motivate reconstruction or replacement. A changed mathematical version needs a verified matching reference and a fresh formal test before final selection. Preserve completed trials rather than resampling an unchanged question until a failure appears.

The [continuous-goal guide](execution/continuous-goals.md) controls the whole task. H measures actual continuous elapsed work and can yield zero selected T4 questions. For K, reaching the selected-question quota ends research; overall completion follows only after delivery checks. Distinct questions may share a mathematical core, but equivalent rephrasings, parameter substitutions, versions, and retries do not multiply the count. A branch being abandoned does not complete either goal. The Goal interface does not natively enforce H or K; track them explicitly. Bounded untested previews and bounded standalone elaboration retain their agreed stopping conditions without an extra goal questionnaire; they cannot satisfy a T4 count without formal screening.

## Inputs and retained artifacts

| Stage | Input | Output and destination |
| --- | --- | --- |
| Intake | Actual user request, established choices, source/task scope, paths, applicable goal and test settings | Resolved choices and execution state in the task cache; focused questions for necessary gaps |
| Research | Supplied or discovered literature, existing questions, calculations and solve evidence | Source exposure, checked connections, meaningful versions, verified references and unresolved gaps in the cache |
| Statement review | Anonymous final prompt and answer interface for the reader; frozen original and matching private reference for a separate semantic checker | Independent findings and accepted exact-version bindings in the cache under [statement review](research/statement-review.md); no private review material goes to the solver |
| Formal solver | Only the exact anonymous statement and answer interface, with the agreed tools and limits | Raw submission, events, actual accounting and execution metadata in the cache; private solutions and research notes are not solver inputs |
| Grading and selection | Frozen task/reference/submission bindings, actual mathematical review and trial evidence | Preserved classification and pending states in the cache; AI selection of final versions, with distinct-question counting where applicable |
| Delivery | Selected versions, matching solutions and sources, authorized write scope | Final bank or explicitly labelled preview; all trial records, unselected versions, backups and reports remain in the cache |

Use the [path and write contract](execution/task-settings.md#paths-and-write-scope) and [manuscript checks](research/problem-design.md#present-and-write). A goal does not authorize replacing old questions. Evaluation-only output stays in the cache and retains the original assigned-task denominator.
