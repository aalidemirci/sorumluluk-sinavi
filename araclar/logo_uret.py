"""Uygulama logosunu üretir.

Logo koddan çizilir; depoda yalnız bu betik durur, üretilen dosyalar
`varliklar/` altına yazılır. Böylece boyut ya da renk değiştiğinde ikili
dosyayı elle güncellemek gerekmez.

Biçim: lacivert yuvarlak köşeli kare zemin, üzerinde takvim ızgarası ve
onay işareti — planlanmış ve onaylanmış sınav takvimini anlatır.

    python araclar/logo_uret.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


LACIVERT = (23, 54, 93)
CAMGOBEGI = (0, 142, 146)
BEYAZ = (255, 255, 255)
ACIK = (232, 238, 245)

VARLIK_KLASORU = Path(__file__).resolve().parents[1] / "varliklar"
BOYUTLAR = (16, 24, 32, 48, 64, 128, 256)


def logo_ciz(kenar: int = 512) -> Image.Image:
    """Logoyu verilen kenar uzunluğunda çizer."""
    olcek = 4  # kenar yumuşatma için büyük çizip küçültürüz
    boy = kenar * olcek
    gorsel = Image.new("RGBA", (boy, boy), (0, 0, 0, 0))
    cizim = ImageDraw.Draw(gorsel)

    # Zemin
    yaricap = int(boy * 0.22)
    cizim.rounded_rectangle([0, 0, boy - 1, boy - 1], radius=yaricap, fill=LACIVERT)

    # Takvim gövdesi
    sol, ust = int(boy * 0.18), int(boy * 0.24)
    sag, alt = boy - sol, boy - int(boy * 0.18)
    cizim.rounded_rectangle([sol, ust, sag, alt], radius=int(boy * 0.05), fill=BEYAZ)

    # Takvim başlık şeridi ve halkaları
    serit_alt = ust + int((alt - ust) * 0.22)
    cizim.rounded_rectangle([sol, ust, sag, serit_alt], radius=int(boy * 0.05),
                            fill=CAMGOBEGI)
    cizim.rectangle([sol, serit_alt - int(boy * 0.04), sag, serit_alt], fill=CAMGOBEGI)
    halka_r = int(boy * 0.022)
    for oran in (0.32, 0.68):
        merkez_x = sol + int((sag - sol) * oran)
        cizim.rounded_rectangle(
            [merkez_x - halka_r, ust - int(boy * 0.05),
             merkez_x + halka_r, ust + int(boy * 0.03)],
            radius=halka_r, fill=ACIK)

    # Gün ızgarası
    izgara_ust = serit_alt + int(boy * 0.05)
    hucre = int((sag - sol - int(boy * 0.12)) / 4)
    bosluk = int(hucre * 0.28)
    for satir in range(2):
        for sutun in range(4):
            x = sol + int(boy * 0.06) + sutun * hucre
            y = izgara_ust + satir * hucre
            if satir == 1 and sutun >= 2:
                continue  # onay işaretine yer bırak
            cizim.rounded_rectangle(
                [x, y, x + hucre - bosluk, y + hucre - bosluk],
                radius=int(hucre * 0.18), fill=ACIK)

    # Onay işareti
    kalinlik = int(boy * 0.055)
    p1 = (sol + int((sag - sol) * 0.52), izgara_ust + int(hucre * 1.05))
    p2 = (sol + int((sag - sol) * 0.64), izgara_ust + int(hucre * 1.42))
    p3 = (sol + int((sag - sol) * 0.92), izgara_ust + int(hucre * 0.55))
    cizim.line([p1, p2, p3], fill=CAMGOBEGI, width=kalinlik, joint="curve")
    for nokta in (p1, p3):
        cizim.ellipse([nokta[0] - kalinlik // 2, nokta[1] - kalinlik // 2,
                       nokta[0] + kalinlik // 2, nokta[1] + kalinlik // 2],
                      fill=CAMGOBEGI)

    return gorsel.resize((kenar, kenar), Image.LANCZOS)


def uret() -> list[Path]:
    VARLIK_KLASORU.mkdir(parents=True, exist_ok=True)
    uretilen = []

    buyuk = logo_ciz(512)
    png = VARLIK_KLASORU / "logo.png"
    buyuk.save(png)
    uretilen.append(png)

    # Evrak antedinde kullanılan küçük boy
    evrak = VARLIK_KLASORU / "logo_evrak.png"
    logo_ciz(128).save(evrak)
    uretilen.append(evrak)

    # Windows uygulama simgesi
    ico = VARLIK_KLASORU / "logo.ico"
    buyuk.save(ico, sizes=[(b, b) for b in BOYUTLAR])
    uretilen.append(ico)

    return uretilen


if __name__ == "__main__":
    for yol in uret():
        print(f"{yol.name:18s} {yol.stat().st_size / 1024:6.1f} KB")
