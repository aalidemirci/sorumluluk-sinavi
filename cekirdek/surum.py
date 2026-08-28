"""Uygulamanın tek sürüm kaynağı.

Sürüm numarası yalnızca burada yazılır. Diğer beş yer bu dosyadan okur:

  * ``arayuz/uygulama.py``      — hakkında penceresinde gösterir
  * ``pyproject.toml``          — ``dynamic version`` ile ``SURUM``u okur
  * ``SorumlulukSinavi.spec``   — exe'ye gömülen Windows sürüm kaynağı
  * ``yapim/sorumluluk_sinavi.iss`` — kurulum dosyasının adını ve sürüm
    bilgisini buradan üretir
  * ``yapim/deb_paketi.py``     — Pardus paketinin adı ve ``DEBIAN/control``
    dosyasındaki ``Version`` alanı

DİKKAT: aşağıdaki satırın biçimi (``SURUM = "x.y.z"``, tek satır, çift
tırnak, sonunda yorum yok) Inno Setup betiği tarafından metin olarak
ayrıştırılır. Biçimi değiştirmeyin; yalnızca numarayı güncelleyin.
"""

from __future__ import annotations

SURUM = "0.5.0"
