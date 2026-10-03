"""Personelin elle eklenmesi, pasife alınması ve silinmesi.

Görevi olan kişi silinemez; bu yüzden görev havuzuna dayanır ve
personel aktarımından ayrı durur.
"""

from __future__ import annotations

from cekirdek.metin import esitle
from ..veritabani import Veritabani, simdi

from .ortak import HizmetHatasi
from .plan_kayitlari import etkin_planlar
from .gorev import _gorev_kayitlari


# ================================================== personel elle yönetimi

def personel_ekle(vt: Veritabani, ad: str, brans: str, unvan: str,
                  personel_tipi: str = "kadrolu", kadro_durumu: str = "") -> int:
    """Rapor dışından elle personel ekler.

    e-Okul raporu asıl kaynaktır; bu yol, rapora henüz yansımamış görevlendirme
    ve ücretli öğretmen gibi durumlar içindir. Eklenen kişinin branşı da branş
    havuzuna girer.
    """
    ad = " ".join(str(ad).split())
    brans = " ".join(str(brans).split())
    unvan = " ".join(str(unvan).split())
    if not (ad and brans and unvan):
        raise HizmetHatasi("Ad, branş ve görev alanları zorunludur.")
    if personel_tipi not in {"kadrolu", "sozlesmeli", "ucretli", "yonetici", "diger"}:
        raise HizmetHatasi("Geçersiz personel tipi.")
    zaman = simdi()
    with vt.baglan() as b:
        mevcut = b.execute("SELECT id,silindi_mi FROM personel WHERE ad_anahtari=?",
                           (esitle(ad),)).fetchone()
        if mevcut and not mevcut[1]:
            raise HizmetHatasi(f"'{ad}' zaten kayıtlı. Aynı adlı ikinci kişi ayırt edilemez.")
        if mevcut:
            b.execute("UPDATE personel SET ad=?,brans=?,unvan=?,personel_tipi=?,"
                      "kadro_durumu=?,aktif_mi=1,silindi_mi=0 WHERE id=?",
                      (ad, brans, unvan, personel_tipi, kadro_durumu, mevcut[0]))
            kimlik = int(mevcut[0])
        else:
            kimlik = int(b.execute(
                "INSERT INTO personel(ad,ad_anahtari,brans,unvan,personel_tipi,kadro_durumu)"
                " VALUES(?,?,?,?,?,?)",
                (ad, esitle(ad), brans, unvan, personel_tipi, kadro_durumu)).lastrowid)
        b.execute(
            "INSERT INTO brans_havuzu(ad,ad_anahtari,kaynak,olusturuldu_at,guncellendi_at)"
            " VALUES(?,?,'manuel_ilce_mem',?,?) ON CONFLICT(ad_anahtari) DO UPDATE SET"
            " aktif_mi=1,guncellendi_at=excluded.guncellendi_at",
            (brans, esitle(brans), zaman, zaman))
        vt.denetim_yaz(b, "personel", kimlik, "elle_eklendi")
        return kimlik


def personel_durumu_degistir(vt: Veritabani, personel_id: int, aktif_mi: bool) -> None:
    """Personeli pasife alır ya da yeniden etkinleştirir.

    Pasif personel yeni görevlendirmeye alınmaz; geçmiş görevleri ve sayaçları
    olduğu gibi kalır.
    """
    with vt.baglan() as b:
        if not b.execute("SELECT 1 FROM v_personel WHERE id=?", (personel_id,)).fetchone():
            raise HizmetHatasi("Personel bulunamadı.")
        b.execute("UPDATE personel SET aktif_mi=? WHERE id=?", (int(aktif_mi), personel_id))
        vt.denetim_yaz(b, "personel", personel_id,
                       "etkinlestirildi" if aktif_mi else "pasife_alindi")


def personel_sil(vt: Veritabani, personel_id: int) -> None:
    """Personeli listeden çıkarır.

    Görevlendirmesi bulunan kişi silinemez: silinirse üretilmiş evrak ile
    veritabanı çelişir. Böyle bir kişi pasife alınmalıdır.
    """
    with vt.baglan() as b:
        satir = b.execute("SELECT ad FROM v_personel WHERE id=?", (personel_id,)).fetchone()
        if not satir:
            raise HizmetHatasi("Personel bulunamadı.")
        gorev = b.execute("SELECT count(*) FROM v_gorevlendirme WHERE personel_id=?",
                          (personel_id,)).fetchone()[0]
        if gorev:
            raise HizmetHatasi(
                f"{satir[0]} için {gorev} sınav görevi kayıtlı; silinemez. "
                "Yeni görev almaması için pasife alın.")
        b.execute("UPDATE personel SET silindi_mi=1,aktif_mi=0 WHERE id=?", (personel_id,))
        vt.denetim_yaz(b, "personel", personel_id, "silindi")


def personel_ayrintili_liste(vt: Veritabani) -> list[dict]:
    """Öğretmen ekranı için görev sayaçlarıyla birlikte personel listesi."""
    sayilar: dict[int, int] = {}
    for kimlik, _, _, _ in _gorev_kayitlari(vt, list(etkin_planlar(vt).values())):
        sayilar[kimlik] = sayilar.get(kimlik, 0) + 1
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT p.id, p.ad, p.unvan, p.brans, p.kadro_durumu, p.aktif_mi,
                   p.kaynak_aktarim_id,
                   (SELECT count(*) FROM v_personel_musaitlik m WHERE m.personel_id = p.id)
            FROM v_personel p ORDER BY p.aktif_mi DESC, p.ad""").fetchall()
    return [{"kimlik": r[0], "ad": r[1], "unvan": r[2], "brans": r[3],
             "kadro": r[4], "aktif_mi": bool(r[5]),
             "kaynak": "e-Okul raporu" if r[6] else "elle eklendi",
             "gorev_sayisi": sayilar.get(r[0], 0), "musaitlik_sayisi": r[7]}
            for r in satirlar]
