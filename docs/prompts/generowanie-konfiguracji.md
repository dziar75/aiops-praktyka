# Generowanie konfiguracji

Skopiuj blok niżej i uzupełnij pola `<...>`. Dane wklejaj przycięte i zredagowane (bez haseł, kluczy, danych osobowych).

```text
Wygeneruj <typ zasobu / moduł>.
Wersje: <Kubernetes / Terraform / provider / Helm>.
Wymagania: <co ma robić>.
Ograniczenia: sekrety tylko z <Secret / menedżer sekretów>, nigdy jawnie; przypięte wersje obrazów
i modułów; resources.requests i limits; <konwencje nazw i etykiet zespołu>.
Format: tylko <YAML / HCL>, bez komentarza. Na końcu, w osobnym bloku: komendy walidacji
(<kubeconform / terraform validate / helm lint>).
```
