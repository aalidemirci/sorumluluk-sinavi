"""Talep oluşturma ve planlama motoru testleri."""

from __future__ import annotations

from datetime import date, time

import pytest

from cekirdek.kurallar import engelleri_ayikla
from cekirdek.modeller import (
    DersAyari, GorevRolu, IkiAsamaliSayim, OturumTuru, Personel, PlanParametreleri, Salon,
    SorumlulukKaydi,
)
from cekirdek.planlayici import PlanlamaBasarisiz, plan_uret, sinir_onizlemesi
from cekirdek.takvim import gunleri_listele, sinav_pencereleri
from cekirdek.talep import birimleri_olustur, yuk_ozeti


PENCERE = sinav_pencereleri(date(2026, 9, 14), date(2027, 2, 8), date(2027, 6, 25))["P1"]
SALONLAR = [Salon(i, f"D-{i:02d}", 30) for i in range(1, 5)]


def kayit(no: str, sube: str, duzey: int, ders: str) -> SorumlulukKaydi:
    return SorumlulukKaydi(no, f"Uydurma Öğrenci {no}", sube, duzey, ders)


def personel_kadrosu(dagilim: dict[str, int]) -> list[Personel]:
    kisiler, kimlik = [], 0
    for brans, adet in dagilim.items():
        for sira in range(adet):
            kimlik += 1
            kisiler.append(Personel(kimlik, f"{brans} Öğretmeni {sira + 1}", brans, "Öğretmen"))
    return kisiler


# ============================================================ birim oluşturma

def test_tek_asamali_ders_tek_oturum_uretir() -> None:
    kayitlar = [kayit("101", "9/A", 9, "MATEMATİK")]
    birimler = birimleri_olustur(kayitlar, {"MATEMATİK": DersAyari("Matematik")}, SALONLAR)
    assert len(birimler) == 1
    assert birimler[0].oturum_turleri == (OturumTuru.YAZILI,)
    assert birimler[0].slot_ihtiyaci == 1


def test_iki_asamali_ders_yazili_ve_uygulama_uretir() -> None:
    """OKY md.58/2-e — eski sürümde bu yalnız sabit yazılmış ders adı için
    çalışıyor, yabancı dil dersleri tek oturum kalıyordu."""
    kayitlar = [kayit("101", "9/A", 9, "İNGİLİZCE")]
    ayar = {"İNGİLİZCE": DersAyari("İngilizce", iki_asamali_mi=True, yabanci_dil_mi=True)}
    birimler = birimleri_olustur(kayitlar, ayar, SALONLAR)
    assert birimler[0].oturum_turleri == (OturumTuru.YAZILI, OturumTuru.UYGULAMA)
    assert birimler[0].slot_ihtiyaci == 2


def test_duzeyler_otuz_ogrenciye_kadar_birlestirilir() -> None:
    """OKY md.58/2-c: toplam otuzu aşmıyorsa tek komisyonla yapılabilir."""
    kayitlar = ([kayit(f"1{i:02d}", "9/A", 9, "MATEMATİK") for i in range(10)]
                + [kayit(f"2{i:02d}", "10/A", 10, "MATEMATİK") for i in range(10)])
    birimler = birimleri_olustur(kayitlar, {"MATEMATİK": DersAyari("Matematik")}, SALONLAR)
    assert len(birimler) == 1
    assert birimler[0].duzeyler == (9, 10)


def test_otuzu_asan_duzeyler_birlestirilmez() -> None:
    kayitlar = ([kayit(f"1{i:02d}", "9/A", 9, "MATEMATİK") for i in range(20)]
                + [kayit(f"2{i:02d}", "10/A", 10, "MATEMATİK") for i in range(20)])
    birimler = birimleri_olustur(kayitlar, {"MATEMATİK": DersAyari("Matematik")}, SALONLAR)
    assert len(birimler) == 2
    assert sorted(b.duzeyler for b in birimler) == [(9,), (10,)]


def test_ortak_ogrencisi_olan_duzeyler_birlestirilmez() -> None:
    """md.58/2-c ek cümlesi: çakışan öğrenciler ayrı ayrı sınava alınır."""
    kayitlar = [kayit("101", "9/A", 9, "MATEMATİK"), kayit("101", "9/A", 10, "MATEMATİK")]
    birimler = birimleri_olustur(kayitlar, {"MATEMATİK": DersAyari("Matematik")}, SALONLAR)
    assert len(birimler) == 2


def test_brans_eslemesi_eksik_ders_plan_uretimini_durdurur() -> None:
    kayitlar = [kayit("101", "9/A", 9, "MATEMATİK")]
    with pytest.raises(ValueError, match="branş eşlemesi"):
        birimleri_olustur(kayitlar, {"MATEMATİK": DersAyari("  ")}, SALONLAR)


def test_salon_sayisi_ogrenci_sayisindan_hesaplanir() -> None:
    kayitlar = [kayit(f"{i:03d}", "9/A", 9, "MATEMATİK") for i in range(45)]
    birimler = birimleri_olustur(kayitlar, {"MATEMATİK": DersAyari("Matematik")}, SALONLAR)
    assert birimler[0].salon_sayisi == 2
    assert birimler[0].gorevli_ihtiyaci == 4  # 2 komisyon + 2 gözcü


# ================================================================= yük özeti

def test_yuk_ozeti_iki_asamali_sayimi_uygular() -> None:
    kayitlar = [kayit("101", "9/A", 9, "İNGİLİZCE"), kayit("101", "9/A", 9, "MATEMATİK")]
    ayar = {"İNGİLİZCE": DersAyari("İngilizce", iki_asamali_mi=True),
            "MATEMATİK": DersAyari("Matematik")}
    birimler = birimleri_olustur(kayitlar, ayar, SALONLAR)
    assert yuk_ozeti(birimler, IkiAsamaliSayim.TEK, 2).azami_yuk == 2
    assert yuk_ozeti(birimler, IkiAsamaliSayim.AYRI, 2).azami_yuk == 3


def test_pencere_onerisi_cogunluga_gore_secilir() -> None:
    """Bir hafta = 5 iş günü × 2 sınav = 10; iki hafta = 20."""
    ozet = yuk_ozeti([], IkiAsamaliSayim.TEK, 2)
    ozet = type(ozet)({f"o{i}": 10 for i in range(100)}, 2)
    assert ozet.onerilen_gun_sayisi(6) == 5
    ozet = type(ozet)({f"o{i}": 20 for i in range(100)}, 2)
    assert ozet.onerilen_gun_sayisi(6) == 10


def test_asiri_yuklu_azinlik_pencereyi_belirlemez() -> None:
    """%99'u 5 dersli, üç öğrenci 26-31 dersli olan gerçek dağılım."""
    yukler = {f"o{i}": 5 for i in range(337)}
    yukler.update({"agir1": 31, "agir2": 26, "agir3": 12})
    ozet = yuk_ozeti([], IkiAsamaliSayim.TEK, 2)
    ozet = type(ozet)(yukler, 2)
    assert ozet.cogunluk_yuku == 5
    assert ozet.azami_yuk == 31
    # Çoğunluk bir haftaya sığar ama 31 dersli öğrenci günde 6 slotla en az
    # 6 gün ister; öneri bu tabanın altına inemez.
    assert ozet.asgari_gun_sayisi(6) == 6
    assert ozet.onerilen_gun_sayisi(6) == 6


def test_kisisel_sinir_yalniz_sigmayan_ogrenci_icin_yukseltilir() -> None:
    ozet = yuk_ozeti([], IkiAsamaliSayim.TEK, 2)
    ozet = type(ozet)({"normal": 5, "agir": 31}, 2)
    sinirlar = ozet.kisisel_sinirlar(10)
    assert "normal" not in sinirlar          # 5 sınav / 10 gün → sınır 2 yeterli
    assert sinirlar["agir"] == 4             # 31 / 10 = 3,1 → en düşük 4


def test_gunluk_slot_sayisini_asan_sinir_reddedilir() -> None:
    ozet = yuk_ozeti([], IkiAsamaliSayim.TEK, 2)
    ozet = type(ozet)({"agir": 31}, 2)
    with pytest.raises(ValueError, match="oturum saati var"):
        ozet.kisisel_sinirlar(5, slot_sayisi=6)   # 31/5 → günde 7 gerekir


def test_sinir_onizlemesi_uygulanamayan_secenegi_isaretler() -> None:
    ozet = yuk_ozeti([], IkiAsamaliSayim.TEK, 2)
    ozet = type(ozet)({"agir": 31}, 2)
    onizleme = {o.gun_sayisi: o for o in sinir_onizlemesi(ozet, [5, 10], 6)}
    assert not onizleme[5].uygulanabilir_mi      # günde 7 sınav, 6 slot var
    assert onizleme[10].uygulanabilir_mi
    assert onizleme[10].en_yuksek_sinir == 4


# =============================================================== plan üretme

@pytest.fixture()
def kucuk_senaryo():
    kayitlar = []
    for sira in range(12):
        kayitlar.append(kayit(f"{100 + sira}", "9/A", 9, "MATEMATİK"))
        kayitlar.append(kayit(f"{100 + sira}", "9/A", 9, "FİZİK"))
    for sira in range(6):
        kayitlar.append(kayit(f"{200 + sira}", "10/B", 10, "İNGİLİZCE"))
    ayarlar = {
        "MATEMATİK": DersAyari("Matematik"),
        "FİZİK": DersAyari("Fizik"),
        "İNGİLİZCE": DersAyari("İngilizce", iki_asamali_mi=True, yabanci_dil_mi=True),
    }
    personel = personel_kadrosu({"Matematik": 3, "Fizik": 3, "İngilizce": 3, "Tarih": 3})
    return kayitlar, ayarlar, personel


def _uret(kucuk_senaryo, **param):
    kayitlar, ayarlar, personel = kucuk_senaryo
    birimler = birimleri_olustur(kayitlar, ayarlar, SALONLAR)
    varsayilan = dict(pencere_kodu="P1", ogrenci_gunluk_sinav_siniri=2)
    varsayilan.update(param)
    parametreler = PlanParametreleri(**varsayilan)
    gunler = gunleri_listele(PENCERE[0], PENCERE[1], parametreler.hafta_sonu_kullan)
    return plan_uret(birimler, parametreler, gunler, personel, SALONLAR, PENCERE,
                     ogretim_yili="2026-2027")


def test_uretilen_plan_kural_ihlali_icermez(kucuk_senaryo) -> None:
    sonuc = _uret(kucuk_senaryo)
    assert engelleri_ayikla(sonuc.ihlaller) == []
    assert len(sonuc.plan.oturumlar) == 4        # matematik, fizik, ingilizce×2


def test_plan_belirlenimlidir(kucuk_senaryo) -> None:
    """Aynı girdi aynı programı üretmelidir."""
    birinci, ikinci = _uret(kucuk_senaryo), _uret(kucuk_senaryo)

    def imza(sonuc):
        return ([(o.anahtar, o.tarih, o.saat, o.salon_kimlikleri)
                 for o in sonuc.plan.oturumlar],
                sorted((g.oturum_anahtari, g.personel_kimligi, g.rol.value)
                       for g in sonuc.plan.gorevlendirmeler))

    assert imza(birinci) == imza(ikinci)


def test_iki_asamali_ders_ayni_gun_ardisik_saatte_planlanir(kucuk_senaryo) -> None:
    sonuc = _uret(kucuk_senaryo)
    ingilizce = sorted((o for o in sonuc.plan.oturumlar if o.ders_adi == "İNGİLİZCE"),
                       key=lambda o: o.saat)
    assert len(ingilizce) == 2
    assert ingilizce[0].tarih == ingilizce[1].tarih
    assert ingilizce[0].oturum_turu is OturumTuru.YAZILI
    assert ingilizce[1].oturum_turu is OturumTuru.UYGULAMA


def test_iki_asamali_dersin_komisyonu_ayni_kalir(kucuk_senaryo) -> None:
    """OKY md.58/2-e: komisyonların aynı üyelerden oluşturulması esastır."""
    sonuc = _uret(kucuk_senaryo)
    komisyonlar = [
        frozenset(g.personel_kimligi for g in sonuc.plan.oturum_gorevleri(o.anahtar)
                  if g.rol is GorevRolu.KOMISYON_UYESI)
        for o in sonuc.plan.oturumlar if o.ders_adi == "İNGİLİZCE"
    ]
    assert len(set(komisyonlar)) == 1


def test_her_oturumda_iki_komisyon_uyesi_ve_salon_kadar_gozcu(kucuk_senaryo) -> None:
    sonuc = _uret(kucuk_senaryo)
    for oturum in sonuc.plan.oturumlar:
        gorevler = sonuc.plan.oturum_gorevleri(oturum.anahtar)
        komisyon = [g for g in gorevler if g.rol is GorevRolu.KOMISYON_UYESI]
        gozcu = [g for g in gorevler if g.rol is GorevRolu.GOZCU]
        assert len(komisyon) == 2
        assert len(gozcu) == oturum.salon_sayisi
        assert len({g.personel_kimligi for g in gorevler}) == len(gorevler)


def test_paralel_oturum_mumkundur() -> None:
    """Ders programı kısıtı olmadığı için aynı saatte birden fazla sınav
    yapılabilir; eski motor buna hiç izin vermiyordu."""
    kayitlar = [kayit(f"{100 + i}", "9/A", 9, ders)
                for i, ders in enumerate(["MATEMATİK", "FİZİK", "KİMYA", "TARİH"])]
    ayarlar = {d: DersAyari(b) for d, b in
               (("MATEMATİK", "Matematik"), ("FİZİK", "Fizik"),
                ("KİMYA", "Kimya"), ("TARİH", "Tarih"))}
    personel = personel_kadrosu({"Matematik": 2, "Fizik": 2, "Kimya": 2, "Tarih": 2,
                                 "Coğrafya": 4})
    parametreler = PlanParametreleri(pencere_kodu="P1", hedef_gun_sayisi=1)
    gunler = gunleri_listele(PENCERE[0], PENCERE[1], False)
    sonuc = plan_uret(birimleri_olustur(kayitlar, ayarlar, SALONLAR), parametreler,
                      gunler, personel, SALONLAR, PENCERE, ogretim_yili="2026-2027")
    assert sonuc.kullanilan_gun_sayisi == 1
    assert engelleri_ayikla(sonuc.ihlaller) == []


def test_hafta_sonu_ancak_gerektiginde_kullanilir(kucuk_senaryo) -> None:
    """OKY md.58/2-ç: hafta içinde planlanır, gerektiğinde hafta sonu."""
    sonuc = _uret(kucuk_senaryo, hafta_sonu_kullan=True)
    assert all(o.tarih.weekday() < 5 for o in sonuc.plan.oturumlar)


def test_gorev_yuku_kisiler_arasinda_dengelenir(kucuk_senaryo) -> None:
    sonuc = _uret(kucuk_senaryo)
    sayac: dict[int, int] = {}
    for gorev in sonuc.plan.gorevlendirmeler:
        sayac[gorev.personel_kimligi] = sayac.get(gorev.personel_kimligi, 0) + 1
    assert max(sayac.values()) - min(sayac.values()) <= 2


def test_salon_yoksa_anlasilir_hata(kucuk_senaryo) -> None:
    kayitlar, ayarlar, personel = kucuk_senaryo
    birimler = birimleri_olustur(kayitlar, ayarlar, SALONLAR)
    gunler = gunleri_listele(PENCERE[0], PENCERE[1], False)
    with pytest.raises(PlanlamaBasarisiz, match="sınav salonu tanımlanmalıdır"):
        plan_uret(birimler, PlanParametreleri(pencere_kodu="P1"), gunler,
                  personel, [], PENCERE)


def test_alan_ogretmeni_yoksa_teshis_uretir() -> None:
    kayitlar = [kayit("101", "9/A", 9, "MATEMATİK")]
    ayarlar = {"MATEMATİK": DersAyari("Matematik")}
    personel = personel_kadrosu({"Tarih": 5})   # hiç matematikçi yok
    birimler = birimleri_olustur(kayitlar, ayarlar, SALONLAR)
    gunler = gunleri_listele(PENCERE[0], PENCERE[1], False)
    with pytest.raises(PlanlamaBasarisiz) as hata:
        plan_uret(birimler, PlanParametreleri(pencere_kodu="P1"), gunler,
                  personel, SALONLAR, PENCERE)
    assert "Matematik branşında görev alabilecek öğretmen yok" in str(hata.value)


def test_gorev_alabilecek_personel_yoksa_anlasilir_hata(kucuk_senaryo) -> None:
    kayitlar, ayarlar, _ = kucuk_senaryo
    birimler = birimleri_olustur(kayitlar, ayarlar, SALONLAR)
    gunler = gunleri_listele(PENCERE[0], PENCERE[1], False)
    yalniz_mudur = [Personel(1, "Uydurma Müdür", "Matematik", "Müdür"),
                    Personel(2, "Uydurma Rehber", "Rehberlik", "Öğretmen")]
    with pytest.raises(PlanlamaBasarisiz, match="Görev alabilecek personel yok"):
        plan_uret(birimler, PlanParametreleri(pencere_kodu="P1"), gunler,
                  yalniz_mudur, SALONLAR, PENCERE)


def test_salon_yetersizliginde_teshis_salon_sayisini_soyler() -> None:
    kayitlar = [kayit(f"{i:03d}", "9/A", 9, "MATEMATİK") for i in range(90)]
    ayarlar = {"MATEMATİK": DersAyari("Matematik")}
    tek_salon = [Salon(1, "D-01", 30)]
    with pytest.raises(ValueError, match="salonlar yetersiz"):
        birimleri_olustur(kayitlar, ayarlar, tek_salon)


def test_birlesik_ders_iki_alandan_komisyon_kurar() -> None:
    """Görsel Sanatlar/Müzik dersinde mümkünse her iki alandan bir üye."""
    kayitlar = [kayit("101", "9/A", 9, "GÖRSEL SANATLAR/MÜZİK")]
    ayarlar = {"GÖRSEL SANATLAR/MÜZİK": DersAyari("Görsel Sanatlar",
                                                  esdeger_branslar=("Müzik",))}
    personel = personel_kadrosu({"Görsel Sanatlar": 2, "Müzik": 2, "Tarih": 2})
    birimler = birimleri_olustur(kayitlar, ayarlar, SALONLAR)
    gunler = gunleri_listele(PENCERE[0], PENCERE[1], False)
    sonuc = plan_uret(birimler, PlanParametreleri(pencere_kodu="P1"), gunler,
                      personel, SALONLAR, PENCERE, ogretim_yili="2026-2027")
    oturum = sonuc.plan.oturumlar[0]
    kimlikler = {g.personel_kimligi for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)
                 if g.rol is GorevRolu.KOMISYON_UYESI}
    branslar = {p.brans for p in personel if p.kimlik in kimlikler}
    assert branslar == {"Görsel Sanatlar", "Müzik"}
    assert engelleri_ayikla(sonuc.ihlaller) == []
