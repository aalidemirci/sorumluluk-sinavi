"""Personel aktarımı (OOK01001R1), branş havuzu ve öğretmen müsaitliği.
"""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

from cekirdek.metin import esitle
from cekirdek.modeller import Musaitsizlik, Personel
from ..rapor_okuma import personel_raporu_oku
from ..veritabani import Veritabani, simdi

from .ortak import AktarimOzeti, HizmetHatasi


# ============================================================== branş havuzu

def brans_havuzu_listele(vt: Veritabani) -> list[tuple[int, str, str]]:
    with vt.baglan() as b:
        return [tuple(r) for r in b.execute(
            "SELECT id,ad,kaynak FROM v_brans_havuzu ORDER BY ad")]


def brans_havuzu_ekle(vt: Veritabani, ad: str, kaynak: str = "manuel_ilce_mem") -> int:
    ad = " ".join(str(ad).split())
    if not ad:
        raise HizmetHatasi("Branş adı zorunludur.")
    zaman = simdi()
    with vt.baglan() as b:
        b.execute(
            "INSERT INTO brans_havuzu(ad,ad_anahtari,kaynak,olusturuldu_at,guncellendi_at)"
            " VALUES(?,?,?,?,?) ON CONFLICT(ad_anahtari) DO UPDATE SET"
            " aktif_mi=1,guncellendi_at=excluded.guncellendi_at",
            (ad, esitle(ad), kaynak, zaman, zaman))
        kimlik = int(b.execute("SELECT id FROM brans_havuzu WHERE ad_anahtari=?",
                               (esitle(ad),)).fetchone()[0])
        vt.denetim_yaz(b, "brans_havuzu", kimlik, "eklendi")
        return kimlik


def personel_onizle(vt: Veritabani, yol: Path) -> AktarimOzeti:
    """Personel raporunu okuyup staging'e yazar; ana tabloya dokunmaz."""
    rapor = personel_raporu_oku(Path(yol))
    with vt.baglan() as b:
        onceki = b.execute(
            "SELECT id,durum FROM ice_aktarim WHERE tur='personel' AND sha256=?",
            (rapor.dosya_ozeti,)).fetchone()
        if onceki and onceki[1] == "onaylandi":
            raise HizmetHatasi("Bu personel raporu daha önce onaylanmıştır.")
        if onceki:
            b.execute("DELETE FROM personel_aktarim_satiri WHERE ice_aktarim_id=?", (onceki[0],))
            aktarim_id = int(onceki[0])
        else:
            aktarim_id = int(b.execute(
                "INSERT INTO ice_aktarim(tur,dosya_adi,sha256,olusturuldu_at)"
                " VALUES('personel',?,?,?)",
                (Path(yol).name, rapor.dosya_ozeti, simdi())).lastrowid)

        mevcut = {r["ad_anahtari"]: r for r in b.execute(
            "SELECT ad_anahtari,brans,unvan,personel_tipi,kadro_durumu,aktif_mi"
            " FROM v_personel")}
        ozet = AktarimOzeti(aktarim_id)
        gelen = set()
        for kayit in rapor.kayitlar:
            anahtar = esitle(kayit.ad)
            gelen.add(anahtar)
            eski = mevcut.get(anahtar)
            if eski is None:
                eylem = "eklenecek"
                ozet.eklenen += 1
            elif ((eski["brans"], eski["unvan"], eski["personel_tipi"],
                   eski["kadro_durumu"], eski["aktif_mi"])
                  != (kayit.brans, kayit.unvan, kayit.personel_tipi, kayit.kadro_durumu, 1)):
                eylem = "guncellenecek"
                ozet.guncellenen += 1
            else:
                eylem = "degismedi"
                ozet.degismedi += 1
            b.execute(
                "INSERT INTO personel_aktarim_satiri(ice_aktarim_id,satir_no,ad,unvan,"
                "kadro_durumu,brans,personel_tipi,kurum_sicil_no,eylem)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (aktarim_id, kayit.satir_no, kayit.ad, kayit.unvan, kayit.kadro_durumu,
                 kayit.brans, kayit.personel_tipi, kayit.kurum_sicil_no or None, eylem))
            ozet.satirlar.append((kayit.ad, kayit.unvan, kayit.kadro_durumu, kayit.brans, eylem))
        ozet.cikan = sum(1 for a, r in mevcut.items() if r["aktif_mi"] and a not in gelen)
        b.execute("UPDATE ice_aktarim SET eklenen=?,guncellenen=?,degismedi=?,cikan=?"
                  " WHERE id=?",
                  (ozet.eklenen, ozet.guncellenen, ozet.degismedi, ozet.cikan, aktarim_id))
        return ozet


def personel_onayla(vt: Veritabani, aktarim_id: int) -> AktarimOzeti:
    """Staging'deki personel farkını ana tabloya uygular."""
    with vt.baglan() as b:
        aktarim = b.execute(
            "SELECT durum FROM ice_aktarim WHERE id=? AND tur='personel'",
            (aktarim_id,)).fetchone()
        if not aktarim:
            raise HizmetHatasi("Personel içe aktarımı bulunamadı.")
        if aktarim[0] == "onaylandi":
            raise HizmetHatasi("Bu içe aktarım zaten onaylanmıştır.")
        satirlar = b.execute(
            "SELECT ad,unvan,kadro_durumu,brans,personel_tipi,kurum_sicil_no,eylem"
            " FROM personel_aktarim_satiri WHERE ice_aktarim_id=? ORDER BY satir_no",
            (aktarim_id,)).fetchall()
        if not satirlar:
            raise HizmetHatasi("Onaylanacak satır yok.")

        mevcut = {r[0]: r[1] for r in b.execute(
            "SELECT ad_anahtari,id FROM personel WHERE silindi_mi=0")}
        ozet = AktarimOzeti(aktarim_id)
        gelen = set()
        zaman = simdi()
        for ad, unvan, kadro, brans, tip, sicil, eylem in satirlar:
            anahtar = esitle(ad)
            gelen.add(anahtar)
            if anahtar in mevcut:
                b.execute(
                    "UPDATE personel SET ad=?,brans=?,unvan=?,personel_tipi=?,kadro_durumu=?,"
                    "kurum_sicil_no=?,aktif_mi=1,kaynak_aktarim_id=? WHERE id=?",
                    (ad, brans, unvan, tip, kadro, sicil, aktarim_id, mevcut[anahtar]))
                ozet.guncellenen += int(eylem == "guncellenecek")
                ozet.degismedi += int(eylem == "degismedi")
            else:
                b.execute(
                    "INSERT INTO personel(ad,ad_anahtari,brans,unvan,personel_tipi,"
                    "kadro_durumu,kurum_sicil_no,kaynak_aktarim_id)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (ad, anahtar, brans, unvan, tip, kadro, sicil, aktarim_id))
                ozet.eklenen += 1
            # Branş havuzu personel raporundan beslenir.
            b.execute(
                "INSERT INTO brans_havuzu(ad,ad_anahtari,kaynak,olusturuldu_at,guncellendi_at)"
                " VALUES(?,?,'personel_raporu',?,?) ON CONFLICT(ad_anahtari) DO UPDATE SET"
                " aktif_mi=1,guncellendi_at=excluded.guncellendi_at",
                (brans, esitle(brans), zaman, zaman))
        for anahtar, kimlik in mevcut.items():
            if anahtar not in gelen:
                ozet.cikan += b.execute(
                    "UPDATE personel SET aktif_mi=0 WHERE id=? AND aktif_mi=1",
                    (kimlik,)).rowcount
        b.execute("UPDATE ice_aktarim SET durum='onaylandi',onaylandi_at=?,eklenen=?,"
                  "guncellenen=?,degismedi=?,cikan=? WHERE id=?",
                  (zaman, ozet.eklenen, ozet.guncellenen, ozet.degismedi, ozet.cikan,
                   aktarim_id))
        vt.denetim_yaz(b, "ice_aktarim", aktarim_id, "personel_onaylandi",
                       f"+{ozet.eklenen} ~{ozet.guncellenen} -{ozet.cikan}")
        return ozet


def personelleri_getir(vt: Veritabani, yalniz_aktif: bool = True) -> list[Personel]:
    kosul = " WHERE aktif_mi=1" if yalniz_aktif else ""
    with vt.baglan() as b:
        return [Personel(r[0], r[1], r[2], r[3], bool(r[4])) for r in b.execute(
            f"SELECT id,ad,brans,unvan,aktif_mi FROM v_personel{kosul} ORDER BY id")]


# ===================================================== öğretmen müsaitliği

HAFTA_GUNLERI = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


def musaitlik_ekle(vt: Veritabani, personel_id: int, *, hafta_gunu: int | None = None,
                   bas_saat: time | None = None, bit_saat: time | None = None,
                   bas_tarih: date | None = None, bit_tarih: date | None = None,
                   aciklama: str = "") -> int:
    """Öğretmenin sınav görevi alamayacağı zamanı kaydeder (SP-09).

    OKY md.58/2-ç sınavların dersleri aksatmayacak şekilde planlanmasını
    ister; program öğretmenin ders programını e-Okul'dan okuyamadığı için
    dolu saatler buradan girilir. Kayıt ya haftalık bir gündür ya da tarih
    aralığıdır; saat verilmezse bütün gün kapsanır.
    """
    if (hafta_gunu is None) == (bas_tarih is None):
        raise HizmetHatasi("Müsaitlik kaydı ya haftanın bir günü ya da bir tarih aralığıdır.")
    if hafta_gunu is not None and not 0 <= hafta_gunu <= 6:
        raise HizmetHatasi("Geçersiz hafta günü.")
    if (bas_saat is None) != (bit_saat is None):
        raise HizmetHatasi("Saat aralığının başı ve sonu birlikte girilmelidir.")
    if bas_saat is not None and bas_saat >= bit_saat:
        raise HizmetHatasi("Saat aralığının sonu başından sonra olmalıdır.")
    if bas_tarih is not None and bit_tarih is not None and bit_tarih < bas_tarih:
        raise HizmetHatasi("Tarih aralığının sonu başından önce olamaz.")
    with vt.baglan() as b:
        if not b.execute("SELECT 1 FROM v_personel WHERE id=?", (personel_id,)).fetchone():
            raise HizmetHatasi("Personel bulunamadı.")
        kimlik = int(b.execute(
            "INSERT INTO personel_musaitlik(personel_id,hafta_gunu,bas_saat,bit_saat,"
            "bas_tarih,bit_tarih,aciklama,olusturuldu_at) VALUES(?,?,?,?,?,?,?,?)",
            (personel_id, hafta_gunu,
             bas_saat.strftime("%H:%M") if bas_saat else None,
             bit_saat.strftime("%H:%M") if bit_saat else None,
             bas_tarih.isoformat() if bas_tarih else None,
             (bit_tarih or bas_tarih).isoformat() if bas_tarih else None,
             aciklama.strip(), simdi())).lastrowid)
        vt.denetim_yaz(b, "personel_musaitlik", kimlik, "eklendi")
        return kimlik


def musaitlik_sil(vt: Veritabani, kayit_id: int) -> None:
    with vt.baglan() as b:
        b.execute("UPDATE personel_musaitlik SET silindi_mi=1 WHERE id=?", (kayit_id,))
        vt.denetim_yaz(b, "personel_musaitlik", kayit_id, "silindi")


def _musaitsizlik(satir) -> Musaitsizlik:
    def saat(metin):
        return time.fromisoformat(metin) if metin else None

    def tarih(metin):
        return date.fromisoformat(metin) if metin else None

    return Musaitsizlik(satir["personel_id"], satir["hafta_gunu"], saat(satir["bas_saat"]),
                        saat(satir["bit_saat"]), tarih(satir["bas_tarih"]),
                        tarih(satir["bit_tarih"]))


def musaitlik_listesi(vt: Veritabani, personel_id: int) -> list[dict]:
    """Bir öğretmenin müsaitlik kayıtları, ekranda okunacak metinle birlikte."""
    with vt.baglan() as b:
        satirlar = b.execute(
            "SELECT * FROM v_personel_musaitlik WHERE personel_id=?"
            " ORDER BY hafta_gunu IS NULL, hafta_gunu, bas_tarih, bas_saat",
            (personel_id,)).fetchall()
    sonuc = []
    for satir in satirlar:
        kayit = _musaitsizlik(satir)
        if kayit.hafta_gunu is not None:
            zaman = f"Her {HAFTA_GUNLERI[kayit.hafta_gunu].lower()}"
        else:
            zaman = kayit.bas_tarih.strftime("%d.%m.%Y")
            if kayit.bit_tarih and kayit.bit_tarih != kayit.bas_tarih:
                zaman += " – " + kayit.bit_tarih.strftime("%d.%m.%Y")
        saat = (f"{kayit.bas_saat.strftime('%H:%M')}–{kayit.bit_saat.strftime('%H:%M')}"
                if kayit.bas_saat else "bütün gün")
        sonuc.append({"kimlik": satir["id"], "zaman": zaman, "saat": saat,
                      "aciklama": satir["aciklama"], "kayit": kayit})
    return sonuc


def musaitsizlikleri_getir(vt: Veritabani) -> dict[int, tuple[Musaitsizlik, ...]]:
    kayitlar: dict[int, list[Musaitsizlik]] = {}
    with vt.baglan() as b:
        for satir in b.execute("SELECT * FROM v_personel_musaitlik"):
            kayitlar.setdefault(satir["personel_id"], []).append(_musaitsizlik(satir))
    return {kimlik: tuple(liste) for kimlik, liste in kayitlar.items()}
