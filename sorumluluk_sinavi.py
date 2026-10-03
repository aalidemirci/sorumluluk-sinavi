"""Sorumluluk Sınavı — giriş noktası."""

from __future__ import annotations

import os
import sys
import traceback


def _hata_goster(baslik: str, mesaj: str, ayrinti: str = "") -> None:
    """Açılış hatasını ham traceback yerine okunur bir pencerede gösterir.

    Paketlenmiş uygulamada konsol yoktur; bir istisna açılışta yakalanmazsa
    kullanıcı yalnızca PyInstaller'ın teknik hata kutusunu görür.
    """
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        _ = QApplication.instance() or QApplication(sys.argv)
        kutu = QMessageBox(QMessageBox.Icon.Critical, baslik,
                           mesaj + (f"\n\nTeknik ayrıntı:\n{ayrinti}" if ayrinti else ""))
        kutu.addButton("Tamam", QMessageBox.ButtonRole.AcceptRole)
        kutu.exec()
    except Exception:                                  # pragma: no cover
        print(f"{baslik}: {mesaj}\n{ayrinti}", file=sys.stderr)


def main() -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        from PySide6.QtWidgets import QApplication

        from arayuz import tema
        from arayuz.uygulama import Uygulama, beklenmeyen_hata_kancasi

        uygulama = QApplication.instance() or QApplication(sys.argv)
        # Ad X11'de pencere sınıfı (WM_CLASS) olur; Pardus menü girdisi
        # pencereyi StartupWMClass=SorumlulukSinavi ile tanır (yapim/
        # deb_paketi.py). Ekranda görünen ad pencere başlığıdır.
        uygulama.setApplicationName("SorumlulukSinavi")
        uygulama.setDesktopFileName("sorumluluk-sinavi")
        tema.uygula(uygulama)
        pencere = Uygulama()
        sys.excepthook = beklenmeyen_hata_kancasi(pencere)
        pencere.show()
        return uygulama.exec()
    except Exception as hata:
        from veri.veritabani import VeritabaniUyumsuz
        if isinstance(hata, VeritabaniUyumsuz):
            _hata_goster("Veritabanı açılamadı", str(hata))
        else:
            _hata_goster(
                "Uygulama açılamadı",
                "Beklenmeyen bir hata oluştu. Sorun sürerse veri klasöründeki "
                "uygulama.log dosyasını inceleyin.",
                traceback.format_exc(limit=4))
        return 1


if __name__ == "__main__":
    sys.exit(main())
