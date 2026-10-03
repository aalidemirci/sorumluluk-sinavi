"""okulapp.org için örnek okul, örnek evrak ve evrak önizlemeleri üretir.

Sitedeki ekran görüntüleri ve örnek belgeler gerçek veriyle değil, bu betiğin
kurduğu örnek bir okulla gösterilir. Adlar şablon dilindedir (kullanıcı
kararı, 03.10.2026): okul "Örnek Anadolu Lisesi", antet "ÖRNEK İLÇE
KAYMAKAMLIĞI", imza yerleri ve öğrenciler "Adı SOYADI" / "Adı Soyadı".
Öğretmenler "Matematik Öğretmeni 1" gibi görev adıyla yazılır: hepsi "Adı
SOYADI" olsa komisyon ve gözcü satırları okunmaz, personel raporu da sicil
numarası olmadan aynı adlı iki kişiyi kabul etmez. Gerçekçi görünen ad
üretilmez (CLAUDE.md → KVKK).

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

OKUL = "Örnek Anadolu Lisesi"
OGRENCI_ADI = "Adı Soyadı"
IMZA_ADI = "Adı SOYADI"

# (ad, görev, kadro, branş). Ad kısa görev adıdır; "Türk Dili ve Edebiyatı
# Öğretmeni 1" gibi uzun adlar evrakın dar sütunlarını taşırırdı.
PERSONEL = [
    ("Okul Müdürü", "Müdür", "Kadrolu", "Coğrafya"),
    ("Müdür Yardımcısı 1", "Müdür Yardımcısı", "Kadrolu", "Tarih"),
    ("Müdür Yardımcısı 2", "Müdür Yardımcısı", "Kadrolu", "Kimya"),
    ("Matematik Öğretmeni 1", "Öğretmen", "Kadrolu", "Matematik"),
    ("Matematik Öğretmeni 2", "Öğretmen", "Kadrolu", "Matematik"),
    ("Matematik Öğretmeni 3", "Öğretmen", "Sözleşmeli", "Matematik"),
    ("Fizik Öğretmeni 1", "Öğretmen", "Kadrolu", "Fizik"),
    ("Fizik Öğretmeni 2", "Öğretmen", "Kadrolu", "Fizik"),
    ("Kimya Öğretmeni 1", "Öğretmen", "Kadrolu", "Kimya"),
    ("Kimya Öğretmeni 2", "Öğretmen", "Kadrolu", "Kimya"),
    ("Biyoloji Öğretmeni 1", "Öğretmen", "Kadrolu", "Biyoloji"),
    ("Biyoloji Öğretmeni 2", "Öğretmen", "Sözleşmeli", "Biyoloji"),
    ("Edebiyat Öğretmeni 1", "Öğretmen", "Kadrolu", "Türk Dili ve Edebiyatı"),
    ("Edebiyat Öğretmeni 2", "Öğretmen", "Kadrolu", "Türk Dili ve Edebiyatı"),
    ("Edebiyat Öğretmeni 3", "Öğretmen", "Sözleşmeli", "Türk Dili ve Edebiyatı"),
    ("İngilizce Öğretmeni 1", "Öğretmen", "Kadrolu", "İngilizce"),
    ("İngilizce Öğretmeni 2", "Öğretmen", "Kadrolu", "İngilizce"),
    ("Almanca Öğretmeni 1", "Öğretmen", "Kadrolu", "Almanca"),
    ("Almanca Öğretmeni 2", "Öğretmen", "Kadrolu", "Almanca"),
    ("Tarih Öğretmeni 1", "Öğretmen", "Kadrolu", "Tarih"),
    ("Tarih Öğretmeni 2", "Öğretmen", "Kadrolu", "Tarih"),
    ("Coğrafya Öğretmeni 1", "Öğretmen", "Kadrolu", "Coğrafya"),
    ("Coğrafya Öğretmeni 2", "Öğretmen", "Kadrolu", "Coğrafya"),
    ("Felsefe Öğretmeni 1", "Öğretmen", "Kadrolu", "Felsefe"),
    ("Felsefe Öğretmeni 2", "Öğretmen", "Kadrolu", "Felsefe"),
    ("Din Kültürü Öğretmeni 1", "Öğretmen", "Kadrolu", "Din Kültürü ve Ahlak Bilgisi"),
    ("Din Kültürü Öğretmeni 2", "Öğretmen", "Kadrolu", "Din Kültürü ve Ahlak Bilgisi"),
    ("Beden Eğitimi Öğretmeni", "Öğretmen", "Kadrolu", "Beden Eğitimi ve Spor"),
    ("Müzik Öğretmeni", "Öğretmen", "Kadrolu", "Müzik"),
    ("Rehber Öğretmen", "Öğretmen", "Kadrolu", "Rehberlik"),
]

# testler/yardimci.py ile aynı OOK12001R010 düzeni; oradaki yazıcı okul adını
# "Uydurma …" diye sabit yazdığı için burada ayrıca tutulur.
SORUMLULUK_BASLIK = ["", "Öğrenci No", "Adı Soyadı", "", "", "", "", "", "Sınıfı", "Dersi"]

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
    "okul_adi": OKUL,
    "mudur_adi": IMZA_ADI,
    "il": "Örnek İl",
    "ilce": "Örnek İlçe",
    "ogretim_yili": "2026-2027",
    "birinci_donem_baslangic": "14.09.2026",
    "ikinci_donem_baslangic": "08.02.2027",
    "ikinci_donem_bitis": "25.06.2027",
    "duzenleyen_adi": IMZA_ADI,
    "duzenleyen_unvani": "Müdür Yardımcısı",
}


def ogrenciler() -> dict[str, list]:
    """Sabit tohumlu örnek öğrenci listesi; 9. sınıfta sorumluluk olmaz.

    Bütün öğrenciler "Adı Soyadı"dır: program öğrenciyi okul numarasıyla
    tanır, ilan çizelgesinde de ad maskelenir ("A** S*****").
    """
    rastgele = random.Random(2026)
    sonuc: dict[str, list] = {}
    for sube, adet in SUBELER.items():
        duzey = int(sube.split("/")[0])
        liste = []
        for i in range(adet):
            dersler: list[tuple[int, str]] = []
            hedef = rastgele.choices([1, 2, 3, 4], weights=[5, 4, 2, 1])[0]
            while len(dersler) < hedef:
                ders_duzeyi = rastgele.choice([d for d in DUZEY_DERSLERI if d < duzey])
                adaylar = DUZEY_DERSLERI[ders_duzeyi]
                ders = rastgele.choices(adaylar, weights=[AGIRLIK[a] for a in adaylar])[0]
                if (ders_duzeyi, ders) not in dersler:
                    dersler.append((ders_duzeyi, ders))
            no = f"{duzey}{'ABC'.index(sube[-1]) + 1}{i + 1:02d}"
            liste.append((no, OGRENCI_ADI, sorted(dersler)))
        sonuc[sube] = liste
    return sonuc


def sorumluluk_raporu_yaz(hedef: Path, subeler: dict[str, list]) -> Path:
    """OOK12001R010 düzeninde örnek rapor (testler/yardimci.py'deki yazıcının eşi)."""
    import csv

    satirlar: list[list[object]] = []
    for sube, ogrenci_listesi in subeler.items():
        duzey, sube_adi = sube.split("/", 1)
        satirlar.append([f"{OKUL} - {duzey}. Sınıf / {sube_adi} Şubesi"] + [""] * 9)
        satirlar.append(list(SORUMLULUK_BASLIK))
        for okul_no, ad_soyad, dersler in ogrenci_listesi:
            for sira, (ders_duzeyi, ders_adi) in enumerate(dersler):
                satir = [""] * 10
                if sira == 0:
                    satir[1], satir[2] = okul_no, ad_soyad
                satir[8], satir[9] = str(ders_duzeyi), ders_adi
                satirlar.append(satir)
    with hedef.open("w", encoding="utf-8-sig", newline="") as akim:
        csv.writer(akim).writerows(satirlar)
    return hedef


def okul_kur(kok: Path) -> None:
    sys.path.insert(0, str(DEPO))
    from openpyxl import Workbook

    from cekirdek.modeller import GorevRolu, IkiAsamaliSayim, PlanParametreleri, PlanTuru
    from evrak import uretici
    from testler.yardimci import personel_satirlari
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
    rapor = sorumluluk_raporu_yaz(kok / "sorumluluk.csv", ogrenciler())
    hizmet.sorumluluk_onayla(vt, hizmet.sorumluluk_onizle(vt, rapor).aktarim_id)

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
    hizmet.musaitlik_ekle(vt, kisiler["Matematik Öğretmeni 1"], hafta_gunu=2,
                          bas_saat=time(8, 0), bit_saat=time(12, 0), aciklama="Ders programı")
    hizmet.musaitlik_ekle(vt, kisiler["Fizik Öğretmeni 2"], bas_tarih=date(2026, 9, 17),
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
                                 kisiler["Müdür Yardımcısı 1"], teslim_tarihi=satir.tarih)

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
