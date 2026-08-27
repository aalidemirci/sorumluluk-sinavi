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
        import tkinter as tk
        from tkinter import messagebox
        kok = tk.Tk()
        kok.withdraw()
        messagebox.showerror(baslik, mesaj + (f"\n\nTeknik ayrıntı:\n{ayrinti}" if ayrinti else ""))
        kok.destroy()
    except Exception:                                  # pragma: no cover
        print(f"{baslik}: {mesaj}\n{ayrinti}", file=sys.stderr)


def main() -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        from arayuz.uygulama import Uygulama
        Uygulama().calistir()
        return 0
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
