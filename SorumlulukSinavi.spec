# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller yapılandırması.

Pakete mutlaka girmesi gerekenler:
  * veri/gocler/*.sql — ilk açılışta şema bunlardan kurulur
  * tzdata           — Windows Python dağıtımı IANA saat dilimi verisi
                       taşımaz; ZoneInfo("Europe/Istanbul") onsuz çalışmaz
"""

from PyInstaller.utils.hooks import collect_data_files


gocler = [(str(yol), "veri/gocler") for yol in __import__("pathlib").Path("veri/gocler").glob("*.sql")]

analiz = Analysis(
    ["sorumluluk_sinavi.py"],
    pathex=["."],
    binaries=[],
    datas=gocler + collect_data_files("tzdata"),
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
