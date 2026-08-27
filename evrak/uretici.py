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
from cekirdek.takvim import pencere_adi
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
    EvrakTuru("01_sinav_programi", "Sınav programı (öğrenci nüshası)",
              "01_sinav_programi.docx"),
    EvrakTuru("02_sinav_programi_gorevli", "Sınav programı (görevli nüshası)",
              "02_sinav_programi_gorevli.docx"),
    EvrakTuru("03_gorevlendirme_cizelgesi", "Görevlendirme çizelgesi ve tebliğ-tebellüğ",
              "03_gorevlendirme_cizelgesi.docx"),
    EvrakTuru("04_gorev_sayac_raporu", "Öğretmen görev sayacı raporu",
              "04_gorev_sayac_raporu.docx"),
    EvrakTuru("05_ilan_sinav_takvimi", "İLAN: sınav takvimi (KVKK uyumlu)",
              "05_ilan_sinav_takvimi.docx"),
    EvrakTuru("06_ilan_ogrenci_cizelgesi", "İLAN: öğrenci sınav çizelgesi (KVKK uyumlu)",
              "06_ilan_ogrenci_cizelgesi.docx"),
)

# Komisyon tutanağı, yoklama listesi, kâğıt sarf tutanağı ve evrak teslim
# tutanağı bu setten çıkarıldı. İlk üçü e-Okul'dan alınır; teslim takibi ise
# ekrandaki çizelgeden yürütülür, ayrıca belge üretmeye gerek yoktur.

# Okul web sayfasında yayımlanmak üzere üretilen, kişisel veri barındırmayan
# ya da maskelenmiş çıktılar.
ILAN_EVRAKLARI = frozenset({"05_ilan_sinav_takvimi", "06_ilan_ogrenci_cizelgesi",
                            "07_ilan_basvuru_duyurusu"})


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
    return (f"{kurum['yil']} Öğretim Yılı • Sorumluluk Sınavları • "
            f"{pencere_adi(pencere_kodu)} dönemi")


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
    b.imza_blogu([("Düzenleyen", "")], kurum["mudur"])
    return b.kaydet(hedef)


# ------------------------------------------------------ 03 görevlendirme oluru

def gorevlendirme_cizelgesi(vt: Veritabani, plan_id: int, hedef: Path) -> str:
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








# -------------------------------------------------- 07 görev sayacı raporu

def gorev_sayac_raporu(vt: Veritabani, plan_id: int, hedef: Path) -> str:
    """Öğretim yılı boyunca kişi başına görev dağılımı; dönem dökümü dâhil.

    Rapor kesinleşmemiş planlardan da üretilir: görev yükünü kesinleştirmeden
    önce görmek gerekir. Taslak plan varsa belgeye uyarı düşülür.
    """
    kurum = _kurum(vt)
    sayaclar = hizmet.gorev_havuzu_ozeti(vt)
    taslaklar = hizmet.taslak_pencereler(vt)
    b = Belge(kurum["ustbilgi"], "Öğretmen Sınav Görevi Sayacı",
              f"{kurum['yil']} Öğretim Yılı — üç sınav dönemi toplamı")
    if taslaklar:
        b.uyari("TASLAK VERİ — şu dönemlerin planı henüz müdür onayıyla kesinleşmemiştir: "
                + ", ".join(taslaklar) + ". Sayılar plan değiştikçe değişebilir.")
    b.paragraf(
        "Aşağıdaki sayılar okulun kendi kayıtlarından alınmıştır; ek ders ücreti tutarı "
        "hesaplanmamıştır. Tahakkuk işlemleri yetkili sistemde yapılır. Görev dağılımı "
        "planlanırken önceki dönemlerin sayaçları da dikkate alınır.", bosluk=10)

    def donem(kayit: dict, kod: str) -> str:
        komisyon, gozcu = kayit["pencereler"].get(kod, (0, 0))
        return f"{komisyon}+{gozcu}" if (komisyon or gozcu) else "—"

    b.tablo(["Adı Soyadı", "Branşı", "Eylül", "Şubat", "Haziran", "Komisyon",
             "Gözcülük", "Toplam", "Durum"],
            [(k["ad"], k["brans"], donem(k, "P1"), donem(k, "P2"), donem(k, "P3"),
              k["komisyon"], k["gozcu"], k["toplam"],
              "sınır aşıldı" if k["asildi_mi"]
              else ("ücretlendirilemez" if not k["ucretlendirilebilir"] else ""))
             for k in sayaclar],
            [22, 16, 7, 7, 7, 9, 9, 8, 12])
    if not sayaclar:
        b.paragraf(
            "Henüz görevlendirme yapılmamıştır. Sınav Planı adımında planı üretip "
            "kaydettikten sonra bu rapor dolacaktır.", bosluk=8)
    b.dayanak_notu(
        "Dönem sütunlarında komisyon üyeliği + gözcülük sayısı gösterilir. "
        "Karar md.12/2-a: bir öğretim yılında bir kişiye 12'den fazla sınav komisyon "
        "üyeliği ve 15'ten fazla sınav gözcülüğü için ücret ödenmez. 8. Dönem Toplu "
        "Sözleşme md.4 gereği 2025-2026 ve 2026-2027 öğretim yıllarında bu sınırlar "
        "uygulanmaz. Karar md.12/2-c gereği yöneticilere sınav görevi için ücret "
        "ödenmez. " + ALTBILGI_NOTU)
    b.imza_blogu([("Düzenleyen", "")], kurum["mudur"])
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

# --------------------------------------------- 07 / 08 başvuru kapısı belgeleri
# Bu ikisi PLANA değil PENCEREYE bağlıdır: duyuru plan doğmadan önce
# yayımlanır. Bu yüzden plan kapsamlı URETICILER sözleşmesine girmezler.

def basvuru_duyurusu(vt: Veritabani, pencere_kodu: str, hedef: Path) -> str:
    """Okul web sayfasında ilan edilecek başvuru duyurusu.

    İLAN belgesidir: kişi adı taşımaz, makam satırıyla çıkar. Beklemeli ve
    devamsız öğrencilerin sorumluluk sınavına alınabilmesi için yazılı başvuru
    yapmaları gerektiğini ve son günü duyurur — OKY md.58/2-d.
    """
    kurum = _kurum(vt)
    duyuru = hizmet.duyuru_getir(vt, pencere_kodu)
    if not duyuru:
        raise hizmet.HizmetHatasi(
            f"{pencere_adi(pencere_kodu)} penceresi için duyuru kaydedilmemiş; "
            "önce Başvuru adımından duyuruyu kaydedin.")
    pencere = hizmet.pencereleri_getir(vt)[pencere_kodu]
    b = Belge(kurum["ustbilgi"], "Sorumluluk Sınavı Başvuru Duyurusu",
              _alt_baslik(kurum, pencere_kodu))
    b.paragraf(
        f"{kurum['yil']} öğretim yılı {pencere_adi(pencere_kodu)} dönemi sorumluluk "
        f"sınavları {tr_tarih(pencere[0])} – {tr_tarih(pencere[1])} tarihleri arasında "
        "yapılacaktır.", bosluk=10)
    b.paragraf(
        "Okulumuzdan mezun olamayan 12. sınıf öğrencileri ile devamsızlık tebligatı "
        "yapıldığı hâlde okula veya sınavlara katılımları sağlanamayan öğrenciler, "
        "sorumluluk sınavına girmek istediklerini yazılı olarak okul müdürlüğüne "
        "bildirmedikleri takdirde sınav planına dâhil EDİLMEZ.", kalin=True, bosluk=10)
    b.bilgi_satirlari([
        ("Başvuru son günü", tr_tarih(duyuru["basvuru_son_gunu"])),
        ("Başvuru şekli", "Okul müdürlüğüne yazılı dilekçe"),
        ("Sınav dönemi", f"{tr_tarih(pencere[0])} – {tr_tarih(pencere[1])}"),
        ("Duyuru tarihi", tr_tarih(duyuru["duyuru_tarihi"])),
        ("Yayım yeri", duyuru["yayim_yeri"] or "Okul müdürlüğünce belirlenir"),
    ])
    b.paragraf(
        "Belirtilen son günden sonra yapılan başvurular, sınav tarihinden en az beş iş günü "
        "önce ulaşmış olmak kaydıyla okul müdürünün onayıyla değerlendirilir. Diğer "
        "öğrencilerimizin başvuru yapmasına gerek yoktur; onlar plana doğrudan alınır.",
        bosluk=8, boyut=9.5)
    b.dayanak_notu(
        "Millî Eğitim Bakanlığı Ortaöğretim Kurumları Yönetmeliği'nin 58 inci maddesinin "
        "ikinci fıkrasının (d) bendi (Ek:RG-8/9/2023-32303). " + KVKK_NOTU)
    b.makam_satiri("Okul Müdürlüğü")
    return b.kaydet(hedef)


def plan_disi_tutanagi(vt: Veritabani, pencere_kodu: str, hedef: Path) -> str:
    """Başvurusu bulunmadığı için plana alınmayan öğrencilerin tutanağı.

    İLAN DEĞİLDİR: okul içi kayıttır ve öğrenci adı taşır. Bir öğrenciyi
    plandan çıkarmak hakkını etkileyen bir karardır; itiraz gelirse dayanağı
    bu tutanaktır.
    """
    kurum = _kurum(vt)
    duyuru = hizmet.duyuru_getir(vt, pencere_kodu)
    satirlar_ham = hizmet.plan_disi_birakilanlar(vt, pencere_kodu)
    b = Belge(kurum["ustbilgi"], "Başvuru Yapmayanların Plan Dışı Bırakılması Tutanağı",
              _alt_baslik(kurum, pencere_kodu))
    if not duyuru:
        b.uyari("Bu pencere için başvuru duyurusu kaydedilmemiştir; tutanağın dayanağı eksiktir.")
    b.paragraf(
        f"{kurum['yil']} öğretim yılı {pencere_adi(pencere_kodu)} dönemi sorumluluk sınavı "
        "planı hazırlanırken, aşağıda kimlikleri yazılı öğrencilerin yazılı başvurusu "
        "bulunmadığından plana dâhil edilmedikleri tespit edilmiştir.", bosluk=10)
    if duyuru:
        b.bilgi_satirlari([
            ("Duyuru tarihi", tr_tarih(duyuru["duyuru_tarihi"])),
            ("Duyuru belge referansı", duyuru["belge_referansi"]),
            ("Yayım yeri", duyuru["yayim_yeri"] or "—"),
            ("Başvuru son günü", tr_tarih(duyuru["basvuru_son_gunu"])),
        ])
    if satirlar_ham:
        b.tablo(
            ["Okul no", "Adı Soyadı", "Şube", "Grup", "Durum"],
            [(s["okul_no"], s["ad_soyad"], s["sube"], s["grup"], s["ozet"])
             for s in satirlar_ham],
            [12, 30, 10, 30, 18])
    else:
        b.paragraf("Bu dönemde plan dışı bırakılan öğrenci bulunmamaktadır.", bosluk=8)
    b.paragraf(
        f"Toplam {len(satirlar_ham)} öğrenci plan dışında bırakılmıştır. "
        "\"Karar bekliyor\" durumundaki öğrenciler için henüz başvuru kararı girilmemiştir; "
        "plan üretilmeden önce bu kayıtların tamamlanması gerekir.", bosluk=8, boyut=9.5)
    b.dayanak_notu(
        "Millî Eğitim Bakanlığı Ortaöğretim Kurumları Yönetmeliği'nin 58 inci maddesinin "
        "ikinci fıkrasının (d) bendi (Ek:RG-8/9/2023-32303) uyarınca, yazılı başvurusu "
        "bulunmayan öğrenciler sorumluluk sınavı planına dâhil edilmemiştir. Bu belge okul "
        "içi kayıt niteliğindedir; ilan edilmez.")
    b.imza_blogu([("Düzenleyen", ""), ("Düzenleyen", "")], olur_adi=kurum["mudur"])
    return b.kaydet(hedef)


PENCERE_EVRAKLARI = (
    EvrakTuru("07_ilan_basvuru_duyurusu", "İLAN: başvuru duyurusu (KVKK uyumlu)",
              "07_ilan_basvuru_duyurusu.docx"),
    EvrakTuru("08_basvuru_plan_disi_tutanagi", "Plan dışı bırakılanlar tutanağı",
              "08_basvuru_plan_disi_tutanagi.docx"),
)

PENCERE_URETICILER = {
    "07_ilan_basvuru_duyurusu": basvuru_duyurusu,
    "08_basvuru_plan_disi_tutanagi": plan_disi_tutanagi,
}


def pencere_evraki_uret(vt: Veritabani, pencere_kodu: str, hedef_klasor: Path,
                        secilenler: list[str] | None = None) -> list[tuple[Path, str]]:
    """Pencere kapsamlı başvuru belgelerini üretir.

    Sürüm izi plan kimliğine değil `öğretim yılı|pencere` anahtarına bağlanır;
    bu belgeler plandan önce doğar.
    """
    hedef_klasor = Path(hedef_klasor)
    hedef_klasor.mkdir(parents=True, exist_ok=True)
    istenen = list(secilenler) if secilenler else [e.anahtar for e in PENCERE_EVRAKLARI]
    dosya_adlari = {e.anahtar: e.dosya_adi for e in PENCERE_EVRAKLARI}
    ogretim_yili = hizmet.ayarlari_getir(vt).get("ogretim_yili", "")
    kayit_anahtari = f"{ogretim_yili}|{pencere_kodu}"
    uretilen: list[tuple[Path, str]] = []
    for anahtar in istenen:
        uretici = PENCERE_URETICILER.get(anahtar)
        if uretici is None:
            raise hizmet.HizmetHatasi(f"Bilinmeyen evrak türü: {anahtar}")
        yol = hedef_klasor / dosya_adlari[anahtar]
        ozet = uretici(vt, pencere_kodu, yol)
        hizmet.evrak_surumu_kaydet(vt, anahtar, kayit_anahtari, yol, ozet)
        uretilen.append((yol, ozet))
    return uretilen


# ----------------------------------------------------------------- paket

URETICILER = {
    "01_sinav_programi": lambda vt, pid, yol: sinav_programi(vt, pid, yol, False),
    "02_sinav_programi_gorevli": lambda vt, pid, yol: sinav_programi(vt, pid, yol, True),
    "03_gorevlendirme_cizelgesi": gorevlendirme_cizelgesi,
    "04_gorev_sayac_raporu": gorev_sayac_raporu,
    "05_ilan_sinav_takvimi": ilan_sinav_takvimi,
}

# Öğrenci gösterim biçimi yalnız bu evraka geçirilir.
GOSTERIM_ALAN_URETICILER = {"06_ilan_ogrenci_cizelgesi": ilan_ogrenci_cizelgesi}


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
