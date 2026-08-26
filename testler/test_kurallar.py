"""Kural katmanı testleri.

Her kural için en az bir *olumsuz* senaryo vardır. Kuralın yalnız tanımlı
olduğunu ya da mutlu yolda geçtiğini sınamak bir şey kanıtlamaz.
"""

from __future__ import annotations

import pytest

from cekirdek.kurallar import (
    BIRLESTIRME_UST_SINIRI, KURALLAR, Ciddiyet, DogrulamaBaglami,
    dogrula_plan, engelleri_ayikla, gereken_salon_sayisi, gunluk_sinav_yuku,
    yillik_sayac_asildi_mi,
)
from cekirdek.modeller import (
    Gorevlendirme, GorevRolu, IkiAsamaliSayim, OturumTuru, Salon,
)
from testler.yardimci import PERSONEL, SALONLAR, baglam, gorevler, kimlikler, oturum, plan


# ------------------------------------------------------------ kural kayıtları

def test_her_kuralin_dayanagi_ve_ciddiyeti_vardir() -> None:
    for kimlik, tanim in KURALLAR.items():
        assert tanim.kimlik == kimlik
        assert tanim.dayanak.strip(), f"{kimlik} dayanaksız"
        assert tanim.aciklama.strip(), f"{kimlik} açıklamasız"
        assert isinstance(tanim.ciddiyet, Ciddiyet)


def test_kural_kimlikleri_beklenen_kumedir() -> None:
    assert set(KURALLAR) == {
        "SG-05", "SG-06",
        "SP-01", "SP-02", "SP-03", "SP-04", "SP-05", "SP-06", "SP-07",
        "SP-10", "SP-11", "SP-12", "SP-14",
        "EK-03", "EK-04", "EK-05",
        "TS-01", "TS-02", "TS-03",
    }


# ------------------------------------------------------------ salon hesabı

def test_salon_sayisi_gercek_kapasitelerden_hesaplanir() -> None:
    salonlar = [Salon(1, "A", 30), Salon(2, "B", 30), Salon(3, "C", 20)]
    assert gereken_salon_sayisi(25, salonlar) == 1
    assert gereken_salon_sayisi(30, salonlar) == 1
    assert gereken_salon_sayisi(31, salonlar) == 2
    assert gereken_salon_sayisi(61, salonlar) == 3


def test_salon_ust_siniri_kapasiteden_kucukse_o_uygulanir() -> None:
    """Salon 100 kişilikse bile varsayılan olarak bir salona 30'dan fazla
    öğrenci konmaz; md.58/2-b her salon için ayrı gözcü ister."""
    buyuk = [Salon(1, "Konferans", 100), Salon(2, "Konferans İki", 100)]
    assert gereken_salon_sayisi(45, buyuk, salon_ust_siniri=30) == 2
    # Okul üst sınırı yükseltirse tek salon yeter.
    assert gereken_salon_sayisi(45, buyuk, salon_ust_siniri=50) == 1


def test_tek_salon_ust_siniri_kadar_ogrenci_alir() -> None:
    tek = [Salon(1, "Konferans", 100)]
    assert gereken_salon_sayisi(30, tek, salon_ust_siniri=30) == 1
    with pytest.raises(ValueError, match="salonlar yetersiz"):
        gereken_salon_sayisi(31, tek, salon_ust_siniri=30)


def test_salon_yetersizse_anlasilir_hata_verir() -> None:
    with pytest.raises(ValueError, match="salonlar yetersiz"):
        gereken_salon_sayisi(200, [Salon(1, "A", 30)])


# ------------------------------------------------------------ SP-01 pencere

def test_sp01_pencere_disina_dusen_oturum_engeldir() -> None:
    sonuc = dogrula_plan(plan([oturum("a", "MATEMATİK", ["101|9/A"], gun=30)]), baglam())
    assert "SP-01" in kimlikler(sonuc)
    assert engelleri_ayikla(sonuc)


def test_sp01_pencere_icindeki_oturum_ihlal_uretmez() -> None:
    sonuc = dogrula_plan(plan([oturum("a", "MATEMATİK", ["101|9/A"])]), baglam())
    assert "SP-01" not in kimlikler(sonuc)


# ------------------------------------------------------- SP-04 birleştirme

def test_sp04_ayni_ogrenci_iki_duzeyden_birlesik_oturuma_konamaz() -> None:
    """OKY md.58/2-c ek cümlesi: çakışan öğrenciler ayrı ayrı sınava alınır."""
    birlesik = oturum("a", "MATEMATİK", ["101|9/A", "101|10/A"], duzeyler=(9, 10))
    sonuc = dogrula_plan(plan([birlesik]), baglam())
    assert "SP-04" in kimlikler(sonuc)
    assert engelleri_ayikla(sonuc)


def test_sp04_birlestirme_otuz_ogrenciyi_asamaz() -> None:
    ogrenciler = [f"{100 + i}|9/A" for i in range(BIRLESTIRME_UST_SINIRI + 1)]
    birlesik = oturum("a", "MATEMATİK", ogrenciler, duzeyler=(9, 10), salonlar=(1, 2))
    ihlaller = [i for i in dogrula_plan(plan([birlesik]), baglam()) if i.kural_kimligi == "SP-04"]
    assert ihlaller and "birleştirme sınırı" in ihlaller[0].aciklama


def test_sp04_tek_duzeyde_otuzdan_fazla_ogrenci_sorun_degil() -> None:
    """Birleştirme sınırı yalnız düzey birleştirmede geçerlidir."""
    ogrenciler = [f"{100 + i}|9/A" for i in range(BIRLESTIRME_UST_SINIRI + 5)]
    tek = oturum("a", "MATEMATİK", ogrenciler, duzeyler=(9,), salonlar=(1, 2))
    assert "SP-04" not in kimlikler(dogrula_plan(plan([tek]), baglam()))


# ------------------------------------------------------------ SP-05 hafta sonu

def test_sp05_gerekcesiz_hafta_sonu_oturumu_engeldir() -> None:
    # 19.09.2026 cumartesi
    sonuc = dogrula_plan(plan([oturum("a", "MATEMATİK", ["101|9/A"], gun=19)]), baglam())
    assert "SP-05" in kimlikler(sonuc)


def test_sp05_gerekceli_hafta_sonu_oturumu_kabul_edilir() -> None:
    cumartesi = oturum("a", "MATEMATİK", ["101|9/A"], gun=19,
                       hafta_sonu_gerekcesi="Hafta içi pencere kapasitesi yetersiz kaldı.")
    assert "SP-05" not in kimlikler(dogrula_plan(plan([cumartesi]), baglam()))


# ---------------------------------------------------------- SP-06 iki aşamalı

def test_sp06_iki_asamali_derste_uygulama_oturumu_eksikse_engeldir() -> None:
    """OKY md.58/2-e — eski sürümde bu kural hiç çalışmıyordu."""
    yalniz_yazili = oturum("a", "TÜRK DİLİ VE EDEBİYATI", ["101|9/A"],
                           brans="Türk Dili ve Edebiyatı", birim="tde-9")
    sonuc = dogrula_plan(plan([yalniz_yazili]),
                         baglam(iki_asamali_dersler=frozenset({"TÜRK DİLİ VE EDEBİYATI"})))
    assert "SP-06" in kimlikler(sonuc)
    assert engelleri_ayikla(sonuc)


def test_sp06_yazili_ve_uygulama_birlikteyse_gecerlidir() -> None:
    ortak = dict(ders="TÜRK DİLİ VE EDEBİYATI", ogrenciler=["101|9/A"],
                 brans="Türk Dili ve Edebiyatı", birim="tde-9")
    ikisi = [oturum("a", saat=(9, 0), tur=OturumTuru.YAZILI, **ortak),
             oturum("b", saat=(10, 0), tur=OturumTuru.UYGULAMA, **ortak)]
    assert "SP-06" not in kimlikler(
        dogrula_plan(plan(ikisi), baglam(iki_asamali_dersler=frozenset({ortak["ders"]}))))


def test_sp06_komisyonlarin_farkli_olmasi_uyari_uretir() -> None:
    """Komisyonların aynı üyelerden oluşturulması esastır."""
    ortak = dict(ders="TÜRK DİLİ VE EDEBİYATI", ogrenciler=["101|9/A"],
                 brans="Türk Dili ve Edebiyatı", birim="tde-9")
    ikisi = [oturum("a", saat=(9, 0), tur=OturumTuru.YAZILI, **ortak),
             oturum("b", saat=(10, 0), tur=OturumTuru.UYGULAMA, **ortak)]
    atamalar = gorevler("a", komisyon=(5, 1), gozcu=(3,)) + gorevler("b", komisyon=(5, 2), gozcu=(4,))
    sonuc = dogrula_plan(plan(ikisi, atamalar),
                         baglam(iki_asamali_dersler=frozenset({ortak["ders"]})))
    sp06 = [i for i in sonuc if i.kural_kimligi == "SP-06"]
    assert sp06 and sp06[0].ciddiyet is Ciddiyet.UYARI


# ------------------------------------------------------------- SP-10 süre

def test_sp10_bir_ders_saatini_asan_sinav_engeldir() -> None:
    sonuc = dogrula_plan(plan([oturum("a", "MATEMATİK", ["101|9/A"], sure=60)]), baglam())
    assert "SP-10" in kimlikler(sonuc)


# -------------------------------------------------------- SP-11 günlük yük

def test_sp11_gunluk_sinir_asiminda_ogrenci_gun_ve_sinavlar_yazilir() -> None:
    ayni_gun = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0)),
        oturum("b", "FİZİK", ["101|9/A"], saat=(10, 0), brans="Fizik"),
        oturum("c", "KİMYA", ["101|9/A"], saat=(11, 0), brans="Kimya"),
    ]
    sonuc = dogrula_plan(plan(ayni_gun),
                         baglam(ogrenci_adlari={"101|9/A": "Uydurma Öğrenci (No: 101, 9/A)"}))
    sp11 = [i for i in sonuc if i.kural_kimligi == "SP-11"]
    assert sp11
    aciklama = sp11[0].aciklama
    assert "Uydurma Öğrenci (No: 101, 9/A)" in aciklama
    assert "14.09.2026" in aciklama
    assert "MATEMATİK" in aciklama and "KİMYA" in aciklama


def test_sp11_kisisel_sinir_yukseltilen_ogrenci_ihlal_uretmez() -> None:
    """Çok sayıda sorumlu dersi olan öğrencinin sınırı yükseltilir."""
    ayni_gun = [
        oturum("a", "MATEMATİK", ["101|12/B"], saat=(9, 0)),
        oturum("b", "FİZİK", ["101|12/B"], saat=(10, 0), brans="Fizik"),
        oturum("c", "KİMYA", ["101|12/B"], saat=(11, 0), brans="Kimya"),
        oturum("d", "TARİH", ["101|12/B"], saat=(13, 30), brans="Tarih"),
    ]
    sonuc = dogrula_plan(plan(ayni_gun), baglam(kisisel_gunluk_sinir={"101|12/B": 4}))
    assert "SP-11" not in kimlikler(sonuc)


def test_sp11_iki_asamali_ders_tek_sinav_sayilir() -> None:
    """Varsayılan sayımda yazılı+uygulama tek sınavdır; öğrencinin o gün üç
    oturumu olsa da iki sınavı sayılır."""
    oturumlar = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0)),
        oturum("b", "İNGİLİZCE", ["101|9/A"], saat=(10, 0), brans="İngilizce",
               birim="ing-9", tur=OturumTuru.YAZILI),
        oturum("c", "İNGİLİZCE", ["101|9/A"], saat=(11, 0), brans="İngilizce",
               birim="ing-9", tur=OturumTuru.UYGULAMA),
    ]
    tek = gunluk_sinav_yuku(oturumlar, IkiAsamaliSayim.TEK)
    ayri = gunluk_sinav_yuku(oturumlar, IkiAsamaliSayim.AYRI)
    assert list(tek.values()) == [2]
    assert list(ayri.values()) == [3]


def test_sp11_ayri_sayim_secilirse_sinir_asilir() -> None:
    oturumlar = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0)),
        oturum("b", "İNGİLİZCE", ["101|9/A"], saat=(10, 0), brans="İngilizce", birim="ing-9"),
        oturum("c", "İNGİLİZCE", ["101|9/A"], saat=(11, 0), brans="İngilizce",
               birim="ing-9", tur=OturumTuru.UYGULAMA),
    ]
    tek_sayim = dogrula_plan(plan(oturumlar, iki_asamali_sayim=IkiAsamaliSayim.TEK), baglam())
    ayri_sayim = dogrula_plan(plan(oturumlar, iki_asamali_sayim=IkiAsamaliSayim.AYRI), baglam())
    assert "SP-11" not in kimlikler(tek_sayim)
    assert "SP-11" in kimlikler(ayri_sayim)


def test_ogrenci_ayni_saatte_iki_sinavda_olamaz() -> None:
    cakisan = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0)),
        oturum("b", "FİZİK", ["101|9/A"], saat=(9, 0), brans="Fizik", salonlar=(2,)),
    ]
    sonuc = dogrula_plan(plan(cakisan), baglam())
    assert engelleri_ayikla(sonuc)
    assert any("aynı anda iki sınavda" in i.aciklama for i in sonuc)


# --------------------------------------------------- SP-02 / SP-03 görev

def test_sp02_tek_komisyon_uyesi_engeldir() -> None:
    tek = oturum("a", "MATEMATİK", ["101|9/A"])
    sonuc = dogrula_plan(plan([tek], gorevler("a", komisyon=(1,), gozcu=(3,))), baglam())
    assert "SP-02" in kimlikler(sonuc)


def test_sp02_alan_ogretmeni_yoksa_engeldir() -> None:
    tek = oturum("a", "MATEMATİK", ["101|9/A"])
    sonuc = dogrula_plan(plan([tek], gorevler("a", komisyon=(3, 4), gozcu=(5,))), baglam())
    assert any("alanından öğretmen yok" in i.aciklama for i in sonuc)


def test_sp02_tek_alan_ogretmeninde_gerekce_zorunludur() -> None:
    tek = oturum("a", "MATEMATİK", ["101|9/A"])
    gerekcesiz = dogrula_plan(plan([tek], gorevler("a", komisyon=(1, 3), gozcu=(4,))), baglam())
    assert any("gerekçe alanına" in i.aciklama for i in gerekcesiz)
    gerekceli = dogrula_plan(
        plan([tek], gorevler("a", komisyon=(1, 3), gozcu=(4,),
                             gerekce="Okulda ikinci Matematik öğretmeni yok.")), baglam())
    assert not any("gerekçe alanına" in i.aciklama for i in gerekceli)


def test_sp03_gozcu_sayisi_salon_sayisina_esit_olmalidir() -> None:
    iki_salon = oturum("a", "MATEMATİK", [f"{100 + i}|9/A" for i in range(40)], salonlar=(1, 2))
    sonuc = dogrula_plan(plan([iki_salon], gorevler("a", komisyon=(1, 2), gozcu=(3,))), baglam())
    assert "SP-03" in kimlikler(sonuc)


def test_mudure_ve_rehber_ogretmene_gorev_verilemez() -> None:
    tek = oturum("a", "MATEMATİK", ["101|9/A"])
    sonuc = dogrula_plan(plan([tek], gorevler("a", komisyon=(1, 7), gozcu=(8,))), baglam())
    assert any("Müdüre sınav görevi verilemez" in i.aciklama for i in sonuc)
    assert any("Rehber öğretmene sınav görevi verilemez" in i.aciklama for i in sonuc)


def test_ek03_ayni_kisi_bir_oturumda_iki_rol_alamaz() -> None:
    tek = oturum("a", "MATEMATİK", ["101|9/A"])
    cifte = gorevler("a", komisyon=(1, 2), gozcu=()) + [
        Gorevlendirme("a", 1, GorevRolu.GOZCU)]
    sonuc = dogrula_plan(plan([tek], cifte), baglam())
    assert "EK-03" in kimlikler(sonuc)


def test_ogretmen_ayni_saatte_iki_oturumda_gorevli_olamaz() -> None:
    paralel = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0), salonlar=(1,)),
        oturum("b", "FİZİK", ["201|9/B"], saat=(9, 0), brans="Fizik", salonlar=(2,)),
    ]
    atamalar = gorevler("a", komisyon=(1, 2), gozcu=(3,)) + gorevler("b", komisyon=(3, 4), gozcu=(5,))
    sonuc = dogrula_plan(plan(paralel, atamalar), baglam())
    assert any("aynı anda iki sınavda görevli" in i.aciklama for i in sonuc)


def test_paralel_oturumlar_farkli_gorevlilerle_gecerlidir() -> None:
    """Ders programı kısıtı kalkınca aynı saatte birden fazla sınav yapılabilir."""
    paralel = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0), salonlar=(1,)),
        oturum("b", "KİMYA", ["201|9/B"], saat=(9, 0), brans="Kimya", salonlar=(2,)),
    ]
    atamalar = (gorevler("a", komisyon=(1, 2), gozcu=(3,))
                + gorevler("b", komisyon=(4, 6), gozcu=(5,),
                           gerekce="Okulda ikinci Kimya öğretmeni yok."))
    assert not engelleri_ayikla(dogrula_plan(plan(paralel, atamalar), baglam(), SALONLAR))


def test_ayni_salon_ayni_saatte_iki_sinava_ayrilamaz() -> None:
    paralel = [
        oturum("a", "MATEMATİK", ["101|9/A"], saat=(9, 0), salonlar=(1,)),
        oturum("b", "KİMYA", ["201|9/B"], saat=(9, 0), brans="Kimya", salonlar=(1,)),
    ]
    sonuc = dogrula_plan(plan(paralel), baglam(), SALONLAR)
    assert any("A-101 salonu" in i.aciklama for i in sonuc)


# ------------------------------------------------------------- EK-05 sayaç

def test_ek05_sinirsiz_ogretim_yillarinda_sayac_asimi_bildirilmez() -> None:
    assert not yillik_sayac_asildi_mi("2026-2027", 99, 99)
    assert yillik_sayac_asildi_mi("2027-2028", 13, 0)
    assert yillik_sayac_asildi_mi("2027-2028", 0, 16)
    assert not yillik_sayac_asildi_mi("2027-2028", 12, 15)


def test_ek05_sinir_asiminda_uyari_uretilir() -> None:
    oturumlar = [oturum(f"o{i}", "MATEMATİK", ["101|9/A"], gun=14 + i % 10, saat=(9, 0))
                 for i in range(13)]
    atamalar = [Gorevlendirme(o.anahtar, 1, GorevRolu.KOMISYON_UYESI) for o in oturumlar]
    sonuc = dogrula_plan(plan(oturumlar, atamalar), baglam(ogretim_yili="2027-2028"))
    ek05 = [i for i in sonuc if i.kural_kimligi == "EK-05"]
    assert ek05 and "13 komisyon üyeliği" in ek05[0].aciklama


def test_ek05_sinirsiz_yilda_plan_uyari_uretmez() -> None:
    oturumlar = [oturum(f"o{i}", "MATEMATİK", ["101|9/A"], gun=14 + i % 10, saat=(9, 0))
                 for i in range(13)]
    atamalar = [Gorevlendirme(o.anahtar, 1, GorevRolu.KOMISYON_UYESI) for o in oturumlar]
    sonuc = dogrula_plan(plan(oturumlar, atamalar), baglam(ogretim_yili="2026-2027"))
    assert "EK-05" not in kimlikler(sonuc)


# --------------------------------------------------------------- sıralama

def test_ihlaller_once_engel_sonra_uyari_siralanir() -> None:
    karisik = [
        oturum("a", "MATEMATİK", ["101|9/A"], gun=19),   # SP-05 engel
        oturum("b", "FİZİK", ["101|9/A"], gun=30, brans="Fizik"),  # SP-01 engel
    ]
    sonuc = dogrula_plan(plan(karisik), baglam())
    ciddiyetler = [i.ciddiyet for i in sonuc]
    assert ciddiyetler == sorted(ciddiyetler, key=lambda c: {"ENGEL": 0, "UYARI": 1, "BILGI": 2}[c.value])


def test_kurallar_bos_planda_ihlal_uretmez() -> None:
    assert dogrula_plan(plan([]), baglam()) == []
