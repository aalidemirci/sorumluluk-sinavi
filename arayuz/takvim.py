"""Sürükle-bırak sınav takvimi (Qt).

Sütunlar gün, satırlar oturum saatidir. Aynı hücrede birden fazla kart
bulunabilir; motor paralel oturuma izin verdiği için bu normaldir. Kart
bırakıldığında taşımayı çağıran katman denetler ve gerekirse geri alır. Kart
sürüklenmeden bırakılırsa bu bir seçimdir; çağıran katman oturumun
ayrıntısını gösterir.

Sonraki oturum saatine taşan uzun uygulama sınavı, sürdüğü hücrelerde kesikli
bir "sürüyor" işaretiyle görünür; Tk sürümünde kart yalnız başladığı satırda
duruyor, devamı boş hücre sanılabiliyordu.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any, Callable

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from arayuz.bilesenler import turu_ayarla

GUN_KISALTMALARI = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")
MIME_TURU = "application/x-sorumluluk-oturum"
SUTUN_GENISLIGI = 188


class OturumKarti(QFrame):
    """Takvimdeki sınav kartı; sürüklenebilir, tıklanınca seçilir."""

    def __init__(self, kart: dict, takvim: "SurukleBirakTakvim"):
        super().__init__()
        self.kart = kart
        self.anahtar = kart["anahtar"]
        self.takvim = takvim
        self.setObjectName("OturumKarti")
        self.setProperty("tur", kart.get("tur", "yazili"))
        self.setProperty("kilitli", bool(kart.get("kilitli")))
        self.setProperty("secili", False)
        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(8, 5, 8, 5)
        duzen.setSpacing(1)
        baslik = QLabel(kart["baslik"] + (" ✓" if kart.get("kilitli") else ""))
        baslik.setObjectName("KartBasligi")
        alt = QLabel(kart.get("alt", ""))
        alt.setObjectName("KartAlti")
        duzen.addWidget(baslik)
        duzen.addWidget(alt)
        self.setToolTip(kart.get("ipucu", kart["baslik"]))
        self.setCursor(Qt.CursorShape.ForbiddenCursor if kart.get("kilitli")
                       else Qt.CursorShape.OpenHandCursor)
        self._bas: QPoint | None = None

    def mousePressEvent(self, olay: QMouseEvent) -> None:  # noqa: N802
        if olay.button() == Qt.MouseButton.LeftButton:
            self._bas = olay.position().toPoint()
        super().mousePressEvent(olay)

    def mouseMoveEvent(self, olay: QMouseEvent) -> None:  # noqa: N802
        if self._bas is None or not (olay.buttons() & Qt.MouseButton.LeftButton):
            return
        if (olay.position().toPoint() - self._bas).manhattanLength() \
                < QApplication.startDragDistance():
            return
        self._bas = None
        veri = QMimeData()
        veri.setData(MIME_TURU, self.anahtar.encode("utf-8"))
        surukle = QDrag(self)
        surukle.setMimeData(veri)
        surukle.setPixmap(self.grab())
        surukle.setHotSpot(olay.position().toPoint())
        surukle.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, olay: QMouseEvent) -> None:  # noqa: N802
        if self._bas is not None and olay.button() == Qt.MouseButton.LeftButton:
            self.takvim.secildi(self.anahtar)
        self._bas = None
        super().mouseReleaseEvent(olay)

    def secili_yap(self, secili: bool) -> None:
        turu_ayarla(self, "secili", secili)


class Hucre(QFrame):
    """Gün × saat hücresi; kartları alt alta dizer, bırakılan kartı kabul eder."""

    def __init__(self, tarih: date, saat: time, takvim: "SurukleBirakTakvim"):
        super().__init__()
        self.tarih, self.saat, self.takvim = tarih, saat, takvim
        self.setObjectName("Hucre")
        self.setProperty("hafta_sonu", tarih.weekday() >= 5)
        self.setProperty("hedef", False)
        self.setAcceptDrops(True)
        self.setMinimumHeight(64)
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(5, 5, 5, 5)
        self.duzen.setSpacing(4)
        self.duzen.addStretch(1)

    def ekle(self, oge: QWidget) -> None:
        self.duzen.insertWidget(self.duzen.count() - 1, oge)

    def dragEnterEvent(self, olay) -> None:  # noqa: N802
        if olay.mimeData().hasFormat(MIME_TURU):
            olay.acceptProposedAction()
            turu_ayarla(self, "hedef", True)

    def dragLeaveEvent(self, olay) -> None:  # noqa: N802
        turu_ayarla(self, "hedef", False)

    def dropEvent(self, olay) -> None:  # noqa: N802
        turu_ayarla(self, "hedef", False)
        anahtar = bytes(olay.mimeData().data(MIME_TURU)).decode("utf-8")
        olay.acceptProposedAction()
        self.takvim.birakildi(anahtar, self.tarih, self.saat)


class SurukleBirakTakvim(QScrollArea):
    """`kartlar`: anahtar, baslik, alt, ipucu, tarih, saat, tur, kilitli,
    suren_saatler (uzun uygulamanın sürdüğü sonraki saatler)."""

    def __init__(self, gunler: list[date], saatler: list[time], kartlar: list[dict],
                 birak_geri_cagirimi: Callable[[str, date, time], Any],
                 sec_geri_cagirimi: Callable[[str], Any] | None = None):
        super().__init__()
        self.gunler, self.saatler, self.kartlar = list(gunler), list(saatler), list(kartlar)
        self._birak, self._sec = birak_geri_cagirimi, sec_geri_cagirimi
        self.secili: str | None = None
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        izgara_kabi = QWidget()
        izgara_kabi.setObjectName("TakvimIzgara")
        izgara = QGridLayout(izgara_kabi)
        izgara.setContentsMargins(0, 0, 4, 4)
        izgara.setHorizontalSpacing(6)
        izgara.setVerticalSpacing(6)
        izgara.setColumnMinimumWidth(0, 56)
        for sutun, gun in enumerate(self.gunler, 1):
            etiket = QLabel(f"{GUN_KISALTMALARI[gun.weekday()]}  {gun.strftime('%d.%m')}")
            etiket.setObjectName("TakvimGun")
            etiket.setAlignment(Qt.AlignmentFlag.AlignCenter)
            turu_ayarla(etiket, "hafta_sonu", gun.weekday() >= 5)
            izgara.addWidget(etiket, 0, sutun)
            izgara.setColumnMinimumWidth(sutun, SUTUN_GENISLIGI)
        self.hucreler: dict[tuple[date, time], Hucre] = {}
        for satir, saat in enumerate(self.saatler, 1):
            etiket = QLabel(saat.strftime("%H:%M"))
            etiket.setObjectName("TakvimSaat")
            etiket.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            izgara.addWidget(etiket, satir, 0)
            for sutun, gun in enumerate(self.gunler, 1):
                hucre = Hucre(gun, saat, self)
                self.hucreler[(gun, saat)] = hucre
                izgara.addWidget(hucre, satir, sutun)
        izgara.setRowStretch(len(self.saatler) + 1, 1)
        izgara.setColumnStretch(len(self.gunler) + 1, 1)

        self.kart_widgetlari: dict[str, OturumKarti] = {}
        for kart in self.kartlar:
            hucre = self.hucreler.get((kart["tarih"], kart["saat"]))
            if hucre is None:
                continue
            widget = OturumKarti(kart, self)
            self.kart_widgetlari[kart["anahtar"]] = widget
            hucre.ekle(widget)
            for saat in kart.get("suren_saatler", ()):
                devam = self.hucreler.get((kart["tarih"], saat))
                if devam is not None:
                    isaret = QLabel(f"↳ {kart['baslik']} sürüyor")
                    isaret.setObjectName("Suren")
                    isaret.setToolTip(kart.get("ipucu", kart["baslik"]))
                    devam.ekle(isaret)
        self.setWidget(izgara_kabi)

    def birakildi(self, anahtar: str, tarih: date, saat: time) -> None:
        self._birak(anahtar, tarih, saat)

    def secildi(self, anahtar: str) -> None:
        self.secimi_goster(anahtar)
        if self._sec is not None:
            self._sec(anahtar)

    def secimi_goster(self, anahtar: str | None) -> None:
        if self.secili in self.kart_widgetlari:
            self.kart_widgetlari[self.secili].secili_yap(False)
        self.secili = anahtar
        if anahtar in self.kart_widgetlari:
            self.kart_widgetlari[anahtar].secili_yap(True)
            self.ensureWidgetVisible(self.kart_widgetlari[anahtar], 40, 40)

    def hucre(self, tarih: date, saat: time) -> Hucre | None:
        return self.hucreler.get((tarih, saat))
