"""Arayüz akış testleri.

Tkinter penceresi gerçekten kurulur; ekran yoksa test atlanır. Amaç görsel
denetim değil, arayüz ile servis katmanı arasındaki bağlantının kopmadığını
doğrulamak: plan üretme, sürükle-bırak taşıma, geri/ileri al ve kaydetme.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

tkinter = pytest.importorskip("tkinter")

from testler.test_hizmet import AYARLAR, _personel_xlsx, _sorumluluk_csv  # noqa: E402
from veri import hizmet  # noqa: E402
from veri.veritabani import Veritabani  # noqa: E402


@pytest.fixture()
def uygulama(tmp_path: Path, monkeypatch):
    """Hazır veriyle kurulmuş bir uygulama penceresi."""
    monkeypatch.setenv("SORUMLULUK_VERI_KLASORU", str(tmp_path))
    vt = Veritabani(tmp_path / "sorumluluk.db")
    vt.gocleri_uygula()
    hizmet.ayarlari_kaydet(vt, AYARLAR)
    hizmet.salon_ekle(vt, "D-01", 30)
    hizmet.salon_ekle(vt, "D-02", 30)
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, _personel_xlsx(tmp_path)).aktarim_id)
    hizmet.sorumluluk_onayla(
        vt, hizmet.sorumluluk_onizle(vt, _sorumluluk_csv(tmp_path)).aktarim_id)
    for ders_id, ad, *_ in hizmet.dersleri_listele(vt):
        brans = {"MATEMATİK": "Matematik", "FİZİK": "Fizik", "İNGİLİZCE": "İngilizce"}[ad]
        hizmet.ders_brans_esle(vt, ders_id, brans, "Zümre kararı")
        if ad == "İNGİLİZCE":
            hizmet.ders_ozellik_guncelle(vt, ders_id, True, True)

    from arayuz.uygulama import Uygulama
    try:
        pencere = Uygulama()
    except tkinter.TclError:                      # pragma: no cover - ekransız ortam
        pytest.skip("Tkinter ekranı yok")
    yield pencere
    pencere.kok.destroy()


def test_tum_sayfalar_acilir(uygulama) -> None:
    for sayfa in range(6):
        uygulama._sayfa_goster(sayfa)


def test_plan_ekraninda_plan_uretilir(uygulama) -> None:
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    assert uygulama.plan_sonucu is not None
    assert len(uygulama.plan_sonucu.plan.oturumlar) == 4
    assert uygulama.kaydedilmemis is True
    assert str(uygulama.kaydet_dugmesi["state"]) == "normal"


def test_surukle_birak_gecerli_tasimayi_uygular(uygulama) -> None:
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    plan = uygulama.plan_sonucu.plan
    # Tek aşamalı bir oturumu bir gün ileri taşı.
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    yeni_tarih = max(o.tarih for o in plan.oturumlar)
    from datetime import timedelta
    hedef = yeni_tarih + timedelta(days=1)
    while hedef.weekday() >= 5:
        hedef += timedelta(days=1)
    uygulama._kart_birakildi(oturum.anahtar, hedef, oturum.saat)
    assert plan.oturum_bul(oturum.anahtar).tarih == hedef
    assert len(uygulama.geri_yigini) == 1


def test_geri_al_ve_ileri_al_calisir(uygulama) -> None:
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    plan = uygulama.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    onceki_tarih = oturum.tarih
    from datetime import timedelta
    hedef = max(o.tarih for o in plan.oturumlar) + timedelta(days=1)
    while hedef.weekday() >= 5:
        hedef += timedelta(days=1)
    uygulama._kart_birakildi(oturum.anahtar, hedef, oturum.saat)
    assert plan.oturum_bul(oturum.anahtar).tarih == hedef

    uygulama._geri_al()
    assert plan.oturum_bul(oturum.anahtar).tarih == onceki_tarih
    assert str(uygulama.geri_dugmesi["state"]) == "disabled"

    uygulama._ileri_al()
    assert plan.oturum_bul(oturum.anahtar).tarih == hedef


def test_ogrenci_cakismasi_tasimayi_engeller(uygulama, monkeypatch) -> None:
    """Aynı öğrencinin iki sınavı aynı saate getirilemez."""
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    plan = uygulama.plan_sonucu.plan
    # 101 numaralı öğrenci hem MATEMATİK hem FİZİK sınavına giriyor.
    matematik = next(o for o in plan.oturumlar if o.ders_adi == "MATEMATİK")
    fizik = next(o for o in plan.oturumlar if o.ders_adi == "FİZİK")
    uyarilar = []
    monkeypatch.setattr("arayuz.uygulama.messagebox.showwarning",
                        lambda baslik, mesaj, **k: uyarilar.append(mesaj))
    onceki = fizik.tarih, fizik.saat
    uygulama._kart_birakildi(fizik.anahtar, matematik.tarih, matematik.saat)
    assert (fizik.tarih, fizik.saat) == onceki          # taşıma geri alındı
    assert uyarilar and "Öğrenci çakışması" in uyarilar[0]


def test_kaydet_plani_veritabanina_yazar(uygulama, monkeypatch) -> None:
    monkeypatch.setattr("arayuz.uygulama.messagebox.showinfo", lambda *a, **k: None)
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    uygulama._plan_kaydet()
    assert uygulama.aktif_plan_id is not None
    assert uygulama.kaydedilmemis is False
    assert str(uygulama.kaydet_dugmesi["state"]) == "disabled"
    plan, bilgi = hizmet.plan_yukle(uygulama.vt, uygulama.aktif_plan_id)
    assert len(plan.oturumlar) == 4
    assert bilgi["kesin_mi"] == 0


def test_kaydedilen_plan_yeniden_acildiginda_yuklenir(uygulama, monkeypatch) -> None:
    monkeypatch.setattr("arayuz.uygulama.messagebox.showinfo", lambda *a, **k: None)
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    uygulama._plan_kaydet()
    plan_id = uygulama.aktif_plan_id
    uygulama._sayfa_goster(0)
    uygulama._sayfa_goster(5)
    assert uygulama.aktif_plan_id == plan_id
    assert uygulama.kaydedilmemis is False


def test_kesinlesen_plan_kilitlenir(uygulama, monkeypatch) -> None:
    monkeypatch.setattr("arayuz.uygulama.messagebox.showinfo", lambda *a, **k: None)
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    uygulama._plan_kaydet()
    uygulama.onay_girdisi.delete(0, "end")
    uygulama.onay_girdisi.insert(0, "2026/144")
    uygulama._plan_kesinlestir()
    plan, bilgi = hizmet.plan_yukle(uygulama.vt, uygulama.aktif_plan_id)
    assert bilgi["kesin_mi"] == 1
    assert all(o.kilitli_mi for o in plan.oturumlar)


def test_kilitli_oturum_tasinamaz(uygulama, monkeypatch) -> None:
    monkeypatch.setattr("arayuz.uygulama.messagebox.showinfo", lambda *a, **k: None)
    hatalar = []
    monkeypatch.setattr("arayuz.uygulama.messagebox.showerror",
                        lambda baslik, mesaj, **k: hatalar.append(mesaj))
    uygulama._sayfa_goster(5)
    uygulama._plan_uret()
    uygulama._plan_kaydet()
    uygulama.onay_girdisi.delete(0, "end")
    uygulama.onay_girdisi.insert(0, "2026/144")
    uygulama._plan_kesinlestir()
    plan = uygulama.plan_sonucu.plan
    oturum = plan.oturumlar[0]
    from datetime import timedelta
    uygulama._kart_birakildi(oturum.anahtar, oturum.tarih + timedelta(days=1), oturum.saat)
    assert hatalar and "kilitli oturum" in hatalar[0].lower()
