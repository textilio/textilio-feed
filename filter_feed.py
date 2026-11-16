#!/usr/bin/env python3
"""
Textilio – zmenšení Google feedu.

Z každé skupiny produktu (g:item_group_id) a barvy (g:color) ponechá jen
jednu položku – preferovanou velikost (M, 122/134, 6 měs. ...).
Ostatní atributy zůstávají beze změny.

Použití: python filter_feed.py vstup.xml vystup.xml.gz
"""
import gzip
import sys
import xml.etree.ElementTree as ET

G = "{http://base.google.com/ns/1.0}"

# Pořadí preferovaných velikostí (první nalezená vyhrává).
PREFERRED = [
    "M", "L", "S",                      # dospělí
    "134", "122", "146", "110", "158",  # děti (výška v cm)
    "6 měs", "6 měs.", "6", "9 měs", "9 měs.", "3 měs", "3 měs.",  # body
]


def norm(s):
    return (s or "").strip().lower()


PREF_INDEX = {norm(s): i for i, s in enumerate(PREFERRED)}


def text(item, tag):
    el = item.find(G + tag)
    return el.text.strip() if el is not None and el.text else ""


def size_rank(size, order_in_group):
    s = norm(size)
    # Sady mají např. "M / 122" – rozhoduje první (dospělá) velikost.
    first = s.split("/")[0].strip()
    if first in PREF_INDEX:
        return (0, PREF_INDEX[first])
    return (1, order_in_group)


def choose(path):
    """1. průchod: pro každou dvojici (skupina, barva) vybere jedno ID."""
    best = {}   # key -> (rank, id)
    counts = {}
    total = 0
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != "item":
            continue
        total += 1
        gid = text(el, "item_group_id") or text(el, "id")
        key = (gid, norm(text(el, "color")))
        n = counts.get(key, 0)
        counts[key] = n + 1
        rank = size_rank(text(el, "size"), n)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, text(el, "id"))
        el.clear()
    keep = {v[1] for v in best.values()}
    return keep, total


def write(path, out_path, keep):
    """2. průchod: zapíše jen vybrané položky, zbytek feedu beze změny."""
    ET.register_namespace("g", G[1:-1])
    kept = 0
    with gzip.open(out_path, "wb") as out:
        out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write(b'<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel>\n')
        depth = 0
        for ev, el in ET.iterparse(path, events=("start", "end")):
            if ev == "start":
                depth += 1
                continue
            depth -= 1
            if el.tag == "item":
                if text(el, "id") in keep:
                    out.write(ET.tostring(el, encoding="utf-8"))
                    out.write(b"\n")
                    kept += 1
                el.clear()
            elif depth == 2 and el.tag in ("title", "link", "description"):
                # hlavička kanálu (title/link/description)
                out.write(ET.tostring(el, encoding="utf-8"))
        out.write(b"</channel></rss>\n")
    return kept


def main():
    src, dst = sys.argv[1], sys.argv[2]
    keep, total = choose(src)
    kept = write(src, dst, keep)
    print(f"Položek ve feedu: {total}, ponecháno: {kept}")
    if kept == 0 or kept > 145000:
        sys.exit("Výsledek mimo očekávaný rozsah – feed se nepublikuje.")


if __name__ == "__main__":
    main()
