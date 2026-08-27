"""Paket içi varlık dosyalarının yolunu çözer.

Uygulama hem kaynaktan hem PyInstaller paketinden çalışır; ikisinde taban
klasör farklıdır. Varlıklar (logo gibi) bu iki durumda da buradan bulunur.
"""

from __future__ import annotations

import sys
from pathlib import Path


def taban_klasor() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def varlik_yolu(ad: str) -> Path | None:
    """Varlık dosyasının yolu; bulunamazsa None (varlık isteğe bağlıdır)."""
    yol = taban_klasor() / "varliklar" / ad
    return yol if yol.exists() else None
