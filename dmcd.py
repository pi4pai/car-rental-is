"""Генерація діаграми класів PlantUML із класифікації (ЛР 2, завдання 2).

Використання: python dmcd.py classification.csv domain.puml
"""
import sys
from pathlib import Path

from review import classes_of, load_classification


def attribute_type(name: str) -> str:
    """Тип атрибута для діаграми визначаємо за змістом його назви."""
    lowered = name.lower()
    if "дата" in lowered.split():
        return "Date"
    if any(word in lowered for word in ("вартість", "штраф", "сума")):
        return "Money"
    if any(word in lowered for word in ("пробіг", "пробігу", "рік", "рівень")):
        return "Integer"
    return "String"


def generate(rows: list[dict]) -> str:
    names = classes_of(rows)
    alias = {name: f"C{i}" for i, name in enumerate(names, start=1)}
    lines = [
        "@startuml",
        "hide circle",
        "hide empty methods",
        "skinparam classAttributeIconSize 0",
        "skinparam shadowing false",
        "skinparam dpi 130",
        "",
    ]
    for name in names:
        lines.append(f'class "{name}" as {alias[name]} {{')
        for row in rows:
            if row["code"] == "A" and row["owner"] == name:
                values = [
                    r["name"] for r in rows
                    if r["code"] == "V" and r["owner"] == name and r["note"] == row["name"]
                ]
                kind = "{" + ", ".join(values) + "}" if values else attribute_type(row["name"])
                lines.append(f"  {row['name']} : {kind}")
        lines.append("}")
    lines.append("")

    for row in rows:
        code = row["code"]
        if code not in {"AS", "AG", "I"}:
            continue
        first, second = alias[row["owner"]], alias[row["target"]]
        if code == "I":
            lines.append(f"{first} <|-- {second}")
            continue
        m, n = (part.strip() for part in row["mult"].split(";"))
        arrow = "o--" if code == "AG" else "--"
        lines.append(f'{first} "{m}" {arrow} "{n}" {second} : {row["name"]} >')

    for row in rows:
        if row["code"] == "AC":
            lines.append(f"({alias[row['owner']]}, {alias[row['target']]}) .. {alias[row['name']]}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print("Використання: python dmcd.py classification.csv domain.puml")
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load_classification(sys.argv[1])
    Path(sys.argv[2]).write_text(generate(rows), encoding="utf-8")
    print(f"Діаграму збережено: {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
