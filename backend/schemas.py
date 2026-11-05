from typing import Optional
import re
from pydantic import BaseModel, field_validator, model_validator

TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$|^24:00$")


class Item(BaseModel):
    id: str = ""
    name: str
    category: Optional[str] = None
    tags: list[str] = []
    description: Optional[str] = None
    price_cents: Optional[int] = None
    availability: str = "unknown"  # available | unavailable | unknown
    allergens: Optional[list[str]] = None
    source_ids: list[str] = []


class FAQ(BaseModel):
    question: str
    answer: str
    source_ids: list[str] = []


class Slot(BaseModel):
    open: str
    close: str  # "24:00" = minuit ; close < open = ferme après minuit

    @field_validator("open", "close")
    @classmethod
    def _valid_time(cls, v: str) -> str:
        if not TIME_RE.match(v):
            raise ValueError("Heure invalide (format HH:MM)")
        return v

    @model_validator(mode="after")
    def _check(self):
        if self.open == "24:00" or self.open == self.close:
            raise ValueError("Créneau invalide")
        return self


class DayHours(BaseModel):
    day: int  # 0 = lundi ... 6 = dimanche
    slots: list[Slot] = []

    @field_validator("day")
    @classmethod
    def _valid_day(cls, v: int) -> int:
        if not 0 <= v <= 6:
            raise ValueError("Jour invalide (0 à 6)")
        return v


class OpeningHours(BaseModel):
    source: str = "unknown"  # google | website | merchant | unknown
    days: list[DayHours] = []
    note: Optional[str] = None  # exceptions, jours fériés...

    @model_validator(mode="after")
    def _full_week(self):
        if self.days:
            by_day = {d.day: d for d in self.days}
            self.days = [by_day.get(i, DayHours(day=i)) for i in range(7)]
        return self


class Knowledge(BaseModel):
    business_name: Optional[str] = None
    currency: str = "EUR"
    description: Optional[str] = None
    opening_hours_text: Optional[str] = None
    opening_hours: Optional[OpeningHours] = None
    ordering_enabled: bool = True
    fulfillment_modes: list[str] = ["pickup"]
    items: list[Item] = []
    faq: list[FAQ] = []
    notes: list[str] = []