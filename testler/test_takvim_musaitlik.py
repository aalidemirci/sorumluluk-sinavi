"""Tatil günleri, öğretmen müsaitliği, tarih biçimi ve başvuru işaretinin yılı.

Veriler uydurmadır (KVKK).
"""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from cekirdek.modeller import PlanParametreleri
from cekirdek.takvim import (
    gunleri_listele, tarih_coz, tarih_yaz, tek_ders_penceresi, varsayilan_pencere_kodu,
)
from veri import hizmet
from veri.hizmet import HizmetHatasi
from testler.test_hizmet import AYARLAR, _kur, vt  # noqa: F401  (fikstür)


# ================================================================ tarih biçimi

def test_tarih_gg_aa_yyyy_ve_iso_kabul_edilir() -> None:
    assert tarih_coz("14.09.2026") == date(2026, 9, 14)
    assert tarih_coz("4.9.2026") == date(2026, 9, 4)
    assert tarih_coz("2026-09-14") == date(2026, 9, 14)
    assert tarih_yaz(date(2026, 9, 4)) == "04.09.2026"


def test_gecersiz_tarih_anlasilir_hata_verir() -> None:
    with pytest.raises(ValueError, match="gg.aa.yyyy"):
        tarih_coz("31.02.2026")
    with pytest.raises(ValueError, match="gg.aa.yyyy"):
        tarih_coz("dün")


def test_kurum_ayarlari_gg_aa_yyyy_ile_kaydedilir(vt) -> None:
    ayar = dict(AYARLAR, birinci_donem_baslangic="14.09.2026",
                ikinci_donem_baslangic="08.02.2027", ikinci_donem_bitis="25.06.2027")
    hizmet.ayarlari_kaydet(vt, ayar)
    assert hizmet.ayarlari_getir(vt)["birinci_donem_baslangic"] == "2026-09-14"
    assert hizmet.pencereleri_getir(vt)["P1"][0] == date(2026, 9, 14)


# ============================================================== tatil günleri

def test_tatil_hafta_sonu_acikken_de_plan_gunu_olmaz() -> None:
    """Eski sürüm hafta sonu açıkken tatil listesini hiç uygulamıyordu."""
    tatil = frozenset({date(2026, 9, 15)})
    for hafta_sonu in (False, True):
        gunler = gunleri_listele(date(2026, 9, 14), date(2026, 9, 20), hafta_sonu, tatil)
        assert date(2026, 9, 15) not in gunler
    assert date(2026, 9, 19) in gunleri_listele(date(2026, 9, 14), date(2026, 9, 20), True, tatil)


def test_plan_tatil_gunune_sinav_koymaz(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    tatiller = [date(2026, 9, d) for d in (14, 15, 16)]
    for gun in tatiller:
        hizmet.tatil_ekle(vt, gun, "Uydurma idari izin")
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    assert not {o.tarih for o in sonuc.plan.oturumlar} & set(tatiller)


def test_kayitli_planda_sonradan_eklenen_tatil_engeldir(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    ilk_gun = min(o.tarih for o in sonuc.plan.oturumlar)
    hizmet.tatil_ekle(vt, ilk_gun, "Uydurma bayram")
    ihlaller = hizmet.plani_dogrula(vt, sonuc.plan, sonuc.yukseltilen_sinirlar)
    assert any(i.kural_kimligi == "SP-08" and i.engel_mi for i in ihlaller)


def test_basvuru_bes_is_gunu_tatili_saymaz(vt, tmp_path: Path) -> None:
    """OKY md.58/2-d: 5 İŞ GÜNÜ. Pencere 14.09.2026 pazartesi; 07.09 son gün
    olarak geçerlidir, araya tatil girerse değildir."""
    _kur(vt, tmp_path)
    hizmet.duyuru_kaydet(vt, "P1", date(2026, 8, 20), date(2026, 9, 7), "Uydurma 2026/1")
    hizmet.tatil_ekle(vt, date(2026, 9, 9), "Uydurma idari izin")
    with pytest.raises(HizmetHatasi, match="en geç 04.09.2026"):
        hizmet.duyuru_kaydet(vt, "P1", date(2026, 8, 20), date(2026, 9, 7), "Uydurma 2026/1")


def test_teslim_suresi_tatili_atlar(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    plan_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1")))
    satir = hizmet.teslim_cizelgesi(vt, plan_id)[0]
    olagan = satir.son_gun()
    hizmet.tatil_ekle(vt, olagan, "Uydurma tatil")
    satir = next(s for s in hizmet.teslim_cizelgesi(vt, plan_id)
                 if s.oturum_id == satir.oturum_id)
    assert satir.son_gun() > olagan


def test_tatil_silinebilir(vt) -> None:
    kimlik = hizmet.tatil_ekle(vt, date(2026, 10, 29), "Cumhuriyet Bayramı")
    assert date(2026, 10, 29) in hizmet.tatilleri_getir(vt)
    hizmet.tatil_sil(vt, kimlik)
    assert date(2026, 10, 29) not in hizmet.tatilleri_getir(vt)


# ========================================================= öğretmen müsaitliği

def test_musaitlik_kaydi_dogrulanir(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    kisi = hizmet.personelleri_getir(vt)[0]
    with pytest.raises(HizmetHatasi, match="ya haftanın bir günü ya da"):
        hizmet.musaitlik_ekle(vt, kisi.kimlik)
    with pytest.raises(HizmetHatasi, match="sonu başından sonra"):
        hizmet.musaitlik_ekle(vt, kisi.kimlik, hafta_gunu=0, bas_saat=time(12, 0),
                              bit_saat=time(8, 0))
    kimlik = hizmet.musaitlik_ekle(vt, kisi.kimlik, hafta_gunu=0, bas_saat=time(8, 0),
                                   bit_saat=time(12, 0), aciklama="Ders")
    liste = hizmet.musaitlik_listesi(vt, kisi.kimlik)
    assert liste[0]["zaman"] == "Her pazartesi" and liste[0]["saat"] == "08:00–12:00"
    hizmet.musaitlik_sil(vt, kimlik)
    assert hizmet.musaitlik_listesi(vt, kisi.kimlik) == []


def test_plan_musait_olmayan_ogretmene_gorev_vermez(vt, tmp_path: Path) -> None:
    """OKY md.58/2-ç: dersleri aksatmayacak şekilde."""
    _kur(vt, tmp_path)
    hedef = next(p for p in hizmet.personelleri_getir(vt) if p.ad == "Uydurma Matematikçi")
    for gun in range(5):
        hizmet.musaitlik_ekle(vt, hedef.kimlik, hafta_gunu=gun)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    assert hedef.kimlik not in {g.personel_kimligi for g in sonuc.plan.gorevlendirmeler}
    assert not [i for i in sonuc.ihlaller if i.kural_kimligi == "SP-09"]


# ===================================================== başvuru işaretinin yılı

def test_onceki_yildan_kalan_isaret_gozden_gecirilmek_uzere_bildirilir(vt, tmp_path) -> None:
    _kur(vt, tmp_path)
    ogrenci = hizmet.basvuru_tablosu(vt, "P1")[0]
    hizmet.ogrenci_bayrak_guncelle(vt, ogrenci["ogrenci_id"], True, False)
    assert hizmet.eski_yildan_isaretler(vt) == []
    hizmet.ayarlari_kaydet(vt, dict(AYARLAR, ogretim_yili="2027-2028"))
    eskiler = hizmet.eski_yildan_isaretler(vt)
    assert [e["ogrenci_id"] for e in eskiler] == [ogrenci["ogrenci_id"]]
    assert "önceki öğretim yılından" in hizmet.isaret_tazeligi_uyarisi(vt)
    satir = next(s for s in hizmet.basvuru_tablosu(vt, "P1")
                 if s["ogrenci_id"] == ogrenci["ogrenci_id"])
    assert satir["eski_isaret_mi"] and "gözden geçirin" in satir["grup_ekran"]
    assert "gözden geçirin" not in satir["grup"]          # tutanak sade kalır
    # Yeniden kaydetmek yılı günceller.
    hizmet.ogrenci_bayrak_guncelle(vt, ogrenci["ogrenci_id"], True, False)
    assert hizmet.eski_yildan_isaretler(vt) == []


# ===================================================== varsayılan dönem, yedek

def test_varsayilan_donem_tarihe_gore_secilir() -> None:
    pencereler = {"P1": (date(2026, 9, 14), date(2026, 9, 27)),
                  "P2": (date(2027, 2, 8), date(2027, 2, 21)),
                  "P3": (date(2027, 6, 12), date(2027, 6, 25))}
    assert varsayilan_pencere_kodu(pencereler, date(2026, 9, 1)) == "P1"
    assert varsayilan_pencere_kodu(pencereler, date(2026, 10, 3)) == "P2"
    assert varsayilan_pencere_kodu(pencereler, date(2026, 10, 3), gecmise_bak=True) == "P1"
    assert varsayilan_pencere_kodu(pencereler, date(2027, 8, 1)) == "P3"


def test_tek_ders_penceresi_takip_eden_haftadir() -> None:
    """OKY md.58/6: takip eden hafta içinde."""
    assert tek_ders_penceresi(date(2026, 9, 23)) == (date(2026, 9, 28), date(2026, 10, 4))
    assert tek_ders_penceresi(date(2026, 9, 25)) == (date(2026, 9, 28), date(2026, 10, 4))


def test_yedek_alinir(vt, tmp_path: Path) -> None:
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    yol = hizmet.yedek_al(vt, tmp_path / "yedekler")
    assert yol.exists() and yol.stat().st_size > 0
