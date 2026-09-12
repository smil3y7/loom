"""
Loom
API Token — pairing secret za Loom Sync extension

Ta modul rešuje en specifičen problem: `/api/ingest` (kamor Loom Sync
extension v "api" delivery mode pošlje dešifrirane sanje) prej ni imel
NOBENE avtentikacije — kombinirano z odprtim CORS (`allow_origins=["*"]`)
je to pomenilo, da bi lahko katerakoli spletna stran v istem brskalniku
vrinila poljubne "sanje" v lokalni arhiv.

Zaščita je namerno dvoplastna (obe plasti neodvisno zadostni):
  1. CORS zaklep na znane origine (glej api/index.py) — brskalnik ne
     pošlje dejanske zahteve, če origin ni na seznamu (preflight pade).
  2. Ta token — obramba v globino, za primer napačne CORS konfiguracije,
     bodočih browser bugov, ali dostopa mimo brskalnika (npr. curl).

Token se generira lokalno ob prvem dostopu in shrani v
`{storage_path}/api_token` (navadna tekstovna datoteka, ne v git). Loom UI
Settings stran ga prikaže uporabniku za ročno kopiranje v extension popup
(glej loom-extension/popup.js) — enkraten "pairing" korak, ne ponavljajoč
se ob vsakem zagonu.
"""

import os
import secrets


def get_or_create_token(storage_path: str) -> str:
    """
    Vrne obstoječi token, ali generira novega ob prvem klicu.

    `secrets.token_urlsafe(32)` — kriptografsko varen naključen niz
    (~256 bit entropije), URL-safe alfabet (primeren za copy-paste v UI
    polje in HTTP header brez escapinga).
    """
    os.makedirs(storage_path, exist_ok=True)
    token_path = os.path.join(storage_path, "api_token")

    try:
        with open(token_path) as f:
            existing = f.read().strip()
            if existing:
                return existing
    except FileNotFoundError:
        pass

    new_token = secrets.token_urlsafe(32)
    with open(token_path, "w") as f:
        f.write(new_token)
    return new_token


def verify_token(provided: str, storage_path: str) -> bool:
    """
    Primerja podan token s shranjenim, časovno konstantno (`secrets.compare_digest`)
    — preprečuje timing attack, kjer bi napadalec iz razlike v odzivnem času
    sklepal, koliko začetnih znakov tokena je pravilnih. Za lokalen single-user
    tool je to sicer nizko-tvegano, ampak `compare_digest` ne stane nič več kot
    `==`, zato ni razloga za bližnjico.
    """
    if not provided:
        return False
    expected = get_or_create_token(storage_path)
    # compare_digest na str zahteva ASCII-only vhod (sicer TypeError) — token
    # sam je vedno ASCII (urlsafe base64), ampak `provided` pride iz HTTP
    # headerja od zunaj in bi teoretično lahko vseboval karkoli. Primerjaj
    # kot bytes, da napačen/zloben vhod vrne False namesto da crasha.
    return secrets.compare_digest(provided.encode("utf-8", "replace"), expected.encode("utf-8"))


def regenerate_token(storage_path: str) -> str:
    """
    Prekliče star token in ustvari novega — uporabno, če je token
    kompromitiran, ali če uporabnik želi izklopiti dostop starim/pozabljenim
    extension instalacijam. Klicoč mora vedeti, da bo obstoječi pairing v
    extensionu po tem neveljaven, dokler uporabnik ne prekopira novega.
    """
    os.makedirs(storage_path, exist_ok=True)
    token_path = os.path.join(storage_path, "api_token")
    new_token = secrets.token_urlsafe(32)
    with open(token_path, "w") as f:
        f.write(new_token)
    return new_token
