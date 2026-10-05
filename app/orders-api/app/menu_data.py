"""Seed data for the canteen menu (prices in PLN)."""
from __future__ import annotations

# (name, category, price_pln)
SEED_MENU: list[tuple[str, str, float]] = [
    ("Rosół z makaronem", "zupy", 9.50),
    ("Żurek staropolski", "zupy", 12.00),
    ("Barszcz czerwony z krokietem", "zupy", 13.50),
    ("Pomidorowa z ryżem", "zupy", 9.00),
    ("Kotlet schabowy z ziemniakami", "dania główne", 24.00),
    ("Pierogi ruskie (8 szt.)", "dania główne", 19.00),
    ("Pierogi z mięsem (8 szt.)", "dania główne", 21.00),
    ("Gołąbki w sosie pomidorowym", "dania główne", 22.50),
    ("Bigos staropolski", "dania główne", 20.00),
    ("Placki ziemniaczane ze śmietaną", "dania główne", 18.50),
    ("Kotlet mielony z kaszą", "dania główne", 21.50),
    ("Naleśniki z serem", "dania główne", 16.00),
    ("Ryba po grecku", "dania główne", 23.00),
    ("Sałatka grecka", "sałatki", 15.00),
    ("Surówka z białej kapusty", "dodatki", 5.00),
    ("Kompot owocowy", "napoje", 4.50),
    ("Woda mineralna 0,5 l", "napoje", 4.00),
    ("Sok jabłkowy", "napoje", 5.50),
    ("Sernik domowy", "desery", 11.00),
    ("Szarlotka na ciepło", "desery", 12.00),
]
