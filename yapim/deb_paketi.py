r"""Pardus için .deb paketi üretir.

Hedef Pardus 23'tür; Debian 12 (bookworm) tabanlıdır, çekirdeği 6.1, sistem
Python'ı 3.11'dir. Paket diğer Debian 12 türevlerinde de kurulur.

Neden Debian'ın kendi python3-* paketlerine dayanmıyoruz
--------------------------------------------------------
"Kaynağı kur, bağımlılıkları apt'tan çek" düzeni denendi ve elendi: Debian
12'nin ``python3-docx`` paketi 0.8.11'dir, uygulama 1.1 ister — arada API
değişti. ``python3-xlrd`` 2.0.1'dir, biz 2.0.2'ye sabitliyoruz. Beş
bağımlılığın ikisi daha baştan tutmuyor.

Buna ek olarak apt bağımlılığı **çevrimdışı kurulumu** kırar: deposuna
erişemeyen bir okul makinesinde ``apt install ./paket.deb`` eksik bağımlılığı
indiremez. Windows tarafındaki söz neyse (tek dosya, Python istemez) Pardus
tarafında da o olmalıdır.

Bu yüzden pakete PyInstaller çıktısı konur: yorumlayıcı, kitaplıklar ve Qt
paketin içindedir. Karşılığında paket büyüktür (bkz. karar 0016); kabul
edilen bedel budur.

Sistemden yalnız her masaüstünde kurulu olanlar istenir
------------------------------------------------------
PyInstaller glibc'yi ve grafik yığınını (libGL, libEGL, libxcb) bilerek
pakete koymaz; bunlar ``Depends`` ile istenir ve her Pardus masaüstünde
zaten yüklüdür. Qt'nin X11 eklentisinin istediği öbür kitaplıklar
(libxcb-cursor, libxkbcommon-x11…) ise pakete girer; bunun için derleme
kabında kurulu olmaları gerekir — kurulu değilse PyInstaller yalnız uyarır.
``bagimlilik_sorunlari`` bu açığı kapatır: paketteki her ELF dosyasının
bağımlılığı ya paketin içinde ya ``SISTEM_KITAPLIKLARI``'nda olmalıdır,
değilse derleme durur.

PyInstaller aynı kitaplığı iki yerden göstermek için sembolik bağlantı
kullanır (``_internal/libQt6Gui.so.6`` → ``PySide6/Qt/lib/…``). Ağaç
kopyalanırken bağlantı korunur; izlenirse her Qt kitaplığı iki kez yer
tutar (ICU verisi tek başına 30 MB).

Neden Debian 12 kabında derlenir
--------------------------------
glibc **ileriye** uyumludur, geriye değil: Ubuntu 24.04'te (glibc 2.39)
derlenen ikili Pardus 23'te (glibc 2.36) çalışmaz. Bu yüzden hem yerel
derlemede hem GitHub Actions'ta ``debian:12`` kabı kullanılır; oradan çıkan
paket Debian 12 ve üzerinin tamamında çalışır.

Kaptaki tuzak: Debian'ın ``python3`` paketi paylaşımlı kitaplığı
(``libpython3.11.so.1.0``) taşımaz. ``libpython3.11`` kurulmadan PyInstaller
"Python shared library was not found" diyerek durur.

Kullanım (Debian 12 kabında, depo kökünde; kitaplık listesi
``.github/workflows/pardus-paketi.yml`` ile aynıdır):

    apt-get install -y python3-venv libpython3.11 dpkg-dev binutils \
      libgl1 libegl1 libfontconfig1 libdbus-1-3 libglib2.0-0 libxkbcommon0 \
      libxkbcommon-x11-0 libx11-xcb1 libxcb-cursor0 libxcb-icccm4 \
      libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
      libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxcb-xkb1
    python3 -m venv .venv
    .venv/bin/pip install -e . pyinstaller
    .venv/bin/python yapim/deb_paketi.py
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from cekirdek.surum import SURUM  # noqa: E402  (sürüm tek kaynaktan gelir)

PAKET_ADI = "sorumluluk-sinavi"
AD = "Sorumluluk Sınavı"
GELISTIRICI = "Ahmet Ali DEMİRCİ <aalidemirci@gmail.com>"
DEPO = "https://github.com/aalidemirci/sorumluluk-sinavi"

# PyInstaller çıktısının kurulacağı yer. /opt, Debian Politikası'nda dağıtımın
# kendi paket düzenine girmeyen bütünleşik yazılımlar için ayrılmıştır;
# /usr/lib altına koymak paketi dağıtımın dosyalarıyla karıştırırdı.
KURULUM_YERI = f"/opt/{PAKET_ADI}"

# Uygulamanın sistemden aldığı kitaplıklar. PyInstaller Python'ı, Qt'yi ve
# kendi bağımlılıklarını pakete koyar; glibc'yi ve grafik yığınını koymaz.
# Buradaki paketler her Pardus masaüstü kurulumunda zaten yüklüdür, yani
# çevrimdışı kurulumu engellemezler. libfontconfig1 kitaplık için değil
# yazı tipi yapılandırması ve en az bir yazı tipi gelsin diye istenir.
BAGIMLILIKLAR = "libc6 (>= 2.36), libgl1, libegl1, libxcb1, libfontconfig1"

# Paketin sistemden almasına izin verilen kitaplıklar: BAGIMLILIKLAR'daki
# paketlerin sağladıkları (libgl1 libglvnd0 ve libglx0'ı da getirir).
# Paketteki bir dosya bunların dışında bir sistem kitaplığına bağlanıyorsa
# derleme durur (bkz. bagimlilik_sorunlari).
SISTEM_KITAPLIKLARI = {
    "libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1",
    "libresolv.so.2", "libutil.so.1", "ld-linux-x86-64.so.2", "ld-linux-aarch64.so.1",
    "libGL.so.1", "libGLX.so.0", "libGLdispatch.so.0", "libEGL.so.1", "libxcb.so.1",
}

# Yüklenemezse Qt'nin sessizce vazgeçtiği eklentiler. GTK teması Pardus
# masaüstünde kurulu GTK'yi kullanır; GTK yoksa Qt kendi iletişim kutularına
# döner. Bu yüzden denetimden muaftır.
ISTEGE_BAGLI = {"libqgtk3.so"}

MIMARILER = {"x86_64": "amd64", "aarch64": "arm64"}


def mimari() -> str:
    """Derleme makinesinin Debian mimari adı.

    Çapraz derleme yapılmaz: PyInstaller çalıştığı mimarinin ikilisini üretir,
    dolayısıyla paketin mimarisi derleme makinesininkidir.
    """
    makine = platform.machine()
    if makine not in MIMARILER:
        raise SystemExit(f"desteklenmeyen mimari: {makine}")
    return MIMARILER[makine]


def pyinstaller_calistir() -> Path:
    """Windows ile aynı .spec dosyasından Linux paketini üretir."""
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "SorumlulukSinavi.spec", "--noconfirm"],
        cwd=KOK, check=True)
    dist = KOK / "dist" / "SorumlulukSinavi"
    if not (dist / "SorumlulukSinavi").is_file():
        raise SystemExit(f"PyInstaller çıktısı bulunamadı: {dist}")
    return dist


_LDD_SATIRI = re.compile(r"^\s*(\S+)\s+=>\s+(not found|\S+)")


def ldd_cozumle(cikti: str) -> list[tuple[str, str | None]]:
    """ldd çıktısından (kitaplık adı, çözülen yol) çiftleri; bulunamayanın yolu None."""
    sonuc: list[tuple[str, str | None]] = []
    for satir in cikti.splitlines():
        eslesme = _LDD_SATIRI.match(satir)
        if eslesme:
            ad, yol = eslesme.groups()
            sonuc.append((ad, None if yol == "not found" else yol))
    return sonuc


def _ldd(dosya: Path, kitaplik_yolu: str) -> list[tuple[str, str | None]]:
    ortam = {**os.environ, "LD_LIBRARY_PATH": kitaplik_yolu}
    sonuc = subprocess.run(["ldd", str(dosya)], capture_output=True, text=True, env=ortam,
                           check=False)
    return ldd_cozumle(sonuc.stdout)


def _elf_mi(dosya: Path) -> bool:
    with dosya.open("rb") as akis:
        return akis.read(4) == b"\x7fELF"


def bagimlilik_sorunlari(
        dist: Path,
        ldd: Callable[[Path, str], list[tuple[str, str | None]]] = _ldd) -> list[str]:
    """Paketteki ELF dosyalarının, ne pakette ne Depends'te olan bağımlılıkları.

    PyInstaller çözemediği kitaplığı yalnız uyarıyla geçer ve paket yine
    üretilir; eksik kitaplık ancak okulun bilgisayarında program açılmayınca
    ortaya çıkar. Bu denetim o durumu derlemede yakalar. Program çalışırken
    PyInstaller kitaplık yolunu ``_internal``'a çevirir; burada da öyle
    çözülür.
    """
    ic = dist.resolve()
    yollar = [dist / "_internal", dist / "_internal" / "PySide6" / "Qt" / "lib"]
    kitaplik_yolu = os.pathsep.join(str(y) for y in yollar if y.is_dir())
    sorunlar = []
    for dosya in sorted(dist.rglob("*")):
        if (dosya.is_symlink() or not dosya.is_file() or dosya.name in ISTEGE_BAGLI
                or not _elf_mi(dosya)):
            continue
        goreli = dosya.relative_to(dist).as_posix()
        for ad, yol in ldd(dosya, kitaplik_yolu):
            if yol is None:
                sorunlar.append(f"{goreli}: {ad} bulunamadı")
            elif ic not in Path(yol).resolve().parents and ad not in SISTEM_KITAPLIKLARI:
                sorunlar.append(f"{goreli}: {ad} pakette yok, Depends'te de yok ({yol})")
    return sorunlar


def masaustu_girdisi() -> str:
    """Menüde görünen .desktop girdisi.

    ``StartupWMClass`` olmadan XFCE açılan pencereyi menü girdisiyle
    eşleştiremez; görev çubuğunda simgesiz ikinci bir kayıt belirir.
    """
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={AD}\n"
        "Comment=Sorumluluk sınavı planlama ve görevlendirme\n"
        f"Exec={KURULUM_YERI}/SorumlulukSinavi\n"
        f"Icon={PAKET_ADI}\n"
        "Terminal=false\n"
        "Categories=Office;Education;\n"
        "StartupWMClass=SorumlulukSinavi\n"
        "Keywords=sorumluluk;sınav;plan;görevlendirme;\n"
    )


def denetim_dosyasi(kurulu_boyut_kb: int) -> str:
    """DEBIAN/control içeriği.

    Açıklama alanının biçimi sözleşmedir: ilk satır özet, sonraki satırlar tek
    boşlukla girintili, boş satır yerine tek nokta. Bozulursa dpkg paketi
    reddeder.
    """
    return (
        f"Package: {PAKET_ADI}\n"
        f"Version: {SURUM}\n"
        f"Architecture: {mimari()}\n"
        f"Maintainer: {GELISTIRICI}\n"
        f"Installed-Size: {kurulu_boyut_kb}\n"
        f"Depends: {BAGIMLILIKLAR}\n"
        "Section: education\n"
        "Priority: optional\n"
        f"Homepage: {DEPO}\n"
        f"Description: {AD} — sınav planlama ve görevlendirme\n"
        " Ortaöğretim kurumlarında sorumluluk sınavı planını, salon ve gözcü\n"
        " görevlendirmesini üreten çevrimdışı masaüstü uygulaması.\n"
        " .\n"
        " Öğrenci ve personel verisi hiçbir yere gönderilmez; e-Okul raporları\n"
        " ve üretilen evrak okulun kendi bilgisayarında kalır. İnternete çıkan\n"
        " tek istek yeni sürüm denetimidir ve veri taşımaz. Veriler kullanıcının\n"
        " ev klasöründe (~/.local/share/sorumluluk-sinavi) durur; paketi\n"
        " kaldırmak veritabanına dokunmaz.\n"
    )


def agac_kur(dist: Path, agac: Path) -> None:
    """Paketin içindeki dosya ağacını kurar."""
    if agac.exists():
        shutil.rmtree(agac)

    uygulama = agac / KURULUM_YERI.lstrip("/")
    # symlinks=True: PyInstaller'ın bağlantıları kopya olursa Qt iki kez yer
    # tutar (bkz. modül belgesi).
    shutil.copytree(dist, uygulama, symlinks=True)

    # /usr/bin'deki bağlantı mutlaktır: paket her zaman aynı yere kurulur,
    # göreli bağlantı yalnızca okunurluğu düşürürdü.
    kabuk = agac / "usr/bin"
    kabuk.mkdir(parents=True, exist_ok=True)
    (kabuk / PAKET_ADI).symlink_to(f"{KURULUM_YERI}/SorumlulukSinavi")

    masaustu = agac / "usr/share/applications"
    masaustu.mkdir(parents=True, exist_ok=True)
    (masaustu / f"{PAKET_ADI}.desktop").write_text(masaustu_girdisi(), encoding="utf-8")

    # Simge iki yere konur: hicolor'ı modern masaüstleri, pixmaps'i eski menü
    # uygulamaları okur. Dosya 512x512'dir; hicolor'da o boy geçerlidir.
    logo = KOK / "varliklar" / "logo.png"
    for hedef in (agac / "usr/share/icons/hicolor/512x512/apps",
                  agac / "usr/share/pixmaps"):
        hedef.mkdir(parents=True, exist_ok=True)
        shutil.copy2(logo, hedef / f"{PAKET_ADI}.png")

    belge = agac / "usr/share/doc" / PAKET_ADI
    belge.mkdir(parents=True, exist_ok=True)
    (belge / "copyright").write_text(
        (KOK / "LICENSE").read_text(encoding="utf-8") + "\n\n"
        + (KOK / "NOTICE").read_text(encoding="utf-8"), encoding="utf-8")

    _izinleri_duzelt(agac)


def _izinleri_duzelt(agac: Path) -> None:
    """dpkg herkese yazılabilir dosya kabul etmez; umask'a güvenilmez."""
    for yol in agac.rglob("*"):
        if yol.is_symlink():
            continue
        if yol.is_dir():
            yol.chmod(0o755)
        else:
            calistirilabilir = yol.stat().st_mode & 0o100
            yol.chmod(0o755 if calistirilabilir else 0o644)


def _boyut_kb(agac: Path) -> int:
    toplam = sum(y.stat().st_size for y in agac.rglob("*")
                 if y.is_file() and not y.is_symlink())
    return max(1, toplam // 1024)


def denetim_klasoru_yaz(agac: Path) -> None:
    """DEBIAN/control ve md5sums dosyalarını yazar.

    md5sums olmadan ``dpkg -V`` kurulu paketi doğrulayamaz; bozuk kopyayı
    ayırt edebilmek için üretilir.
    """
    debian = agac / "DEBIAN"
    debian.mkdir(parents=True, exist_ok=True)
    (debian / "control").write_text(denetim_dosyasi(_boyut_kb(agac)), encoding="utf-8")

    satirlar = []
    for yol in sorted(agac.rglob("*")):
        if not yol.is_file() or yol.is_symlink() or debian in yol.parents:
            continue
        ozet = hashlib.md5(yol.read_bytes()).hexdigest()
        satirlar.append(f"{ozet}  {yol.relative_to(agac).as_posix()}")
    (debian / "md5sums").write_text("\n".join(satirlar) + "\n", encoding="utf-8")

    for ad in ("control", "md5sums"):
        (debian / ad).chmod(0o644)
    debian.chmod(0o755)


def deb_uret(agac: Path, cikti: Path) -> Path:
    """dpkg-deb ile paketi kurar.

    ``--root-owner-group``: dosyalar, derleyenin kullanıcı kimliği ne olursa
    olsun root:root görünsün. fakeroot bu sayede gerekmez.
    """
    cikti.mkdir(parents=True, exist_ok=True)
    hedef = cikti / f"{PAKET_ADI}_{SURUM}_{mimari()}.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(agac), str(hedef)],
                   check=True)
    return hedef


def sha256_yaz(paket: Path) -> Path:
    """Windows paketlerindeki SHA256SUMS dosyasının Pardus karşılığı."""
    ozet = hashlib.sha256(paket.read_bytes()).hexdigest()
    dosya = paket.parent / f"SHA256SUMS-{SURUM}-pardus.txt"
    dosya.write_text(f"{ozet}  {paket.name}\n", encoding="utf-8")
    return dosya


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Pardus .deb paketini üretir")
    ayristirici.add_argument(
        "--dist-hazir", action="store_true",
        help="PyInstaller'ı yeniden çalıştırma; mevcut dist/SorumlulukSinavi kullanılsın")
    secenekler = ayristirici.parse_args()

    if sys.platform != "linux":
        raise SystemExit("Bu betik Linux içindir; Debian 12 kabında çalıştırın.")
    if shutil.which("dpkg-deb") is None:
        raise SystemExit("dpkg-deb bulunamadı (apt-get install dpkg-dev).")

    dist = KOK / "dist" / "SorumlulukSinavi"
    if secenekler.dist_hazir:
        if not (dist / "SorumlulukSinavi").is_file():
            raise SystemExit(f"--dist-hazir verildi ama {dist} yok.")
    else:
        dist = pyinstaller_calistir()

    sorunlar = bagimlilik_sorunlari(dist)
    if sorunlar:
        raise SystemExit("Paketin sistemden istediği bu kitaplıklar ne pakette ne Depends'te:\n  "
                         + "\n  ".join(sorunlar[:40])
                         + "\nDerleme kabına eksik paketi kurun ya da BAGIMLILIKLAR'ı gözden "
                           "geçirin.")

    agac = KOK / "build" / "deb" / f"{PAKET_ADI}_{SURUM}_{mimari()}"
    agac_kur(dist, agac)
    denetim_klasoru_yaz(agac)
    paket = deb_uret(agac, KOK / "dist-kurulum")
    ozetler = sha256_yaz(paket)

    print(f"paket : {paket.relative_to(KOK)}  ({paket.stat().st_size // 1024 // 1024} MB)")
    print(f"özet  : {ozetler.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
