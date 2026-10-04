"""Yayımlanan son sürümün denetimi ve doğrulanmış kurulum dosyasının indirilmesi.

Karar 0015: programın internete çıkan TEK isteği budur ve kişisel ya da okul
verisi taşımaz. Kardeş projelerle (Kelebek Sınav, Disiplin Defteri) aynı
standart izlenir: yalnız bu deponun GitHub'daki ``latest release`` kaydı
okunur; Windows kurulum dosyası GitHub'ın varlık özetiyle (``sha256:...``) ya
da aynı yayımdaki ``SHA256SUMS-<sürüm>.txt`` ile doğrulanmadan kullanıcıya
verilmez.

Ağ kodu yalnız bu modüldedir; testler/test_ag_yalitimi.py başka bir modülün
ağ kitaplığı içe aktarmasını engeller. Denetim açılış zincirine girmez:
arayüz pencere açıldıktan sonra arka planda bir kez sorar ve hatayı sessizce
yutar; Hakkında sayfasında elle denetlenir ve hata orada gösterilir.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cekirdek.surum import SURUM

GITHUB_DEPOSU = os.environ.get(
    "SORUMLULUK_GUNCELLEME_DEPOSU", "aalidemirci/sorumluluk-sinavi").strip()
GITHUB_API_SURUMU = "2026-03-10"
SON_SURUM_ADRESI = f"https://api.github.com/repos/{GITHUB_DEPOSU}/releases/latest"
SURUM_LISTESI_ADRESI = f"https://api.github.com/repos/{GITHUB_DEPOSU}/releases?per_page=10"
KULLANICI_AJANI = "Sorumluluk-Sinavi-Guncelleyici"
# GitHub engelli ağlarda (MEB) paket buradan indirilir; arayüz bu adresi önerir.
INDIRME_SAYFASI = "https://okulapp.org/sorumluluk-sinavi/#indir"
KURULUM_DESENI = re.compile(r"^SorumlulukSinavi-Kurulum-[0-9A-Za-z.\-]+\.exe$", re.IGNORECASE)
AZAMI_KURULUM_BAYTI = 250 * 1024 * 1024
ZAMAN_ASIMI_SN = 20
ONBELLEK_SN = 15 * 60

_onbellek_kilidi = threading.Lock()
_onbellekteki_yayim: tuple[float, "YayimBilgisi"] | None = None


class GuncellemeHatasi(RuntimeError):
    """Kullanıcıya olduğu gibi gösterilebilen güncelleme hatası."""


class SurumBulunamadi(GuncellemeHatasi):
    """GitHub 404: kararlı sürüm hiç yayımlanmamış (ör. yalnız ön sürüm var)."""


@dataclass(frozen=True)
class YayimVarligi:
    ad: str
    indirme_adresi: str
    boyut: int
    ozet: str


@dataclass(frozen=True)
class YayimBilgisi:
    surum: str
    etiket: str
    ad: str
    yayim_zamani: str
    sayfa_adresi: str
    kurulum: YayimVarligi | None
    ozet_dosyasi: YayimVarligi | None


def _on_surum_anahtari(ek: str) -> tuple[tuple[int, int | str], ...]:
    """Ön sürüm ekinin doğal sıralama anahtarı: "beta.10" > "beta.9".

    Ek dizge olarak karşılaştırılsaydı onuncu ön sürümde beta.9 kullanıcısına
    güncelleme önerilmezdi. Rakam öbekleri sayı, gerisi metin olarak
    karşılaştırılır; sayısal parça metinden küçüktür (semver önceliği).
    """
    parcalar = re.findall(r"\d+|[^\d.]+", ek)
    return tuple((0, int(p)) if p.isdigit() else (1, p.lower()) for p in parcalar)


def surum_anahtari(deger: str) -> tuple[tuple[int, ...], int, tuple[tuple[int, int | str], ...]]:
    """Sürüm karşılaştırma anahtarı; ön sürüm aynı numaralı kararlı sürümden küçüktür.

    Dizge karşılaştırması "0.10.0"ı "0.9.0"dan küçük sayardı.
    """
    bas, _, ek = deger.strip().partition("-")
    sayilar: list[int] = []
    for parca in bas.split("."):
        eslesme = re.match(r"^\d+", parca.strip())
        sayilar.append(int(eslesme.group(0)) if eslesme else 0)
    sayilar += [0] * (4 - len(sayilar))
    return (tuple(sayilar[:4]), 0 if ek else 1, _on_surum_anahtari(ek))


def guncelleme_klasoru() -> Path:
    """İndirilen kurulum dosyasının yazıldığı önbellek.

    Veri klasörünün (``…/plan``) dışındadır: yedeklenen ya da taşınan veri
    klasörüne kurulum dosyası karışmaz.
    """
    ozel = os.environ.get("SORUMLULUK_GUNCELLEME_KLASORU")
    if ozel:
        return Path(ozel)
    if sys.platform.startswith("win"):
        ev = Path(os.environ.get("USERPROFILE") or Path.home())
        yerel = Path(os.environ.get("LOCALAPPDATA") or ev / "AppData" / "Local")
        return yerel / "SorumlulukSinavi" / "guncelleme"
    ev = Path(os.environ.get("HOME") or Path.home())
    onbellek = Path(os.environ.get("XDG_CACHE_HOME") or ev / ".cache")
    return onbellek / "sorumluluk-sinavi" / "guncelleme"


def _istek(adres: str) -> Request:
    return Request(  # noqa: S310 — çağıran yalnız HTTPS GitHub adreslerini kabul eder
        adres,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_SURUMU,
            "User-Agent": KULLANICI_AJANI,
        },
    )


def _adresi_oku(adres: str, *, azami_bayt: int) -> bytes:
    """Yanıtı parça parça okur; sınır aşılırsa belleği doldurmadan keser."""
    try:
        with urlopen(_istek(adres), timeout=ZAMAN_ASIMI_SN) as yanit:  # noqa: S310
            parcalar: list[bytes] = []
            toplam = 0
            while True:
                parca = yanit.read(min(1024 * 1024, azami_bayt + 1 - toplam))
                if not parca:
                    break
                toplam += len(parca)
                if toplam > azami_bayt:
                    raise GuncellemeHatasi("Güncelleme dosyası beklenen boyut sınırını aşıyor.")
                parcalar.append(parca)
            return b"".join(parcalar)
    except HTTPError as hata:
        if hata.code == 404:
            raise SurumBulunamadi("Henüz yayımlanmış bir sürüm bulunmuyor.") from hata
        if hata.code in {403, 429}:
            raise GuncellemeHatasi(
                "Güncelleme denetimi geçici olarak sınırlandı; daha sonra yeniden deneyin."
            ) from hata
        raise GuncellemeHatasi(f"Güncelleme sunucusu HTTP {hata.code} hatası verdi.") from hata
    except (URLError, TimeoutError, OSError) as hata:
        raise GuncellemeHatasi(
            "Güncelleme sunucusuna ulaşılamadı. İnternet bağlantısını kontrol edin."
        ) from hata


def _guvenli_adres(deger: Any) -> str:
    adres = str(deger or "").strip()
    parca = urlparse(adres)
    if parca.scheme != "https" or parca.hostname not in {"github.com", "api.github.com"}:
        return ""
    return adres


def _varlik(deger: Any) -> YayimVarligi | None:
    if not isinstance(deger, dict):
        return None
    ad = str(deger.get("name") or "").strip()
    # Ad dosya yoluna çevrilir: yol bileşeni taşıyan varlık önbellek dışına
    # yazamasın diye reddedilir.
    if "/" in ad or "\\" in ad or ".." in ad:
        return None
    adres = _guvenli_adres(deger.get("browser_download_url"))
    if not ad or not adres:
        return None
    try:
        boyut = max(0, int(deger.get("size") or 0))
    except (TypeError, ValueError):
        boyut = 0
    return YayimVarligi(ad=ad, indirme_adresi=adres, boyut=boyut,
                        ozet=str(deger.get("digest") or "").strip().lower())


def _yayimi_coz(veri: Any) -> YayimBilgisi:
    if not isinstance(veri, dict):
        raise GuncellemeHatasi("Sürüm yanıtı beklenen biçimde değil.")
    etiket = str(veri.get("tag_name") or "").strip()
    surum = etiket.removeprefix("v").strip()
    if not surum:
        raise GuncellemeHatasi("Sürüm kaydında sürüm etiketi bulunmuyor.")
    varliklar = [v for ham in veri.get("assets") or [] if (v := _varlik(ham))]
    kurulum = next((v for v in varliklar if KURULUM_DESENI.fullmatch(v.ad)), None)
    # Yayımda iki özet dosyası olur: üç paketi kapsayan SHA256SUMS-<sürüm>.txt
    # ve yalnız Pardus paketini kapsayan …-pardus.txt. Kurulum ilkindedir.
    ozet_adlari = {f"SHA256SUMS-{surum}.TXT", "SHA256SUMS.TXT"}
    ozet_dosyasi = next((v for v in varliklar if v.ad.upper() in ozet_adlari), None)
    return YayimBilgisi(
        surum=surum,
        etiket=etiket,
        ad=str(veri.get("name") or etiket),
        yayim_zamani=str(veri.get("published_at") or ""),
        sayfa_adresi=_guvenli_adres(veri.get("html_url")),
        kurulum=kurulum,
        ozet_dosyasi=ozet_dosyasi,
    )


def _cozumle(ham: bytes) -> Any:
    try:
        return json.loads(ham.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as hata:
        raise GuncellemeHatasi("Sürüm yanıtı okunamadı.") from hata


def _on_surumlerin_en_yenisi() -> YayimBilgisi:
    """Kararlı sürüm yokken sürüm LİSTESİNDEN en yükseği seçilir.

    GitHub'ın ``releases/latest`` ucu ön sürümleri döndürmez; yalnız ön
    sürüm yayımlanmışken denetim bu yol olmadan hep "sürüm yok" derdi.
    """
    veri = _cozumle(_adresi_oku(SURUM_LISTESI_ADRESI, azami_bayt=4 * 1024 * 1024))
    if not isinstance(veri, list):
        raise GuncellemeHatasi("Sürüm yanıtı beklenen biçimde değil.")
    yayimlar: list[YayimBilgisi] = []
    for kayit in veri:
        if not isinstance(kayit, dict) or kayit.get("draft"):
            continue
        try:
            yayimlar.append(_yayimi_coz(kayit))
        except GuncellemeHatasi:
            continue
    if not yayimlar:
        raise SurumBulunamadi("Henüz yayımlanmış bir sürüm bulunmuyor.")
    return max(yayimlar, key=lambda y: surum_anahtari(y.surum))


def son_yayim(*, zorla: bool = False) -> YayimBilgisi:
    """Yayımlanan son sürüm; 15 dakika önbellekte tutulur, başarısız sorgu tutulmaz."""
    global _onbellekteki_yayim

    simdi = time.monotonic()
    with _onbellek_kilidi:
        if (not zorla and _onbellekteki_yayim
                and simdi - _onbellekteki_yayim[0] < ONBELLEK_SN):
            return _onbellekteki_yayim[1]
    try:
        yayim = _yayimi_coz(_cozumle(_adresi_oku(SON_SURUM_ADRESI, azami_bayt=2 * 1024 * 1024)))
    except SurumBulunamadi:
        yayim = _on_surumlerin_en_yenisi()
    with _onbellek_kilidi:
        _onbellekteki_yayim = (simdi, yayim)
    return yayim


def kurulum_destekleniyor_mu() -> bool:
    """Program içinden indirme yalnız Windows kurulum dosyasını bilir.

    Pardus'ta güncelleme .deb paketiyle yapılır; aynı düğme orada
    çalıştırılamayan bir Windows dosyası indirirdi.
    """
    return sys.platform.startswith("win")


def guncelleme_durumu(*, zorla: bool = False, calisan_surum: str | None = None) -> dict[str, Any]:
    """Arayüzün gösterdiği özet: kurulu ve yayımlanan sürüm, indirilebilir mi."""
    calisan = calisan_surum or SURUM
    yayim = son_yayim(zorla=zorla)
    var = surum_anahtari(yayim.surum) > surum_anahtari(calisan)
    indirilebilir = kurulum_destekleniyor_mu() and yayim.kurulum is not None
    return {
        "calisan_surum": calisan,
        "son_surum": yayim.surum,
        "guncelleme_var": var,
        "yayim_adi": yayim.ad,
        "yayim_zamani": yayim.yayim_zamani,
        "sayfa_adresi": yayim.sayfa_adresi,
        "platform": "windows" if kurulum_destekleniyor_mu() else "linux",
        "indirilebilir": var and indirilebilir,
        "kurulum_adi": yayim.kurulum.ad if indirilebilir and yayim.kurulum else "",
        "kurulum_boyutu": yayim.kurulum.boyut if indirilebilir and yayim.kurulum else 0,
    }


def _beklenen_ozet(yayim: YayimBilgisi) -> str:
    kurulum = yayim.kurulum
    if kurulum is None:
        raise GuncellemeHatasi("Bu sürümde Windows kurulum dosyası bulunmuyor.")
    if kurulum.ozet.startswith("sha256:"):
        ozet = kurulum.ozet.removeprefix("sha256:")
        if re.fullmatch(r"[0-9a-f]{64}", ozet):
            return ozet
    if yayim.ozet_dosyasi is None:
        raise GuncellemeHatasi("Kurulum dosyasının doğrulama özeti bulunmuyor.")
    metin = _adresi_oku(yayim.ozet_dosyasi.indirme_adresi, azami_bayt=256 * 1024).decode(
        "utf-8", errors="replace")
    for satir in metin.splitlines():
        parcalar = satir.strip().split(maxsplit=1)
        if len(parcalar) != 2:
            continue
        ozet, ad = parcalar
        if ad.lstrip("*") == kurulum.ad and re.fullmatch(r"[0-9a-fA-F]{64}", ozet):
            return ozet.lower()
    raise GuncellemeHatasi("Özet dosyasında Windows kurulum dosyası bulunmuyor.")


def son_kurulumu_indir(*, zorla: bool = False) -> Path:
    """Yeni sürümün kurulum dosyasını doğrulayarak önbelleğe indirir.

    Doğrulanamayacak dosya ağdan hiç çekilmez; özeti tutmayan dosya diske
    yazılmaz. Sürüm düşürme yolu yoktur: eski sürüm yeni şemalı veriyi açamaz.
    """
    if not kurulum_destekleniyor_mu():
        raise GuncellemeHatasi(
            "Program içinden indirme yalnız Windows'ta çalışır. Pardus için yeni .deb "
            "paketini indirme sayfasından alıp kurun.")
    yayim = son_yayim(zorla=zorla)
    if surum_anahtari(yayim.surum) <= surum_anahtari(SURUM):
        raise GuncellemeHatasi("Program zaten güncel; indirilecek daha yeni bir sürüm yok.")
    kurulum = yayim.kurulum
    if kurulum is None:
        raise GuncellemeHatasi("Yeni sürümde Windows kurulum dosyası bulunmuyor.")
    if kurulum.boyut > AZAMI_KURULUM_BAYTI:
        raise GuncellemeHatasi("Kurulum dosyası güvenli boyut sınırını aşıyor.")

    beklenen = _beklenen_ozet(yayim)
    icerik = _adresi_oku(kurulum.indirme_adresi, azami_bayt=AZAMI_KURULUM_BAYTI)
    if hashlib.sha256(icerik).hexdigest() != beklenen:
        # Kullanıcıya görünen iletide teknik terim (SHA-256) geçmez (karar 0015).
        raise GuncellemeHatasi("İndirilen kurulum dosyası doğrulanamadı: içeriği yayımlanan "
                               "dosyayla aynı değil. Dosya kullanılmadı; yeniden deneyin.")

    klasor = guncelleme_klasoru()
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / kurulum.ad
    gecici = hedef.with_suffix(hedef.suffix + ".part")
    gecici.write_bytes(icerik)
    gecici.replace(hedef)
    return hedef
