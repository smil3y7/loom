# Loom — Dedup utility
# lib/dedup.py
#
# Ena Oneiro sanja lahko proizvede VEČ canonical zapisov (do 4: osnovna
# sanja / do 3 AI interpretacije / uporabnikov notes) — glej
# loom-extension mapAllToCanonical(). Vsi ti zapisi imajo IDENTIČEN
# `content`, razliko nosi samo `metadata.extras.oneiro_interpretation`.
# Ker embedding temelji izključno na title+content (_prepare_text v
# lib/embeddings.py), dobijo skoraj identičen vektor — brez deduplikacije
# bi se ista sanja pojavila 2-4x v iskalnih rezultatih in bi jo clustering
# skoraj zagotovo "odkril" kot lasten vzorec, čeprav gre samo za isto
# sanjo večkrat.
#
# Dedup se uporablja SAMO pri branju za search/clustering (LocalSearchIndex,
# ClusteringEngine) — embedding generacija in shranjevanje ostaneta
# nedotaknjena, vsak canonical entry dobi svoj pravi embedding. S tem se
# izognemo tveganju zapletanja embedding queue mehanike (retry/failed
# tracking); cena je nekaj odvečnega, poceni lokalnega računanja.
#
# Za vire brez tega pojava (browser_atlas, lab, oneiro sanje brez
# interpretacij) je vsak dream_id sam svoj reprezentant — funkcije so
# zanje no-op (1:1 grupiranje).

from lib.schema import CanonicalDream


def dedup_group_key(dream: CanonicalDream) -> str:
    """
    Ključ za grupiranje entryjev ki predstavljajo isto izvorno sanjo.

    Za Oneiro sanje z interpretacijami: skupni `extras.oneiro_id`
    (isti za vse variante iste sanje, nastavljen v extension
    mapToCanonical()). Za vse ostalo: dream_id sam.
    """
    extras = dream.metadata.extras if dream.metadata else {}
    oneiro_id = extras.get("oneiro_id") if extras else None
    if dream.source_app == "oneiro" and oneiro_id:
        return f"oneiro:{oneiro_id}"
    return dream.dream_id


def pick_representative(dreams: list[CanonicalDream]) -> CanonicalDream:
    """
    Med entryji ki delijo isti dedup_group_key izbere enega za
    prikaz/embedding v search/clustering rezultatih.

    Prioriteta:
    1. Entry brez interpretacije (`oneiro_interpretation_source` je None)
       — to je "najčistejša" reprezentacija same sanje, brez interpretacijske
       vsebine v extras.
    2. Sicer prvi po dream_id (deterministično in stabilno med runi —
       ne spremeni se glede na vrstni red iteracije po dict-u).
    """
    for d in dreams:
        extras = d.metadata.extras if d.metadata else {}
        if not (extras and extras.get("oneiro_interpretation_source")):
            return d
    return sorted(dreams, key=lambda d: d.dream_id)[0]


def compute_representative_ids(dreams_by_id: dict[str, CanonicalDream]) -> set[str]:
    """
    Vrne množico dream_id-jev ki so "reprezentanti" svoje dedup grupe —
    edini ki naj se pojavijo v search rezultatih in clustering vhodu.

    Za vire/sanje brez multipliciranja je vsak dream_id sam svoj
    reprezentant (množica bo vsebovala vse ključe dreams_by_id nespremenjeno).
    """
    groups: dict[str, list[CanonicalDream]] = {}
    for dream in dreams_by_id.values():
        key = dedup_group_key(dream)
        groups.setdefault(key, []).append(dream)

    representative_ids = set()
    for group_dreams in groups.values():
        rep = pick_representative(group_dreams)
        representative_ids.add(rep.dream_id)
    return representative_ids
