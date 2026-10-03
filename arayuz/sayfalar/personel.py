"""02 Öğretmen listesi: e-Okul personel raporu, elle düzenleme ve müsaitlik."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout

from arayuz.bilesenler import (
    secim_kutusu,
    AramaKutusu, Kart, Serit, Sutun, Tablo, arka_planda, cip, dugme, etiket, yatay,
)
from arayuz.palet import RENK
from arayuz.pencereler import MusaitlikPenceresi, PersonelEklePenceresi
from arayuz.sayfalar.temel import Sayfa
from veri import hizmet
from veri.hizmet import HizmetHatasi
from veri.rapor_okuma import RaporHatasi

RAPOR_YONERGESI = ("Raporu e-Okul'da açın → görüntüleyicide HTML5'i seçin → dışa aktarmada "
                   "Excel → SADECE VERİ seçeneğini işaretleyin. \"Excel'e aktar\" düğmesiyle "
                   "alınan biçimlendirilmiş çıktı okunamaz.")
ONIZLEME_ADLARI = {"eklenecek": "eklenecek", "guncellenecek": "güncellenecek",
                   "degismedi": "değişmedi"}
ONIZLEME_ZEMINI = {"eklenecek": RENK["basari_zemin"], "guncellenecek": RENK["uyari_zemin"]}


class PersonelSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.ozet = None
        self.kayitlar: list[dict] = []

        ust = Kart("e-Okul personel raporu (OOK01001R1 — Kurum Personel Listesi)",
                   "Öğretmen listesi ve branş havuzu bu rapordan kurulur. Önizleme onaylanmadan "
                   "hiçbir kayıt değişmez.")
        ust.ekle(Serit(RAPOR_YONERGESI, "bilgi"))
        self.onizle_dugmesi = dugme("Rapor seç ve önizle", "ana", "yukle",
                                    tiklaninca=self.rapor_sec)
        self.onayla_dugmesi = dugme("Farkları onayla", "", "onay", tiklaninca=self.onayla)
        self.vazgec_dugmesi = dugme("Önizlemeyi kapat", "metin", tiklaninca=self.onizlemeyi_kapat)
        self.durum = QHBoxLayout()
        self.durum.setSpacing(6)
        ust.ekle(yatay(self.onizle_dugmesi, self.onayla_dugmesi, self.vazgec_dugmesi, 0))
        ust.ekle(self.durum)
        self.duzen.addWidget(ust)

        liste = Kart()
        self.arama_kutusu = AramaKutusu("Ad, branş ya da görev ara…")
        self.brans_suzgeci = secim_kutusu()
        self.durum_suzgeci = secim_kutusu()
        self.durum_suzgeci.addItems(["Aktif ve pasif", "Yalnız aktif", "Yalnız pasif"])
        self.sayac = etiket("", "Soluk")
        liste.ekle(yatay(self.arama_kutusu, self.brans_suzgeci, self.durum_suzgeci, 0, self.sayac))

        self.tablo = Tablo(
            [Sutun("Adı Soyadı", lambda k: k["ad"], 230,
                   siralama=lambda k: (not k["aktif_mi"], k["ad"])),
             Sutun("Görevi", lambda k: k["unvan"], 160),
             Sutun("Kadro", lambda k: k["kadro"], 110),
             Sutun("Branşı", lambda k: k["brans"], 190),
             Sutun("Durum", lambda k: k["durum_metni"], 190),
             Sutun("Görev", lambda k: k.get("gorev_sayisi", ""), 70, "sag",
                   ipucu=lambda k: "Bu öğretim yılındaki komisyon üyeliği ve gözcülük sayısı"),
             Sutun("Müsait değil", lambda k: k.get("musait_metni", ""), uzat=True)],
            anahtar=lambda k: k["anahtar"], coklu_secim=True,
            siralama=(0, Qt.SortOrder.AscendingOrder),
            zemin=lambda k: k.get("zemin"), yazi_rengi=lambda k: k.get("yazi_rengi"),
            bos_metin="Personel listesi boş. Yukarıdan e-Okul personel raporunu içe aktarın.")
        self.tablo.aramaya_bagla(self.arama_kutusu)
        self.tablo.cift_tiklandi.connect(lambda _k: self.musaitlik_ac())
        self.tablo.secim_degisti.connect(self._dugmeleri_tazele)
        for kutu in (self.brans_suzgeci, self.durum_suzgeci):
            kutu.currentIndexChanged.connect(lambda _i: self._suzgeci_uygula())
        self.tablo.suzgec.modelReset.connect(self._sayaci_tazele)
        self.tablo.suzgec.layoutChanged.connect(self._sayaci_tazele)
        self.tablo.suzgec.rowsInserted.connect(self._sayaci_tazele)
        self.tablo.suzgec.rowsRemoved.connect(self._sayaci_tazele)
        liste.ekle(self.tablo, 1)

        self.musaitlik_dugmesi = dugme("Müsaitlik…", "", "saat", "Dolu saatler (OKY md.58/2-ç); "
                                       "satıra çift tıklamak da açar.", self.musaitlik_ac)
        self.durum_dugmesi = dugme("Pasife al / Etkinleştir", "", "degistir",
                                   tiklaninca=self.durum_degistir)
        self.sil_dugmesi = dugme("Listeden sil", "tehlike", "sil",
                                 "Görevi olan kişi silinemez, pasife alınır.", self.sil)
        liste.ekle(yatay(self.musaitlik_dugmesi, self.durum_dugmesi, self.sil_dugmesi, 0,
                         dugme("Elle ekle…", "", "ekle", tiklaninca=self.elle_ekle)))
        self.duzen.addWidget(liste, 1)
        self._kipi_ayarla(onizleme=False)

    # ------------------------------------------------------------------ veri
    def goster(self) -> None:
        if self.ozet is None:
            self.listeyi_doldur()

    def listeyi_doldur(self) -> None:
        self.kayitlar = hizmet.personel_ayrintili_liste(self.vt)
        for kisi in self.kayitlar:
            kisi["anahtar"] = kisi["kimlik"]
            kisi["durum_metni"] = f"{'aktif' if kisi['aktif_mi'] else 'pasif'} — {kisi['kaynak']}"
            kisi["musait_metni"] = (f"{kisi['musaitlik_sayisi']} kayıt"
                                    if kisi["musaitlik_sayisi"] else "")
            kisi["zemin"] = None if kisi["aktif_mi"] else RENK["pasif_zemin"]
            kisi["yazi_rengi"] = None if kisi["aktif_mi"] else RENK["soluk"]
        self._branslari_doldur(sorted({k["brans"] for k in self.kayitlar if k["brans"]}))
        self.tablo.yukle(self.kayitlar)
        self._suzgeci_uygula()
        self._dugmeleri_tazele()

    def _branslari_doldur(self, branslar: list[str]) -> None:
        secili = self.brans_suzgeci.currentText()
        self.brans_suzgeci.blockSignals(True)
        self.brans_suzgeci.clear()
        self.brans_suzgeci.addItem("Bütün branşlar")
        self.brans_suzgeci.addItems(branslar)
        if secili in branslar:
            self.brans_suzgeci.setCurrentText(secili)
        self.brans_suzgeci.blockSignals(False)

    def _suzgeci_uygula(self) -> None:
        brans = self.brans_suzgeci.currentText() if self.brans_suzgeci.currentIndex() > 0 else ""
        durum = self.durum_suzgeci.currentIndex()

        def kosul(k: dict) -> bool:
            if brans and k["brans"] != brans:
                return False
            if self.ozet is None and durum == 1 and not k["aktif_mi"]:
                return False
            if self.ozet is None and durum == 2 and k["aktif_mi"]:
                return False
            return True

        self.tablo.kosulu_ayarla(kosul)
        self._sayaci_tazele()

    def _sayaci_tazele(self, *_) -> None:
        gorunen = self.tablo.suzgec.rowCount()
        toplam = self.tablo.model.rowCount()
        self.sayac.setText(f"{gorunen} / {toplam} kişi" if gorunen != toplam else f"{toplam} kişi")

    def _dugmeleri_tazele(self) -> None:
        secim = bool(self.tablo.secili_satirlar())
        liste_kipi = self.ozet is None
        for d in (self.musaitlik_dugmesi, self.durum_dugmesi, self.sil_dugmesi):
            d.setEnabled(secim and liste_kipi)

    # -------------------------------------------------------------- önizleme
    def _kipi_ayarla(self, onizleme: bool) -> None:
        self.onayla_dugmesi.setEnabled(onizleme)
        self.vazgec_dugmesi.setVisible(onizleme)
        self.durum_suzgeci.setEnabled(not onizleme)
        self._dugmeleri_tazele()

    def _durumu_yaz(self, parcalar: list[tuple[str, str]]) -> None:
        while self.durum.count():
            oge = self.durum.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()
        for metin, tur in parcalar:
            self.durum.addWidget(cip(metin, tur))
        self.durum.addStretch(1)

    def rapor_sec(self) -> None:
        yol, _ = QFileDialog.getOpenFileName(self, "e-Okul personel raporu", "",
                                             "e-Okul personel listesi (*.xls *.xlsx)")
        if yol:
            self.raporu_onizle(Path(yol))

    def raporu_onizle(self, yol: Path) -> None:
        self.uyg.mesgul_ac("Personel raporu okunuyor…")
        arka_planda(lambda: hizmet.personel_onizle(self.vt, yol), self._onizleme_geldi,
                    self._onizleme_hatasi)

    def _onizleme_hatasi(self, hata: BaseException) -> None:
        self.uyg.mesgul_kapat()
        if isinstance(hata, (HizmetHatasi, RaporHatasi, OSError, ValueError)):
            self.hata("Personel raporu okunamadı", hata)
        else:
            raise hata

    def _onizleme_geldi(self, ozet) -> None:
        self.uyg.mesgul_kapat()
        self.ozet = ozet
        satirlar = [{"anahtar": sira, "ad": ad, "unvan": unvan, "kadro": kadro, "brans": brans,
                     "durum_metni": ONIZLEME_ADLARI.get(eylem, eylem), "aktif_mi": True,
                     "zemin": ONIZLEME_ZEMINI.get(eylem)}
                    for sira, (ad, unvan, kadro, brans, eylem) in enumerate(ozet.satirlar)]
        self._branslari_doldur(sorted({s["brans"] for s in satirlar if s["brans"]}))
        self.tablo.yukle(satirlar, secimi_koru=False)
        self._suzgeci_uygula()
        self._durumu_yaz([(f"{ozet.toplam} kişi", ""), (f"+{ozet.eklenen} yeni", "basari"),
                          (f"~{ozet.guncellenen} değişen", "uyari"),
                          (f"={ozet.degismedi} aynı", ""),
                          (f"−{ozet.cikan} pasife alınacak", "engel" if ozet.cikan else "")])
        self._kipi_ayarla(onizleme=True)
        logging.info("Personel önizleme: %s satır", ozet.toplam)

    def onizlemeyi_kapat(self) -> None:
        self.ozet = None
        self._durumu_yaz([])
        self._kipi_ayarla(onizleme=False)
        self.listeyi_doldur()

    def onayla(self) -> None:
        if self.ozet is None:
            return
        ozet = self.ozet
        if not self.ileti.soru("Personel listesini güncelle",
                               f"{ozet.eklenen} kişi eklenecek, {ozet.guncellenen} kişi "
                               f"güncellenecek, {ozet.cikan} kişi pasife alınacak.\n\n"
                               "Devam edilsin mi?", "Onayla"):
            return
        try:
            sonuc = hizmet.personel_onayla(self.vt, ozet.aktarim_id)
        except HizmetHatasi as hata:
            self.hata("Onay verilemedi", hata)
            return
        self.onizlemeyi_kapat()
        self.bildir(f"Personel listesi güncellendi: {sonuc.eklenen} eklendi, "
                    f"{sonuc.guncellenen} güncellendi, {sonuc.cikan} pasife alındı.")

    # ------------------------------------------------------------- işlemler
    def musaitlik_ac(self) -> None:
        kisi = self.tablo.secili_satir()
        if kisi is None or self.ozet is not None:
            return
        MusaitlikPenceresi(self.uyg, kisi).exec()
        self.listeyi_doldur()

    def durum_degistir(self) -> None:
        secili = self.tablo.secili_satirlar()
        try:
            for kisi in secili:
                hizmet.personel_durumu_degistir(self.vt, kisi["kimlik"], not kisi["aktif_mi"])
        except HizmetHatasi as hata:
            self.hata("Durum değiştirilemedi", hata)
        self.listeyi_doldur()
        if secili:
            self.bildir(f"{len(secili)} kişinin durumu değiştirildi.")

    def sil(self) -> None:
        secili = self.tablo.secili_satirlar()
        if not secili:
            return
        adlar = ", ".join(k["ad"] for k in secili[:3]) + (" …" if len(secili) > 3 else "")
        if not self.ileti.soru("Personeli sil", f"{adlar} listeden silinecek. Devam edilsin mi?",
                               "Sil", uyari=True):
            return
        silinen = 0
        for kisi in secili:
            try:
                hizmet.personel_sil(self.vt, kisi["kimlik"])
                silinen += 1
            except HizmetHatasi as hata:
                self.hata(f"{kisi['ad']} silinemedi", hata)
        self.listeyi_doldur()
        if silinen:
            self.bildir(f"{silinen} kişi silindi.")

    def elle_ekle(self) -> None:
        pencere = PersonelEklePenceresi(self.uyg)
        if pencere.exec():
            self.listeyi_doldur()
            if pencere.eklenen is not None:
                self.tablo.sec(pencere.eklenen)
            self.bildir("Personel eklendi.")
