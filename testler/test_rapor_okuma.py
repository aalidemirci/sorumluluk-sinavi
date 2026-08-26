from __future__ import annotations

from pathlib import Path

import pytest

from cekirdek.metin import esitle, kucult, siralama_anahtari
from veri.rapor_okuma import (
    RaporHatasi, personel_raporu_coz, sorumluluk_raporu_coz, sorumluluk_raporu_oku, tablo_oku,
)
from testler.yardimci import ORNEK_PERSONEL, ornek_sorumluluk_csv, personel_satirlari


# ------------------------------------------------------------- Türkçe metin

def test_turkce_kucultme_i_harfini_bozmaz() -> None:
    assert kucult("İSTANBUL") == "istanbul"
    assert kucult("IĞDIR") == "ığdır"
    assert esitle("  Müdür   Yardımcısı ") == "müdür yardımcısı"


def test_turkce_siralama_c_ile_ch_arasini_ayirir() -> None:
    adlar = ["Zeynep", "Çiğdem", "Ahmet", "İlker", "Irmak", "Ömer"]
    assert sorted(adlar, key=siralama_anahtari) == [
        "Ahmet", "Çiğdem", "Irmak", "İlker", "Ömer", "Zeynep",
    ]


# -------------------------------------------------------- sorumluluk raporu

def test_sorumluluk_raporu_sube_ogrenci_ve_ders_cikarir(tmp_path: Path) -> None:
    rapor = sorumluluk_raporu_oku(ornek_sorumluluk_csv(tmp_path / "ornek.csv"))
    assert len(rapor.kayitlar) == 6
    assert rapor.ogrenci_sayisi == 3
    assert rapor.sube_sayisi == 2
    assert rapor.ders_duzey_sayisi == 5
    assert rapor.subeler == ("9/A", "10/B")


def test_ogrenci_no_ve_ad_izleyen_satirlara_tasinir(tmp_path: Path) -> None:
    """Rapor öğrenci bilgisini yalnız ilk ders satırında yazar."""
    rapor = sorumluluk_raporu_oku(ornek_sorumluluk_csv(tmp_path / "ornek.csv"))
    birinci = [k for k in rapor.kayitlar if k.okul_no == "101"]
    assert len(birinci) == 2
    assert {k.ders_adi for k in birinci} == {"MATEMATİK", "FİZİK"}
    assert all(k.ad_soyad == "Uydurma Öğrenci Bir" for k in birinci)


def test_ogrenci_yuku_hesabi_planlama_penceresini_belirler(tmp_path: Path) -> None:
    rapor = sorumluluk_raporu_oku(ornek_sorumluluk_csv(tmp_path / "ornek.csv"))
    assert rapor.ogrenci_yukleri() == {"101|9/A": 2, "102|9/A": 1, "201|10/B": 3}
    assert rapor.azami_ogrenci_yuku == 3


def test_excel_sayisal_ogrenci_no_ondaliktan_arindirilir() -> None:
    satirlar = [
        ["Uydurma Lisesi - 9. Sınıf / A Şubesi"],
        ["", "Öğrenci No", "Adı Soyadı", "", "", "", "", "", "Sınıfı", "Dersi"],
        ["", "1234.0", "Uydurma Öğrenci", "", "", "", "", "", "9.0", "MATEMATİK"],
    ]
    rapor = sorumluluk_raporu_coz(satirlar, "ozet")
    assert rapor.kayitlar[0].okul_no == "1234"
    assert rapor.kayitlar[0].sinif_duzeyi == 9


def test_sube_basligi_olmayan_dosya_anlasilir_hata_verir() -> None:
    with pytest.raises(RaporHatasi, match="OOK12001R010"):
        sorumluluk_raporu_coz([["rastgele"], ["içerik"]], "ozet")


def test_desteklenmeyen_bicim_reddedilir(tmp_path: Path) -> None:
    hedef = tmp_path / "rapor.txt"
    hedef.write_text("veri", encoding="utf-8")
    with pytest.raises(RaporHatasi, match="desteklenir"):
        tablo_oku(hedef)


# ------------------------------------------------------------ personel raporu

def test_personel_raporu_baslik_satirini_bulur() -> None:
    rapor = personel_raporu_coz(personel_satirlari(ORNEK_PERSONEL), "ozet")
    assert len(rapor.kayitlar) == len(ORNEK_PERSONEL)
    assert rapor.yonetici_sayisi == 2
    assert rapor.ogretmen_sayisi == len(ORNEK_PERSONEL) - 2
    assert "Rehberlik" in rapor.branslar()


def test_personel_tipi_kadro_durumundan_cikarilir() -> None:
    rapor = personel_raporu_coz(personel_satirlari(ORNEK_PERSONEL), "ozet")
    tipler = {k.ad: k.personel_tipi for k in rapor.kayitlar}
    assert tipler["Uydurma Edebiyatçı"] == "sozlesmeli"
    assert tipler["Uydurma Matematikçi"] == "kadrolu"


def test_toplam_satiri_personel_sayilmaz() -> None:
    rapor = personel_raporu_coz(personel_satirlari(ORNEK_PERSONEL), "ozet")
    assert all("toplam" not in esitle(k.ad) for k in rapor.kayitlar)


def test_ayni_adli_iki_personel_sicilsiz_kabul_edilmez() -> None:
    ikiz = ORNEK_PERSONEL + [("Uydurma Matematikçi", "Öğretmen", "Kadrolu", "Kimya")]
    with pytest.raises(RaporHatasi, match="kurum sicil numarası"):
        personel_raporu_coz(personel_satirlari(ikiz), "ozet")


def test_eksik_zorunlu_alan_satir_numarasiyla_bildirilir() -> None:
    eksik = [("Uydurma Kişi", "Öğretmen", "", "Matematik")]
    with pytest.raises(RaporHatasi, match="zorunlu personel alanı eksik"):
        personel_raporu_coz(personel_satirlari(eksik), "ozet")


def test_baslik_bulunamazsa_anlasilir_hata_verir() -> None:
    with pytest.raises(RaporHatasi, match="Personel Listesi başlıkları"):
        personel_raporu_coz([["rastgele"], ["içerik"]], "ozet")
