"""Servis katmanı ve uçtan uca akış testleri."""

from __future__ import annotations

from pathlib import Path

import pytest

from cekirdek.kurallar import engelleri_ayikla
from cekirdek.modeller import IkiAsamaliSayim, PlanParametreleri
from veri import hizmet
from veri.hizmet import HizmetHatasi
from veri.veritabani import Veritabani
from testler.yardimci import ORNEK_PERSONEL, personel_satirlari, sorumluluk_csv_yaz


AYARLAR = {
    "okul_adi": "Uydurma Anadolu Lisesi",
    "mudur_adi": "Uydurma Müdür",
    "il": "UYDURMA İL",
    "ilce": "UYDURMA İLÇE",
    "ogretim_yili": "2026-2027",
    "birinci_donem_baslangic": "2026-09-14",
    "ikinci_donem_baslangic": "2027-02-08",
    "ikinci_donem_bitis": "2027-06-25",
}


@pytest.fixture()
def vt(tmp_path: Path) -> Veritabani:
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    veritabani.gocleri_uygula()
    return veritabani


def _personel_xlsx(tmp_path: Path, kisiler=None) -> Path:
    from openpyxl import Workbook
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    kitap = Workbook()
    for satir in personel_satirlari(kisiler or ORNEK_PERSONEL):
        kitap.active.append(satir)
    hedef = tmp_path / "personel.xlsx"
    kitap.save(hedef)
    return hedef


def _sorumluluk_csv(tmp_path: Path) -> Path:
    return sorumluluk_csv_yaz(tmp_path / "sorumluluk.csv", {
        "9/A": [
            ("101", "Uydurma Öğrenci Bir", [(9, "MATEMATİK"), (9, "FİZİK")]),
            ("102", "Uydurma Öğrenci İki", [(9, "MATEMATİK"), (9, "İNGİLİZCE")]),
        ],
        "10/B": [
            ("201", "Uydurma Öğrenci Üç", [(10, "MATEMATİK"), (9, "FİZİK")]),
        ],
    })


def _kur(vt: Veritabani, tmp_path: Path) -> None:
    """Kurum ayarları, salonlar, personel ve sorumluluk kayıtlarını hazırlar."""
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.salon_ekle(vt, "D-01", 30)
    hizmet.salon_ekle(vt, "D-02", 30)
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, _personel_xlsx(tmp_path)).aktarim_id)
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    branslar = {ad: kimlik for kimlik, ad, _ in
                [(k, a, s) for k, a, s in hizmet.brans_havuzu_listele(vt)]}
    assert "Matematik" in branslar
    for ders_id, ad, *_ in hizmet.dersleri_listele(vt):
        brans = {"MATEMATİK": "Matematik", "FİZİK": "Fizik",
                 "İNGİLİZCE": "İngilizce"}[ad]
        if brans not in branslar:
            hizmet.brans_havuzu_ekle(vt, brans)
        hizmet.ders_brans_esle(vt, ders_id, brans, "Zümre kararı")
        if ad == "İNGİLİZCE":
            hizmet.ders_ozellik_guncelle(vt, ders_id, iki_asamali_mi=True,
                                         yabanci_dil_mi=True)


# ============================================================ kurum ayarları

def test_eksik_ayar_reddedilir(vt: Veritabani) -> None:
    with pytest.raises(HizmetHatasi, match="doldurulmalıdır"):
        hizmet.ayarlari_kaydet(vt, {"okul_adi": "Uydurma"})


def test_donem_tarihleri_kronolojik_olmalidir(vt: Veritabani) -> None:
    bozuk = dict(AYARLAR, ikinci_donem_baslangic="2026-09-01")
    with pytest.raises(HizmetHatasi, match="kronolojik"):
        hizmet.ayarlari_kaydet(vt, bozuk)


def test_pencereler_donem_tarihlerinden_hesaplanir(vt: Veritabani) -> None:
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    pencereler = hizmet.pencereleri_getir(vt)
    assert set(pencereler) == {"P1", "P2", "P3"}
    assert pencereler["P1"][0].isoformat() == "2026-09-14"
    assert (pencereler["P1"][1] - pencereler["P1"][0]).days == 13


def test_ayar_yokken_pencere_istenirse_anlasilir_hata(vt: Veritabani) -> None:
    with pytest.raises(HizmetHatasi, match="dönem tarihleri"):
        hizmet.pencereleri_getir(vt)


# ==================================================================== salon

def test_ayni_adli_salon_yinelenmez(vt: Veritabani) -> None:
    hizmet.salon_ekle(vt, "D-01", 30)
    hizmet.salon_ekle(vt, "d-01", 25)      # Türkçe küçültmeyle aynı salon
    salonlar = hizmet.salonlari_getir(vt)
    assert len(salonlar) == 1
    assert salonlar[0].kapasite == 25


def test_gecersiz_kapasite_reddedilir(vt: Veritabani) -> None:
    with pytest.raises(HizmetHatasi, match="sıfırdan büyük"):
        hizmet.salon_ekle(vt, "D-01", 0)


# =============================================================== içe aktarma

def test_personel_onizlemesi_ana_tabloyu_degistirmez(vt: Veritabani, tmp_path: Path) -> None:
    ozet = hizmet.personel_onizle(vt, _personel_xlsx(tmp_path))
    assert ozet.eklenen == len(ORNEK_PERSONEL)
    assert hizmet.personelleri_getir(vt) == []      # onay verilmeden yazılmaz


def test_personel_onayi_brans_havuzunu_besler(vt: Veritabani, tmp_path: Path) -> None:
    ozet = hizmet.personel_onizle(vt, _personel_xlsx(tmp_path))
    hizmet.personel_onayla(vt, ozet.aktarim_id)
    assert len(hizmet.personelleri_getir(vt)) == len(ORNEK_PERSONEL)
    branslar = {ad for _, ad, kaynak in hizmet.brans_havuzu_listele(vt)
                if kaynak == "personel_raporu"}
    assert {"Matematik", "Fizik", "Rehberlik"} <= branslar


def test_ayni_personel_raporu_iki_kez_onaylanamaz(vt: Veritabani, tmp_path: Path) -> None:
    ozet = hizmet.personel_onizle(vt, _personel_xlsx(tmp_path))
    hizmet.personel_onayla(vt, ozet.aktarim_id)
    with pytest.raises(HizmetHatasi, match="daha önce onaylanmıştır"):
        hizmet.personel_onizle(vt, _personel_xlsx(tmp_path))
    with pytest.raises(HizmetHatasi, match="zaten onaylanmıştır"):
        hizmet.personel_onayla(vt, ozet.aktarim_id)


def test_rapordan_dusen_personel_pasife_alinir(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, _personel_xlsx(tmp_path)).aktarim_id)
    eksik = [k for k in ORNEK_PERSONEL if k[0] != "Uydurma Fizikçi"]
    ikinci = _personel_xlsx(tmp_path / "ikinci", eksik)
    ozet = hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, ikinci).aktarim_id)
    assert ozet.cikan == 1
    adlar = {p.ad for p in hizmet.personelleri_getir(vt)}
    assert "Uydurma Fizikçi" not in adlar


def test_sorumluluk_onayi_ogrenci_ve_ders_olusturur(vt: Veritabani, tmp_path: Path) -> None:
    ozet = hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path))
    assert ozet.eklenen == 6
    assert hizmet.sorumluluk_kayitlari(vt) == []
    hizmet.sorumluluk_onayla(vt, ozet.aktarim_id)
    kayitlar = hizmet.sorumluluk_kayitlari(vt)
    assert len(kayitlar) == 6
    assert {d[1] for d in hizmet.dersleri_listele(vt)} == {"MATEMATİK", "FİZİK", "İNGİLİZCE"}


def test_kismi_liste_onayinda_eskiler_pasife_alinmaz(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    kismi = sorumluluk_csv_yaz(tmp_path / "kismi.csv", {
        "9/A": [("101", "Uydurma Öğrenci Bir", [(9, "MATEMATİK")])]})
    ozet = hizmet.sorumluluk_onizle(vt, kismi)
    hizmet.sorumluluk_onayla(vt, ozet.aktarim_id, tam_liste=False)
    assert len(hizmet.sorumluluk_kayitlari(vt)) == 6      # hiçbiri düşmedi


def test_tam_liste_onayinda_dosyada_olmayanlar_pasife_alinir(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    kismi = sorumluluk_csv_yaz(tmp_path / "kismi.csv", {
        "9/A": [("101", "Uydurma Öğrenci Bir", [(9, "MATEMATİK")])]})
    ozet = hizmet.sorumluluk_onizle(vt, kismi)
    hizmet.sorumluluk_onayla(vt, ozet.aktarim_id, tam_liste=True)
    assert len(hizmet.sorumluluk_kayitlari(vt)) == 1


# ================================================================ ders/branş

def test_havuzda_olmayan_brans_eslenemez(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    ders_id = hizmet.dersleri_listele(vt)[0][0]
    with pytest.raises(HizmetHatasi, match="branş havuzunda yok"):
        hizmet.ders_brans_esle(vt, ders_id, "Uydurma Branş", "Karar")


def test_esleme_gerekcesi_zorunludur(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    hizmet.brans_havuzu_ekle(vt, "Matematik")
    ders_id = hizmet.dersleri_listele(vt)[0][0]
    with pytest.raises(HizmetHatasi, match="gerekçesi zorunludur"):
        hizmet.ders_brans_esle(vt, ders_id, "Matematik", "   ")


def test_esdeger_brans_ayara_yansir(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    for ad in ("Görsel Sanatlar", "Müzik"):
        hizmet.brans_havuzu_ekle(vt, ad)
    ders_id = hizmet.dersleri_listele(vt)[0][0]
    ders_adi = hizmet.dersleri_listele(vt)[0][1]
    hizmet.ders_brans_esle(vt, ders_id, "Görsel Sanatlar", "Zümre kararı", ("Müzik",))
    ayar = hizmet.ders_ayarlari(vt)[ders_adi]
    assert ayar.brans == "Görsel Sanatlar"
    assert ayar.esdeger_branslar == ("Müzik",)
    assert ayar.alan_branslari == ("Görsel Sanatlar", "Müzik")


def test_iki_asamali_onerisi_mevzuata_uyar() -> None:
    assert hizmet.iki_asamali_onerisi("TÜRK DİLİ VE EDEBİYATI")
    assert hizmet.iki_asamali_onerisi("YABANCI DİL")
    assert hizmet.iki_asamali_onerisi("İKİNCİ YABANCI DİL")
    assert not hizmet.iki_asamali_onerisi("MATEMATİK")
    assert not hizmet.iki_asamali_onerisi("SEÇMELİ METİN TAHLİLLERİ")


# ==================================================================== plan

def test_uctan_uca_plan_uretilir_ve_kaydedilir(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    assert engelleri_ayikla(sonuc.ihlaller) == []
    assert len(sonuc.plan.oturumlar) == 4      # MAT, FİZ, İNG yazılı + uygulama

    plan_id = hizmet.plan_kaydet(vt, sonuc)
    geri, bilgi = hizmet.plan_yukle(vt, plan_id)
    assert bilgi["kesin_mi"] == 0
    assert len(geri.oturumlar) == len(sonuc.plan.oturumlar)
    assert len(geri.gorevlendirmeler) == len(sonuc.plan.gorevlendirmeler)
    # Yüklenen plan da aynı kurallardan geçmelidir.
    assert engelleri_ayikla(hizmet.plani_dogrula(vt, geri)) == []


def test_plan_hazirla_veritabanina_yazmaz(vt: Veritabani, tmp_path: Path) -> None:
    """Plan bellekte düzenlenir; ancak Kaydet'te yazılır."""
    _kur(vt, tmp_path)
    hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    with vt.baglan() as b:
        assert b.execute("SELECT count(*) FROM plan").fetchone()[0] == 0
        assert b.execute("SELECT count(*) FROM oturum").fetchone()[0] == 0


def test_kaydedilen_plan_yuklenip_yeniden_dogrulanabilir(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    plan_id = hizmet.plan_kaydet(vt, sonuc)
    geri, _ = hizmet.plan_yukle(vt, plan_id)
    # Elle bozulan plan doğrulamadan geçmemelidir.
    geri.oturumlar[0].tarih = geri.oturumlar[0].tarih.replace(year=2030)
    assert engelleri_ayikla(hizmet.plani_dogrula(vt, geri))


def test_yeni_taslak_oncekinin_yerine_gecer(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    hizmet.plan_kaydet(vt, sonuc)
    ikinci_id = hizmet.plan_kaydet(vt, sonuc)
    with vt.baglan() as b:
        acik = [r[0] for r in b.execute("SELECT id FROM v_plan")]
    assert acik == [ikinci_id]


def test_plan_mudur_onayiyla_kesinlesir_ve_kilitlenir(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    plan_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(
        vt, PlanParametreleri(pencere_kodu="P1")))
    with pytest.raises(HizmetHatasi, match="müdür onay numarası"):
        hizmet.plan_kesinlestir(vt, plan_id, "  ")
    hizmet.plan_kesinlestir(vt, plan_id, "2026/144")
    _, bilgi = hizmet.plan_yukle(vt, plan_id)
    assert bilgi["kesin_mi"] == 1
    with pytest.raises(HizmetHatasi, match="Kesinleşmiş plan silinemez"):
        hizmet.plan_sil(vt, plan_id)


def test_iki_asamali_sayim_gunluk_yuku_degistirir(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    tek = hizmet.yuk_ozetini_getir(vt, IkiAsamaliSayim.TEK, 2)
    ayri = hizmet.yuk_ozetini_getir(vt, IkiAsamaliSayim.AYRI, 2)
    assert ayri.azami_yuk > tek.azami_yuk


def test_salon_yokken_plan_uretilemez(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    with pytest.raises(HizmetHatasi, match="sınav salonu tanımlayın"):
        hizmet.sinav_birimleri(vt)


def test_sorumluluk_kaydi_yokken_anlasilir_hata(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.salon_ekle(vt, "D-01", 30)
    with pytest.raises(HizmetHatasi, match="sorumluluk raporunu içe aktarın"):
        hizmet.sinav_birimleri(vt)


def test_slot_saatleri_dogrulanir() -> None:
    assert len(hizmet.slot_saatlerini_coz("08:00, 09:00, 10:00")) == 3
    with pytest.raises(HizmetHatasi, match="artan sırada"):
        hizmet.slot_saatlerini_coz("10:00, 09:00")
    with pytest.raises(HizmetHatasi, match="yinelenemez"):
        hizmet.slot_saatlerini_coz("09:00, 09:00")
    with pytest.raises(HizmetHatasi, match="SS:DD"):
        hizmet.slot_saatlerini_coz("dokuz")
