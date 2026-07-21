"""Skill endpoints — serve SKILL.md content for chat preprompt."""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Skills"])

SKILLS_DIR = Path(__file__).resolve().parents[4] / "skills"


def _list_skills() -> list[dict[str, str]]:
    if not SKILLS_DIR.is_dir():
        return []
    out: list[dict[str, str]] = []
    for child in sorted(SKILLS_DIR.iterdir()):
        skill_file = child / "SKILL.md"
        if skill_file.is_file():
            name = child.name
            desc = ""
            try:
                text = skill_file.read_text(encoding="utf-8")
                for line in text.splitlines():
                    if line.startswith("description:"):
                        desc = line.removeprefix("description:").strip().strip("'\"")
                        break
            except Exception:
                pass
            out.append({"name": name, "description": desc})
    return out


@router.get("/api/skills")
async def list_skills() -> dict[str, Any]:
    skills = _list_skills()
    return {"success": True, "skills": skills, "count": len(skills)}


@router.get("/api/skills/{name}")
async def get_skill(name: str) -> str:
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if not skill_file.is_file():
        return "not found"
    try:
        return skill_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read skill %s: %s", name, e)
        return "not found"
