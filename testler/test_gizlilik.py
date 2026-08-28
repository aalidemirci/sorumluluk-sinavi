"""Depoya gerçek kişi verisi girmesini engelleyen testler (KVKK).

Öğrenci, veli ve personel verisi hiçbir koşulda depoya girmez. `.gitignore`
ilk savunma hattıdır ama beyaz liste yanlış genişletilirse ya da bir dosya
`git add -f` ile zorlanırsa sessizce delinir. Buradaki testler o deliği
kapatır: **izlenen** dosyaların tamamını denetlerler.

Kural biçim bazlıdır. Yeni bir dosya türünü izlemeye almanız gerekiyorsa
önce içinde gerçek kişi verisi olmadığından emin olun, sonra aşağıdaki
listeleri güncelleyin.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]

# İzlenmesine izin verilen uzantılar. Burada olmayan her şey reddedilir.
# .yml: GitHub Actions iş akışları (.github/workflows).
IZINLI_UZANTILAR = {".py", ".sql", ".toml", ".md", ".spec", ".iss", ".gitignore", ".yml"}

# Uzantısı olmayan ya da kuralı aşan tek tek dosyalar.
IZINLI_DOSYALAR = {"LICENSE", "NOTICE", ".gitignore"}

# Uzantısı riskli olduğu hâlde izlenmesi gereken dosyalar. Hepsi koddan
# üretilen görsellerdir; kişi verisi taşımazlar.
IZINLI_IKILI_DOSYALAR = {
    "varliklar/logo.png",
    "varliklar/logo_evrak.png",
    "varliklar/logo.ico",
}

# .gitignore'da bulunması şart olan kurallar.
ZORUNLU_YOKSAYMA = (
    "*.xlsx", "*.xls", "*.csv", "*.docx", "*.pdf", "*.db", "*.log",
    "*.png", "*.zip", "*.json", ".env", "/yerel/", "/sablonlar/ozel/",
)

TC_KIMLIK = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
TELEFON = re.compile(r"(?<!\d)0?5\d{2}[ .-]?\d{3}[ .-]?\d{2}[ .-]?\d{2}(?!\d)")


def _izlenen_dosyalar() -> list[str]:
    if shutil.which("git") is None or not (KOK / ".git").exists():
        pytest.skip("git yok; izlenen dosya listesi çıkarılamıyor")
    sonuc = subprocess.run(["git", "ls-files"], cwd=KOK, capture_output=True,
                           text=True, encoding="utf-8", check=True)
    return [s for s in sonuc.stdout.splitlines() if s]


def test_izlenen_dosyalarin_uzantilari_izinli() -> None:
    """Bir .xlsx ya da .docx izlenmeye başlarsa test kırılır."""
    yabanci = [y for y in _izlenen_dosyalar()
               if y not in IZINLI_IKILI_DOSYALAR
               and Path(y).name not in IZINLI_DOSYALAR
               and Path(y).suffix not in IZINLI_UZANTILAR]
    assert yabanci == [], f"izinsiz uzantılı izlenen dosyalar: {yabanci}"


def test_izlenen_metin_dosyalarinda_kimlik_numarasi_yok() -> None:
    bulgular: list[str] = []
    for y in _izlenen_dosyalar():
        yol = KOK / y
        if yol.suffix not in IZINLI_UZANTILAR or not yol.exists():
            continue
        metin = yol.read_text(encoding="utf-8", errors="replace")
        for satir_no, satir in enumerate(metin.splitlines(), 1):
            if TC_KIMLIK.search(satir):
                bulgular.append(f"{y}:{satir_no} T.C. kimlik numarası benzeri")
            if TELEFON.search(satir):
                bulgular.append(f"{y}:{satir_no} telefon numarası benzeri")
    assert bulgular == [], "\n".join(bulgular)


def test_gitignore_zorunlu_kurallari_icerir() -> None:
    satirlar = {s.strip() for s in (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()}
    eksik = [k for k in ZORUNLU_YOKSAYMA if k not in satirlar]
    assert eksik == [], f".gitignore'dan düşen kurallar: {eksik}"


def test_yoksayma_kuralina_takilan_izlenen_dosya_yok() -> None:
    """İzlenen bir dosya yoksayma kuralına da uyuyorsa kural yanıltıcıdır.

    Git izlenen dosyaları yoksaymaz; böyle bir dosya "korunuyorum" sanılırken
    her değişiklikte push edilmeye devam eder.
    """
    if shutil.which("git") is None or not (KOK / ".git").exists():
        pytest.skip("git yok")
    sonuc = subprocess.run(["git", "ls-files", "-i", "-c", "--exclude-standard"],
                           cwd=KOK, capture_output=True, text=True,
                           encoding="utf-8", check=True)
    takilanlar = [s for s in sonuc.stdout.splitlines() if s]
    assert takilanlar == [], f"izlendiği hâlde yoksayma kuralına uyan: {takilanlar}"
