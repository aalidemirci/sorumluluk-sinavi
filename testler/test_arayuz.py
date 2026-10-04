"""Arayüz akış testleri (Qt, ekransız).

Pencere gerçekten kurulur; amaç görsel denetim değil, arayüz ile servis
katmanı arasındaki bağlantının kopmadığını doğrulamak: plan üretme,
sürükle-bırak taşıma, geri/ileri al, kaydetme, başvuru işaretleri ve
güncelleme şeridi. İleti kutuları kayıt tutan sahteyle değiştirilir;
pencereler açılmadan kurulup yöntemleri doğrudan çağrılır.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QItemSelectionModel, Qt  # noqa: E402

from arayuz import tema  # noqa: E402
from arayuz.uygulama import ADIMLAR, Uygulama, sayfa_sirasi  # noqa: E402
from cekirdek.modeller import PlanTuru  # noqa: E402
from testler.test_hizmet import AYARLAR, _personel_xlsx, _sorumluluk_csv  # noqa: E402
from veri import hizmet  # noqa: E402
from veri.veritabani import Veritabani  # noqa: E402

PLAN_ZAMAN_ASIMI_MS = 120_000


class KayitliIleti:
    """İleti kutularının yerine geçer: ne gösterildiğini kaydeder, soruya `cevap` döner."""

    def __init__(self) -> None:
        self.kayitlar: list[tuple[str, str, str]] = []
        self.cevap = True
        self.metin_cevabi: str | None = None      # None: önerilen metin kabul edilir
        self.metin_vazgec = False

    def hata(self, baslik: str, metin: str, ust=None) -> None:
        self.kayitlar.append(("hata", baslik, metin))

    def uyari(self, baslik: str, metin: str, ust=None) -> None:
        self.kayitlar.append(("uyari", baslik, metin))

    def bilgi(self, baslik: str, metin: str, ust=None) -> None:
        self.kayitlar.append(("bilgi", baslik, metin))

    def soru(self, baslik: str, metin: str, evet: str = "Evet", hayir: str = "Vazgeç",
             uyari: bool = False, ust=None) -> bool:
        self.kayitlar.append(("soru", baslik, metin))
        return self.cevap

    def metin_iste(self, baslik: str, metin: str, varsayilan: str = "", ust=None) -> str | None:
        self.kayitlar.append(("metin", baslik, metin))
        if self.metin_vazgec:
            return None
        return varsayilan if self.metin_cevabi is None else self.metin_cevabi

    def turden(self, tur: str) -> list[str]:
        return [metin for t, _b, metin in self.kayitlar if t == tur]


@pytest.fixture(scope="session", autouse=True)
def _tema(qapp):
    """Gerçek stil sayfası uygulanır: bozuk bir kural burada da görünür."""
    tema.uygula(qapp)


@pytest.fixture()
def uygulama(qtbot, tmp_path: Path, monkeypatch):
    """Hazır veriyle kurulmuş bir ana pencere."""
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
    # Ekranlar bugünün tarihine göre dönem seçer; testler Eylül'e sabitlenir.
    monkeypatch.setattr(hizmet, "varsayilan_pencere",
                        lambda vt, gecmise_bak=False, bugun=None: "P1")
    pencere = Uygulama()
    pencere.ileti = KayitliIleti()
    qtbot.addWidget(pencere)
    yield pencere
    pencere.sayfalar.get(sayfa_sirasi("Sınav Planı")) and setattr(
        pencere.sayfalar[sayfa_sirasi("Sınav Planı")], "kaydedilmemis", False)


def plan_sayfasi(uyg):
    uyg.sayfa_goster(sayfa_sirasi("Sınav Planı"))
    return uyg.sayfalar[sayfa_sirasi("Sınav Planı")]


def plan_uret(uyg, qtbot):
    sayfa = plan_sayfasi(uyg)
    sayfa.plan_sonucu = None
    sayfa.plan_uret()
    qtbot.waitUntil(lambda: sayfa.plan_sonucu is not None and not uyg.mesgul.isVisible(),
                    timeout=PLAN_ZAMAN_ASIMI_MS)
    return sayfa


def basvuru_sayfasi(uyg):
    uyg.sayfa_goster(sayfa_sirasi("Başvuru"))
    return uyg.sayfalar[sayfa_sirasi("Başvuru")]


def _ogrenci_id(vt, okul_no: str) -> int:
    with vt.baglan() as b:
        return b.execute("SELECT id FROM v_ogrenci WHERE okul_no=?", (okul_no,)).fetchone()[0]


def _bos_is_gunu(plan) -> date:
    hedef = max(o.tarih for o in plan.oturumlar) + timedelta(days=1)
    while hedef.weekday() >= 5:
        hedef += timedelta(days=1)
    return hedef


# ================================================================== genel

def test_tum_sayfalar_hatasiz_acilir(uygulama) -> None:
    """Adım eklendiğinde sayfa sınıfı ve ADIMLAR uyumsuz kalmasın."""
    for sira, adim in enumerate(ADIMLAR):
        uygulama.sayfa_goster(sira)
        assert uygulama.baslik.text() == adim[1]
        assert uygulama.yigin.currentWidget() is uygulama.sayfalar[sira]
    assert uygulama.ileti.turden("hata") == []


def test_qt_metinleri_turkce(qapp) -> None:
    """Sağ tık menüsü ve standart düğmeler Qt'nin Türkçe çevirisinden gelir."""
    from PySide6.QtCore import QCoreApplication
    assert QCoreApplication.translate("QLineEdit", "&Undo") == "&Geri Al"
    assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "İptal"


def test_beklenmeyen_hata_gosterilir_iletisi_gunluge_yazilmaz(uygulama, caplog) -> None:
    """Paketlenmiş programda konsol yok: yuvada fırlatılan beklenmeyen hata
    kullanıcıya gösterilir. Günlüğe çağrı yığını ve tür yazılır; ileti öğrenci
    adı taşıyabileceği için yazılmaz (KVKK)."""
    import logging
    import sys
    from arayuz.uygulama import beklenmeyen_hata_kancasi
    kanca = beklenmeyen_hata_kancasi(uygulama)
    uygulama.mesgul_ac("Deneme")
    ad = "Uydurma " + "Öğrenci Bir"        # kaynak satırında ad geçmesin
    try:
        raise KeyError(ad)
    except KeyError:
        tur, deger, iz = sys.exc_info()
    with caplog.at_level(logging.ERROR):
        kanca(tur, deger, iz)
    assert "KeyError" in caplog.text and "test_arayuz.py" in caplog.text
    assert ad not in caplog.text
    assert any(ad in metin for metin in uygulama.ileti.turden("hata"))
    assert not uygulama.mesgul.isVisible()


def test_kisayol_etkin_sayfaya_iletilir(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    assert sayfa.kaydedilmemis
    uygulama._sayfaya_ilet("kisayol_kaydet")
    assert not sayfa.kaydedilmemis and sayfa.aktif_plan_id is not None


def test_kapanista_kaydedilmemis_plan_sorulur(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    uygulama.show()
    uygulama.ileti.cevap = False
    assert uygulama.close() is False
    assert uygulama.ileti.turden("soru") and sayfa.kaydedilmemis


# ============================================================ sınav planı

def test_plan_ekraninda_plan_uretilir(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    assert len(sayfa.plan_sonucu.plan.oturumlar) == 4
    assert sayfa.kaydedilmemis is True
    assert sayfa.kaydet_dugmesi.isEnabled()
    assert set(sayfa.takvim.kart_widgetlari) == {o.anahtar for o in sayfa.plan_sonucu.plan.oturumlar}


def test_surukle_birak_gecerli_tasimayi_uygular_ve_geri_alinir(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    onceki, hedef = oturum.tarih, _bos_is_gunu(plan)
    sayfa.kart_birakildi(oturum.anahtar, hedef, oturum.saat)
    assert plan.oturum_bul(oturum.anahtar).tarih == hedef
    assert len(sayfa.geri_yigini) == 1
    sayfa.geri_al()
    assert plan.oturum_bul(oturum.anahtar).tarih == onceki
    assert not sayfa.geri_dugmesi.isEnabled()
    sayfa.ileri_al()
    assert plan.oturum_bul(oturum.anahtar).tarih == hedef


def test_hafta_sonuna_surukleyince_gerekce_sorulur(uygulama, qtbot) -> None:
    """SP-05 (OKY md.58/2-ç): hafta sonu oturumu gerekçe ister. Elle taşımada
    girilecek yer olmadığından gerçek verinin kopyasıyla denemede hafta sonuna
    her taşıma geri alınıyordu. Olumsuz senaryo: sorudan vazgeçilirse taşıma
    yapılmaz ve "taşınamadı" uyarısı da çıkmaz."""
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    onceki, cumartesi = oturum.tarih, date(2026, 9, 19)
    uygulama.ileti.metin_vazgec = True
    sayfa.kart_birakildi(oturum.anahtar, cumartesi, oturum.saat)
    assert oturum.tarih == onceki and not uygulama.ileti.turden("uyari")
    assert any("OKY md.58/2-ç" in m for m in uygulama.ileti.turden("metin"))
    uygulama.ileti.metin_vazgec = False
    uygulama.ileti.metin_cevabi = "Uydurma gerekçe: hafta içi salon yok."
    sayfa.kart_birakildi(oturum.anahtar, cumartesi, oturum.saat)
    assert oturum.tarih == cumartesi
    assert oturum.hafta_sonu_gerekcesi == "Uydurma gerekçe: hafta içi salon yok."
    sayfa.geri_al()
    assert oturum.tarih == onceki and oturum.hafta_sonu_gerekcesi == ""


def test_salonu_degisen_tasima_bildirimde_yazilir(uygulama, qtbot, monkeypatch) -> None:
    """Salon değişikliği evrakı (salon listeleri) etkiler; bildirim bunu söyler.
    Olumsuz senaryo: salonu değişmeyen taşımada ek cümle yoktur."""
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    bildirimler = _bildirimleri_kaydet(uygulama, monkeypatch)
    asil = hizmet.oturum_tasi
    for degisti in (True, False):
        def sahte(*a, **k):
            sonuc = asil(*a, **k)
            sonuc.salon_degisti = degisti and sonuc.uygulandi
            return sonuc

        monkeypatch.setattr(hizmet, "oturum_tasi", sahte)
        oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
        sayfa.kart_birakildi(oturum.anahtar, _bos_is_gunu(plan), oturum.saat)
        assert ("boş salona geçirildi" in bildirimler[-1]) is degisti
        sayfa.geri_al()


def test_hafta_ici_tasimada_gerekce_sorulmaz(uygulama, qtbot) -> None:
    """Olumsuz senaryo: hafta içine taşımada gerekçe sorusu çıkmaz."""
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    hedef = _bos_is_gunu(plan)
    sayfa.kart_birakildi(oturum.anahtar, hedef, oturum.saat)
    assert oturum.tarih == hedef and not uygulama.ileti.turden("metin")


def test_ogrenci_cakismasi_tasimayi_engeller(uygulama, qtbot) -> None:
    """Aynı öğrencinin iki sınavı aynı saate getirilemez (101: MATEMATİK ve FİZİK)."""
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    matematik = next(o for o in plan.oturumlar if o.ders_adi == "MATEMATİK")
    fizik = next(o for o in plan.oturumlar if o.ders_adi == "FİZİK")
    onceki = fizik.tarih, fizik.saat
    sayfa.kart_birakildi(fizik.anahtar, matematik.tarih, matematik.saat)
    assert (fizik.tarih, fizik.saat) == onceki
    assert any("Öğrenci çakışması" in m for m in uygulama.ileti.turden("uyari"))


def test_kaydet_ve_yeniden_acilis(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    sayfa.plan_kaydet()
    plan_id = sayfa.aktif_plan_id
    assert plan_id is not None and not sayfa.kaydedilmemis
    plan, bilgi = hizmet.plan_yukle(uygulama.vt, plan_id)
    assert len(plan.oturumlar) == 4 and bilgi["kesin_mi"] == 0
    uygulama.sayfa_goster(sayfa_sirasi("Kurum Ayarları"))
    uygulama.sayfa_goster(sayfa_sirasi("Sınav Planı"))
    assert sayfa.aktif_plan_id == plan_id and not sayfa.kaydedilmemis


def test_kaydedilmemis_plan_sayfa_degisince_kaybolmaz(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    uretilen = sayfa.plan_sonucu
    uygulama.sayfa_goster(sayfa_sirasi("Salonlar"))
    uygulama.sayfa_goster(sayfa_sirasi("Sınav Planı"))
    assert sayfa.plan_sonucu is uretilen and sayfa.kaydedilmemis


def test_donem_degisince_o_donemin_plani_acilir(uygulama, qtbot) -> None:
    """Eski sürümde dönem kutusu değişse de ekranda Eylül planı kalıyordu."""
    sayfa = plan_uret(uygulama, qtbot)
    sayfa.plan_kaydet()
    plan_id = sayfa.aktif_plan_id
    secenekler = [s[1:] for s in sayfa.secenekler]
    sayfa.pencere_secimi.setCurrentIndex(secenekler.index(("P2", PlanTuru.OLAGAN)))
    assert sayfa.aktif_plan_id is None and sayfa.plan_sonucu is None
    sayfa.pencere_secimi.setCurrentIndex(secenekler.index(("P1", PlanTuru.OLAGAN)))
    assert sayfa.aktif_plan_id == plan_id


def test_kesinlesen_plan_kilitlenir_ve_tasinamaz(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    sayfa.plan_kaydet()
    sayfa.onay_girdisi.setText("2026/144")
    sayfa.plan_kesinlestir()
    plan, bilgi = hizmet.plan_yukle(uygulama.vt, sayfa.aktif_plan_id)
    assert bilgi["kesin_mi"] == 1 and all(o.kilitli_mi for o in plan.oturumlar)
    assert not sayfa.kesinlestir_dugmesi.isEnabled()
    oturum = sayfa.plan_sonucu.plan.oturumlar[0]
    sayfa.kart_birakildi(oturum.anahtar, oturum.tarih + timedelta(days=1), oturum.saat)
    assert any("kilitli oturum" in m.lower() for m in uygulama.ileti.turden("hata"))


def test_karta_tiklamak_gorevlileri_gosterir(uygulama, qtbot) -> None:
    sayfa = plan_uret(uygulama, qtbot)
    oturum = sayfa.plan_sonucu.plan.oturumlar[0]
    sayfa.takvim.secildi(oturum.anahtar)
    assert "Komisyon:" in sayfa.secim_etiketi.text()
    assert sayfa.gorevli_dugmesi.isEnabled()
    assert sayfa.takvim.kart_widgetlari[oturum.anahtar].property("secili") is True


def test_gorevli_degistir_penceresi_degisikligi_uygular_ve_geri_alinir(uygulama, qtbot) -> None:
    from arayuz.pencereler import GorevliDegistirPenceresi
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if not o.birim_anahtari)
    pencere = GorevliDegistirPenceresi(uygulama, sayfa, oturum.anahtar)
    qtbot.addWidget(pencere)
    gozcu = next(g for g in plan.oturum_gorevleri(oturum.anahtar) if g.rol.value == "gozcu")
    assert pencere.mevcut.sec(f"{gozcu.personel_kimligi}|gozcu")
    aday = next(a for a in pencere.adaylar.gorunen_satirlar() if a["uygun_mu"])
    assert pencere.adaylar.sec(aday["kimlik"])
    pencere.degistir()
    assert aday["kimlik"] in {g.personel_kimligi for g in plan.oturum_gorevleri(oturum.anahtar)}
    assert len(sayfa.geri_yigini) == 1 and sayfa.kaydedilmemis
    sayfa.geri_al()
    assert aday["kimlik"] not in {g.personel_kimligi
                                  for g in plan.oturum_gorevleri(oturum.anahtar)}


@pytest.mark.parametrize("sure, beklenen, suren", [(90, "(uyg. –09:30)", True),
                                                   (40, "(uyg.)", False)])
def test_sonraki_saate_tasan_uygulama_takvimde_gorunur(uygulama, qtbot, sure, beklenen,
                                                       suren) -> None:
    """Kart yalnız başladığı satırda çizilir; 08:00'de başlayan 90 dakikalık
    uygulama bitişiyle yazılır ve 09:00 hücresinde "sürüyor" işareti bırakır.
    40 dakikada (olumsuz senaryo) kart eskisi gibidir."""
    sayfa = plan_sayfasi(uygulama)
    sayfa.uygulama_suresi.setValue(sure)
    sayfa = plan_uret(uygulama, qtbot)
    plan = sayfa.plan_sonucu.plan
    oturum = next(o for o in plan.oturumlar if o.oturum_turu.value == "uygulama")
    hedef = _bos_is_gunu(plan)
    sayfa.kart_birakildi(oturum.anahtar, hedef, time(8, 0))
    assert (oturum.tarih, oturum.saat) == (hedef, time(8, 0))
    kart = next(k for k in sayfa.takvim.kartlar if k["anahtar"] == oturum.anahtar)
    assert kart["baslik"].endswith(beklenen)
    hucre = sayfa.takvim.hucre(hedef, time(9, 0))
    surenler = [hucre.duzen.itemAt(i).widget() for i in range(hucre.duzen.count())
                if hucre.duzen.itemAt(i).widget() is not None]
    assert any(w.objectName() == "Suren" for w in surenler) is suren


def test_takvim_kalabalik_hucredeki_butun_kartlari_cizer(qtbot) -> None:
    """Eski sürüm bir hücreye üçten fazla oturum düşünce fazlasını çizmiyordu."""
    from arayuz.takvim import SurukleBirakTakvim
    kartlar = [{"anahtar": f"k{i}", "baslik": f"Ders {i}", "tarih": date(2026, 9, 14),
                "saat": time(9, 0), "tur": "yazili", "kilitli": False} for i in range(6)]
    takvim = SurukleBirakTakvim([date(2026, 9, 14)], [time(9, 0), time(10, 0)], kartlar,
                                lambda *a: None)
    qtbot.addWidget(takvim)
    assert set(takvim.kart_widgetlari) == {f"k{i}" for i in range(6)}
    assert takvim.hucre(date(2026, 9, 14), time(10, 0)) is not None


def test_tek_ders_ve_musaitlik_pencereleri(uygulama, qtbot) -> None:
    from arayuz.pencereler import MusaitlikPenceresi, TekDersPenceresi
    sayfa = plan_uret(uygulama, qtbot)
    sayfa.plan_kaydet()
    tek = TekDersPenceresi(uygulama, "P1")
    qtbot.addWidget(tek)
    kisi = hizmet.personel_ayrintili_liste(uygulama.vt)[0]
    pencere = MusaitlikPenceresi(uygulama, kisi)
    qtbot.addWidget(pencere)
    pencere.gun.setCurrentIndex(2)
    pencere.h_bas.setText("08:00")
    pencere.h_bit.setText("12:00")
    pencere._haftalik_ekle()
    assert pencere.tablo.model.rowCount() == 1
    assert hizmet.musaitlik_listesi(uygulama.vt, kisi["kimlik"])[0]["zaman"] == "Her çarşamba"


# ================================================================ başvuru

def _satir_sec(tablo, anahtarlar) -> None:
    secim = tablo.gorunum.selectionModel()
    secim.clearSelection()
    for satir in range(tablo.suzgec.rowCount()):
        indeks = tablo.suzgec.index(satir, 0)
        if tablo.suzgec.data(indeks, Qt.ItemDataRole.UserRole) in anahtarlar:
            secim.select(indeks, QItemSelectionModel.SelectionFlag.Select
                         | QItemSelectionModel.SelectionFlag.Rows)


def test_basvuruda_kutucuk_hemen_kaydeder_ve_geri_alinir(uygulama) -> None:
    """Tk sürümünde öğrenci seçilip kutu işaretleniyor, ayrı düğmeyle kaydediliyor
    ve sayfa baştan çiziliyordu. Burada kutucuk hemen kaydeder, bildirim geri alır."""
    sayfa = basvuru_sayfasi(uygulama)
    kimlik = _ogrenci_id(uygulama.vt, "102")
    satir = next(s for s in sayfa.tablo.gorunen_satirlar() if s["ogrenci_id"] == kimlik)
    sayfa.tablo.model.setData(sayfa.tablo.model.index(sayfa.tablo.model.sira_bul(kimlik), 0),
                              Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
    guncel = {s["ogrenci_id"]: s for s in hizmet.basvuru_tablosu(uygulama.vt, "P1")}
    assert guncel[kimlik]["mezun_olamayan_mi"] and not guncel[kimlik]["devamsizlik_tebligati_mi"]
    assert satir["okul_no"] in uygulama.bildirim.metin.text()
    assert uygulama.bildirim.eylem.isVisibleTo(uygulama.bildirim)
    uygulama.bildirim.eylem.click()
    guncel = {s["ogrenci_id"]: s for s in hizmet.basvuru_tablosu(uygulama.vt, "P1")}
    assert not guncel[kimlik]["bayrakli_mi"]


def test_basvuruda_toplu_isaret_obur_bayraga_dokunmaz(uygulama) -> None:
    sayfa = basvuru_sayfasi(uygulama)
    birinci, ikinci = _ogrenci_id(uygulama.vt, "101"), _ogrenci_id(uygulama.vt, "102")
    hizmet.ogrenci_bayrak_guncelle(uygulama.vt, ikinci, False, True)
    sayfa.tazele()
    _satir_sec(sayfa.tablo, {birinci, ikinci})
    sayfa.toplu_isaretle("mezun_olamayan", True)
    guncel = {s["ogrenci_id"]: s for s in hizmet.basvuru_tablosu(uygulama.vt, "P1")}
    assert guncel[birinci]["mezun_olamayan_mi"] and guncel[ikinci]["mezun_olamayan_mi"]
    assert guncel[ikinci]["devamsizlik_tebligati_mi"]          # öbür bayrak korundu
    assert {s["ogrenci_id"] for s in sayfa.tablo.secili_satirlar()} == {birinci, ikinci}


def test_basvuru_aramasi_ve_suzgecleri(uygulama, qtbot) -> None:
    sayfa = basvuru_sayfasi(uygulama)
    toplam = sayfa.tablo.suzgec.rowCount()
    assert toplam == 3
    sayfa.tablo.suzgec.aramayi_ayarla("ogrenci iki")          # Türkçe karaktersiz yazım
    assert [s["okul_no"] for s in sayfa.tablo.gorunen_satirlar()] == ["102"]
    sayfa.tablo.suzgec.aramayi_ayarla("")
    sayfa.yalniz_isaretli.setChecked(True)
    assert sayfa.tablo.suzgec.rowCount() == 0
    sayfa.yalniz_isaretli.setChecked(False)
    sayfa.sube_suzgeci.setCurrentText("10/B")
    assert [s["okul_no"] for s in sayfa.tablo.gorunen_satirlar()] == ["201"]


def test_numara_listesiyle_isaretleme(uygulama, qtbot) -> None:
    from arayuz.pencereler import NumaraListesiPenceresi
    basvuru_sayfasi(uygulama)
    pencere = NumaraListesiPenceresi(uygulama)
    qtbot.addWidget(pencere)
    pencere.metin.setPlainText("101 Uydurma Öğrenci Bir 9/A\n201, 999")
    pencere.tur.setCurrentIndex(1)                            # devamsızlık tebligatı
    pencere.onizle()
    assert [(s["no"], s["durum"]) for s in pencere.satirlar] == [
        ("101", "bulundu"), ("201", "bulundu"), ("999", "bulunamadi")]
    assert pencere.uygula_dugmesi.isEnabled()
    pencere.uygula()
    assert pencere.degisen == 2
    guncel = {s["okul_no"]: s for s in hizmet.basvuru_tablosu(uygulama.vt, "P1")}
    assert guncel["101"]["devamsizlik_tebligati_mi"] and guncel["201"]["devamsizlik_tebligati_mi"]
    assert not guncel["102"]["bayrakli_mi"]


def test_basvuru_karari_kaydedilir_ve_sonrakine_gecilir(uygulama) -> None:
    for no in ("101", "102"):
        hizmet.ogrenci_bayrak_guncelle(uygulama.vt, _ogrenci_id(uygulama.vt, no), True, False)
    hizmet.duyuru_kaydet(uygulama.vt, "P1", date(2026, 8, 28), date(2026, 9, 7),
                         "Duyuru 2026/1", "Okul web sayfası")
    sayfa = basvuru_sayfasi(uygulama)
    assert not sayfa.duyuru_yok_seridi.isVisibleTo(sayfa)
    sira = [s["ogrenci_id"] for s in sayfa.karar_tablosu.gorunen_satirlar()]
    assert len(sira) == 2
    sayfa.karar_tablosu.sec(sira[0])
    sayfa.basvuru_tarihi.ayarla(date(2026, 9, 3))
    sayfa.dilekce.setText("Dilekçe 2026/5")
    sayfa.karari_kaydet(sonrakine=True)
    guncel = {s["ogrenci_id"]: s for s in hizmet.basvuru_tablosu(uygulama.vt, "P1")}
    assert guncel[sira[0]]["basvuru_durumu"] == "basvurdu"
    assert sayfa.karar_tablosu.secili_satir()["ogrenci_id"] == sira[1]


def test_gec_basvuruda_onay_alani_acilir(uygulama) -> None:
    hizmet.ogrenci_bayrak_guncelle(uygulama.vt, _ogrenci_id(uygulama.vt, "101"), True, False)
    hizmet.duyuru_kaydet(uygulama.vt, "P1", date(2026, 8, 28), date(2026, 9, 7),
                         "Duyuru 2026/1", "Okul web sayfası")
    sayfa = basvuru_sayfasi(uygulama)
    sayfa.karar_tablosu.sec(_ogrenci_id(uygulama.vt, "101"))
    sayfa.basvuru_tarihi.ayarla(date(2026, 9, 5))
    assert not sayfa.gec_onay.isEnabled()
    sayfa.basvuru_tarihi.ayarla(date(2026, 9, 8))             # son günden sonra
    assert sayfa.gec_onay.isEnabled() and "müdür onayına" in sayfa.gec_ipucu.text()


# ================================================================ güncelleme

GUNCEL_DURUM = {"calisan_surum": "0.8.0", "son_surum": "0.9.0", "guncelleme_var": True,
                "yayim_adi": "Sorumluluk Sınavı 0.9.0", "yayim_zamani": "", "sayfa_adresi": "",
                "platform": "windows", "indirilebilir": True,
                "kurulum_adi": "SorumlulukSinavi-Kurulum-0.9.0.exe", "kurulum_boyutu": 16_000_000}


def test_guncelleme_seridi_gosterilir_ve_ertelenir(uygulama) -> None:
    uygulama.guncelleme_durumu_geldi(dict(GUNCEL_DURUM))
    assert uygulama.guncelleme_seridi.isVisibleTo(uygulama)
    assert "0.9.0 hazır" in uygulama.guncelleme_seridi.metin.text()
    uygulama._guncellemeyi_ertele()
    assert not uygulama.guncelleme_seridi.isVisibleTo(uygulama)
    uygulama.guncelleme_durumu_geldi(dict(GUNCEL_DURUM))     # aynı sürüm yeniden önerilmez
    assert not uygulama.guncelleme_seridi.isVisibleTo(uygulama)


def test_guncel_programda_serit_cikmaz(uygulama) -> None:
    """Olumsuz senaryo: yeni sürüm yoksa şerit görünmez."""
    uygulama.guncelleme_durumu_geldi({**GUNCEL_DURUM, "guncelleme_var": False,
                                      "son_surum": "0.8.0"})
    assert not uygulama.guncelleme_seridi.isVisibleTo(uygulama)


def test_hakkinda_paneli_platforma_gore_yol_gosterir(uygulama) -> None:
    uygulama.sayfa_goster(sayfa_sirasi("Hakkında"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Hakkında")]
    sayfa.durumu_goster(dict(GUNCEL_DURUM))
    assert sayfa.indir_dugmesi.isVisibleTo(sayfa) and not sayfa.baslat_dugmesi.isVisibleTo(sayfa)
    sayfa.durumu_goster({**GUNCEL_DURUM, "platform": "linux", "indirilebilir": False})
    assert not sayfa.indir_dugmesi.isVisibleTo(sayfa)
    assert sayfa.sayfa_dugmesi.isVisibleTo(sayfa) and ".deb" in sayfa.sonuc.metin.text()


def test_acilis_denetimi_kapatilabilir(uygulama, monkeypatch) -> None:
    from arayuz.uygulama import acilis_denetimi_acik_mi
    monkeypatch.setenv("SORUMLULUK_GUNCELLEME_DENETIMI", "1")
    uygulama.ayarlar.setValue("guncelleme/acilista_denetle", True)
    assert acilis_denetimi_acik_mi(uygulama.ayarlar)
    uygulama.ayarlar.setValue("guncelleme/acilista_denetle", False)
    assert not acilis_denetimi_acik_mi(uygulama.ayarlar)
    monkeypatch.setenv("SORUMLULUK_GUNCELLEME_DENETIMI", "0")
    uygulama.ayarlar.setValue("guncelleme/acilista_denetle", True)
    assert not acilis_denetimi_acik_mi(uygulama.ayarlar)


def test_hakkinda_secenegi_tercihi_yazar(uygulama, monkeypatch) -> None:
    from veri import guncelleme
    # Ortam "1" iken açılış zamanlayıcısı ağa çıkmasın.
    monkeypatch.setattr(guncelleme, "guncelleme_durumu", lambda **_: dict(GUNCEL_DURUM))
    monkeypatch.setenv("SORUMLULUK_GUNCELLEME_DENETIMI", "1")
    uygulama.ayarlar.setValue("guncelleme/acilista_denetle", True)
    uygulama.sayfa_goster(sayfa_sirasi("Hakkında"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Hakkında")]
    assert sayfa.acilista.isChecked() and sayfa.acilista.isEnabled()
    sayfa.acilista.setChecked(False)
    assert uygulama.ayarlar.value("guncelleme/acilista_denetle", type=bool) is False


def test_kurum_kapattiysa_secenek_kapali_gorunur(uygulama) -> None:
    """Olumsuz senaryo: ortam değişkeni denetimi kapatmışsa kutu işaretli
    görünmez, değiştirilemez; kullanıcının kendi tercihi de bozulmaz."""
    uygulama.ayarlar.setValue("guncelleme/acilista_denetle", True)
    uygulama.sayfa_goster(sayfa_sirasi("Hakkında"))      # conftest: denetim kapalı
    sayfa = uygulama.sayfalar[sayfa_sirasi("Hakkında")]
    assert not sayfa.acilista.isChecked() and not sayfa.acilista.isEnabled()
    assert uygulama.ayarlar.value("guncelleme/acilista_denetle", type=bool) is True


def test_indirme_ilerlemesi_boyutla_gosterilir(uygulama) -> None:
    """0.8.2'ye kadar indirme sürerken yalnız dönen bir çubuk vardı; 24 MB okul
    ağında dakikalar sürebilir. Olumsuz senaryo: boyut bilinmiyorsa çubuk belirsiz
    kalır ve sonraki iş yine belirsiz çubukla başlar."""
    uygulama.sayfa_goster(sayfa_sirasi("Hakkında"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Hakkında")]
    cubuk = uygulama.mesgul.cubuk
    uygulama.mesgul_ac("Kurulum dosyası indiriliyor ve doğrulanıyor…")
    assert cubuk.maximum() == 0
    sayfa._indirme_ilerlemesi(6 * 1024 * 1024, 24 * 1024 * 1024)
    assert "6,0 MB / 24,0 MB" in uygulama.mesgul.metin.text()
    assert cubuk.value() * 4 == cubuk.maximum() > 0
    sayfa._indirme_ilerlemesi(24 * 1024 * 1024, 24 * 1024 * 1024)
    assert "doğrulanıyor" in uygulama.mesgul.metin.text() and cubuk.value() == cubuk.maximum()
    sayfa._indirme_ilerlemesi(5 * 1024 * 1024, 0)
    assert cubuk.maximum() == 0 and uygulama.mesgul.metin.text().endswith("5,0 MB")
    sayfa._indirme_ilerlemesi(6 * 1024 * 1024, 24 * 1024 * 1024)
    uygulama.mesgul_ac("Plan üretiliyor…")
    assert cubuk.maximum() == 0


def test_indirme_ilerlemesi_is_parcacigindan_ortuye_ulasir(uygulama, qtbot, monkeypatch,
                                                           tmp_path) -> None:
    """İlerleme indirmeyi yapan iş parçacığından gelir; Qt sinyali ana iş
    parçacığına sıraya koyar ve indirme bitmeden önce teslim eder."""
    from veri import guncelleme
    indirilen = tmp_path / "SorumlulukSinavi-Kurulum-0.9.0.exe"
    indirilen.write_bytes(b"x")

    def sahte_indir(*, ilerleme=None, **_k):
        ilerleme(1024 * 1024, 2 * 1024 * 1024)
        return indirilen

    monkeypatch.setattr(guncelleme, "son_kurulumu_indir", sahte_indir)
    uygulama.sayfa_goster(sayfa_sirasi("Hakkında"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Hakkında")]
    sayfa.durumu_goster(dict(GUNCEL_DURUM))
    sayfa.indir()
    qtbot.waitUntil(lambda: sayfa.indirilen == indirilen, timeout=10_000)
    assert "1,0 MB / 2,0 MB" in uygulama.mesgul.metin.text()
    assert not uygulama.mesgul.isVisible() and sayfa.baslat_dugmesi.isVisibleTo(sayfa)


def test_acilista_eski_kurulum_dosyalari_silinir(qtbot, tmp_path, monkeypatch) -> None:
    """Kurulumdan sonra indirilen dosya önbellekte kalıyordu. Temizlik ağa çıkmaz;
    açılış denetimi kapalıyken de (conftest) yapılır. Olumsuz senaryo: kurulu
    sürümden yeni kurulum dosyası silinmez."""
    from cekirdek.surum import SURUM
    klasor = tmp_path / "guncelleme"
    klasor.mkdir()
    kurulan = klasor / f"SorumlulukSinavi-Kurulum-{SURUM}.exe"
    yenisi = klasor / "SorumlulukSinavi-Kurulum-99.0.0.exe"
    for yol in (kurulan, yenisi):
        yol.write_bytes(b"x")
    monkeypatch.setenv("SORUMLULUK_VERI_KLASORU", str(tmp_path / "veri"))
    monkeypatch.setenv("SORUMLULUK_GUNCELLEME_KLASORU", str(klasor))
    pencere = Uygulama()
    pencere.ileti = KayitliIleti()
    qtbot.addWidget(pencere)
    qtbot.waitUntil(lambda: not kurulan.exists(), timeout=10_000)
    assert yenisi.exists()


# ================================================================== bileşen

def test_tablo_turkce_siralar_ve_harf_duyarsiz_arar(qtbot) -> None:
    from arayuz.bilesenler import Sutun, Tablo
    tablo = Tablo([Sutun("Ad", lambda s: s, 200)], anahtar=lambda s: s,
                  siralama=(0, Qt.SortOrder.AscendingOrder))
    qtbot.addWidget(tablo)
    tablo.yukle(["Zeynep", "Çiğdem", "İlker", "Irmak", "Ömer", "Cem"])
    assert tablo.gorunen_satirlar() == ["Cem", "Çiğdem", "Irmak", "İlker", "Ömer", "Zeynep"]
    tablo.suzgec.aramayi_ayarla("cigdem")
    assert tablo.gorunen_satirlar() == ["Çiğdem"]
    tablo.suzgec.aramayi_ayarla("xyz")
    assert tablo.gorunen_satirlar() == [] and tablo.bos.isVisibleTo(tablo)


def test_tablo_yeniden_yuklemede_secimi_korur(qtbot) -> None:
    from arayuz.bilesenler import Sutun, Tablo
    tablo = Tablo([Sutun("Ad", lambda s: s["ad"], 200)], anahtar=lambda s: s["no"],
                  coklu_secim=True)
    qtbot.addWidget(tablo)
    tablo.yukle([{"no": i, "ad": f"Öğrenci {i}"} for i in range(5)])
    _satir_sec(tablo, {1, 3})
    tablo.yukle([{"no": i, "ad": f"Öğrenci {i} (güncel)"} for i in range(5)])
    assert [s["no"] for s in tablo.secili_satirlar()] == [1, 3]


def test_tablo_dar_alanda_sutunlari_daraltir_genis_alanda_geri_acar(qtbot) -> None:
    """%150 ölçekte ve 1366×768'de son sütunlar ancak yatay kaydırmayla
    görünüyordu: sabit sütunlar artık orantılı daralır."""
    from arayuz.bilesenler import SUTUN_EN_DAR, UZAYAN_EN_AZ, Sutun, Tablo
    tablo = Tablo([Sutun("A", lambda s: s, 200), Sutun("B", lambda s: s, 200),
                   Sutun("C", lambda s: s, 200), Sutun("D", lambda s: s, uzat=True)])
    qtbot.addWidget(tablo)
    tablo.yukle(["x"])
    tablo.show()
    tablo.resize(500, 300)
    qtbot.waitUntil(lambda: tablo.gorunum.columnWidth(0) < 200)
    genislik = tablo.gorunum.viewport().width()
    sabit = sum(tablo.gorunum.columnWidth(i) for i in range(3))
    assert sabit + UZAYAN_EN_AZ <= genislik + 3
    assert min(tablo.gorunum.columnWidth(i) for i in range(3)) >= SUTUN_EN_DAR
    tablo.resize(1400, 300)
    qtbot.waitUntil(lambda: tablo.gorunum.columnWidth(0) == 200)
    assert [tablo.gorunum.columnWidth(i) for i in range(3)] == [200, 200, 200]


def test_tablo_elle_boyutlandirilan_sutuna_dokunmaz(qtbot) -> None:
    """Olumsuz senaryo: kullanıcı sütunu elle ayarladıysa pencere değişince geri alınmaz."""
    from arayuz.bilesenler import Sutun, Tablo
    tablo = Tablo([Sutun("A", lambda s: s, 200), Sutun("B", lambda s: s, uzat=True)])
    qtbot.addWidget(tablo)
    tablo.show()
    tablo.resize(900, 300)
    qtbot.wait(20)
    tablo.gorunum.horizontalHeader().resizeSection(0, 320)
    tablo.resize(400, 300)
    qtbot.wait(20)
    assert tablo.gorunum.columnWidth(0) == 320


def test_takvim_hucresi_kisa_ekranda_kartlari_sikistirmaz(qtbot) -> None:
    """Hücreye sabit 64 piksellik taban konunca kısa ekranda iki kart üst üste
    biniyordu; takvim artık sıkışmak yerine kayar."""
    from arayuz.takvim import HUCRE_EN_AZ, SurukleBirakTakvim
    gun, saat = date(2026, 9, 14), time(8, 0)
    kartlar = [{"anahtar": f"k{i}", "baslik": f"Ders {i}", "alt": "5 öğrenci • 1 salon",
                "tarih": gun, "saat": saat, "tur": "yazili", "kilitli": False}
               for i in range(3)]
    takvim = SurukleBirakTakvim([gun], [saat, time(9, 0), time(10, 0)], kartlar,
                                lambda *a: None)
    qtbot.addWidget(takvim)
    takvim.show()
    takvim.resize(400, 200)
    qtbot.wait(20)
    for kart in takvim.kart_widgetlari.values():
        assert kart.height() >= kart.minimumSizeHint().height()
    assert takvim.verticalScrollBar().maximum() > 0
    # Olumsuz senaryo: boş hücre bırakma hedefi olacak kadar yüksek kalır.
    assert takvim.hucre(gun, time(10, 0)).height() >= HUCRE_EN_AZ


def test_plan_yan_paneli_kisa_ekranda_metni_kirpmaz(uygulama, qtbot) -> None:
    """%150 ölçekte (1280×680) seçili sınavın görevli listesi kırpılıyordu."""
    sayfa = plan_uret(uygulama, qtbot)
    # Ekransız ekran küçük olduğundan pencere büyütülmüş açılır; boyut
    # ancak normal pencerede ayarlanır.
    uygulama.showNormal()
    uygulama.resize(1280, 680)
    sayfa.takvim.secildi(sayfa.plan_sonucu.plan.oturumlar[0].anahtar)
    qtbot.wait(50)
    etiket = sayfa.secim_etiketi
    assert etiket.height() >= etiket.heightForWidth(etiket.width())


# ============================================================ evrak ve teslim

def _evrak_sayfasi(uyg, qtbot):
    plan = plan_uret(uyg, qtbot)
    plan.plan_kaydet()
    uyg.sayfa_goster(sayfa_sirasi("Evrak ve Teslim"))
    return uyg.sayfalar[sayfa_sirasi("Evrak ve Teslim")]


def _bildirimleri_kaydet(uyg, monkeypatch) -> list[str]:
    bildirimler: list[str] = []
    monkeypatch.setattr(uyg, "bildir", lambda metin, *a, **k: bildirimler.append(metin))
    return bildirimler


def test_evrak_uretimi_secilen_klasore_yazar(uygulama, qtbot, tmp_path, monkeypatch) -> None:
    evrak = _evrak_sayfasi(uygulama, qtbot)
    hedef = tmp_path / "evrak"
    hedef.mkdir()
    monkeypatch.setattr("arayuz.sayfalar.evrak.QFileDialog.getExistingDirectory",
                        lambda *a, **k: str(hedef))
    evrak._hepsi(True)
    evrak.uret()
    qtbot.waitUntil(lambda: evrak.sonuc_tablosu.model.rowCount() > 0, timeout=PLAN_ZAMAN_ASIMI_MS)
    assert len(list(hedef.glob("*.docx"))) == evrak.sonuc_tablosu.model.rowCount()
    assert evrak.klasor_dugmesi.isEnabled() and not uygulama.mesgul.isVisible()


def test_evrak_uretimi_secim_yoksa_uyarir(uygulama, qtbot, monkeypatch) -> None:
    """Olumsuz senaryo: belge seçilmeden klasör sorulmaz."""
    evrak = _evrak_sayfasi(uygulama, qtbot)
    sorulan = []
    monkeypatch.setattr("arayuz.sayfalar.evrak.QFileDialog.getExistingDirectory",
                        lambda *a, **k: sorulan.append(1) or "")
    evrak._hepsi(False)
    evrak.uret()
    assert not sorulan and uygulama.ileti.turden("uyari")


def test_teslim_cizelgesinde_toplu_teslim_ve_geri_alma(uygulama, qtbot, monkeypatch) -> None:
    evrak = _evrak_sayfasi(uygulama, qtbot)
    evrak.sekmeler.setCurrentIndex(1)
    bildirimler = _bildirimleri_kaydet(uygulama, monkeypatch)
    satirlar = evrak.teslim_tablosu.gorunen_satirlar()[:2]
    anahtarlar = {(s.oturum_id, s.evrak_turu) for s in satirlar}
    _satir_sec(evrak.teslim_tablosu, anahtarlar)
    evrak.teslim_eden.setCurrentIndex(1)
    evrak.teslim_alan.setCurrentIndex(2)
    evrak.teslim_al()
    durum = {(s.oturum_id, s.evrak_turu): s.teslim_edildi_mi
             for s in hizmet.teslim_cizelgesi(uygulama.vt, evrak.plan_id)}
    assert all(durum[a] for a in anahtarlar) and bildirimler == ["2 evrak teslim alındı."]
    _satir_sec(evrak.teslim_tablosu, anahtarlar)
    evrak.teslimi_geri_al()
    durum = {(s.oturum_id, s.evrak_turu): s.teslim_edildi_mi
             for s in hizmet.teslim_cizelgesi(uygulama.vt, evrak.plan_id)}
    assert not any(durum[a] for a in anahtarlar)


def test_teslimde_ayni_kisi_hata_verir_basari_bildirmez(uygulama, qtbot, monkeypatch) -> None:
    """Olumsuz senaryo (TS-03): hata gösterilip yine de "teslim alındı" deniyordu."""
    evrak = _evrak_sayfasi(uygulama, qtbot)
    bildirimler = _bildirimleri_kaydet(uygulama, monkeypatch)
    satir = evrak.teslim_tablosu.gorunen_satirlar()[0]
    _satir_sec(evrak.teslim_tablosu, {(satir.oturum_id, satir.evrak_turu)})
    evrak.teslim_eden.setCurrentIndex(1)
    evrak.teslim_alan.setCurrentIndex(1)
    evrak.teslim_al()
    assert any("TS-03" in m for m in uygulama.ileti.turden("hata")) and bildirimler == []
    assert not any(s.teslim_edildi_mi for s in hizmet.teslim_cizelgesi(uygulama.vt, evrak.plan_id))


def test_toplu_basvurmadi_kismen_kaydedilince_kac_kayit_islendigini_soyler(
        uygulama, monkeypatch) -> None:
    for no in ("101", "102"):
        hizmet.ogrenci_bayrak_guncelle(uygulama.vt, _ogrenci_id(uygulama.vt, no), True, False)
    hizmet.duyuru_kaydet(uygulama.vt, "P1", date(2026, 8, 28), date(2026, 9, 7),
                         "Duyuru 2026/1", "Okul web sayfası")
    sayfa = basvuru_sayfasi(uygulama)
    bildirimler = _bildirimleri_kaydet(uygulama, monkeypatch)
    _satir_sec(sayfa.karar_tablosu, {s["ogrenci_id"] for s in sayfa.karar_tablosu.gorunen_satirlar()})
    asil = hizmet.basvuru_kaydet
    cagri = []

    def ikincide_bozul(*a, **k):
        cagri.append(1)
        if len(cagri) == 2:
            raise hizmet.HizmetHatasi("Uydurma hata.")
        return asil(*a, **k)

    monkeypatch.setattr(hizmet, "basvuru_kaydet", ikincide_bozul)
    sayfa.secilenleri_basvurmadi_say()
    hatalar = uygulama.ileti.turden("hata")
    assert hatalar and "1 öğrenci başvurmadı olarak kaydedildi; kalanlar işlenmedi" in hatalar[-1]
    assert bildirimler == []


def test_personel_silinemeyince_ad_gunluge_yazilmaz(uygulama, monkeypatch, caplog) -> None:
    """KVKK: günlük sorun bildiriminde geliştiriciye gönderilir ve kişisel veri
    içermediği söylenir. "… silinemedi" başlığına konan öğretmen adı günlüğe
    giriyordu. Ad ekrandaki iletide kalır; günlükte başlık ve hata türü durur."""
    import logging
    uygulama.sayfa_goster(sayfa_sirasi("Öğretmen Listesi"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Öğretmen Listesi")]
    kisi = sayfa.tablo.gorunen_satirlar()[0]
    sayfa.tablo.sec(kisi["kimlik"])

    def bozul(*a, **k):
        raise hizmet.HizmetHatasi("Uydurma engel.")

    monkeypatch.setattr(hizmet, "personel_sil", bozul)
    with caplog.at_level(logging.WARNING):
        sayfa.sil()
    assert "Personel silinemedi: HizmetHatasi" in caplog.text
    assert kisi["ad"] not in caplog.text
    assert any(m.startswith(f"{kisi['ad']}: ") for m in uygulama.ileti.turden("hata"))


def test_personel_durumu_degismezse_basari_bildirmez(uygulama, monkeypatch) -> None:
    uygulama.sayfa_goster(sayfa_sirasi("Öğretmen Listesi"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Öğretmen Listesi")]
    bildirimler = _bildirimleri_kaydet(uygulama, monkeypatch)
    sayfa.tablo.sec(sayfa.tablo.gorunen_satirlar()[0]["kimlik"])

    def bozul(*a, **k):
        raise hizmet.HizmetHatasi("Uydurma hata.")

    monkeypatch.setattr(hizmet, "personel_durumu_degistir", bozul)
    sayfa.durum_degistir()
    assert uygulama.ileti.turden("hata") and bildirimler == []


def test_guncelleme_paneli_teknik_terim_kullanmaz(uygulama) -> None:
    """Kardeş projelerle aynı dil (karar 0015): panelin hiçbir durumunda GitHub,
    Release, kurucu ya da SHA-256 geçmez. Ağ engeli ipucunda "GitHub'a erişim"
    yazıyordu."""
    import re
    from veri import guncelleme
    uygulama.sayfa_goster(sayfa_sirasi("Hakkında"))
    sayfa = uygulama.sayfalar[sayfa_sirasi("Hakkında")]
    yasak = re.compile(r"GitHub|Release|kurucu|SHA-256", re.IGNORECASE)
    metinler = []
    for durum in (dict(GUNCEL_DURUM),
                  {**GUNCEL_DURUM, "platform": "linux", "indirilebilir": False},
                  {**GUNCEL_DURUM, "guncelleme_var": False, "son_surum": "0.8.0"},
                  {**GUNCEL_DURUM, "indirilebilir": False}):
        sayfa.durumu_goster(durum)
        metinler.append(sayfa.sonuc.metin.text())
    sayfa._denetlenemedi(guncelleme.GuncellemeHatasi("Güncelleme sunucusuna ulaşılamadı."))
    metinler.append(sayfa.sonuc.metin.text())
    sayfa._indirilemedi(guncelleme.GuncellemeHatasi("Güncelleme dosyası doğrulanamadı."))
    metinler.append(sayfa.sonuc.metin.text())
    uygulama.guncelleme_durumu_geldi(dict(GUNCEL_DURUM))
    metinler.append(uygulama.guncelleme_seridi.metin.text())
    bulunan = [m for m in metinler if yasak.search(m)]
    assert not bulunan, bulunan


def test_plan_yan_paneli_yalniz_sigmayinca_kayar(uygulama, qtbot) -> None:
    """0.8.1'de kural tablosunun tercih boyu (192 piksel) yüzünden içerik sığarken
    de kaydırma çubuğu çıkıyordu: 1440×900'de dokuz satırlık seçimle eski kod ~19
    piksel kaydırıyor (sekiz satırdan başlayarak), yenisi ~40 piksel boş bırakıyor
    (on iki satırdan önce kaymaz). Olumsuz senaryo: sığmayınca kayar ve kural
    tablosu en küçük boyunun altına inmez. Seçim metni sabit uzunlukta verilir ki
    sonuç veriye bağlı olmasın."""
    from arayuz.sayfalar.plan import KURAL_TABLOSU_EN_AZ
    sayfa = plan_sayfasi(uygulama)
    # Ekransız ekran küçük olduğundan pencere büyütülmüş açılır; boyut
    # ancak normal pencerede ayarlanır.
    uygulama.showNormal()
    uygulama.resize(1440, 900)
    sayfa.secim_etiketi.setText("\n".join(f"satır {i}" for i in range(9)))
    qtbot.wait(50)
    assert sayfa.yan_alan.verticalScrollBar().maximum() == 0
    uygulama.resize(1280, 620)
    qtbot.wait(50)
    assert sayfa.yan_alan.verticalScrollBar().maximum() > 0
    assert sayfa.ihlal_tablosu.height() >= KURAL_TABLOSU_EN_AZ
