"""OKY md.58/6 — tek ders sınavı.

"Sorumluluk sınavı sonunda tek dersten başarısızlığı bulunan son sınıf
öğrencileri için aynı usulle takip eden hafta içinde bir sınav daha yapılır."
Veriler uydurmadır (KVKK).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cekirdek.kurallar import engelleri_ayikla
from cekirdek.modeller import PlanParametreleri, PlanTuru
from cekirdek.takvim import tek_ders_penceresi
from veri import hizmet
from veri.hizmet import HizmetHatasi
from testler.test_hizmet import AYARLAR, _personel_xlsx, vt  # noqa: F401  (fikstür)
from testler.yardimci import sorumluluk_csv_yaz


TEK_DERS = PlanParametreleri(pencere_kodu="P1", plan_turu=PlanTuru.TEK_DERS)


@pytest.fixture()
def olagan_plan(vt, tmp_path: Path):
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.salon_ekle(vt, "D-01", 30)
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, _personel_xlsx(tmp_path)).aktarim_id)
    csv = sorumluluk_csv_yaz(tmp_path / "s.csv", {
        "12/A": [("401", "Uydurma Son Sınıf", [(11, "MATEMATİK"), (10, "FİZİK")])],
        "10/B": [("201", "Uydurma Onuncu", [(9, "MATEMATİK")])],
    })
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, csv).aktarim_id)
    for ders_id, ad, *_ in hizmet.dersleri_listele(vt):
        hizmet.ders_brans_esle(vt, ders_id, {"MATEMATİK": "Matematik", "FİZİK": "Fizik"}[ad],
                               "Zümre kararı")
    plan_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(vt, PlanParametreleri("P1")))
    return vt, plan_id


def test_adaylar_olagan_plandaki_son_sinif_ogrencileridir(olagan_plan) -> None:
    vt, _ = olagan_plan
    adaylar = hizmet.tek_ders_adaylari(vt, "P1")
    assert {a["okul_no"] for a in adaylar} == {"401"}
    assert {a["ders"] for a in adaylar} == {"MATEMATİK", "FİZİK"}
    assert not any(a["secili_mi"] for a in adaylar)


def test_ogrenci_basina_tek_ders_secilir(olagan_plan) -> None:
    vt, _ = olagan_plan
    adaylar = hizmet.tek_ders_adaylari(vt, "P1")
    matematik = next(a for a in adaylar if a["ders"] == "MATEMATİK")
    fizik = next(a for a in adaylar if a["ders"] == "FİZİK")
    hizmet.tek_ders_sec(vt, "P1", matematik["ogrenci_id"], matematik["sorumluluk_kaydi_id"])
    hizmet.tek_ders_sec(vt, "P1", fizik["ogrenci_id"], fizik["sorumluluk_kaydi_id"])
    secili = [a["ders"] for a in hizmet.tek_ders_adaylari(vt, "P1") if a["secili_mi"]]
    assert secili == ["FİZİK"]
    hizmet.tek_ders_sec(vt, "P1", fizik["ogrenci_id"], None)
    assert hizmet.tek_ders_kayitlari(vt, "P1") == []


def test_secim_yokken_tek_ders_plani_uretilmez(olagan_plan) -> None:
    vt, _ = olagan_plan
    with pytest.raises(HizmetHatasi, match="öğrenci seçilmedi"):
        hizmet.plan_hazirla(vt, TEK_DERS)


def test_tek_ders_plani_takip_eden_haftaya_kurulur(olagan_plan) -> None:
    vt, olagan_id = olagan_plan
    aday = next(a for a in hizmet.tek_ders_adaylari(vt, "P1") if a["ders"] == "MATEMATİK")
    hizmet.tek_ders_sec(vt, "P1", aday["ogrenci_id"], aday["sorumluluk_kaydi_id"])
    sonuc = hizmet.plan_hazirla(vt, TEK_DERS)
    olagan, _ = hizmet.plan_yukle(vt, olagan_id)
    bas, bit = tek_ders_penceresi(max(o.tarih for o in olagan.oturumlar))
    assert all(bas <= o.tarih <= bit for o in sonuc.plan.oturumlar)
    assert [o.ogrenci_anahtarlari for o in sonuc.plan.oturumlar] == [("401|12/A",)]
    assert engelleri_ayikla(sonuc.ihlaller) == []

    tek_id = hizmet.plan_kaydet(vt, sonuc)
    assert hizmet.son_plani_getir(vt, "P1", PlanTuru.TEK_DERS) == tek_id
    assert hizmet.son_plani_getir(vt, "P1") == olagan_id          # olağan plan yerinde
    yuklenen, _ = hizmet.plan_yukle(vt, tek_id)
    assert yuklenen.parametreler.plan_turu is PlanTuru.TEK_DERS
    assert not engelleri_ayikla(hizmet.plani_dogrula(vt, yuklenen))


def test_tek_ders_gorevleri_yillik_sayaca_girer(olagan_plan) -> None:
    vt, _ = olagan_plan
    once = sum(k["toplam"] for k in hizmet.gorev_havuzu_ozeti(vt))
    aday = next(a for a in hizmet.tek_ders_adaylari(vt, "P1") if a["ders"] == "MATEMATİK")
    hizmet.tek_ders_sec(vt, "P1", aday["ogrenci_id"], aday["sorumluluk_kaydi_id"])
    sonuc = hizmet.plan_hazirla(vt, TEK_DERS)
    hizmet.plan_kaydet(vt, sonuc)
    sonra = sum(k["toplam"] for k in hizmet.gorev_havuzu_ozeti(vt))
    assert sonra == once + len(sonuc.plan.gorevlendirmeler)
