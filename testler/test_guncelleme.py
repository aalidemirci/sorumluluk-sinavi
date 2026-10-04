"""Güncelleme denetiminin ağsız testleri (karar 0015).

Kelebek Sınav'ın test_updates.py dosyasından uyarlandı: akış aynı, adlar bu
deponun Türkçe düzenindedir. Ağ hiç kullanılmaz — `son_yayim`/`_adresi_oku`
sahtelenir; ağ katmanının kendisi sınanırken de `urlopen` sahtelenir.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import time
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from veri import guncelleme

KURULUM_ADI = "SorumlulukSinavi-Kurulum-0.9.0.exe"
YAYIM_TABANI = "https://github.com/aalidemirci/sorumluluk-sinavi/releases/download/v0.9.0"


@pytest.fixture(autouse=True)
def _onbellek_yalitilir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Önbellek modül düzeyinde yaşar: her test boş önbellekle başlar."""
    monkeypatch.setattr(guncelleme, "_onbellekteki_yayim", None)


@pytest.fixture(autouse=True)
def _windows_platformu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Program içi indirme yalnız Windows'ta açıktır; testler her yerde koşar."""
    monkeypatch.setattr(guncelleme, "kurulum_destekleniyor_mu", lambda: True)


def _yayim(*, ozet: str = "", ozet_dosyasi: guncelleme.YayimVarligi | None = None,
           surum: str = "0.9.0") -> guncelleme.YayimBilgisi:
    return guncelleme.YayimBilgisi(
        surum=surum, etiket=f"v{surum}", ad=f"Sorumluluk Sınavı {surum}",
        yayim_zamani="2026-11-01T12:00:00Z",
        sayfa_adresi=f"https://github.com/aalidemirci/sorumluluk-sinavi/releases/tag/v{surum}",
        kurulum=guncelleme.YayimVarligi(KURULUM_ADI, f"{YAYIM_TABANI}/{KURULUM_ADI}", 8, ozet),
        ozet_dosyasi=ozet_dosyasi)


# ============================================================ sürüm yanıtı

def test_yayim_yaniti_kurulumu_ve_birlesik_ozeti_secer() -> None:
    """Yayımda iki özet dosyası vardır; kurulumu kapsayan birleşik olandır."""
    yayim = guncelleme._yayimi_coz({  # noqa: SLF001
        "tag_name": "v0.9.0", "name": "Sorumluluk Sınavı 0.9.0",
        "html_url": "https://github.com/aalidemirci/sorumluluk-sinavi/releases/tag/v0.9.0",
        "assets": [
            {"name": KURULUM_ADI, "browser_download_url": f"{YAYIM_TABANI}/{KURULUM_ADI}",
             "size": 1234, "digest": f"sha256:{'a' * 64}"},
            {"name": "SHA256SUMS-0.9.0-pardus.txt",
             "browser_download_url": f"{YAYIM_TABANI}/SHA256SUMS-0.9.0-pardus.txt"},
            {"name": "SHA256SUMS-0.9.0.txt",
             "browser_download_url": f"{YAYIM_TABANI}/SHA256SUMS-0.9.0.txt"},
            {"name": "sorumluluk-sinavi_0.9.0_amd64.deb",
             "browser_download_url": f"{YAYIM_TABANI}/sorumluluk-sinavi_0.9.0_amd64.deb"},
        ],
    })
    assert yayim.surum == "0.9.0"
    assert yayim.kurulum is not None and yayim.kurulum.boyut == 1234
    assert yayim.ozet_dosyasi is not None and yayim.ozet_dosyasi.ad == "SHA256SUMS-0.9.0.txt"


def test_yalniz_pardus_ozeti_kurulum_ozeti_sayilmaz() -> None:
    """Olumsuz senaryo: yalnız Pardus özeti varsa kurulum doğrulanamaz sayılır."""
    yayim = guncelleme._yayimi_coz({  # noqa: SLF001
        "tag_name": "v0.9.0",
        "assets": [{"name": "SHA256SUMS-0.9.0-pardus.txt",
                    "browser_download_url": f"{YAYIM_TABANI}/SHA256SUMS-0.9.0-pardus.txt"}],
    })
    assert yayim.ozet_dosyasi is None


def test_yol_bilesenli_varlik_adi_reddedilir() -> None:
    yayim = guncelleme._yayimi_coz({  # noqa: SLF001
        "tag_name": "v0.9.0",
        "assets": [{"name": "SorumlulukSinavi-Kurulum-/../../ele-gecir.exe",
                    "browser_download_url": f"{YAYIM_TABANI}/x.exe"}],
    })
    assert yayim.kurulum is None


def test_guvenilmeyen_varlik_adresi_kabul_edilmez() -> None:
    yayim = guncelleme._yayimi_coz({  # noqa: SLF001
        "tag_name": "v0.9.0",
        "html_url": "http://github.com/aalidemirci/sorumluluk-sinavi",
        "assets": [{"name": KURULUM_ADI, "browser_download_url": "https://example.org/zararli.exe"}],
    })
    assert yayim.kurulum is None
    assert yayim.sayfa_adresi == ""            # https değil → bağlantı verilmez


@pytest.mark.parametrize("govde", [None, [], "v0.9.0", {"tag_name": ""}, {"tag_name": " v "}])
def test_bicimsiz_surum_yaniti_reddedilir(govde: Any) -> None:
    with pytest.raises(guncelleme.GuncellemeHatasi):
        guncelleme._yayimi_coz(govde)  # noqa: SLF001


@pytest.mark.parametrize("ham", [b"{bozuk json", b"\xff\xfe\x00"])
def test_okunamayan_surum_yaniti_guncelleme_hatasidir(monkeypatch: pytest.MonkeyPatch,
                                                       ham: bytes) -> None:
    """Okul ağındaki vekil sunucu HTML ya da çöp döndürebilir: iz dökümü değil ileti."""
    monkeypatch.setattr(guncelleme, "_adresi_oku", lambda *_a, **_k: ham)
    with pytest.raises(guncelleme.GuncellemeHatasi, match="okunamadı"):
        guncelleme.son_yayim(zorla=True)


# ======================================================== sürüm karşılaştırma

def test_surum_anahtari_sayisal_karsilastirir_ve_on_surumu_kucuk_sayar() -> None:
    anahtar = guncelleme.surum_anahtari
    assert anahtar("0.10.0") > anahtar("0.9.0")          # dizge sırasında tersi olurdu
    assert anahtar("0.8.0-beta.2") < anahtar("0.8.0")
    assert anahtar("0.8.0-beta.10") > anahtar("0.8.0-beta.9")
    assert anahtar("0.8") == anahtar("0.8.0")
    assert anahtar(" 0.8.0 ") == anahtar("0.8.0")


def test_durum_yeni_surumu_bildirir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guncelleme, "son_yayim", lambda **_k: _yayim())
    durum = guncelleme.guncelleme_durumu(calisan_surum="0.7.0")
    assert durum["guncelleme_var"] is True and durum["indirilebilir"] is True
    assert (durum["son_surum"], durum["kurulum_adi"]) == ("0.9.0", KURULUM_ADI)


@pytest.mark.parametrize("calisan", ["0.9.0", "0.10.0", "0.9.1-beta.1"])
def test_guncel_ya_da_daha_yeni_kurulumda_guncelleme_onerilmez(
        monkeypatch: pytest.MonkeyPatch, calisan: str) -> None:
    monkeypatch.setattr(guncelleme, "son_yayim", lambda **_k: _yayim())
    durum = guncelleme.guncelleme_durumu(calisan_surum=calisan)
    assert durum["guncelleme_var"] is False and durum["indirilebilir"] is False


def test_pardusta_windows_kurulumu_onerilmez(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pardus'ta güncelleme .deb ile yapılır: indirme kapalı, ad ve boyut boştur."""
    monkeypatch.setattr(guncelleme, "kurulum_destekleniyor_mu", lambda: False)
    monkeypatch.setattr(guncelleme, "son_yayim", lambda **_k: _yayim())
    durum = guncelleme.guncelleme_durumu(calisan_surum="0.7.0")
    assert durum["guncelleme_var"] is True
    assert (durum["platform"], durum["indirilebilir"]) == ("linux", False)
    assert (durum["kurulum_adi"], durum["kurulum_boyutu"]) == ("", 0)
    with pytest.raises(guncelleme.GuncellemeHatasi, match="yalnız Windows"):
        guncelleme.son_kurulumu_indir()


# ================================================================= ağ katmanı

class _SahteYanit:
    def __init__(self, govde: bytes) -> None:
        self._akis = io.BytesIO(govde)

    def __enter__(self) -> "_SahteYanit":
        return self

    def __exit__(self, *_hata: object) -> None:
        return None

    def read(self, boyut: int = -1) -> bytes:
        return self._akis.read(boyut)


def _http_hatasi(kod: int) -> HTTPError:
    return HTTPError(guncelleme.SON_SURUM_ADRESI, kod, "hata", Message(), None)


def test_istek_github_basliklariyla_ve_zaman_asimiyla_gider(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """GitHub API'si User-Agent'sız isteği 403'ler; zaman aşımı olmazsa ağsız
    okulda denetim süresiz beklerdi."""
    gorulen: dict[str, Any] = {}

    def sahte_urlopen(istek: Request, timeout: float) -> _SahteYanit:
        gorulen.update(istek=istek, timeout=timeout)
        return _SahteYanit(b'{"tag_name": "v0.9.0"}')

    monkeypatch.setattr(guncelleme, "urlopen", sahte_urlopen)
    assert guncelleme._adresi_oku(guncelleme.SON_SURUM_ADRESI, azami_bayt=1024) == (  # noqa: SLF001
        b'{"tag_name": "v0.9.0"}')
    istek = gorulen["istek"]
    assert istek.full_url == guncelleme.SON_SURUM_ADRESI
    assert istek.get_header("User-agent") == guncelleme.KULLANICI_AJANI
    assert istek.get_header("Accept") == "application/vnd.github+json"
    assert 0 < gorulen["timeout"] <= 30


def test_istek_hicbir_kisisel_ya_da_okul_verisi_tasimaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Karar 0015: adreste sorgu dizgesi, istekte gövde ya da çerez yoktur."""
    gorulen: dict[str, Any] = {}

    def sahte_urlopen(istek: Request, timeout: float) -> _SahteYanit:
        gorulen["istek"] = istek
        return _SahteYanit(b'{"tag_name": "v0.9.0"}')

    monkeypatch.setattr(guncelleme, "urlopen", sahte_urlopen)
    guncelleme.son_yayim(zorla=True)
    istek = gorulen["istek"]
    assert "?" not in istek.full_url and istek.data is None
    assert {ad.lower() for ad in istek.headers} == {"accept", "x-github-api-version",
                                                    "user-agent"}


def test_yanit_boyut_sinirinda_kesilir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guncelleme, "urlopen", lambda *_a, **_k: _SahteYanit(b"x" * 10))
    assert guncelleme._adresi_oku("https://github.com/x", azami_bayt=10) == b"x" * 10  # noqa: SLF001
    monkeypatch.setattr(guncelleme, "urlopen", lambda *_a, **_k: _SahteYanit(b"x" * 11))
    with pytest.raises(guncelleme.GuncellemeHatasi, match="boyut sınırını aşıyor"):
        guncelleme._adresi_oku("https://github.com/x", azami_bayt=10)  # noqa: SLF001


@pytest.mark.parametrize(("kod", "beklenen"), [(403, "geçici olarak sınırlandı"),
                                               (429, "geçici olarak sınırlandı"),
                                               (500, "HTTP 500")])
def test_http_hatalari_turkce_iletiye_cevrilir(monkeypatch: pytest.MonkeyPatch, kod: int,
                                               beklenen: str) -> None:
    def patla(*_a: object, **_k: object) -> _SahteYanit:
        raise _http_hatasi(kod)

    monkeypatch.setattr(guncelleme, "urlopen", patla)
    with pytest.raises(guncelleme.GuncellemeHatasi, match=beklenen) as yakalanan:
        guncelleme._adresi_oku(guncelleme.SON_SURUM_ADRESI, azami_bayt=1024)  # noqa: SLF001
    # 404 dışındaki hatalar "sürüm yok" sayılmaz; ön sürüm yolu tetiklenmemeli.
    assert not isinstance(yakalanan.value, guncelleme.SurumBulunamadi)


def test_http_404_surum_yok_hatasidir(monkeypatch: pytest.MonkeyPatch) -> None:
    def patla(*_a: object, **_k: object) -> _SahteYanit:
        raise _http_hatasi(404)

    monkeypatch.setattr(guncelleme, "urlopen", patla)
    with pytest.raises(guncelleme.SurumBulunamadi):
        guncelleme._adresi_oku(guncelleme.SON_SURUM_ADRESI, azami_bayt=1024)  # noqa: SLF001


@pytest.mark.parametrize("hata", [URLError("dns yok"), TimeoutError("zaman aşımı"),
                                  OSError("ağ kapalı")])
def test_ag_yokken_anlasilir_ileti_verilir(monkeypatch: pytest.MonkeyPatch,
                                           hata: Exception) -> None:
    """Çevrimdışı okul olağan durumdur: ham soket hatası değil, Türkçe ileti."""
    def patla(*_a: object, **_k: object) -> _SahteYanit:
        raise hata

    monkeypatch.setattr(guncelleme, "urlopen", patla)
    with pytest.raises(guncelleme.GuncellemeHatasi, match="İnternet bağlantısını kontrol edin"):
        guncelleme._adresi_oku(guncelleme.SON_SURUM_ADRESI, azami_bayt=1024)  # noqa: SLF001


# ====================================================== ön sürüm ve önbellek

def _sahte_liste(monkeypatch: pytest.MonkeyPatch, liste: Any) -> None:
    def sahte(adres: str, *, azami_bayt: int) -> bytes:
        if adres == guncelleme.SON_SURUM_ADRESI:
            raise guncelleme.SurumBulunamadi("kararlı sürüm yok")
        assert adres == guncelleme.SURUM_LISTESI_ADRESI
        return json.dumps(liste).encode("utf-8")

    monkeypatch.setattr(guncelleme, "_adresi_oku", sahte)


def test_kararli_surum_yokken_on_surum_listeden_secilir(monkeypatch: pytest.MonkeyPatch) -> None:
    _sahte_liste(monkeypatch, [{"tag_name": "v0.9.0-beta.9", "assets": []},
                               {"tag_name": "v0.9.0-beta.10", "assets": []},
                               {"tag_name": "v1.0.0", "draft": True, "assets": []}])
    assert guncelleme.son_yayim(zorla=True).surum == "0.9.0-beta.10"


def test_on_surum_listesi_liste_degilse_reddedilir(monkeypatch: pytest.MonkeyPatch) -> None:
    _sahte_liste(monkeypatch, {"message": "API rate limit exceeded"})
    with pytest.raises(guncelleme.GuncellemeHatasi, match="beklenen biçimde değil"):
        guncelleme.son_yayim(zorla=True)


def test_listede_yayimlanmis_surum_yoksa_surum_yok_denir(monkeypatch: pytest.MonkeyPatch) -> None:
    _sahte_liste(monkeypatch, [{"tag_name": "v1.0.0", "draft": True}, {"tag_name": ""}, "x"])
    with pytest.raises(guncelleme.SurumBulunamadi):
        guncelleme.son_yayim(zorla=True)


@pytest.fixture
def sayac(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    durum: dict[str, Any] = {"cagri": 0, "saat": 1000.0, "etiket": "v0.9.0"}

    def sahte(_adres: str, *, azami_bayt: int) -> bytes:
        durum["cagri"] += 1
        return json.dumps({"tag_name": durum["etiket"]}).encode("utf-8")

    monkeypatch.setattr(guncelleme, "_adresi_oku", sahte)
    monkeypatch.setattr(time, "monotonic", lambda: durum["saat"])
    return durum


def test_sorgu_onbellekten_yanitlanir_zorla_tazeler(sayac: dict[str, Any]) -> None:
    ilk = guncelleme.son_yayim()
    sayac["etiket"] = "v0.10.0"
    assert guncelleme.son_yayim() is ilk and sayac["cagri"] == 1
    assert guncelleme.son_yayim(zorla=True).surum == "0.10.0" and sayac["cagri"] == 2


def test_onbellek_suresi_dolunca_yeniden_sorulur(sayac: dict[str, Any]) -> None:
    guncelleme.son_yayim()
    sayac["etiket"] = "v0.10.0"
    sayac["saat"] += guncelleme.ONBELLEK_SN - 1
    assert guncelleme.son_yayim().surum == "0.9.0"
    sayac["saat"] += 2
    assert guncelleme.son_yayim().surum == "0.10.0"


def test_basarisiz_sorgu_onbellege_yazilmaz(sayac: dict[str, Any],
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    def kopuk(_adres: str, *, azami_bayt: int) -> bytes:
        raise guncelleme.GuncellemeHatasi("Güncelleme sunucusuna ulaşılamadı.")

    with monkeypatch.context() as gecici:
        gecici.setattr(guncelleme, "_adresi_oku", kopuk)
        with pytest.raises(guncelleme.GuncellemeHatasi):
            guncelleme.son_yayim()
    assert guncelleme.son_yayim().surum == "0.9.0"


# ======================================================== doğrulanmış indirme

def _indirme_ortami(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                    yayim: guncelleme.YayimBilgisi, yanitlar: dict[str, bytes],
                    calisan: str = "0.7.0") -> list[str]:
    istenen: list[str] = []

    def sahte(adres: str, *, azami_bayt: int) -> bytes:
        istenen.append(adres)
        return yanitlar[adres]

    monkeypatch.setattr(guncelleme, "son_yayim", lambda **_k: yayim)
    monkeypatch.setattr(guncelleme, "SURUM", calisan)
    monkeypatch.setattr(guncelleme, "_adresi_oku", sahte)
    monkeypatch.setattr(guncelleme, "guncelleme_klasoru", lambda: tmp_path / "guncelleme")
    return istenen


def test_kurulum_sha256_dogrulanarak_onbellege_yazilir(monkeypatch: pytest.MonkeyPatch,
                                                       tmp_path: Path) -> None:
    icerik = b"kurulum"
    yayim = _yayim(ozet=f"sha256:{hashlib.sha256(icerik).hexdigest()}")
    _indirme_ortami(monkeypatch, tmp_path, yayim, {yayim.kurulum.indirme_adresi: icerik})
    hedef = guncelleme.son_kurulumu_indir()
    assert hedef.read_bytes() == icerik and hedef.parent == tmp_path / "guncelleme"
    assert not hedef.with_suffix(hedef.suffix + ".part").exists()


def test_ozeti_tutmayan_kurulum_yazilmaz(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yayim = _yayim(ozet=f"sha256:{'0' * 64}")
    _indirme_ortami(monkeypatch, tmp_path, yayim, {yayim.kurulum.indirme_adresi: b"farkli"})
    with pytest.raises(guncelleme.GuncellemeHatasi, match="doğrulanamadı"):
        guncelleme.son_kurulumu_indir()
    assert not (tmp_path / "guncelleme").exists()


@pytest.mark.parametrize("varlik_ozeti", ["", "sha256:kisa-ve-bozuk"])
def test_varlik_ozeti_yoksa_ozet_dosyasiyla_dogrulanir(monkeypatch: pytest.MonkeyPatch,
                                                       tmp_path: Path, varlik_ozeti: str) -> None:
    """Eski yayımlarda varlık özeti yoktur: `sha256sum -b` biçimli özet dosyası okunur."""
    icerik = b"kurulum"
    ozet_dosyasi = guncelleme.YayimVarligi("SHA256SUMS-0.9.0.txt",
                                           f"{YAYIM_TABANI}/SHA256SUMS-0.9.0.txt", 300, "")
    yayim = _yayim(ozet=varlik_ozeti, ozet_dosyasi=ozet_dosyasi)
    metin = (f"{'0' * 64} *sorumluluk-sinavi_0.9.0_amd64.deb\n\nbozuk-satir\n"
             f"{hashlib.sha256(icerik).hexdigest().upper()} *{KURULUM_ADI}\n")
    _indirme_ortami(monkeypatch, tmp_path, yayim,
                    {ozet_dosyasi.indirme_adresi: metin.encode(),
                     yayim.kurulum.indirme_adresi: icerik})
    assert guncelleme.son_kurulumu_indir().read_bytes() == icerik


def test_dogrulama_ozeti_olmayan_kurulum_hic_indirilmez(monkeypatch: pytest.MonkeyPatch,
                                                        tmp_path: Path) -> None:
    istenen = _indirme_ortami(monkeypatch, tmp_path, _yayim(ozet=""), {})
    with pytest.raises(guncelleme.GuncellemeHatasi, match="doğrulama özeti bulunmuyor"):
        guncelleme.son_kurulumu_indir()
    assert istenen == []


@pytest.mark.parametrize("calisan", ["0.9.0", "0.10.0"])
def test_guncel_kurulum_indirme_yapmaz(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                                       calisan: str) -> None:
    """Sürüm düşürme yolu yoktur: eski sürüm yeni şemalı veriyi açamaz."""
    istenen = _indirme_ortami(monkeypatch, tmp_path, _yayim(ozet=f"sha256:{'a' * 64}"), {},
                              calisan=calisan)
    with pytest.raises(guncelleme.GuncellemeHatasi, match="zaten güncel"):
        guncelleme.son_kurulumu_indir()
    assert istenen == []


def test_asiri_buyuk_kurulum_indirilmez(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    olagan = _yayim(ozet=f"sha256:{'a' * 64}")
    sisman = guncelleme.YayimBilgisi(
        **{**olagan.__dict__, "kurulum": guncelleme.YayimVarligi(
            KURULUM_ADI, olagan.kurulum.indirme_adresi, guncelleme.AZAMI_KURULUM_BAYTI + 1,
            olagan.kurulum.ozet)})
    istenen = _indirme_ortami(monkeypatch, tmp_path, sisman, {})
    with pytest.raises(guncelleme.GuncellemeHatasi, match="güvenli boyut sınırını"):
        guncelleme.son_kurulumu_indir()
    assert istenen == []


@pytest.mark.parametrize(("platform", "ortam", "beklenen"), [
    ("win32", {"LOCALAPPDATA": "/k/AppData/Local", "USERPROFILE": "/k"},
     Path("/k/AppData/Local/SorumlulukSinavi/guncelleme")),
    ("linux", {"XDG_CACHE_HOME": "/ev/.onbellek", "HOME": "/ev"},
     Path("/ev/.onbellek/sorumluluk-sinavi/guncelleme")),
    ("linux", {"HOME": "/ev"}, Path("/ev/.cache/sorumluluk-sinavi/guncelleme")),
])
def test_guncelleme_klasoru_veri_klasorunun_disindadir(monkeypatch: pytest.MonkeyPatch,
                                                      platform: str, ortam: dict[str, str],
                                                      beklenen: Path) -> None:
    for ad in ("SORUMLULUK_GUNCELLEME_KLASORU", "LOCALAPPDATA", "USERPROFILE",
               "XDG_CACHE_HOME", "HOME"):
        monkeypatch.delenv(ad, raising=False)
    for ad, deger in ortam.items():
        monkeypatch.setenv(ad, deger)
    monkeypatch.setattr(sys, "platform", platform)
    klasor = guncelleme.guncelleme_klasoru()
    assert klasor == beklenen and "plan" not in klasor.parts
