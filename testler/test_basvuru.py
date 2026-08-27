"""Başvuru kapısı — OKY md.58/2-d.

Mezun olamayan 12. sınıf ve devamsızlık tebligatı yapılmış öğrenciler yazılı
başvuru olmadan plana alınmaz. Buradaki tüm ad ve numaralar uydurmadır (KVKK).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook

from cekirdek.kurallar import engelleri_ayikla
from cekirdek.modeller import PlanParametreleri
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

# P1 = 14.09.2026 başlar. Son başvuru 07.09.2026: aradaki 5 iş günü sağlanır.
DUYURU_TARIHI = date(2026, 8, 28)
SON_GUN = date(2026, 9, 7)


@pytest.fixture()
def vt(tmp_path: Path) -> Veritabani:
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    veritabani.gocleri_uygula()
    return veritabani


def _kur(vt: Veritabani, tmp_path: Path) -> None:
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.salon_ekle(vt, "D-01", 30)
    hizmet.salon_ekle(vt, "D-02", 30)
    kitap = Workbook()
    for satir in personel_satirlari(ORNEK_PERSONEL):
        kitap.active.append(satir)
    personel_yolu = tmp_path / "personel.xlsx"
    kitap.save(personel_yolu)
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, personel_yolu).aktarim_id)

    csv_yolu = sorumluluk_csv_yaz(tmp_path / "sorumluluk.csv", {
        "9/A": [
            ("101", "Uydurma Öğrenci Bir", [(9, "MATEMATİK")]),
            ("102", "Uydurma Öğrenci İki", [(9, "MATEMATİK")]),
        ],
        "12/A": [
            ("301", "Uydurma Beklemeli", [(9, "MATEMATİK")]),
            ("302", "Uydurma Devamsız", [(9, "MATEMATİK")]),
        ],
    })
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, csv_yolu).aktarim_id)
    for ders_id, ad, *_ in hizmet.dersleri_listele(vt):
        hizmet.brans_havuzu_ekle(vt, "Matematik")
        hizmet.ders_brans_esle(vt, ders_id, "Matematik", "Zümre kararı")
        assert ad == "MATEMATİK"


def _ogrenci_id(vt: Veritabani, okul_no: str) -> int:
    with vt.baglan() as b:
        return b.execute("SELECT id FROM v_ogrenci WHERE okul_no=?", (okul_no,)).fetchone()[0]


def _isaretle(vt: Veritabani, tmp_path: Path) -> tuple[int, int]:
    """301'i beklemeli, 302'yi devamsız işaretler ve duyuruyu kaydeder."""
    beklemeli = _ogrenci_id(vt, "301")
    devamsiz = _ogrenci_id(vt, "302")
    hizmet.ogrenci_bayrak_guncelle(vt, beklemeli, True, False)
    hizmet.ogrenci_bayrak_guncelle(vt, devamsiz, False, True)
    hizmet.duyuru_kaydet(vt, "P1", DUYURU_TARIHI, SON_GUN, "Duyuru 2026/1",
                         "Okul web sayfası ve pano")
    return beklemeli, devamsiz


def _plandaki_ogrenciler(sonuc) -> set[str]:
    return {a for o in sonuc.plan.oturumlar for a in o.ogrenci_anahtarlari}


# ============================================================ süzgeç ve kapı

def test_basvurusuz_bayrakli_ogrenci_plana_alinmaz(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    _isaretle(vt, tmp_path)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    assert _plandaki_ogrenciler(sonuc) == {"101|9/A", "102|9/A"}


def test_basvuran_bayrakli_ogrenci_plana_alinir(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    beklemeli, _ = _isaretle(vt, tmp_path)
    hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 3), "Dilekçe 2026/7")
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    assert "301|12/A" in _plandaki_ogrenciler(sonuc)
    assert "302|12/A" not in _plandaki_ogrenciler(sonuc)


def test_bayraksiz_ogrenci_basvurusuz_plana_girer(vt: Veritabani, tmp_path: Path) -> None:
    """Kapı yalnız iki gruba uygulanır; geri kalan öğrenci hiç işleme girmez."""
    _kur(vt, tmp_path)
    _isaretle(vt, tmp_path)
    tablo = {s["okul_no"]: s for s in hizmet.basvuru_tablosu(vt, "P1")}
    assert tablo["101"]["ozet"] == "Başvuru aranmaz"
    assert tablo["301"]["ozet"] == "KARAR BEKLİYOR"
    assert tablo["301"]["grup"] == "Mezun olamayan 12. sınıf"
    assert tablo["302"]["grup"] == "Devamsızlık tebligatı yapılan"


def test_elle_eklenen_basvurusuz_ogrenci_engel_uretir(vt: Veritabani, tmp_path: Path) -> None:
    """Planlayıcı dışlar; elle düzenlemede de aynı kapı çalışmalıdır."""
    _kur(vt, tmp_path)
    beklemeli, _ = _isaretle(vt, tmp_path)
    hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 3), "Dilekçe 2026/7")
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    oturum = sonuc.plan.oturumlar[0]
    oturum.ogrenci_anahtarlari = (*oturum.ogrenci_anahtarlari, "302|12/A")
    ihlaller = hizmet.plani_dogrula(vt, sonuc.plan)
    sp07 = [i for i in engelleri_ayikla(ihlaller) if i.kural_kimligi == "SP-07"]
    assert len(sp07) == 1
    assert "Uydurma Devamsız" in sp07[0].aciklama
    assert sp07[0].dayanak_metni.startswith("OKY md.58/2-d")


# ================================================================== duyuru

def test_duyuru_olmadan_basvuru_alinamaz(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    beklemeli = _ogrenci_id(vt, "301")
    hizmet.ogrenci_bayrak_guncelle(vt, beklemeli, True, False)
    with pytest.raises(HizmetHatasi, match="duyurusu kaydedilmeden"):
        hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 3), "Dilekçe")


def test_son_gun_pencereye_bes_is_gunu_kalmadan_olamaz(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    with pytest.raises(HizmetHatasi, match="Başvuru son günü en geç"):
        hizmet.duyuru_kaydet(vt, "P1", DUYURU_TARIHI, date(2026, 9, 10), "Duyuru 2026/1")


def test_gec_duyuru_uyarir_ama_engellemez(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    uyarilar = hizmet.duyuru_kaydet(vt, "P1", date(2026, 9, 5), SON_GUN, "Duyuru 2026/1")
    assert uyarilar and "okul uygulaması" in uyarilar[0].lower()
    assert hizmet.duyuru_getir(vt, "P1")["belge_referansi"] == "Duyuru 2026/1"


def test_bayraksiz_ogrenci_icin_basvuru_kaydedilemez(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    _isaretle(vt, tmp_path)
    with pytest.raises(HizmetHatasi, match="md.58/2-d"):
        hizmet.basvuru_kaydet(vt, _ogrenci_id(vt, "101"), "P1", "basvurdu",
                              date(2026, 9, 3), "Dilekçe")


# ============================================================= geç başvuru

def test_gec_basvuru_mudur_onayi_ister(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    beklemeli, _ = _isaretle(vt, tmp_path)
    with pytest.raises(HizmetHatasi, match="müdür onayına bağlıdır"):
        hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 8), "Dilekçe")
    hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 8),
                          "Dilekçe", "2026/55")
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    assert "301|12/A" in _plandaki_ogrenciler(sonuc)


def test_gec_basvuru_fiili_sinav_tarihine_gore_bes_is_gunu_arar(
        vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    beklemeli, _ = _isaretle(vt, tmp_path)
    plan_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(
        vt, PlanParametreleri(pencere_kodu="P1")))
    with vt.baglan() as b:
        sinav = b.execute("SELECT MIN(tarih) FROM v_oturum WHERE plan_id=?",
                          (plan_id,)).fetchone()[0]
    assert sinav
    with pytest.raises(HizmetHatasi, match="en az 5 iş günü önce"):
        hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu",
                              date.fromisoformat(sinav), "Dilekçe", "2026/55")


# ======================================================== pencere ve tutanak

def test_basvuru_pencere_basina_yenilenir(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    beklemeli, _ = _isaretle(vt, tmp_path)
    hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 3), "Dilekçe 2026/7")
    hizmet.duyuru_kaydet(vt, "P2", date(2027, 1, 20), date(2027, 2, 1), "Duyuru 2027/1")
    assert [s["okul_no"] for s in hizmet.basvuru_bekleyenler(vt, "P1")] == ["302"]
    bekleyen_p2 = {s["okul_no"] for s in hizmet.basvuru_bekleyenler(vt, "P2")}
    assert bekleyen_p2 == {"301", "302"}   # P1 başvurusu P2'ye devretmez


def test_plan_disi_tutanagi_basvurmayanlari_ve_karar_bekleyenleri_ayirir(
        vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    beklemeli, devamsiz = _isaretle(vt, tmp_path)
    hizmet.basvuru_kaydet(vt, devamsiz, "P1", "basvurmadi")
    satirlar = {s["okul_no"]: s["ozet"] for s in hizmet.plan_disi_birakilanlar(vt, "P1")}
    assert satirlar == {"301": "KARAR BEKLİYOR", "302": "Başvurmadı — plan dışı"}
    hizmet.basvuru_kaydet(vt, beklemeli, "P1", "basvurdu", date(2026, 9, 3), "Dilekçe")
    assert [s["okul_no"] for s in hizmet.plan_disi_birakilanlar(vt, "P1")] == ["302"]


# ============================================== şube değişimi (dar düzeltme)

def test_sube_degisince_isaret_korunur_ve_ogrenci_ikilenmez(
        vt: Veritabani, tmp_path: Path) -> None:
    """Kimlik okul numarasıdır; şube bir özniteliktir.

    Şube değişiminde yeni satır açılsaydı md.58/2-d bayrakları sıfırlanır ve
    işaretlenmiş öğrenci bir sonraki pencerede işaretsiz olarak plana girerdi.
    """
    _kur(vt, tmp_path)
    beklemeli, _ = _isaretle(vt, tmp_path)
    ikinci = sorumluluk_csv_yaz(tmp_path / "sorumluluk2.csv", {
        "9/A": [("101", "Uydurma Öğrenci Bir", [(9, "MATEMATİK")])],
        "12/B": [("301", "Uydurma Beklemeli", [(9, "MATEMATİK")])],
    })
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, ikinci).aktarim_id)
    with vt.baglan() as b:
        satirlar = b.execute(
            "SELECT id,sube,mezun_olamayan_mi FROM v_ogrenci WHERE okul_no='301'").fetchall()
    assert len(satirlar) == 1, "Şube değişimi ikinci bir öğrenci satırı doğurmamalıdır."
    assert satirlar[0][0] == beklemeli
    assert satirlar[0][1] == "12/B"
    assert satirlar[0][2] == 1


# ================================================= SP-15 liste tazeliği

def test_eylul_planinda_liste_hatirlatmasi_cikmaz(vt: Veritabani, tmp_path: Path) -> None:
    """P1 aktarımın hemen ardından yapılır; hatırlatma gürültü olur."""
    _kur(vt, tmp_path)
    assert hizmet.liste_tazeligi_uyarisi(vt, "P1") == ""


def test_subat_ve_haziran_planinda_eski_liste_hatirlatilir(
        vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    with vt.baglan() as b:
        b.execute("UPDATE ice_aktarim SET onaylandi_at='2026-09-10T09:00:00+03:00'"
                  " WHERE tur='sorumluluk'")
    for kod in ("P2", "P3"):
        mesaj = hizmet.liste_tazeligi_uyarisi(vt, kod)
        assert "10.09.2026" in mesaj and "SP-15" in mesaj


def test_taze_liste_hatirlatma_uretmez(vt: Veritabani, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    with vt.baglan() as b:
        b.execute("UPDATE ice_aktarim SET onaylandi_at='2027-02-01T09:00:00+03:00'"
                  " WHERE tur='sorumluluk'")
    assert hizmet.liste_tazeligi_uyarisi(vt, "P2") == ""
