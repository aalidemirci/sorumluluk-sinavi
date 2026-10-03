"""04 e-Okul sorumluluk raporu (OOK12001R010)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout

from arayuz.bilesenler import (
    secim_kutusu,
    AramaKutusu, Kart, Serit, Sutun, Tablo, arka_planda, cip, dugme, etiket, yatay,
)
from arayuz.palet import RENK
from arayuz.sayfalar.personel import RAPOR_YONERGESI
from arayuz.sayfalar.temel import Sayfa
from veri import hizmet
from veri.hizmet import HizmetHatasi
from veri.rapor_okuma import RaporHatasi

ONIZLEME_ADLARI = {"eklenecek": "yeni", "guncellenecek": "değişen", "degismedi": "aynı",
                   "kayitli": "kayıtlı"}
ONIZLEME_ZEMINI = {"eklenecek": RENK["basari_zemin"], "guncellenecek": RENK["uyari_zemin"]}


class SorumlulukSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.ozet = None

        ust = Kart("e-Okul sorumluluk raporu (OOK12001R010 — Sorumluluk Sınavına Girecek "
                   "Öğrenci Listesi)",
                   "Hangi öğrencinin hangi derslerden sorumlu olduğu bu rapordan okunur. Rapor "
                   "okulun tamamını kapsıyorsa dosyada bulunmayan aktif kayıtlar pasife alınır; "
                   "kısmi liste aktarıyorsanız aşağıdaki kutuyu kaldırın.")
        ust.ekle(Serit(RAPOR_YONERGESI, "bilgi"))
        self.tam_liste = QCheckBox("Bu rapor okulun tam listesidir")
        self.tam_liste.setChecked(True)
        self.onayla_dugmesi = dugme("Önizlemeyi onayla", "", "onay", tiklaninca=self.onayla)
        self.vazgec_dugmesi = dugme("Önizlemeyi kapat", "metin", tiklaninca=self.onizlemeyi_kapat)
        ust.ekle(yatay(dugme("Rapor seç ve önizle", "ana", "yukle", tiklaninca=self.rapor_sec),
                       self.onayla_dugmesi, self.vazgec_dugmesi, self.tam_liste, 0))
        self.durum = QHBoxLayout()
        self.durum.setSpacing(6)
        ust.ekle(self.durum)
        # SG-05: raporda programın okumadığı sütunlar varsa yalnız başlık adları.
        self.uyari_seridi = Serit("", "uyari")
        self.uyari_seridi.hide()
        ust.ekle(self.uyari_seridi)
        self.duzen.addWidget(ust)

        liste = Kart()
        self.arama_kutusu = AramaKutusu("Numara, ad, şube ya da ders ara…")
        self.sube_suzgeci = secim_kutusu()
        self.eylem_suzgeci = secim_kutusu()
        self.eylem_suzgeci.addItems(["Bütün satırlar", "Yalnız yeni", "Yalnız değişen"])
        self.sayac = etiket("", "Soluk")
        liste.ekle(yatay(self.arama_kutusu, self.sube_suzgeci, self.eylem_suzgeci, 0, self.sayac))
        self.tablo = Tablo(
            [Sutun("Okul no", lambda s: s["no"], 100),
             Sutun("Adı Soyadı", lambda s: s["ad"], 240),
             Sutun("Şube", lambda s: s["sube"], 90),
             Sutun("Düzey", lambda s: s["duzey"], 70, "sag"),
             Sutun("Ders", lambda s: s["ders"], 280),
             Sutun("Durum", lambda s: ONIZLEME_ADLARI.get(s["eylem"], s["eylem"]), uzat=True)],
            anahtar=lambda s: s["anahtar"], zemin=lambda s: ONIZLEME_ZEMINI.get(s["eylem"]),
            bos_metin="Sorumluluk kaydı yok. Yukarıdan e-Okul raporunu içe aktarın.")
        self.tablo.aramaya_bagla(self.arama_kutusu)
        for kutu in (self.sube_suzgeci, self.eylem_suzgeci):
            kutu.currentIndexChanged.connect(lambda _i: self._suzgeci_uygula())
        liste.ekle(self.tablo, 1)
        self.duzen.addWidget(liste, 1)
        self._kipi_ayarla(onizleme=False)

    # ------------------------------------------------------------------ veri
    def goster(self) -> None:
        if self.ozet is None:
            self._kayitlari_doldur()

    def _kayitlari_doldur(self) -> None:
        kayitlar = hizmet.sorumluluk_kayitlari(self.vt)
        satirlar = [{"anahtar": sira, "no": k.okul_no, "ad": k.ad_soyad, "sube": k.sube,
                     "duzey": k.sinif_duzeyi, "ders": k.ders_adi, "eylem": "kayitli"}
                    for sira, k in enumerate(kayitlar)]
        self._satirlari_goster(satirlar)
        ogrenci = len({(k.okul_no, k.sube) for k in kayitlar})
        self._durumu_yaz([(f"Kayıtlı {len(kayitlar)} sorumluluk kaydı", ""),
                          (f"{ogrenci} öğrenci", "")] if kayitlar else [])

    def _satirlari_goster(self, satirlar: list[dict]) -> None:
        subeler = sorted({s["sube"] for s in satirlar},
                         key=lambda s: (hizmet.sube_duzeyi(s) or 99, s))
        secili = self.sube_suzgeci.currentText()
        self.sube_suzgeci.blockSignals(True)
        self.sube_suzgeci.clear()
        self.sube_suzgeci.addItem("Bütün şubeler")
        self.sube_suzgeci.addItems(subeler)
        if secili in subeler:
            self.sube_suzgeci.setCurrentText(secili)
        self.sube_suzgeci.blockSignals(False)
        self.tablo.yukle(satirlar, secimi_koru=False)
        self._suzgeci_uygula()

    def _suzgeci_uygula(self) -> None:
        sube = self.sube_suzgeci.currentText() if self.sube_suzgeci.currentIndex() > 0 else ""
        eylem = {1: "eklenecek", 2: "guncellenecek"}.get(self.eylem_suzgeci.currentIndex())
        self.tablo.kosulu_ayarla(lambda s: (not sube or s["sube"] == sube)
                                 and (eylem is None or s["eylem"] == eylem))
        gorunen, toplam = self.tablo.suzgec.rowCount(), self.tablo.model.rowCount()
        self.sayac.setText(f"{gorunen} / {toplam} satır" if gorunen != toplam
                           else f"{toplam} satır")

    def _durumu_yaz(self, parcalar: list[tuple[str, str]]) -> None:
        while self.durum.count():
            oge = self.durum.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()
        for metin, tur in parcalar:
            self.durum.addWidget(cip(metin, tur))
        self.durum.addStretch(1)

    def _kipi_ayarla(self, onizleme: bool) -> None:
        self.onayla_dugmesi.setEnabled(onizleme)
        self.vazgec_dugmesi.setVisible(onizleme)
        self.eylem_suzgeci.setVisible(onizleme)
        if not onizleme:
            self.uyari_seridi.hide()

    # -------------------------------------------------------------- önizleme
    def rapor_sec(self) -> None:
        yol, _ = QFileDialog.getOpenFileName(self, "e-Okul sorumluluk raporu", "",
                                             "e-Okul dosyası (*.xlsx *.xls *.csv)")
        if yol:
            self.raporu_onizle(Path(yol))

    def raporu_onizle(self, yol: Path) -> None:
        self.uyg.mesgul_ac("Sorumluluk raporu okunuyor…")
        arka_planda(lambda: hizmet.sorumluluk_onizle(self.vt, yol), self._onizleme_geldi,
                    self._onizleme_hatasi)

    def _onizleme_hatasi(self, hata: BaseException) -> None:
        self.uyg.mesgul_kapat()
        if isinstance(hata, (HizmetHatasi, RaporHatasi, OSError, ValueError)):
            self.hata("Sorumluluk raporu okunamadı", hata)
        else:
            raise hata

    def _onizleme_geldi(self, ozet) -> None:
        self.uyg.mesgul_kapat()
        self.ozet = ozet
        satirlar = [{"anahtar": sira, "no": no, "ad": ad, "sube": sube, "duzey": duzey,
                     "ders": ders, "eylem": eylem}
                    for sira, (no, ad, sube, duzey, ders, eylem) in enumerate(ozet.satirlar)]
        self._satirlari_goster(satirlar)
        ogrenci = len({(s["no"], s["sube"]) for s in satirlar})
        self._durumu_yaz([(f"{ozet.toplam} kayıt", ""), (f"{ogrenci} öğrenci", ""),
                          (f"+{ozet.eklenen} yeni", "basari"),
                          (f"~{ozet.guncellenen} değişen", "uyari"),
                          (f"−{ozet.cikan} düşecek", "engel" if ozet.cikan else "")])
        self.uyari_seridi.ayarla("\n".join(ozet.uyarilar), "uyari")
        self._kipi_ayarla(onizleme=True)

    def onizlemeyi_kapat(self) -> None:
        self.ozet = None
        self.eylem_suzgeci.setCurrentIndex(0)
        self._kipi_ayarla(onizleme=False)
        self._kayitlari_doldur()

    def onayla(self) -> None:
        if self.ozet is None:
            return
        ozet = self.ozet
        uyari = (f"\n\nDosyada bulunmayan {ozet.cikan} aktif kayıt pasife alınacak."
                 if self.tam_liste.isChecked() and ozet.cikan else "")
        if not self.ileti.soru("Sorumluluk kayıtlarını güncelle",
                               f"{ozet.toplam} kayıt işlenecek.{uyari}\n\nDevam edilsin mi?",
                               "Onayla"):
            return
        try:
            hizmet.sorumluluk_onayla(self.vt, ozet.aktarim_id, self.tam_liste.isChecked())
        except HizmetHatasi as hata:
            self.hata("Onay verilemedi", hata)
            return
        self.onizlemeyi_kapat()
        self.bildir("Sorumluluk kayıtları güncellendi.")
