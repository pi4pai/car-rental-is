"""Тест відповідності моделі та коду (ЛР 2, завдання 3).

Читає classification.csv і інтроспекцією перевіряє domain.py: для кожного класу
моделі є клас Python, для кожного атрибута — поле, для наслідування — успадкування.
"""
import dataclasses
from pathlib import Path

import pytest

import domain
from review import load_classification

ROWS = load_classification(Path(__file__).parent / "classification.csv")

CLASS_NAMES = {
    "Автопарк": "Fleet",
    "Автомобіль": "Car",
    "Тарифний план": "Tariff",
    "Клієнт": "Client",
    "Бронювання": "Booking",
    "Оренда": "Rental",
    "Працівник": "Employee",
    "Менеджер": "Manager",
    "Адміністратор": "Administrator",
    "Акт стану": "ConditionReport",
    "Платіж": "Payment",
}

ATTRIBUTE_NAMES = {
    ("Автопарк", "назва"): "name",
    ("Автопарк", "адреса"): "address",
    ("Автомобіль", "державний номер"): "plate_number",
    ("Автомобіль", "марка"): "brand",
    ("Автомобіль", "модель"): "model",
    ("Автомобіль", "рік випуску"): "year",
    ("Автомобіль", "пробіг"): "mileage",
    ("Автомобіль", "статус"): "status",
    ("Тарифний план", "назва"): "name",
    ("Тарифний план", "вартість за добу"): "daily_rate",
    ("Тарифний план", "штраф за добу прострочення"): "late_fee_per_day",
    ("Тарифний план", "дата початку дії"): "valid_from",
    ("Клієнт", "ПІБ"): "full_name",
    ("Клієнт", "телефон"): "phone",
    ("Клієнт", "електронна пошта"): "email",
    ("Клієнт", "номер посвідчення водія"): "license_number",
    ("Бронювання", "номер"): "number",
    ("Бронювання", "дата початку"): "start_date",
    ("Бронювання", "дата завершення"): "end_date",
    ("Бронювання", "попередня вартість"): "estimated_cost",
    ("Бронювання", "статус"): "status",
    ("Оренда", "номер договору"): "contract_number",
    ("Оренда", "дата видачі"): "issue_date",
    ("Оренда", "планова дата повернення"): "planned_return_date",
    ("Оренда", "фактична дата повернення"): "actual_return_date",
    ("Оренда", "остаточна вартість"): "final_cost",
    ("Працівник", "табельний номер"): "personnel_number",
    ("Працівник", "ПІБ"): "full_name",
    ("Працівник", "телефон"): "phone",
    ("Менеджер", "пункт видачі"): "pickup_point",
    ("Адміністратор", "дата призначення"): "appointment_date",
    ("Акт стану", "тип акта"): "report_type",
    ("Акт стану", "дата складання"): "report_date",
    ("Акт стану", "показник пробігу"): "mileage",
    ("Акт стану", "рівень пального"): "fuel_level",
    ("Акт стану", "опис пошкоджень"): "damage_description",
    ("Платіж", "сума"): "amount",
    ("Платіж", "дата"): "payment_date",
    ("Платіж", "спосіб оплати"): "method",
}

CLASSES = [r for r in ROWS if r["code"] in {"C", "AC"}]
ATTRIBUTES = [r for r in ROWS if r["code"] == "A"]
INHERITANCE = [r for r in ROWS if r["code"] == "I"]
ASSOCIATION_CLASSES = [r for r in ROWS if r["code"] == "AC"]


def python_class(model_name: str):
    assert model_name in CLASS_NAMES, f"немає відповідності для класу «{model_name}»"
    name = CLASS_NAMES[model_name]
    assert hasattr(domain, name), f"у domain.py немає класу {name} («{model_name}»)"
    return getattr(domain, name)


def field_names(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


@pytest.mark.parametrize("row", CLASSES, ids=lambda r: r["name"])
def test_model_class_exists_as_dataclass(row):
    assert dataclasses.is_dataclass(python_class(row["name"]))


@pytest.mark.parametrize("row", ATTRIBUTES, ids=lambda r: f"{r['owner']}.{r['name']}")
def test_model_attribute_is_a_field(row):
    key = (row["owner"], row["name"])
    assert key in ATTRIBUTE_NAMES, f"немає відповідності для атрибута {key}"
    cls = python_class(row["owner"])
    assert ATTRIBUTE_NAMES[key] in field_names(cls), f"{cls.__name__} не має поля {ATTRIBUTE_NAMES[key]}"


@pytest.mark.parametrize("row", INHERITANCE, ids=lambda r: r["target"])
def test_model_inheritance_is_subclass(row):
    assert issubclass(python_class(row["target"]), python_class(row["owner"]))


@pytest.mark.parametrize("row", ASSOCIATION_CLASSES, ids=lambda r: r["name"])
def test_association_class_refers_to_both_ends(row):
    fields = {f.name: f.type for f in dataclasses.fields(python_class(row["name"]))}
    for end in (row["owner"], row["target"]):
        assert python_class(end) in fields.values(), f"{row['name']}: немає посилання на {end}"


def test_every_mapping_entry_is_used():
    """Зайвий запис у словнику означає, що атрибут прибрали з моделі, а з коду ні."""
    used = {(r["owner"], r["name"]) for r in ATTRIBUTES}
    assert set(ATTRIBUTE_NAMES) == used
