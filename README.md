# Burger VPS Demo v4

Nowości:
- klient przy aktywnej sesji widzi status własnych zamówień
- kelner widzi status stolików: nowe / w przygotowaniu / gotowe
- nowocześniejszy design w stylu food app 2026
- admin, KDS, kelner i QR nadal działają

## Start
```bash
sudo docker compose down
sudo docker compose build --no-cache
sudo docker compose up -d
```

## QR
```bash
sudo docker compose exec burger-app python generate_qr.py
```

## Widoki
- `/` menu klienta + aktywne zamówienia i ich status
- `/admin`
- `/kds`
- `/waiter`


## Admin QR
W adminie miniatury QR są widoczne obok linków. Kliknięcie miniatury otwiera powiększenie.


## Obrazy produktów
W tej wersji strona używa zapisanych obrazów:
- classic_burger.png
- cheese_burger.png
- fries.png
- cola.png

Są już w katalogu `static/img` i pokazują się na stronie menu.

## QR automatycznie
QR generują się automatycznie przy starcie aplikacji. Nie musisz już uruchamiać `generate_qr.py`, chyba że chcesz wygenerować je ręcznie ponownie.


## v7
- klient widzi komunikat: siedzi przy stoliku X
- klient widzi także zamówienia zamknięte jako zrealizowane / zamknięte
- dodano ketchup i sos z obrazkami
- layout dopracowany pod telefon i tablet, z mniejszymi obrazkami na mobile
