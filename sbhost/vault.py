"""A read-only reader for a vault folder: the Markdown notes, their YAML frontmatter and their tags.

Phase 1 writes nothing to the vault. A note is one `.md` file. Its frontmatter is the YAML block between
the first two `---` lines. Tags come from the frontmatter's `tags` list.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_FENCE = "---"


def _split(text: str) -> tuple[dict, str]:
    if not text.startswith(_FENCE):
        return {}, text
    lines = text.split("\n")
    try:
        end = lines.index(_FENCE, 1)
    except ValueError:
        return {}, text
    frontmatter = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, "\n".join(lines[end + 1:])


class VaultReader:
    """Reads every note under `root`. `entries()` returns one dict per note, with `stem`, `path`,
    `frontmatter`, `tags` and `body`, the shape the plugins read."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def recorded(self) -> list[str]:
        """The vaults this host reads: one, when the folder exists."""
        return [self._root.name] if self._root.is_dir() else []

    def entries(self) -> list[dict]:
        if not self._root.is_dir():
            return []
        found = []
        for path in sorted(self._root.rglob("*.md")):
            frontmatter, body = _split(path.read_text(encoding="utf-8", errors="replace"))
            tags = frontmatter.get("tags") or []
            found.append({
                "stem": path.stem,
                "path": str(path),
                "frontmatter": frontmatter,
                "tags": [str(tag) for tag in tags] if isinstance(tags, list) else [],
                "body": body,
            })
        return found
