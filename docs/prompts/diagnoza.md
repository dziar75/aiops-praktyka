# Diagnoza awarii

Skopiuj blok niżej i uzupełnij pola `<...>`. Dane wklejaj przycięte i zredagowane (bez haseł, kluczy, danych osobowych).

```text
Jesteś SRE. Środowisko: <Kubernetes/EKS wersja, namespace, komponent i jego wersja>.
Objaw: <co widać, od kiedy, co się zmieniło ostatnio>.
Dane:
<wynik describe / logs --previous / events — przycięty i zredagowany>
Już sprawdziłem: <co wykluczone i jak>.
Zadanie: podaj 3 najbardziej prawdopodobne hipotezy, od najbardziej prawdopodobnej.
Ograniczenia: proponuj tylko komendy read-only. Nie proponuj jeszcze poprawki.
Jeśli brakuje danych, napisz, jakiej komendy potrzebujesz, zamiast zgadywać.
Format: tabela | hipoteza | dowód z danych powyżej | komenda weryfikująca |.
```
