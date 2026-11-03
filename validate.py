"""Автоматизоване рецензування якості вимог (ЛР 1, завдання 3).

Використання: python validate.py srs.yaml
Код завершення: 1 — знайдено дефекти, 0 — специфікація чиста.
"""
import difflib
import re
import sys
from dataclasses import dataclass

from srs_model import Specification, load_specification

ALLOWED_TYPES = {
    "functional",
    "operational",
    "performance",
    "security",
    "cultural",
    "constraint",
}

ID_PATTERN = re.compile(r"^(R\d+(\.\d+)*|N\d+|C\d+)$")

REQUIRED_PREFIXES = ("іс повинна", "система повинна")

# Розмиті слова: перевіряємо основу на початку слова, щоб ловити всі форми
# («швидко», «швидкий», «зручний», «зручно» тощо).
VAGUE_WORDS = [
    "швидк",
    "зручн",
    "легк",
    "тощо",
    "інтуїтивн",
    "ефективн",
    "оптимальн",
    "достатнь",
    "гнучк",
    "сучасн",
    "приблизн",
    "дружн",
]

# Власна перевірка 1: деталі реалізації у вимогах.
# «клас» навмисно не включено: «клас автомобіля» — термін предметної області.
IMPLEMENTATION_WORDS = [
    "кнопк",
    "таблиц",
    "mysql",
    "postgresql",
    "sqlite",
    "django",
    "flask",
    "html",
    "json",
    "випадаюч",
]

SIMILARITY_THRESHOLD = 0.85


@dataclass
class Defect:
    """Один знайдений дефект вимоги."""
    req_id: str
    kind: str
    message: str

    def __str__(self) -> str:
        return f"{self.req_id} [{self.kind}] {self.message}"


def normalize(text: str) -> str:
    """Нижній регістр, один пробіл між словами, апострофи до одного вигляду."""
    text = text.lower().replace("’", "'").replace("ʼ", "'")
    return " ".join(text.split())


def find_word_stem(text: str, stems: list[str]) -> str | None:
    """Повертає першу основу зі списку, з якої починається якесь слово тексту."""
    words = re.findall(r"[\w']+", normalize(text))
    for stem in stems:
        if any(word.startswith(stem) for word in words):
            return stem
    return None


def check_ids(spec: Specification) -> list[Defect]:
    """Перевірка 1: ID відповідає шаблону й унікальний."""
    defects = []
    seen = set()
    for req in spec.requirements:
        if not ID_PATTERN.match(req.id):
            defects.append(Defect(req.id, "формат", "ID не відповідає шаблону R1 / R1.1 / N1 / C1"))
        if req.id in seen:
            defects.append(Defect(req.id, "надлишковість", "ID повторюється"))
        seen.add(req.id)
    return defects


def check_types(spec: Specification) -> list[Defect]:
    """Перевірка 2: тип вимоги з допустимого переліку."""
    return [
        Defect(req.id, "формат", f"недопустимий тип «{req.type}»")
        for req in spec.requirements
        if req.type not in ALLOWED_TYPES
    ]


def check_wording(spec: Specification) -> list[Defect]:
    """Перевірка 3: текст починається з «ІС повинна» або «Система повинна»."""
    return [
        Defect(req.id, "формулювання", "немає «ІС повинна…»")
        for req in spec.requirements
        if not normalize(req.text).startswith(REQUIRED_PREFIXES)
    ]


def check_vague_words(spec: Specification) -> list[Defect]:
    """Перевірка 4: немає розмитих слів."""
    defects = []
    for req in spec.requirements:
        stem = find_word_stem(req.text, VAGUE_WORDS)
        if stem:
            defects.append(Defect(req.id, "неоднозначність", f"розмите слово «{stem}…»"))
    return defects


def check_performance_numbers(spec: Specification) -> list[Defect]:
    """Перевірка 5: вимога продуктивності містить числовий критерій."""
    return [
        Defect(req.id, "неперевірюваність", "немає числового критерію")
        for req in spec.requirements
        if req.type == "performance" and not re.search(r"\d", req.text)
    ]


def check_priorities(spec: Specification) -> list[Defect]:
    """Перевірка 6: пріоритет — ціле число 1..5 для всіх, крім обмежень."""
    defects = []
    for req in spec.requirements:
        if req.type == "constraint":
            continue
        priority = req.priority
        # bool — підклас int у Python, тому відсікаємо його окремо
        if not isinstance(priority, int) or isinstance(priority, bool) or not 1 <= priority <= 5:
            defects.append(Defect(req.id, "пріоритет", "пріоритет має бути 1..5"))
    return defects


def check_parents(spec: Specification) -> list[Defect]:
    """Перевірка 7: батьківська вимога існує, а ID підвимоги продовжує ID батька."""
    defects = []
    ids = {req.id for req in spec.requirements}
    for req in spec.requirements:
        if req.parent:
            if req.parent not in ids:
                defects.append(Defect(req.id, "нетрасованість", f"немає батька {req.parent}"))
            elif not req.id.startswith(req.parent + "."):
                defects.append(Defect(req.id, "нетрасованість", f"ID не продовжує ID батька {req.parent}"))
        elif "." in req.id:
            defects.append(Defect(req.id, "нетрасованість", "підвимога без поля parent"))
    return defects


def check_similar_texts(spec: Specification) -> list[Defect]:
    """Перевірка 8: немає двох вимог із дуже схожими текстами (≥ 85 %)."""
    defects = []
    reqs = spec.requirements
    for i, later in enumerate(reqs):
        for earlier in reqs[:i]:
            ratio = difflib.SequenceMatcher(None, normalize(earlier.text), normalize(later.text)).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                defects.append(Defect(later.id, "надлишковість", f"схожа на {earlier.id} ({ratio:.0%})"))
    return defects


def check_implementation_words(spec: Specification) -> list[Defect]:
    """Власна перевірка 1: вимога не містить деталей реалізації."""
    defects = []
    for req in spec.requirements:
        stem = find_word_stem(req.text, IMPLEMENTATION_WORDS)
        if stem:
            defects.append(Defect(req.id, "деталі реалізації", f"слово реалізації «{stem}…»"))
    return defects


def check_user_stories_used(spec: Specification) -> list[Defect]:
    """Власна перевірка 2: кожна user story є джерелом хоча б однієї вимоги."""
    sources = " ".join(req.source for req in spec.requirements)
    return [
        Defect(story.id, "неповнота", "user story не є джерелом жодної вимоги")
        for story in spec.user_stories
        if story.id not in sources
    ]


def check_constraints(spec: Specification) -> list[Defect]:
    """Власна перевірка 3: обмеження має ID виду C1 і не має пріоритету."""
    defects = []
    for req in spec.requirements:
        is_c_id = req.id.startswith("C")
        if is_c_id and req.type != "constraint":
            defects.append(Defect(req.id, "формат", "ID обмеження, але тип не constraint"))
        if req.type == "constraint" and not is_c_id:
            defects.append(Defect(req.id, "формат", "обмеження має мати ID виду C1"))
        if req.type == "constraint" and req.priority is not None:
            defects.append(Defect(req.id, "пріоритет", "обмеження не має пріоритету"))
    return defects


CHECKS = [
    check_ids,
    check_types,
    check_wording,
    check_vague_words,
    check_performance_numbers,
    check_priorities,
    check_parents,
    check_similar_texts,
    check_implementation_words,
    check_user_stories_used,
    check_constraints,
]


def validate(spec: Specification) -> list[Defect]:
    """Запускає всі перевірки і повертає список дефектів."""
    defects = []
    for check in CHECKS:
        defects.extend(check(spec))
    return defects


def main() -> int:
    if len(sys.argv) != 2:
        print("Використання: python validate.py srs.yaml")
        return 2
    # Консоль Windows за замовчуванням не UTF-8 — без цього кирилиця ламається
    sys.stdout.reconfigure(encoding="utf-8")
    spec = load_specification(sys.argv[1])
    defects = validate(spec)
    for defect in defects:
        print(defect)
    print(f"Перевірено {len(spec.requirements)} вимог, знайдено {len(defects)} дефектів")
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
