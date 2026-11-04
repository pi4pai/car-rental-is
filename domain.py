"""Доменна модель ІС прокату автомобілів (ЛР 2, завдання 3).

Кратності й інваріанти моделі забезпечуються методами класів: їх порушення
спричиняє виняток DomainError з поясненням.
"""
from dataclasses import dataclass, field
from datetime import date

MAX_ACTIVE_BOOKINGS = 3
MAX_CONDITION_REPORTS = 2

CAR_AVAILABLE = "доступний"
CAR_BOOKED = "заброньований"
CAR_RENTED = "в оренді"
CAR_SERVICE = "на обслуговуванні"
CAR_STATUSES = {CAR_AVAILABLE, CAR_BOOKED, CAR_RENTED, CAR_SERVICE}

BOOKING_ACTIVE = "активне"
BOOKING_CANCELLED = "скасоване"
BOOKING_COMPLETED = "завершене"

REPORT_ISSUE = "видача"
REPORT_RETURN = "повернення"
PAYMENT_METHODS = {"готівка", "банківська картка"}


class DomainError(Exception):
    """Порушення кратності або інваріанта предметної області."""


@dataclass(eq=False)
class Employee:
    personnel_number: str
    full_name: str
    phone: str


@dataclass(eq=False)
class Manager(Employee):
    pickup_point: str
    rentals: list["Rental"] = field(default_factory=list, repr=False)
    reports: list["ConditionReport"] = field(default_factory=list, repr=False)


@dataclass(eq=False)
class Administrator(Employee):
    appointment_date: date
    fleets: list["Fleet"] = field(default_factory=list, repr=False)
    tariffs: list["Tariff"] = field(default_factory=list, repr=False)


@dataclass(eq=False)
class Tariff:
    name: str
    daily_rate: float
    late_fee_per_day: float
    valid_from: date
    cars: list["Car"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.daily_rate <= 0:
            raise DomainError(f"Тариф «{self.name}»: вартість за добу має бути більшою за 0")
        if self.late_fee_per_day < 0:
            raise DomainError(f"Тариф «{self.name}»: штраф не може бути від'ємним")


@dataclass(eq=False)
class Fleet:
    name: str
    address: str
    cars: list["Car"] = field(default_factory=list, repr=False)

    def add_car(self, car: "Car") -> None:
        """Автомобіль належить рівно одному автопарку (кратність 1;0..*)."""
        if car.fleet is not None:
            raise DomainError(f"Автомобіль {car.plate_number} уже належить автопарку «{car.fleet.name}»")
        if any(c.plate_number == car.plate_number for c in self.cars):
            raise DomainError(f"В автопарку вже є автомобіль з номером {car.plate_number}")
        car.fleet = self
        self.cars.append(car)


@dataclass(eq=False)
class Car:
    plate_number: str
    brand: str
    model: str
    year: int
    mileage: int
    tariff: Tariff
    status: str = CAR_AVAILABLE
    fleet: Fleet | None = field(default=None, repr=False)
    bookings: list["Booking"] = field(default_factory=list, repr=False)
    rentals: list["Rental"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        # Кратність «тарифікується за»: рівно один тарифний план
        if self.tariff is None:
            raise DomainError(f"Автомобіль {self.plate_number} повинен мати тарифний план")
        if self.status not in CAR_STATUSES:
            raise DomainError(f"Недопустимий статус автомобіля: {self.status}")
        self.tariff.cars.append(self)

    def active_rental(self) -> "Rental | None":
        return next((r for r in self.rentals if r.is_active), None)

    def is_free(self, start: date, end: date, ignore: "Booking | None" = None) -> bool:
        """Період не перетинається з іншими активними бронюваннями."""
        return not any(
            b is not ignore and b.is_active and b.overlaps(start, end)
            for b in self.bookings
        )


@dataclass(eq=False)
class Client:
    full_name: str
    phone: str
    email: str
    license_number: str
    bookings: list["Booking"] = field(default_factory=list, repr=False)
    rentals: list["Rental"] = field(default_factory=list, repr=False)

    def active_bookings(self) -> list["Booking"]:
        return [b for b in self.bookings if b.is_active]


@dataclass(eq=False)
class Booking:
    number: str
    client: Client
    car: Car
    start_date: date
    end_date: date
    estimated_cost: float = 0.0
    status: str = BOOKING_ACTIVE

    @classmethod
    def create(cls, number: str, client: Client, car: Car, start_date: date, end_date: date) -> "Booking":
        """Створює бронювання, перевіряючи всі правила предметної області."""
        if end_date <= start_date:
            raise DomainError("Дата завершення має бути пізнішою за дату початку: мінімальна оренда – одна доба")
        if len(client.active_bookings()) >= MAX_ACTIVE_BOOKINGS:
            raise DomainError(f"Клієнт уже має {MAX_ACTIVE_BOOKINGS} активних бронювання: це максимум")
        if not car.is_free(start_date, end_date):
            raise DomainError(f"Автомобіль {car.plate_number} уже заброньовано на цей період")
        days = (end_date - start_date).days
        booking = cls(number, client, car, start_date, end_date, days * car.tariff.daily_rate)
        client.bookings.append(booking)
        car.bookings.append(booking)
        return booking

    @property
    def is_active(self) -> bool:
        return self.status == BOOKING_ACTIVE

    def overlaps(self, start: date, end: date) -> bool:
        return self.start_date < end and start < self.end_date

    def cancel(self) -> None:
        if not self.is_active:
            raise DomainError(f"Бронювання {self.number} уже не активне")
        self.status = BOOKING_CANCELLED


@dataclass(eq=False)
class ConditionReport:
    report_type: str
    report_date: date
    mileage: int
    fuel_level: int
    damage_description: str
    manager: Manager = field(repr=False)

    def __post_init__(self) -> None:
        if self.report_type not in {REPORT_ISSUE, REPORT_RETURN}:
            raise DomainError(f"Недопустимий тип акта: {self.report_type}")
        if not 0 <= self.fuel_level <= 100:
            raise DomainError("Рівень пального вказують у відсотках від 0 до 100")
        self.manager.reports.append(self)


@dataclass(eq=False)
class Payment:
    amount: float
    payment_date: date
    method: str

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise DomainError("Сума платежу має бути більшою за 0")
        if self.method not in PAYMENT_METHODS:
            raise DomainError(f"Недопустимий спосіб оплати: {self.method}")


@dataclass(eq=False)
class Rental:
    """Асоціативний клас зв'язку «Клієнт орендує Автомобіль»."""
    contract_number: str
    client: Client
    car: Car
    manager: Manager
    issue_date: date
    planned_return_date: date
    actual_return_date: date | None = None
    final_cost: float | None = None
    reports: list[ConditionReport] = field(default_factory=list, repr=False)
    payments: list[Payment] = field(default_factory=list, repr=False)

    @classmethod
    def issue(cls, contract_number: str, client: Client, car: Car, manager: Manager,
              issue_date: date, planned_return_date: date, report: ConditionReport) -> "Rental":
        """Видача автомобіля: один автомобіль – не більше однієї активної оренди."""
        if car.active_rental() is not None:
            raise DomainError(f"Автомобіль {car.plate_number} уже перебуває в активній оренді")
        if car.status == CAR_SERVICE:
            raise DomainError(f"Автомобіль {car.plate_number} на обслуговуванні")
        if planned_return_date <= issue_date:
            raise DomainError("Планова дата повернення має бути пізнішою за дату видачі: мінімум одна доба")
        rental = cls(contract_number, client, car, manager, issue_date, planned_return_date)
        rental.add_report(report)
        client.rentals.append(rental)
        car.rentals.append(rental)
        manager.rentals.append(rental)
        car.status = CAR_RENTED
        return rental

    @property
    def is_active(self) -> bool:
        return self.actual_return_date is None

    def add_report(self, report: ConditionReport) -> None:
        """Оренда містить не більше двох актів: по одному кожного типу (кратність 1;0..2)."""
        if len(self.reports) >= MAX_CONDITION_REPORTS:
            raise DomainError(f"Оренда {self.contract_number}: не більше {MAX_CONDITION_REPORTS} актів стану")
        if any(r.report_type == report.report_type for r in self.reports):
            raise DomainError(f"Оренда {self.contract_number}: акт типу «{report.report_type}» уже є")
        self.reports.append(report)

    def add_payment(self, payment: Payment) -> None:
        self.payments.append(payment)

    def calculate_cost(self, return_date: date) -> float:
        """Вартість = оплачені доби за тарифом + штраф за кожну добу прострочення."""
        if return_date < self.issue_date:
            raise DomainError("Дата повернення не може бути раніше за дату видачі")
        tariff = self.car.tariff
        days = max((return_date - self.issue_date).days, 1)
        late_days = max((return_date - self.planned_return_date).days, 0)
        return days * tariff.daily_rate + late_days * tariff.late_fee_per_day

    def close(self, return_date: date, report: ConditionReport) -> float:
        """Повернення автомобіля: завершує оренду й повертає остаточну вартість."""
        if not self.is_active:
            raise DomainError(f"Оренду {self.contract_number} уже завершено")
        cost = self.calculate_cost(return_date)
        self.add_report(report)
        self.actual_return_date = return_date
        self.final_cost = cost
        self.car.mileage = report.mileage
        self.car.status = CAR_AVAILABLE
        return cost
