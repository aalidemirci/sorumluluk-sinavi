"""01 Kurum ayarları: okul bilgileri, dönem tarihleri, tatil günleri, yedek."""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from arayuz.bilesenler import (
    Kart, Sutun, Tablo, TarihAlani, cip, dugme, etiket, kaydirilabilir, yatay,
)
from arayuz.sayfalar.temel import Sayfa
from cekirdek.takvim import pencere_adi, tarih_coz, tarih_yaz
from evrak.uretici import birim_adi, ust_idare
from veri import hizmet
from veri.hizmet import HizmetHatasi

AYAR_ALANLARI = (
    ("okul_adi", "Okul adı"),
    ("mudur_adi", "Müdür adı"),
    ("il", "İl"),
    ("ilce", "İlçe"),
    ("ogretim_yili", "Öğretim yılı (ör. 2026-2027)"),
    ("birinci_donem_baslangic", "1. dönem başlangıcı"),
    ("ikinci_donem_baslangic", "2. dönem başlangıcı"),
    ("ikinci_donem_bitis", "2. dönem bitişi"),
    # İsteğe bağlı: evrak anteti ve imza bloğu.
    ("ust_idare", "Antet: üst idare (boşsa ilçeden)"),
    ("duzenleyen_adi", "Düzenleyen adı (isteğe bağlı)"),
    ("duzenleyen_unvani", "Düzenleyen unvanı (ör. Müdür Yardımcısı)"),
)
TARIH_ALANLARI = frozenset(hizmet.DONEM_TARIHLERI)
# Tarih aralığıyla eklenen tatilde gün sınırı: yanlışlıkla yıl seçilmesin.
EN_UZUN_TATIL_GUNU = 40


class KurumSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        icerik = QWidget()
        sutun = QVBoxLayout(icerik)
        sutun.setContentsMargins(0, 0, 8, 0)
        sutun.setSpacing(14)
        sutun.addWidget(self._okul_karti())
        sutun.addWidget(self._tatil_karti(), 1)
        sutun.addWidget(self._yedek_karti())
        self.duzen.addWidget(kaydirilabilir(icerik))

    # ------------------------------------------------------------- okul kartı
    def _okul_karti(self) -> Kart:
        kart = Kart("Okul ve dönem bilgileri",
                    "Sınav pencereleri (Eylül/Şubat/Haziran) bu tarihlerden hesaplanır — "
                    "OKY md.58/2-a. Antet ve düzenleyen bilgisi evrakta kullanılır (Resmî "
                    "Yazışma Yönetmeliği md.10).")
        izgara = QGridLayout()
        izgara.setHorizontalSpacing(14)
        izgara.setVerticalSpacing(8)
        self.girdiler: dict[str, QWidget] = {}
        for sira, (anahtar, ad) in enumerate(AYAR_ALANLARI):
            satir, sutun = sira // 2, (sira % 2) * 2
            girdi: QWidget = (TarihAlani(bos_olabilir=True) if anahtar in TARIH_ALANLARI
                              else QLineEdit())
            izgara.addWidget(QLabel(ad), satir, sutun)
            izgara.addWidget(girdi, satir, sutun + 1)
            self.girdiler[anahtar] = girdi
        izgara.setColumnStretch(1, 1)
        izgara.setColumnStretch(3, 1)
        kart.ekle(izgara)

        self.pencere_cipleri = QHBoxLayout()
        self.pencere_cipleri.setSpacing(8)
        self.antet = etiket("", "Soluk", sar=True)
        kart.ekle(self.pencere_cipleri)
        kart.ekle(self.antet)
        kart.ekle(yatay(0, dugme("Kaydet", "ana", "kaydet", "Ctrl+S", self.kaydet)))
        return kart

    def _okulu_doldur(self) -> None:
        mevcut = hizmet.ayarlari_getir(self.vt)
        for anahtar, girdi in self.girdiler.items():
            deger = mevcut.get(anahtar, "")
            if isinstance(girdi, TarihAlani):
                try:
                    girdi.ayarla(tarih_coz(deger) if deger else None)
                except ValueError:
                    girdi.ayarla(None)
            else:
                girdi.setText(deger)
        antet = mevcut.get("ust_idare") or ust_idare(mevcut.get("il", ""), mevcut.get("ilce", ""))
        self.antet.setText(f"Evrak anteti: T.C. / {antet} / {birim_adi(mevcut.get('okul_adi', ''))}"
                           if antet else "")
        self._pencereleri_goster()

    def _pencereleri_goster(self) -> None:
        while self.pencere_cipleri.count():
            oge = self.pencere_cipleri.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()
        try:
            pencereler = hizmet.pencereleri_getir(self.vt)
        except HizmetHatasi:
            self.pencere_cipleri.addWidget(
                cip("Tarihler kaydedilince sınav pencereleri burada görünür.", "uyari"))
            self.pencere_cipleri.addStretch(1)
            return
        self.pencere_cipleri.addWidget(etiket("Sınav pencereleri", "Soluk"))
        for kod, (bas, bit) in pencereler.items():
            self.pencere_cipleri.addWidget(
                cip(f"{pencere_adi(kod)}: {tarih_yaz(bas)} – {tarih_yaz(bit)}"))
        self.pencere_cipleri.addStretch(1)

    def kaydet(self) -> None:
        degerler = {}
        for anahtar, girdi in self.girdiler.items():
            if isinstance(girdi, TarihAlani):
                deger = girdi.tarih()
                degerler[anahtar] = tarih_yaz(deger) if deger else ""
            else:
                degerler[anahtar] = girdi.text()
        try:
            hizmet.ayarlari_kaydet(self.vt, degerler)
        except HizmetHatasi as hata:
            self.hata("Kurum ayarları kaydedilemedi", hata)
            return
        self._okulu_doldur()
        self.bildir("Kurum ayarları kaydedildi.")

    kisayol_kaydet = kaydet

    # ------------------------------------------------------------ tatil kartı
    def _tatil_karti(self) -> Kart:
        kart = Kart("Tatil ve idari izin günleri",
                    "Plan bu günlere sınav koymaz; başvurudaki 5 iş günü ve evrak teslim süresi "
                    "bu günleri iş günü saymaz (SP-08). Sınav penceresine düşenler özellikle "
                    "önemlidir. Birden çok günü bitiş tarihiyle bir kerede ekleyebilirsiniz.")
        self.tatil_tablosu = Tablo(
            [Sutun("Tarih", lambda t: tarih_yaz(t["tarih"]), 120, siralama=lambda t: t["tarih"]),
             Sutun("Gün", lambda t: hizmet.HAFTA_GUNLERI[t["tarih"].weekday()], 120),
             Sutun("Açıklama", lambda t: t["aciklama"], uzat=True)],
            anahtar=lambda t: t["kimlik"], coklu_secim=True,
            bos_metin="Henüz tatil günü girilmedi.")
        self.tatil_tablosu.setMinimumHeight(190)
        kart.ekle(self.tatil_tablosu, 1)
        self.tatil_bas = TarihAlani()
        self.tatil_bit = TarihAlani(bos_olabilir=True)
        self.tatil_aciklama = QLineEdit()
        self.tatil_aciklama.setPlaceholderText("Açıklama (ör. Cumhuriyet Bayramı)")
        self.tatil_aciklama.returnPressed.connect(self._tatil_ekle)
        kart.ekle(yatay(QLabel("Tarih"), self.tatil_bas, QLabel("Bitiş (isteğe bağlı)"),
                        self.tatil_bit, self.tatil_aciklama,
                        dugme("Ekle", "", "ekle", tiklaninca=self._tatil_ekle),
                        dugme("Seçilenleri sil", "tehlike", "sil", tiklaninca=self._tatil_sil)))
        return kart

    def _tatilleri_doldur(self) -> None:
        self.tatil_tablosu.yukle(hizmet.tatil_listesi(self.vt))

    def _tatil_ekle(self) -> None:
        bas, bit = self.tatil_bas.tarih(), self.tatil_bit.tarih() or self.tatil_bas.tarih()
        try:
            if bit < bas:
                raise HizmetHatasi("Bitiş tarihi başlangıçtan önce olamaz.")
            if (bit - bas).days >= EN_UZUN_TATIL_GUNU:
                raise HizmetHatasi(f"Bir kerede en çok {EN_UZUN_TATIL_GUNU} gün eklenebilir.")
            mevcut = hizmet.tatilleri_getir(self.vt)
            eklenen = 0
            gun = bas
            while gun <= bit:
                if gun not in mevcut:
                    hizmet.tatil_ekle(self.vt, gun, self.tatil_aciklama.text())
                    eklenen += 1
                gun += timedelta(days=1)
        except (HizmetHatasi, ValueError) as hata:
            self.hata("Tatil eklenemedi", hata)
            return
        self.tatil_aciklama.clear()
        self.tatil_bit.ayarla(None)
        self._tatilleri_doldur()
        self.bildir(f"{eklenen} tatil günü eklendi." if eklenen else "Bu günler zaten kayıtlı.")

    def _tatil_sil(self) -> None:
        secili = self.tatil_tablosu.secili_satirlar()
        if not secili:
            self.ileti.uyari("Seçim yok", "Silinecek günleri tablodan seçin.")
            return
        for tatil in secili:
            hizmet.tatil_sil(self.vt, tatil["kimlik"])
        self._tatilleri_doldur()
        self.bildir(f"{len(secili)} tatil günü silindi.")

    # ------------------------------------------------------------- yedek kartı
    def _yedek_karti(self) -> Kart:
        kart = Kart("Veri ve yedek",
                    "Veritabanı bu bilgisayardadır. Yedeği kurumun yedek ortamında saklayın; "
                    "e-posta, kişisel bulut ya da herkese açık depoya koymayın.")
        self.klasor_etiketi = etiket(f"Veri klasörü: {self.vt.yol.parent}", "Soluk")
        kart.ekle(yatay(self.klasor_etiketi, 0,
                        dugme("Klasörü aç", "", "klasor", tiklaninca=self._klasoru_ac),
                        dugme("Yedek al…", "", "indir", tiklaninca=self._yedekle)))
        return kart

    def _klasoru_ac(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.vt.yol.parent)))

    def _yedekle(self) -> None:
        son = str(self.uyg.ayarlar.value("yedek/son_klasor", str(Path.home())))
        klasor = QFileDialog.getExistingDirectory(self, "Yedeğin yazılacağı klasör", son)
        if not klasor:
            return
        try:
            yol = hizmet.yedek_al(self.vt, Path(klasor))
        except (OSError, sqlite3.Error) as hata:
            self.hata("Yedek alınamadı", hata)
            return
        self.uyg.ayarlar.setValue("yedek/son_klasor", klasor)
        self.ileti.bilgi("Yedek alındı", f"Veritabanının tam yedeği alındı:\n{yol}\n\n"
                         "Yedeği kurumun yedek ortamında saklayın; e-posta, kişisel bulut veya "
                         "herkese açık depoya koymayın.")

    # ------------------------------------------------------------------ genel
    def goster(self) -> None:
        self._okulu_doldur()
        self._tatilleri_doldur()


__all__ = ["KurumSayfasi"]
