"""Windows kurulum betiğinin yükseltme davranışı (yapim/sorumluluk_sinavi.iss).

Yeni sürüm eskisinin üzerine kurulur. Inno Setup'ta [Files] yalnız üzerine
yazar; adı değişen ya da artık kullanılmayan dosyayı ve kısayolu silmez.
Silinmesi gerekenler [InstallDelete]'te tek tek yazılıdır. Veritabanı kurulum
klasörünün dışındadır ve hiçbir silme kuralı oraya uzanmamalıdır.
"""

from __future__ import annotations

import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
BETIK = (KOK / "yapim" / "sorumluluk_sinavi.iss").read_text(encoding="utf-8")


def _silinenler(bolum: str) -> list[str]:
    """Bölümdeki silme kurallarının hedefleri (yorum satırları atlanır)."""
    eslesme = re.search(rf"^\[{bolum}\][ \t]*$(.*?)(?=^\[|\Z)", BETIK, re.MULTILINE | re.DOTALL)
    assert eslesme, bolum
    hedefler = []
    for satir in eslesme.group(1).splitlines():
        satir = satir.strip()
        if satir and not satir.startswith(";"):
            ad = re.search(r'Name: "([^"]+)"', satir)
            assert ad, satir
            hedefler.append(ad.group(1))
    return hedefler


def test_yukseltmede_eski_kitapliklar_silinir() -> None:
    """Tk'den Qt'ye geçişte (0.8.0) eski Tcl/Tk dosyaları _internal altında kalıyordu."""
    assert "{app}\\_internal" in _silinenler("InstallDelete")


def test_ingilizce_sihirbazdan_kalan_kaldirma_kisayolu_silinir() -> None:
    """0.6.0'dan önceki sihirbaz İngilizce iletilerle (Default.isl) kaldırma
    kısayolunu "Uninstall Sorumluluk Sınavı" adıyla kurardı. Türkçe sihirbaz aynı
    kısayolu başka adla kurduğu için eskisi Başlat menüsünde kalıyordu
    (04.10.2026 güncelleme denemesi)."""
    assert "{group}\\Uninstall {#Ad}.lnk" in _silinenler("InstallDelete")
    assert 'MessagesFile: "compiler:Languages\\Turkish.isl"' in BETIK


def test_silme_kurallari_veri_klasorune_uzanmaz() -> None:
    """Olumsuz senaryo: kurulum ve kaldırma yalnız kendi klasörünü ve Başlat menüsü
    grubunu siler; %LOCALAPPDATA%\\SorumlulukSinavi\\plan'a hiçbir kural uzanmaz."""
    for bolum in ("InstallDelete", "UninstallDelete"):
        hedefler = _silinenler(bolum)
        assert hedefler, bolum
        for ad in hedefler:
            assert ad.startswith(("{app}\\", "{group}\\")), (bolum, ad)
            assert ".." not in ad and "plan" not in ad.lower(), (bolum, ad)
