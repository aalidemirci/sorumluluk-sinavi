"""Sorumluluk Sınavı — giriş noktası."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    from arayuz.uygulama import Uygulama
    Uygulama().calistir()


if __name__ == "__main__":
    sys.exit(main())
