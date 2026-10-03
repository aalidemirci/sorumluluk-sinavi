"""Qt teması: renkler `arayuz.palet`ten, biçim tek bir stil sayfasından gelir.

Fusion stili kullanılır: Windows ve Pardus'ta aynı çizilir, yerel stilin
sürüme göre değişen görünümü programa sızmaz. Renkler palet sözlüğünden
okunur; koda doğrudan renk yazılmaz (bkz. palet.py başındaki not).

Yazı tipi platforma göre seçilir: Windows'ta Segoe UI, Pardus'ta Noto Sans
ya da DejaVu Sans. Tk sürümünde yazı tipi adı sabitti ve Pardus'ta geniş
DejaVu'ya düşen metin düğmeleri taşırıyordu; Qt düzenleri metni ölçerek
yerleştirdiği için aynı sorun burada yaşanmaz.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from arayuz.palet import RENK

YAZI_TIPI_ADAYLARI = ("Segoe UI", "Noto Sans", "Cantarell", "Ubuntu", "DejaVu Sans")
TEMEL_PUNTO = 10


def yazi_tipi_ailesi() -> str:
    """Kurulu ilk aday; hiçbiri yoksa Qt'nin varsayılanı."""
    kurulu = set(QFontDatabase.families())
    return next((ad for ad in YAZI_TIPI_ADAYLARI if ad in kurulu),
                QApplication.font().family())


def _palet() -> QPalette:
    p = QPalette()
    renk = {ad: QColor(deger) for ad, deger in RENK.items()}
    for grup in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        p.setColor(grup, QPalette.ColorRole.Window, renk["zemin"])
        p.setColor(grup, QPalette.ColorRole.WindowText, renk["yazi"])
        p.setColor(grup, QPalette.ColorRole.Base, renk["alan"])
        p.setColor(grup, QPalette.ColorRole.AlternateBase, renk["zebra"])
        p.setColor(grup, QPalette.ColorRole.Text, renk["yazi"])
        p.setColor(grup, QPalette.ColorRole.Button, renk["kart"])
        p.setColor(grup, QPalette.ColorRole.ButtonText, renk["yazi"])
        p.setColor(grup, QPalette.ColorRole.Highlight, renk["bag"])
        p.setColor(grup, QPalette.ColorRole.HighlightedText, renk["panel_yazi"])
        p.setColor(grup, QPalette.ColorRole.ToolTipBase, renk["yazi"])
        p.setColor(grup, QPalette.ColorRole.ToolTipText, renk["panel_yazi"])
        p.setColor(grup, QPalette.ColorRole.PlaceholderText, renk["soluk"])
        p.setColor(grup, QPalette.ColorRole.Link, renk["bag"])
    pasif = QPalette.ColorGroup.Disabled
    for rol in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                QPalette.ColorRole.ButtonText):
        p.setColor(pasif, rol, QColor(RENK["pasif_yazi"]))
    p.setColor(pasif, QPalette.ColorRole.Base, renk["zemin"])
    p.setColor(pasif, QPalette.ColorRole.Button, renk["zemin"])
    return p


def stil_sayfasi(aile: str, ok_asagi: str = "", ok_yukari: str = "") -> str:
    r = RENK
    return f"""
* {{ font-family: "{aile}"; }}
QWidget {{ color: {r['yazi']}; }}
QMainWindow, QDialog, QWidget#Icerik, QStackedWidget, QScrollArea, QWidget#KaydirmaIci {{
    background: {r['zemin']};
}}
QToolTip {{ background: {r['yazi']}; color: {r['panel_yazi']}; border: none; padding: 6px 8px; }}

/* ------------------------------------------------------------ kenar çubuğu */
QFrame#KenarCubugu {{ background: {r['kenar']}; }}
QLabel#Marka {{ color: {r['panel_yazi']}; font-size: 11pt; font-weight: 600; }}
QLabel#MarkaAlt {{ color: {r['panel_silik']}; font-size: 8pt; }}
QLabel#KenarBaslik {{ color: {r['panel_silik']}; font-size: 8pt; font-weight: 600;
    letter-spacing: 1px; padding: 14px 18px 6px 18px; }}
QPushButton#NavDugme {{
    color: {r['panel_soluk']}; background: transparent; border: none; border-radius: 8px;
    text-align: left; padding: 8px 12px; margin: 1px 10px; font-size: 10pt;
}}
QPushButton#NavDugme:hover {{ background: {r['kenar2']}; color: {r['panel_yazi']}; }}
QPushButton#NavDugme:checked {{ background: {r['vurgu2']}; color: {r['vurgu_yazi']};
    font-weight: 600; }}
QFrame#KenarAlt {{ background: {r['kenar2']}; border-radius: 10px; }}
QLabel#KenarAltBaslik {{ color: {r['vurgu2']}; font-weight: 600; font-size: 9pt; }}
QLabel#KenarAltMetin {{ color: {r['panel_silik']}; font-size: 8pt; }}

/* ------------------------------------------------------------ sayfa başlığı */
QLabel#SayfaBaslik {{ font-size: 18pt; font-weight: 600; color: {r['yazi']}; }}
QLabel#SayfaAlt {{ color: {r['soluk']}; font-size: 9pt; }}

/* -------------------------------------------------------------------- kart */
QFrame#Kart {{ background: {r['kart']}; border: 1px solid {r['cizgi']}; border-radius: 12px; }}
QLabel#KartBaslik {{ font-size: 12pt; font-weight: 600; }}
QLabel#KartAlt, QLabel#Soluk {{ color: {r['soluk']}; font-size: 9pt; }}
QLabel#Bolum {{ font-size: 10pt; font-weight: 600; color: {r['kenar']}; }}
QLabel#Deger {{ font-size: 15pt; font-weight: 600; }}

/* ------------------------------------------------------------------- şerit */
QFrame#Serit {{ border-radius: 10px; border: 1px solid {r['cizgi']}; background: {r['chip']}; }}
QFrame#Serit[tur="uyari"] {{ background: {r['uyari_zemin']}; border-color: {r['uyari_kenar']}; }}
QFrame#Serit[tur="engel"] {{ background: {r['engel_zemin']}; border-color: {r['engel_kenar']}; }}
QFrame#Serit[tur="basari"] {{ background: {r['basari_zemin']}; border-color: {r['basari_kenar']}; }}
QFrame#Serit QLabel {{ background: transparent; }}

/* ------------------------------------------------------------------- çip */
QLabel#Cip {{ background: {r['tint']}; border-radius: 10px; padding: 3px 10px; font-size: 9pt; }}
QLabel#Cip[tur="engel"] {{ background: {r['engel_zemin']}; color: {r['engel']}; }}
QLabel#Cip[tur="uyari"] {{ background: {r['uyari_zemin']}; color: {r['uyari_yazi']}; }}
QLabel#Cip[tur="basari"] {{ background: {r['basari_zemin']}; color: {r['basari']}; }}

/* ---------------------------------------------------------------- düğmeler */
QPushButton {{
    background: {r['kart']}; border: 1px solid {r['cizgi']}; border-radius: 8px;
    padding: 7px 14px; font-size: 10pt;
}}
QPushButton:hover {{ background: {r['tint']}; }}
QPushButton:pressed {{ background: {r['chip']}; }}
QPushButton:disabled {{ color: {r['pasif_yazi']}; background: {r['zemin']}; }}
QPushButton:focus {{ border-color: {r['bag']}; }}
QPushButton[tur="ana"] {{
    background: {r['vurgu']}; border: 1px solid {r['vurgu']}; color: {r['vurgu_yazi']};
    font-weight: 600;
}}
QPushButton[tur="ana"]:hover {{ background: {r['vurgu2']}; border-color: {r['vurgu2']}; }}
QPushButton[tur="ana"]:disabled {{ background: {r['vurgu_pasif']}; border-color: {r['vurgu_pasif']};
    color: {r['vurgu_pasif_yazi']}; }}
QPushButton[tur="ana"]:focus {{ border-color: {r['kenar']}; }}
QPushButton[tur="tehlike"] {{ color: {r['engel']}; }}
QPushButton[tur="tehlike"]:hover {{ background: {r['engel_zemin']}; }}
QPushButton[tur="metin"] {{ background: transparent; border: none; color: {r['bag']};
    padding: 4px 6px; }}
QPushButton[tur="metin"]:hover {{ text-decoration: underline; }}
QPushButton[tur="serit"] {{ background: {r['serit_dugme']}; }}
QToolButton {{ border: none; border-radius: 6px; padding: 4px; background: transparent; }}
QToolButton:hover {{ background: {r['tint']}; }}

/* --------------------------------------------------------------- girdiler */
QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox, QPlainTextEdit, QTextEdit {{
    background: {r['alan']}; border: 1px solid {r['cizgi']}; border-radius: 7px;
    padding: 5px 8px; selection-background-color: {r['bag']}; selection-color: {r['panel_yazi']};
}}
QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox {{ min-height: 22px; }}
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{
    border: none; background: transparent; width: 24px;
}}
QComboBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow {{
    image: url("{ok_asagi}"); width: 12px; height: 12px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ border: none; background: transparent; width: 20px; }}
QSpinBox::up-arrow {{ image: url("{ok_yukari}"); width: 10px; height: 10px; }}
QSpinBox::down-arrow {{ image: url("{ok_asagi}"); width: 10px; height: 10px; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {r['bag']}; }}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled {{
    background: {r['zemin']}; color: {r['pasif_yazi']};
}}
QLineEdit[gecersiz="true"], QDateEdit[gecersiz="true"] {{ border: 1px solid {r['engel']};
    background: {r['engel_zemin']}; }}
QComboBox QAbstractItemView {{
    background: {r['kart']}; border: 1px solid {r['cizgi']}; selection-background-color: {r['chip']};
    selection-color: {r['yazi']}; outline: none;
}}

/* ----------------------------------------------------------------- tablo */
QTableView {{
    background: {r['kart']}; alternate-background-color: {r['zebra']};
    border: 1px solid {r['cizgi']}; border-radius: 8px; gridline-color: {r['cizgi']};
    selection-background-color: {r['chip']}; selection-color: {r['yazi']};
    /* Satır seçilir, hücre değil: odaktaki hücrenin çerçevesi açık bir
       düzenleyici gibi görünüyordu. Seçili satır zemini odağı gösterir. */
    outline: 0;
}}
QTableView::item {{ padding: 2px 6px; }}
QTableView::item:selected {{ background: {r['chip']}; color: {r['yazi']}; }}
QHeaderView::section {{
    background: {r['tint']}; color: {r['yazi']}; border: none;
    border-right: 1px solid {r['cizgi']}; border-bottom: 1px solid {r['cizgi']};
    padding: 6px 8px; font-weight: 600; font-size: 9pt;
}}
QTableCornerButton::section {{ background: {r['tint']}; border: none; }}
QListWidget, QListView, QTextBrowser {{
    background: {r['kart']}; border: 1px solid {r['cizgi']}; border-radius: 8px;
}}
QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {r['chip']}; color: {r['yazi']}; }}

/* ---------------------------------------------------------------- sekmeler */
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent; color: {r['soluk']}; padding: 8px 16px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {r['kenar']}; border-bottom: 2px solid {r['kenar']}; }}
QTabBar::tab:hover:!selected {{ color: {r['yazi']}; }}

/* ----------------------------------------------------------- kaydırma çubuğu */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {r['kaydirma']}; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {r['kaydirma_ust']}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {r['kaydirma']}; border-radius: 4px; min-width: 32px; }}
QScrollBar::handle:horizontal:hover {{ background: {r['kaydirma_ust']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ------------------------------------------------------------- bildirim */
QFrame#Bildirim {{ background: {r['yazi']}; border-radius: 10px; }}
QFrame#Bildirim QLabel {{ color: {r['panel_yazi']}; background: transparent; }}
QFrame#Bildirim QPushButton {{ background: transparent; border: none; color: {r['vurgu2']};
    font-weight: 600; padding: 4px 8px; }}
QFrame#MesgulOrtusu {{ background: {r['ortu']}; }}
QLabel#MesgulMetin {{ font-size: 11pt; font-weight: 600; color: {r['kenar']};
    background: transparent; }}
QProgressBar {{ border: none; background: {r['tint']}; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {r['kenar']}; border-radius: 3px; }}
QSplitter::handle {{ background: transparent; }}

/* ------------------------------------------------------------------ takvim */
QWidget#TakvimIzgara {{ background: {r['kart']}; }}
QLabel#TakvimGun {{ background: {r['tint']}; border-radius: 8px; padding: 7px 6px;
    font-weight: 600; font-size: 9pt; }}
QLabel#TakvimGun[hafta_sonu="true"] {{ background: {r['uyari_zemin']}; }}
QLabel#TakvimSaat {{ color: {r['soluk']}; font-weight: 600; font-size: 9pt; padding: 8px 4px 0 0; }}
QFrame#Hucre {{ background: {r['alan']}; border: 1px solid {r['cizgi']}; border-radius: 8px; }}
QFrame#Hucre[hafta_sonu="true"] {{ background: {r['uyari_zemin']}; }}
QFrame#Hucre[hedef="true"] {{ background: {r['takvim_hedef']}; border: 1px dashed {r['kenar']}; }}
QFrame#OturumKarti {{ background: {r['chip']}; border: 1px solid {r['takvim_kart_kenar']};
    border-radius: 7px; }}
QFrame#OturumKarti[tur="uygulama"] {{ background: {r['basari_zemin']};
    border-color: {r['takvim_uygulama_kenar']}; }}
QFrame#OturumKarti[kilitli="true"] {{ background: {r['pasif_zemin']};
    border-color: {r['takvim_kilit_kenar']}; }}
QFrame#OturumKarti[secili="true"] {{ border: 2px solid {r['kenar']}; }}
QLabel#KartBasligi {{ font-weight: 600; font-size: 9pt; background: transparent; }}
QLabel#KartAlti {{ color: {r['soluk']}; font-size: 8pt; background: transparent; }}
QLabel#Suren {{ border: 1px dashed {r['takvim_uygulama_kenar']}; border-radius: 6px;
    color: {r['soluk']}; font-size: 8pt; padding: 3px 6px; background: transparent; }}
"""


def uygula(uygulama: QApplication) -> None:
    """Stili, paleti, yazı tipini ve Türkçe yerel ayarı uygular."""
    QLocale.setDefault(QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey))
    uygulama.setStyle("Fusion")
    uygulama.setPalette(_palet())
    aile = yazi_tipi_ailesi()
    yazi = QFont(aile, TEMEL_PUNTO)
    yazi.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    uygulama.setFont(yazi)
    asagi, yukari = _ok_resimleri()
    uygulama.setStyleSheet(stil_sayfasi(aile, asagi, yukari))
    _qt_cevirisini_yukle(uygulama)


def _qt_cevirisini_yukle(uygulama: QApplication) -> None:
    """Qt'nin kendi metinleri Türkçe olur: sağ tık menüsü (Geri Al, Kopyala,
    Tümünü Seç), takvim ve standart düğmeler.

    Çeviri dosyası Qt ile gelir (qtbase_tr.qm); paket yalnız Türkçesini taşır.
    Bulunamazsa o menüler İngilizce kalır, program çalışmaya devam eder.
    """
    ceviri = QTranslator(uygulama)
    if ceviri.load(QLocale(QLocale.Language.Turkish), "qtbase", "_",
                   QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        uygulama.installTranslator(ceviri)


def _ok_resimleri() -> tuple[str, str]:
    """Açılır kutu okları geçici klasöre PNG olarak yazılır.

    Stil sayfası resmi yalnız dosya yolundan okur; ok çizimi stil sayfasıyla
    değiştirildiğinde Fusion'ın kendi oku ve çerçevesi kaybolur. Dosya her
    açılışta yeniden yazılır; içinde veri yoktur.
    """
    from arayuz.simgeler import pixmap
    klasor = Path(tempfile.gettempdir()) / "sorumluluk-sinavi-tema"
    klasor.mkdir(parents=True, exist_ok=True)
    yollar = []
    for ad in ("asagi", "yukari"):
        hedef = klasor / f"ok_{ad}.png"
        pixmap(ad, RENK["soluk"], 12).save(str(hedef))
        yollar.append(hedef.as_posix())
    return yollar[0], yollar[1]
