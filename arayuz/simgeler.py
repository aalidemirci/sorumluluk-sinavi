"""Arayüz simgeleri: koda gömülü, 24×24 çizgi SVG'leri.

Simge yazı tipi ya da dış dosya kullanılmaz: emoji ve özel karakterler
Pardus'un DejaVu yazı tipinde kare çıkıyordu (bkz. test_arayuz_karakterleri),
dış dosya ise paketlemede unutulabilir. Çizimler basit geometridir; renk
çağrı anında verilir, böylece aynı simge koyu kenar çubuğunda ve açık kartta
kullanılabilir.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from arayuz.palet import RENK

CIZIMLER = {
    "kurum": '<path d="M4 21V8l8-5 8 5v13"/><path d="M9 21v-6h6v6"/><path d="M3 21h18"/>',
    "ogretmen": ('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 '
                 '6.5 6"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2c2.7.3 5 2.3 5 '
                 '5.8"/>'),
    "salon": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M4 12h16M12 3v18"/>',
    "rapor": ('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
              '<path d="M14 3v5h5"/><path d="M8 13h8M8 17h8M12 11v8"/>'),
    "basvuru": ('<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1"/>'
                '<path d="M9 13l2 2 4-4"/>'),
    "ders": ('<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>'
             '<path d="M8 7h7"/>'),
    "plan": ('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'
             '<path d="M8 14h3M13 14h3M8 17h3"/>'),
    "evrak": ('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
              '<path d="M14 3v5h5"/><path d="M9 13h6M9 17h6M9 9h2"/>'),
    "yardim": ('<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 '
               '.9-1 1.5V14"/><path d="M12 17.5h.01"/>'),
    "bilgi": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5h.01"/>',
    "ara": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "ekle": '<path d="M12 5v14M5 12h14"/>',
    "sil": ('<path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 13a1 1 0 0 0 1 '
            '1h8a1 1 0 0 0 1-1l1-13"/><path d="M9 7V4h6v3"/>'),
    "onay": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "kaydet": ('<path d="M5 3h11l3 3v13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z"/><path d="M8 3v5h7V3"/>'
               '<rect x="8" y="13" width="8" height="6" rx="1"/>'),
    "geri": '<path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "ileri": '<path d="M15 14l5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    "yenile": ('<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 3v5h5"/>'
               '<path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 21v-5h-5"/>'),
    "indir": '<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>',
    "yukle": '<path d="M12 20V9"/><path d="M7 14l5-5 5 5"/><path d="M5 4h14"/>',
    "klasor": ('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 '
               '1-2-2z"/>'),
    "uyari": '<path d="M12 3L2 20h20z"/><path d="M12 10v4"/><path d="M12 17.2h.01"/>',
    "basari": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 10"/>',
    "hata": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "kapat": '<path d="M6 6l12 12M18 6L6 18"/>',
    "kilit": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "saat": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "suzgec": '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    "dis": ('<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 '
            '0 1-1-1V7a1 1 0 0 1 1-1h5"/>'),
    "kisi": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    "liste": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
    "guncelle": '<circle cx="12" cy="12" r="9"/><path d="M12 16V8"/><path d="M8.5 11.5L12 8l3.5 3.5"/>',
    "degistir": ('<path d="M7 4L3 8l4 4"/><path d="M3 8h14"/><path d="M17 20l4-4-4-4"/>'
                 '<path d="M21 16H7"/>'),
    "cozumle": '<path d="M5 20V11M12 20V5M19 20v-6"/><path d="M3 20h18"/>',
    "uret": '<path d="M7 4l13 8-13 8z"/>',
    "asagi": '<path d="M6 9l6 6 6-6"/>',
    "yukari": '<path d="M6 15l6-6 6 6"/>',
    "kalem": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
}


def svg(ad: str, renk: str) -> bytes:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="{renk}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{CIZIMLER[ad]}</svg>').encode("utf-8")


@lru_cache(maxsize=256)
def pixmap(ad: str, renk: str = RENK["yazi"], boyut: int = 18) -> QPixmap:
    """Ekranın piksel oranında çizilir; yüksek DPI ekranda bulanık olmaz."""
    oran = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() \
        else 1.0
    kenar = max(1, round(boyut * oran))
    resim = QPixmap(kenar, kenar)
    resim.fill(Qt.GlobalColor.transparent)
    cizici = QPainter(resim)
    QSvgRenderer(QByteArray(svg(ad, renk))).render(cizici, QRectF(0, 0, kenar, kenar))
    cizici.end()
    resim.setDevicePixelRatio(oran)
    return resim


def simge(ad: str, renk: str = RENK["yazi"], boyut: int = 18) -> QIcon:
    return QIcon(pixmap(ad, renk, boyut))
