"""LICENSE'ın (Markdown) kurulum sihirbazı için düz metin hâlini üretir.

Inno Setup'ın lisans sayfası Markdown işlemez: LICENSE doğrudan verildiğinde
başlık işaretleri, çapa bağlantıları ve vurgu yıldızları olduğu gibi
görünüyordu (04.10.2026 güncelleme denemesi). Lisansın kendisi değişmez;
yalnız işaretleme kalkar, sözcükler aynı sırada kalır.
testler/test_lisans.py bunu sözcük sözcük denetler.

LICENSE değişirse depo kökünde yeniden çalıştırın:

    .venv/Scripts/python araclar/lisans_duz_metin.py
"""

from __future__ import annotations

import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
KAYNAK = KOK / "LICENSE"
HEDEF = KOK / "yapim" / "lisans.txt"


def _satir_ici(metin: str) -> str:
    metin = re.sub(r"\[([^\]]+)\]\(#[^)]*\)", r"\1", metin)    # iç bağlantı: yalnız yazısı
    metin = re.sub(r"<(https?://[^>]+)>", r"\1", metin)       # açık adres
    metin = re.sub(r"`([^`]+)`", r'"\1"', metin)               # satır içi kod
    return re.sub(r"\*{1,3}([^*]+?)\*{1,3}", r"\1", metin)    # kalın ve eğik


def duz_metin(markdown: str) -> str:
    """Başlıklar altı çizili satıra, alıntı girintiye döner; satır kırılımı korunur."""
    satirlar: list[str] = []
    for ham in markdown.splitlines():
        baslik = re.match(r"^(#{1,6})\s+(.+?)\s*$", ham)
        if baslik:
            yazi = _satir_ici(baslik.group(2))
            if satirlar and satirlar[-1]:
                satirlar.append("")
            satirlar += [yazi, ("=" if len(baslik.group(1)) == 1 else "-") * len(yazi), ""]
            continue
        satir = _satir_ici(ham.rstrip())
        if satir.startswith(">"):
            satir = "    " + satir.lstrip(">").strip()
        if not satir and (not satirlar or not satirlar[-1]):
            continue
        satirlar.append(satir)
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return "\n".join(satirlar) + "\n"


if __name__ == "__main__":
    # Sihirbazın metin kutusu Windows satır sonuyla yazılır; içerik ASCII'dir.
    HEDEF.write_text(duz_metin(KAYNAK.read_text(encoding="utf-8")), encoding="ascii",
                     newline="\r\n")
    print(f"yazıldı: {HEDEF.relative_to(KOK)}")
