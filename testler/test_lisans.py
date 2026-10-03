"""Qt/PySide6 lisans koşullarının pakette karşılandığını koruyan testler.

Arayüz Qt for Python ile çalışır ve Qt burada LGPL-3.0 ile kullanılır
(karar 0016). LGPL-3.0 md.4 dağıtılan her kopyayla LGPL ve GPL metinlerinin
verilmesini, program telif bildirimi gösteriyorsa Qt'ninkinin de orada yer
almasını ister. NOTICE dağıtılan sürümün kaynak kodu adresini yazar; Qt
sürümü yükseltilip NOTICE unutulursa bildirim başka bir sürümü gösterir.
Bu testler o kaymayı yakalar.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
LISANS_METINLERI = {
    "LGPL-3.0-only.txt": "GNU LESSER GENERAL PUBLIC LICENSE",
    "GPL-3.0-only.txt": "GNU GENERAL PUBLIC LICENSE",
}


def sabit_qt_surumu(pyproject: str) -> str:
    """pyproject'te tam sabitlenmiş PySide6 sürümü; aralık kabul edilmez."""
    for bagimlilik in tomllib.loads(pyproject)["project"]["dependencies"]:
        eslesme = re.fullmatch(r"PySide6-Essentials==(\d+\.\d+\.\d+)",
                               bagimlilik.replace(" ", ""))
        if eslesme:
            return eslesme.group(1)
    raise ValueError("PySide6-Essentials tam sürümle sabitlenmemiş")


def _surum() -> str:
    return sabit_qt_surumu((KOK / "pyproject.toml").read_text(encoding="utf-8"))


def test_notice_dagitilan_qt_surumunu_ve_kaynagini_yazar() -> None:
    surum = _surum()
    notice = (KOK / "NOTICE").read_text(encoding="utf-8")
    assert f"Qt {surum}" in notice and f"Qt for Python {surum}" in notice
    assert f"qt-everywhere-src-{surum}" in notice
    assert f"pyside-setup-everywhere-src-{surum}" in notice
    assert "LGPL-3.0-only" in notice


def test_hakkinda_sayfasi_qt_bildirimini_gosterir() -> None:
    """LGPL-3.0 md.4-c: program telif bildirimi gösteriyorsa Qt'ninki de orada olur."""
    from arayuz.yardim_metni import LISANS_BOLUMLERI
    metin = " ".join(p for _baslik, paragraflar in LISANS_BOLUMLERI for p in paragraflar)
    assert f"Qt {_surum()}" in metin and "The Qt Company" in metin
    assert "LGPL" in metin and "LICENSES" in metin


def test_kurulu_qt_sabitlenen_surumdur() -> None:
    """Paket bu ortamdan derlenir; başka sürüm kuruluysa NOTICE yanlış olur."""
    import PySide6
    assert PySide6.__version__ == _surum()


def test_sabitlenmemis_surum_reddedilir() -> None:
    """Olumsuz senaryo: aralıkla yazılan bağımlılık hangi sürümün dağıtıldığını söylemez."""
    with pytest.raises(ValueError):
        sabit_qt_surumu('[project]\ndependencies = ["PySide6-Essentials>=6.9,<7"]\n')


def test_lisans_metinleri_pakete_girer() -> None:
    for ad, baslik in LISANS_METINLERI.items():
        metin = (KOK / "LICENSES" / ad).read_text(encoding="utf-8")
        assert baslik in metin[:200] and "Version 3, 29 June 2007" in metin[:200]
    spec = (KOK / "SorumlulukSinavi.spec").read_text(encoding="utf-8")
    assert 'pathlib.Path("LICENSES").glob("*.txt")' in spec
    iss = (KOK / "yapim" / "sorumluluk_sinavi.iss").read_text(encoding="utf-8")
    assert r'Source: "..\LICENSES\*"; DestDir: "{app}\LICENSES"' in iss
