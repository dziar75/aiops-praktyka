# Grupowanie alertów w incydenty

Skopiuj blok niżej. Plik `alerty.json` pobierz z Grafany (Explore → Loki, `{container="alert-log"} | json`, Download). Etykiety alertów i godziny nie zawierają sekretów, ale zanim wkleisz, sprawdź, co wklejasz.

```text
W pliku alerty.json są powiadomienia Alertmanagera z weekendu (jedna linia JSON na powiadomienie).
Pogrupuj je w incydenty: alerty z tego samego okna czasu i o powiązanej przyczynie to jeden incydent.
Dla każdego incydentu podaj: od–do, nazwy alertów, priorytet P1–P3 z uzasadnieniem.
Osobno wypisz alerty, które wyglądają na szum, i zaproponuj, co z nimi zrobić (wyciszyć, usunąć regułę, zmienić severity), z uzasadnieniem.
Nie zgaduj przyczyn, których nie widać w danych.
Format: tabela markdown.
```
