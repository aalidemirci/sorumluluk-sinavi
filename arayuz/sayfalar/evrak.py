"""08 Evrak ve teslim: belge üretimi ve sınav evrakının teslim takibi."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QTabWidget, QWidget,
)

from arayuz.bilesenler import (
    AramaKutusu, Kart, Serit, Sutun, Tablo, TarihAlani, arka_planda, cip, dugme, etiket,
    secim_kutusu, yatay,
)
from arayuz.palet import RENK
from arayuz.sayfalar.plan import donem_secenekleri
from arayuz.sayfalar.temel import Sayfa, kismi_ileti
from cekirdek.modeller import PlanTuru
from cekirdek.takvim import tarih_yaz
from evrak import uretici
from veri import hizmet
from veri.hizmet import HizmetHatasi

TESLIM_ZEMINI = {"gecikti": RENK["engel_zemin"], "teslim alındı": RENK["basari_zemin"]}


class EvrakSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.secenekler: list[tuple[str, str, PlanTuru]] = []
        self.plan_id: int | None = None
        self.son_klasor: Path | None = None

        ust = Kart(kenar=(16, 12, 16, 12))
        self.donem = secim_kutusu(en_az=20)
        self.donem.currentIndexChanged.connect(lambda _i: self.tazele())
        self.durum = QHBoxLayout()
        self.durum.setSpacing(6)
        ust.ekle(yatay(QLabel("Dönem"), self.donem, 0))
        ust.ekle(self.durum)
        self.plan_yok = Serit("Bu dönemde kayıtlı plan yok. Önce Sınav Planı adımında planı "
                              "kaydedin.", "uyari")
        self.plan_yok.dugme_ekle("Sınav Planı'na git", lambda: self.uyg.sayfa_goster(6))
        self.plan_yok.hide()
        ust.ekle(self.plan_yok)
        self.duzen.addWidget(ust)

        self.sekmeler = QTabWidget()
        self.sekmeler.addTab(self._uretim_sekmesi(), "Evrak üretimi")
        self.sekmeler.addTab(self._teslim_sekmesi(), "Teslim çizelgesi")
        self.duzen.addWidget(self.sekmeler, 1)

    # ================================================================= üretim
    def _uretim_sekmesi(self) -> QWidget:
        kap = QWidget()
        duzen = QHBoxLayout(kap)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(14)
        secim = Kart("Üretilecek belgeler",
                     "Belgeler .docx olarak seçtiğiniz klasöre yazılır. Aynı içerik yeniden "
                     "üretilirse sürüm numarası artmaz; kesinleşmiş plandan üretilen belge onaylı "
                     "sürüm sayılır ve sonradan değişirse değişiklik föyü kaydedilir.")
        izgara = QGridLayout()
        izgara.setVerticalSpacing(6)
        self.evrak_secimleri: dict[str, QCheckBox] = {}
        for sira, evrak in enumerate(uretici.EVRAKLAR):
            kutu = QCheckBox(evrak.ad)
            kutu.setChecked(True)
            izgara.addWidget(kutu, sira // 2, sira % 2)
            self.evrak_secimleri[evrak.anahtar] = kutu
        secim.ekle(izgara)
        secim.ekle(yatay(dugme("Tümünü seç", "metin", tiklaninca=lambda: self._hepsi(True)),
                         dugme("Seçimi kaldır", "metin", tiklaninca=lambda: self._hepsi(False)),
                         0))
        self.ogrenci_gosterimi = secim_kutusu([ad for _, ad in hizmet.OGRENCI_GOSTERIMI],
                                              en_az=26)
        secim.ekle(yatay(QLabel("İlan çizelgesinde öğrenci"), self.ogrenci_gosterimi, 0))
        secim.ekle(etiket("Açık ad hiçbir seçenekte yayımlanmaz (KVKK).", "Soluk"))
        self.uret_dugmesi = dugme("Klasör seç ve üret", "ana", "evrak", tiklaninca=self.uret)
        secim.ekle(yatay(0, self.uret_dugmesi))
        secim.duzen.addStretch(1)
        duzen.addWidget(secim, 1)

        sonuc = Kart("Son üretim")
        self.foy_seridi = Serit("", "uyari")
        self.foy_seridi.hide()
        sonuc.ekle(self.foy_seridi)
        self.sonuc_tablosu = Tablo(
            [Sutun("Dosya", lambda s: s["ad"], 300),
             Sutun("İçerik özeti (SHA-256)", lambda s: s["ozet"], uzat=True)],
            anahtar=lambda s: s["ad"], bos_metin="Henüz bu oturumda belge üretilmedi.")
        sonuc.ekle(self.sonuc_tablosu, 1)
        self.klasor_dugmesi = dugme("Klasörü aç", "", "klasor", tiklaninca=self._klasoru_ac)
        self.klasor_dugmesi.setEnabled(False)
        sonuc.ekle(yatay(0, self.klasor_dugmesi))
        duzen.addWidget(sonuc, 1)
        return kap

    def _hepsi(self, deger: bool) -> None:
        for kutu in self.evrak_secimleri.values():
            kutu.setChecked(deger)

    def _klasoru_ac(self) -> None:
        if self.son_klasor:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.son_klasor)))

    def uret(self) -> None:
        if self.plan_id is None:
            self.ileti.uyari("Plan yok", "Önce Sınav Planı adımında planı kaydedin.")
            return
        secilenler = [a for a, kutu in self.evrak_secimleri.items() if kutu.isChecked()]
        if not secilenler:
            self.ileti.uyari("Seçim yok", "En az bir belge seçin.")
            return
        son = str(self.uyg.ayarlar.value("evrak/son_klasor", str(Path.home())))
        klasor = QFileDialog.getExistingDirectory(self, "Evrakın yazılacağı klasör", son)
        if klasor:
            self.klasore_uret(Path(klasor), secilenler)

    def klasore_uret(self, klasor: Path, secilenler: list[str]) -> None:
        plan_id = self.plan_id
        # Bu üretimde doğan değişiklik föyleri: önce/sonra karşılaştırılır.
        onceki = {(f["tur"], f["surum"])
                  for f in hizmet.onayli_belge_degisiklikleri(self.vt, str(plan_id))}
        gosterim = hizmet.OGRENCI_GOSTERIMI[self.ogrenci_gosterimi.currentIndex()][0]
        self.uyg.ayarlar.setValue("evrak/son_klasor", str(klasor))
        self.uyg.mesgul_ac("Belgeler üretiliyor…")
        arka_planda(lambda: uretici.evrak_uret(self.vt, plan_id, klasor, secilenler,
                                               ogrenci_gosterimi=gosterim),
                    lambda sonuc: self._uretildi(sonuc, klasor, plan_id, onceki),
                    self._uretilemedi)

    def _uretilemedi(self, hata: BaseException) -> None:
        self.uyg.mesgul_kapat()
        if isinstance(hata, (HizmetHatasi, OSError)):
            self.hata("Evrak üretilemedi", hata)
        else:
            raise hata

    def _uretildi(self, uretilenler, klasor: Path, plan_id: int, onceki: set) -> None:
        self.uyg.mesgul_kapat()
        self.son_klasor = klasor
        self.klasor_dugmesi.setEnabled(True)
        self.sonuc_tablosu.yukle([{"ad": yol.name, "ozet": ozet[:32] + "…"}
                                  for yol, ozet in uretilenler], secimi_koru=False)
        yeni = [f for f in hizmet.onayli_belge_degisiklikleri(self.vt, str(plan_id))
                if (f["tur"], f["surum"]) not in onceki]
        if yeni:
            adlar = {e.anahtar: e.ad for e in uretici.EVRAKLAR}
            self.foy_seridi.ayarla(
                "Onaylı belge değişti: " + "; ".join(
                    f"{adlar.get(f['tur'], f['tur'])} (sürüm {f['surum']})" for f in yeni)
                + ". İmzalanmış eski çıktıların yerine yeni sürümü imzaya sunun; değişiklik "
                  "föyü belge geçmişine kaydedildi.", "uyari")
        else:
            self.foy_seridi.hide()
        self.bildir(f"{len(uretilenler)} belge {klasor} klasörüne yazıldı.", "Klasörü aç",
                    self._klasoru_ac)

    # ================================================================= teslim
    def _teslim_sekmesi(self) -> QWidget:
        kart = Kart(kenar=(16, 14, 16, 12))
        kart.ekle(etiket("Sınav sonrası komisyondan geri alınan evrak burada izlenir. Teslim "
                         "süresi sınav tarihini izleyen ilk iş günüdür; tatil günleri sayılmaz.",
                         "Soluk", sar=True))
        self.arama_kutusu = AramaKutusu("Sınav, evrak ya da kişi ara…")
        self.teslim_suzgeci = secim_kutusu(["Bütün evrak", "Bekleyen", "Geciken",
                                            "Teslim alınan"], en_az=12)
        self.teslim_suzgeci.currentIndexChanged.connect(lambda _i: self._teslim_suzgeci())
        kart.ekle(yatay(self.arama_kutusu, self.teslim_suzgeci, 0))
        self.teslim_tablosu = Tablo(
            [Sutun("Sınav", lambda s: s.oturum_etiketi, 230),
             Sutun("Tarih", lambda s: tarih_yaz(s.tarih), 95, siralama=lambda s: s.tarih),
             Sutun("Evrak", lambda s: s.evrak_adi, 170),
             Sutun("Adet", lambda s: "" if s.adet is None else s.adet, 60, "sag"),
             Sutun("Teslim eden", lambda s: s.teslim_eden, 160),
             Sutun("Teslim alan", lambda s: s.teslim_alan, 160),
             Sutun("Durum", lambda s: s.durum(), uzat=True)],
            anahtar=lambda s: (s.oturum_id, s.evrak_turu), coklu_secim=True,
            zemin=lambda s: TESLIM_ZEMINI.get(s.durum()),
            bos_metin="Bu dönemin kayıtlı planı yok ya da planda oturum yok.")
        self.teslim_tablosu.aramaya_bagla(self.arama_kutusu)
        kart.ekle(self.teslim_tablosu, 1)

        self.teslim_eden = self._kisi_kutusu()
        self.teslim_alan = self._kisi_kutusu()
        self.teslim_adet = QSpinBox()
        self.teslim_adet.setRange(0, 999)
        self.teslim_adet.setSpecialValueText("—")
        self.teslim_adet.setToolTip("Boş bırakmak için 0")
        self.teslim_tarihi = TarihAlani()
        self.teslim_aciklama = QLineEdit()
        self.teslim_aciklama.setPlaceholderText("Açıklama")
        kart.ekle(yatay(QLabel("Teslim eden"), self.teslim_eden, QLabel("Teslim alan"),
                        self.teslim_alan, QLabel("Adet"), self.teslim_adet, 0))
        kart.ekle(yatay(QLabel("Teslim tarihi"), self.teslim_tarihi, self.teslim_aciklama,
                        dugme("Seçilenleri teslim al", "ana", "onay", tiklaninca=self.teslim_al),
                        dugme("Teslimi geri al", "", "geri", tiklaninca=self.teslimi_geri_al)))
        return kart

    def _kisi_kutusu(self) -> QComboBox:
        kutu = secim_kutusu(en_az=22)
        kutu.setEditable(True)
        kutu.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        kutu.completer().setFilterMode(kutu.completer().filterMode().MatchContains)
        kutu.completer().setCompletionMode(kutu.completer().CompletionMode.PopupCompletion)
        return kutu

    def _kisileri_doldur(self) -> None:
        kisiler = sorted(hizmet.personelleri_getir(self.vt), key=lambda p: p.ad)
        for kutu in (self.teslim_eden, self.teslim_alan):
            secili = kutu.currentData()
            kutu.blockSignals(True)
            kutu.clear()
            kutu.addItem("", None)
            for kisi in kisiler:
                kutu.addItem(f"{kisi.ad} ({kisi.brans})" if kisi.brans else kisi.ad, kisi.kimlik)
            if secili is not None:
                kutu.setCurrentIndex(max(0, kutu.findData(secili)))
            kutu.blockSignals(False)

    def _teslim_suzgeci(self) -> None:
        secim = self.teslim_suzgeci.currentIndex()
        istenen = {1: "bekleniyor", 2: "gecikti", 3: "teslim alındı"}.get(secim)
        self.teslim_tablosu.kosulu_ayarla(lambda s: istenen is None or s.durum() == istenen)

    def _secili_kisi(self, kutu: QComboBox) -> int | None:
        metin = kutu.currentText().strip()
        sira = kutu.findText(metin)
        return kutu.itemData(sira) if sira > 0 else None

    def teslim_al(self) -> None:
        secili = self.teslim_tablosu.secili_satirlar()
        if not secili:
            self.ileti.uyari("Seçim yok", "Çizelgeden evrak satırı seçin (birden çok satır "
                                          "seçilebilir).")
            return
        eden, alan = self._secili_kisi(self.teslim_eden), self._secili_kisi(self.teslim_alan)
        if eden is None or alan is None:
            self.ileti.uyari("Görevli seçilmedi", "Teslim eden ve teslim alan görevliyi seçin.")
            return
        adet = self.teslim_adet.value() or None
        kaydedilen = 0
        try:
            for satir in secili:
                hizmet.teslim_kaydet(self.vt, satir.oturum_id, satir.evrak_turu, eden, alan,
                                     adet, self.teslim_aciklama.text(), self.teslim_tarihi.tarih())
                kaydedilen += 1
        except HizmetHatasi as hata:
            # Hata sonrası başarı bildirimi gösterilmez; kısmen kaydedildiyse kaç
            # satırın işlendiği söylenir, çizelge gerçek durumu gösterir.
            self._teslim_tazele()
            self.hata("Teslim kaydedilemedi", kismi_ileti(hata, kaydedilen, "evrak teslim alındı"))
            return
        self._teslim_tazele()
        self.bildir(f"{kaydedilen} evrak teslim alındı.")

    def teslimi_geri_al(self) -> None:
        secili = [s for s in self.teslim_tablosu.secili_satirlar() if s.teslim_edildi_mi]
        if not secili:
            self.ileti.bilgi("Kayıt yok", "Seçili satırlarda teslim kaydı bulunmuyor.")
            return
        geri_alinan = 0
        try:
            for satir in secili:
                hizmet.teslim_geri_al(self.vt, satir.oturum_id, satir.evrak_turu)
                geri_alinan += 1
        except HizmetHatasi as hata:
            self._teslim_tazele()
            self.hata("Teslim geri alınamadı",
                      kismi_ileti(hata, geri_alinan, "teslim kaydı geri alındı"))
            return
        self._teslim_tazele()
        self.bildir(f"{geri_alinan} teslim kaydı geri alındı.")

    def _teslim_tazele(self) -> None:
        satirlar = hizmet.teslim_cizelgesi(self.vt, self.plan_id) if self.plan_id else []
        self.teslim_tablosu.yukle(satirlar)
        self._teslim_suzgeci()
        self._durumu_yaz()

    # ================================================================= genel
    def goster(self) -> None:
        try:
            hizmet.pencereleri_getir(self.vt)
        except HizmetHatasi as hata:
            self.plan_yok.ayarla(str(hata), "engel")
            self.sekmeler.setEnabled(False)
            return
        self.sekmeler.setEnabled(True)
        # Evrak sınavdan sonra toplanır: varsayılan, başlamış son dönemdir.
        secili = (self.secenekler[self.donem.currentIndex()][1:] if self.secenekler
                  and self.donem.currentIndex() >= 0 else
                  (hizmet.varsayilan_pencere(self.vt, gecmise_bak=True), PlanTuru.OLAGAN))
        self.secenekler = [(ad.split("  ")[0], kod, tur)
                           for ad, kod, tur in donem_secenekleri(self.vt)]
        self.donem.blockSignals(True)
        self.donem.clear()
        self.donem.addItems([s[0] for s in self.secenekler])
        self.donem.setCurrentIndex(next((i for i, s in enumerate(self.secenekler)
                                         if (s[1], s[2]) == tuple(secili)), 0))
        self.donem.blockSignals(False)
        self._kisileri_doldur()
        self.tazele()

    def tazele(self) -> None:
        if not self.secenekler:
            return
        _, kod, tur = self.secenekler[max(0, self.donem.currentIndex())]
        self.plan_id = hizmet.son_plani_getir(self.vt, kod, tur)
        self.plan_yok.setVisible(self.plan_id is None)
        self.plan_yok.ayarla("Bu dönemde kayıtlı plan yok. Önce Sınav Planı adımında planı "
                             "kaydedin." if self.plan_id is None else "", "uyari")
        self.uret_dugmesi.setEnabled(self.plan_id is not None)
        self._teslim_tazele()

    def _durumu_yaz(self) -> None:
        while self.durum.count():
            oge = self.durum.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()
        if self.plan_id is not None:
            ozet = hizmet.teslim_ozeti(self.vt, self.plan_id)
            self.durum.addWidget(cip(f"Plan #{self.plan_id}"))
            self.durum.addWidget(cip(f"{ozet['teslim']}/{ozet['toplam']} evrak teslim alındı",
                                     "basari" if ozet["teslim"] == ozet["toplam"] else ""))
            if ozet["gecikti"]:
                self.durum.addWidget(cip(f"{ozet['gecikti']} gecikmiş", "engel"))
        self.durum.addStretch(1)


__all__ = ["EvrakSayfasi"]
