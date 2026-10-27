# Paper Math Bench

A Codex skill for turning mathematical research into hard, concise calculation problems with verified reference solutions and reproducible model evaluation.

**Contents**

- [What the skill does](#what-the-skill-does)
- [Install and invoke](#install-and-invoke)
- [Usage](#usage)
- [How a problem reaches final testing](#how-a-problem-reaches-final-testing)
- [Example](#example)
- [Evaluation defaults and limits](#evaluation-defaults-and-limits)
- [Package guide](#package-guide)

## What the skill does

| Entry point | Purpose | Output |
| --- | --- | --- |
| **Find** | Read papers and identify substantive calculation opportunities. | Checked source notes, candidate targets, dependencies, and remaining gaps. |
| **Author** | Construct difficult calculations from supplied or discovered literature. | Concise English problems, complete verified solutions, citations, and screening records. |
| **Elaborate** | Strengthen selected problems in an existing local TeX bank. | Revised problems and matching reference solutions within the authorized editing scope. |
| **Evaluate** | Test a local bank with fresh independent solver processes. | Version-bound submissions, grading, token accounting, and reports; the source bank stays read-only. |

The skill favors mathematical depth over long statements or obscure notation. Problem-specific definitions and answer-affecting conventions must be clear. Standard concepts are used by name, and formulas carry the statement wherever they improve clarity.

This English edition asks every intake and clarification question, including suggested options, in **English**, regardless of the conversation language. Original user replies are preserved verbatim in research and configuration evidence.

## Install and invoke

Clone this repository and copy its skill folder into the working project's `.agents/skills` directory. Replace `/path/to/project` with your project directory:

```sh
git clone https://github.com/BrookWW/SkillofCreatingCalculationProblems.git
mkdir -p /path/to/project/.agents/skills
cp -R SkillofCreatingCalculationProblems/paper-math-bench \
  /path/to/project/.agents/skills/paper-math-bench
```

Keep the complete `paper-math-bench` folder together: its scripts, references, and templates are part of the skill. Codex discovers project skills in `.agents/skills`; see the [official skills documentation](https://developers.openai.com/codex/skills#where-to-save-skills).

In Codex CLI or the IDE extension, invoke it in a prompt with:

```text
$paper-math-bench
```

Use a compatible Codex environment with Python 3.10 or later. Authoring also needs access to the selected literature and a TeX toolchain for compiling the final bank. Real model evaluation requires a Codex CLI that supports the exact requested model and settings.

## Usage

Give the skill the intended task and the paths it should use. It asks in English for required information that is still missing.

**Discover papers and author problems:**

```text
Use $paper-math-bench.

Find 10 arXiv papers first submitted between 2026-01-01 and 2026-04-01
in math.FA, math.AP, math.CA, math.DG, or math.CO.
Work continuously for 6 hours on research, construction, verification, and screening.
Append selected problems and complete solutions to /absolute/path/to/bank/main.tex.
Keep downloads, calculations, backups, and evaluation records in /absolute/path/to/cache.
Use the default gpt-5.6-sol / max screening configuration.
```

Paper discovery requires a date interval, principal-paper count, and subject scope. Full authoring has a separate work goal: a continuous duration or a requested number of accepted local T4 problems. A duration does not guarantee that any candidate will qualify.

**Evaluate an existing bank:**

```text
Use $paper-math-bench to evaluate all problems in /absolute/path/to/bank/main.tex.
Keep the source unchanged and put the evaluation bundle, runs, and reports
under /absolute/path/to/cache. Use the default model and budget.
```

To refine existing problems, identify the bank and selected labels, specify whether to append or replace them, and state whether formal model trials are in scope. The [task settings](paper-math-bench/references/execution/task-settings.md) describe the inputs for each entry point.

## How a problem reaches final testing

1. Research the mathematics and complete a verified reference solution.
2. Freeze the original statement, answer requirements, reference, and rubric.
3. Automatically start a fresh statement-reader agent with only the anonymous statement and public answer interface.
4. Make necessary editorial corrections, then use a separate semantic checker to compare the original and final tasks. Revisions must preserve objects, domains, quantifiers, assumptions, conventions, calculation targets, and answer requirements, without adding solution hints.
5. Recheck the final anonymous statement and validate its version-bound review record before the formal solver starts.
6. Preserve the raw trial and assess it against the verified reference. Grading and classification recheck the frozen review evidence.

A revision with uncertain or changed mathematical meaning cannot pass as an editorial clarification. Hashes bind the reviewed and tested versions; mathematical equivalence remains an independent mathematical judgment. See [statement review](paper-math-bench/references/research/statement-review.md) and [role prompts](paper-math-bench/references/execution/agent-prompts.md).

## Example

**An extremal weighted partition sum.**

For $x\ge 0$, define

```math
w_0(x)=w_1(x)=1,\qquad
w_j(x)=\exp\!\left(\frac{9}{2}\frac{(j-2)x}{j+x}\right)
\quad(j\ge 2).
```

For every positive integer $n$, set

```math
\begin{aligned}
C_n(x)
&=\frac{1}{n!\,w_n(x)}
\sum_{\substack{m_1,\ldots,m_n\in\mathbb Z_{\ge 0}\\
                 \sum_{j=1}^{n}j m_j=n}}
\frac{(k!)^2w_k(x)}{\prod_{j=1}^{n}m_j!}
\prod_{j=2}^{n}\left(\frac{j!\,w_j(x)}{200}\right)^{m_j},
\\
k&=\sum_{j=1}^{n}m_j.
\end{aligned}
```

Determine the constants $\lambda>1$, $\alpha\in\mathbb R$, and $K>0$ for which

```math
\sup_{x\ge 0}C_n(x)\sim K n^\alpha\lambda^n
\qquad(n\to\infty).
```

You may assume that constants of this form exist.

<details>
<summary><strong>Full reference solution</strong></summary>

**Answer.** The constants are

```math
\boxed{
\begin{gathered}
\lambda=\frac{e^{3/2}}{4},\qquad \alpha=9,\\
K=\frac{\sqrt{3}\,\pi^3}{2^{18}200^3}
\exp\left(-15+\frac{e^{-2}}{100}\right).
\end{gathered}
}
```

**Entropy optimization.** Write $\beta=9/2$, $A=200$, and $L=\log\lambda$. For a probability vector $(p_i)$ and $c>0$, define

```math
E_c(p)=\sum_i p_i\log p_i+\beta\left(\sum_i\frac{p_i c}{p_i+c}-\frac{c}{1+c}\right).
```

The derivative of $g_c(p)=\log p+\beta c/(p+c)$ has the sign of $(p/c-1/2)(p/c-2)$. Its maximum on $(0,1]$ is therefore attained at $p=c/2$, if admissible, or at $p=1$. Consequently,

```math
E_c(p)\leq
\begin{cases}
\max\left\{0,\log(c/2)+3-\dfrac{9c}{2(1+c)}\right\},&0<c\leq2,\\
0,&c>2.
\end{cases}
```

The nonzero candidate has derivative $(c-1/2)(c-2)/[c(1+c)^2]$ and a unique global maximum $L=3/2-\log4$ at $c=1/2$. Equality requires every positive $p_i$ to equal $1/4$. Thus the globally optimal mass distribution has four equal components.

**Reduction of the partition sum.** We justify applying this optimization to the entire partition sum. Represent the nonlinear blocks by an ordered list $j_1,\ldots,j_r\geq2$ and divide by $r!$, where $r=\sum_{j\geq2}m_j$. For $n\geq3$, set

```math
N=n-2,\qquad a=m_1+2r-2,\qquad b_i=j_i-2.
```

Then

```math
a+\sum_i b_i=N,\qquad m_1=a-2r+2\geq0,\qquad k=a-r+2.
```

The all-singleton term is exactly one. For every other term, log-convexity of factorials and monotonicity of the weights give

```math
\frac{(k!)^2}{m_1!}\leq(a+2)!,\qquad w_k(x)\leq w_{a+2}(x).
```

Put

```math
\begin{aligned}
c&=\frac{x+2}{N},\qquad
\beta'=\frac{\beta x}{x+2},\qquad
\ell=L+\frac{\beta'c}{1+c},\\
U_N(b)&=(b+2)!\left(\frac{e}{N}\right)^b e^{-\ell b}w_{b+2}(x).
\end{aligned}
```

The identity $\log w_{b+2}(x)=\beta'N(b/N)c/(b/N+c)$ is exact, and

```math
U_N(0)=2,\qquad U_N(N)\sim\sqrt{2\pi}\,N^{5/2}e^{-LN}.
```

Each ordered summand is bounded by

```math
\frac{U_N(a)\prod_i U_N(b_i)}{r!A^rU_N(N)},\qquad a\geq2r-2.
```

The entropy bound remains valid for $0\leq\beta'\leq\beta$. Uniform Stirling bounds show, with $p=b/N>0$, that

```math
U_N(b)\leq C(b+1)^{5/2}\exp\left\{Np\left[\log p+\frac{\beta'c}{p+c}-\ell\right]\right\}.
```

**Tail estimates.** Here are tail estimates that distinguish the relevant scales. Fix $\delta\in(0,1/20)$ and one $t>0$, and choose $\epsilon>0$ sufficiently small depending on $t$. Call an index a peak index when it lies in $[(1/4-\delta)N,(1/4+\delta)N]$, and a low index when it lies in $[0,\epsilon N]$; all other indices are middle indices. Uniformly in $x$, for every fixed integer $d\geq1$,

```math
\begin{aligned}
\sum_{b=d}^{\lfloor\epsilon N\rfloor}e^{tb}U_N(b)&=O(N^{-d}),\\
\sum_{b=0}^{\lfloor\epsilon N\rfloor}e^{tb}U_N(b)&=2+O(N^{-1}).
\end{aligned}
```

Indeed, their summands are bounded by $C(b+1)^{5/2}(e^{\beta-L+t}b/N)^b$. Every middle index has an exponentially small factor, by the strict entropy bound. There are only a bounded number of middle and peak indices, while $1/r!$ sums all low nonlinear indices into a bounded exponential series. Thus terms with a middle index are negligible. There can be at most four peak indices. With at most three peaks, low indices must carry a fixed positive fraction of $N$; the tilted low-index bound makes their contribution exponentially small.

Near the unique maximum, the entropy gap is quadratic. In particular, the convolution of four peak factors at a fixed total index is $O(N^{23/2})$, and division by $U_N(N)$ gives $O(N^9e^{LN})$. If $a$ is low and the four peaks are nonlinear blocks, then $r\geq4$ and $a\geq6$; the low-index bound supplies an additional $O(N^{-6})$. This case is only $O(N^3e^{LN})$. The leading terms therefore have $a$ at a peak and three nonlinear peak blocks. Every positive low nonlinear index costs $O(N^{-1})$. The only remaining low nonlinear indices are zero, corresponding to blocks of size two. Their number has the summable majorant $(2/A)^d/d!$. This proves that it suffices to calculate each fixed $d=m_2$ and then sum over $d$.

**Contribution of the large blocks.** Let the three large block sizes be $j_1,j_2,j_3$, and write

```math
h=n-j_1-j_2-j_3=m_1+2d,\qquad k=h-d+3.
```

The ordered-triple contribution has the factorial factor

```math
\begin{gathered}
\frac{h!j_1!j_2!j_3!}{n!}
\frac{((h-d+3)!)^2}{(h-2d)!h!}
\frac{(2/A)^d}{3!A^3d!},\\
\frac{((h-d+3)!)^2}{(h-2d)!h!}\sim h^6.
\end{gathered}
```

Set $p_0=h/n$, $p_i=j_i/n$ for $i=1,2,3$, and now $c=x/n$. The multinomial factor is

```math
\frac{h!j_1!j_2!j_3!}{n!}\sim(2\pi n)^{3/2}\left(\prod_{i=0}^3p_i\right)^{1/2}\exp\left(n\sum_{i=0}^3p_i\log p_i\right).
```

After extracting the leading weight exponential, the bounded factor from $w_h\prod_i w_{j_i}/w_n$ is

```math
\exp\left[-2\beta c\left(\sum_{i=0}^3\frac{1}{p_i+c}-\frac{1}{1+c}\right)\right].
```

At $p_i=1/4$, $c=1/2$, this equals $e^{-21}$, and $w_{h-d+3}/w_h\longrightarrow e^{6-2d}$. The net bounded weight factor is consequently $e^{-15-2d}$.

**Gaussian evaluation and the supremum.** In the free coordinates $(p_1,p_2,p_3)$, the Hessian of $E_c$ is

```math
H=-\frac{4}{3}(I_3+\mathbf{1}\mathbf{1}^T),\qquad \det(-H)=\frac{256}{27}.
```

The mixed derivatives with $c$ vanish, and $\partial_c^2 E_c=-8/3$. Hence, for $x=n/2+z\sqrt{n}$ with bounded $z$, the Gaussian lattice sum contributes

```math
n^{3/2}\frac{(2\pi)^{3/2}}{\sqrt{256/27}}e^{-4z^2/3}.
```

Combining this with $h^6\sim(n/4)^6$, $\prod_i p_i^{1/2}=1/16$, and the multinomial Stirling factor gives

```math
C_n(n/2+z\sqrt{n})\sim\frac{\sqrt{3}\,\pi^3}{2^{18}A^3}e^{-15}n^9e^{Ln}e^{-4z^2/3}\sum_{d=0}^{\infty}\frac{((2/A)e^{-2})^d}{d!}.
```

The series is $\exp(2e^{-2}/A)$. The same quadratic gap gives uniform Gaussian suppression when $|x-n/2|/\sqrt{n}\longrightarrow\infty$, and uniform exponential suppression outside a fixed neighborhood of $x/n=1/2$. Thus taking the supremum in $x$ selects $z=0$ and yields the stated constant.

</details>

## Evaluation defaults and limits

| Setting | Default |
| --- | --- |
| Screening model | `gpt-5.6-sol` |
| Reasoning effort | `max` |
| Formal attempts | One fresh independent attempt per final verified version |
| Requested per-attempt budget | 1,000,000 cumulative input plus output tokens |
| Budget reminder | At 660,000 tokens; unfinished work may continue within the requested total |
| Additional wall timeout | None |

The authoring and review agents inherit the current authoring configuration; selecting a screening model does not change them. Explicit user overrides take precedence. Unsupported runtime settings stop without silently substituting another model.

The CLI runner provides instruction-only isolation. It requests no source lookup or web use, but does not enforce a filesystem read allowlist or prove network isolation. Reported token accounting and requested native budget units may differ. T2/T3/T4 are local operational classifications, separate from official human-difficulty certification. Detailed rules are in [model testing and grading](paper-math-bench/references/evaluation/model-testing.md).

## Package guide

- [Skill entry point](paper-math-bench/SKILL.md)
- [Workflow and data flow](paper-math-bench/references/workflow-map.md)
- [Problem design](paper-math-bench/references/research/problem-design.md) and [refinement](paper-math-bench/references/research/problem-refinement.md)
- [Statement style](paper-math-bench/references/research/statement-style.md) and [independent statement review](paper-math-bench/references/research/statement-review.md)
- [Task intake and English question templates](paper-math-bench/references/execution/task-settings.md)
- [Development and validation](DEVELOPMENT.md)

The repository contains the reusable English skill, blank manuscript templates, synthetic implementation tests, and the single example and its full reference solution above. Other research problem banks, source PDFs, private solutions, model runs, and task caches stay outside the distribution.
