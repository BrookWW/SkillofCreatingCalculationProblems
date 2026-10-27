"""Create a minimal amsart project, preserving every existing file."""

# Contents (search the numbered section headings below):
# 1. Project initialization
# 2. Command-line interface

from __future__ import annotations

import argparse
from pathlib import Path


# 1. Project initialization

def initialize(destination: str | Path) -> dict[str, list[str]]:
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and not destination.is_dir():
        raise ValueError("The project destination must be a directory.")
    assets = Path(__file__).resolve().parents[1] / "assets"
    sources = {name: (assets / name).read_text(encoding="utf-8")
               for name in ("main.tex", "references.bib")}
    for name in sources:
        target = destination / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"Expected an ordinary project file: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    result: dict[str, list[str]] = {"created": [], "preserved": []}
    for name in ("main.tex", "references.bib"):
        target = destination / name
        if target.exists():
            result["preserved"].append(str(target))
        else:
            with target.open("x", encoding="utf-8") as stream:
                stream.write(sources[name])
            result["created"].append(str(target))
    return result


# 2. Command-line interface

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        result = initialize(args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    for operation, paths in result.items():
        for path in paths:
            print(f"{operation}: {path}")


if __name__ == "__main__":
    main()
