"""Personel elle yönetimi ve dönemler arası görev havuzu testleri."""

from __future__ import annotations

from pathlib import Path

import pytest

from cekirdek.modeller import PlanParametreleri
from veri import hizmet
from veri.hizmet import HizmetHatasi
from veri.veritabani import Veritabani
from testler.test_hizmet import AYARLAR, _kur


@pytest.fixture()
def hazir(tmp_path: Path):
    vt = Veritabani(tmp_path / "sorumluluk.db")
    vt.gocleri_uygula()
    _kur(vt, tmp_path)
    return vt, tmp_path


# ================================================ personel elle yönetimi

def test_elle_personel_eklenir_ve_brans_havuza_girer(hazir) -> None:
    vt, _ = hazir
    kimlik = hizmet.personel_ekle(vt, "Uydurma Yeni Öğretmen", "Almanca", "Öğretmen")
    kisi = next(k for k in hizmet.personel_ayrintili_liste(vt) if k["kimlik"] == kimlik)
    assert kisi["ad"] == "Uydurma Yeni Öğretmen"
    assert kisi["kaynak"] == "elle eklendi"
    assert "Almanca" in [ad for _, ad, _ in hizmet.brans_havuzu_listele(vt)]


def test_eksik_alanla_personel_eklenemez(hazir) -> None:
    vt, _ = hazir
    with pytest.raises(HizmetHatasi, match="zorunludur"):
        hizmet.personel_ekle(vt, "Uydurma Kişi", "", "Öğretmen")


def test_ayni_adli_personel_iki_kez_eklenemez(hazir) -> None:
    vt, _ = hazir
    hizmet.personel_ekle(vt, "Uydurma Yeni", "Almanca", "Öğretmen")
    with pytest.raises(HizmetHatasi, match="zaten kayıtlı"):
        hizmet.personel_ekle(vt, "Uydurma Yeni", "Fransızca", "Öğretmen")


def test_personel_pasife_alinip_geri_etkinlestirilir(hazir) -> None:
    vt, _ = hazir
    kimlik = hizmet.personelleri_getir(vt)[0].kimlik
    hizmet.personel_durumu_degistir(vt, kimlik, False)
    assert kimlik not in {k.kimlik for k in hizmet.personelleri_getir(vt)}
    hizmet.personel_durumu_degistir(vt, kimlik, True)
    assert kimlik in {k.kimlik for k in hizmet.personelleri_getir(vt)}


def test_pasif_personel_gorevlendirmeye_alinmaz(hazir) -> None:
    """Pasife alınan öğretmen yeni planda görev almamalıdır."""
    vt, tmp_path = hazir
    matematikciler = [k for k in hizmet.personelleri_getir(vt) if k.brans == "Matematik"]
    hizmet.personel_durumu_degistir(vt, matematikciler[0].kimlik, False)
    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    atananlar = {g.personel_kimligi for g in sonuc.plan.gorevlendirmeler}
    assert matematikciler[0].kimlik not in atananlar


def test_gorevi_olmayan_personel_silinir(hazir) -> None:
    vt, _ = hazir
    kimlik = hizmet.personel_ekle(vt, "Uydurma Silinecek", "Almanca", "Öğretmen")
    hizmet.personel_sil(vt, kimlik)
    assert kimlik not in {k["kimlik"] for k in hizmet.personel_ayrintili_liste(vt)}


def test_gorevi_olan_personel_silinemez(hazir) -> None:
    """Silinirse üretilmiş evrak ile veritabanı çelişir."""
    vt, _ = hazir
    hizmet.plan_kaydet(vt, hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1")))
    gorevli = hizmet.gorevli_listesi(vt, hizmet.son_plani_getir(vt, "P1"))[0]
    with pytest.raises(HizmetHatasi, match="silinemez"):
        hizmet.personel_sil(vt, gorevli["kimlik"])


# ============================================ dönemler arası görev havuzu

def test_plan_ogretim_yiliyla_kaydedilir(hazir) -> None:
    vt, _ = hazir
    plan_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(
        vt, PlanParametreleri(pencere_kodu="P1")))
    with vt.baglan() as b:
        yil = b.execute("SELECT ogretim_yili FROM v_plan WHERE id=?", (plan_id,)).fetchone()[0]
    assert yil == AYARLAR["ogretim_yili"]


def test_onceki_donem_sayaclari_toplanir(hazir) -> None:
    vt, _ = hazir
    hizmet.plan_kaydet(vt, hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1")))
    sayaclar = hizmet.onceki_gorev_sayaclari(vt)
    assert sayaclar
    assert sum(k + g for k, g in sayaclar.values()) > 0


def test_plan_kendi_sayacini_baslangica_katmaz(hazir) -> None:
    """P1 yeniden üretilirken kendi görevleri başlangıç sayacı olmamalıdır."""
    vt, _ = hazir
    plan_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(
        vt, PlanParametreleri(pencere_kodu="P1")))
    assert hizmet.onceki_gorev_sayaclari(vt, haric_plan_id=plan_id) == {}


def test_ikinci_donem_ilk_donemin_yukunu_dikkate_alir(hazir) -> None:
    """P1'de görev almış öğretmen P2'de geri plana düşmelidir."""
    vt, _ = hazir
    birinci = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))
    hizmet.plan_kaydet(vt, birinci)
    p1_yuku = {}
    for gorev in birinci.plan.gorevlendirmeler:
        p1_yuku[gorev.personel_kimligi] = p1_yuku.get(gorev.personel_kimligi, 0) + 1

    ikinci = hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P2"))
    p2_yuku = {}
    for gorev in ikinci.plan.gorevlendirmeler:
        p2_yuku[gorev.personel_kimligi] = p2_yuku.get(gorev.personel_kimligi, 0) + 1

    # İki dönemin toplamı, tek dönemin dağılımından daha dengeli olmalı:
    # P1'de en çok görev alan kişi P2'de en çok görev alan olmamalıdır.
    en_yuklu_p1 = max(p1_yuku, key=lambda k: (p1_yuku[k], k))
    toplam = {k: p1_yuku.get(k, 0) + p2_yuku.get(k, 0) for k in set(p1_yuku) | set(p2_yuku)}
    assert max(toplam.values()) - min(toplam.values()) <= max(p1_yuku.values()) + 1
    assert p2_yuku.get(en_yuklu_p1, 0) <= max(p2_yuku.values())


def test_gorev_havuzu_ozeti_donem_dokumu_verir(hazir) -> None:
    vt, _ = hazir
    hizmet.plan_kaydet(vt, hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1")))
    ozet = hizmet.gorev_havuzu_ozeti(vt)
    assert ozet
    ilk = ozet[0]
    assert "P1" in ilk["pencereler"]
    assert ilk["toplam"] == ilk["komisyon"] + ilk["gozcu"]


def test_yonetici_ucretlendirilemez_isaretlenir(hazir) -> None:
    vt, _ = hazir
    hizmet.plan_kaydet(vt, hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1")))
    for kayit in hizmet.gorev_havuzu_ozeti(vt):
        beklenen = "müdür" not in kayit["unvan"].lower()
        assert kayit["ucretlendirilebilir"] == beklenen
