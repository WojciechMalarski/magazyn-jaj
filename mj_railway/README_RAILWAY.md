# Magazyn Jaj – wdrożenie na Railway

Ta paczka jest przygotowana pod wdrożenie aplikacji Django na Railway z PostgreSQL.

## Co już jest dodane
- obsługa PostgreSQL przez zmienne środowiskowe Railway
- WhiteNoise do plików statycznych
- Gunicorn jako serwer produkcyjny
- `railway.json` z komendą startową
- przykładowy plik `.env.railway.example`

## Krok 1 – wrzuć kod na GitHub
1. Rozpakuj projekt.
2. Utwórz nowe repozytorium na GitHub.
3. Wgraj cały folder projektu do repozytorium.

## Krok 2 – utwórz projekt na Railway
1. Zaloguj się do Railway.
2. Wybierz `New Project`.
3. Wybierz `Deploy from GitHub repo`.
4. Wskaż repozytorium z tym projektem.

## Krok 3 – dodaj bazę PostgreSQL
1. Na canvas projektu kliknij `Create`.
2. Wybierz `Database` -> `Add PostgreSQL`.

## Krok 4 – ustaw zmienne środowiskowe aplikacji
W usłudze aplikacji wejdź w `Variables` i dodaj:

```
SECRET_KEY=zmien_na_dlugi_losowy_klucz
DEBUG=False
ALLOWED_HOSTS=twoj-serwis.up.railway.app
CSRF_TRUSTED_ORIGINS=https://twoj-serwis.up.railway.app
DB_SSL_REQUIRED=true
PGDATABASE=${{Postgres.PGDATABASE}}
PGUSER=${{Postgres.PGUSER}}
PGPASSWORD=${{Postgres.PGPASSWORD}}
PGHOST=${{Postgres.PGHOST}}
PGPORT=${{Postgres.PGPORT}}
```

## Krok 5 – publiczny adres
1. Wejdź w `Settings` -> `Networking`.
2. Kliknij `Generate Domain`.
3. Skopiuj adres `.up.railway.app`.
4. Wróć do `Variables` i uzupełnij:
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
5. Zrób redeploy.

## Krok 6 – pierwsze logowanie
Ponieważ aplikacja ma logowanie Django, po wdrożeniu utwórz superusera przez shell Railway:

```bash
python manage.py createsuperuser
```

Możesz to zrobić z terminala Railway lub przez lokalny CLI po podłączeniu projektu.

## Uwaga
Przy każdym starcie Railway wykona:
- `python manage.py migrate`
- `python manage.py collectstatic --noinput`
- `gunicorn ...`

To wystarczy na start dla jednej aplikacji.
