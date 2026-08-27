"""Uygulamanın tek sürüm kaynağı.

Sürüm numarası yalnızca burada yazılır. Diğer üç yer bu dosyadan okur:

  * ``arayuz/uygulama.py``      — hakkında penceresinde gösterir
  * ``pyproject.toml``          — ``dynamic version`` ile ``SURUM``u okur
  * ``yapim/sorumluluk_sinavi.iss`` — kurulum dosyasının adını ve sürüm
    bilgisini buradan üretir

DİKKAT: aşağıdaki satırın biçimi (``SURUM = "x.y.z"``, tek satır, çift
tırnak, sonunda yorum yok) Inno Setup betiği tarafından metin olarak
ayrıştırılır. Biçimi değiştirmeyin; yalnızca numarayı güncelleyin.
"""

from __future__ import annotations

SURUM = "0.3.0"
