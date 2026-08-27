"""Sınav evrakı üreticileri.

Her belge türü bir fonksiyondur ve verisini `veri.hizmet` üzerinden alır.
Belgeler EBYS/DYS kayıt numarası ve güvenli elektronik imza ibaresi üretmez;
okulun kendi kayıtlarından hazırlanmış çıktılardır.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from veri import hizmet
from veri.veritabani import Veritabani
from .belge import Belge, tr_tarih


ALTBILGI_NOTU = (
    "Bu belge okulun yerel kayıtlarından hazırlanmıştır; EBYS/DYS kayıt numarası ve "
    "güvenli elektronik imza ibaresi içermez."
)

ROL_ADLARI = {"komisyon_uyesi": "Komisyon üyesi", "gozcu": "Gözcü"}


@dataclass(frozen=True)
class EvrakTuru:
    anahtar: str
    ad: str
    dosya_adi: str


EVRAKLAR = (
    EvrakTuru("01_sinav_programi", "Sınav programı (öğrenci nüshası)", "01_sinav_programi.docx"),
    EvrakTuru("02_sinav_programi_gorevli", "Sınav programı (görevli nüshası)",
              "02_sinav_programi_gorevli.docx"),
    EvrakTuru("03_gorevlendirme_oluru", "Görevlendirme oluru", "03_gorevlendirme_oluru.docx"),
    EvrakTuru("04_komisyon_tutanaklari", "Komisyon tutanakları", "04_komisyon_tutanaklari.docx"),
    EvrakTuru("05_yoklama_listeleri", "Yoklama / salon listeleri", "05_yoklama_listeleri.docx"),
    EvrakTuru("06_kagit_sarf_tutanaklari", "Kâğıt sarf tutanakları",
              "06_kagit_sarf_tutanaklari.docx"),
    EvrakTuru("07_gorev_sayac_raporu", "Öğretmen görev sayacı raporu",
              "07_gorev_sayac_raporu.docx"),
    EvrakTuru("08_evrak_teslim_tutanagi", "Evrak teslim tutanağı",
              "08_evrak_teslim_tutanagi.docx"),
)


def _kurum(vt: Veritabani) -> dict[str, str]:
    ayar = hizmet.ayarlari_getir(vt)
    return {
        "okul": ayar.get("okul_adi", ""),
        "mudur": ayar.get("mudur_adi", ""),
        "il": ayar.get("il", ""),
        "ilce": ayar.get("ilce", ""),
        "yil": ayar.get("ogretim_yili", ""),
        "ustbilgi": " / ".join(x for x in (ayar.get("il", ""), ayar.get("ilce", ""),
                                           ayar.get("okul_adi", "")) if x),
    }


def _alt_baslik(kurum: dict, pencere_kodu: str) -> str:
    return f"{kurum['yil']} Öğretim Yılı • Sorumluluk Sınavları • {pencere_kodu} dönemi"


def _oturum_saat(oturum: dict) -> str:
    return f"{tr_tarih(oturum['tarih'])} {oturum['saat']}"


# ------------------------------------------------------------ 01 / 02 program

def sinav_programi(vt: Veritabani, plan_id: int, hedef: Path,
                   gorevli_nushasi: bool = False) -> str:
    kurum = _kurum(vt)
    plan, bilgi = hizmet.plan_yukle(vt, plan_id)
    oturumlar = hizmet.plan_oturumlari(vt, plan_id)
    nusha = "Görevli nüshası" if gorevli_nushasi else "Öğrenci nüshası"
    b = Belge(kurum["ustbilgi"], "Sorumluluk Sınavı Programı",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu) + f" • {nusha}",
              yatay=gorevli_nushasi)
    if bilgi["kesin_mi"]:
        b.paragraf(f"Müdür onay no: {bilgi['mudur_onay_no']} — plan kesinleşmiştir.",
                   kalin=True, boyut=9.5)
    else:
        b.uyari("TASLAK — plan henüz müdür onayıyla kesinleştirilmemiştir.")

    if gorevli_nushasi:
        basliklar = ["Tarih / Saat", "Sınıf ve ders", "Süre", "Salon", "Öğr.", "Görevliler"]
        genislikler = [16, 26, 6, 14, 6, 32]
        satirlar = [(
            _oturum_saat(o), o["etiket"], f"{o['sure']} dk",
            ", ".join(o["salonlar"]) or "—", o["ogrenci_sayisi"],
            "; ".join(f"{ad} ({ROL_ADLARI.get(rol, rol)})" for ad, rol, _ in o["gorevliler"])
            or "görevli atanmadı",
        ) for o in oturumlar]
    else:
        basliklar = ["Tarih", "Saat", "Sınıf ve ders", "Süre", "Salon"]
        genislikler = [16, 10, 40, 10, 24]
        satirlar = [(tr_tarih(o["tarih"]), o["saat"], o["etiket"], f"{o['sure']} dk",
                     ", ".join(o["salonlar"]) or "—") for o in oturumlar]
    b.tablo(basliklar, satirlar, genislikler)

    b.dayanak_notu(
        "Sınav tarihleri OKY md.58/2-a uyarınca dönem pencereleri içinde belirlenmiştir. "
        "Sınav süresi ÖDY md.5/1-l gereği bir ders saatini aşmaz. " + ALTBILGI_NOTU)
    b.imza_blogu([("Düzenleyen", ""), ("Kontrol eden", "")], kurum["mudur"])
    return b.kaydet(hedef)


# ------------------------------------------------------ 03 görevlendirme oluru

def gorevlendirme_oluru(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    kurum = _kurum(vt)
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    oturumlar = hizmet.plan_oturumlari(vt, plan_id)
    b = Belge(kurum["ustbilgi"], "Sınav Görevlendirme Oluru",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    b.paragraf(
        f"{kurum['yil']} öğretim yılı sorumluluk sınavlarında, Ortaöğretim Kurumları "
        "Yönetmeliği'nin 58 inci maddesinin ikinci fıkrası uyarınca aşağıda adları yazılı "
        "öğretmenlerin karşılarında gösterilen sınavlarda görevlendirilmeleri hususunu "
        "olurlarınıza arz ederim.", bosluk=12)

    satirlar = []
    for oturum in oturumlar:
        for ad, rol, brans in oturum["gorevliler"]:
            satirlar.append((ad, brans, ROL_ADLARI.get(rol, rol), oturum["etiket"],
                             _oturum_saat(oturum), ", ".join(oturum["salonlar"]) or "—"))
    b.tablo(["Adı Soyadı", "Branşı", "Görevi", "Sınav", "Tarih / Saat", "Salon"],
            satirlar, [22, 18, 14, 22, 14, 10])

    b.dayanak_notu(
        "Komisyon iki sınav öğretmeninden oluşur, en az biri dersin alanındandır; her sınav "
        "salonu için bir gözcü öğretmen görevlendirilir (OKY md.58/2-a, 2-b). Bir sınavda "
        "aynı kişiye hem komisyon üyeliği hem gözcülük verilmez ve yöneticilere sınav görevi "
        "için ücret ödenmez (Karar md.12/2-b, 2-c). " + ALTBILGI_NOTU)
    b.imza_blogu([("Düzenleyen", "")], kurum["mudur"])
    return b.kaydet(hedef)


# ------------------------------------------------------ 04 komisyon tutanağı

def komisyon_tutanaklari(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    kurum = _kurum(vt)
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    oturumlar = hizmet.plan_oturumlari(vt, plan_id)
    b = Belge(kurum["ustbilgi"], "Sorumluluk Sınavı Komisyon Tutanağı",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    for sira, oturum in enumerate(oturumlar):
        if sira:
            b.sayfa_sonu()
            b.yeni_bolum_basligi("Sorumluluk Sınavı Komisyon Tutanağı",
                      _alt_baslik(kurum, plan.parametreler.pencere_kodu))
        b.bilgi_satirlari([
            ("Sınav", oturum["etiket"]),
            ("Tarih ve saat", _oturum_saat(oturum)),
            ("Süre", f"{oturum['sure']} dakika"),
            ("Salon", ", ".join(oturum["salonlar"]) or "—"),
            ("Sınava çağrılan öğrenci sayısı", oturum["ogrenci_sayisi"]),
        ])
        b.paragraf(
            "Yukarıda belirtilen sorumluluk sınavı, aşağıda imzası bulunan komisyon "
            "tarafından yapılmıştır. Sınava giren öğrenci sayısı ……… , girmeyen öğrenci "
            "sayısı ……… olup, sınav evrakı okul müdürlüğüne teslim edilmiştir.", bosluk=10)
        komisyon = [(ad, brans) for ad, rol, brans in oturum["gorevliler"]
                    if rol == "komisyon_uyesi"]
        gozculer = [(ad, brans) for ad, rol, brans in oturum["gorevliler"] if rol == "gozcu"]
        b.tablo(["Görevi", "Adı Soyadı", "Branşı", "İmza"],
                [("Komisyon üyesi", ad, brans, "") for ad, brans in komisyon]
                + [("Gözcü", ad, brans, "") for ad, brans in gozculer],
                [18, 32, 28, 22])
        b.dayanak_notu(
            "OKY md.58/2-a: sorumluluk sınavları iki alan öğretmeni, bulunmaması hâlinde "
            "biri alan öğretmeni olmak üzere iki öğretmen ve bir gözcü öğretmen tarafından "
            "yapılır. " + ALTBILGI_NOTU)
    if not oturumlar:
        b.paragraf("Planda oturum bulunmuyor.")
    return b.kaydet(hedef)


# ------------------------------------------------------- 05 yoklama listesi

def yoklama_listeleri(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    kurum = _kurum(vt)
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    oturumlar = hizmet.plan_oturumlari(vt, plan_id)
    b = Belge(kurum["ustbilgi"], "Sınav Yoklama ve Salon Listesi",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    ilk = True
    for oturum in oturumlar:
        ogrenciler = hizmet.oturum_ogrencileri(vt, oturum["id"])
        salonlar = sorted({o["salon"] for o in ogrenciler}) or [""]
        for salon in salonlar:
            if not ilk:
                b.sayfa_sonu()
                b.yeni_bolum_basligi("Sınav Yoklama ve Salon Listesi",
                          _alt_baslik(kurum, plan.parametreler.pencere_kodu))
            ilk = False
            salondakiler = [o for o in ogrenciler if o["salon"] == salon] or ogrenciler
            b.bilgi_satirlari([
                ("Sınav", oturum["etiket"]),
                ("Tarih ve saat", _oturum_saat(oturum)),
                ("Salon", salon or "atanmadı"),
                ("Öğrenci sayısı", len(salondakiler)),
            ])
            b.tablo(["S. No", "Okul No", "Adı Soyadı", "Şube", "İmza"],
                    [(sira, o["okul_no"], o["ad_soyad"], o["sube"], "")
                     for sira, o in enumerate(salondakiler, 1)],
                    [8, 14, 38, 12, 28])
            b.imza_blogu([("Gözcü", ""), ("Komisyon üyesi", "")])
    if not oturumlar:
        b.paragraf("Planda oturum bulunmuyor.")
    return b.kaydet(hedef)


# -------------------------------------------------- 06 kâğıt sarf tutanağı

def kagit_sarf_tutanaklari(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    kurum = _kurum(vt)
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    oturumlar = hizmet.plan_oturumlari(vt, plan_id)
    b = Belge(kurum["ustbilgi"], "Sınav Kâğıdı Sarf Tutanağı",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    b.paragraf(
        "Aşağıdaki sınavlarda kullanılmak üzere teslim alınan, kullanılan ve iade edilen "
        "sınav kâğıdı sayıları karşılarında gösterilmiştir.", bosluk=10)
    b.tablo(["Sınav", "Tarih / Saat", "Öğrenci", "Teslim alınan", "Kullanılan", "İade"],
            [(o["etiket"], _oturum_saat(o), o["ogrenci_sayisi"], "", "", "")
             for o in oturumlar],
            [30, 16, 10, 16, 14, 14])
    b.dayanak_notu("Sayılar sınav sonrası komisyonca elle doldurulur. " + ALTBILGI_NOTU)
    b.imza_blogu([("Komisyon üyesi", ""), ("Komisyon üyesi", "")], kurum["mudur"])
    return b.kaydet(hedef)


# -------------------------------------------------- 07 görev sayacı raporu

def gorev_sayac_raporu(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    kurum = _kurum(vt)
    sayaclar = hizmet.gorev_sayaclari(vt)
    b = Belge(kurum["ustbilgi"], "Öğretmen Sınav Görevi Sayacı",
              f"{kurum['yil']} Öğretim Yılı")
    b.paragraf(
        "Aşağıdaki sayılar okulun kendi kayıtlarından alınmıştır; ek ders ücreti tutarı "
        "hesaplanmamıştır. Tahakkuk işlemleri yetkili sistemde yapılır.", bosluk=10)
    b.tablo(["Adı Soyadı", "Branşı", "Görevi", "Komisyon", "Gözcülük", "Toplam", "Durum"],
            [(s["ad"], s["brans"], s["unvan"], s["komisyon"], s["gozcu"],
              s["komisyon"] + s["gozcu"],
              "sınır aşıldı" if s["asildi_mi"]
              else ("ücretlendirilemez" if not s["ucretlendirilebilir"] else ""))
             for s in sayaclar],
            [24, 18, 14, 10, 10, 8, 16])
    b.dayanak_notu(
        "Karar md.12/2-a: bir öğretim yılında bir kişiye 12'den fazla sınav komisyon üyeliği "
        "ve 15'ten fazla sınav gözcülüğü için ücret ödenmez. 8. Dönem Toplu Sözleşme md.4 "
        "gereği 2025-2026 ve 2026-2027 öğretim yıllarında bu sınırlar uygulanmaz. "
        "Karar md.12/2-c gereği yöneticilere sınav görevi için ücret ödenmez. " + ALTBILGI_NOTU)
    b.imza_blogu([("Düzenleyen", "")], kurum["mudur"])
    return b.kaydet(hedef)


# ------------------------------------------------- 08 evrak teslim tutanağı

def evrak_teslim_tutanagi(vt: Veritabani, plan_id: int, hedef: Path,
                          bugun: date | None = None) -> str:
    kurum = _kurum(vt)
    plan, _ = hizmet.plan_yukle(vt, plan_id)
    cizelge = hizmet.teslim_cizelgesi(vt, plan_id)
    ozet = hizmet.teslim_ozeti(vt, plan_id, bugun)
    b = Belge(kurum["ustbilgi"], "Sınav Evrakı Teslim-Tesellüm Tutanağı",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    b.paragraf(
        f"Toplam {ozet['toplam']} evrak kaleminden {ozet['teslim']} adedi teslim alınmış, "
        f"{ozet['bekliyor']} adedi beklenmekte, {ozet['gecikti']} adedi gecikmiştir.",
        bosluk=10)
    if ozet["gecikti"]:
        b.uyari(f"{ozet['gecikti']} evrak kalemi süresinde teslim edilmemiştir.")

    b.tablo(["Sınav", "Tarih", "Evrak", "Adet", "Teslim eden", "Teslim alan", "Durum"],
            [(s.oturum_etiketi, tr_tarih(s.tarih), s.evrak_adi,
              "" if s.adet is None else s.adet, s.teslim_eden or "",
              s.teslim_alan or "", s.durum(bugun)) for s in cizelge],
            [22, 10, 20, 7, 16, 16, 12])
    b.dayanak_notu(
        "Teslim eden komisyon üyesi ile teslim alan görevli aynı kişi olamaz. Teslim süresi "
        "sınav tarihini izleyen ilk iş günüdür; süre okul uygulamasıdır. " + ALTBILGI_NOTU)
    b.imza_blogu([("Teslim eden", ""), ("Teslim alan", "")], kurum["mudur"])
    return b.kaydet(hedef)


# ----------------------------------------------------------------- paket

URETICILER = {
    "01_sinav_programi": lambda vt, pid, yol: sinav_programi(vt, pid, yol, False),
    "02_sinav_programi_gorevli": lambda vt, pid, yol: sinav_programi(vt, pid, yol, True),
    "03_gorevlendirme_oluru": gorevlendirme_oluru,
    "04_komisyon_tutanaklari": komisyon_tutanaklari,
    "05_yoklama_listeleri": yoklama_listeleri,
    "06_kagit_sarf_tutanaklari": kagit_sarf_tutanaklari,
    "07_gorev_sayac_raporu": gorev_sayac_raporu,
    "08_evrak_teslim_tutanagi": evrak_teslim_tutanagi,
}


def evrak_uret(vt: Veritabani, plan_id: int, hedef_klasor: Path,
               secilenler: list[str] | None = None) -> list[tuple[Path, str]]:
    """Seçilen evrakları üretir; (dosya yolu, SHA-256) listesi döndürür.

    Üretilen her belge `belge_surumu` ve `evrak_kaydi` tablolarına işlenir;
    aynı belge yeniden üretilirse sürüm numarası artar.
    """
    hedef_klasor = Path(hedef_klasor)
    hedef_klasor.mkdir(parents=True, exist_ok=True)
    istenen = list(secilenler) if secilenler else [e.anahtar for e in EVRAKLAR]
    dosya_adlari = {e.anahtar: e.dosya_adi for e in EVRAKLAR}
    uretilen: list[tuple[Path, str]] = []
    for anahtar in istenen:
        uretici = URETICILER.get(anahtar)
        if uretici is None:
            raise hizmet.HizmetHatasi(f"Bilinmeyen evrak türü: {anahtar}")
        yol = hedef_klasor / dosya_adlari[anahtar]
        ozet = uretici(vt, plan_id, yol)
        hizmet.evrak_surumu_kaydet(vt, anahtar, str(plan_id), yol, ozet)
        uretilen.append((yol, ozet))
    return uretilen
