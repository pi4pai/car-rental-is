from collections import Counter
from pathlib import Path
import sys

from srs_model import load_specification

REQUIREMENT_TYPE_NAMES = {
    "functional": "Функціональні вимоги",
    "operational": "Операційні вимоги",
    "performance": "Вимоги до продуктивності",
    "security": "Вимоги до безпеки",
    "cultural": "Культурні вимоги",
    "constraint": "Обмеження",
}

PRIORITY_NAMES = {
    1: "Високий",
    2: "Середній",
    3: "Низький",
    4: "Бажаний",
}

def build_report(spec):
    lines = [
        f"# Специфікація вимог до програмного забезпечення (SRS)",
        "",
        f"## 1. Вступ",
        "",
        f"### 1.1. Назва проєкту",
        "",
        spec.project,
        "",
        "### 1.2. Замовник (спонсор)",
        "",
        spec.system_request.sponsor,
        "",
        "### 1.3. Бізнес-потреба",
        "",
        spec.system_request.business_need,
        "",
        "### 1.4. Бізнес-вимоги",
        "",
    ]

    for item in spec.system_request.business_requirements:
        lines.append(f"- {item}")

    lines.extend(["", "### 1.5. Очікувана бізнес-цінність", ""])
    for item in spec.system_request.business_value:
        lines.append(f"- {item}")

    lines.extend(["", "## 2. Загальний опис", "", "### 2.1. Стейкхолдери", ""])
    for stakeholder in spec.stakeholders:
        lines.append(f"- **{stakeholder.role}.** {stakeholder.description}")

    lines.extend(["", "### 2.2. Користувацькі історії", ""])
    for story in spec.user_stories:
        lines.append(f"- **{story.id}.** {story.text}")

    lines.extend(["", "### 2.3. Основні обмеження", ""])
    for constraint in spec.system_request.constraints:
        lines.append(f"- {constraint}")

    lines.extend([
        "",
        "## 3. Конкретні вимоги",
        "",
        "### 3.1. Вимоги за типами",
        "",
    ])

    requirements_by_id = {req.id: req for req in spec.requirements}
    children_by_parent = {}
    for req in spec.requirements:
        if req.parent:
            children_by_parent.setdefault(req.parent, []).append(req)

    top_level = [req for req in spec.requirements if not req.parent]

    # Group parent requirements and their subrequirements under the same type.
    types_in_order = []
    for req in top_level:
        if req.type not in types_in_order:
            types_in_order.append(req.type)

    for req_type in types_in_order:
        lines.extend([
            "",
            f"#### {REQUIREMENT_TYPE_NAMES.get(req_type, req_type)}",
            "",
        ])

        for req in top_level:
            if req.type != req_type:
                continue

            priority = (
                f"Пріоритет: **{PRIORITY_NAMES.get(req.priority, req.priority)}**"
                if req.priority is not None
                else "Пріоритет не визначено"
            )
            lines.append(f"- **{req.id}.** {req.text} ({priority}; Джерело: {req.source})")

            for child in children_by_parent.get(req.id, []):
                child_priority = (
                    f"Пріоритет: **{PRIORITY_NAMES.get(child.priority, child.priority)}**"
                    if child.priority is not None
                    else "Пріоритет не визначено"
                )
                lines.append(
                    f"  - **{child.id}.** {child.text} "
                    f"({child_priority}; Джерело: {child.source})"
                )

    type_counts = Counter(req.type for req in spec.requirements)
    priority_counts = Counter(
        req.priority for req in spec.requirements if req.priority is not None
    )

    lines.extend([
        "",
        "### 3.2. Статистика вимог",
        "",
        "#### Кількість вимог за типами",
        "",
        "| Тип вимоги | Кількість |",
        "|---|---:|",
    ])

    for req_type, count in sorted(type_counts.items()):
        lines.append(
            f"| {REQUIREMENT_TYPE_NAMES.get(req_type, req_type)} | {count} |"
        )

    lines.extend([
        "",
        "#### Кількість вимог за пріоритетами",
        "",
        "| Пріоритет | Кількість |",
        "|---|---:|",
    ])

    for priority in sorted(priority_counts):
        lines.append(
            f"| {PRIORITY_NAMES.get(priority, priority)} | {priority_counts[priority]} |"
        )

    lines.extend([
        "",
        f"**Загальна кількість вимог:** {len(spec.requirements)}.",
        "",
    ])

    return "\n".join(lines)

def main():
    if len(sys.argv) != 3:
        print("Використання: py srs_report.py srs.yaml SRS.md")
        raise SystemExit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    spec = load_specification(input_path)
    report = build_report(spec)
    output_path.write_text(report, encoding="utf-8")

    print(f"SRS-документ успішно створено: {output_path.resolve()}")
    print(f"Загальна кількість вимог: {len(spec.requirements)}")

if __name__ == "__main__":
    main()
