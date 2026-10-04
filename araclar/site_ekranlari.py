"""okulapp.org için ekran görüntüleri: Debian 12 kabında, ekransız Qt ile.

Gerçek ekran yakalanmaz. Windows masaüstü kilitliyken görüntü siyah gelir;
gerçek ekranı yakalamak da üstteki başka bir penceredeki veriyi alabilir.
Qt pencereyi ekransız (offscreen) kipte kendisi çizer, sanal ekran gerekmez.
Kapta yazı tipi DejaVu'dur; görünüm Pardus'unkine yakın olur, taşan düğme de
önce burada görünür. Veri araclar/site_ornekleri.py'nin kurduğu örnek okuldur
("Örnek Anadolu Lisesi").

Kullanım, depo kökünde (Git Bash; <cikti> site_ornekleri.py'nin klasörü):

    MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/kaynak:ro" \\
      -v "<cikti>:/cikti" debian:12 bash -c "apt-get update -qq && \\
      apt-get install -y -qq --no-install-recommends python3-venv libegl1 \\
      libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 libglib2.0-0 \\
      fonts-dejavu-core >/dev/null && python3 -m venv /tmp/v && \\
      /tmp/v/bin/pip install -q openpyxl python-docx xlrd==2.0.2 tzdata pillow \\
      PySide6-Essentials==6.11.2 && PYTHONDONTWRITEBYTECODE=1 \\
      /tmp/v/bin/python /kaynak/araclar/site_ekranlari.py /cikti"

Windows'ta da çalışır (QT_QPA_FONTDIR=C:/Windows/Fonts ile), ama yazı tipi
Segoe UI olur; sitedeki görüntüler kaptan alınır.

Çıktı <cikti>/ekranlar/ altına .png ve .webp olarak yazılır. Pencereler,
açıldıkları ekranın karartılmış görüntüsü üstüne konur; böylece bütün
kareler 1440×900 olur ve sitedeki ızgarada aynı boyda durur. Arayüz
metninde emoji kullanılırsa kapta kare görünür (bkz.
testler/test_arayuz_karakterleri.py).
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
GENISLIK, YUKSEKLIK = 1440, 900


def main(cikti: Path) -> None:
    os.environ["SORUMLULUK_VERI_KLASORU"] = VERI
    # Örnek ekranlar ağa çıkmaz; güncelleme şeridi de görüntüye girmez.
    os.environ["SORUMLULUK_GUNCELLEME_DENETIMI"] = "0"
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    shutil.rmtree(VERI, ignore_errors=True)
    shutil.copytree(cikti / "veri", VERI)

    from PIL import Image, ImageDraw, ImageFilter
    from PySide6.QtWidgets import QApplication

    from veri import hizmet

    # Örnek plan Eylül dönemindedir; ekranlar bugüne göre başka dönemi açmasın.
    hizmet.varsayilan_pencere = lambda vt, gecmise_bak=False, bugun=None: "P1"

    from arayuz import tema
    from arayuz.pencereler import (
        GorevliDegistirPenceresi, MusaitlikPenceresi, NumaraListesiPenceresi, TekDersPenceresi,
    )
    from arayuz.uygulama import Uygulama, sayfa_sirasi
    from cekirdek.modeller import GorevRolu

    hedef = cikti / "ekranlar"
    shutil.rmtree(hedef, ignore_errors=True)
    hedef.mkdir(parents=True)
    qt = QApplication.instance() or QApplication([])
    tema.uygula(qt)
    uyg = Uygulama()
    # Ekransız kipin sanal ekranı küçüktür; pencere büyütülmüş açılmasın.
    uyg.showNormal()
    uyg.resize(GENISLIK, YUKSEKLIK)

    def bekle(sure: float = 0.6) -> None:
        son = time.time() + sure
        while time.time() < son:
            qt.processEvents()
            time.sleep(0.02)

    def yakala(ad: str, pencere=None) -> Image.Image:
        bekle()
        yol = hedef / f"{ad}.png"
        (pencere or uyg).grab().save(str(yol))
        with Image.open(yol) as resim:
            return resim.convert("RGBA")

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

    def ac(ad: str):
        uyg.sayfa_goster(sayfa_sirasi(ad))
        return uyg.sayfalar[sayfa_sirasi(ad)]

    for sayfa, ad in (("Kurum Ayarları", "ekran-kurum-ayarlari"),
                      ("Ders / Branş", "ekran-ders-brans")):
        ac(sayfa)
        kaydet(ad, yakala(ad))

    basvuru_sayfasi = ac("Başvuru")
    basvuru = yakala("ekran-basvuru")
    kaydet("ekran-basvuru", basvuru)

    # e-Okul'dan kopyalanmış gibi satırlar: üç işaretsiz öğrenci (farklı
    # şubelerden) ve listede olmayan bir numara.
    adaylar = {}
    for satir in basvuru_sayfasi.tablo.gorunen_satirlar():
        if not satir["bayrakli_mi"]:
            adaylar.setdefault(satir["sube"], satir)
    secilen = list(adaylar.values())[:3]
    metin = "\n".join(f"{s['okul_no']} {s['ad_soyad']} {s['sube']}" for s in secilen)
    pencere = NumaraListesiPenceresi(uyg)
    pencere.metin.setPlainText(metin + "\n99999")
    # Devamsızlık tebligatı her sınıfta olabilir; "mezun olamayan 12. sınıf"
    # işareti 10. sınıf örneğinde yanıltıcı görünürdü.
    pencere.tur.setCurrentIndex(
        [kod for kod, _ in NumaraListesiPenceresi.TURLER].index("devamsizlik_tebligati"))
    pencere.onizle()
    pencere.show()
    pencere.resize(760, 560)
    kaydet("ekran-numara-listesi", ust_uste(basvuru, yakala("pencere-numara-listesi", pencere)))
    pencere.close()

    ogretmen_sayfasi = ac("Öğretmen Listesi")
    ogretmen = yakala("zemin-ogretmen-listesi")

    plan_sayfasi = ac("Sınav Planı")
    plan_zemini = yakala("zemin-sinav-plani")
    plan = plan_sayfasi.plan_sonucu.plan
    # En çok gözcüsü olan, yani salonlara bölünmüş sınav seçili görünsün.
    iki_salonlu = max(plan.oturumlar, key=lambda o: sum(
        1 for g in plan.oturum_gorevleri(o.anahtar) if g.rol is GorevRolu.GOZCU))
    plan_sayfasi.takvim.secildi(iki_salonlu.anahtar)
    secili = yakala("ekran-sinav-plani")
    kaydet("ekran-sinav-plani", secili)

    pencere = GorevliDegistirPenceresi(uyg, plan_sayfasi, iki_salonlu.anahtar)
    pencere.show()
    son_gorev = plan.oturum_gorevleri(iki_salonlu.anahtar)[-1]
    pencere.mevcut.sec(f"{son_gorev.personel_kimligi}|{son_gorev.rol.value}")
    kaydet("ekran-gorevli-degistir", ust_uste(secili, yakala("pencere-gorevli", pencere)))
    pencere.close()

    ac("Öğretmen Listesi")
    kisi = next(k for k in ogretmen_sayfasi.tablo.gorunen_satirlar()
                if k["ad"] == "Matematik Öğretmeni 1")
    pencere = MusaitlikPenceresi(uyg, kisi)
    pencere.show()
    kaydet("ekran-musaitlik", ust_uste(ogretmen, yakala("pencere-musaitlik", pencere)))
    pencere.close()

    pencere = TekDersPenceresi(uyg, "P1")
    pencere.show()
    kaydet("ekran-tek-ders", ust_uste(plan_zemini, yakala("pencere-tek-ders", pencere)))
    pencere.close()

    ac("Evrak ve Teslim").sekmeler.setCurrentIndex(1)
    kaydet("ekran-teslim-cizelgesi", yakala("ekran-teslim-cizelgesi"))
    uyg.close()
    print("ekranlar:", sorted(p.name for p in hedef.glob("ekran-*.webp")))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
