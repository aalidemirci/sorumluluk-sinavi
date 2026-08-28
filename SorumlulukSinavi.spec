# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller yapılandırması.

Pakete mutlaka girmesi gerekenler:
  * veri/gocler/*.sql — ilk açılışta şema bunlardan kurulur
  * tzdata           — Windows Python dağıtımı IANA saat dilimi verisi
                       taşımaz; ZoneInfo("Europe/Istanbul") onsuz çalışmaz

Exe'ye Windows sürüm kaynağı gömülür; dosya özelliklerinin "Ayrıntılar"
sekmesi ve kurulum/kaldırma kayıtları bunu okur.

Aynı betik Pardus paketi için de kullanılır (bkz. yapim/deb_paketi.py).
Windows'a özgü iki parça — sürüm kaynağı ve .ico simgesi — orada yoktur:
``PyInstaller.utils.win32.versioninfo`` Linux'ta içe aktarılamaz, ``icon``
ise .ico beklediği için Linux yapımını kırar. İkisi de WINDOWS koşuluna
bağlandı; tek betik iki platformu da üretir.
"""

import sys

from PyInstaller.utils.hooks import collect_data_files

WINDOWS = sys.platform == "win32"

if WINDOWS:
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )


pathlib = __import__("pathlib")

# Sürüm tek kaynaktan gelir; ayrıntı için cekirdek/surum.py.
sys.path.insert(0, SPECPATH)
from cekirdek.surum import SURUM  # noqa: E402

# Windows sürüm kaynağı 4 parçalı sayı ister; SURUM üç parçalıdır.
SAYISAL_SURUM = tuple(int(p) for p in SURUM.split(".")) + (0,)

# Bu iki metin yapim/sorumluluk_sinavi.iss ile aynı olmak zorundadır;
# testler/test_surum.py ikisinin ayrışmasını engeller.
AD = "Sorumluluk Sınavı"
GELISTIRICI = "Ahmet Ali DEMİRCİ"

# Dosya özelliklerindeki "Ayrıntılar" sekmesi bunu gösterir. Dil 0x041F
# (Türkçe), kod sayfası 1200 (Unicode).
surum_kaynagi = VSVersionInfo(
    ffi=FixedFileInfo(filevers=SAYISAL_SURUM, prodvers=SAYISAL_SURUM),
    kids=[
        StringFileInfo([StringTable("041F04B0", [
            StringStruct("CompanyName", GELISTIRICI),
            StringStruct("FileDescription", AD),
            StringStruct("FileVersion", SURUM),
            StringStruct("InternalName", "SorumlulukSinavi"),
            StringStruct("LegalCopyright",
                         f"Telif hakkı 2026 {GELISTIRICI} — "
                         "PolyForm Noncommercial License 1.0.0"),
            StringStruct("OriginalFilename", "SorumlulukSinavi.exe"),
            StringStruct("ProductName", AD),
            StringStruct("ProductVersion", SURUM),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x041F, 1200])]),
    ],
) if WINDOWS else None
gocler = [(str(yol), "veri/gocler") for yol in pathlib.Path("veri/gocler").glob("*.sql")]
varliklar = [(str(yol), "varliklar") for yol in pathlib.Path("varliklar").glob("*.*")]
# Lisans sayfası bu dosyalara atıf yapar; pakette bulunmaları gerekir.
lisans = [(ad, ".") for ad in ("LICENSE", "NOTICE") if pathlib.Path(ad).exists()]

analiz = Analysis(
    ["sorumluluk_sinavi.py"],
    pathex=["."],
    binaries=[],
    datas=gocler + varliklar + lisans + collect_data_files("tzdata"),
    hiddenimports=[
        "tzdata",
        "openpyxl",
        "xlrd",
        "arayuz.uygulama",
        "arayuz.takvim",
        "veri.hizmet",
        "veri.rapor_okuma",
        "veri.veritabani",
        "cekirdek.planlayici",
        "cekirdek.kurallar",
        "cekirdek.talep",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Kullanılmayan ağır paketler pakete girmesin.
    excludes=["numpy", "pandas", "matplotlib", "PIL", "pytest", "PyInstaller"],
    noarchive=False,
)

pyz = PYZ(analiz.pure)

exe = EXE(
    pyz,
    analiz.scripts,
    [],
    exclude_binaries=True,
    name="SorumlulukSinavi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,      # masaüstü uygulaması; konsol penceresi açılmaz
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="varliklar/logo.ico" if WINDOWS else None,
    version=surum_kaynagi,
)

coll = COLLECT(
    exe,
    analiz.binaries,
    analiz.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SorumlulukSinavi",
)
