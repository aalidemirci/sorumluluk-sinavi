"""Ekranların ortak bileşenleri.

Tk sürümünde her ekran tablosunu, düğmesini ve iletisini kendisi kuruyordu;
arama, sıralama ve "kaydettikten sonra seçim korunsun" gibi davranışlar hiçbir
ekranda yoktu. Burada bir kez yazılır, bütün ekranlar aynısını kullanır:

* `Tablo`: Türkçe sıralama (ç, ğ, ı, ö, ş, ü doğru yerde), Türkçe büyük/küçük
  harf duyarsız arama, yeniden yüklemede seçimin korunması, onay kutusu
  sütunları, boş durum yazısı.
* `Bildirim`: başarılı işlem için kendiliğinden kapanan şerit. Tk sürümünde
  her kayıt bir ileti kutusu açıyor, "Tamam"a basmak gerekiyordu.
* `arka_planda`: uzun işi (plan üretimi, rapor okuma, evrak) arayüzü
  dondurmadan yürütür.
* `Iletisim`: düğmeleri Türkçe ileti kutuları. Qt'nin standart düğmeleri
  çeviri dosyası olmadan İngilizce çıkar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Callable

from PySide6.QtCore import (
    QAbstractTableModel, QDate, QEvent, QModelIndex, QObject, QPoint, QRect, QRunnable,
    QSize, QSortFilterProxyModel, Qt, QThreadPool, QTimer, Signal,
)
from PySide6.QtGui import QAction, QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QFrame, QHBoxLayout, QHeaderView, QInputDialog,
    QLabel, QLayout, QLayoutItem, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QTableView, QVBoxLayout, QWidget,
)

from arayuz.palet import RENK
from arayuz.simgeler import simge
from cekirdek.metin import arama_anahtari, siralama_anahtari
from veri.hizmet import HizmetHatasi

ANAHTAR_ROLU = Qt.ItemDataRole.UserRole
NESNE_ROLU = Qt.ItemDataRole.UserRole + 1


# ================================================================ küçük yapı taşları

def dugme(metin: str, tur: str = "", simge_adi: str | None = None, ipucu: str = "",
          tiklaninca: Callable[[], Any] | None = None) -> QPushButton:
    """`tur`: "ana" (sayfanın asıl eylemi), "tehlike" (silme), "metin" (bağlantı
    gibi), "" (ikincil). Biçim stil sayfasındadır."""
    d = QPushButton(metin)
    if tur:
        d.setProperty("tur", tur)
    if simge_adi:
        renk = {"ana": RENK["vurgu_yazi"], "tehlike": RENK["engel"],
                "metin": RENK["bag"]}.get(tur, RENK["yazi"])
        d.setIcon(simge(simge_adi, renk))
        d.setIconSize(QSize(16, 16))
    if ipucu:
        d.setToolTip(ipucu)
    d.setCursor(Qt.CursorShape.PointingHandCursor)
    if tiklaninca is not None:
        d.clicked.connect(lambda _=False: tiklaninca())
    return d


def secim_kutusu(ogeler: list[str] | tuple[str, ...] = (), en_az: int = 10) -> QComboBox:
    """İçeriğe göre genişleyen açılır kutu; dolduruldukça daralıp metni kesmez."""
    kutu = QComboBox()
    kutu.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
    kutu.setMinimumContentsLength(en_az)
    kutu.addItems(list(ogeler))
    return kutu


def etiket(metin: str = "", ad: str = "", sar: bool = False) -> QLabel:
    e = QLabel(metin)
    if ad:
        e.setObjectName(ad)
    if sar:
        e.setWordWrap(True)
    e.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return e


def cip(metin: str = "", tur: str = "") -> QLabel:
    e = QLabel(metin)
    e.setObjectName("Cip")
    e.setProperty("tur", tur)
    return e


def turu_ayarla(widget: QWidget, ozellik: str, deger: Any) -> None:
    """Stil sayfasının okuduğu özelliği değiştirip görünümü tazeler."""
    widget.setProperty(ozellik, deger)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def yatay(*ogeler: QWidget | int | None, bosluk: int = 8) -> QHBoxLayout:
    """Sırayla yerleştirir; `0` esnek boşluktur, `None` atlanır."""
    duzen = QHBoxLayout()
    duzen.setContentsMargins(0, 0, 0, 0)
    duzen.setSpacing(bosluk)
    for oge in ogeler:
        if oge is None:
            continue
        if isinstance(oge, int) and not isinstance(oge, bool):
            duzen.addStretch(1)
        else:
            duzen.addWidget(oge)
    return duzen


class Kart(QFrame):
    """Başlıklı, kenarlıklı yüzey; içerik `duzen`e eklenir."""

    def __init__(self, baslik: str = "", aciklama: str = "", parent: QWidget | None = None,
                 kenar: tuple[int, int, int, int] = (18, 16, 18, 16)):
        super().__init__(parent)
        self.setObjectName("Kart")
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(*kenar)
        self.duzen.setSpacing(10)
        self.baslik_etiketi = etiket(baslik, "KartBaslik") if baslik else None
        if self.baslik_etiketi:
            self.duzen.addWidget(self.baslik_etiketi)
        self.aciklama_etiketi = etiket(aciklama, "KartAlt", sar=True) if aciklama else None
        if self.aciklama_etiketi:
            self.duzen.addWidget(self.aciklama_etiketi)

    def ekle(self, oge: QWidget | QLayout, uzat: int = 0) -> None:
        if isinstance(oge, QLayout):
            self.duzen.addLayout(oge, uzat)
        else:
            self.duzen.addWidget(oge, uzat)


class Serit(QFrame):
    """Sayfa içi bilgi/uyarı şeridi. `tur`: bilgi, uyari, engel, basari."""

    kapandi = Signal()
    SIMGE = {"bilgi": ("bilgi", "bag"), "uyari": ("uyari", "uyari"),
             "engel": ("hata", "engel"), "basari": ("basari", "basari")}

    def __init__(self, metin: str = "", tur: str = "bilgi", kapatilabilir: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Serit")
        self._simge = QLabel()
        self._simge.setFixedSize(20, 20)
        self.metin = etiket(metin, sar=True)
        self.metin.setTextFormat(Qt.TextFormat.PlainText)
        self.dugmeler = QHBoxLayout()
        self.dugmeler.setSpacing(6)
        duzen = QHBoxLayout(self)
        duzen.setContentsMargins(14, 10, 10, 10)
        duzen.setSpacing(10)
        duzen.addWidget(self._simge, 0, Qt.AlignmentFlag.AlignTop)
        duzen.addWidget(self.metin, 1)
        duzen.addLayout(self.dugmeler)
        if kapatilabilir:
            kapat = dugme("", "metin", "kapat", "Kapat", self._kapat)
            kapat.setFixedWidth(30)
            duzen.addWidget(kapat, 0, Qt.AlignmentFlag.AlignTop)
        self.turu_ayarla(tur)

    def turu_ayarla(self, tur: str) -> None:
        ad, renk = self.SIMGE.get(tur, self.SIMGE["bilgi"])
        self._simge.setPixmap(simge(ad, RENK[renk], 20).pixmap(20, 20))
        turu_ayarla(self, "tur", tur)

    def ayarla(self, metin: str, tur: str | None = None) -> None:
        self.metin.setText(metin)
        if tur:
            self.turu_ayarla(tur)
        self.setVisible(bool(metin))

    def dugme_ekle(self, metin: str, tiklaninca: Callable[[], Any]) -> QPushButton:
        d = dugme(metin, "serit", tiklaninca=tiklaninca)
        self.dugmeler.addWidget(d)
        return d

    def _kapat(self) -> None:
        self.hide()
        self.kapandi.emit()


class AkisDuzeni(QLayout):
    """Öğeleri satıra sığdığı kadar dizer, sığmayanı alt satıra alır.

    Plan parametreleri ve süzgeç çubukları dar ekranda (1366 px) tek satıra
    sığmaz; Tk sürümünde taşan öğe görünmez oluyordu.
    """

    def __init__(self, parent: QWidget | None = None, bosluk: int = 10):
        super().__init__(parent)
        self._ogeler: list[QLayoutItem] = []
        self.setContentsMargins(0, 0, 0, 0)
        self._bosluk = bosluk

    def addItem(self, oge: QLayoutItem) -> None:  # noqa: N802 (Qt adı)
        self._ogeler.append(oge)

    def count(self) -> int:
        return len(self._ogeler)

    def itemAt(self, sira: int) -> QLayoutItem | None:  # noqa: N802
        return self._ogeler[sira] if 0 <= sira < len(self._ogeler) else None

    def takeAt(self, sira: int) -> QLayoutItem | None:  # noqa: N802
        return self._ogeler.pop(sira) if 0 <= sira < len(self._ogeler) else None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, genislik: int) -> int:  # noqa: N802
        return self._yerlestir(QRect(0, 0, genislik, 0), sadece_olc=True)

    def setGeometry(self, alan: QRect) -> None:  # noqa: N802
        super().setGeometry(alan)
        self._yerlestir(alan, sadece_olc=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        boyut = QSize()
        for oge in self._ogeler:
            boyut = boyut.expandedTo(oge.minimumSize())
        return boyut

    def _yerlestir(self, alan: QRect, sadece_olc: bool) -> int:
        x, y, satir_yuksekligi = alan.x(), alan.y(), 0
        for oge in self._ogeler:
            # isHidden: yalnız açıkça gizlenen atlanır; henüz gösterilmemiş
            # pencerede isVisible hep False döner ve ölçüm sıfır çıkardı.
            if oge.widget() is not None and oge.widget().isHidden():
                continue
            boyut = oge.sizeHint()
            sonraki = x + boyut.width() + self._bosluk
            if sonraki - self._bosluk > alan.right() and satir_yuksekligi > 0:
                x = alan.x()
                y += satir_yuksekligi + self._bosluk
                sonraki = x + boyut.width() + self._bosluk
                satir_yuksekligi = 0
            if not sadece_olc:
                oge.setGeometry(QRect(QPoint(x, y), boyut))
            x = sonraki
            satir_yuksekligi = max(satir_yuksekligi, boyut.height())
        return y + satir_yuksekligi - alan.y()


def akis(*ogeler: QWidget, bosluk: int = 10) -> QWidget:
    """Öğeleri akış düzeninde taşıyan kap."""
    kap = QWidget()
    duzen = AkisDuzeni(kap, bosluk)
    for oge in ogeler:
        duzen.addWidget(oge)
    return kap


def etiketli(metin: str, oge: QWidget) -> QWidget:
    """Etiket ve denetimi tek parça yapar; akış düzeninde birlikte kayarlar."""
    kap = QWidget()
    duzen = QHBoxLayout(kap)
    duzen.setContentsMargins(0, 0, 0, 0)
    duzen.setSpacing(6)
    duzen.addWidget(QLabel(metin))
    duzen.addWidget(oge)
    return kap


# ================================================================== girdiler

class AramaKutusu(QLineEdit):
    """Türkçe harf duyarsız arama; yazarken kısa gecikmeyle `degisti` yayar."""

    degisti = Signal(str)

    def __init__(self, yer_tutucu: str = "Ara…", parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText(yer_tutucu)
        self.setClearButtonEnabled(True)
        self.addAction(QAction(simge("ara", RENK["soluk"], 16), "", self),
                       QLineEdit.ActionPosition.LeadingPosition)
        self.setMinimumWidth(220)
        self._zamanlayici = QTimer(self, singleShot=True, interval=150)
        self._zamanlayici.timeout.connect(lambda: self.degisti.emit(self.text()))
        self.textChanged.connect(lambda _m: self._zamanlayici.start())


class TarihAlani(QDateEdit):
    """gg.aa.yyyy biçimli tarih; takvim açılır. `bos_olabilir` ise boş bırakılabilir.

    Tk sürümünde tarih serbest metindi; yanlış yazılan tarih ancak kaydederken
    fark ediliyordu.
    """

    BOS = QDate(2000, 1, 1)

    def __init__(self, deger: date | None = None, bos_olabilir: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.bos_olabilir = bos_olabilir
        self.setCalendarPopup(True)
        self.setDisplayFormat("dd.MM.yyyy")
        takvim = self.calendarWidget()
        takvim.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        takvim.setVerticalHeaderFormat(takvim.VerticalHeaderFormat.NoVerticalHeader)
        takvim.installEventFilter(self)
        if bos_olabilir:
            self.setMinimumDate(self.BOS)
            self.setSpecialValueText(" ")
            self.setToolTip("Boşaltmak için Delete tuşuna basın.")
        self.setMinimumWidth(130)
        self.ayarla(deger if deger is not None or bos_olabilir else date.today())

    def eventFilter(self, nesne: QObject, olay: QEvent) -> bool:  # noqa: N802
        # Boş alanın takvimi 2000 yılında açılmasın.
        if olay.type() == QEvent.Type.Show and self.date() == self.BOS:
            bugun = QDate.currentDate()
            self.calendarWidget().setCurrentPage(bugun.year(), bugun.month())
        return super().eventFilter(nesne, olay)

    def keyPressEvent(self, olay: QKeyEvent) -> None:  # noqa: N802
        if self.bos_olabilir and olay.key() == Qt.Key.Key_Delete:
            self.ayarla(None)
            return
        super().keyPressEvent(olay)

    def tarih(self) -> date | None:
        q = self.date()
        if self.bos_olabilir and q == self.BOS:
            return None
        return date(q.year(), q.month(), q.day())

    def ayarla(self, deger: date | None) -> None:
        if deger is None:
            self.setDate(self.BOS if self.bos_olabilir else QDate.currentDate())
        else:
            self.setDate(QDate(deger.year, deger.month, deger.day))


def saat_coz(metin: str) -> time | None:
    """Boş metin "bütün gün" demektir ve None döner."""
    metin = str(metin or "").strip()
    if not metin:
        return None
    try:
        return datetime.strptime(metin, "%H:%M").time()
    except ValueError as hata:
        raise HizmetHatasi(f"'{metin}' geçerli bir saat değil; SS:DD yazın (ör. 08:30).") from hata


class SaatAlani(QLineEdit):
    """SS:DD biçimli, boş bırakılabilir saat."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("SS:DD")
        self.setMaxLength(5)
        self.setFixedWidth(80)

    def saat(self) -> time | None:
        return saat_coz(self.text())


# ===================================================================== tablo

@dataclass(frozen=True)
class Sutun:
    """Tablo sütunu. `onay` verilirse sütun onay kutusudur ve tıklanınca
    `Tablo.onay_degisti` yayılır; değeri sayfa kaydedip satırı tazeler."""

    baslik: str
    deger: Callable[[Any], Any]
    genislik: int = 120
    hiza: str = "sol"
    onay: Callable[[Any], bool] | None = None
    siralama: Callable[[Any], Any] | None = None
    ipucu: Callable[[Any], str] | None = None
    uzat: bool = False


def _siralama_degeri(deger: Any) -> tuple:
    """Sayılar sayı, metin Türk alfabesiyle; demet bileşik anahtardır."""
    if isinstance(deger, tuple):
        return (0, tuple(_siralama_degeri(oge) for oge in deger))
    if deger is None or deger == "":
        return (2,)
    if isinstance(deger, bool):
        return (0, int(deger))
    if isinstance(deger, (int, float)):
        return (0, deger)
    if isinstance(deger, (date, time)):
        return (0, deger.isoformat())
    metin = str(deger)
    if re.fullmatch(r"\d{1,9}", metin):
        return (0, int(metin))
    return (1, siralama_anahtari(metin))


class SatirModeli(QAbstractTableModel):
    onay_degisti = Signal(object, int, bool)

    HIZA = {"sol": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "sag": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "orta": Qt.AlignmentFlag.AlignCenter}

    def __init__(self, sutunlar: list[Sutun], anahtar: Callable[[Any], Any] | None = None,
                 zemin: Callable[[Any], str | None] | None = None,
                 yazi_rengi: Callable[[Any], str | None] | None = None,
                 kalin: Callable[[Any], bool] | None = None,
                 arama_eki: Callable[[Any], str] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.sutunlar = sutunlar
        self.anahtar = anahtar or (lambda s: id(s))
        self.zemin, self.yazi_rengi, self.kalin = zemin, yazi_rengi, kalin
        self.arama_eki = arama_eki
        self.satirlar: list[Any] = []
        self._arama: list[str] = []

    def _arama_metni(self, satir: Any) -> str:
        parcalar = [str(s.deger(satir) or "") for s in self.sutunlar if s.onay is None]
        if self.arama_eki:
            parcalar.append(self.arama_eki(satir))
        return arama_anahtari(" ".join(parcalar))

    def yukle(self, satirlar: list[Any]) -> None:
        self.beginResetModel()
        self.satirlar = list(satirlar)
        self._arama = [self._arama_metni(s) for s in self.satirlar]
        self.endResetModel()

    def satir(self, sira: int) -> Any:
        return self.satirlar[sira]

    def arama_metni(self, sira: int) -> str:
        return self._arama[sira]

    def sira_bul(self, anahtar: Any) -> int | None:
        return next((i for i, s in enumerate(self.satirlar) if self.anahtar(s) == anahtar), None)

    def guncelle(self, yeni: Any) -> None:
        """Satırı anahtarına göre değiştirir; seçim ve kaydırma korunur."""
        sira = self.sira_bul(self.anahtar(yeni))
        if sira is None:
            return
        self.satirlar[sira] = yeni
        self._arama[sira] = self._arama_metni(yeni)
        self.dataChanged.emit(self.index(sira, 0), self.index(sira, len(self.sutunlar) - 1))

    def siralama_anahtari(self, indeks: QModelIndex) -> tuple:
        sutun = self.sutunlar[indeks.column()]
        satir = self.satirlar[indeks.row()]
        if sutun.siralama is not None:
            return _siralama_degeri(sutun.siralama(satir))
        if sutun.onay is not None:
            return (0, int(sutun.onay(satir)))
        return _siralama_degeri(sutun.deger(satir))

    # --- Qt arabirimi
    def rowCount(self, ust: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if ust.isValid() else len(self.satirlar)

    def columnCount(self, ust: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if ust.isValid() else len(self.sutunlar)

    def data(self, indeks: QModelIndex, rol: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not indeks.isValid():
            return None
        satir = self.satirlar[indeks.row()]
        sutun = self.sutunlar[indeks.column()]
        if rol == Qt.ItemDataRole.DisplayRole:
            if sutun.onay is not None:
                return None
            deger = sutun.deger(satir)
            return "" if deger is None else str(deger)
        if rol == Qt.ItemDataRole.CheckStateRole and sutun.onay is not None:
            return Qt.CheckState.Checked if sutun.onay(satir) else Qt.CheckState.Unchecked
        if rol == Qt.ItemDataRole.TextAlignmentRole:
            return self.HIZA.get(sutun.hiza, self.HIZA["sol"])
        if rol == Qt.ItemDataRole.BackgroundRole and self.zemin:
            renk = self.zemin(satir)
            return QColor(renk) if renk else None
        if rol == Qt.ItemDataRole.ForegroundRole and self.yazi_rengi:
            renk = self.yazi_rengi(satir)
            return QColor(renk) if renk else None
        if rol == Qt.ItemDataRole.FontRole and self.kalin and self.kalin(satir):
            yazi = QFont()
            yazi.setBold(True)
            return yazi
        if rol == Qt.ItemDataRole.ToolTipRole:
            if sutun.ipucu:
                return sutun.ipucu(satir) or None
            if sutun.onay is None:
                deger = sutun.deger(satir)
                return str(deger) if deger not in (None, "") and len(str(deger)) > 28 else None
        if rol == ANAHTAR_ROLU:
            return self.anahtar(satir)
        if rol == NESNE_ROLU:
            return satir
        return None

    def flags(self, indeks: QModelIndex) -> Qt.ItemFlag:
        bayrak = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if indeks.isValid() and self.sutunlar[indeks.column()].onay is not None:
            bayrak |= Qt.ItemFlag.ItemIsUserCheckable
        return bayrak

    def setData(self, indeks: QModelIndex, deger: Any, rol: int = Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if rol == Qt.ItemDataRole.CheckStateRole and indeks.isValid():
            secili = Qt.CheckState(deger) == Qt.CheckState.Checked
            self.onay_degisti.emit(self.satirlar[indeks.row()], indeks.column(), secili)
        # Model kendi kendine değişmez: sayfa kaydedip `guncelle` çağırır;
        # kayıt başarısızsa kutu eski hâlinde kalır.
        return False

    def headerData(self, bolum: int, yon: Qt.Orientation,  # noqa: N802
                   rol: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if yon == Qt.Orientation.Horizontal and rol == Qt.ItemDataRole.DisplayRole:
            return self.sutunlar[bolum].baslik
        if yon == Qt.Orientation.Horizontal and rol == Qt.ItemDataRole.TextAlignmentRole:
            return self.HIZA.get(self.sutunlar[bolum].hiza, self.HIZA["sol"])
        return None


class SuzgecModeli(QSortFilterProxyModel):
    """Arama (bütün sözcükler geçmeli) ve isteğe bağlı satır koşulu."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._sozcukler: list[str] = []
        self._kosul: Callable[[Any], bool] | None = None

    def aramayi_ayarla(self, metin: str) -> None:
        # Qt 6.9'dan beri durum, begin/endFilterChange arasında değiştirilir;
        # invalidateRowsFilter kullanımdan kalktı.
        self.beginFilterChange()
        self._sozcukler = arama_anahtari(metin).split()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def kosulu_ayarla(self, kosul: Callable[[Any], bool] | None) -> None:
        self.beginFilterChange()
        self._kosul = kosul
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, sira: int, ust: QModelIndex) -> bool:  # noqa: N802
        model: SatirModeli = self.sourceModel()
        if self._kosul is not None and not self._kosul(model.satir(sira)):
            return False
        if self._sozcukler:
            metin = model.arama_metni(sira)
            return all(sozcuk in metin for sozcuk in self._sozcukler)
        return True

    def lessThan(self, sol: QModelIndex, sag: QModelIndex) -> bool:  # noqa: N802
        model: SatirModeli = self.sourceModel()
        return model.siralama_anahtari(sol) < model.siralama_anahtari(sag)


# Sütun genişlikleri tasarım genişliğidir. Tablo daha darsa (1366×768 ekran,
# %150 ölçek) sabit sütunlar orantılı daralır ve uzayan sütuna en az
# UZAYAN_EN_AZ kalır; yoksa son sütunlar ancak yatay kaydırmayla görünüyordu.
UZAYAN_EN_AZ = 110
SUTUN_EN_DAR = 48


class Tablo(QWidget):
    """Arama, Türkçe sıralama ve seçim koruması olan tablo."""

    secim_degisti = Signal()
    cift_tiklandi = Signal(object)
    onay_degisti = Signal(object, int, bool)

    def __init__(self, sutunlar: list[Sutun], anahtar: Callable[[Any], Any] | None = None, *,
                 zemin: Callable[[Any], str | None] | None = None,
                 yazi_rengi: Callable[[Any], str | None] | None = None,
                 kalin: Callable[[Any], bool] | None = None,
                 arama_eki: Callable[[Any], str] | None = None,
                 bos_metin: str = "Kayıt yok.", coklu_secim: bool = False,
                 siralanabilir: bool = True,
                 siralama: tuple[int, Qt.SortOrder] | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.model = SatirModeli(sutunlar, anahtar, zemin, yazi_rengi, kalin, arama_eki, self)
        self.suzgec = SuzgecModeli(self)
        self.suzgec.setSourceModel(self.model)
        self.gorunum = QTableView()
        self.gorunum.setModel(self.suzgec)
        self.gorunum.setSortingEnabled(siralanabilir)
        self.gorunum.setAlternatingRowColors(True)
        self.gorunum.setShowGrid(False)
        self.gorunum.setWordWrap(False)
        self.gorunum.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.gorunum.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection if coklu_secim
            else QAbstractItemView.SelectionMode.SingleSelection)
        self.gorunum.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.gorunum.verticalHeader().setVisible(False)
        self.gorunum.verticalHeader().setDefaultSectionSize(32)
        self.gorunum.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.gorunum.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        baslik = self.gorunum.horizontalHeader()
        baslik.setHighlightSections(False)
        baslik.setSectionsMovable(False)
        baslik.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        uzayan = [i for i, s in enumerate(sutunlar) if s.uzat]
        for i, sutun in enumerate(sutunlar):
            self.gorunum.setColumnWidth(i, sutun.genislik)
            if i in uzayan:
                baslik.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        if not uzayan:
            baslik.setStretchLastSection(True)
        self._genislikler = [s.genislik for s in sutunlar]
        # Uzayan sütun yoksa son sütun uzar; daralmada payı o alır.
        self._esnek = set(uzayan) or {len(sutunlar) - 1}
        self._elle_boyutlandi = False
        self._sigdiriyor = False
        baslik.sectionResized.connect(self._sutun_boyutlandi)
        # Varsayılan: servisin verdiği sıra korunur (ör. işaretliler önde);
        # kullanıcı başlığa tıklayınca o sütuna göre sıralanır.
        if siralama is None:
            baslik.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        else:
            self.gorunum.sortByColumn(*siralama)
        self.gorunum.selectionModel().selectionChanged.connect(lambda *_: self.secim_degisti.emit())
        self.gorunum.doubleClicked.connect(self._cift_tiklama)
        self.model.onay_degisti.connect(self.onay_degisti)
        self.gorunum.installEventFilter(self)

        self.bos = QLabel(bos_metin, self.gorunum.viewport())
        self.bos.setObjectName("Soluk")
        self.bos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bos.setWordWrap(True)
        self.suzgec.modelReset.connect(self._bosu_tazele)
        self.suzgec.layoutChanged.connect(self._bosu_tazele)
        self.suzgec.rowsInserted.connect(self._bosu_tazele)
        self.suzgec.rowsRemoved.connect(self._bosu_tazele)
        self.gorunum.viewport().installEventFilter(self)

        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(self.gorunum)
        self._bosu_tazele()

    # --- olaylar
    def eventFilter(self, nesne: QObject, olay: QEvent) -> bool:  # noqa: N802
        if nesne is self.gorunum.viewport() and olay.type() == QEvent.Type.Resize:
            self.bos.setGeometry(self.gorunum.viewport().rect().adjusted(20, 20, -20, -20))
            self._sutunlari_sigdir()
        if (nesne is self.gorunum and olay.type() == QEvent.Type.KeyPress
                and isinstance(olay, QKeyEvent) and olay.key() == Qt.Key.Key_Space):
            indeks = self.gorunum.currentIndex()
            if indeks.isValid() and self.suzgec.flags(indeks) & Qt.ItemFlag.ItemIsUserCheckable:
                durum = self.suzgec.data(indeks, Qt.ItemDataRole.CheckStateRole)
                yeni = (Qt.CheckState.Unchecked if Qt.CheckState(durum) == Qt.CheckState.Checked
                        else Qt.CheckState.Checked)
                self.suzgec.setData(indeks, yeni.value, Qt.ItemDataRole.CheckStateRole)
                return True
        return super().eventFilter(nesne, olay)

    def _sutun_boyutlandi(self, indeks: int, _eski: int, _yeni: int) -> None:
        # Kullanıcı bir sütunu elle genişletti ya da daralttı: tercihi korunur,
        # pencere boyu değişince sütunlar artık kendiliğinden ayarlanmaz.
        if not self._sigdiriyor and indeks not in self._esnek:
            self._elle_boyutlandi = True

    def _sutunlari_sigdir(self) -> None:
        if self._elle_boyutlandi:
            return
        sabit = [i for i in range(len(self._genislikler)) if i not in self._esnek]
        toplam = sum(self._genislikler[i] for i in sabit)
        if not toplam:
            return
        alan = self.gorunum.viewport().width() - UZAYAN_EN_AZ * len(self._esnek)
        olcek = max(0.0, min(1.0, alan / toplam))
        self._sigdiriyor = True
        try:
            for i in sabit:
                self.gorunum.setColumnWidth(
                    i, max(SUTUN_EN_DAR, int(self._genislikler[i] * olcek)))
        finally:
            self._sigdiriyor = False

    def _cift_tiklama(self, indeks: QModelIndex) -> None:
        self.cift_tiklandi.emit(self.suzgec.data(indeks, NESNE_ROLU))

    def _bosu_tazele(self, *_) -> None:
        self.bos.setVisible(self.suzgec.rowCount() == 0)
        self.bos.setGeometry(self.gorunum.viewport().rect().adjusted(20, 20, -20, -20))

    # --- veri
    def yukle(self, satirlar: list[Any], secimi_koru: bool = True) -> None:
        secili = {self.model.anahtar(s) for s in self.secili_satirlar()} if secimi_koru else set()
        kaydirma = self.gorunum.verticalScrollBar().value()
        self.model.yukle(satirlar)
        if secili:
            self._anahtarlari_sec(secili)
        self.gorunum.verticalScrollBar().setValue(kaydirma)
        self._bosu_tazele()

    def _anahtarlari_sec(self, anahtarlar: set) -> None:
        secim = self.gorunum.selectionModel()
        ilk = True
        for satir in range(self.suzgec.rowCount()):
            indeks = self.suzgec.index(satir, 0)
            if self.suzgec.data(indeks, ANAHTAR_ROLU) in anahtarlar:
                bayrak = (secim.SelectionFlag.Select | secim.SelectionFlag.Rows)
                if ilk:
                    secim.setCurrentIndex(indeks, bayrak)
                    ilk = False
                else:
                    secim.select(indeks, bayrak)

    def sec(self, anahtar: Any) -> bool:
        """Anahtarı verilen satırı seçer ve görünür yapar."""
        for satir in range(self.suzgec.rowCount()):
            indeks = self.suzgec.index(satir, 0)
            if self.suzgec.data(indeks, ANAHTAR_ROLU) == anahtar:
                self.gorunum.selectionModel().setCurrentIndex(
                    indeks, self.gorunum.selectionModel().SelectionFlag.ClearAndSelect
                    | self.gorunum.selectionModel().SelectionFlag.Rows)
                self.gorunum.scrollTo(indeks)
                return True
        return False

    def secili_satirlar(self) -> list[Any]:
        satirlar = self.gorunum.selectionModel().selectedRows() if self.gorunum.selectionModel() \
            else []
        return [self.suzgec.data(i, NESNE_ROLU) for i in sorted(satirlar, key=lambda i: i.row())]

    def secili_satir(self) -> Any | None:
        satirlar = self.secili_satirlar()
        return satirlar[0] if satirlar else None

    def gorunen_satirlar(self) -> list[Any]:
        return [self.suzgec.data(self.suzgec.index(i, 0), NESNE_ROLU)
                for i in range(self.suzgec.rowCount())]

    def guncelle(self, satir: Any) -> None:
        self.model.guncelle(satir)

    def aramaya_bagla(self, kutu: AramaKutusu) -> None:
        kutu.degisti.connect(self.suzgec.aramayi_ayarla)

    def kosulu_ayarla(self, kosul: Callable[[Any], bool] | None) -> None:
        self.suzgec.kosulu_ayarla(kosul)
        self._bosu_tazele()

    def bos_metni(self, metin: str) -> None:
        self.bos.setText(metin)


# ============================================================ geri bildirim

class Bildirim(QFrame):
    """Ekranın altında beliren, kendiliğinden kapanan bildirim.

    Eylem verilirse (ör. "Geri al") düğme olarak görünür; süre uzar.
    """

    def __init__(self, ust: QWidget):
        super().__init__(ust)
        self.setObjectName("Bildirim")
        self.metin = QLabel()
        self.metin.setWordWrap(True)
        self.eylem = QPushButton()
        self.eylem.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eylem.clicked.connect(self._eylemi_calistir)
        duzen = QHBoxLayout(self)
        duzen.setContentsMargins(16, 10, 10, 10)
        duzen.setSpacing(12)
        duzen.addWidget(self.metin, 1)
        duzen.addWidget(self.eylem)
        self._zamanlayici = QTimer(self, singleShot=True)
        self._zamanlayici.timeout.connect(self.hide)
        self._geri_cagir: Callable[[], Any] | None = None
        ust.installEventFilter(self)
        self.hide()

    def eventFilter(self, nesne: QObject, olay: QEvent) -> bool:  # noqa: N802
        if nesne is self.parent() and olay.type() == QEvent.Type.Resize and self.isVisible():
            self._yerlestir()
        return super().eventFilter(nesne, olay)

    def _yerlestir(self) -> None:
        ust = self.parentWidget()
        genislik = min(620, max(320, ust.width() - 80))
        self.setFixedWidth(genislik)
        self.adjustSize()
        self.move((ust.width() - genislik) // 2, ust.height() - self.height() - 24)

    def goster(self, metin: str, eylem_metni: str = "", eylem: Callable[[], Any] | None = None,
               sure_ms: int = 4500) -> None:
        self.metin.setText(metin)
        self._geri_cagir = eylem
        self.eylem.setText(eylem_metni)
        self.eylem.setVisible(bool(eylem_metni and eylem))
        self.show()
        self._yerlestir()
        self.raise_()
        self._zamanlayici.start(sure_ms + (3500 if eylem else 0))

    def _eylemi_calistir(self) -> None:
        geri_cagir, self._geri_cagir = self._geri_cagir, None
        self.hide()
        if geri_cagir:
            geri_cagir()


class MesgulOrtusu(QFrame):
    """Uzun iş sürerken sayfanın üstüne konan yarı saydam örtü."""

    def __init__(self, ust: QWidget):
        super().__init__(ust)
        self.setObjectName("MesgulOrtusu")
        self.metin = QLabel()
        self.metin.setObjectName("MesgulMetin")
        self.metin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cubuk = QProgressBar()
        self.cubuk.setRange(0, 0)
        self.cubuk.setTextVisible(False)
        self.cubuk.setFixedWidth(260)
        duzen = QVBoxLayout(self)
        duzen.addStretch(1)
        duzen.addWidget(self.metin, 0, Qt.AlignmentFlag.AlignCenter)
        duzen.addWidget(self.cubuk, 0, Qt.AlignmentFlag.AlignCenter)
        duzen.addStretch(1)
        ust.installEventFilter(self)
        self.hide()

    def eventFilter(self, nesne: QObject, olay: QEvent) -> bool:  # noqa: N802
        if nesne is self.parent() and olay.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return super().eventFilter(nesne, olay)

    def ac(self, metin: str) -> None:
        self.metin.setText(metin)
        # Her iş belirsiz çubukla başlar; ilerlemeyi bilen iş kendisi doldurur.
        self.cubuk.setRange(0, 0)
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()

    def ilerleme(self, deger: int, toplam: int, metin: str) -> None:
        """Boyutu bilinen işte (indirme) çubuk dolar; toplam 0 ise belirsiz döner."""
        self.metin.setText(metin)
        if toplam > 0:
            self.cubuk.setRange(0, 1000)
            self.cubuk.setValue(min(1000, deger * 1000 // toplam))
        else:
            self.cubuk.setRange(0, 0)

    def kapat(self) -> None:
        self.hide()


# ================================================================ arka plan işi

class _Sinyaller(QObject):
    bitti = Signal(object)
    hata = Signal(object)


class _Gorev(QRunnable):
    def __init__(self, is_: Callable[[], Any]):
        super().__init__()
        self.is_ = is_
        self.sinyaller = _Sinyaller()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            sonuc = self.is_()
        except BaseException as hata:  # noqa: BLE001 — arayüze iletilir
            self.sinyaller.hata.emit(hata)
            return
        self.sinyaller.bitti.emit(sonuc)


_SUREN_GOREVLER: set[_Gorev] = set()


def arka_planda(is_: Callable[[], Any], bitince: Callable[[Any], Any],
                hatada: Callable[[BaseException], Any]) -> None:
    """İşi iş parçacığında yürütür, sonucu ana iş parçacığında teslim eder.

    Veritabanı bağlantısı her çağrıda yeniden açıldığı (Veritabani.baglan)
    için iş parçacıkları bağlantı paylaşmaz.
    """
    gorev = _Gorev(is_)
    _SUREN_GOREVLER.add(gorev)

    def _bitti(sonuc: Any) -> None:
        _SUREN_GOREVLER.discard(gorev)
        bitince(sonuc)

    def _hata(hata: BaseException) -> None:
        _SUREN_GOREVLER.discard(gorev)
        hatada(hata)

    gorev.sinyaller.bitti.connect(_bitti, Qt.ConnectionType.QueuedConnection)
    gorev.sinyaller.hata.connect(_hata, Qt.ConnectionType.QueuedConnection)
    QThreadPool.globalInstance().start(gorev)


def suren_is_var_mi() -> bool:
    return bool(_SUREN_GOREVLER)


# ================================================================ iletiler

class Iletisim:
    """Türkçe düğmeli ileti kutuları. Testler bunu kayıt tutan sahtesiyle değiştirir."""

    def __init__(self, ust: QWidget):
        self.ust = ust

    def _kutu(self, simge_turu: QMessageBox.Icon, baslik: str, metin: str,
              dugmeler: list[tuple[str, QMessageBox.ButtonRole]], varsayilan: int = 0,
              ust: QWidget | None = None) -> int:
        kutu = QMessageBox(ust or self.ust)
        kutu.setIcon(simge_turu)
        kutu.setWindowTitle(baslik)
        kutu.setText(metin)
        eklenen = [kutu.addButton(ad, rol) for ad, rol in dugmeler]
        kutu.setDefaultButton(eklenen[varsayilan])
        kutu.exec()
        return eklenen.index(kutu.clickedButton()) if kutu.clickedButton() in eklenen else -1

    def hata(self, baslik: str, metin: str, ust: QWidget | None = None) -> None:
        self._kutu(QMessageBox.Icon.Critical, baslik, metin,
                   [("Tamam", QMessageBox.ButtonRole.AcceptRole)], ust=ust)

    def uyari(self, baslik: str, metin: str, ust: QWidget | None = None) -> None:
        self._kutu(QMessageBox.Icon.Warning, baslik, metin,
                   [("Tamam", QMessageBox.ButtonRole.AcceptRole)], ust=ust)

    def bilgi(self, baslik: str, metin: str, ust: QWidget | None = None) -> None:
        self._kutu(QMessageBox.Icon.Information, baslik, metin,
                   [("Tamam", QMessageBox.ButtonRole.AcceptRole)], ust=ust)

    def soru(self, baslik: str, metin: str, evet: str = "Evet", hayir: str = "Vazgeç",
             uyari: bool = False, ust: QWidget | None = None) -> bool:
        secim = self._kutu(QMessageBox.Icon.Warning if uyari else QMessageBox.Icon.Question,
                           baslik, metin, [(evet, QMessageBox.ButtonRole.YesRole),
                                           (hayir, QMessageBox.ButtonRole.NoRole)],
                           varsayilan=1 if uyari else 0, ust=ust)
        return secim == 0

    def metin_iste(self, baslik: str, metin: str, varsayilan: str = "",
                   ust: QWidget | None = None) -> str | None:
        """Tek satırlık metin ister (ör. hafta sonu gerekçesi); vazgeçilirse None."""
        kutu = QInputDialog(ust or self.ust)
        kutu.setWindowTitle(baslik)
        kutu.setLabelText(metin)
        kutu.setTextValue(varsayilan)
        kutu.setOkButtonText("Tamam")
        kutu.setCancelButtonText("Vazgeç")
        kutu.resize(max(kutu.width(), 560), kutu.height())
        if not kutu.exec():
            return None
        return kutu.textValue().strip()


# ============================================================== kaydırılan sayfa

def kaydirilabilir(icerik: QWidget) -> QScrollArea:
    """Uzun formları küçük ekranda (1366×768) kaydırılabilir yapar."""
    alan = QScrollArea()
    alan.setWidgetResizable(True)
    alan.setFrameShape(QFrame.Shape.NoFrame)
    icerik.setObjectName("KaydirmaIci")
    alan.setWidget(icerik)
    return alan


def ayrac() -> QFrame:
    cizgi = QFrame()
    cizgi.setFrameShape(QFrame.Shape.HLine)
    cizgi.setStyleSheet(f"color: {RENK['cizgi']};")
    return cizgi


__all__ = [
    "AkisDuzeni", "AramaKutusu", "Bildirim", "Iletisim", "Kart", "MesgulOrtusu", "SaatAlani",
    "SatirModeli", "Serit", "Sutun", "secim_kutusu", "SuzgecModeli", "Tablo", "TarihAlani", "akis",
    "arka_planda", "ayrac", "cip", "dugme", "etiket", "etiketli", "kaydirilabilir", "saat_coz",
    "suren_is_var_mi", "turu_ayarla", "yatay",
]
