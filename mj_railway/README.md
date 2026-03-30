# Magazyn Jaj — starter MVP (Django)

To jest starter aplikacji webowej do zarządzania magazynem jaj.

## Funkcje w tej wersji
- logowanie użytkownika
- klienci
- przyjęcia dzienne z datą zniesienia
- sprzedaż z pozycjami, ceną za skrzynkę i numerem faktury
- stłuczki informacyjne
- korekty magazynowe
- dashboard ze stanami i dzisiejszą sprzedażą / produkcją
- historia ruchów magazynowych
- blokada sprzedaży poniżej zera

## Założenia biznesowe
- 1 skrzynka = 12 wkładek
- 1 wkładka = 30 jaj
- rozmiary: 3, 2B, 2A, 1B, 1A, S, SS
- stłuczki nie wpływają na stan magazynu
- cena wpisywana jest za skrzynkę
- numer faktury jest unikalny

## Szybki start
```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Logowanie
- panel logowania: `/accounts/login/`
- dashboard: `/`

## Co można rozbudować później
- eksport CSV / Excel
- lepszy front
- pełny podgląd na telefonie
- raporty miesięczne
- płatności częściowe
