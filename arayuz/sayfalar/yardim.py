"""09 Yardım: mevzuat hükümleri, kullanım ve çalışma mantığı.

Metin `arayuz.yardim_metni` içindedir. Sol listede bölümler, sağda metin
durur; arama yalnız eşleşen bölümleri gösterir ve sözcükleri işaretler.
"""

from __future__ import annotations

import html
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QSplitter, QTextBrowser

from arayuz import yardim_metni
from arayuz.bilesenler import AramaKutusu, Kart
from arayuz.palet import RENK
from arayuz.sayfalar.temel import Sayfa
from cekirdek.metin import arama_anahtari


# Katlanmış arama harfinin özgün metindeki karşılıkları (vurgulama için).
_ESNEK = {"c": "[cçCÇ]", "g": "[gğGĞ]", "i": "[iıİI]", "o": "[oöOÖ]", "s": "[sşSŞ]",
          "u": "[uüUÜ]", "a": "[aâAÂ]"}


def _esnek_desen(sozcuk: str) -> str:
    return "".join(_ESNEK.get(harf, re.escape(harf)) for harf in sozcuk)


def bolumleri_html(bolumler, sozcukler: list[str]) -> str:
    """Bölümleri HTML'e çevirir; sözcük verilirse yalnız eşleşen bölümler kalır."""
    parcalar = [f"<p style='color:{RENK['soluk']}'>Sorumluluk sınavlarına ilişkin mevzuat "
                "hükümleri, programın kullanımı ve çalışma mantığı.</p>"]
    desen = (re.compile("|".join(_esnek_desen(s) for s in sozcukler), re.IGNORECASE)
             if sozcukler else None)

    def isaretle(metin: str) -> str:
        guvenli = html.escape(metin)
        if desen is None:
            return guvenli
        return desen.sub(lambda e: f"<span style='background:{RENK['takvim_hedef']}'>"
                                   f"{e.group(0)}</span>", guvenli)

    gosterilen = 0
    for sira, (baslik, paragraflar) in enumerate(bolumler):
        if sozcukler:
            butun = arama_anahtari(baslik + " " + " ".join(paragraflar))
            if not all(s in butun for s in sozcukler):
                continue
        gosterilen += 1
        parcalar.append(f"<h2 id='b{sira}' style='color:{RENK['kenar']}; margin-top:18px'>"
                        f"{isaretle(baslik)}</h2>")
        for paragraf in paragraflar:
            if paragraf.startswith("•"):
                parcalar.append(f"<p style='margin-left:18px'>{isaretle(paragraf)}</p>")
            else:
                parcalar.append(f"<p>{isaretle(paragraf)}</p>")
    if sozcukler and not gosterilen:
        parcalar.append("<p><i>Aranan sözcükleri içeren bölüm bulunamadı.</i></p>")
    return "<html><body style='line-height:145%'>" + "".join(parcalar) + "</body></html>"


class YardimSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        sol = Kart("İçindekiler", kenar=(14, 12, 14, 12))
        self.arama_kutusu = AramaKutusu("Yardımda ara…")
        self.arama_kutusu.setMinimumWidth(200)
        self.arama_kutusu.degisti.connect(self._ara)
        sol.ekle(self.arama_kutusu)
        self.liste = QListWidget()
        for baslik, _ in yardim_metni.BOLUMLER:
            self.liste.addItem(baslik)
        self.liste.currentRowChanged.connect(self._bolume_git)
        sol.ekle(self.liste, 1)
        sol.setMinimumWidth(240)
        sol.setMaximumWidth(320)

        self.metin = QTextBrowser()
        self.metin.setOpenExternalLinks(False)
        sag = Kart(kenar=(10, 10, 10, 10))
        sag.ekle(self.metin, 1)
        bolme = QSplitter(Qt.Orientation.Horizontal)
        bolme.setChildrenCollapsible(False)
        bolme.addWidget(sol)
        bolme.addWidget(sag)
        bolme.setStretchFactor(1, 1)
        self.duzen.addWidget(bolme, 1)
        self._ara("")

    def _ara(self, metin: str) -> None:
        sozcukler = arama_anahtari(metin).split()
        self.metin.setHtml(bolumleri_html(yardim_metni.BOLUMLER, sozcukler))
        for sira, (baslik, paragraflar) in enumerate(yardim_metni.BOLUMLER):
            butun = arama_anahtari(baslik + " " + " ".join(paragraflar))
            self.liste.item(sira).setHidden(bool(sozcukler)
                                            and not all(s in butun for s in sozcukler))

    def _bolume_git(self, sira: int) -> None:
        if sira >= 0:
            self.metin.scrollToAnchor(f"b{sira}")
