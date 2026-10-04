"""Bütün testler için ortam.

* Qt ekransız (offscreen) kipte çalışır: CI'da ve kapta ekran yoktur,
  geliştirici makinesinde de testler pencere açmamalıdır.
* Açılış güncelleme denetimi kapalıdır: testler ağa çıkmaz (karar 0015).
  Güncelleme servisinin kendisi sahte ağla sınanır (test_guncelleme.py).
* Güncelleme önbelleği geçici bir klasördür: program açılışta oradaki eski
  kurulum dosyalarını siler; testlerde açılan her pencere geliştiricinin
  gerçek önbelleğini temizlemesin.
* Windows'ta ekransız Qt yazı tiplerini kendi klasöründe arar, bulamayınca
  her testte uyarır; sistemin yazı tipi klasörü gösterilir.

Değişkenler Qt içe aktarılmadan önce ayarlanmalıdır; bu yüzden modül
düzeyindedir.
"""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["SORUMLULUK_GUNCELLEME_DENETIMI"] = "0"
_GUNCELLEME_ONBELLEGI = tempfile.mkdtemp(prefix="ss-guncelleme-")
atexit.register(shutil.rmtree, _GUNCELLEME_ONBELLEGI, ignore_errors=True)
os.environ["SORUMLULUK_GUNCELLEME_KLASORU"] = _GUNCELLEME_ONBELLEGI
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR",
                          str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"))
