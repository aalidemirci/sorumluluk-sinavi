"""06 Ders / branş eşleştirme ve iki aşamalı dersler (OKY md.58/2-e)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QLineEdit, QSplitter

from arayuz.bilesenler import (
    AramaKutusu, Kart, Sutun, Tablo, cip, dugme, etiket, secim_kutusu, turu_ayarla, yatay,
)
from arayuz.palet import RENK
from arayuz.sayfalar.temel import Sayfa
from veri import hizmet
from veri.hizmet import HizmetHatasi

YOK = "—"


def _ders_satiri(kayit: tuple) -> dict:
    ders_id, ad, brans, iki, yabanci, kayit_sayisi = kayit[:6]
    esdeger = hizmet.ders_esdeger_branslari(kayit)
    return {"kimlik": ders_id, "ad": ad, "brans": brans, "esdeger": esdeger,
            "iki_asamali_mi": bool(iki), "yabanci_dil_mi": bool(yabanci),
            "kayit_sayisi": kayit_sayisi, "eslendi_mi": bool(brans),
            "gosterim": " + ".join((brans, *esdeger)) if brans else "eşlenmedi"}


class DersSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.dersler: list[dict] = []
        kart = Kart("Ders / branş eşleştirme",
                    "Her ders bir alan branşına eşlenmeden plan üretilemez; komisyonun alan "
                    "öğretmeni bu branştan seçilir. Türk dili ve edebiyatı ile yabancı dil dersleri "
                    "iki aşamalı (yazılı ve uygulama) işaretlenir — OKY md.58/2-e. Birleşik derste "
                    "(ör. Görsel Sanatlar/Müzik) ikinci alanı da seçin.")
        self.arama_kutusu = AramaKutusu("Ders ya da branş ara…")
        self.yalniz_eksik = QCheckBox("Yalnız eşlenmemiş dersler")
        self.yalniz_eksik.toggled.connect(lambda _d: self._suzgeci_uygula())
        self.durum = cip()
        kart.ekle(yatay(self.arama_kutusu, self.yalniz_eksik, 0, self.durum))

        self.tablo = Tablo(
            [Sutun("Ders", lambda d: d["ad"], 230),
             Sutun("Branş", lambda d: d["gosterim"], 220),
             Sutun("İki aşamalı", lambda d: "Evet" if d["iki_asamali_mi"] else "Hayır", 100),
             Sutun("Kayıt", lambda d: d["kayit_sayisi"], 70, "sag",
                   ipucu=lambda d: "Aktif sorumluluk kaydı sayısı"),
             Sutun("", lambda d: "", uzat=True)],
            anahtar=lambda d: d["kimlik"], siralama=(0, Qt.SortOrder.AscendingOrder),
            zemin=lambda d: None if d["eslendi_mi"] else RENK["engel_zemin"],
            bos_metin="Ders yok. Dersler e-Okul sorumluluk raporundan gelir.")
        self.tablo.aramaya_bagla(self.arama_kutusu)
        self.tablo.secim_degisti.connect(self._forma_al)

        form = Kart("Seçili ders", kenar=(16, 14, 16, 14))
        form.setMinimumWidth(330)
        form.setMaximumWidth(420)
        self.ders_adi = etiket("Tablodan bir ders seçin.", "Bolum", sar=True)
        form.ekle(self.ders_adi)
        self.brans = secim_kutusu(en_az=16)
        self.esdeger = secim_kutusu(en_az=16)
        self.iki_asamali = QCheckBox("İki aşamalı (yazılı + uygulama)")
        self.karar = QLineEdit("Zümre kararı")
        alanlar = QGridLayout()
        alanlar.setVerticalSpacing(8)
        for satir, (ad, girdi) in enumerate((("Branş", self.brans),
                                             ("İkinci alan", self.esdeger),
                                             ("Karar / gerekçe", self.karar))):
            alanlar.addWidget(QLabel(ad), satir, 0)
            alanlar.addWidget(girdi, satir, 1)
        form.ekle(alanlar)
        form.ekle(self.iki_asamali)
        form.ekle(etiket("Eşleme kararının gerekçesi zorunludur; denetimde sorulur.", "Soluk",
                         sar=True))
        self.kaydet_dugmesi = dugme("Kaydet", "", "kaydet", tiklaninca=self.kaydet)
        self.sonraki_dugmesi = dugme("Kaydet ve sıradaki eşlenmemiş", "ana", "ileri",
                                     tiklaninca=lambda: self.kaydet(sonrakine=True))
        form.ekle(yatay(self.kaydet_dugmesi, self.sonraki_dugmesi))
        form.duzen.addStretch(1)

        bolme = QSplitter(Qt.Orientation.Horizontal)
        bolme.addWidget(self.tablo)
        bolme.addWidget(form)
        bolme.setStretchFactor(0, 1)
        bolme.setChildrenCollapsible(False)
        kart.ekle(bolme, 1)

        self.yeni_brans = QLineEdit()
        self.yeni_brans.setPlaceholderText("Okulda öğretmeni olmayan branş (ör. Felsefe)")
        self.yeni_brans.setMinimumWidth(340)
        self.yeni_brans.returnPressed.connect(self.brans_ekle)
        kart.ekle(yatay(self.yeni_brans, dugme("Branş havuzuna ekle", "", "ekle",
                                               tiklaninca=self.brans_ekle), 0))
        self.duzen.addWidget(kart, 1)
        self._forma_al()

    # ------------------------------------------------------------------ veri
    def goster(self) -> None:
        self.dersler = [_ders_satiri(k) for k in hizmet.dersleri_listele(self.vt)]
        branslar = [ad for _, ad, _ in hizmet.brans_havuzu_listele(self.vt)]
        for kutu, ilk in ((self.brans, ""), (self.esdeger, YOK)):
            secili = kutu.currentText()
            kutu.blockSignals(True)
            kutu.clear()
            kutu.addItems([ilk] + branslar if ilk else branslar)
            kutu.setCurrentText(secili)
            kutu.blockSignals(False)
        self.tablo.yukle(self.dersler)
        self._suzgeci_uygula()
        eksik = sum(1 for d in self.dersler if not d["eslendi_mi"])
        self.durum.setText(f"{eksik} ders eşlenmedi" if eksik else "Tüm dersler eşlendi")
        turu_ayarla(self.durum, "tur", "engel" if eksik else "basari")
        self._forma_al()

    def _suzgeci_uygula(self) -> None:
        eksik = self.yalniz_eksik.isChecked()
        self.tablo.kosulu_ayarla(lambda d: not eksik or not d["eslendi_mi"])

    def _forma_al(self) -> None:
        ders = self.tablo.secili_satir()
        for oge in (self.brans, self.esdeger, self.iki_asamali, self.karar, self.kaydet_dugmesi,
                    self.sonraki_dugmesi):
            oge.setEnabled(ders is not None)
        if ders is None:
            self.ders_adi.setText("Tablodan bir ders seçin.")
            return
        self.ders_adi.setText(f"{ders['ad']} • {ders['kayit_sayisi']} sorumluluk kaydı")
        self.brans.setCurrentText(ders["brans"])
        self.esdeger.setCurrentText(ders["esdeger"][0] if ders["esdeger"] else YOK)
        self.iki_asamali.setChecked(ders["iki_asamali_mi"] if ders["eslendi_mi"]
                                    else hizmet.iki_asamali_onerisi(ders["ad"]))

    def kaydet(self, sonrakine: bool = False) -> None:
        ders = self.tablo.secili_satir()
        if ders is None:
            return
        try:
            if not self.brans.currentText():
                raise HizmetHatasi("Branş havuzundan bir alan seçin.")
            esdeger = () if self.esdeger.currentText() in ("", YOK) else (
                self.esdeger.currentText(),)
            hizmet.ders_brans_esle(self.vt, ders["kimlik"], self.brans.currentText(),
                                   self.karar.text(), esdeger)
            hizmet.ders_ozellik_guncelle(self.vt, ders["kimlik"], self.iki_asamali.isChecked(),
                                         hizmet.yabanci_dil_mi(ders["ad"]))
        except HizmetHatasi as hata:
            self.hata("Eşleme kaydedilemedi", hata)
            return
        sira = [d["kimlik"] for d in self.tablo.gorunen_satirlar()]
        self.goster()
        self.bildir(f"{ders['ad']} → {self.brans.currentText()} kaydedildi.")
        if sonrakine:
            gorunen = {d["kimlik"]: d for d in self.tablo.gorunen_satirlar()}
            konum = sira.index(ders["kimlik"]) if ders["kimlik"] in sira else -1
            for aday in sira[konum + 1:] + sira[:konum + 1]:
                if aday in gorunen and not gorunen[aday]["eslendi_mi"]:
                    self.tablo.sec(aday)
                    return
            self.bildir("Eşlenmemiş ders kalmadı.")

    def kisayol_kaydet(self) -> None:
        self.kaydet()

    def brans_ekle(self) -> None:
        try:
            hizmet.brans_havuzu_ekle(self.vt, self.yeni_brans.text())
        except HizmetHatasi as hata:
            self.hata("Branş eklenemedi", hata)
            return
        ad = self.yeni_brans.text().strip()
        self.yeni_brans.clear()
        self.goster()
        self.bildir(f"{ad} branş havuzuna eklendi.")
