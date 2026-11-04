"""Тести допоміжних програм ЛР 2: brainstorm, dmcd, review."""
from brainstorm import extract_phrases, find_markup_errors
from dmcd import attribute_type
from review import review


def row(code, name="", owner="", target="", mult="", phrase="x"):
    return {"phrase": phrase, "code": code, "name": name, "owner": owner, "target": target,
            "mult": mult, "rule": "", "note": ""}


# --- brainstorm ---

def test_brainstorm_counts_duplicates_ignoring_case_and_spaces():
    rows = extract_phrases("[Клієнт]{1} та [клієнт]{1} і [ клієнт  ]{1}, [бронює]{3}")
    assert {"phrase": "клієнт", "rule": 1, "count": 3} in rows
    assert len(rows) == 2


def test_brainstorm_reports_unclosed_bracket():
    assert any("дужка" in e for e in find_markup_errors("[клієнт{1} бронює"))


def test_brainstorm_reports_rule_out_of_range():
    assert any("1-9" in e for e in find_markup_errors("[клієнт]{10}"))


def test_brainstorm_accepts_valid_text():
    assert find_markup_errors("[клієнт]{1} [бронює]{3}") == []


# --- dmcd ---

def test_attribute_type_by_name():
    assert attribute_type("планова дата повернення") == "Date"
    assert attribute_type("вартість за добу") == "Money"
    assert attribute_type("марка") == "String"


# --- review ---

def test_review_finds_class_without_attributes():
    issues = review([row("C", "А"), row("C", "Б"), row("AS", "зв", "А", "Б", "1;1"), row("A", "поле", "А")])
    assert issues == ["клас «Б» не має атрибутів"]


def test_review_finds_isolated_class():
    assert any("ізольований" in i for i in review([row("C", "А"), row("A", "поле", "А")]))


def test_review_finds_link_without_multiplicity():
    rows = [row("C", "А"), row("C", "Б"), row("A", "п", "А"), row("A", "п", "Б"), row("AS", "зв", "А", "Б")]
    assert any("кратностей" in i for i in review(rows))


def test_review_finds_missing_class_in_link():
    rows = [row("C", "А"), row("A", "п", "А"), row("AS", "зв", "А", "Б", "1;1")]
    assert any("немає класу «Б»" in i for i in review(rows))


def test_review_finds_class_used_as_attribute():
    rows = [row("C", "А"), row("C", "Б"), row("A", "б", "А"), row("A", "п", "Б"), row("AS", "зв", "А", "Б", "1;1")]
    assert any("збігається" in i for i in review(rows))


def test_review_finds_double_definition():
    rows = [row("C", "А"), row("C", "А"), row("A", "п", "А"), row("I", "є", "А", "А")]
    assert any("визначено 2" in i for i in review(rows))
