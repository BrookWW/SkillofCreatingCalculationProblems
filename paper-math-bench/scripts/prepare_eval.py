#!/usr/bin/env python3
"""Export anonymous statements and private, unreviewed reference solutions.

This conservative parser supports amsart with T2/T3/T4/Solutions sections or
the legacy Problems/Solutions layout. It never executes TeX/code or reads includes.
"""

# Contents (search the numbered section headings below):
# 1. TeX policies and solver instructions
# 2. TeX parsing and statement anonymization
# 3. Bundle creation and publication
# 4. Command-line interface
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


# 1. TeX policies and solver instructions

COMMAND = re.compile(r"\\([A-Za-z@]+|[^A-Za-z@])")
STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._-]*\Z")
SAFE_COMMANDS = set("""
alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa
lambda mu nu xi pi varpi rho varrho sigma varsigma tau upsilon phi varphi chi psi
omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega
frac dfrac tfrac binom dbinom tbinom sqrt left right middle big Big bigg Bigg
bigl bigr Bigl Bigr biggl biggr Biggl Biggr mathbb mathbf mathcal mathfrak
mathrm mathit mathsf mathtt mathrm boldsymbol operatorname text textrm textit
textbf emph overline underline widehat widetilde hat bar tilde vec dot ddot
sum prod coprod int iint iiint oint lim limsup liminf inf sup min max log ln exp
sin cos tan cot sec csc sinh cosh tanh arcsin arccos arctan det gcd dim ker
in notin ni subset subseteq supset supseteq cap cup bigcap bigcup setminus
emptyset varnothing forall exists neg land lor implies iff to mapsto
rightarrow longrightarrow leftarrow leftrightarrow Rightarrow Leftarrow Leftrightarrow
uparrow downarrow ne neq le leq ge geq ll gg sim simeq approx asymp equiv
cong propto parallel perp mid nmid cdot times div pm mp circ bullet star
infty partial nabla ell hbar Re Im aleph lfloor rfloor lceil rceil langle
rangle lvert rvert lVert rVert vert Vert backslash ldots cdots vdots ddots
quad qquad thinspace medspace thickspace enspace hspace vphantom phantom
displaystyle textstyle scriptstyle scriptscriptstyle substack overset underset
underbrace overbrace stackrel boxed pmod bmod mod item begin end
""".split())
SAFE_SYMBOLS = set("\\{}[]()|!,;: %_$#&>/")
SAFE_ENVIRONMENTS = set("""
enumerate itemize aligned alignedat gathered split cases matrix pmatrix bmatrix
Bmatrix vmatrix Vmatrix array equation equation* align align* gather gather*
multline multline* displaymath math
""".split())
DANGEROUS = set("""
input include includeonly openin openout closein closeout read readline write
immediate special directlua latelua luaexec pdfobj pdfxform pdfrefobj pdffiledump
pdfextension pdfliteral shipout endinput scantokens csname endcsname catcode
def gdef edef xdef let futurelet expandafter noexpand unexpanded protected
newenvironment renewenvironment renewcommand providecommand newif newread
newwrite newtoks toks everyjob everypar everymath everydisplay everyeof
AtBeginDocument AtEndDocument AddToHook makeatletter makeatother ExplSyntaxOn
ExplSyntaxOff verb verbatim lstinputlisting includegraphics graphicspath
IfFileExists InputIfFileExists filecontents RequirePackage jobname meaning
string detokenize scantokens loop repeat if ifx ifnum ifdim ifdefined ifcsname
else fi begingroup endgroup global afterassignment aftergroup
""".split())
PACKAGES = set("amsmath amssymb amsthm mathtools hyperref geometry needspace bm mathrsfs dsfont bbm fvextra".split())
RESERVED = set("documentclass usepackage title date author address email thanks keywords subjclass newtheorem theoremstyle maketitle label ref eqref cite section subsection bibliography bibliographystyle DeclareMathOperator newcommand".split())
SECTION_LAYOUTS = (("Problems", "Solutions"), ("T2", "T3", "T4", "Solutions"))
PROBLEM_SECTIONS = {"Problems", "T2", "T3", "T4"}
PRIVATE_VERBATIM = "PaperMathBenchPrivateVerbatim"
RESERVED.add(PRIVATE_VERBATIM)
INSTRUCTIONS = (
    "Solve only the supplied mathematical problem. Local Python computation is "
    "allowed. Do not use the web, network, source lookup, delegation, memories, "
    "or authoring skills. Do not read manuscripts, bibliography, source papers, "
    "reference answers, other attempts, or unrelated files. No grading feedback "
    "is available during this attempt. These are instruction-only restrictions, "
    "not a claim that access is technically blocked. Give the requested answer "
    "and a concise calculation. Include a proof only when the problem explicitly "
    "requests one. Return only a "
    'JSON object with exactly these fields: "answer" (string), "derivation" '
    '(string), and "complete" (boolean). Set "complete" to false if you cannot '
    "fully solve the problem.\n\n"
)


# 2. TeX parsing and statement anonymization

def _group(text: str, pos: int, opening: str = "{") -> tuple[str, int]:
    pos = _space(text, pos)
    if pos >= len(text) or text[pos] != opening:
        raise ValueError(f"Expected {opening!r} near character {pos}")
    start, braces, brackets = pos + 1, 0, 0
    pos += 1
    while pos < len(text):
        char = text[pos]
        if char == "\\":
            match = COMMAND.match(text, pos)
            if not match:
                raise ValueError("Incomplete TeX command")
            pos = match.end()
            continue
        if char == "{":
            braces += 1
        elif char == "}":
            if opening == "{" and braces == 0:
                return text[start:pos], pos + 1
            braces -= 1
            if braces < 0:
                raise ValueError("Unbalanced braces in optional argument")
        elif opening == "[" and braces == 0:
            if char == "[":
                brackets += 1
            elif char == "]":
                if brackets == 0:
                    return text[start:pos], pos + 1
                brackets -= 1
        pos += 1
    raise ValueError("Unterminated TeX argument")


def _space(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def _uncomment(text: str, verbatim: list[str] | None = None) -> str:
    """Remove TeX comments while protecting private literal blocks for parsing."""
    parts, pos = [], 0
    while pos < len(text):
        if text[pos] == "\\":
            match = COMMAND.match(text, pos)
            if not match:
                raise ValueError("Incomplete TeX command")
            if match[1] == PRIVATE_VERBATIM:
                raise ValueError("Reserved private-data marker in source")
            if verbatim is not None and match[1] == "begin":
                opening = re.match(r"[ \t]*\{Verbatim\}", text[match.end():])
                if opening:
                    end = match.end() + opening.end()
                    line_start = text.rfind("\n", 0, pos) + 1
                    if text[line_start:pos].strip():
                        raise ValueError("Verbatim must begin on its own line")
                    while end < len(text) and text[end] in " \t":
                        end += 1
                    if end < len(text) and text[end] == "[":
                        _, end = _group(text, end, "[")
                    line_end = text.find("\n", end)
                    if line_end < 0 or text[end:line_end].strip():
                        raise ValueError("Invalid Verbatim opening line")
                    header = text[pos:line_end]
                    if ("^^" in header or any(ord(c) < 32 and c not in "\t\r" for c in header)
                            or any(m[1] in DANGEROUS for m in COMMAND.finditer(header))):
                        raise ValueError("Unsafe Verbatim options")
                    closing = re.search(r"(?m)^[ \t]*\\end\{Verbatim\}[ \t]*(?:\r?\n|$)", text[line_end + 1:])
                    if closing is None:
                        raise ValueError("Unterminated Verbatim block")
                    end = line_end + 1 + closing.end()
                    verbatim.append(text[pos:end])
                    parts.append(f"\\{PRIVATE_VERBATIM}{{{len(verbatim) - 1}}}")
                    pos = end
                    continue
            parts.append(match.group())
            pos = match.end()
        elif text[pos] == "%":
            end = text.find("\n", pos)
            pos = len(text) if end < 0 else end + 1
        else:
            parts.append(text[pos])
            pos += 1
    return "".join(parts)


def _macro(text: str, command: str, pos: int) -> tuple[str, str, str, int]:
    pos = _space(text, pos)
    star = pos < len(text) and text[pos] == "*"
    pos += int(star)
    pos = _space(text, pos)
    if pos < len(text) and text[pos] == "{":
        name, pos = _group(text, pos)
    else:
        match = COMMAND.match(text, pos)
        if not match:
            raise ValueError("Expected a custom macro name")
        name, pos = match.group(), match.end()
    if not re.fullmatch(r"\\[A-Za-z]+", name):
        raise ValueError(f"Unsupported macro name: {name!r}")
    name = name[1:]
    if name in SAFE_COMMANDS | DANGEROUS | RESERVED:
        raise ValueError(f"Custom macro may not redefine \\{name}")
    argc, pos = "", _space(text, pos)
    if pos < len(text) and text[pos] == "[":
        if command != "newcommand":
            raise ValueError("Unsupported math operator argument")
        number, pos = _group(text, pos, "[")
        if number not in "0123456789" or len(number) != 1:
            raise ValueError("Macro arity must be one digit")
        argc = f"[{number}]"
    body, pos = _group(text, pos)
    if re.search(r"#(?![1-9])", body) or any(int(n) > int(argc[1] if argc else 0) for n in re.findall(r"#([1-9])", body)):
        raise ValueError(f"Invalid parameter in \\{name}")
    definition = f"\\{command}{'*' if star else ''}{{\\{name}}}{argc}{{{body}}}"
    return name, body, definition, pos


def _parse(text: str) -> tuple[list[str], dict[str, str], dict[str, tuple[str, str]]]:
    verbatim, private_blocks = [], set()
    text = _uncomment(text, verbatim)
    if "^^" in text or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise ValueError("Unsupported TeX character encoding")
    for match in COMMAND.finditer(text):
        if match[1] in DANGEROUS:
            raise ValueError(f"Unsupported or dangerous TeX command: \\{match[1]}")
    problems, headers, macros, stack = [], [], {}, []
    pos = depth = 0
    section = None
    seen_sections = []
    document_seen = class_seen = False
    problem_start = bibliography_start = document_end = None
    while pos < len(text):
        char = text[pos]
        if char != "\\":
            depth += (char == "{") - (char == "}")
            if depth < 0:
                raise ValueError("Unbalanced TeX braces")
            pos += 1
            continue
        match = COMMAND.match(text, pos)
        if not match:
            raise ValueError("Incomplete TeX command")
        command, start, pos = match[1], pos, match.end()
        if command == PRIVATE_VERBATIM:
            if (section != "Solutions" or not headers or bibliography_start is not None
                    or stack != [("document", 0)] or depth):
                raise ValueError("Verbatim is allowed only in a private solution")
            index, pos = _group(text, pos)
            if not index.isdecimal() or int(index) >= len(verbatim) or int(index) in private_blocks:
                raise ValueError("Invalid private-data marker")
            private_blocks.add(int(index))
        elif command in {"newcommand", "DeclareMathOperator"}:
            if document_seen or depth:
                raise ValueError("Custom macro definitions must be in the preamble")
            name, body, definition, pos = _macro(text, command, pos)
            if name in macros:
                raise ValueError(f"Duplicate custom macro: \\{name}")
            macros[name] = (body, definition)
        elif command in {"documentclass", "usepackage"}:
            if document_seen or depth:
                raise ValueError("Document directives must be in the preamble")
            pos = _space(text, pos)
            if pos < len(text) and text[pos] == "[":
                _, pos = _group(text, pos, "[")
            value, pos = _group(text, pos)
            if command == "documentclass":
                if class_seen or value != "amsart":
                    raise ValueError("Exactly one amsart document class is required")
                class_seen = True
            elif any(p.strip() not in PACKAGES for p in value.split(",")):
                raise ValueError(f"Unsupported package: {value}")
        elif not document_seen and command in {"title", "date", "author", "address", "email", "thanks", "keywords", "subjclass"}:
            pos = _space(text, pos)
            if pos < len(text) and text[pos] == "[":
                _, pos = _group(text, pos, "[")
            _, pos = _group(text, pos)
        elif command in {"begin", "end"}:
            env, pos = _group(text, pos)
            if not re.fullmatch(r"[A-Za-z]+\*?", env):
                raise ValueError("Unsupported environment name")
            if env == "Verbatim":
                raise ValueError("Unsupported Verbatim delimiters")
            if command == "begin":
                if env == "document":
                    if document_seen or stack or depth:
                        raise ValueError("Invalid document environment")
                    document_seen = True
                elif not stack:
                    raise ValueError("Environment outside document")
                if env == "problem":
                    if section not in PROBLEM_SECTIONS or stack != [("document", 0)] or depth:
                        raise ValueError("Problem must be directly in a problem section")
                    pos = _space(text, pos)
                    if pos < len(text) and text[pos] == "[":
                        _, pos = _group(text, pos, "[")
                    problem_start = pos
                stack.append((env, depth))
            else:
                if not stack or stack.pop() != (env, depth):
                    raise ValueError(f"Mismatched environment: {env}")
                if env == "problem":
                    problems.append(text[problem_start:start])
                elif env == "document":
                    document_end = start
        elif command in {"section", "subsection"}:
            if stack != [("document", 0)] or depth:
                raise ValueError("Section headers must be at document level")
            pos = _space(text, pos)
            star = pos < len(text) and text[pos] == "*"
            pos += int(star)
            title, pos = _group(text, pos)
            if command == "section":
                seen_sections.append(title)
                if not any(tuple(seen_sections) == layout[:len(seen_sections)] for layout in SECTION_LAYOUTS):
                    raise ValueError("Expected T2, T3, T4, Solutions or legacy Problems, Solutions")
                section = title
            else:
                header = re.fullmatch(r"Solution\s+to\s+Problem\s*~?\s*\\ref\s*\{([A-Za-z0-9:._-]+)\}", title)
                if section != "Solutions" or not star or not header or bibliography_start is not None:
                    raise ValueError("Unsupported solution header")
                headers.append((header[1], start, pos))
        elif command in {"bibliographystyle", "bibliography"}:
            if section != "Solutions" or stack != [("document", 0)] or depth:
                raise ValueError("Bibliography must follow the solutions")
            bibliography_start = start if bibliography_start is None else bibliography_start
            _, pos = _group(text, pos)
    if (depth or stack or not class_seen or document_end is None
            or tuple(seen_sections) not in SECTION_LAYOUTS):
        raise ValueError("Incomplete or unbalanced amsart benchmark")
    if len(private_blocks) != len(verbatim):
        raise ValueError("Verbatim is allowed only in a private solution")
    if not problems or not headers:
        raise ValueError("Problems and solutions are required")
    solutions = {}
    for index, (label, _, start) in enumerate(headers):
        end = headers[index + 1][1] if index + 1 < len(headers) else (bibliography_start or document_end)
        solution = text[start:end].strip() + "\n"
        if label in solutions or not solution.strip():
            raise ValueError(f"Duplicate or empty solution: {label}")
        solution = re.sub(r"\\" + PRIVATE_VERBATIM + r"\{(\d+)\}",
                          lambda match: verbatim[int(match[1])], solution)
        solutions[label] = solution
    return problems, solutions, macros


def _statement(body: str, macros: dict[str, tuple[str, str]]) -> tuple[str, str]:
    labels, pieces, used, visiting = [], [], set(), set()

    def validate(value: str) -> None:
        for match in COMMAND.finditer(value):
            name = match[1]
            if name in macros:
                if name in visiting:
                    raise ValueError(f"Recursive custom macro: \\{name}")
                if name not in used:
                    visiting.add(name)
                    validate(macros[name][0])
                    visiting.remove(name)
                    used.add(name)
            elif name in {"begin", "end"}:
                env, _ = _group(value, match.end())
                if env not in SAFE_ENVIRONMENTS:
                    raise ValueError(f"Unsupported statement environment: {env}")
            elif name not in SAFE_COMMANDS and name not in SAFE_SYMBOLS:
                raise ValueError(f"Unsupported statement command: \\{name}")

    previous = 0
    for match in COMMAND.finditer(body):
        if match[1] == "label":
            label, end = _group(body, match.end())
            labels.append(label)
            pieces.append(body[previous:match.start()])
            previous = end
    pieces.append(body[previous:])
    if len(labels) != 1 or not STABLE_ID.fullmatch(labels[0]):
        raise ValueError("Each problem requires exactly one valid stable label")
    statement = "".join(pieces).strip()
    if not statement:
        raise ValueError(f"Empty statement: {labels[0]}")
    validate(statement)
    definitions = "\n".join(definition for name, (_, definition) in macros.items() if name in used)
    if definitions:
        statement = "\\(\n" + definitions + "\n\\)\n\n" + statement
    return labels[0], INSTRUCTIONS + statement + "\n"


# 3. Bundle creation and publication

def _hash(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _rename_exclusive(staging: Path, target: Path) -> None:
    """Atomically publish without replacing an existing directory, even in a race."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename = library.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        result = rename(os.fsencode(staging), os.fsencode(target), 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        rename = library.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        result = rename(-100, os.fsencode(staging), -100, os.fsencode(target), 1)  # RENAME_NOREPLACE
    elif os.name == "nt":
        os.rename(staging, target)
        return
    else:
        raise OSError(errno.ENOTSUP, "Atomic exclusive directory rename is unavailable")
    if result:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(target))


def _remove_tree(path: Path) -> None:
    """Remove owned staging files, tolerating already-removed metadata sidecars."""
    def onerror(_function, _name, error_info):
        error = error_info[1]
        if not isinstance(error, FileNotFoundError):
            raise error
    shutil.rmtree(path, onerror=onerror)


def _publish_copy(staging: Path, target: Path) -> None:
    """Reserve a new directory and publish the manifest after all payload files."""
    target.mkdir(mode=0o700)  # Exclusive reservation; an existing target is untouched.
    try:
        manifest = staging / "manifest.json"
        manifest_bytes = manifest.read_bytes() if manifest.is_file() else None
        paths = sorted(staging.rglob("*"))
        for source in paths:
            relative = source.relative_to(staging)
            if any(part.startswith("._") for part in relative.parts):
                continue
            destination = target / relative
            if source.is_dir():
                destination.mkdir()
            elif relative.as_posix() != "manifest.json":
                with source.open("rb") as incoming, destination.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
        _remove_tree(staging)
        if manifest_bytes is not None:
            with (target / "manifest.json").open("xb") as outgoing:
                outgoing.write(manifest_bytes)
    except BaseException:
        _remove_tree(target)
        raise


def _publish(staging: Path, target: Path) -> None:
    """Use exclusive rename, or manifest-last exclusive copy when unsupported."""
    try:
        _rename_exclusive(staging, target)
    except OSError as error:
        unsupported = {errno.ENOTSUP, errno.EOPNOTSUPP, errno.ENOSYS, errno.EINVAL}
        if error.errno not in unsupported:
            raise
        _publish_copy(staging, target)


def prepare(tex: str | Path, destination: str | Path, ids: list[str] | None = None) -> Path:
    """Create a new bundle requiring rubric review before model execution."""
    source = Path(tex).resolve(strict=True)
    raw = source.read_bytes()
    problems, solutions, macros = _parse(raw.decode("utf-8"))
    tasks = [_statement(body, macros) for body in problems]
    labels = [label for label, _ in tasks]
    if len(set(labels)) != len(labels):
        raise ValueError("Duplicate problem stable label")
    if set(labels) != set(solutions):
        raise ValueError("Problem and solution stable labels do not match")
    selected = set(labels if ids is None else ids)
    if not selected or selected - set(labels):
        raise ValueError(f"Unknown or empty selected stable IDs: {sorted(selected - set(labels))}")
    target = Path(destination).absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Destination already exists: {target}")
    target = target.parent.resolve(strict=True) / target.name
    if any(a == "public" and re.fullmatch(r"task-\d+", b) for a, b in zip(target.parts, target.parts[1:])):
        raise ValueError("Destination may not be inside a public task workspace")
    staging = Path(tempfile.mkdtemp(prefix=".prepare-eval-", dir=target.parent))
    try:
        (staging / "private").mkdir()
        manifest_tasks = []
        for index, (label, prompt) in enumerate(tasks, 1):
            if label not in selected:
                continue
            task_id = f"task-{index:04d}"
            statement_hash, solution_hash = _hash(prompt), _hash(solutions[label])
            public_dir, private_file = f"public/{task_id}", f"private/{task_id}.json"
            public = staging / public_dir
            public.mkdir(parents=True)
            (public / "prompt.md").write_bytes(prompt.encode("utf-8"))
            _json(public / "task.json", {"schema_version": 1, "id": task_id, "statement_sha256": statement_hash})
            _json(staging / private_file, {
                "schema_version": 1, "id": task_id, "stable_id": label,
                "statement_sha256": statement_hash, "solution_sha256": solution_hash,
                "reference_solution_tex": solutions[label],
                "rubric": {"review_status": "unreviewed", "reference_status": "unverified",
                           "answer_type": "manual", "accepted_answer": None, "requires_proof": False,
                           "requirements": [], "verification_evidence": []},
            })
            manifest_tasks.append({"id": task_id, "stable_id": label,
                                   "statement_sha256": statement_hash, "solution_sha256": solution_hash,
                                   "public_dir": public_dir, "private_file": private_file})
        _json(staging / "manifest.json", {"schema_version": 1,
              "created_at": datetime.now(timezone.utc).isoformat(), "source_tex": str(source),
              "benchmark_sha256": _hash(raw), "tasks": manifest_tasks})
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Destination already exists: {target}")
        _publish(staging, target)
    except BaseException:
        _remove_tree(staging)
        raise
    return target


# 4. Command-line interface

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--ids", nargs="+", metavar="STABLE_LABEL")
    args = parser.parse_args()
    try:
        result = prepare(args.tex, args.destination, args.ids)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(2, f"prepare_eval: {error}\n")
    print(f"Prepared {result}; private rubrics and references require review before model execution.")


if __name__ == "__main__":
    main()
