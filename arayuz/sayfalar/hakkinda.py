"""10 Hakkında: program bilgisi, güncelleme denetimi ve kullanım koşulları.

Güncelleme paneli kardeş projelerle aynı düzendedir (karar 0015): kurulu ve
yayımlanan son sürüm yan yana gösterilir; Windows'ta kurulum dosyası
doğrulanarak indirilir, Pardus'ta paketle güncelleme yolu tarif edilir.
Kullanıcıya görünen metinde "GitHub", "Release" ya da "kurucu" geçmez.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QTextBrowser, QVBoxLayout

from arayuz import yardim_metni
from arayuz.bilesenler import Kart, Serit, arka_planda, cip, dugme, etiket, yatay
from arayuz.sayfalar.temel import Sayfa
from arayuz.uygulama import acilis_denetimi_acik_mi, kurum_denetimi_kapatmis_mi
from cekirdek.kaynak import varlik_yolu
from cekirdek.surum import SURUM
from veri import guncelleme

MEB_IPUCU = ("Okul ağında GitHub'a erişim kapalı olabilir. Yeni sürümü okulapp.org/sorumluluk-"
             "sinavi adresinden de indirebilirsiniz.")


def _boyut(bayt: int) -> str:
    return f"{bayt / (1024 * 1024):.1f}".replace(".", ",") + " MB" if bayt > 0 else ""


class HakkindaSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.durum: dict[str, Any] | None = None
        self.indirilen: Path | None = None

        ust = Kart(kenar=(18, 16, 18, 16))
        satir = yatay()
        logo = varlik_yolu("logo.png")
        if logo is not None and not QPixmap(str(logo)).isNull():
            resim = QLabel()
            resim.setPixmap(QPixmap(str(logo)).scaled(
                72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            satir.addWidget(resim)
        yazi = QVBoxLayout()
        yazi.setSpacing(2)
        yazi.addWidget(etiket("Sorumluluk Sınavı", "SayfaBaslik"))
        yazi.addWidget(etiket(f"Sürüm {SURUM}", "Soluk"))
        yazi.addWidget(etiket("Ortaöğretim kurumları için çevrimdışı sorumluluk sınavı planlama "
                              "ve görevlendirme uygulaması", sar=True))
        satir.addLayout(yazi, 1)
        ust.ekle(satir)
        self.duzen.addWidget(ust)

        self.duzen.addWidget(self._guncelleme_karti())

        lisans = Kart("Lisans ve kullanım koşulları", kenar=(18, 14, 18, 14))
        metin = QTextBrowser()
        parcalar = []
        for baslik, paragraflar in yardim_metni.LISANS_BOLUMLERI:
            parcalar.append(f"<h3>{baslik}</h3>")
            parcalar += [f"<p>{p}</p>" for p in paragraflar]
        metin.setHtml("".join(parcalar))
        lisans.ekle(metin, 1)
        self.duzen.addWidget(lisans, 1)

    # ------------------------------------------------------------- güncelleme
    def _guncelleme_karti(self) -> Kart:
        kart = Kart("Uygulama güncellemesi",
                    "Yayımlanan son sürüm denetlenir; programın internete çıkan tek isteği "
                    "budur ve kişisel ya da okul verisi taşımaz. Kurulum dosyası, bütünlüğü "
                    "doğrulanmadan indirmeye sunulmaz.", kenar=(18, 14, 18, 14))
        self.denetle_dugmesi = dugme("Şimdi denetle", "", "yenile", tiklaninca=self.denetle)
        self.acilista = QCheckBox("Program açılırken yeni sürümü denetle")
        if kurum_denetimi_kapatmis_mi():
            # Kutu gerçekte olanı gösterir: denetim kapalıdır. Kullanıcının
            # kendi tercihi ayarlarda dokunulmadan kalır.
            self.acilista.setChecked(False)
            self.acilista.setEnabled(False)
            self.acilista.setToolTip("Bu bilgisayarda açılış denetimi kurum ayarıyla "
                                     "kapatılmış (SORUMLULUK_GUNCELLEME_DENETIMI=0).")
        else:
            self.acilista.setChecked(acilis_denetimi_acik_mi(self.uyg.ayarlar))
            self.acilista.toggled.connect(
                lambda d: self.uyg.ayarlar.setValue("guncelleme/acilista_denetle", d))
        kart.ekle(yatay(self.denetle_dugmesi, self.acilista, 0))

        sayilar = QGridLayout()
        self.kurulu = etiket(SURUM, "Deger")
        self.son = etiket("—", "Deger")
        for sutun, (ad, deger) in enumerate((("Kurulu sürüm", self.kurulu),
                                             ("Yayımlanan son sürüm", self.son))):
            kutu = QVBoxLayout()
            kutu.addWidget(etiket(ad, "Soluk"))
            kutu.addWidget(deger)
            sayilar.addLayout(kutu, 0, sutun)
        sayilar.setColumnStretch(2, 1)
        kart.ekle(sayilar)

        self.sonuc = Serit("", "bilgi")
        self.sonuc.hide()
        self.indir_dugmesi = self.sonuc.dugme_ekle("Doğrula ve indir", self.indir)
        self.baslat_dugmesi = self.sonuc.dugme_ekle("Kurulumu başlat", self.kurulumu_baslat)
        self.sayfa_dugmesi = self.sonuc.dugme_ekle("İndirme sayfasını aç", self._indirme_sayfasi)
        kart.ekle(self.sonuc)
        self.durum_cipi = cip("Henüz denetlenmedi.")
        kart.ekle(yatay(self.durum_cipi, 0))
        return kart

    def goster(self) -> None:
        if self.uyg.guncelleme_durumu is not None and self.durum is None:
            self.durumu_goster(self.uyg.guncelleme_durumu)

    def denetle(self) -> None:
        self.denetle_dugmesi.setEnabled(False)
        self.durum_cipi.setText("Denetleniyor…")
        arka_planda(lambda: guncelleme.guncelleme_durumu(zorla=True), self.durumu_goster,
                    self._denetlenemedi)

    def _denetlenemedi(self, hata: BaseException) -> None:
        self.denetle_dugmesi.setEnabled(True)
        self.durum_cipi.setText("Denetlenemedi.")
        if not isinstance(hata, guncelleme.GuncellemeHatasi):
            raise hata
        self.sonuc.ayarla(f"{hata} {MEB_IPUCU}", "engel")
        self._dugmeleri_ayarla(indir=False, baslat=False, sayfa=True)
        self.sonuc.show()

    def durumu_goster(self, durum: dict[str, Any]) -> None:
        self.durum = durum
        self.uyg.guncelleme_durumu = durum
        self.denetle_dugmesi.setEnabled(True)
        self.son.setText(durum["son_surum"])
        self.durum_cipi.setText("Denetlendi.")
        if not durum["guncelleme_var"]:
            self.sonuc.ayarla("Program güncel.", "basari")
            self._dugmeleri_ayarla(indir=False, baslat=False, sayfa=False)
        elif durum["platform"] == "linux":
            self.sonuc.ayarla(
                f"Yeni sürüm hazır: {durum['son_surum']}. Pardus'ta güncelleme paketle yapılır: "
                "yeni sürümün .deb dosyasını indirme sayfasından alıp eski sürümün üzerine kurun. "
                "Verileriniz kurulum klasörünün dışında tutulduğu için korunur.", "bilgi")
            self._dugmeleri_ayarla(indir=False, baslat=False, sayfa=True)
        else:
            boyut = _boyut(durum.get("kurulum_boyutu", 0))
            self.sonuc.ayarla(
                f"Yeni sürüm hazır: {durum['son_surum']}"
                + (f" (kurulum dosyası {boyut})" if boyut else "")
                + ". \"Doğrula ve indir\" dosyayı indirip yayımlanan özetiyle karşılaştırır; "
                  "kurulumu siz başlatırsınız. Verileriniz kurulum klasörünün dışında "
                  "tutulduğu için korunur."
                + ("" if durum["indirilebilir"] else
                   " Bu sürümde Windows kurulum dosyası bulunmuyor."), "bilgi")
            self._dugmeleri_ayarla(indir=durum["indirilebilir"], baslat=False, sayfa=True)
        self.sonuc.show()

    def _dugmeleri_ayarla(self, indir: bool, baslat: bool, sayfa: bool) -> None:
        self.indir_dugmesi.setVisible(indir)
        self.baslat_dugmesi.setVisible(baslat)
        self.sayfa_dugmesi.setVisible(sayfa)

    def indir(self) -> None:
        self.indir_dugmesi.setEnabled(False)
        self.uyg.mesgul_ac("Kurulum dosyası indiriliyor ve doğrulanıyor…")
        arka_planda(guncelleme.son_kurulumu_indir, self._indirildi, self._indirilemedi)

    def _indirilemedi(self, hata: BaseException) -> None:
        self.uyg.mesgul_kapat()
        self.indir_dugmesi.setEnabled(True)
        if not isinstance(hata, guncelleme.GuncellemeHatasi):
            raise hata
        self.sonuc.ayarla(f"{hata} {MEB_IPUCU}", "engel")
        self._dugmeleri_ayarla(indir=True, baslat=False, sayfa=True)

    def _indirildi(self, yol: Path) -> None:
        self.uyg.mesgul_kapat()
        self.indirilen = yol
        self.sonuc.ayarla(f"Kurulum dosyası doğrulanarak indirildi: {yol}. \"Kurulumu başlat\" "
                          "programı kapatır ve kurulumu açar.", "basari")
        self._dugmeleri_ayarla(indir=False, baslat=True, sayfa=False)

    def kurulumu_baslat(self) -> None:
        """Program kapanır, ardından doğrulanmış kurulum dosyası çalıştırılır.

        Önce pencere kapatılır: kaydedilmemiş plan varsa kullanıcıya sorulur ve
        veritabanı açık kalmaz.
        """
        if self.indirilen is None or not self.indirilen.exists():
            return
        if not self.uyg.close():
            return
        if sys.platform.startswith("win"):
            os.startfile(str(self.indirilen))  # noqa: S606 — doğrulanmış yerel dosya

    def _indirme_sayfasi(self) -> None:
        QDesktopServices.openUrl(QUrl(guncelleme.INDIRME_SAYFASI))
