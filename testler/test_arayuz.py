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

    # Ekranlar bugünün tarihine göre dönem seçer; testler takvimden bağımsız
    # olsun diye Eylül'e sabitlenir.
    monkeypatch.setattr(hizmet, "varsayilan_pencere",
                        lambda vt, gecmise_bak=False, bugun=None: "P1")
    from arayuz.uygulama import Uygulama
    # Kök `tk_koku`dan gelir; buradaki TclError artık atlanmaz, testi kırar.
    pencere = Uygulama(tkinter.Toplevel(tk_koku))
    yield pencere
    for cocuk in list(pencere.kok.winfo_children()):
        if isinstance(cocuk, tkinter.Toplevel):
            cocuk.destroy()
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


@pytest.mark.parametrize("sure, beklenen", [("90", "(uyg. –09:30)"), ("40", "(uyg.)")])
def test_sonraki_saate_tasan_uygulama_karti_bitisini_gosterir(uygulama, sure, beklenen) -> None:
    """Kart yalnız başladığı satırda çizilir; 08:00'de başlayan 90 dakikalık
    uygulama bitişiyle yazılmazsa 09:00 hücresi boş sanılır. 40 dakikada
    (olumsuz senaryo) kart eskisi gibidir."""
    from datetime import time as saat, timedelta
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama.uygulama_suresi.set(sure)
    uygulama._plan_uret()
    plan = uygulama.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if o.oturum_turu.value == "uygulama")
    hedef = max(o.tarih for o in plan.oturumlar) + timedelta(days=1)
    while hedef.weekday() >= 5:
        hedef += timedelta(days=1)
    uygulama._kart_birakildi(oturum.anahtar, hedef, saat(8, 0))
    assert (oturum.tarih, oturum.saat) == (hedef, saat(8, 0))
    kart = next(k for k in uygulama.takvim.kartlar if k["anahtar"] == oturum.anahtar)
    assert kart["baslik"].endswith(beklenen)


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


def test_basvuru_ekraninda_secilen_ogrencinin_isaretleri_kutulara_gelir(uygulama) -> None:
    """Eski sürümde kutular boş açılıyor, tek bayrağı değiştirmek isteyen
    kullanıcı öbürünü sessizce siliyordu: öğrenci başvurusuz plana giriyordu."""
    with uygulama.vt.baglan() as b:
        ogrenci_id = b.execute("SELECT id FROM v_ogrenci ORDER BY okul_no").fetchone()[0]
    hizmet.ogrenci_bayrak_guncelle(uygulama.vt, ogrenci_id, False, True)
    uygulama._sayfa_goster(sayfa("Başvuru"))
    uygulama.basvuru_tablosu.selection_set(str(ogrenci_id))
    uygulama.kok.update()
    mezun, devamsiz = uygulama.basvuru_isaretleri
    assert mezun.get() is False and devamsiz.get() is True


def _plan_kaydet(uygulama, monkeypatch) -> int:
    monkeypatch.setattr("arayuz.uygulama.messagebox.showinfo", lambda *a, **k: None)
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama._plan_uret()
    uygulama._plan_kaydet()
    return uygulama.aktif_plan_id


def test_donem_degisince_o_donemin_plani_acilir(uygulama, monkeypatch) -> None:
    """Eski sürümde dönem kutusu değişse de ekranda Eylül planı kalıyordu."""
    plan_id = _plan_kaydet(uygulama, monkeypatch)
    secenekler = [s[1:] for s in uygulama._plan_secenekleri]
    from cekirdek.modeller import PlanTuru
    uygulama.pencere_secimi.current(secenekler.index(("P2", PlanTuru.OLAGAN)))
    uygulama._plan_donemi_degisti()
    assert uygulama.aktif_plan_id is None and uygulama.plan_sonucu is None
    uygulama.pencere_secimi.current(secenekler.index(("P1", PlanTuru.OLAGAN)))
    uygulama._plan_donemi_degisti()
    assert uygulama.aktif_plan_id == plan_id


def test_kaydedilmemis_plan_sayfa_degisince_kaybolmaz(uygulama) -> None:
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama._plan_uret()
    uretilen = uygulama.plan_sonucu
    uygulama._sayfa_goster(sayfa("Salonlar"))
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    assert uygulama.plan_sonucu is uretilen and uygulama.kaydedilmemis is True


def test_karta_tiklamak_gorevlileri_gosterir(uygulama) -> None:
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama._plan_uret()
    oturum = uygulama.plan_sonucu.plan.oturumlar[0]
    uygulama._kart_secildi(oturum.anahtar)
    assert "Komisyon:" in uygulama.secim_etiketi["text"]
    assert str(uygulama.gorevli_dugmesi["state"]) == "normal"


def test_gorevli_degistir_penceresi_degisikligi_uygular_ve_geri_alinir(uygulama) -> None:
    from arayuz.pencereler import GorevliDegistirPenceresi
    uygulama._sayfa_goster(sayfa("Sınav Planı"))
    uygulama._plan_uret()
    plan = uygulama.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    pencere = GorevliDegistirPenceresi(uygulama, oturum.anahtar)
    gozcu = next(i for i in pencere.mevcut.get_children() if i.endswith("|gozcu"))
    pencere.mevcut.selection_set(gozcu)
    pencere._adaylari_doldur()
    aday = pencere.adaylar.get_children()[0]
    pencere.adaylar.selection_set(aday)
    pencere._degistir()
    assert int(aday) in {g.personel_kimligi for g in plan.oturum_gorevleri(oturum.anahtar)}
    assert len(uygulama.geri_yigini) == 1 and uygulama.kaydedilmemis
    uygulama._geri_al()
    assert int(aday) not in {g.personel_kimligi for g in plan.oturum_gorevleri(oturum.anahtar)}


def test_tek_ders_ve_musaitlik_pencereleri_acilir(uygulama, monkeypatch) -> None:
    from arayuz.pencereler import MusaitlikPenceresi, TekDersPenceresi
    _plan_kaydet(uygulama, monkeypatch)
    TekDersPenceresi(uygulama, "P1").destroy()
    uygulama._sayfa_goster(sayfa("Öğretmen Listesi"))
    kisi = uygulama.personel_kayitlari[0]
    pencere = MusaitlikPenceresi(uygulama, kisi)
    pencere.gun.current(2)
    pencere.h_bas.insert(0, "08:00")
    pencere.h_bit.insert(0, "12:00")
    pencere._haftalik_ekle()
    assert len(pencere.tablo.get_children()) == 1
    pencere._kapat()
    assert hizmet.musaitlik_listesi(uygulama.vt, kisi["kimlik"])[0]["zaman"] == "Her çarşamba"


def test_takvim_kalabalik_hucredeki_butun_kartlari_cizer(tk_koku) -> None:
    """Eski sürüm bir hücreye üçten fazla oturum düşünce fazlasını çizmiyordu."""
    from datetime import date, time
    from arayuz.takvim import SurukleBirakTakvim
    ust = tkinter.Toplevel(tk_koku)
    try:
        kartlar = [{"anahtar": f"k{i}", "baslik": f"Ders {i}", "tarih": date(2026, 9, 14),
                    "saat": time(9, 0), "tur": "yazili", "kilitli": False} for i in range(6)]
        takvim = SurukleBirakTakvim(ust, [date(2026, 9, 14)], [time(9, 0), time(10, 0)],
                                    kartlar, lambda *a: None)
        cizilen = {etiket for nesne in takvim.canvas.find_withtag("kart")
                   for etiket in takvim.canvas.gettags(nesne) if etiket.startswith("kart:")}
        assert cizilen == {f"kart:k{i}" for i in range(6)}
        # Satır büyüdüğü için ikinci saatin hücresi hâlâ doğru bulunur.
        x, y = takvim.hucre_merkezi(date(2026, 9, 14), time(10, 0))
        assert takvim._koordinattan_hucre(x, y) == (0, 1)
    finally:
        ust.destroy()
