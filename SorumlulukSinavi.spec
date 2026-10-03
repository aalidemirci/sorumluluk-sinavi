# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller yapılandırması.

Pakete mutlaka girmesi gerekenler:
  * veri/gocler/*.sql — ilk açılışta şema bunlardan kurulur
  * tzdata           — Windows Python dağıtımı IANA saat dilimi verisi
                       taşımaz; ZoneInfo("Europe/Istanbul") onsuz çalışmaz
  * arayuz.sayfalar  — sayfalar ilk açılışta importlib ile yüklenir;
                       PyInstaller bu içe aktarmayı göremez
  * LICENSES/*.txt   — Qt/PySide6 LGPL-3.0 ile dağıtılır; LGPL ve GPL
                       metinleri her kopyayla verilir (LGPL-3.0 md.4-b)

Qt'nin kullanılmayan büyük parçaları ise pakete girmez (bkz. _gereksiz_mi).

Exe'ye Windows sürüm kaynağı gömülür; dosya özelliklerinin "Ayrıntılar"
sekmesi ve kurulum/kaldırma kayıtları bunu okur.

Aynı betik Pardus paketi için de kullanılır (bkz. yapim/deb_paketi.py).
Windows'a özgü iki parça — sürüm kaynağı ve .ico simgesi — orada yoktur:
``PyInstaller.utils.win32.versioninfo`` Linux'ta içe aktarılamaz, ``icon``
ise .ico beklediği için Linux yapımını kırar. İkisi de WINDOWS koşuluna
bağlandı; tek betik iki platformu da üretir.
"""

import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

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
lisans += [(str(yol), "LICENSES") for yol in pathlib.Path("LICENSES").glob("*.txt")]

analiz = Analysis(
    ["sorumluluk_sinavi.py"],
    pathex=["."],
    binaries=[],
    datas=gocler + varliklar + lisans + collect_data_files("tzdata"),
    hiddenimports=[
        "tzdata",
        "openpyxl",
        "xlrd",
        # Arayüz ve servis katmanı paketlerdir; modülleri tek tek yazılmaz ki
        # yeni modül eklenince paket eksik kalmasın.
        *collect_submodules("arayuz"),
        *collect_submodules("veri.hizmet"),
        "veri.guncelleme",
        "veri.rapor_okuma",
        "veri.veritabani",
        "cekirdek.planlayici",
        "cekirdek.kurallar",
        "cekirdek.talep",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Kullanılmayan ağır paketler pakete girmesin. tkinter: arayüz Qt'ye
    # geçti (karar 0016); Tcl/Tk ~15 MB tutuyordu. PySide6.QtNetwork:
    # PySide6/__init__.py onu yalnız wheel'de bulunmayan bir openssl klasörü
    # varsa yükler; PyInstaller koşulu göremeyip ağ modülünü TLS
    # eklentileriyle birlikte pakete koyuyordu. Program Qt'nin ağ katmanını
    # kullanmaz (karar 0015, test_ag_yalitimi.py).
    excludes=["numpy", "pandas", "matplotlib", "PIL", "pytest", "PyInstaller",
              "tkinter", "_tkinter", "PySide6.QtNetwork"],
    noarchive=False,
)


# Kullanılmayan Qt eklentileri. Windows: Direct2D ve "minimal" platformları.
# Linux: yalnız X11 (xcb) platformu kalır; Pardus masaüstü X11'dir, Wayland
# oturumunda da XWayland üzerinden çalışır. Gömülü sistem platformları
# (eglfs, linuxfb, vnc, vkkhrdisplay), evdev girişleri ve Wayland
# eklentileri paketin sistemden istediği kitaplıkları çoğaltıyordu: vnc
# Qt6Network'ü, Wayland libwayland-* paketlerini istiyor. Ortak: dokunmatik
# TUIO (UDP'den dinler) ve programın açmadığı resim biçimleri; simgeler
# QtSvg ile çizilir, logo PNG'dir ve PNG Qt'nin içindedir.
GEREKSIZ_EKLENTILER = {
    "qdirect2d", "qminimal", "qtuiotouchplugin",
    "qgif", "qicns", "qjpeg", "qtga", "qtiff", "qwbmp", "qwebp",
    "qeglfs", "qlinuxfb", "qminimalegl", "qvkkhrdisplay", "qvnc", "qwayland",
    "qevdevkeyboardplugin", "qevdevmouseplugin", "qevdevtabletplugin", "qevdevtouchplugin",
}
GEREKSIZ_EKLENTI_KLASORLERI = {
    "egldeviceintegrations", "wayland-decoration-client",
    "wayland-graphics-integration-client", "wayland-shell-integration",
}
# Yalnız çıkarılan eklentilerin kullandığı Qt kitaplıkları. Qt6Network
# Windows'ta da yalnız TUIO eklentisinin bağımlılığı olarak giriyordu.
GEREKSIZ_KITAPLIKLAR = ("Qt6Network", "Qt6EglFS", "Qt6EglFs", "Qt6Wayland", "Qt6WlShell")


def _gereksiz_mi(hedef):
    """Qt'nin bu programda kullanılmayan büyük parçaları.

    * Çeviriler: arayüz yalnız Türkçedir; Qt'nin standart metinleri için
      qtbase_tr.qm yeter (bkz. arayuz/tema.py). Ötekiler ~10 MB tutar.
    * opengl32sw.dll: OpenGL'in yazılım yedeği (~20 MB). Qt Widgets
      çizimi OpenGL kullanmaz; QtQuick ya da QOpenGLWidget yoktur.
    * Yukarıdaki eklenti ve kitaplık listeleri (Windows'ta qx.dll, Linux'ta
      libqx.so). Linux'ta pakette kalan her kitaplığın bağımlılığı
      yapim/deb_paketi.py'de ayrıca denetlenir.
    """
    parcalar = hedef.replace("\\", "/").split("/")
    ad, klasorler = parcalar[-1], parcalar[:-1]
    if "translations" in klasorler:
        return ad != "qtbase_tr.qm"
    if "plugins" in klasorler:
        return (klasorler[-1] in GEREKSIZ_EKLENTI_KLASORLERI
                or ad.split(".")[0].removeprefix("lib") in GEREKSIZ_EKLENTILER)
    return ad.removeprefix("lib").startswith(GEREKSIZ_KITAPLIKLAR) or ad == "opengl32sw.dll"


analiz.datas = [oge for oge in analiz.datas if not _gereksiz_mi(oge[0])]
analiz.binaries = [oge for oge in analiz.binaries if not _gereksiz_mi(oge[0])]

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
