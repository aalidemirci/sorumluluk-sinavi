"""03 Salonlar: sınav salonları ve kapasiteleri."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QSpinBox

from arayuz.bilesenler import Kart, Sutun, Tablo, dugme, etiket, yatay
from arayuz.sayfalar.temel import Sayfa
from cekirdek.kurallar import SALON_OGRENCI_UST_SINIRI
from veri import hizmet
from veri.hizmet import HizmetHatasi


class SalonSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        kart = Kart("Sınav salonları",
                    "Salon sayısı ve kapasitesi, aynı saatte kaç sınav yapılabileceğini belirler. "
                    f"Program bir salona en çok {SALON_OGRENCI_UST_SINIRI} öğrenci koyar (okul "
                    "kararı); her salon için ayrı bir gözcü görevlendirilir — OKY md.58/2-b. "
                    "Var olan bir salonun adını yazıp kaydetmek kapasitesini günceller.")
        self.ad = QLineEdit()
        self.ad.setPlaceholderText("Salon adı (ör. A-101)")
        self.ad.returnPressed.connect(self.kaydet)
        self.kapasite = QSpinBox()
        self.kapasite.setRange(1, 500)
        self.kapasite.setValue(30)
        self.kapasite.setSuffix(" kişi")
        kart.ekle(yatay(self.ad, QLabel("Kapasite"), self.kapasite,
                        dugme("Ekle / güncelle", "ana", "kaydet", tiklaninca=self.kaydet), 0))
        self.tablo = Tablo(
            [Sutun("Salon", lambda s: s.ad, 280),
             Sutun("Kapasite", lambda s: s.kapasite, 120, "sag"),
             Sutun("Planda en çok", lambda s: min(s.kapasite, SALON_OGRENCI_UST_SINIRI), 140,
                   "sag", ipucu=lambda s: "Bir salona konan en çok öğrenci (okul kararı)"),
             Sutun("", lambda s: "", uzat=True)],
            anahtar=lambda s: s.kimlik, coklu_secim=True,
            bos_metin="Henüz salon tanımlanmadı. Plan üretmeden önce en az bir salon gerekir.")
        self.tablo.secim_degisti.connect(self._secimi_forma_al)
        kart.ekle(self.tablo, 1)
        self.toplam = etiket("", "Soluk")
        kart.ekle(yatay(self.toplam, 0,
                        dugme("Seçilenleri sil", "tehlike", "sil", tiklaninca=self.sil)))
        self.duzen.addWidget(kart, 1)

    def goster(self) -> None:
        salonlar = hizmet.salonlari_getir(self.vt)
        self.tablo.yukle(salonlar)
        self.toplam.setText(f"Toplam {len(salonlar)} salon, "
                            f"{sum(s.kapasite for s in salonlar)} kişilik kapasite.")

    def _secimi_forma_al(self) -> None:
        salon = self.tablo.secili_satir()
        if salon is not None:
            self.ad.setText(salon.ad)
            self.kapasite.setValue(salon.kapasite)

    def kaydet(self) -> None:
        try:
            kimlik = hizmet.salon_ekle(self.vt, self.ad.text(), self.kapasite.value())
        except HizmetHatasi as hata:
            self.hata("Salon kaydedilemedi", hata)
            return
        self.goster()
        self.tablo.sec(kimlik)
        self.bildir(f"{self.ad.text().strip()} kaydedildi.")

    def sil(self) -> None:
        secili = self.tablo.secili_satirlar()
        if not secili:
            self.ileti.uyari("Seçim yok", "Silinecek salonu seçin.")
            return
        for salon in secili:
            try:
                hizmet.salon_sil(self.vt, salon.kimlik)
            except HizmetHatasi as hata:
                self.hata("Salon silinemedi", hata, kim=salon.ad)
        self.ad.clear()
        self.goster()
