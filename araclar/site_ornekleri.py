"""okulapp.org için örnek okul, örnek evrak ve evrak önizlemeleri üretir.

Sitedeki ekran görüntüleri ve örnek belgeler gerçek veriyle değil, bu betiğin
kurduğu açıkça uydurma bir okulla gösterilir ("Uydurma Anadolu Lisesi",
"UYDURMA İLÇE", "Uydurma Matematikçi"…). Gerçekçi görünen ad üretilmez
(CLAUDE.md → KVKK).

Kullanım, depo kökünde:

    .venv/Scripts/python araclar/site_ornekleri.py <cikti_klasoru>
    python araclar/site_ornekleri.py --pdf <cikti_klasoru>

İlk komut <cikti>/veri/sorumluluk.db (ekran görüntüleri bu veritabanından
alınır, bkz. araclar/site_ekranlari.py) ile <cikti>/evrak/*.docx üretir.
İkincisi LibreOffice ile PDF'e çevirip <cikti>/ornek-evrak/ altına PDF ve ilk
sayfa önizlemesi (.webp) yazar; pymupdf ve Pillow ister, bu yüzden ayrı
adımdır (.venv'de kurulu değiller).

Örnek okul bilerek bitmiş bir dönemi gösterir: olağan plan ve tek ders planı
kesinleşmiş, bütün başvuru kararları girilmiştir. Yoksa görev sayacı
raporunda TASLAK kutusu, tutanakta KARAR BEKLİYOR görünür ve örnek, programın
olağan çıktısı sanılır. Hedef gün sayısı 3'tür: bir haftalık varsayılanda
her saate tek sınav düşer ve paralel oturum ile salon bölme görünmez.
"""

from __future__ import annotations

import random
import shutil
import subprocess
import sys
import tempfile
from datetime import date, time, timedelta
from pathlib import Path

DEPO = Path(__file__).resolve().parents[1]

SAYILAR = ["", "Bir", "İki", "Üç", "Dört", "Beş", "Altı", "Yedi", "Sekiz", "Dokuz"]
ONLAR = ["", "On", "Yirmi", "Otuz", "Kırk", "Elli", "Altmış", "Yetmiş", "Seksen", "Doksan"]

PERSONEL = [
    ("Uydurma Müdür", "Müdür", "Kadrolu", "Coğrafya"),
    ("Uydurma Yardımcı", "Müdür Yardımcısı", "Kadrolu", "Tarih"),
    ("Uydurma Yardımcı İki", "Müdür Yardımcısı", "Kadrolu", "Kimya"),
    ("Uydurma Matematikçi", "Öğretmen", "Kadrolu", "Matematik"),
    ("Uydurma Matematikçi İki", "Öğretmen", "Kadrolu", "Matematik"),
    ("Uydurma Matematikçi Üç", "Öğretmen", "Sözleşmeli", "Matematik"),
    ("Uydurma Fizikçi", "Öğretmen", "Kadrolu", "Fizik"),
    ("Uydurma Fizikçi İki", "Öğretmen", "Kadrolu", "Fizik"),
    ("Uydurma Kimyacı", "Öğretmen", "Kadrolu", "Kimya"),
    ("Uydurma Kimyacı İki", "Öğretmen", "Kadrolu", "Kimya"),
    ("Uydurma Biyolog", "Öğretmen", "Kadrolu", "Biyoloji"),
    ("Uydurma Biyolog İki", "Öğretmen", "Sözleşmeli", "Biyoloji"),
    ("Uydurma Edebiyatçı", "Öğretmen", "Kadrolu", "Türk Dili ve Edebiyatı"),
    ("Uydurma Edebiyatçı İki", "Öğretmen", "Kadrolu", "Türk Dili ve Edebiyatı"),
    ("Uydurma Edebiyatçı Üç", "Öğretmen", "Sözleşmeli", "Türk Dili ve Edebiyatı"),
    ("Uydurma İngilizceci", "Öğretmen", "Kadrolu", "İngilizce"),
    ("Uydurma İngilizceci İki", "Öğretmen", "Kadrolu", "İngilizce"),
    ("Uydurma Almancacı", "Öğretmen", "Kadrolu", "Almanca"),
    ("Uydurma Almancacı İki", "Öğretmen", "Kadrolu", "Almanca"),
    ("Uydurma Tarihçi", "Öğretmen", "Kadrolu", "Tarih"),
    ("Uydurma Tarihçi İki", "Öğretmen", "Kadrolu", "Tarih"),
    ("Uydurma Coğrafyacı", "Öğretmen", "Kadrolu", "Coğrafya"),
    ("Uydurma Coğrafyacı İki", "Öğretmen", "Kadrolu", "Coğrafya"),
    ("Uydurma Felsefeci", "Öğretmen", "Kadrolu", "Felsefe"),
    ("Uydurma Felsefeci İki", "Öğretmen", "Kadrolu", "Felsefe"),
    ("Uydurma Din Kültürcü", "Öğretmen", "Kadrolu", "Din Kültürü ve Ahlak Bilgisi"),
    ("Uydurma Din Kültürcü İki", "Öğretmen", "Kadrolu", "Din Kültürü ve Ahlak Bilgisi"),
    ("Uydurma Beden Eğitimci", "Öğretmen", "Kadrolu", "Beden Eğitimi ve Spor"),
    ("Uydurma Müzikçi", "Öğretmen", "Kadrolu", "Müzik"),
    ("Uydurma Rehber", "Öğretmen", "Kadrolu", "Rehberlik"),
]

DERS_BRANS = {
    "MATEMATİK": "Matematik", "FİZİK": "Fizik", "KİMYA": "Kimya", "BİYOLOJİ": "Biyoloji",
    "TÜRK DİLİ VE EDEBİYATI": "Türk Dili ve Edebiyatı", "İNGİLİZCE": "İngilizce",
    "ALMANCA": "Almanca", "TARİH": "Tarih", "COĞRAFYA": "Coğrafya", "FELSEFE": "Felsefe",
    "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "Din Kültürü ve Ahlak Bilgisi",
}
# Sorumluluğun en çok kaldığı dersler önde; matematik bilerek ağır ki bir
# sınav otuzu aşsın ve iki salona bölünsün (OKY md.58/2-b).
AGIRLIK = {"MATEMATİK": 14, "FİZİK": 6, "KİMYA": 6, "BİYOLOJİ": 4, "İNGİLİZCE": 5,
           "TÜRK DİLİ VE EDEBİYATI": 4, "ALMANCA": 2, "TARİH": 3, "COĞRAFYA": 3,
           "FELSEFE": 2, "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": 1}
DUZEY_DERSLERI = {
    9: list(DERS_BRANS),
    10: list(DERS_BRANS),
    11: ["MATEMATİK", "FİZİK", "KİMYA", "BİYOLOJİ", "TÜRK DİLİ VE EDEBİYATI", "İNGİLİZCE",
         "ALMANCA", "TARİH", "FELSEFE"],
}
SUBELER = {"10/A": 22, "10/B": 20, "10/C": 18, "11/A": 20, "11/B": 18, "12/A": 16, "12/B": 14}

AYARLAR = {
    "okul_adi": "Uydurma Anadolu Lisesi",
    "mudur_adi": "Uydurma Müdür",
    "il": "UYDURMA İL",
    "ilce": "UYDURMA İLÇE",
    "ogretim_yili": "2026-2027",
    "birinci_donem_baslangic": "14.09.2026",
    "ikinci_donem_baslangic": "08.02.2027",
    "ikinci_donem_bitis": "25.06.2027",
    "duzenleyen_adi": "Uydurma Yardımcı",
    "duzenleyen_unvani": "Müdür Yardımcısı",
}


def sayi_adi(n: int) -> str:
    yuz = "Yüz" if n >= 100 else ""
    n %= 100
    return " ".join(p for p in (yuz, ONLAR[n // 10], SAYILAR[n % 10]) if p)


def ogrenciler() -> dict[str, list]:
    """Sabit tohumlu uydurma öğrenci listesi; 9. sınıfta sorumluluk olmaz."""
    rastgele = random.Random(2026)
    sira = 0
    sonuc: dict[str, list] = {}
    for sube, adet in SUBELER.items():
        duzey = int(sube.split("/")[0])
        liste = []
        for i in range(adet):
            sira += 1
            dersler: list[tuple[int, str]] = []
            hedef = rastgele.choices([1, 2, 3, 4], weights=[5, 4, 2, 1])[0]
            while len(dersler) < hedef:
                ders_duzeyi = rastgele.choice([d for d in DUZEY_DERSLERI if d < duzey])
                adaylar = DUZEY_DERSLERI[ders_duzeyi]
                ders = rastgele.choices(adaylar, weights=[AGIRLIK[a] for a in adaylar])[0]
                if (ders_duzeyi, ders) not in dersler:
                    dersler.append((ders_duzeyi, ders))
            no = f"{duzey}{'ABC'.index(sube[-1]) + 1}{i + 1:02d}"
            liste.append((no, f"Uydurma Öğrenci {sayi_adi(sira)}", sorted(dersler)))
        sonuc[sube] = liste
    return sonuc


def okul_kur(kok: Path) -> None:
    sys.path.insert(0, str(DEPO))
    from openpyxl import Workbook

    from cekirdek.modeller import GorevRolu, IkiAsamaliSayim, PlanParametreleri, PlanTuru
    from evrak import uretici
    from testler.yardimci import personel_satirlari, sorumluluk_csv_yaz
    from veri import hizmet
    from veri.veritabani import Veritabani

    shutil.rmtree(kok, ignore_errors=True)
    (kok / "veri").mkdir(parents=True)
    vt = Veritabani(kok / "veri" / "sorumluluk.db")
    vt.gocleri_uygula()

    hizmet.ayarlari_kaydet(vt, AYARLAR)
    for ad, kapasite in (("A-101", 30), ("A-102", 30), ("B-201", 28)):
        hizmet.salon_ekle(vt, ad, kapasite)
    hizmet.tatil_ekle(vt, date(2026, 10, 29), "Cumhuriyet Bayramı")
    hizmet.tatil_ekle(vt, date(2027, 4, 23), "Ulusal Egemenlik ve Çocuk Bayramı")
    hizmet.tatil_ekle(vt, date(2027, 5, 19), "Atatürk'ü Anma, Gençlik ve Spor Bayramı")

    kitap = Workbook()
    for satir in personel_satirlari(PERSONEL):
        kitap.active.append(satir)
    kitap.save(kok / "personel.xlsx")
    hizmet.personel_onayla(vt, hizmet.personel_onizle(vt, kok / "personel.xlsx").aktarim_id)
    csv = sorumluluk_csv_yaz(kok / "sorumluluk.csv", ogrenciler())
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, csv).aktarim_id)

    havuz = {ad for _, ad, _ in hizmet.brans_havuzu_listele(vt)}
    for ders_id, ad, *_ in hizmet.dersleri_listele(vt):
        brans = DERS_BRANS[ad]
        if brans not in havuz:
            hizmet.brans_havuzu_ekle(vt, brans)
            havuz.add(brans)
        hizmet.ders_brans_esle(vt, ders_id, brans, "Zümre kararı")
        if ad in {"TÜRK DİLİ VE EDEBİYATI", "İNGİLİZCE", "ALMANCA"}:
            hizmet.ders_ozellik_guncelle(vt, ders_id, iki_asamali_mi=True,
                                         yabanci_dil_mi=ad != "TÜRK DİLİ VE EDEBİYATI")

    kisiler = {p.ad: p.kimlik for p in hizmet.personelleri_getir(vt)}
    hizmet.musaitlik_ekle(vt, kisiler["Uydurma Matematikçi"], hafta_gunu=2,
                          bas_saat=time(8, 0), bit_saat=time(12, 0), aciklama="Ders programı")
    hizmet.musaitlik_ekle(vt, kisiler["Uydurma Fizikçi İki"], bas_tarih=date(2026, 9, 17),
                          bit_tarih=date(2026, 9, 18), aciklama="İl dışı görev")

    # OKY md.58/2-d: duyuru, işaretler ve başvurular plandan önce. Son başvuru
    # günü sınavdan 5 iş günü önceye düşmeli; hizmet bunu denetler.
    bas, _ = hizmet.pencereleri_getir(vt)["P1"]
    hizmet.duyuru_kaydet(vt, "P1", bas - timedelta(days=13), bas - timedelta(days=7),
                         "Okul Müdürlüğünün 2026/112 sayılı duyurusu", "Okul internet sitesi")
    tablo = hizmet.basvuru_tablosu(vt, "P1")
    on_ikiler = [s for s in tablo if s["sube"].startswith("12")]
    for sira, satir in enumerate(on_ikiler[:3]):
        hizmet.ogrenci_bayrak_guncelle(vt, satir["ogrenci_id"], mezun_olamayan=sira < 2,
                                       devamsizlik_tebligati=sira == 2)
    for satir in on_ikiler[:2]:
        hizmet.basvuru_kaydet(vt, satir["ogrenci_id"], "P1", "basvurdu",
                              basvuru_tarihi=bas - timedelta(days=10), belge_referansi="Dilekçe")
    hizmet.basvuru_kaydet(vt, on_ikiler[2]["ogrenci_id"], "P1", "basvurmadi")

    sonuc = hizmet.plan_hazirla(vt, PlanParametreleri(
        pencere_kodu="P1", ogrenci_gunluk_sinav_siniri=2,
        iki_asamali_sayim=IkiAsamaliSayim.TEK, hedef_gun_sayisi=3))
    plan_id = hizmet.plan_kaydet(vt, sonuc)
    hizmet.plan_kesinlestir(vt, plan_id, "2026/17")
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    print(f"plan #{plan_id}: {len(plan.oturumlar)} oturum, {len(plan.gorevlendirmeler)} görev")

    # Kesin planda bir gözcü değişikliği: görevlendirme çizelgesinde listelenir.
    for oturum in plan.oturumlar:
        gozcu = next((g for g in plan.oturum_gorevleri(oturum.anahtar)
                      if g.rol is GorevRolu.GOZCU), None)
        uygun = [a for a in (hizmet.gorevli_adaylari(vt, plan, oturum.anahtar, GorevRolu.GOZCU,
                                                     gozcu.personel_kimligi) if gozcu else [])
                 if a.get("uygun_mu")]
        if uygun:
            hizmet.kesin_plan_gorevli_degistir(vt, plan_id, oturum.anahtar,
                                               gozcu.personel_kimligi, uygun[0]["kimlik"],
                                               "2026/18", "Başka görevde")
            break

    # Teslim çizelgesi: bir sınavın evrakı gelmemiş kalsın, gecikme üstte görünsün.
    with vt.baglan() as b:
        komisyon = {r[0]: r[1] for r in b.execute(
            "SELECT oturum_id, MIN(personel_id) FROM v_gorevlendirme "
            "WHERE rol='komisyon_uyesi' GROUP BY oturum_id")}
    for sira, satir in enumerate(hizmet.teslim_cizelgesi(vt, plan_id)):
        if sira not in (3, 4, 5):
            hizmet.teslim_kaydet(vt, satir.oturum_id, satir.evrak_turu, komisyon[satir.oturum_id],
                                 kisiler["Uydurma Yardımcı"], teslim_tarihi=satir.tarih)

    # Tek ders sınavı (OKY md.58/6): bir 12. sınıf öğrencisi için, kesinleşmiş.
    adaylar = hizmet.tek_ders_adaylari(vt, "P1")
    if adaylar:
        hizmet.tek_ders_sec(vt, "P1", adaylar[0]["ogrenci_id"], adaylar[0]["sorumluluk_kaydi_id"])
        tek_id = hizmet.plan_kaydet(vt, hizmet.plan_hazirla(
            vt, PlanParametreleri(pencere_kodu="P1", plan_turu=PlanTuru.TEK_DERS)))
        hizmet.plan_kesinlestir(vt, tek_id, "2026/19")

    for yol, _ in uretici.evrak_uret(vt, plan_id, kok / "evrak"):
        print("evrak:", yol.name)
    for yol, _ in uretici.pencere_evraki_uret(vt, "P1", kok / "evrak"):
        print("evrak:", yol.name)


def pdf_ve_onizleme(kok: Path) -> None:
    """docx → PDF (LibreOffice) ve ilk sayfanın .webp önizlemesi."""
    import pymupdf
    from PIL import Image

    soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
    hedef = kok / "ornek-evrak"
    shutil.rmtree(hedef, ignore_errors=True)
    hedef.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as gecici:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", gecici,
                        *map(str, sorted((kok / "evrak").glob("*.docx")))],
                       check=True, capture_output=True)
        for pdf in sorted(Path(gecici).glob("*.pdf")):
            ad = pdf.stem.replace("_", "-")
            shutil.copy(pdf, hedef / f"{ad}.pdf")
            # with: Windows'ta açık kalan belge geçici klasörün silinmesini engeller.
            with pymupdf.open(pdf) as belge:
                metin = " ".join(sayfa.get_text() for sayfa in belge)
                if "TASLAK" in metin or "KARAR BEKL" in metin:
                    raise SystemExit(f"{ad}: örnek belge taslak durumu gösteriyor")
                pix = belge[0].get_pixmap(dpi=110)
                sayfa_sayisi = belge.page_count
            Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
                hedef / f"{ad}.webp", "WEBP", quality=82, method=6)
            print(f"{ad}: {sayfa_sayisi} sayfa")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--pdf":
        pdf_ve_onizleme(Path(sys.argv[2]))
    elif len(sys.argv) == 2:
        okul_kur(Path(sys.argv[1]))
    else:
        raise SystemExit(__doc__)
