#!/usr/bin/env python3
"""Prints the CHANGELOG section for one version, for use as GitHub release notes.

The changelog is already the place where each release is described properly, so a
release body should be that text rather than a second, thinner description that
drifts out of step with it.

Usage:  python scripts/changelog_section.py 5.1.0 [path/to/CHANGELOG.md]

Exits 1 with a message on stderr when the version has no section, so the release
workflow fails loudly instead of publishing an empty release.
"""

import re
import sys
from pathlib import Path

# Section headings look like:  ## 💥 **v5.0.0** - August 2026 *(Breaking)*
# The version is matched on its own so decoration and dates can change freely.
_HEADING = re.compile(r"^##\s+.*?\*\*v(?P<version>\d+\.\d+\.\d+)\*\*", re.M)


def section_for(version, text):
    """Returns the body of the section for ``version``, or None when absent."""
    matches = list(_HEADING.finditer(text))
    for index, match in enumerate(matches):
        if match.group("version") != version:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        # Drop the trailing "---" separator and the rest of the heading line.
        body = body.split("\n", 1)[1] if "\n" in body else ""
        return body.strip().rstrip("-").strip()
    return None


def main():
    if not 2 <= len(sys.argv) <= 3:
        print(__doc__, file=sys.stderr)
        return 1

    version = sys.argv[1].lstrip("v")
    path = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("docs/CHANGELOG.md")

    if not path.exists():
        print(f"changelog not found: {path}", file=sys.stderr)
        return 1

    body = section_for(version, path.read_text(encoding="utf-8"))
    if not body:
        print(
            f"no section for v{version} in {path} — add one before tagging",
            file=sys.stderr,
        )
        return 1

    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
