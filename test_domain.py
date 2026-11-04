"""Тести доменної моделі (ЛР 2, завдання 3). Запуск: pytest test_domain.py -v"""
from datetime import date

import pytest

from domain import (
    CAR_AVAILABLE,
    CAR_RENTED,
    CAR_SERVICE,
    REPORT_ISSUE,
    REPORT_RETURN,
    Administrator,
    Booking,
    Car,
    Client,
    ConditionReport,
    DomainError,
    Fleet,
    Manager,
    Payment,
    Rental,
    Tariff,
)

START = date(2026, 11, 10)
END = date(2026, 11, 13)


@pytest.fixture
def tariff():
    return Tariff("Економ", 1000.0, 200.0, date(2026, 1, 1))


@pytest.fixture
def car(tariff):
    return Car("ВХ1234АА", "Skoda", "Fabia", 2022, 40000, tariff)


@pytest.fixture
def client():
    return Client("Іваненко Іван", "+380670000001", "ivan@example.com", "ВХА123456")


@pytest.fixture
def manager():
    return Manager("M-1", "Петренко Олена", "+380670000002", "Центральний")


def issue_report(manager, mileage=40000):
    return ConditionReport(REPORT_ISSUE, START, mileage, 100, "немає", manager)


def return_report(manager, mileage=40500):
    return ConditionReport(REPORT_RETURN, END, mileage, 80, "немає", manager)


def issue_rental(client, car, manager):
    return Rental.issue("D-1", client, car, manager, START, END, issue_report(manager))


# --- нормальні сценарії ---

def test_booking_is_linked_to_client_and_car(client, car):
    booking = Booking.create("B-1", client, car, START, END)
    assert booking in client.bookings and booking in car.bookings
    assert booking.estimated_cost == 3000.0


def test_rental_issue_changes_car_status(client, car, manager):
    rental = issue_rental(client, car, manager)
    assert car.status == CAR_RENTED
    assert car.active_rental() is rental


def test_return_on_time_costs_only_days(client, car, manager):
    rental = issue_rental(client, car, manager)
    assert rental.close(END, return_report(manager)) == 3000.0
    assert car.status == CAR_AVAILABLE
    assert car.mileage == 40500


def test_late_return_adds_fee(client, car, manager):
    rental = issue_rental(client, car, manager)
    # 5 діб за тарифом 1000 + 2 доби прострочення по 200
    assert rental.close(date(2026, 11, 15), return_report(manager)) == 5400.0


def test_cancelled_booking_frees_period(client, car):
    Booking.create("B-1", client, car, START, END).cancel()
    assert Booking.create("B-2", client, car, START, END).is_active


def test_administrator_is_employee_with_own_field():
    admin = Administrator("A-1", "Коваль Ігор", "+380670000003", date(2025, 3, 1))
    assert isinstance(admin.fleets, list) and admin.full_name == "Коваль Ігор"


# --- порушення кратностей та інваріантів ---

def test_car_requires_tariff():
    with pytest.raises(DomainError, match="тарифний план"):
        Car("ВХ1234АА", "Skoda", "Fabia", 2022, 40000, None)


def test_car_belongs_to_one_fleet(car):
    Fleet("Центр", "вул. Свободи, 1").add_car(car)
    with pytest.raises(DomainError, match="уже належить"):
        Fleet("Захід", "вул. Львівська, 2").add_car(car)


def test_client_max_three_active_bookings(client, tariff):
    for i in range(3):
        other = Car(f"ВХ000{i}АА", "Skoda", "Fabia", 2022, 1000, tariff)
        Booking.create(f"B-{i}", client, other, START, END)
    extra = Car("ВХ9999АА", "Skoda", "Fabia", 2022, 1000, tariff)
    with pytest.raises(DomainError, match="максимум"):
        Booking.create("B-4", client, extra, START, END)


def test_overlapping_booking_is_rejected(client, car):
    Booking.create("B-1", client, car, START, END)
    other = Client("Сидоренко Анна", "+380670000004", "anna@example.com", "ВХА654321")
    with pytest.raises(DomainError, match="уже заброньовано"):
        Booking.create("B-2", other, car, date(2026, 11, 12), date(2026, 11, 14))


def test_adjacent_booking_is_allowed(client, car):
    Booking.create("B-1", client, car, START, END)
    assert Booking.create("B-2", client, car, END, date(2026, 11, 14)).is_active


def test_booking_minimum_one_day(client, car):
    with pytest.raises(DomainError, match="одна доба"):
        Booking.create("B-1", client, car, START, START)


def test_car_cannot_be_in_two_active_rentals(client, car, manager):
    issue_rental(client, car, manager)
    with pytest.raises(DomainError, match="активній оренді"):
        Rental.issue("D-2", client, car, manager, START, END, issue_report(manager))


def test_car_in_service_cannot_be_issued(client, car, manager):
    car.status = CAR_SERVICE
    with pytest.raises(DomainError, match="на обслуговуванні"):
        issue_rental(client, car, manager)


def test_rental_at_most_two_reports(client, car, manager):
    rental = issue_rental(client, car, manager)
    rental.add_report(return_report(manager))
    with pytest.raises(DomainError, match="не більше 2"):
        rental.add_report(return_report(manager))


def test_rental_one_report_of_each_type(client, car, manager):
    rental = issue_rental(client, car, manager)
    with pytest.raises(DomainError, match="уже є"):
        rental.add_report(issue_report(manager))


def test_closed_rental_cannot_be_closed_again(client, car, manager):
    rental = issue_rental(client, car, manager)
    rental.close(END, return_report(manager))
    with pytest.raises(DomainError, match="уже завершено"):
        rental.close(END, return_report(manager))


@pytest.mark.parametrize("rate", [0, -100])
def test_tariff_rate_must_be_positive(rate):
    with pytest.raises(DomainError, match="більшою за 0"):
        Tariff("Економ", rate, 0, START)


def test_payment_amount_must_be_positive():
    with pytest.raises(DomainError, match="більшою за 0"):
        Payment(0, START, "готівка")


def test_payment_method_is_checked():
    with pytest.raises(DomainError, match="спосіб оплати"):
        Payment(100, START, "криптовалюта")
