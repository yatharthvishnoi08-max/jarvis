"""Skill management and dynamic skill execution inspired by OpenJarvis.
Follows the agentskills.io standard.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "catalog"

@dataclass
class Skill:
    name: str
    description: str
    content: str
    path: Path
    author: str = "JARVIS Core"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "path": str(self.path)
        }

class SkillManager:
    """Discovers, catalogs, and loads on-demand agent skills."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or SKILLS_DIR
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        self._skills.clear()
        for skill_file in self.root_dir.glob("**/SKILL.md"):
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    self._skills[skill.name.lower()] = skill
            except Exception:
                pass

    def _parse_skill_file(self, path: Path) -> Optional[Skill]:
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---"):
            return None

        parts = raw.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter_str = parts[1]
        body = parts[2].strip()

        meta = yaml.safe_load(frontmatter_str) or {}
        name = meta.get("name", path.parent.name)
        description = meta.get("description", "")
        author = meta.get("author", "Community")
        tags = meta.get("tags", [])

        return Skill(
            name=name,
            description=description,
            content=body,
            path=path,
            author=author,
            tags=tags
        )

    def list_skills(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._skills.values()]

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name.lower())

    def install_skill(self, name: str, description: str, instructions: str, tags: Optional[List[str]] = None) -> bool:
        """Create and install a new skill on disk."""
        skill_dir = self.root_dir / name.lower()
        skill_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "name": name,
            "description": description,
            "author": "Chairman / JARVIS",
            "tags": tags or []
        }

        frontmatter = yaml.dump(meta, sort_keys=False)
        content = f"---\n{frontmatter}---\n\n{instructions.strip()}\n"

        target_file = skill_dir / "SKILL.md"
        target_file.write_text(content, encoding="utf-8")
        self.reload()
        return True

skill_manager = SkillManager()
