"""Arayüz ve evrak kaynaklarında emoji (BMP dışı karakter) bulunmaz.

Tk 8.6 Linux'ta renkli emoji çizemez; Pardus'un varsayılan yazı tipi DejaVu'da
da emoji yoktur. Kesinleşmiş sınav kartındaki kilit emojisi debian:12 kabında
kare olarak göründü (03.10.2026). Windows'ta da BMP dışı karakterin çizimi Tk
sürümüne bağlıdır. İşaret gerekiyorsa DejaVu'da bulunan bir karakter seçilir
(ör. ✓, U+2713). Evrak da aynı kurala uyar: belgeyi açan makinede emoji yazı
tipi olmayabilir.
"""

from __future__ import annotations

from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


def _bmp_disi_satirlar(kok: Path, klasorler: tuple[str, ...]) -> list[str]:
    bulunan = []
    for klasor in klasorler:
        for yol in sorted((kok / klasor).glob("*.py")):
            for no, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
                if any(ord(karakter) > 0xFFFF for karakter in satir):
                    bulunan.append(f"{yol.relative_to(kok).as_posix()}:{no}")
    return bulunan


def test_arayuz_ve_evrakta_bmp_disi_karakter_yok() -> None:
    bulunan = _bmp_disi_satirlar(KOK, ("arayuz", "evrak"))
    assert not bulunan, f"BMP dışı karakter (emoji) kullanılmış: {bulunan}"


def test_denetim_emojiyi_yakalar(tmp_path: Path) -> None:
    """Olumsuz senaryo: denetim emoji içeren satırı bulur, kaçış dizisini değil."""
    (tmp_path / "arayuz").mkdir()
    (tmp_path / "arayuz" / "ornek.py").write_text(
        'kacis = "\\U0001F512"\nkilit = "\U0001F512"\nonay = "\u2713"\n', encoding="utf-8")
    assert _bmp_disi_satirlar(tmp_path, ("arayuz",)) == ["arayuz/ornek.py:2"]
