"""Брейнштормінг: розмічений текст -> brainstorm.csv (ЛР 2, завдання 1).

Розмітка: [фраза]{номер правила 1-9}.
Використання: python brainstorm.py domain.txt brainstorm.csv
Код завершення: 1 — розмітка містить помилки, 0 — усе коректно.
"""
import csv
import re
import sys
from pathlib import Path

MARK_PATTERN = re.compile(r"\[([^\[\]]*)\]\{([^{}]*)\}")


def normalize_phrase(phrase: str) -> str:
    """Нижній регістр і один пробіл між словами: ключ для пошуку дублікатів."""
    return " ".join(phrase.lower().split())


def find_markup_errors(text: str) -> list[str]:
    """Повертає повідомлення про незакриті дужки та некоректні номери правил."""
    errors = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in MARK_PATTERN.finditer(line):
            if not match.group(1).strip():
                errors.append(f"рядок {line_number}: порожня фраза")
            number = match.group(2).strip()
            if not number.isdigit() or not 1 <= int(number) <= 9:
                errors.append(f"рядок {line_number}: номер правила поза діапазоном 1-9: «{match.group(0)}»")
        # Коректні мітки прибрали — усе, що лишилось із дужок, є помилкою
        rest = MARK_PATTERN.sub("", line)
        for symbol in "[]{}":
            if symbol in rest:
                fragment = rest[rest.index(symbol):][:30]
                errors.append(f"рядок {line_number}: незакрита або зайва дужка «{symbol}» біля «{fragment}»")
                break
    return errors


def extract_phrases(text: str) -> list[dict]:
    """Збирає унікальні пари «фраза + правило» і рахує кількість згадувань."""
    found = {}
    for match in MARK_PATTERN.finditer(text):
        number = match.group(2).strip()
        if not number.isdigit():
            continue
        key = (normalize_phrase(match.group(1)), int(number))
        found[key] = found.get(key, 0) + 1
    return [
        {"phrase": phrase, "rule": rule, "count": count}
        for (phrase, rule), count in found.items()
    ]


def save_csv(rows: list[dict], path: str | Path) -> None:
    # utf-8-sig: щоб Excel правильно показував кирилицю
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["phrase", "rule", "count"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if len(sys.argv) != 3:
        print("Використання: python brainstorm.py domain.txt brainstorm.csv")
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    errors = find_markup_errors(text)
    for error in errors:
        print(error)
    rows = extract_phrases(text)
    save_csv(rows, sys.argv[2])
    words = len(MARK_PATTERN.sub(r"\1", text).split())
    print(f"Слів в описі: {words}; унікальних фраз: {len(rows)}; помилок розмітки: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
