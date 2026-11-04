"""Автоматичне рецензування класифікації (ЛР 2, завдання 2).

Використання: python review.py classification.csv [brainstorm.csv]
Код завершення: 1 — є зауваження, 0 — модель чиста.
"""
import csv
import re
import sys
from pathlib import Path

CLASS_CODES = {"C", "AC"}
LINK_CODES = {"AS", "AG", "I", "AC"}
ALLOWED_CODES = {"C", "A", "AS", "AG", "I", "AC", "V", "M", "-"}
MULT_PATTERN = re.compile(r"^(\*|\d+|\d+\.\.(\d+|\*))$")


def load_classification(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as file:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(file)
        ]


def classes_of(rows: list[dict]) -> list[str]:
    """Назви класів у порядку появи, без повторів."""
    names = []
    for row in rows:
        if row["code"] in CLASS_CODES and row["name"] not in names:
            names.append(row["name"])
    return names


def review(rows: list[dict]) -> list[str]:
    """Перевіряє класифікацію за контрольним списком і повертає зауваження."""
    issues = []
    names = classes_of(rows)
    class_rows = [r["name"] for r in rows if r["code"] in CLASS_CODES]

    for row in rows:
        if row["code"] not in ALLOWED_CODES:
            issues.append(f"«{row['phrase']}»: невідомий код «{row['code']}»")

    # Подвійне визначення класу
    for name in names:
        if class_rows.count(name) > 1:
            issues.append(f"клас «{name}» визначено {class_rows.count(name)} рази")

    # Класи без атрибутів
    owners = {r["owner"] for r in rows if r["code"] == "A"}
    for name in names:
        if name not in owners:
            issues.append(f"клас «{name}» не має атрибутів")

    # Атрибут належить існуючому класу; назва не збігається з класом (клас як тип)
    for row in rows:
        if row["code"] != "A":
            continue
        if row["owner"] not in names:
            issues.append(f"атрибут «{row['name']}»: немає класу-власника «{row['owner']}»")
        if row["name"].lower() in {n.lower() for n in names}:
            issues.append(f"атрибут «{row['name']}» класу «{row['owner']}» збігається з назвою класу")

    links = [r for r in rows if r["code"] in LINK_CODES]

    # Зв'язки на неіснуючий клас
    for link in links:
        for end in (link["owner"], link["target"]):
            if end not in names:
                issues.append(f"зв'язок «{link['name']}»: немає класу «{end}»")

    # Зв'язки без кратностей (наслідування кратностей не має)
    for link in links:
        if link["code"] in {"I", "AC"}:
            continue
        parts = link["mult"].split(";")
        if len(parts) != 2 or not all(MULT_PATTERN.match(part.strip()) for part in parts):
            issues.append(f"зв'язок «{link['name']}» ({link['owner']} - {link['target']}): немає кратностей виду m;n")

    # Асоціативний клас приєднується до наявної асоціації
    associations = {
        frozenset((r["owner"], r["target"])) for r in rows if r["code"] == "AS"
    }
    for row in rows:
        if row["code"] == "AC" and frozenset((row["owner"], row["target"])) not in associations:
            issues.append(f"асоціативний клас «{row['name']}»: немає асоціації {row['owner']} - {row['target']}")

    # Ізольовані класи
    linked = set()
    for link in links:
        linked.update((link["owner"], link["target"]))
    linked.update(r["name"] for r in rows if r["code"] == "AC")
    for name in names:
        if name not in linked:
            issues.append(f"клас «{name}» ізольований: немає жодного зв'язку")
    return issues


def unclassified_phrases(rows: list[dict], brainstorm_path: str | Path) -> list[str]:
    """Кожна фраза брейнштормінгу має бути класифікована."""
    with open(brainstorm_path, encoding="utf-8-sig", newline="") as file:
        phrases = [row["phrase"] for row in csv.DictReader(file)]
    known = {row["phrase"] for row in rows}
    return [f"фразу «{p}» не класифіковано" for p in phrases if p not in known]


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print("Використання: python review.py classification.csv [brainstorm.csv]")
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load_classification(sys.argv[1])
    issues = review(rows)
    if len(sys.argv) == 3:
        issues += unclassified_phrases(rows, sys.argv[2])
    for issue in issues:
        print(issue)
    counts = {code: sum(r["code"] == code for r in rows) for code in ("C", "AC", "A", "AS", "AG", "I")}
    print(f"Класів: {counts['C'] + counts['AC']} (асоціативних: {counts['AC']}), атрибутів: {counts['A']}, "
          f"зв'язків: {counts['AS'] + counts['AG'] + counts['I']} "
          f"(AS {counts['AS']}, AG {counts['AG']}, I {counts['I']}); зауважень: {len(issues)}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
