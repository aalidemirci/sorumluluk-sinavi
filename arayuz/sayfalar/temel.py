"""Sayfaların ortak tabanı.

Sayfa bir kez kurulur ve ana pencerede yaşamaya devam eder; her açılışta
`goster()` veriyi veritabanından tazeler. Tk sürümünde sayfa her kayıttan
sonra baştan çiziliyordu: kaydırma, seçim ve yazılan arama kayboluyordu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from arayuz.uygulama import Uygulama


class Sayfa(QWidget):
    def __init__(self, uyg: "Uygulama"):
        super().__init__()
        self.uyg = uyg
        self.vt = uyg.vt
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(0, 0, 0, 0)
        self.duzen.setSpacing(14)
        # Ctrl+F bu kutuya gider (varsa).
        self.arama_kutusu: QWidget | None = None

    @property
    def ileti(self):
        return self.uyg.ileti

    def bildir(self, metin: str, eylem_metni: str = "",
               eylem: Callable[[], Any] | None = None) -> None:
        self.uyg.bildir(metin, eylem_metni, eylem)

    def hata(self, baslik: str, hata: BaseException | str) -> None:
        self.uyg.hata_goster(baslik, hata)

    def goster(self) -> None:
        """Sayfa her açıldığında çağrılır; veriyi tazeler."""

    def kapanabilir_mi(self) -> bool:
        """Pencere kapanırken ya da sayfadan çıkarken kaydedilmemiş iş var mı?"""
        return True


def kismi_ileti(hata: Exception, yapilan: int, ne: str) -> str:
    """Toplu işlem hatası için ileti; hatadan önce işlenen satır varsa söylenir.

    Toplu işlem ilk hatada durur. Önceki sürüm hatayı gösterip yine de "N kayıt
    işlendi" bildirimi veriyordu; kullanıcı hiçbir şeyin kaydedilmediğini
    göremiyordu.
    """
    return f"{yapilan} {ne}; kalanlar işlenmedi. {hata}" if yapilan else str(hata)
