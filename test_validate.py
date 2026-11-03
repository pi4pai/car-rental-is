"""Тести валідатора вимог (ЛР 1, завдання 3). Запуск: pytest -v"""
from pathlib import Path

import pytest

import validate
from srs_model import Requirement, Specification, SystemRequest, UserStory, load_specification

HERE = Path(__file__).parent


def req(id="R1", type="functional", text="ІС повинна забезпечувати бронювання автомобіля.",
        priority=1, parent=None, source="User Story US-01"):
    """Коректна вимога, у якій тест змінює одне поле."""
    return Requirement(id=id, type=type, text=text, source=source, priority=priority, parent=parent)


def make_spec(*requirements, stories=("US-01",)):
    return Specification(
        project="Тест",
        system_request=SystemRequest(sponsor="Керівник", business_need="Тест"),
        stakeholders=[],
        user_stories=[UserStory(id=s, text="Як клієнт, я хочу …") for s in stories],
        requirements=list(requirements),
    )


def kinds(defects):
    return {d.kind for d in defects}


def test_clean_requirement_has_no_defects():
    assert validate.validate(make_spec(req())) == []


# Перевірка 1
@pytest.mark.parametrize("bad_id", ["REQ-1", "R1.", "r1", "N1.1", "F1"])
def test_id_pattern(bad_id):
    defects = validate.check_ids(make_spec(req(id=bad_id)))
    assert "формат" in kinds(defects)


def test_id_duplicate():
    spec = make_spec(req(id="R1"), req(id="R1", text="ІС повинна зберігати дату видачі."))
    assert "надлишковість" in kinds(validate.check_ids(spec))


# Перевірка 2
def test_type_not_allowed():
    defects = validate.check_types(make_spec(req(type="usability")))
    assert [d.req_id for d in defects] == ["R1"]


# Перевірка 3
def test_wording_without_prefix():
    defects = validate.check_wording(make_spec(req(text="Проєкт повинен бути на Python.")))
    assert "формулювання" in kinds(defects)


def test_wording_system_prefix_is_allowed():
    assert validate.check_wording(make_spec(req(text="Система повинна зберігати тарифи."))) == []


# Перевірка 4
@pytest.mark.parametrize("word", ["зручно", "швидкий", "тощо", "інтуїтивно"])
def test_vague_words(word):
    defects = validate.check_vague_words(make_spec(req(text=f"ІС повинна {word} показувати тарифи.")))
    assert "неоднозначність" in kinds(defects)


# Перевірка 5
def test_performance_without_number():
    spec = make_spec(req(id="N1", type="performance", text="ІС повинна показувати пошук без затримок."))
    assert "неперевірюваність" in kinds(validate.check_performance_numbers(spec))


def test_performance_with_number_is_ok():
    spec = make_spec(req(id="N1", type="performance", text="ІС повинна показувати пошук за 2 с."))
    assert validate.check_performance_numbers(spec) == []


# Перевірка 6
@pytest.mark.parametrize("priority", [0, 6, "високий", None, True, 2.5])
def test_priority_out_of_range(priority):
    defects = validate.check_priorities(make_spec(req(priority=priority)))
    assert "пріоритет" in kinds(defects)


@pytest.mark.parametrize("priority", [1, 5])
def test_priority_boundaries_ok(priority):
    assert validate.check_priorities(make_spec(req(priority=priority))) == []


def test_constraint_without_priority_is_ok():
    spec = make_spec(req(id="C1", type="constraint", priority=None))
    assert validate.check_priorities(spec) == []


# Перевірка 7
def test_parent_missing():
    spec = make_spec(req(id="R3.1", parent="R3"))
    assert "нетрасованість" in kinds(validate.check_parents(spec))


def test_child_id_does_not_continue_parent():
    spec = make_spec(req(id="R1"), req(id="R4.1", parent="R1", text="ІС повинна зберігати дату."))
    assert "нетрасованість" in kinds(validate.check_parents(spec))


def test_subrequirement_without_parent_field():
    spec = make_spec(req(id="R1"), req(id="R1.1", text="ІС повинна зберігати дату."))
    assert "нетрасованість" in kinds(validate.check_parents(spec))


# Перевірка 8
def test_similar_texts():
    spec = make_spec(
        req(id="R1", text="ІС повинна забезпечувати створення бронювання автомобіля."),
        req(id="R2", text="ІС  повинна забезпечувати створення бронювань автомобіля."),
    )
    defects = validate.check_similar_texts(spec)
    assert [(d.req_id, d.kind) for d in defects] == [("R2", "надлишковість")]


def test_different_texts_are_ok():
    spec = make_spec(
        req(id="R1", text="ІС повинна забезпечувати створення бронювання автомобіля."),
        req(id="R2", text="ІС повинна розраховувати вартість оренди за тарифом."),
    )
    assert validate.check_similar_texts(spec) == []


# Власна перевірка 1
def test_implementation_words():
    spec = make_spec(req(text="ІС повинна зберігати тарифи в таблиці MySQL."))
    assert "деталі реалізації" in kinds(validate.check_implementation_words(spec))


def test_car_class_is_domain_term_not_implementation():
    spec = make_spec(req(text="ІС повинна показувати клас автомобіля."))
    assert validate.check_implementation_words(spec) == []


# Власна перевірка 2
def test_user_story_not_used_as_source():
    spec = make_spec(req(source="User Story US-01"), stories=("US-01", "US-02"))
    defects = validate.check_user_stories_used(spec)
    assert [d.req_id for d in defects] == ["US-02"]


# Власна перевірка 3
def test_constraint_with_priority():
    spec = make_spec(req(id="C1", type="constraint", priority=1))
    assert "пріоритет" in kinds(validate.check_constraints(spec))


def test_c_id_with_wrong_type():
    spec = make_spec(req(id="C2", type="operational"))
    assert "формат" in kinds(validate.check_constraints(spec))


# Цілі файли
def test_bad_srs_triggers_every_check():
    spec = load_specification(HERE / "bad_srs.yaml")
    for check in validate.CHECKS:
        assert check(spec), f"{check.__name__} не спрацювала на bad_srs.yaml"


def test_working_srs_has_no_defects():
    spec = load_specification(HERE / "srs.yaml")
    assert validate.validate(spec) == []


def test_exit_codes(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["validate.py", str(HERE / "srs.yaml")])
    assert validate.main() == 0
    monkeypatch.setattr("sys.argv", ["validate.py", str(HERE / "bad_srs.yaml")])
    assert validate.main() == 1
