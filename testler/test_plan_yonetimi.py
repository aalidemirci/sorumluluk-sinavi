"""Plan kimliği, kesin plan koruması, salon dağıtımı ve elle düzenleme.

Veriler uydurmadır (KVKK).
"""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from cekirdek.kurallar import salonlara_dagit
from cekirdek.modeller import GorevRolu, OturumTuru, PlanParametreleri
from veri import hizmet
from veri.hizmet import HizmetHatasi
from testler.test_hizmet import AYARLAR, _kur, vt  # noqa: F401  (fikstür)


def _plan(vt):
    return hizmet.plan_hazirla(vt, PlanParametreleri(pencere_kodu="P1"))


# ======================================================== kesin plan koruması

def test_kesin_planin_ustune_yeni_plan_kaydedilemez(vt, tmp_path: Path) -> None:
    """Eski sürüm aynı dönem için yeni taslak kaydediyordu; ekran ve evrak
    taslağı gösteriyor, görev sayaçları iki planı birden sayıyordu."""
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    plan_id = hizmet.plan_kaydet(vt, sonuc)
    hizmet.plan_kesinlestir(vt, plan_id, "Uydurma 2026/7")
    with pytest.raises(HizmetHatasi, match="kesinleşmiştir"):
        hizmet.plan_kaydet(vt, sonuc)
    with pytest.raises(HizmetHatasi, match="kesinleşmiştir"):
        _plan(vt)
    assert hizmet.son_plani_getir(vt, "P1") == plan_id


def test_gorev_sayaci_her_donemden_tek_plan_sayar(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    hizmet.plan_kaydet(vt, sonuc)
    hizmet.plan_kaydet(vt, _plan(vt))            # taslak yerine taslak
    toplam = sum(k["toplam"] for k in hizmet.gorev_havuzu_ozeti(vt))
    assert toplam == len(sonuc.plan.gorevlendirmeler)


def test_kesin_plan_zaten_kesinse_yeniden_kesinlesmez(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    plan_id = hizmet.plan_kaydet(vt, _plan(vt))
    hizmet.plan_kesinlestir(vt, plan_id, "Uydurma 1")
    with pytest.raises(HizmetHatasi, match="zaten kesinleşmiştir"):
        hizmet.plan_kesinlestir(vt, plan_id, "Uydurma 2")


# ===================================================== öğretim yılı süzgeci

def test_yeni_ogretim_yilinda_eski_plan_acilmaz_ve_silinmez(vt, tmp_path: Path) -> None:
    """Eski sürümde yeni yılın Eylül ekranı geçen yılın planını açıyor, yeni
    plan kaydedilince geçen yılın Eylül taslağı da siliniyordu."""
    _kur(vt, tmp_path)
    eski_id = hizmet.plan_kaydet(vt, _plan(vt))
    hizmet.ayarlari_kaydet(vt, dict(AYARLAR, ogretim_yili="2027-2028",
                                    birinci_donem_baslangic="2027-09-13",
                                    ikinci_donem_baslangic="2028-02-07",
                                    ikinci_donem_bitis="2028-06-23"))
    assert hizmet.son_plani_getir(vt, "P1") is None
    yeni_id = hizmet.plan_kaydet(vt, _plan(vt))
    assert hizmet.son_plani_getir(vt, "P1") == yeni_id
    with vt.baglan() as b:
        assert b.execute("SELECT count(*) FROM v_plan WHERE id=?", (eski_id,)).fetchone()[0] == 1


# =============================================================== salon dağıtımı

def test_salonlara_kapasiteyle_orantili_dagitilir() -> None:
    """Eski sürüm sırayla dağıtıp 10 kişilik salona 17 öğrenci yazıyordu."""
    assert salonlara_dagit(35, [30, 10]) == [27, 8]
    assert salonlara_dagit(40, [30, 30]) == [20, 20]
    assert salonlara_dagit(10, [30]) == [10]
    adetler = salonlara_dagit(59, [30, 30, 20])
    assert sum(adetler) == 59 and all(a <= k for a, k in zip(adetler, [30, 30, 20]))


def test_kayitli_planda_salon_kapasitesi_asilmaz(vt, tmp_path: Path) -> None:
    from testler.test_hizmet import _personel_xlsx
    from testler.yardimci import sorumluluk_csv_yaz
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.salon_ekle(vt, "Büyük", 30)
    hizmet.salon_ekle(vt, "Küçük", 10)
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, _personel_xlsx(tmp_path)).aktarim_id)
    ogrenciler = [(f"{300 + i}", f"Uydurma Öğrenci {i}", [(9, "MATEMATİK")]) for i in range(35)]
    csv = sorumluluk_csv_yaz(tmp_path / "s.csv", {"10/A": ogrenciler})
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, csv).aktarim_id)
    ders_id = hizmet.dersleri_listele(vt)[0][0]
    hizmet.ders_brans_esle(vt, ders_id, "Matematik", "Zümre kararı")
    plan_id = hizmet.plan_kaydet(vt, _plan(vt))
    with vt.baglan() as b:
        dagilim = dict(b.execute(
            "SELECT s.ad, count(*) FROM v_oturum_ogrenci oo JOIN v_salon s ON s.id=oo.salon_id"
            " JOIN v_oturum o ON o.id=oo.oturum_id WHERE o.plan_id=? GROUP BY s.ad",
            (plan_id,)).fetchall())
        gozcu_salonu = b.execute(
            "SELECT count(*) FROM v_gorevlendirme g JOIN v_oturum o ON o.id=g.oturum_id"
            " WHERE o.plan_id=? AND g.rol='gozcu' AND g.salon_id IS NOT NULL",
            (plan_id,)).fetchone()[0]
    assert dagilim == {"Büyük": 27, "Küçük": 8}
    assert gozcu_salonu == 2


# ================================================= iki aşamalı dersi taşıma

def _iki_asamali(sonuc):
    yazili = next(o for o in sonuc.plan.oturumlar
                  if o.ders_adi == "İNGİLİZCE" and o.oturum_turu is OturumTuru.YAZILI)
    uygulama = next(o for o in sonuc.plan.oturumlar
                    if o.ders_adi == "İNGİLİZCE" and o.oturum_turu is OturumTuru.UYGULAMA)
    return yazili, uygulama


def _bos_gun(sonuc, *disinda):
    dolu = {o.tarih for o in sonuc.plan.oturumlar} | set(disinda)
    return next(date(2026, 9, g) for g in (14, 15, 16, 17, 18, 21, 22, 23, 24, 25)
                if date(2026, 9, g) not in dolu)


def test_uygulama_oturumu_tek_basina_baska_gune_tasinir(vt, tmp_path: Path) -> None:
    """OKY md.58/2-e: yazılı ve uygulama farklı günlerde de yapılabilir."""
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    yazili, uygulama = _iki_asamali(sonuc)
    yazili_yeri = (yazili.tarih, yazili.saat)
    hedef = _bos_gun(sonuc)
    tasima = hizmet.oturum_tasi(vt, sonuc.plan, uygulama.anahtar, hedef, time(13, 30),
                                sonuc.yukseltilen_sinirlar)
    assert tasima.uygulandi, tasima.mesaj()
    assert (uygulama.tarih, uygulama.saat) == (hedef, time(13, 30))
    assert (yazili.tarih, yazili.saat) == yazili_yeri


def test_yazili_tasininca_uygulama_saat_farkiyla_gelir(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    yazili, uygulama = _iki_asamali(sonuc)
    hedef = _bos_gun(sonuc)
    tasima = hizmet.oturum_tasi(vt, sonuc.plan, yazili.anahtar, hedef, time(9, 0),
                                sonuc.yukseltilen_sinirlar)
    assert tasima.uygulandi, tasima.mesaj()
    assert (yazili.tarih, yazili.saat) == (hedef, time(9, 0))
    assert (uygulama.tarih, uygulama.saat) == (hedef, time(10, 0))


# ===================================================== uzun uygulama sınavı

def test_uzun_uygulama_surerken_ogrencinin_sinavi_baslayamaz(vt, tmp_path: Path) -> None:
    """OKY md.45/1-f: uygulama süresini zümre belirler. 09:00'da başlayan 90
    dakikalık uygulama 10:00 sınavı başlarken sürer; eski doğrulayıcı yalnız
    başlangıç saatlerine baktığı için bu taşımaya izin veriyordu. 40 dakikalık
    uygulamada aynı taşıma geçerlidir (olumsuz senaryo)."""
    _kur(vt, tmp_path)
    for sure, izinli in ((90, False), (40, True)):
        sonuc = hizmet.plan_hazirla(
            vt, PlanParametreleri(pencere_kodu="P1", uygulama_suresi_dakika=sure))
        _, uygulama = _iki_asamali(sonuc)
        ogrenci = uygulama.ogrenci_anahtarlari[0]
        matematik = next(o for o in sonuc.plan.oturumlar
                         if o.ders_adi == "MATEMATİK" and ogrenci in o.ogrenci_anahtarlari)
        hedef = _bos_gun(sonuc)
        assert hizmet.oturum_tasi(vt, sonuc.plan, matematik.anahtar, hedef, time(10, 0),
                                  sonuc.yukseltilen_sinirlar).uygulandi
        tasima = hizmet.oturum_tasi(vt, sonuc.plan, uygulama.anahtar, hedef, time(9, 0),
                                    sonuc.yukseltilen_sinirlar)
        assert tasima.uygulandi is izinli, tasima.mesaj()
        if not izinli:
            assert any("İNGİLİZCE (09:00–10:30) sürüyor" in i.aciklama
                       for i in tasima.ogrenci_engelleri)


def test_uzun_uygulamadaki_gorevli_sonraki_sinava_aday_olamaz(vt, tmp_path: Path) -> None:
    from testler.yardimci import gorevler, oturum, plan as plan_kur
    _kur(vt, tmp_path)
    kisiler = [p.kimlik for p in hizmet.personelleri_getir(vt) if p.gorev_alabilir_mi]
    suren, degisen, *komisyon = kisiler[:6]
    for sure, uygun_mu in ((90, False), (40, True)):
        plan = plan_kur(
            [oturum("u", "İNGİLİZCE", ["102|9/A"], saat=(9, 0), brans="İngilizce",
                    tur=OturumTuru.UYGULAMA, sure=sure),
             oturum("m", "MATEMATİK", ["201|10/B"], saat=(10, 0), salonlar=(2,))],
            gorevler("u", komisyon=tuple(komisyon[:2]), gozcu=(suren,))
            + gorevler("m", komisyon=tuple(komisyon[2:]), gozcu=(degisen,)))
        aday = next(a for a in hizmet.gorevli_adaylari(vt, plan, "m", GorevRolu.GOZCU, degisen)
                    if a["kimlik"] == suren)
        assert aday["uygun_mu"] is uygun_mu, sure
        assert aday["neden"] == ("" if uygun_mu else "aynı anda başka sınavda görevli")


# ===================================================== görevli değişikliği

def test_taslakta_gorevli_degistirilir_ve_geri_alinabilir(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    oturum = sonuc.plan.oturumlar[0]
    gozcu = next(g for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)
                 if g.rol is GorevRolu.GOZCU)
    goruntu = hizmet.plan_anlik_goruntusu(sonuc.plan)
    adaylar = hizmet.gorevli_adaylari(vt, sonuc.plan, oturum.anahtar, GorevRolu.GOZCU,
                                      gozcu.personel_kimligi)
    uygun = next(a for a in adaylar if a["uygun_mu"])
    assert all(a["uygun_mu"] for a in adaylar[:adaylar.index(uygun) + 1])
    tasima = hizmet.gorevli_degistir(vt, sonuc.plan, oturum.anahtar, gozcu.personel_kimligi,
                                     uygun["kimlik"], sonuc.yukseltilen_sinirlar)
    assert tasima.uygulandi, tasima.mesaj()
    yeni = {g.personel_kimligi for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)}
    assert uygun["kimlik"] in yeni and gozcu.personel_kimligi not in yeni
    hizmet.plani_geri_yukle(sonuc.plan, goruntu)
    assert gozcu.personel_kimligi in {g.personel_kimligi
                                      for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)}


def test_mudure_gorev_verilen_degisiklik_geri_alinir(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    oturum = sonuc.plan.oturumlar[0]
    gozcu = next(g for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)
                 if g.rol is GorevRolu.GOZCU)
    mudur = next(p for p in hizmet.personelleri_getir(vt) if p.unvan == "Müdür")
    adaylar = hizmet.gorevli_adaylari(vt, sonuc.plan, oturum.anahtar, GorevRolu.GOZCU,
                                      gozcu.personel_kimligi)
    assert next(a for a in adaylar if a["kimlik"] == mudur.kimlik)["uygun_mu"] is False
    tasima = hizmet.gorevli_degistir(vt, sonuc.plan, oturum.anahtar, gozcu.personel_kimligi,
                                     mudur.kimlik, sonuc.yukseltilen_sinirlar)
    assert not tasima.uygulandi and tasima.ogretmen_engelleri
    assert gozcu.personel_kimligi in {g.personel_kimligi
                                      for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)}


def test_kesin_planda_gorevli_degisikligi_onay_ister_ve_kaydedilir(vt, tmp_path: Path) -> None:
    _kur(vt, tmp_path)
    plan_id = hizmet.plan_kaydet(vt, _plan(vt))
    hizmet.plan_kesinlestir(vt, plan_id, "Uydurma 2026/7")
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)    # tek aşamalı
    gozcu = next(g for g in plan.oturum_gorevleri(oturum.anahtar) if g.rol is GorevRolu.GOZCU)
    with pytest.raises(HizmetHatasi, match="onay numarası"):
        hizmet.kesin_plan_gorevli_degistir(vt, plan_id, oturum.anahtar,
                                           gozcu.personel_kimligi, 0, "", "izinli")
    with pytest.raises(HizmetHatasi, match="müdür onayıyla"):
        hizmet.gorevli_degistir(vt, plan, oturum.anahtar, gozcu.personel_kimligi, 1)
    aday = next(a for a in hizmet.gorevli_adaylari(vt, plan, oturum.anahtar, GorevRolu.GOZCU,
                                                     gozcu.personel_kimligi) if a["uygun_mu"])
    sonuc = hizmet.kesin_plan_gorevli_degistir(vt, plan_id, oturum.anahtar,
                                               gozcu.personel_kimligi, aday["kimlik"],
                                               "Uydurma 2026/9", "Başka görevde")
    assert sonuc.uygulandi, sonuc.mesaj()
    plan, bilgi = hizmet.plan_yukle(vt, plan_id)
    assert bilgi["kesin_mi"]
    assert aday["kimlik"] in {g.personel_kimligi for g in plan.oturum_gorevleri(oturum.anahtar)}
    degisiklik = hizmet.gorevli_degisiklikleri(vt, plan_id)
    assert len(degisiklik) == 1 and degisiklik[0]["onay_no"] == "Uydurma 2026/9"


def test_iki_asamali_derste_degisiklik_es_oturuma_da_uygulanir(vt, tmp_path: Path) -> None:
    """OKY md.58/2-e: komisyonların aynı üyelerden oluşturulması esastır."""
    _kur(vt, tmp_path)
    sonuc = _plan(vt)
    yazili, uygulama = _iki_asamali(sonuc)
    uye = next(g for g in sonuc.plan.oturum_gorevleri(yazili.anahtar)
               if g.rol is GorevRolu.KOMISYON_UYESI)
    aday = next(a for a in hizmet.gorevli_adaylari(vt, sonuc.plan, yazili.anahtar,
                                                     GorevRolu.KOMISYON_UYESI,
                                                     uye.personel_kimligi)
                if a["uygun_mu"] and a["kimlik"] not in {
                    g.personel_kimligi for g in sonuc.plan.oturum_gorevleri(uygulama.anahtar)})
    tasima = hizmet.gorevli_degistir(vt, sonuc.plan, yazili.anahtar, uye.personel_kimligi,
                                     aday["kimlik"], sonuc.yukseltilen_sinirlar,
                                     gerekce="Uydurma gerekçe")
    assert tasima.uygulandi, tasima.mesaj()
    for oturum in (yazili, uygulama):
        kimlikler = {g.personel_kimligi for g in sonuc.plan.oturum_gorevleri(oturum.anahtar)}
        assert aday["kimlik"] in kimlikler and uye.personel_kimligi not in kimlikler
