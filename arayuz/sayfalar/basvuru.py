"""05 Başvuru kapısı — OKY md.58/2-d.

Okuldan mezun olamayan 12. sınıf öğrencileri ile devamsızlık tebligatı yapılan
öğrenciler plana ancak yazılı başvuruyla girer. Akış üç adımdır ve sayfa da
üç sekmedir: işaretler (yıl boyu geçerli), duyuru (dönemlik), başvuru kararları
(dönemlik).

Tk sürümünde işaretleme çok zordu: yüzlerce satırlık aranamayan listede
öğrenci bulunuyor, seçiliyor, kutu işaretleniyor, "kaydet"e basılıyor ve
sayfa baştan çizildiği için kaydırma ve seçim kayboluyordu. Burada kutucuğa
tıklamak hemen kaydeder (bildirimden geri alınır), arama ve süzgeçler vardır,
birden çok öğrenci topluca ya da numara listesiyle işaretlenir.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QRadioButton, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from arayuz.bilesenler import (
    secim_kutusu,
    AramaKutusu, Kart, Serit, Sutun, Tablo, TarihAlani, cip, dugme, etiket, yatay,
)
from arayuz.palet import RENK
from arayuz.pencereler import NumaraListesiPenceresi
from arayuz.sayfalar.temel import Sayfa, kismi_ileti
from cekirdek.takvim import is_gunu_ekle, pencere_adi, tarih_yaz
from veri import hizmet
from veri.hizmet import HizmetHatasi

PENCERE_KODLARI = ("P1", "P2", "P3")
ISARET_ALANLARI = ("mezun_olamayan", "devamsizlik_tebligati")
ISARET_ADLARI = {"mezun_olamayan": "beklemeli (mezun olamayan 12. sınıf)",
                 "devamsizlik_tebligati": "devamsızlık tebligatı"}


def _isaret_sirasi(satir: dict) -> tuple:
    """İşaretliler önde, sonra sınıf, şube ve Türk alfabesiyle ad."""
    return (not satir["bayrakli_mi"], satir["sinif"] or 99, satir["sube"], satir["ad_soyad"])


def _ozet_zemini(satir: dict) -> str | None:
    if not satir["bayrakli_mi"]:
        return None
    if satir["eski_isaret_mi"]:
        return RENK["uyari_zemin"]
    if satir["ozet"] == "KARAR BEKLİYOR":
        return RENK["uyari_zemin"]
    if satir["ozet"].startswith("Başvurmadı"):
        return RENK["engel_zemin"]
    return RENK["basari_zemin"]


class BasvuruSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.kod = ""
        self.satirlar: list[dict] = []
        self.duyuru: dict | None = None

        ust = Kart()
        self.donem = secim_kutusu()
        self.donem.addItems([pencere_adi(k) for k in PENCERE_KODLARI])
        self.donem.currentIndexChanged.connect(lambda _i: self._donem_degisti())
        self.cipler = QHBoxLayout()
        self.cipler.setSpacing(6)
        ust.ekle(yatay(QLabel("Dönem"), self.donem, 0))
        ust.ekle(self.cipler)
        self.eski_seridi = Serit("", "uyari")
        self.eski_seridi.dugme_ekle("Bu öğrencileri göster", self._eskileri_goster)
        self.eski_seridi.hide()
        ust.ekle(self.eski_seridi)
        self.duzen.addWidget(ust)

        self.sekmeler = QTabWidget()
        self.sekmeler.addTab(self._isaret_sekmesi(), "1. Beklemeli ve devamsız işaretleri")
        self.sekmeler.addTab(self._duyuru_sekmesi(), "2. Duyuru")
        self.sekmeler.addTab(self._karar_sekmesi(), "3. Başvuru kararları")
        self.duzen.addWidget(self.sekmeler, 1)

    # =============================================================== işaretler
    def _isaret_sekmesi(self) -> QWidget:
        kart = Kart(kenar=(16, 14, 16, 12))
        kart.ekle(etiket(
            "Okuldan mezun olamayan 12. sınıf öğrencileri ile devamsızlık tebligatı yapıldığı "
            "hâlde okula ya da sınavlara katılımları sağlanamayan öğrenciler plana ancak yazılı "
            "başvuruyla girer (OKY md.58/2-d). e-Okul raporu bu ayrımı taşımaz; işaret burada "
            "konur ve öğretim yılı boyunca geçerlidir. Kutucuğa tıklamak hemen kaydeder.",
            "Soluk", sar=True))
        self.arama_kutusu = AramaKutusu("Numara, ad ya da şube ara…")
        self.sube_suzgeci = secim_kutusu()
        self.yalniz_12 = QCheckBox("Yalnız 12. sınıflar")
        self.yalniz_isaretli = QCheckBox("Yalnız işaretliler")
        self.yalniz_eski = QCheckBox("Önceki yıldan kalan işaretler")
        self.isaret_sayaci = etiket("", "Soluk")
        for kutu in (self.yalniz_12, self.yalniz_isaretli, self.yalniz_eski):
            kutu.toggled.connect(lambda _d: self._isaret_suzgeci())
        self.sube_suzgeci.currentIndexChanged.connect(lambda _i: self._isaret_suzgeci())
        kart.ekle(yatay(self.arama_kutusu, self.sube_suzgeci, self.yalniz_12, self.yalniz_isaretli,
                        self.yalniz_eski, 0, self.isaret_sayaci))

        self.tablo = Tablo(
            [Sutun("Beklemeli", lambda s: "", 96, onay=lambda s: s["mezun_olamayan_mi"],
                   ipucu=lambda s: "Mezun olamayan 12. sınıf öğrencisi (OKY md.58/2-d)"),
             Sutun("Devamsız", lambda s: "", 92, onay=lambda s: s["devamsizlik_tebligati_mi"],
                   ipucu=lambda s: "Devamsızlık tebligatı yapıldı (OKY md.58/2-d)"),
             Sutun("Okul no", lambda s: s["okul_no"], 90),
             Sutun("Adı Soyadı", lambda s: s["ad_soyad"], 230),
             Sutun("Şube", lambda s: s["sube"], 80, siralama=_isaret_sirasi),
             Sutun("Ders", lambda s: s["ders_sayisi"], 60, "sag",
                   ipucu=lambda s: "Aktif sorumluluk kaydı sayısı"),
             Sutun("İşaret yılı", lambda s: s["isaret_yili"] if s["bayrakli_mi"] else "", 110),
             Sutun("Bu dönem başvuru", lambda s: s["ozet"], uzat=True)],
            anahtar=lambda s: s["ogrenci_id"], coklu_secim=True, zemin=_ozet_zemini,
            kalin=lambda s: s["bayrakli_mi"], siralama=(4, Qt.SortOrder.AscendingOrder),
            bos_metin="Aktif sorumluluk kaydı olan öğrenci yok. Önce e-Okul sorumluluk raporunu "
                      "içe aktarın.")
        self.tablo.aramaya_bagla(self.arama_kutusu)
        self.tablo.onay_degisti.connect(self._isaret_degisti)
        self.tablo.suzgec.layoutChanged.connect(self._isaret_sayacini_tazele)
        self.tablo.suzgec.modelReset.connect(self._isaret_sayacini_tazele)
        self.tablo.suzgec.rowsInserted.connect(self._isaret_sayacini_tazele)
        self.tablo.suzgec.rowsRemoved.connect(self._isaret_sayacini_tazele)
        kart.ekle(self.tablo, 1)
        kart.ekle(yatay(
            etiket("Seçilenler:", "Soluk"),
            dugme("Beklemeli işaretle", "", "onay",
                  tiklaninca=lambda: self.toplu_isaretle("mezun_olamayan", True)),
            dugme("Devamsız işaretle", "", "onay",
                  tiklaninca=lambda: self.toplu_isaretle("devamsizlik_tebligati", True)),
            dugme("İşaretleri kaldır", "", "kapat", tiklaninca=self.toplu_isaret_kaldir),
            0, dugme("Numara listesiyle işaretle…", "", "liste", tiklaninca=self.numara_listesi)))
        return kart

    def _isaret_suzgeci(self) -> None:
        sube = self.sube_suzgeci.currentText() if self.sube_suzgeci.currentIndex() > 0 else ""
        yalniz_12 = self.yalniz_12.isChecked()
        yalniz_isaretli = self.yalniz_isaretli.isChecked()
        yalniz_eski = self.yalniz_eski.isChecked()

        def kosul(s: dict) -> bool:
            return ((not sube or s["sube"] == sube)
                    and (not yalniz_12 or s["sinif"] == 12)
                    and (not yalniz_isaretli or s["bayrakli_mi"])
                    and (not yalniz_eski or s["eski_isaret_mi"]))

        self.tablo.kosulu_ayarla(kosul)
        self._isaret_sayacini_tazele()

    def _isaret_sayacini_tazele(self, *_) -> None:
        gorunen, toplam = self.tablo.suzgec.rowCount(), self.tablo.model.rowCount()
        self.isaret_sayaci.setText(f"{gorunen} / {toplam} öğrenci" if gorunen != toplam
                                   else f"{toplam} öğrenci")

    def _isaret_degisti(self, satir: dict, sutun: int, deger: bool) -> None:
        alan = ISARET_ALANLARI[sutun]
        self._isaretleri_uygula([satir], {alan: deger},
                                f"{satir['okul_no']} {satir['ad_soyad']}: {ISARET_ADLARI[alan]} "
                                + ("işaretlendi." if deger else "işareti kaldırıldı."))

    def _isaretleri_uygula(self, satirlar: list[dict], degerler: dict[str, bool],
                           bildirim: str) -> None:
        """İşaretleri yazar; bildirimdeki "Geri al" her öğrencinin eski hâlini geri koyar."""
        onceki = [(s["ogrenci_id"], s["mezun_olamayan_mi"], s["devamsizlik_tebligati_mi"])
                  for s in satirlar]
        try:
            degisen = hizmet.ogrenci_bayraklarini_toplu_guncelle(
                self.vt, [s["ogrenci_id"] for s in satirlar], **degerler)
        except HizmetHatasi as hata:
            self.hata("İşaret kaydedilemedi", hata)
            return
        self.tazele()
        if degisen:
            self.bildir(bildirim, "Geri al", lambda: self._geri_koy(onceki))
        else:
            self.bildir("Değişen işaret yok.")

    def _geri_koy(self, onceki: list[tuple[int, bool, bool]]) -> None:
        donen = 0
        try:
            for kimlik, mezun, devamsiz in onceki:
                hizmet.ogrenci_bayraklarini_toplu_guncelle(
                    self.vt, [kimlik], mezun_olamayan=mezun, devamsizlik_tebligati=devamsiz)
                donen += 1
        except HizmetHatasi as hata:
            self.tazele()
            self.hata("Geri alınamadı", kismi_ileti(hata, donen, "öğrencinin işareti döndü"))
            return
        self.tazele()
        self.bildir("İşaretler eski hâline döndü.")

    def toplu_isaretle(self, alan: str, deger: bool) -> None:
        secili = self.tablo.secili_satirlar()
        if not secili:
            self.ileti.uyari("Seçim yok", "Tablodan öğrenci seçin (Ctrl ya da Shift ile birden "
                                          "çok satır seçilebilir).")
            return
        self._isaretleri_uygula(secili, {alan: deger},
                                f"{len(secili)} öğrenci {ISARET_ADLARI[alan]} olarak işaretlendi.")

    def toplu_isaret_kaldir(self) -> None:
        secili = self.tablo.secili_satirlar()
        if not secili:
            self.ileti.uyari("Seçim yok", "İşareti kaldırılacak öğrencileri seçin.")
            return
        self._isaretleri_uygula(secili, {"mezun_olamayan": False, "devamsizlik_tebligati": False},
                                f"{len(secili)} öğrencinin işareti kaldırıldı.")

    def numara_listesi(self) -> None:
        pencere = NumaraListesiPenceresi(self.uyg)
        if pencere.exec():
            self.tazele()
            self.bildir(f"{pencere.degisen} öğrencinin işareti değişti.")

    def _eskileri_goster(self) -> None:
        self.sekmeler.setCurrentIndex(0)
        self.yalniz_eski.setChecked(True)

    # ================================================================= duyuru
    def _duyuru_sekmesi(self) -> QWidget:
        kap = QWidget()
        duzen = QVBoxLayout(kap)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(14)
        kart = Kart("Başvuru duyurusu",
                    "Duyuru başvuru kapısının dayanağıdır: kaydedilmeden başvuru alınamaz. "
                    "Mevzuattaki tek bağlayıcı süre başvurunun sınav tarihinden en az 5 iş günü "
                    "önce yapılmasıdır (OKY md.58/2-d); son gün buna göre denetlenir.")
        izgara = QGridLayout()
        izgara.setHorizontalSpacing(14)
        izgara.setVerticalSpacing(8)
        self.duyuru_tarihi = TarihAlani()
        self.son_gun = TarihAlani()
        self.belge_referansi = QLineEdit()
        self.belge_referansi.setPlaceholderText("ör. Okul Müdürlüğünün 2026/11 sayılı duyurusu")
        self.yayim_yeri = QLineEdit()
        for satir, (ad, girdi) in enumerate((("Duyuru tarihi", self.duyuru_tarihi),
                                             ("Son başvuru günü", self.son_gun),
                                             ("Belge referansı", self.belge_referansi),
                                             ("Yayım yeri", self.yayim_yeri))):
            izgara.addWidget(QLabel(ad), satir, 0)
            izgara.addWidget(girdi, satir, 1)
        izgara.setColumnStretch(1, 1)
        kart.ekle(izgara)
        self.son_gun_ipucu = etiket("", "Soluk", sar=True)
        kart.ekle(self.son_gun_ipucu)
        kart.ekle(yatay(0, dugme("Duyuruyu kaydet", "ana", "kaydet",
                                 tiklaninca=self.duyuruyu_kaydet)))
        duzen.addWidget(kart)

        belge = Kart("Belgeler",
                     "Duyuru ilanı okul web sayfasında yayımlanır ve kişi adı taşımaz. Plan dışı "
                     "bırakılanlar tutanağı okul içi kayıttır, ilan edilmez.")
        self.belge_ozeti = etiket("", "Soluk")
        belge.ekle(yatay(self.belge_ozeti, 0, dugme("Duyuru ve tutanağı üret…", "", "evrak",
                                                     tiklaninca=self.belgeleri_uret)))
        duzen.addWidget(belge)
        duzen.addStretch(1)
        return kap

    def _duyuruyu_doldur(self) -> None:
        self.duyuru = hizmet.duyuru_getir(self.vt, self.kod)
        try:
            pencere_bas = hizmet.pencereleri_getir(self.vt)[self.kod][0]
            en_gec = is_gunu_ekle(pencere_bas, -hizmet.BASVURU_IS_GUNU,
                                  hizmet.tatilleri_getir(self.vt))
            self.son_gun_ipucu.setText(
                f"{pencere_adi(self.kod)} penceresi {tarih_yaz(pencere_bas)} tarihinde başlıyor; "
                f"son başvuru günü en geç {tarih_yaz(en_gec)} olabilir (5 iş günü).")
        except HizmetHatasi:
            en_gec = None
            self.son_gun_ipucu.setText("Kurum Ayarları'nda dönem tarihleri girilmeden duyuru "
                                       "kaydedilemez.")
        if self.duyuru:
            self.duyuru_tarihi.ayarla(self.duyuru["duyuru_tarihi"])
            self.son_gun.ayarla(self.duyuru["basvuru_son_gunu"])
            self.belge_referansi.setText(self.duyuru["belge_referansi"])
            self.yayim_yeri.setText(self.duyuru["yayim_yeri"])
        else:
            self.duyuru_tarihi.ayarla(date.today())
            self.son_gun.ayarla(en_gec or date.today())
            self.belge_referansi.clear()
            self.yayim_yeri.setText("Okul web sayfası ve okul panosu")
        plan_disi = len(hizmet.plan_disi_birakilanlar(self.vt, self.kod))
        self.belge_ozeti.setText(f"Plan dışı tutanağına girecek öğrenci: {plan_disi}")

    def duyuruyu_kaydet(self) -> None:
        try:
            uyarilar = hizmet.duyuru_kaydet(self.vt, self.kod, self.duyuru_tarihi.tarih(),
                                            self.son_gun.tarih(), self.belge_referansi.text(),
                                            self.yayim_yeri.text())
        except HizmetHatasi as hata:
            self.hata("Duyuru kaydedilemedi", hata)
            return
        self.tazele()
        if uyarilar:
            self.ileti.uyari("Duyuru kaydedildi", "\n\n".join(uyarilar))
        else:
            self.bildir(f"{pencere_adi(self.kod)} duyurusu kaydedildi.")

    def belgeleri_uret(self) -> None:
        from evrak.uretici import pencere_evraki_uret
        son = str(self.uyg.ayarlar.value("evrak/son_klasor", str(Path.home())))
        klasor = QFileDialog.getExistingDirectory(self, "Belgelerin kaydedileceği klasör", son)
        if not klasor:
            return
        try:
            uretilen = pencere_evraki_uret(self.vt, self.kod, Path(klasor))
        except (HizmetHatasi, OSError) as hata:
            self.hata("Belgeler üretilemedi", hata)
            return
        self.uyg.ayarlar.setValue("evrak/son_klasor", klasor)
        self.ileti.bilgi("Belgeler üretildi",
                         "\n".join(str(yol) for yol, _ in uretilen)
                         + "\n\nDuyuru ilan edilmek üzere hazırlanmıştır ve kişi adı taşımaz. "
                           "Tutanak okul içi kayıttır, ilan edilmez.")

    # ======================================================== başvuru kararları
    def _karar_sekmesi(self) -> QWidget:
        kart = Kart(kenar=(16, 14, 16, 12))
        self.duyuru_yok_seridi = Serit(
            "Bu dönem için duyuru kaydedilmedi; başvuru kararı girilemez.", "uyari")
        self.duyuru_yok_seridi.dugme_ekle("Duyuruya git", lambda: self.sekmeler.setCurrentIndex(1))
        kart.ekle(self.duyuru_yok_seridi)
        self.karar_arama = AramaKutusu("Numara ya da ad ara…")
        self.yalniz_bekleyen = QCheckBox("Yalnız karar bekleyenler")
        self.yalniz_bekleyen.toggled.connect(lambda _d: self._karar_suzgeci())
        kart.ekle(yatay(self.karar_arama, self.yalniz_bekleyen, 0))

        self.karar_tablosu = Tablo(
            [Sutun("Okul no", lambda s: s["okul_no"], 80),
             Sutun("Adı Soyadı", lambda s: s["ad_soyad"], 170),
             Sutun("Şube", lambda s: s["sube"], 60),
             Sutun("Grup", lambda s: s["grup"], 180),
             Sutun("Durum", lambda s: s["ozet"], 160),
             Sutun("Tarih", lambda s: tarih_yaz(s["basvuru_tarihi"]) if s["basvuru_tarihi"]
                   else "", 90, siralama=lambda s: s["basvuru_tarihi"]),
             Sutun("Dilekçe", lambda s: s["belge_referansi"], uzat=True)],
            anahtar=lambda s: s["ogrenci_id"], coklu_secim=True, zemin=_ozet_zemini,
            bos_metin="İşaretli öğrenci yok. Başvuru yalnız 1. sekmede işaretlenen öğrenciler "
                      "için gerekir; diğerleri başvurusuz plana girer.")
        self.karar_tablosu.aramaya_bagla(self.karar_arama)
        self.karar_tablosu.secim_degisti.connect(self._karari_forma_al)

        form = Kart("Seçili öğrencinin başvurusu", kenar=(16, 14, 16, 14))
        form.setMinimumWidth(320)
        form.setMaximumWidth(400)
        self.karar_ogrenci = etiket("Tablodan bir öğrenci seçin.", "Bolum", sar=True)
        form.ekle(self.karar_ogrenci)
        self.basvurdu = QRadioButton("Başvurdu")
        self.basvurmadi = QRadioButton("Başvurmadı (plan dışı)")
        grup = QButtonGroup(self)
        grup.addButton(self.basvurdu)
        grup.addButton(self.basvurmadi)
        self.basvurdu.setChecked(True)
        self.basvurdu.toggled.connect(lambda _d: self._form_alanlarini_ayarla())
        form.ekle(yatay(self.basvurdu, self.basvurmadi, 0))
        self.basvuru_tarihi = TarihAlani()
        self.basvuru_tarihi.dateChanged.connect(lambda _t: self._form_alanlarini_ayarla())
        self.dilekce = QLineEdit()
        self.dilekce.setPlaceholderText("Dilekçe tarih/sayı")
        self.gec_onay = QLineEdit()
        self.gec_onay.setPlaceholderText("Müdür onay no")
        alanlar = QGridLayout()
        alanlar.setVerticalSpacing(8)
        for satir, (ad, girdi) in enumerate((("Başvuru tarihi", self.basvuru_tarihi),
                                             ("Dilekçe", self.dilekce),
                                             ("Geç başvuru onayı", self.gec_onay))):
            alanlar.addWidget(QLabel(ad), satir, 0)
            alanlar.addWidget(girdi, satir, 1)
        form.ekle(alanlar)
        self.gec_ipucu = etiket("", "Soluk", sar=True)
        form.ekle(self.gec_ipucu)
        self.kaydet_dugmesi = dugme("Kaydet", "", "kaydet", tiklaninca=self.karari_kaydet)
        self.sonraki_dugmesi = dugme("Kaydet ve sonrakine geç", "ana", "ileri",
                                     "Ctrl+Enter",
                                     lambda: self.karari_kaydet(sonrakine=True))
        form.ekle(yatay(self.kaydet_dugmesi, self.sonraki_dugmesi))
        form.duzen.addStretch(1)

        bolme = QSplitter(Qt.Orientation.Horizontal)
        bolme.addWidget(self.karar_tablosu)
        bolme.addWidget(form)
        bolme.setStretchFactor(0, 1)
        bolme.setChildrenCollapsible(False)
        kart.ekle(bolme, 1)
        kart.ekle(yatay(etiket("Seçilenler:", "Soluk"),
                        dugme("Başvurmadı olarak kaydet", "", "kapat",
                              tiklaninca=self.secilenleri_basvurmadi_say), 0))
        for alan in (self.dilekce, self.gec_onay):
            alan.returnPressed.connect(lambda: self.karari_kaydet(sonrakine=True))
        self._form_alanlarini_ayarla()
        return kart

    def _karar_suzgeci(self) -> None:
        bekleyen = self.yalniz_bekleyen.isChecked()
        self.karar_tablosu.kosulu_ayarla(
            lambda s: s["bayrakli_mi"] and (not bekleyen or s["basvuru_durumu"] is None))

    def _form_alanlarini_ayarla(self) -> None:
        basvurdu = self.basvurdu.isChecked()
        self.basvuru_tarihi.setEnabled(basvurdu)
        self.dilekce.setEnabled(basvurdu)
        gec = bool(basvurdu and self.duyuru and self.basvuru_tarihi.tarih()
                   and self.basvuru_tarihi.tarih() > self.duyuru["basvuru_son_gunu"])
        self.gec_onay.setEnabled(gec)
        self.gec_ipucu.setText(
            f"Son başvuru günü ({tarih_yaz(self.duyuru['basvuru_son_gunu'])}) geçmiş: plana "
            "eklenmesi müdür onayına bağlıdır; 5 iş günü şartı fiilî sınav tarihine göre "
            "denetlenir." if gec else "")

    def _karari_forma_al(self) -> None:
        satir = self.karar_tablosu.secili_satir()
        etkin = satir is not None and self.duyuru is not None
        for oge in (self.basvurdu, self.basvurmadi, self.kaydet_dugmesi, self.sonraki_dugmesi):
            oge.setEnabled(etkin)
        if satir is None:
            self.karar_ogrenci.setText("Tablodan bir öğrenci seçin.")
            return
        self.karar_ogrenci.setText(f"{satir['okul_no']} {satir['ad_soyad']} ({satir['sube']})\n"
                                   f"{satir['grup']}")
        (self.basvurmadi if satir["basvuru_durumu"] == "basvurmadi"
         else self.basvurdu).setChecked(True)
        self.basvuru_tarihi.ayarla(satir["basvuru_tarihi"] or date.today())
        self.dilekce.setText(satir["belge_referansi"])
        self.gec_onay.setText(satir["mudur_onay_no"])
        self._form_alanlarini_ayarla()

    def karari_kaydet(self, sonrakine: bool = False) -> None:
        satir = self.karar_tablosu.secili_satir()
        if satir is None:
            return
        basvurdu = self.basvurdu.isChecked()
        try:
            hizmet.basvuru_kaydet(self.vt, satir["ogrenci_id"], self.kod,
                                  "basvurdu" if basvurdu else "basvurmadi",
                                  self.basvuru_tarihi.tarih() if basvurdu else None,
                                  self.dilekce.text() if basvurdu else "",
                                  self.gec_onay.text() if basvurdu else "")
        except (HizmetHatasi, ValueError) as hata:
            self.hata("Başvuru kaydedilemedi", hata)
            return
        gorunenler = [s["ogrenci_id"] for s in self.karar_tablosu.gorunen_satirlar()]
        self.tazele()
        self.bildir(f"{satir['okul_no']} {satir['ad_soyad']}: başvuru kararı kaydedildi.")
        if sonrakine:
            self._sonrakine_gec(satir["ogrenci_id"], gorunenler)

    def _sonrakine_gec(self, kimlik: int, onceki_sira: list[int]) -> None:
        """Kaydedilen öğrenciden sonraki, kararı bekleyen öğrenciye geçer."""
        satirlar = {s["ogrenci_id"]: s for s in self.karar_tablosu.gorunen_satirlar()}
        sira = onceki_sira.index(kimlik) if kimlik in onceki_sira else -1
        for aday in onceki_sira[sira + 1:] + onceki_sira[:sira + 1]:
            if aday in satirlar and satirlar[aday]["basvuru_durumu"] is None:
                self.karar_tablosu.sec(aday)
                self.dilekce.setFocus()
                return
        self.bildir("Kararı bekleyen başka öğrenci kalmadı.")

    def secilenleri_basvurmadi_say(self) -> None:
        secili = self.karar_tablosu.secili_satirlar()
        if not secili:
            self.ileti.uyari("Seçim yok", "Tablodan öğrenci seçin.")
            return
        if not self.ileti.soru("Başvurmadı olarak kaydet",
                               f"{len(secili)} öğrenci bu dönem başvurmadı olarak kaydedilecek ve "
                               "plan dışı kalacak. Devam edilsin mi?", "Kaydet"):
            return
        kaydedilen = 0
        try:
            for satir in secili:
                hizmet.basvuru_kaydet(self.vt, satir["ogrenci_id"], self.kod, "basvurmadi")
                kaydedilen += 1
        except HizmetHatasi as hata:
            self.tazele()
            self.hata("Başvuru kaydedilemedi",
                      kismi_ileti(hata, kaydedilen, "öğrenci başvurmadı olarak kaydedildi"))
            return
        self.tazele()
        self.bildir(f"{kaydedilen} öğrenci başvurmadı olarak kaydedildi.")

    def kisayol_kaydet(self) -> None:
        if self.sekmeler.currentIndex() == 1:
            self.duyuruyu_kaydet()
        elif self.sekmeler.currentIndex() == 2:
            self.karari_kaydet()

    # ================================================================= genel
    def goster(self) -> None:
        if not self.kod:
            kod = hizmet.varsayilan_pencere(self.vt)
            self.donem.blockSignals(True)
            self.donem.setCurrentIndex(PENCERE_KODLARI.index(kod) if kod in PENCERE_KODLARI
                                       else 0)
            self.donem.blockSignals(False)
            self.kod = PENCERE_KODLARI[self.donem.currentIndex()]
        self.tazele(duyuruyu_da=True)

    def _donem_degisti(self) -> None:
        self.kod = PENCERE_KODLARI[self.donem.currentIndex()]
        self.tazele(duyuruyu_da=True)

    def tazele(self, duyuruyu_da: bool = False) -> None:
        """Tabloları yeniden okur; seçim, kaydırma ve süzgeçler korunur."""
        if duyuruyu_da or self.duyuru is None:
            self._duyuruyu_doldur()
        else:
            self.duyuru = hizmet.duyuru_getir(self.vt, self.kod)
            self.belge_ozeti.setText("Plan dışı tutanağına girecek öğrenci: "
                                     f"{len(hizmet.plan_disi_birakilanlar(self.vt, self.kod))}")
        self.satirlar = hizmet.basvuru_tablosu(self.vt, self.kod)
        self._subeleri_doldur()
        self.tablo.yukle(self.satirlar)
        self._isaret_suzgeci()
        self.karar_tablosu.yukle(self.satirlar)
        self._karar_suzgeci()
        self._karari_forma_al()
        self.duyuru_yok_seridi.setVisible(self.duyuru is None)
        self._cipleri_yaz()
        eski = hizmet.isaret_tazeligi_uyarisi(self.vt)
        self.eski_seridi.ayarla(eski, "uyari")

    def _subeleri_doldur(self) -> None:
        subeler = sorted({s["sube"] for s in self.satirlar},
                         key=lambda s: (hizmet.sube_duzeyi(s) or 99, s))
        secili = self.sube_suzgeci.currentText()
        self.sube_suzgeci.blockSignals(True)
        self.sube_suzgeci.clear()
        self.sube_suzgeci.addItem("Bütün şubeler")
        self.sube_suzgeci.addItems(subeler)
        if secili in subeler:
            self.sube_suzgeci.setCurrentText(secili)
        self.sube_suzgeci.blockSignals(False)

    def _cipleri_yaz(self) -> None:
        while self.cipler.count():
            oge = self.cipler.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()
        bayrakli = [s for s in self.satirlar if s["bayrakli_mi"]]
        beklemeli = sum(1 for s in bayrakli if s["mezun_olamayan_mi"])
        devamsiz = sum(1 for s in bayrakli if s["devamsizlik_tebligati_mi"])
        bekleyen = sum(1 for s in bayrakli if s["basvuru_durumu"] is None)
        plan_disi = sum(1 for s in bayrakli if s["ozet"].startswith("Başvurmadı"))
        parcalar: list[tuple[str, str]] = [
            (f"İşaretli öğrenci: {len(bayrakli)} (beklemeli {beklemeli}, devamsız {devamsiz})", "")]
        if self.duyuru:
            parcalar.append((f"Duyuru kayıtlı • son başvuru "
                             f"{tarih_yaz(self.duyuru['basvuru_son_gunu'])}", "basari"))
        else:
            parcalar.append(("Bu dönem için duyuru kaydedilmedi", "uyari"))
        if bayrakli:
            parcalar.append((f"Karar bekleyen: {bekleyen}", "uyari" if bekleyen else "basari"))
            parcalar.append((f"Plan dışı: {plan_disi}", "engel" if plan_disi else ""))
        for metin, tur in parcalar:
            self.cipler.addWidget(cip(metin, tur))
        self.cipler.addStretch(1)


__all__ = ["BasvuruSayfasi"]
