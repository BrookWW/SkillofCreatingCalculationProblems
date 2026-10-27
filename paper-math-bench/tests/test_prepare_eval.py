# Contents
# 1. Module setup: exporter loader and source paths.
# 2. TeX fixtures: legacy and tiered layouts.
# 3. PrepareEvalTests: anonymous export, validation, and safe publication.
# 4. Test entry point: unittest.main().

"""Tests for anonymous statement export and private reference isolation."""
# Module setup
import hashlib
import errno
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_eval.py"
SPEC = importlib.util.spec_from_file_location("prepare_eval", SCRIPT)
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)
OPTIONAL_BANK_PATH = os.environ.get("PAPER_MATH_BENCH_TEST_BANK")
OPTIONAL_BANK = Path(OPTIONAL_BANK_PATH).expanduser() if OPTIONAL_BANK_PATH else None


def logical_children(folder):
    """Count payload entries while accepting their paired AppleDouble metadata."""
    names = {p.name for p in folder.iterdir()}
    return {name for name in names if not (name.startswith("._") and name[2:] in names)}


# TeX fixture
def document(statement=r"Compute $1+1$.", label="prob:one", solution="PRIVATE GOLD ANSWER.", preamble="", title="Private title"):
    return (
        "\\documentclass{amsart}\n" + preamble + "\n\\title{Private manuscript}\n"
        "\\begin{document}\n\\section{Problems}\n"
        f"\\begin{{problem}}[{title}]\n\\label{{{label}}}\n{statement}\n\\end{{problem}}\n"
        "\\textit{Source.} \\cite{private-source}\n\\section{Solutions}\n"
        f"\\subsection*{{Solution to Problem~\\ref{{{label}}}}}\n{solution}\n"
        "\\bibliographystyle{amsplain}\n\\bibliography{private-bib}\n\\end{document}\n"
    )


def tiered_document(entries):
    """Build a title-free tier bank with solutions in reverse label order."""
    parts = [r"\documentclass{amsart}", r"\newtheorem{problem}{Problem}", r"\begin{document}"]
    for tier in ("T2", "T3", "T4"):
        parts.append(f"\\section{{{tier}}}")
        for group, label, statement, _ in entries:
            if group == tier:
                parts.append(f"\\begin{{problem}}\\label{{{label}}}{statement}\\end{{problem}}")
                parts.append(r"\textit{Source.} \cite{private-source}")
    parts.append(r"\section{Solutions}")
    for _, label, _, solution in reversed(entries):
        parts.append(f"\\subsection*{{Solution to Problem~\\ref{{{label}}}}}\n{solution}")
    parts.extend([r"\bibliographystyle{amsplain}", r"\bibliography{private-bib}", r"\end{document}"])
    return "\n".join(parts) + "\n"


# PrepareEvalTests: export and validation
class PrepareEvalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "main.tex"
        self.destination = self.root / "bundle"

    def prepare(self, source=None, ids=None):
        self.source.write_text(document() if source is None else source, encoding="utf-8")
        return exporter.prepare(self.source, self.destination, ids)

    def assert_rejected(self, source):
        with self.assertRaises((ValueError, OSError)):
            self.prepare(source)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".prepare-eval-*")), [])

    @unittest.skipUnless(OPTIONAL_BANK and OPTIONAL_BANK.is_file(),
                         "Set PAPER_MATH_BENCH_TEST_BANK to opt into a local bank export check.")
    def test_optional_question_bank_export(self):
        result = exporter.prepare(OPTIONAL_BANK, self.destination)
        manifest = json.loads((result / "manifest.json").read_text())
        count = OPTIONAL_BANK.read_text().count(r"\begin{problem}")
        self.assertGreater(count, 0)
        self.assertEqual(len(manifest["tasks"]), count)
        self.assertEqual(manifest["source_tex"], str(OPTIONAL_BANK.resolve()))
        self.assertEqual(manifest["benchmark_sha256"], hashlib.sha256(OPTIONAL_BANK.read_bytes()).hexdigest())
        for index, task in enumerate(manifest["tasks"], 1):
            self.assertEqual(task["id"], f"task-{index:04d}")
            public = result / task["public_dir"]
            self.assertEqual(logical_children(public), {"prompt.md", "task.json"})
            prompt = (public / "prompt.md").read_text()
            metadata = json.loads((public / "task.json").read_text())
            self.assertEqual(set(metadata), {"schema_version", "id", "statement_sha256"})
            self.assertEqual(metadata["statement_sha256"], hashlib.sha256(prompt.encode()).hexdigest())
            for forbidden in ("Source.", "\\cite", "\\label", "\\bibliography", "Solution to Problem", task["stable_id"]):
                self.assertNotIn(forbidden, prompt)
            private = json.loads((result / task["private_file"]).read_text())
            self.assertEqual(private["solution_sha256"], hashlib.sha256(private["reference_solution_tex"].encode()).hexdigest())
            self.assertEqual(private["rubric"]["review_status"], "unreviewed")
            self.assertEqual(private["rubric"]["reference_status"], "unverified")
            self.assertFalse(private["rubric"]["requires_proof"])
            self.assertNotIn("\\bibliography", private["reference_solution_tex"])
        self.assertEqual(len(logical_children(result / "public")), count)

    def test_comments_and_nested_title_are_not_exported(self):
        source = document(
            statement="Show \\{a,{b}\\} is finite.\n% \\end{problem} \\begin{problem} \\label{fake}\n"
                      "\\begin{enumerate}\\item Prove $a\\le b$.\\end{enumerate}",
            title=r"Secret [nested] {title with ] and {braces}}",
        )
        source = "% \\input{secret} \\begin{problem}\n" + source
        prompt = (self.prepare(source) / "public/task-0001/prompt.md").read_text()
        self.assertNotIn("Secret", prompt)
        self.assertNotIn("fake", prompt)
        self.assertIn(r"\begin{enumerate}", prompt)
        self.assertIn(r"\{a,{b}\}", prompt)

    def test_escaped_percent_and_comment_line_join(self):
        prompt = (self.prepare(document("A 10\\% rate, $a% comment\n+b$.")) / "public/task-0001/prompt.md").read_text()
        self.assertIn(r"10\%", prompt)
        self.assertIn("$a+b$", prompt)

    def test_private_solution_preserves_nested_tex(self):
        gold = r"\[\boxed{\begin{aligned}x&=2,\\y&=3.\end{aligned}}\]"
        result = self.prepare(document(solution=gold))
        private = json.loads((result / "private/task-0001.json").read_text())
        self.assertEqual(private["reference_solution_tex"], gold + "\n")
        self.assertNotIn(gold, (result / "public/task-0001/prompt.md").read_text())

    def test_tier_layout_order_anonymity_and_label_binding(self):
        entries = [(tier, f"prob:stable-{index}", f"Compute ${index}+1$.", f"PRIVATE ANSWER {index}.")
                   for index, tier in enumerate(("T2", "T3", "T4"), 1)]
        result = self.prepare(tiered_document(entries))
        tasks = json.loads((result / "manifest.json").read_text())["tasks"]
        self.assertEqual([t["id"] for t in tasks], ["task-0001", "task-0002", "task-0003"])
        self.assertEqual([t["stable_id"] for t in tasks], [e[1] for e in entries])
        for task, entry in zip(tasks, entries):
            prompt = (result / task["public_dir"] / "prompt.md").read_text()
            self.assertIn(entry[2], prompt)
            for hidden in ("T2", "T3", "T4", "Source.", "private-source", entry[1], entry[3]):
                self.assertNotIn(hidden, prompt)
            private = json.loads((result / task["private_file"]).read_text())
            self.assertEqual(private["reference_solution_tex"], entry[3] + "\n")

    def test_empty_tiers_are_allowed_but_empty_bank_is_not_exported(self):
        for mask in range(1, 8):
            entries = [(tier, f"prob:{index}", f"Compute ${index}$.", f"Answer {index}.")
                       for index, tier in enumerate(("T2", "T3", "T4")) if mask & (1 << index)]
            self.source.write_text(tiered_document(entries))
            result = exporter.prepare(self.source, self.root / f"bundle-{mask}")
            tasks = json.loads((result / "manifest.json").read_text())["tasks"]
            self.assertEqual([t["id"] for t in tasks],
                             [f"task-{index:04d}" for index in range(1, len(entries) + 1)])
        self.assert_rejected(tiered_document([]))

    def test_tier_layout_rejects_mixed_missing_reordered_and_duplicate_sections(self):
        base = tiered_document([("T3", "prob:one", "Compute $1$.", "One.")])
        for source in (base.replace(r"\section{T2}", r"\section{Problems}"),
                       base.replace(r"\section{T3}", r"\section{T2}"),
                       base.replace(r"\section{T3}", ""),
                       base.replace(r"\section{T2}", r"\section{T1}"),
                       base.replace(r"\section{T2}", r"\section{temporary}").replace(
                           r"\section{T3}", r"\section{T2}").replace(
                           r"\section{temporary}", r"\section{T3}"),
                       base.replace(r"\section{Solutions}", r"\section{Notes}\section{Solutions}")):
            with self.subTest(source=source):
                self.assert_rejected(source)

    def test_private_verbatim_is_opaque_and_preserved_byte_for_byte(self):
        literal = ("\\begin{Verbatim}[breaklines=true,fontsize=\\small]\r\n"
                   "% literal comment\r\n\\input{literal-data}\r\n{ unbalanced\r\n"
                   "\\section{T1}\r\nprint('100%')\r\n\\end{Verbatim}\r\n")
        result = self.prepare(document(solution="Before.\n" + literal + "After.",
                                       preamble=r"\usepackage{fvextra}"))
        private = json.loads((result / "private/task-0001.json").read_text())
        self.assertIn(literal.encode(), private["reference_solution_tex"].encode())
        prompt = (result / "public/task-0001/prompt.md").read_text()
        for hidden in ("Verbatim", "literal-data", "100%", exporter.PRIVATE_VERBATIM):
            self.assertNotIn(hidden, prompt)
        self.assertEqual(private["solution_sha256"], hashlib.sha256(
            private["reference_solution_tex"].encode()).hexdigest())

    def test_private_verbatim_without_options_and_commented_delimiters(self):
        literal = "\\begin{Verbatim}\n% data\n\\end{Verbatim}\n"
        source = "% \\begin{Verbatim}\n" + document(solution=literal)
        private = json.loads((self.prepare(source) / "private/task-0001.json").read_text())
        self.assertIn(literal, private["reference_solution_tex"])

    def test_verbatim_outside_private_solution_and_unsafe_options_fail_closed(self):
        literal = "\\begin{Verbatim}\nprivate code\n\\end{Verbatim}\n"
        base = document()
        header = r"\subsection*{Solution to Problem~\ref{prob:one}}"
        for source in (document(statement="\n" + literal),
                       document(preamble=literal),
                       document(preamble="\\newcommand{\\hidden}{\n" + literal + "}\n"),
                       base.replace(header, literal + header),
                       base.replace(r"\end{document}", literal + r"\end{document}"),
                       document(solution=literal.replace(r"\end{Verbatim}", "")),
                       document(solution=literal.replace(r"\begin{Verbatim}",
                                r"\begin{Verbatim}[formatcom=\input{secret}]")),
                       document(solution="Safe.\n\\input{secret}"),
                       document(preamble=r"\newcommand{\PaperMathBenchPrivateVerbatim}{leak}")):
            with self.subTest(source=source):
                self.assert_rejected(source)

    def test_safe_emphasis_and_long_arrow_do_not_enable_public_code(self):
        prompt = (self.prepare(document(r"An \emph{example}: $x\longrightarrow0$.",
                                        preamble=r"\usepackage{fvextra}")) /
                  "public/task-0001/prompt.md").read_text()
        self.assertIn(r"\emph{example}", prompt)
        self.assertIn(r"\longrightarrow", prompt)

    def test_only_used_safe_macro_definitions_are_copied(self):
        preamble = (r"\newcommand{\R}{\mathbb{R}}" + "\n" +
                    r"\newcommand{\norm}[1]{\left\|#1\right\|}" + "\n" +
                    r"\newcommand{\privateTitle}{Private manuscript metadata}")
        result = self.prepare(document(r"For $x\in\R$, compute $\norm{x}$.", preamble=preamble))
        prompt = (result / "public/task-0001/prompt.md").read_text()
        self.assertIn(r"\newcommand{\R}{\mathbb{R}}", prompt)
        self.assertIn(r"\newcommand{\norm}[1]", prompt)
        self.assertNotIn("privateTitle", prompt)
        self.assertNotIn("metadata", prompt)

    def test_unknown_and_recursive_macros_fail_closed(self):
        for preamble in ("", r"\newcommand{\unknown}{\anotherUnknown}", r"\newcommand{\unknown}{\unknown}"):
            with self.subTest(preamble=preamble):
                self.assert_rejected(document(r"Compute $\unknown$.", preamble=preamble))

    def test_includes_file_io_and_dynamic_tex_are_rejected(self):
        for command in (r"\input{answers}", r"\include{answers}", r"\write18{cat answers}",
                        r"\csname input\endcsname{answers}", r"\def\leak{answers}",
                        r"\newcommand{\leak}{\input{answers}}", r"\usepackage{answers}"):
            with self.subTest(command=command):
                self.assert_rejected(document(preamble=command))

    def test_citations_references_and_verbatim_in_statement_are_rejected(self):
        for statement in (r"See \cite{answer}.", r"Use \ref{answer}.", r"\verb|\begin{problem}|",
                          r"\href{gold}{answer}", "\\begin{verbatim}\ncode\n\\end{verbatim}",
                          "\\begin{lstlisting}\ncode\n\\end{lstlisting}",
                          r"An \emph{\input{secret}} example."):
            with self.subTest(statement=statement):
                self.assert_rejected(document(statement))

    def test_missing_invalid_and_duplicate_labels_are_rejected(self):
        base = document()
        for source in (base.replace(r"\label{prob:one}", ""),
                       document(label="bad id"),
                       base.replace(r"\label{prob:one}", r"\label{prob:one}\label{prob:two}")):
            with self.subTest(source=source):
                self.assert_rejected(source)
        second = "\\begin{problem}\\label{prob:one}Another statement.\\end{problem}\n"
        self.assert_rejected(base.replace(r"\section{Solutions}", second + r"\section{Solutions}"))

    def test_missing_duplicate_and_unknown_solutions_are_rejected(self):
        base = document()
        header = r"\subsection*{Solution to Problem~\ref{prob:one}}"
        for source in (base.replace(header, ""), base.replace(header, header + "X\n" + header),
                       base.replace(header, header.replace("prob:one", "prob:unknown")),
                       document(solution="")):
            with self.subTest(source=source):
                self.assert_rejected(source)

    def test_selection_preserves_original_index_and_checks_unknown_ids(self):
        self.source.write_text(tiered_document([
            ("T2", "prob:first", "Compute $1+1$.", "Two."),
            ("T3", "prob:second", "Compute $2+1$.", "Three."),
            ("T4", "prob:third", "Compute $3+1$.", "Four."),
        ]))
        result = exporter.prepare(self.source, self.destination, ["prob:second"])
        manifest = json.loads((result / "manifest.json").read_text())
        self.assertEqual([t["id"] for t in manifest["tasks"]], ["task-0002"])
        self.assertEqual(logical_children(result / "public"), {"task-0002"})
        with self.assertRaises(ValueError):
            exporter.prepare(self.source, self.root / "unknown", ["prob:unknown"])
        self.assertFalse((self.root / "unknown").exists())

    def test_existing_destination_is_never_overwritten(self):
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("untouched")
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(marker.read_text(), "untouched")

    def test_publish_race_does_not_replace_existing_empty_directory(self):
        staging = self.root / "staging"
        staging.mkdir()
        (staging / "payload").write_text("private")
        self.destination.mkdir()
        with self.assertRaises(FileExistsError):
            exporter._publish(staging, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertTrue((staging / "payload").exists())

    def test_write_failure_leaves_no_partial_destination(self):
        with patch.object(exporter, "_json", side_effect=OSError("disk error")):
            self.assert_rejected(document())

    def test_unsupported_exclusive_rename_preserves_export_hashes(self):
        with patch.object(exporter, "_rename_exclusive", side_effect=OSError(errno.ENOTSUP, "unsupported")):
            result = self.prepare()
        manifest = json.loads((result / "manifest.json").read_text())
        task = manifest["tasks"][0]
        self.assertEqual(task["statement_sha256"], hashlib.sha256(
            (result / task["public_dir"] / "prompt.md").read_bytes()).hexdigest())
        self.assertTrue((result / task["private_file"]).is_file())
        self.assertEqual(list(self.root.glob(".prepare-eval-*")), [])

    def test_copy_publication_commits_manifest_after_payload(self):
        copy = exporter.shutil.copyfileobj
        observed = []

        def checked_copy(incoming, outgoing):
            self.assertFalse((self.destination / "manifest.json").exists())
            observed.append(Path(outgoing.name).name)
            return copy(incoming, outgoing)

        with patch.object(exporter, "_rename_exclusive", side_effect=OSError(errno.ENOSYS, "unsupported")), \
                patch.object(exporter.shutil, "copyfileobj", side_effect=checked_copy):
            self.prepare()
        self.assertIn("prompt.md", observed)
        self.assertTrue((self.destination / "manifest.json").is_file())

    def test_copy_publication_race_preserves_existing_target(self):
        staging = self.root / "staging"
        staging.mkdir()
        (staging / "payload").write_text("private")
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("untouched")
        with patch.object(exporter, "_rename_exclusive", side_effect=OSError(errno.ENOTSUP, "unsupported")):
            with self.assertRaises(FileExistsError):
                exporter._publish(staging, self.destination)
        self.assertEqual(marker.read_text(), "untouched")
        self.assertTrue((staging / "payload").is_file())

    def test_copy_failure_removes_uncommitted_destination(self):
        with patch.object(exporter, "_rename_exclusive", side_effect=OSError(errno.ENOTSUP, "unsupported")), \
                patch.object(exporter.shutil, "copyfileobj", side_effect=OSError("disk error")):
            self.assert_rejected(document())

    def test_publication_permission_error_does_not_use_copy(self):
        with patch.object(exporter, "_rename_exclusive", side_effect=PermissionError(errno.EACCES, "denied")), \
                patch.object(exporter, "_publish_copy") as fallback:
            with self.assertRaises(PermissionError):
                self.prepare()
        fallback.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_destination_inside_public_task_is_rejected(self):
        workspace = self.root / "public" / "task-0001"
        workspace.mkdir(parents=True)
        self.destination = workspace / "gold-bundle"
        self.assert_rejected(document())

    def test_unbalanced_and_nested_problem_structures_are_rejected(self):
        base = document()
        for source in (base.replace("Compute $1+1$.", "Compute {$1+1$."),
                       base.replace("Compute $1+1$.", r"\begin{problem}nested\end{problem}"),
                       base.replace(r"\end{problem}", r"\end{enumerate}")):
            with self.subTest(source=source):
                self.assert_rejected(source)


# Test entry point
if __name__ == "__main__":
    unittest.main()
