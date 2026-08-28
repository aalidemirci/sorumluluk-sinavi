"""Arayüz akış testleri.

Tkinter penceresi gerçekten kurulur; yalnızca gerçekten ekransız bir ortamda
(bkz. EKRANSIZ_IZLERI) atlanır, başka her Tk hatası testi kırar. Amaç görsel
denetim değil, arayüz ile servis katmanı arasındaki bağlantının kopmadığını
doğrulamak: plan üretme, sürükle-bırak taşıma, geri/ileri al ve kaydetme.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

tkinter = pytest.importorskip("tkinter")

from arayuz.uygulama import ADIMLAR  # noqa: E402
from testler.test_hizmet import AYARLAR, _personel_xlsx, _sorumluluk_csv  # noqa: E402
from veri import hizmet  # noqa: E402
from veri.veritabani import Veritabani  # noqa: E402

# Yalnızca bu izleri taşıyan TclError "ekran yok" sayılır. Liste bilinçli
# olarak dardır: eskiden bütün TclError'lar atlamaya yol açıyordu ve arayüzde
# bozulan bir şey testi kırmak yerine sessizce atlatabiliyordu.
EKRANSIZ_IZLERI = (
    "no display name",
    "couldn't connect to display",
    "can't find package tk",
)

TK_KOKU_DENEME = 5


def ekransiz_mi(hata: BaseException) -> bool:
    """TclError gerçekten ekransızlıktan mı geliyor?"""
    return any(iz in str(hata).lower() for iz in EKRANSIZ_IZLERI)


def sayfa(ad: str) -> int:
    """Adım adından sıra numarası.

    Sabit indis yazılırsa araya yeni bir adım eklendiğinde testler sessizce
    yanlış sayfayı açar; ADIMLAR'dan türetmek bunu önler.
    """
    return next(i for i, (_, baslik, _) in enumerate(ADIMLAR) if baslik == ad)


@pytest.fixture(scope="session")
def tk_koku():
    """Bütün oturumun paylaştığı tek Tk kökü.

    Her `tk.Tk()` çağrısı Tcl'in kitaplık dosyalarını (`tk.tcl`, `ttk/*.tcl`)
    yeniden okur. Bu dosyalar sanal ortamda değil sistem Python kurulumunda
    durur; makinedeki bütün süreçler aynı kopyayı paylaşır. Test başına bir
    kök kurulduğunda bu okuma on kez tekrarlanıyor ve virüs taraması dosyayı
    anlık kilitlediğinde `couldn't read file …` ya da
    `invalid command name "tcl_findLibrary"` hatası düşüyordu. Kökü bir kez
    kurmak bu yüzeyi onda bire indirir; kalan tek okuma da yeniden denenir.
    """
    hata = None
    for kalan in reversed(range(TK_KOKU_DENEME)):
        try:
            kok = tkinter.Tk()
            break
        except tkinter.TclError as tcl_hatasi:
            if ekransiz_mi(tcl_hatasi):
                pytest.skip(f"Tkinter ekranı yok: {tcl_hatasi}")
            hata = tcl_hatasi
            if not kalan:                 # geçici değilmiş: testler kırmızı versin
                raise
            time.sleep(0.3)
    if hata is not None:
        print(f"Tk kökü {TK_KOKU_DENEME - 1} denemeden sonra kuruldu; son hata: {hata}")
    kok.withdraw()                        # boş kök pencere ekranda görünmesin
    yield kok
    kok.destroy()


@pytest.fixture()
def uygulama(tk_koku, tmp_path: Path, monkeypatch):
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
    # Kök `tk_koku`dan gelir; buradaki TclError artık atlanmaz, testi kırar.
    pencere = Uygulama(tkinter.Toplevel(tk_koku))
    yield pencere
    pencere.kok.destroy()


def test_yalnizca_ekransizlik_testi_atlatir() -> None:
    """Atlama kuralı dar mı: gerçek arayüz hatası yutuluyor mu?

    Eskiden fikstür bütün TclError'ları yutup testi atlıyordu; arayüzde bozulan
    bir şey kırmızı vermek yerine sessizce atlanabiliyordu. Aşağıdaki ikinci
    grup, kararsızlığın kaynağı olan geçici Tcl okuma hatalarıdır — onlar da
    atlama sebebi değildir, yeniden denenir ve sürerse testi kırar.
    """
    assert ekransiz_mi(tkinter.TclError(
        'no display name and no $DISPLAY environment variable'))
    assert ekransiz_mi(tkinter.TclError('couldn\'t connect to display ":0"'))

    assert not ekransiz_mi(tkinter.TclError('invalid command name "tcl_findLibrary"'))
    assert not ekransiz_mi(tkinter.TclError(
        'couldn\'t read file ".../ttk/combobox.tcl": no such file or directory'))
    assert not ekransiz_mi(tkinter.TclError('unknown option "-bg"'))


def test_tum_sayfalar_hatasiz_cizilir(uygulama) -> None:
    """Adım eklendiğinde dağıtımın ADIMLAR ile uyumsuz kalmadığını doğrular."""
    for sira in range(len(ADIMLAR)):
        uygulama._sayfa_goster(sira)
        uygulama.kok.update_idletasks()


def test_plan_ekraninda_plan_uretilir(uygulama) -> None:
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama._plan_uret()
    assert uygulama.plan_sonucu is not None
    assert len(uygulama.plan_sonucu.plan.oturumlar) == 4
    assert uygulama.kaydedilmemis is True
    assert str(uygulama.kaydet_dugmesi["state"]) == "normal"


def test_surukle_birak_gecerli_tasimayi_uygular(uygulama) -> None:
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
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
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
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
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
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
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
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
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama._plan_uret()
    uygulama._plan_kaydet()
    plan_id = uygulama.aktif_plan_id
    uygulama._sayfa_goster(sayfa("Kurum Ayarları"))
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    assert uygulama.aktif_plan_id == plan_id
    assert uygulama.kaydedilmemis is False


def test_kesinlesen_plan_kilitlenir(uygulama, monkeypatch) -> None:
    monkeypatch.setattr("arayuz.uygulama.messagebox.showinfo", lambda *a, **k: None)
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
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
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
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


def test_basvuru_sayfasi_acilir_ve_bayrakli_ogrenciyi_gosterir(uygulama) -> None:
    """Başvuru sayfası servis katmanına bağlı mı; bayraklı öğrenci görünüyor mu."""
    from datetime import date

    with uygulama.vt.baglan() as b:
        ogrenci_id = b.execute("SELECT id FROM v_ogrenci ORDER BY okul_no").fetchone()[0]
    hizmet.ogrenci_bayrak_guncelle(uygulama.vt, ogrenci_id, True, False)
    hizmet.duyuru_kaydet(uygulama.vt, "P1", date(2026, 8, 28), date(2026, 9, 7),
                         "Duyuru 2026/1", "Okul web sayfası")

    uygulama._sayfa_goster(sayfa("Başvuru"))
    uygulama.kok.update_idletasks()

    satirlar = hizmet.basvuru_tablosu(uygulama.vt, "P1")
    bayrakli = [s for s in satirlar if s["bayrakli_mi"]]
    assert len(bayrakli) == 1
    assert bayrakli[0]["ozet"] == "KARAR BEKLİYOR"
    assert len(hizmet.basvuru_bekleyenler(uygulama.vt, "P1")) == 1
