"""Programın tek ağ isteği güncelleme denetimidir (karar 0015).

Ağ kitaplığı yalnız veri/guncelleme.py'de içe aktarılabilir. Başka bir
modüle eklenen `urllib`, `socket`, `requests` ya da Qt'nin ağ modülü bu testi
kırar: çevrimdışılık sözü tek bir yerden denetlenebilir kalmalıdır.
"""

from __future__ import annotations

import ast
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
IZINLI = {"veri/guncelleme.py"}
YASAK_KOKLER = {"urllib", "http", "socket", "ssl", "requests", "httpx", "aiohttp",
                "ftplib", "smtplib", "xmlrpc"}
YASAK_QT = {"QtNetwork", "QtWebEngineCore", "QtWebEngineWidgets", "QtWebSockets"}


def _yasak_mi(ad: str) -> bool:
    parcalar = ad.split(".")
    return parcalar[0] in YASAK_KOKLER or bool(YASAK_QT & set(parcalar))


def _ag_ice_aktarimlari(yol: Path, kok: Path = KOK) -> list[str]:
    """Her içe aktarma deyimi en çok bir kez raporlanır."""
    bulunan = []
    for dugum in ast.walk(ast.parse(yol.read_text(encoding="utf-8"))):
        if isinstance(dugum, ast.Import):
            adlar = [ad.name for ad in dugum.names]
        elif isinstance(dugum, ast.ImportFrom) and dugum.module:
            adlar = [dugum.module] + [f"{dugum.module}.{ad.name}" for ad in dugum.names]
        else:
            continue
        yasak = next((ad for ad in adlar if _yasak_mi(ad)), None)
        if yasak:
            bulunan.append(f"{yol.relative_to(kok).as_posix()}:{dugum.lineno} {yasak}")
    return sorted(bulunan, key=lambda s: int(s.split(":")[1].split(" ")[0]))


def _kaynaklar(kok: Path) -> list[Path]:
    yollar = [kok / "sorumluluk_sinavi.py"] if (kok / "sorumluluk_sinavi.py").exists() else []
    for klasor in ("cekirdek", "veri", "evrak", "arayuz"):
        if (kok / klasor).is_dir():
            yollar += sorted((kok / klasor).rglob("*.py"))
    return yollar


def test_ag_kitapligi_yalniz_guncelleme_modulunde() -> None:
    ihlaller = [satir for yol in _kaynaklar(KOK)
                if yol.relative_to(KOK).as_posix() not in IZINLI
                for satir in _ag_ice_aktarimlari(yol)]
    assert not ihlaller, f"Ağ kitaplığı izinli modül dışında: {ihlaller}"


def test_guncelleme_modulu_gercekten_ag_kullanir() -> None:
    """İzin listesi bayatlamasın: modül taşınırsa bu denetim boşa düşmez."""
    assert _ag_ice_aktarimlari(KOK / "veri" / "guncelleme.py")


def test_denetim_ag_ice_aktarimini_yakalar(tmp_path: Path) -> None:
    """Olumsuz senaryo: başka modüldeki ağ içe aktarımı ve Qt ağ modülü yakalanır."""
    (tmp_path / "arayuz").mkdir()
    ornek = tmp_path / "arayuz" / "ornek.py"
    ornek.write_text("import os\nfrom urllib.request import urlopen\n"
                     "from PySide6 import QtNetwork\nfrom PySide6.QtNetwork import QTcpSocket\n"
                     "from PySide6.QtWidgets import QLabel\n", encoding="utf-8")
    bulunan = _ag_ice_aktarimlari(ornek, tmp_path)
    assert [s.split(" ")[0] for s in bulunan] == [
        "arayuz/ornek.py:2", "arayuz/ornek.py:3", "arayuz/ornek.py:4"]
    assert [ornek] == [y for y in _kaynaklar(tmp_path) if y.name == "ornek.py"]
