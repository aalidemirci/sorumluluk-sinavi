"""Pardus paket betiğinin saf parçaları (karar 0009, 0016).

Paket yalnız Linux'ta, debian:12 kabında derlenir. Burada ldd çıktısının
okunması, bağımlılık denetiminin kararı (sahte ldd ile) ve paket ağacının
sembolik bağlantıları koruması sınanır; gerçek derleme GitHub Actions'ta
yapılır.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]


def _betik():
    tanim = importlib.util.spec_from_file_location("deb_paketi", KOK / "yapim" / "deb_paketi.py")
    modul = importlib.util.module_from_spec(tanim)
    tanim.loader.exec_module(modul)
    return modul


deb = _betik()

LDD_CIKTISI = """\
\tlinux-vdso.so.1 (0x00007ffd5d3f2000)
\tlibQt6Gui.so.6 => /opt/x/_internal/libQt6Gui.so.6 (0x00007f2a1c000000)
\tlibGL.so.1 => /lib/x86_64-linux-gnu/libGL.so.1 (0x00007f2a1bf00000)
\tlibxcb-cursor.so.0 => not found
\t/lib64/ld-linux-x86-64.so.2 (0x00007f2a1d2f5000)
"""


def _elf(yol: Path) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(b"\x7fELF" + b"\0" * 12)


def test_ldd_ciktisi_okunur() -> None:
    assert deb.ldd_cozumle(LDD_CIKTISI) == [
        ("libQt6Gui.so.6", "/opt/x/_internal/libQt6Gui.so.6"),
        ("libGL.so.1", "/lib/x86_64-linux-gnu/libGL.so.1"),
        ("libxcb-cursor.so.0", None),
    ]


def test_pakette_ya_da_depends_te_olmayan_kitaplik_yakalanir(tmp_path: Path) -> None:
    """Olumsuz senaryo: kapta kurulu olmadığı için pakete girmeyen libxcb-cursor
    ve sistemden alınıp Depends'te yazılmayan libxkbcommon derlemeyi durdurur.
    GTK teması isteğe bağlıdır; ELF olmayan dosyaya bakılmaz."""
    dist = tmp_path / "SorumlulukSinavi"
    _elf(dist / "SorumlulukSinavi")
    _elf(dist / "_internal" / "libQt6Gui.so.6")
    _elf(dist / "_internal" / "PySide6" / "Qt" / "plugins" / "platformthemes" / "libqgtk3.so")
    (dist / "_internal" / "veri.txt").write_text("ELF değil", encoding="utf-8")
    yanitlar = {
        "SorumlulukSinavi": [
            ("libQt6Gui.so.6", str(dist / "_internal" / "libQt6Gui.so.6")),
            ("libc.so.6", "/lib/x86_64-linux-gnu/libc.so.6"),
            ("libGL.so.1", "/lib/x86_64-linux-gnu/libGL.so.1"),
        ],
        "libQt6Gui.so.6": [
            ("libxkbcommon.so.0", "/lib/x86_64-linux-gnu/libxkbcommon.so.0"),
            ("libxcb-cursor.so.0", None),
        ],
        "libqgtk3.so": [("libgtk-3.so.0", None)],
    }
    sorunlar = deb.bagimlilik_sorunlari(dist, lambda dosya, _yol: yanitlar[dosya.name])
    assert sorunlar == [
        "_internal/libQt6Gui.so.6: libxkbcommon.so.0 pakette yok, Depends'te de yok "
        "(/lib/x86_64-linux-gnu/libxkbcommon.so.0)",
        "_internal/libQt6Gui.so.6: libxcb-cursor.so.0 bulunamadı",
    ]


def test_bagimliliklari_karsilanan_paket_sorunsuzdur(tmp_path: Path) -> None:
    dist = tmp_path / "SorumlulukSinavi"
    _elf(dist / "SorumlulukSinavi")
    _elf(dist / "_internal" / "libxcb-cursor.so.0")
    yanitlar = {
        "SorumlulukSinavi": [("libxcb-cursor.so.0", str(dist / "_internal" / "libxcb-cursor.so.0")),
                             ("libEGL.so.1", "/lib/x86_64-linux-gnu/libEGL.so.1")],
        "libxcb-cursor.so.0": [("libxcb.so.1", "/lib/x86_64-linux-gnu/libxcb.so.1")],
    }
    assert deb.bagimlilik_sorunlari(dist, lambda dosya, _yol: yanitlar[dosya.name]) == []


def test_sistem_kitapliklari_depends_ile_karsilanir() -> None:
    """İzin verilen her sistem kitaplığının paketi Depends satırında olmalıdır."""
    saglayan = {"libGL.so.1": "libgl1", "libEGL.so.1": "libegl1", "libxcb.so.1": "libxcb1",
                "libc.so.6": "libc6"}
    for kitaplik, paket in saglayan.items():
        assert kitaplik in deb.SISTEM_KITAPLIKLARI
        assert paket in deb.BAGIMLILIKLAR


def test_paket_agaci_sembolik_baglantiyi_korur(tmp_path: Path) -> None:
    """PyInstaller aynı Qt kitaplığını bağlantıyla iki yerden gösterir; ağaç
    kopyalanırken bağlantı izlenirse kitaplık iki kez yer tutar (ilk Qt
    derlemesinde kurulu boyut 207 MB'ye çıkmıştı)."""
    dist = tmp_path / "dist"
    kitaplik = dist / "_internal" / "PySide6" / "Qt" / "lib" / "libQt6Gui.so.6"
    kitaplik.parent.mkdir(parents=True)
    kitaplik.write_bytes(b"x" * 4096)
    (dist / "SorumlulukSinavi").write_bytes(b"\x7fELF")
    try:
        (dist / "_internal" / "libQt6Gui.so.6").symlink_to("PySide6/Qt/lib/libQt6Gui.so.6")
    except OSError:
        pytest.skip("bu sistemde sembolik bağlantı kurulamıyor")
    agac = tmp_path / "agac"
    try:
        deb.agac_kur(dist, agac)
    except OSError:
        pytest.skip("bu sistemde sembolik bağlantı kurulamıyor")
    kurulu = agac / deb.KURULUM_YERI.lstrip("/") / "_internal" / "libQt6Gui.so.6"
    assert kurulu.is_symlink()
    assert deb._boyut_kb(agac) < 2 * 4096 // 1024 + 200     # kitaplık bir kez sayılır


def test_menu_girdisi_pencere_sinifiyla_eslesir() -> None:
    """XFCE açılan pencereyi menü girdisine StartupWMClass ile bağlar; Qt'de
    pencere sınıfı (WM_CLASS) uygulama adıdır. Ayrışırsa görev çubuğunda
    simgesiz ikinci bir kayıt belirir."""
    sinif = re.search(r"^StartupWMClass=(.+)$", deb.masaustu_girdisi(), re.M).group(1)
    giris = (KOK / "sorumluluk_sinavi.py").read_text(encoding="utf-8")
    assert f'setApplicationName("{sinif}")' in giris
