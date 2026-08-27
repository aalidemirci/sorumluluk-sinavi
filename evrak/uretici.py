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

GUN_ADLARI = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma",
              "Cumartesi", "Pazar")


@dataclass(frozen=True)
class EvrakTuru:
    anahtar: str
    ad: str
    dosya_adi: str


EVRAKLAR = (
    EvrakTuru("01_sinav_programi", "Sınav programı (öğrenci nüshası)", "01_sinav_programi.docx"),
    EvrakTuru("02_sinav_programi_gorevli", "Sınav programı (görevli nüshası)",
              "02_sinav_programi_gorevli.docx"),
    EvrakTuru("03_gorevlendirme_oluru", "Görevlendirme çizelgesi ve tebliğ-tebellüğ",
              "03_gorevlendirme_cizelgesi.docx"),
    EvrakTuru("04_komisyon_tutanaklari", "Komisyon tutanakları", "04_komisyon_tutanaklari.docx"),
    EvrakTuru("05_yoklama_listeleri", "Yoklama / salon listeleri", "05_yoklama_listeleri.docx"),
    EvrakTuru("06_kagit_sarf_tutanaklari", "Kâğıt sarf tutanakları",
              "06_kagit_sarf_tutanaklari.docx"),
    EvrakTuru("07_gorev_sayac_raporu", "Öğretmen görev sayacı raporu",
              "07_gorev_sayac_raporu.docx"),
    EvrakTuru("08_evrak_teslim_tutanagi", "Evrak teslim tutanağı",
              "08_evrak_teslim_tutanagi.docx"),
    EvrakTuru("09_ilan_sinav_takvimi", "İLAN: sınav takvimi (KVKK uyumlu)",
              "09_ilan_sinav_takvimi.docx"),
    EvrakTuru("10_ilan_ogrenci_cizelgesi", "İLAN: öğrenci sınav çizelgesi (KVKK uyumlu)",
              "10_ilan_ogrenci_cizelgesi.docx"),
)

# Okul web sayfasında yayımlanmak üzere üretilen, kişisel veri barındırmayan
# ya da maskelenmiş çıktılar.
ILAN_EVRAKLARI = frozenset({"09_ilan_sinav_takvimi", "10_ilan_ogrenci_cizelgesi"})


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
    """Komisyon bazlı görevlendirme çizelgesi ve tebliğ-tebellüğ bölümü.

    Her satır bir sınav komisyonudur: sınav, öğrenci sayısı, tarih, saat,
    salon, komisyon üyeleri ve gözcüler bir arada görünür. Altta görevli her
    personelin tarih yazıp imzalayacağı tebliğ-tebellüğ tablosu vardır.
    """
    kurum = _kurum(vt)
    plan, bilgi = hizmet.plan_yukle(vt, plan_id)
    oturumlar = hizmet.plan_oturumlari(vt, plan_id)
    b = Belge(kurum["ustbilgi"], "Sınav Görevlendirme Çizelgesi",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu), yatay=True)
    if bilgi["kesin_mi"]:
        b.paragraf(f"Müdür onay no: {bilgi['mudur_onay_no']}", kalin=True, boyut=9.5)
    b.paragraf(
        f"{kurum['yil']} öğretim yılı sorumluluk sınavlarında, Ortaöğretim Kurumları "
        "Yönetmeliği'nin 58 inci maddesinin ikinci fıkrası uyarınca aşağıdaki komisyonların "
        "kurulması ve karşılarında adı yazılı öğretmenlerin görevlendirilmeleri hususunu "
        "olurlarınıza arz ederim.", bosluk=12)

    satirlar = []
    for oturum in oturumlar:
        komisyon = [ad for ad, rol, _ in oturum["gorevliler"] if rol == "komisyon_uyesi"]
        gozculer = [ad for ad, rol, _ in oturum["gorevliler"] if rol == "gozcu"]
        ders = oturum["ders"]
        if "/" in oturum["duzey"]:
            ders += f" ({oturum['duzey'].replace('/', '. ve ')}. sınıflar birleştirilmiştir)"
        else:
            ders = f"{oturum['duzey']}. sınıf — {ders}"
        if oturum["tur"] == "uygulama":
            ders += " (uygulama sınavı)"
        satirlar.append((
            ders, oturum["ogrenci_sayisi"], tr_tarih(oturum["tarih"]), oturum["saat"],
            ", ".join(oturum["salonlar"]) or "—",
            "\n".join(komisyon) or "atanmadı",
            "\n".join(gozculer) or "atanmadı",
        ))
    b.tablo(["Sınav Yapılacak Ders veya Dersler", "Öğrenci\nSayısı", "Sınav\nTarihi",
             "Sınav\nSaati", "Sınav Salonu", "Komisyon Üyeleri", "Gözcü / Gözcüler"],
            satirlar, [26, 7, 9, 7, 13, 19, 19])

    b.dayanak_notu(
        "Komisyon iki sınav öğretmeninden oluşur, en az biri dersin alanındandır; her sınav "
        "salonu için bir gözcü öğretmen görevlendirilir (OKY md.58/2-a, 2-b). Farklı "
        "sınıflardaki aynı dersin öğrenci sayısı toplamda otuzu aşmıyorsa sınavlar "
        "birleştirilerek tek komisyonla yapılabilir (md.58/2-c). Bir sınavda aynı kişiye hem "
        "komisyon üyeliği hem gözcülük verilmez ve yöneticilere sınav görevi için ücret "
        "ödenmez (Karar md.12/2-b, 2-c). " + ALTBILGI_NOTU)

    b.imza_blogu([("Düzenleyen", "")], kurum["mudur"])

    # --- tebliğ-tebellüğ ---
    b.sayfa_sonu()
    b.yeni_bolum_basligi("Tebliğ - Tebellüğ Belgesi",
                         _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    b.paragraf(
        "Yukarıdaki çizelgede gösterilen sınav görevleri tarafıma tebliğ edilmiştir. "
        "Görev yerimi, tarihini ve saatini okudum, anladım.", bosluk=12)
    gorevliler = hizmet.gorevli_listesi(vt, plan_id)
    b.tablo(["S. No", "Adı Soyadı", "Branşı", "Komisyon\nüyeliği", "Gözcülük",
             "Tebliğ Tarihi", "İmza"],
            [(sira, g["ad"], g["brans"], g["komisyon"], g["gozcu"], "", "")
             for sira, g in enumerate(gorevliler, 1)],
            [6, 24, 18, 9, 8, 14, 21])
    b.dayanak_notu(
        "Tebliğ tarihi ve imza görevli tarafından elle doldurulur. " + ALTBILGI_NOTU)
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



# ============================================ 09 / 10 ilan çizelgeleri (KVKK)

KVKK_NOTU = (
    "Bu çizelge okul web sayfasında ilan edilmek üzere hazırlanmıştır. 6698 sayılı Kişisel "
    "Verilerin Korunması Kanunu gereği öğrencilerin açık ad ve soyadı, T.C. kimlik numarası "
    "ve iletişim bilgileri yayımlanmaz. Sınavlarda görevlendirilen öğretmenlerin adları da "
    "bu çizelgede yer almaz; belge kişi adı taşımaksızın okul müdürlüğünce çıkarılmıştır."
)


def ilan_sinav_takvimi(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    """Okul web sayfasında ilan edilecek sınav takvimi.

    Hiçbir kişisel veri içermez: ne öğrenci ne görevli adı geçer. Yalnız
    hangi dersin sınavının ne zaman ve nerede yapılacağı yazar.
    """
    kurum = _kurum(vt)
    plan, bilgi = hizmet.plan_yukle(vt, plan_id)
    takvim = hizmet.ilan_takvimi(vt, plan_id)
    b = Belge(kurum["ustbilgi"], "Sorumluluk Sınavı Takvimi",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    if not bilgi["kesin_mi"]:
        b.uyari("TASLAK — plan müdür onayıyla kesinleşmeden ilan edilmemelidir.")
    b.paragraf(
        f"{kurum['yil']} öğretim yılı sorumluluk sınavları aşağıdaki takvime göre "
        "yapılacaktır. Öğrencilerimizin sınav saatinden en az on beş dakika önce sınav "
        "salonunda hazır bulunmaları gerekmektedir.", bosluk=12)

    gunler: dict = {}
    for kayit in takvim:
        gunler.setdefault(kayit["tarih"], []).append(kayit)
    satirlar = []
    for tarih in sorted(gunler):
        for sira, kayit in enumerate(sorted(gunler[tarih], key=lambda k: k["saat"])):
            satirlar.append((
                f"{tr_tarih(tarih)} {GUN_ADLARI[tarih.weekday()]}" if sira == 0 else "",
                kayit["saat"], kayit["etiket"], f"{kayit['sure']} dk",
                kayit["salonlar"] or "—"))
    b.tablo(["Tarih", "Saat", "Ders", "Süre", "Salon"], satirlar, [22, 10, 38, 8, 22])

    b.paragraf(
        "Sınavla ilgili sorularınız için okul müdürlüğüne başvurabilirsiniz.",
        bosluk=6, boyut=9.5)
    b.dayanak_notu(
        "Sınav tarihleri Ortaöğretim Kurumları Yönetmeliği'nin 58 inci maddesi uyarınca "
        "belirlenmiştir. " + KVKK_NOTU)
    b.makam_satiri("Okul Müdürlüğü")
    return b.kaydet(hedef)


def ilan_ogrenci_cizelgesi(vt: Veritabani, plan_id: int, hedef: Path,
                           gosterim: str = "no_ve_maskeli_ad") -> str:
    """Hangi öğrencinin hangi derslerden sınava gireceğini gösteren ilan çizelgesi.

    Öğrenci kendi satırını okul numarasından bulur; açık ad yayımlanmaz.
    Ad, seçilen biçime göre maskelenir ya da hiç yazılmaz.
    """
    kurum = _kurum(vt)
    plan, bilgi = hizmet.plan_yukle(vt, plan_id)
    ogrenciler = hizmet.ilan_ogrenci_cizelgesi(vt, plan_id, gosterim)
    b = Belge(kurum["ustbilgi"], "Öğrenci Sorumluluk Sınavı Çizelgesi",
              _alt_baslik(kurum, plan.parametreler.pencere_kodu))
    if not bilgi["kesin_mi"]:
        b.uyari("TASLAK — plan müdür onayıyla kesinleşmeden ilan edilmemelidir.")
    b.paragraf(
        "Aşağıdaki çizelgede her öğrencinin gireceği sorumluluk sınavları gösterilmiştir. "
        "Öğrencilerimiz kendi satırlarını okul numaralarından bulabilir; ad ve soyadı "
        "kişisel verilerin korunması amacıyla maskelenmiştir.", bosluk=12)

    satirlar = []
    for ogrenci in ogrenciler:
        for sira, sinav in enumerate(ogrenci["sinavlar"]):
            satirlar.append((
                ogrenci["etiket"] if sira == 0 else "",
                ogrenci["sube"] if sira == 0 else "",
                sinav["etiket"], tr_tarih(sinav["tarih"]), sinav["saat"],
                sinav["salonlar"] or "—"))
    b.tablo(["Öğrenci", "Şube", "Ders", "Tarih", "Saat", "Salon"],
            satirlar, [22, 8, 30, 12, 8, 20])

    b.paragraf(
        f"Çizelgede {len(ogrenciler)} öğrenci yer almaktadır. Bilgilerinde yanlışlık "
        "gördüğünüzü düşünüyorsanız okul müdürlüğüne başvurunuz.", bosluk=6, boyut=9.5)
    b.dayanak_notu(KVKK_NOTU)
    b.makam_satiri("Okul Müdürlüğü")
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
    "09_ilan_sinav_takvimi": ilan_sinav_takvimi,
}

# Öğrenci gösterim biçimi yalnız bu evraka geçirilir.
GOSTERIM_ALAN_URETICILER = {"10_ilan_ogrenci_cizelgesi": ilan_ogrenci_cizelgesi}


def evrak_uret(vt: Veritabani, plan_id: int, hedef_klasor: Path,
               secilenler: list[str] | None = None,
               ogrenci_gosterimi: str = "no_ve_maskeli_ad") -> list[tuple[Path, str]]:
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
        gosterimli = GOSTERIM_ALAN_URETICILER.get(anahtar)
        if uretici is None and gosterimli is None:
            raise hizmet.HizmetHatasi(f"Bilinmeyen evrak türü: {anahtar}")
        yol = hedef_klasor / dosya_adlari[anahtar]
        ozet = (gosterimli(vt, plan_id, yol, ogrenci_gosterimi) if gosterimli
                else uretici(vt, plan_id, yol))
        hizmet.evrak_surumu_kaydet(vt, anahtar, str(plan_id), yol, ozet)
        uretilen.append((yol, ozet))
    return uretilen
