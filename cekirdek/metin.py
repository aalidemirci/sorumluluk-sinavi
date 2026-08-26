"""Türkçeye özgü metin işlemleri.

Python'un yerleşik `lower()`/`upper()` çağrıları `I`/`İ` çiftini yanlış
dönüştürür ("İSTANBUL".lower() -> "i̇stanbul"). Ad, unvan ve branş
karşılaştırmalarının tamamı bu modülden geçmelidir.
"""

from __future__ import annotations

import re


_KUCULT = str.maketrans({"I": "ı", "İ": "i"})
_BUYULT = str.maketrans({"i": "İ", "ı": "I"})

# Türk alfabesinin harf sırası; sözlük sıralaması bunun üzerinden yapılır.
_ALFABE = "abcçdefgğhıijklmnoöprsştuüvyz"
_SIRA = {harf: sira for sira, harf in enumerate(_ALFABE)}


def kucult(metin: str) -> str:
    return metin.translate(_KUCULT).lower()


def buyult(metin: str) -> str:
    return metin.translate(_BUYULT).upper()


def sadelestir(deger: object) -> str:
    """Hücre değerini tek boşluklu, kırpılmış metne çevirir."""
    return re.sub(r"\s+", " ", str(deger if deger is not None else "").strip())


def esitle(metin: str) -> str:
    """Karşılaştırma anahtarı: sadeleştirilmiş ve Türkçe küçültülmüş biçim."""
    return kucult(sadelestir(metin))


def siralama_anahtari(metin: str) -> tuple[int, ...]:
    """Türk alfabesine göre sıralama anahtarı üretir."""
    return tuple(_SIRA.get(harf, 1000 + ord(harf)) for harf in kucult(metin))
