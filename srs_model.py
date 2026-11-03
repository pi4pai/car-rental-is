from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

@dataclass
class Requirement:
    """Опис однієї вимоги до інформаційної системи."""

    id: str
    type: str
    text: str
    source: str
    priority: int | None = None
    parent: str | None = None

@dataclass
class Stakeholder:
    """Опис зацікавленої сторони системи."""

    role: str
    description: str

@dataclass
class UserStory:
    """Опис користувацької історії."""

    id: str
    text: str

@dataclass
class SystemRequest:
    """Системний запит на розроблення інформаційної системи."""

    sponsor: str
    business_need: str
    business_requirements: list[str] = field(default_factory=list)
    business_value: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

@dataclass
class Specification:
    """Повна специфікація вимог до інформаційної системи."""

    project: str
    system_request: SystemRequest
    stakeholders: list[Stakeholder]
    user_stories: list[UserStory]
    requirements: list[Requirement]

def normalize_text(value: Any) -> str:
    """Перетворює багаторядковий текст на один рядок."""
    if value is None:
        return ""
    return " ".join(str(value).split())

def load_specification(path: str | Path) -> Specification:
    """Завантажує специфікацію з YAML-файлу."""
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("YAML-файл повинен містити словник верхнього рівня.")

    request_data = data["system_request"]

    system_request = SystemRequest(
        sponsor=normalize_text(request_data["sponsor"]),
        business_need=normalize_text(request_data["business_need"]),
        business_requirements=[
            normalize_text(item)
            for item in request_data.get("business_requirements", [])
        ],
        business_value=[
            normalize_text(item)
            for item in request_data.get("business_value", [])
        ],
        constraints=[
            normalize_text(item)
            for item in request_data.get("constraints", [])
        ],
    )

    stakeholders = [
        Stakeholder(
            role=normalize_text(item["role"]),
            description=normalize_text(item["description"]),
        )
        for item in data.get("stakeholders", [])
    ]

    user_stories = [
        UserStory(
            id=normalize_text(item["id"]),
            text=normalize_text(item["text"]),
        )
        for item in data.get("user_stories", [])
    ]

    requirements = [
        Requirement(
            id=normalize_text(item["id"]),
            type=normalize_text(item["type"]),
            text=normalize_text(item["text"]),
            source=normalize_text(item["source"]),
            priority=item.get("priority"),
            parent=item.get("parent"),
        )
        for item in data.get("requirements", [])
    ]

    return Specification(
        project=normalize_text(data["project"]),
        system_request=system_request,
        stakeholders=stakeholders,
        user_stories=user_stories,
        requirements=requirements,
    )
