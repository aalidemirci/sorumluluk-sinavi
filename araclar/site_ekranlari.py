"""okulapp.org için ekran görüntüleri: Debian 12 kabında, sanal ekranda (Xvfb).

Gerçek ekran yakalanmaz. Windows masaüstü kilitliyken görüntü siyah gelir;
gerçek ekranı yakalamak da üstteki başka bir penceredeki veriyi alabilir.
Kap ikisini de ortadan kaldırır, görünüm de Pardus'unkine yakın olur (DejaVu).
Veri araclar/site_ornekleri.py'nin kurduğu uydurma okuldur.

Kullanım, depo kökünde (Git Bash; <cikti> site_ornekleri.py'nin klasörü):

    MSYS_NO_PATHCONV=1 docker run --rm --init -v "$PWD:/kaynak:ro" \\
      -v "<cikti>:/cikti" debian:12 bash -c "apt-get update -qq && \\
      apt-get install -y -qq --no-install-recommends python3-venv python3-tk \\
      xvfb fonts-dejavu-core >/dev/null && python3 -m venv /tmp/v && \\
      /tmp/v/bin/pip install -q openpyxl python-docx xlrd==2.0.2 tzdata pillow && \\
      (Xvfb :99 -screen 0 1600x1000x24 -nolisten tcp &) && sleep 3 && \\
      DISPLAY=:99 PYTHONDONTWRITEBYTECODE=1 /tmp/v/bin/python \\
      /kaynak/araclar/site_ekranlari.py /cikti"

Çıktı <cikti>/ekranlar/ altına .png ve .webp olarak yazılır. Pencereler,
açıldıkları ekranın karartılmış görüntüsü üstüne konur; böylece bütün
kareler 1440×900 olur ve sitedeki ızgarada aynı boyda durur.

Tuzaklar: xvfb-run kapta 1 numaralı süreç olunca Xvfb'nin hazır sinyalini
kaçırıp sonsuza dek bekleyebilir; bu yüzden Xvfb elle başlatılır ve kap
--init ile çalışır. Arayüz metninde emoji kullanılırsa burada kare görünür
(bkz. testler/test_arayuz_karakterleri.py).
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

DEPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPO))

# Pardus'taki varsayılan veri yolu: Kurum Ayarları ekranının altında görünür.
VERI = "/home/ogretmen/.local/share/sorumluluk-sinavi/plan"


def main(cikti: Path) -> None:
    os.environ["SORUMLULUK_VERI_KLASORU"] = VERI
    shutil.rmtree(VERI, ignore_errors=True)
    shutil.copytree(cikti / "veri", VERI)

    from PIL import Image, ImageDraw, ImageFilter, ImageGrab
    from tkinter import ttk

    from veri import hizmet

    # Örnek plan Eylül dönemindedir; ekranlar bugüne göre başka dönemi açmasın.
    hizmet.varsayilan_pencere = lambda vt, gecmise_bak=False, bugun=None: "P1"

    from arayuz.pencereler import GorevliDegistirPenceresi, MusaitlikPenceresi, TekDersPenceresi
    from arayuz.uygulama import Uygulama
    from cekirdek.modeller import GorevRolu

    hedef = cikti / "ekranlar"
    shutil.rmtree(hedef, ignore_errors=True)
    hedef.mkdir(parents=True)
    uyg = Uygulama()
    uyg.kok.geometry("1440x900+0+0")

    def bekle(sure: float = 0.8) -> None:
        son = time.time() + sure
        while time.time() < son:
            uyg.kok.update()
            time.sleep(0.05)

    def yakala(ad: str, pencere=None) -> Image.Image:
        bekle()
        w = pencere or uyg.kok
        x, y = w.winfo_rootx(), w.winfo_rooty()
        resim = ImageGrab.grab(bbox=(x, y, x + w.winfo_width(), y + w.winfo_height()),
                               xdisplay=os.environ["DISPLAY"])
        resim.save(hedef / f"{ad}.png")
        return resim

    def kaydet(ad: str, resim: Image.Image) -> None:
        resim.convert("RGB").save(hedef / f"{ad}.webp", "WEBP", quality=88, method=6)

    def ust_uste(zemin: Image.Image, pencere: Image.Image) -> Image.Image:
        """Pencereyi karartılmış ekranın ortasına, gölge ve çerçeveyle koyar."""
        zemin = zemin.convert("RGBA")
        sonuc = Image.alpha_composite(zemin, Image.new("RGBA", zemin.size, (25, 10, 15, 110)))
        x, y = (zemin.width - pencere.width) // 2, (zemin.height - pencere.height) // 2
        golge = Image.new("RGBA", zemin.size, (0, 0, 0, 0))
        ImageDraw.Draw(golge).rectangle(
            (x + 6, y + 10, x + pencere.width + 6, y + pencere.height + 10), fill=(0, 0, 0, 120))
        sonuc = Image.alpha_composite(sonuc, golge.filter(ImageFilter.GaussianBlur(12)))
        cerceve = Image.new("RGBA", (pencere.width + 2, pencere.height + 2), (90, 30, 50, 255))
        cerceve.paste(pencere.convert("RGBA"), (1, 1))
        sonuc.paste(cerceve, (x - 1, y - 1))
        return sonuc

    for sira, ad in ((0, "ekran-kurum-ayarlari"), (4, "ekran-basvuru"), (5, "ekran-ders-brans")):
        uyg._sayfa_goster(sira)
        kaydet(ad, yakala(ad))

    uyg._sayfa_goster(1)
    ogretmen = yakala("zemin-ogretmen-listesi")

    uyg._sayfa_goster(6)
    plan_zemini = yakala("zemin-sinav-plani")
    plan = uyg.plan_sonucu.plan
    # En çok gözcüsü olan, yani salonlara bölünmüş sınav seçili görünsün.
    iki_salonlu = max(plan.oturumlar, key=lambda o: sum(
        1 for g in plan.oturum_gorevleri(o.anahtar) if g.rol is GorevRolu.GOZCU))
    uyg._kart_secildi(iki_salonlu.anahtar)
    secili = yakala("ekran-sinav-plani")
    kaydet("ekran-sinav-plani", secili)

    pencere = GorevliDegistirPenceresi(uyg, iki_salonlu.anahtar)
    bekle()
    pencere.mevcut.selection_set(pencere.mevcut.get_children()[-1])
    pencere._adaylari_doldur()
    kaydet("ekran-gorevli-degistir", ust_uste(secili, yakala("pencere-gorevli", pencere)))
    pencere.destroy()

    uyg._sayfa_goster(1)
    bekle()
    kisi = next(k for k in uyg.personel_kayitlari if k["ad"] == "Uydurma Matematikçi")
    pencere = MusaitlikPenceresi(uyg, kisi)
    kaydet("ekran-musaitlik", ust_uste(ogretmen, yakala("pencere-musaitlik", pencere)))
    pencere.destroy()

    pencere = TekDersPenceresi(uyg, "P1")
    kaydet("ekran-tek-ders", ust_uste(plan_zemini, yakala("pencere-tek-ders", pencere)))
    pencere.destroy()

    uyg._sayfa_goster(7)
    bekle()

    def defterler(kok):
        for cocuk in kok.winfo_children():
            if isinstance(cocuk, ttk.Notebook):
                yield cocuk
            yield from defterler(cocuk)

    for defter in defterler(uyg.icerik):
        defter.select(1)
    kaydet("ekran-teslim-cizelgesi", yakala("ekran-teslim-cizelgesi"))
    uyg.kok.destroy()
    print("ekranlar:", sorted(p.name for p in hedef.glob("ekran-*.webp")))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
