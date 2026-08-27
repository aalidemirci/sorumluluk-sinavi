"""Sorumluluk sınavı kuralları — tek doğruluk kaynağı.

Her kural burada bir kez tanımlanır ve bir kez uygulanır. Planlayıcı da,
elle yapılan düzenlemeler de aynı `dogrula_plan` çağrısından geçer;
planlayıcının ürettiği plan ayrıca doğrulanır. Kuralların ikinci bir kopyası
hiçbir katmanda tutulmaz.

Kimlik önekleri:
    SG  sorumluluğun doğuşu (içe aktarılan veriye dair bilgi kuralları)
    SP  sınav planlaması
    EK  ek ders görev sayacı (parasal hesap yapılmaz)
    TS  evrak teslim takibi
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

from .modeller import (
    Ciddiyet, GorevRolu, Gorevlendirme, IkiAsamaliSayim, Ihlal, Oturum,
    OturumTuru, Personel, Plan, Salon,
)
from .metin import esitle, siralama_anahtari


# OKY md.58/2-c: farklı sınıflardaki aynı dersin öğrenci sayısı toplamda
# otuzu aşmıyorsa sınavlar birleştirilerek tek komisyonla yapılabilir.
BIRLESTIRME_UST_SINIRI = 30

# OKY md.58/2-b: öğrenci sayısının otuzu aşması hâlinde birden fazla salon
# kullanılır ve her salon için ayrıca bir gözcü görevlendirilir.
SALON_OGRENCI_UST_SINIRI = 30

# OKY md.58/2-a: iki sınav öğretmeni (en az biri alan öğretmeni).
KOMISYON_UYE_SAYISI = 2

# Karar md.12/2-a: bir öğretim yılında bir kişiye 12'den fazla komisyon
# üyeliği ve 15'ten fazla gözcülük için ücret ödenmez.
YILLIK_KOMISYON_SINIRI = 12
YILLIK_GOZCU_SINIRI = 15

# 8. Dönem Toplu Sözleşme md.4 gereği bu öğretim yıllarında yukarıdaki
# sınırlar uygulanmaz; sayaç yine tutulur ve gösterilir.
SINIRSIZ_OGRETIM_YILLARI = frozenset({"2025-2026", "2026-2027"})


@dataclass(frozen=True)
class KuralTanimi:
    kimlik: str
    baslik: str
    dayanak: str
    ciddiyet: Ciddiyet
    aciklama: str


def _k(kimlik: str, baslik: str, dayanak: str, ciddiyet: Ciddiyet, aciklama: str) -> KuralTanimi:
    return KuralTanimi(kimlik, baslik, dayanak, ciddiyet, aciklama)


KURALLAR: dict[str, KuralTanimi] = {t.kimlik: t for t in (
    # --- SG: sorumluluğun doğuşu (içe aktarma bilgisi) --------------------
    _k("SG-05", "Nakil/geçiş kaynağı ayrı tutulur", "OKY md.58/1 son cümle", Ciddiyet.BILGI,
       "Nakil ve geçişler nedeniyle ortaya çıkan sorumlu dersler 3/6 sayacına dâhil edilmez; "
       "kayıt kaynağı 'basarisizlik' veya 'nakil_gecis' olarak ayrı tutulur."),
    _k("SG-06", "Tavan aşımı hata değildir", "OKY md.58/1; SG-06 yorum notu", Ciddiyet.BILGI,
       "İçe aktarılan veride 3/6 tavanını aşan öğrenci bulunabilir (mezun olamayan 12. sınıf, "
       "nakil, olağanüstü dönem). Bu içe aktarmada hata sayılmaz, yalnız işaretlenir."),

    # --- SP: planlama ------------------------------------------------------
    _k("SP-01", "Sınav penceresi", "OKY md.58/2-a (Değişik ibare:RG-15/11/2022-32014)", Ciddiyet.ENGEL,
       "Sınav tarihi seçilen pencereye düşmelidir: birinci dönemin ilk iki haftası (P1), "
       "ikinci dönemin ilk iki haftası (P2) veya son iki haftası (P3)."),
    _k("SP-02", "Komisyon ve gözcü", "OKY md.58/2-a (gözcü ibaresi Ek:RG-8/9/2023-32303)", Ciddiyet.ENGEL,
       "Sınav iki alan öğretmeni, bulunmaması hâlinde biri alan öğretmeni olmak üzere iki "
       "öğretmen ve gözcü öğretmen tarafından yapılır. İki alan öğretmeni bulunamıyorsa "
       "gerekçe zorunludur."),
    _k("SP-03", "Gözcü sayısı = salon sayısı", "OKY md.58/2-b + okul kararı", Ciddiyet.ENGEL,
       "Öğrenci sayısının otuzu aşması ve/veya birden fazla salon kullanılması hâlinde her "
       "sınav salonu için bir gözcü görevlendirilir. Salon başına bir gözcü sayılması okul "
       "kararıdır; mevzuat 'ayrıca bir gözcü daha' der."),
    _k("SP-04", "Düzey birleştirme", "OKY md.58/2-c (Ek cümle:RG-8/9/2023-32303)", Ciddiyet.ENGEL,
       "Farklı sınıflardaki aynı dersin öğrenci sayısı toplamda otuzu aşmıyorsa sınavlar "
       "birleştirilebilir. Aynı öğrenci aynı dersin iki düzeyinden sorumluysa birleştirilemez, "
       "ayrı ayrı sınava alınır."),
    _k("SP-05", "Hafta sonu ve müdür onayı", "OKY md.58/2-ç", Ciddiyet.ENGEL,
       "Sınavlar dersleri aksatmayacak biçimde hafta içinde planlanır; gerektiğinde cumartesi "
       "ve pazar da yapılabilir, bu durumda gerekçe kaydedilir. Plan müdür onayıyla kesinleşir."),
    _k("SP-06", "İki aşamalı dersler", "OKY md.58/2-e (Ek:RG-22/2/2025-32821)", Ciddiyet.ENGEL,
       "Türk dili ve edebiyatı ile yabancı dil derslerinin sorumluluk sınavları yazılı ve "
       "uygulamalı olarak iki aşamada yapılır. Komisyonların aynı üyelerden oluşturulması esastır."),
    _k("SP-10", "Sınav süresi", "ÖDY md.5/1-l", Ciddiyet.ENGEL,
       "Zorunlu hâller dışında yazılı sınav süresi bir ders saatini aşamaz."),
    _k("SP-11", "Günlük sınav sayısı", "ÖDY md.5/1-k", Ciddiyet.UYARI,
       "Bir günde yapılacak yazılı ve uygulamalı sınavların sayısının ikiyi geçmemesi esastır; "
       "zorunlu hâllerde bir sınav daha yapılabilir. Uygulama, sınırı öğrenci başına uygular."),
    # --- EK: görev sayacı (parasal hesap yok) -----------------------------
    _k("EK-03", "Aynı sınavda çifte rol yok", "Karar md.12/2-b", Ciddiyet.ENGEL,
       "Bir sınavda aynı kişiye hem komisyon üyeliği hem gözcülük verilemez."),

    # --- Davranışı belgeleyen kurallar (ihlal üretmez) ---------------------
    # Bunlar denetim değil, programın verdiği kararın dayanağıdır. SG-05 kayıt
    # kaynağını ayrı tutar (sorumluluk_kaydi.kaynak), SG-06 tavan aşımını hata
    # saymaz (içe aktarma tavan denetlemez), EK-04 yönetici görevini ücretsiz
    # işaretler (gorevlendirme.ucretlendirilebilir_mi).
    _k("EK-04", "Yönetici görevi ücretsizdir", "Karar md.12/2-c", Ciddiyet.BILGI,
       "Yöneticiler görevlendirilebilir fakat sınav görevi için ücret ödenmez. Bu program "
       "tutar hesaplamaz; yalnız görevi ücretsiz olarak işaretler."),
    _k("EK-05", "Yıllık görev sayacı", "Karar md.12/2-a; 8. Dönem Toplu Sözleşme md.4", Ciddiyet.UYARI,
       "Bir öğretim yılında bir kişiye 12'den fazla komisyon üyeliği ve 15'ten fazla gözcülük "
       "için ücret ödenmez. 2025-2026 ve 2026-2027 öğretim yıllarında bu sınırlar uygulanmaz, "
       "sayaç yine gösterilir."),

    # --- TS: evrak teslim takibi ------------------------------------------
    _k("TS-01", "Evrak teslim kaydı", "Okul uygulaması", Ciddiyet.UYARI,
       "Yapılan her oturum için sınav kâğıtlarının ve tutanakların teslim alındığı kaydedilir."),
    _k("TS-02", "Teslim gecikmesi", "Okul uygulaması", Ciddiyet.UYARI,
       "Sınav tarihinden sonra belirlenen süre içinde teslim edilmeyen evrak gecikmiş sayılır."),
    _k("TS-03", "Teslim eden ve alan ayrı kişidir", "Okul uygulaması", Ciddiyet.ENGEL,
       "Evrakı teslim eden komisyon üyesi ile teslim alan görevli aynı kişi olamaz."),
)}


def ihlal(kimlik: str, kayit: str, aciklama: str = "", ciddiyet: Ciddiyet | None = None) -> Ihlal:
    """Tanımlı bir kuraldan ihlal üretir; dayanak metni tanımdan gelir."""
    tanim = KURALLAR[kimlik]
    return Ihlal(tanim.kimlik, tanim.dayanak, kayit,
                 ciddiyet or tanim.ciddiyet, aciklama or tanim.aciklama)


# =========================================================== yardımcı hesap

def gereken_salon_sayisi(ogrenci_sayisi: int, salonlar: list[Salon],
                         salon_ust_siniri: int = SALON_OGRENCI_UST_SINIRI) -> int:
    """SP-03: öğrenciyi alacak en az salon sayısı.

    Salonların gerçek kapasiteleri kullanılır; hiçbir salona `salon_ust_siniri`
    değerinden fazla öğrenci konmaz.
    """
    if ogrenci_sayisi <= 0:
        return 0
    if not salonlar:
        raise ValueError("Salon tanımlanmadan salon sayısı hesaplanamaz.")
    kapasiteler = sorted((min(s.kapasite, salon_ust_siniri) for s in salonlar), reverse=True)
    kalan = ogrenci_sayisi
    for sira, kapasite in enumerate(kapasiteler, 1):
        kalan -= kapasite
        if kalan <= 0:
            return sira
    raise ValueError(
        f"{ogrenci_sayisi} öğrenci için tanımlı salonlar yetersiz "
        f"(toplam kapasite {sum(kapasiteler)})."
    )


def gunluk_sinav_yuku(oturumlar: list[Oturum], sayim: IkiAsamaliSayim) -> Counter:
    """(öğrenci, gün) -> o gün sayılan sınav adedi.

    İki aşamalı bir dersin yazılı ve uygulama oturumu `sayim` TEK ise birlikte
    tek sınav sayılır; öğrencinin o gün üç *oturumu* olsa da iki *sınavı* olur.
    """
    sayac: Counter = Counter()
    gorulen_birim: set[tuple[str, date, str]] = set()
    for oturum in oturumlar:
        for ogrenci in oturum.ogrenci_anahtarlari:
            if sayim is IkiAsamaliSayim.TEK and oturum.birim_anahtari:
                anahtar = (ogrenci, oturum.tarih, oturum.birim_anahtari)
                if anahtar in gorulen_birim:
                    continue
                gorulen_birim.add(anahtar)
            sayac[(ogrenci, oturum.tarih)] += 1
    return sayac


def yillik_sayac_asildi_mi(ogretim_yili: str, komisyon: int, gozcu: int) -> bool:
    """EK-05: 12/15 sınırının aşılıp aşılmadığı. Sınırsız yıllarda hep False."""
    if ogretim_yili in SINIRSIZ_OGRETIM_YILLARI:
        return False
    return komisyon > YILLIK_KOMISYON_SINIRI or gozcu > YILLIK_GOZCU_SINIRI


# ============================================================== doğrulayıcı

@dataclass
class DogrulamaBaglami:
    """Doğrulayıcının plana bakarken ihtiyaç duyduğu dış bilgiler."""

    pencere: tuple[date, date]
    personel: dict[int, Personel]
    ogrenci_adlari: dict[str, str] = None          # anahtar -> "Ad Soyad (No, Şube)"
    iki_asamali_dersler: frozenset[str] = frozenset()
    ogretim_yili: str = ""
    kisisel_gunluk_sinir: dict[str, int] = None    # öğrenci anahtarı -> yükseltilmiş sınır

    def __post_init__(self) -> None:
        if self.ogrenci_adlari is None:
            self.ogrenci_adlari = {}
        if self.kisisel_gunluk_sinir is None:
            self.kisisel_gunluk_sinir = {}

    def ogrenci_etiketi(self, anahtar: str) -> str:
        return self.ogrenci_adlari.get(anahtar, anahtar)

    def sinir(self, ogrenci: str, varsayilan: int) -> int:
        return self.kisisel_gunluk_sinir.get(ogrenci, varsayilan)


def _sp01_pencere(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    bas, bit = baglam.pencere
    return [
        ihlal("SP-01", o.anahtar,
              f"{o.ders_adi} sınavı {o.tarih.strftime('%d.%m.%Y')} tarihinde; seçilen pencere "
              f"{bas.strftime('%d.%m.%Y')}–{bit.strftime('%d.%m.%Y')} aralığıdır.")
        for o in plan.oturumlar if not bas <= o.tarih <= bit
    ]


def _sp05_hafta_sonu(plan: Plan) -> list[Ihlal]:
    return [
        ihlal("SP-05", o.anahtar,
              f"{o.ders_adi} sınavı {o.tarih.strftime('%d.%m.%Y')} "
              f"({'cumartesi' if o.tarih.weekday() == 5 else 'pazar'}) gününe konmuş; "
              "hafta sonu oturumu için gerekçe girilmelidir.")
        for o in plan.oturumlar if o.tarih.weekday() >= 5 and not o.hafta_sonu_gerekcesi.strip()
    ]


def _sp10_sure(plan: Plan) -> list[Ihlal]:
    ders_saati = plan.parametreler.oturum_suresi_dakika
    return [
        ihlal("SP-10", o.anahtar,
              f"{o.ders_adi} sınavı {o.sure_dakika} dakika; bir ders saati {ders_saati} dakikadır.")
        for o in plan.oturumlar if o.sure_dakika > ders_saati
    ]


def _sp11_gunluk_yuk(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    varsayilan = plan.parametreler.ogrenci_gunluk_sinav_siniri
    sayac = gunluk_sinav_yuku(plan.oturumlar, plan.parametreler.iki_asamali_sayim)
    gunluk_dersler: dict[tuple[str, date], list[str]] = defaultdict(list)
    for oturum in sorted(plan.oturumlar, key=lambda o: (o.tarih, o.saat)):
        for ogrenci in oturum.ogrenci_anahtarlari:
            tur = "Uygulamalı" if oturum.oturum_turu is OturumTuru.UYGULAMA else "Yazılı"
            gunluk_dersler[(ogrenci, oturum.tarih)].append(
                f"{oturum.saat.strftime('%H:%M')} {oturum.ders_adi} ({tur})")

    ihlaller = []
    for (ogrenci, gun), adet in sorted(sayac.items(), key=lambda x: (x[0][1], x[0][0])):
        sinir = baglam.sinir(ogrenci, varsayilan)
        if adet <= sinir:
            continue
        # Kişisel sınırı yükseltilmiş öğrencide bile aşım varsa bu bir hatadır.
        ciddiyet = Ciddiyet.ENGEL if adet > sinir + 1 else Ciddiyet.UYARI
        ihlaller.append(ihlal(
            "SP-11", f"{ogrenci}:{gun.isoformat()}",
            f"{baglam.ogrenci_etiketi(ogrenci)} — {gun.strftime('%d.%m.%Y')} — "
            f"{adet} sınav (sınır {sinir}): " + "; ".join(gunluk_dersler[(ogrenci, gun)]),
            ciddiyet))
    return ihlaller


def _ogrenci_slot_cakismasi(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    """Bir öğrenci aynı tarih ve saatte iki sınavda olamaz."""
    yerlesim: dict[tuple[str, date, object], list[Oturum]] = defaultdict(list)
    for oturum in plan.oturumlar:
        for ogrenci in oturum.ogrenci_anahtarlari:
            yerlesim[(ogrenci, oturum.tarih, oturum.saat)].append(oturum)
    return [
        ihlal("SP-11", f"{ogrenci}:{gun.isoformat()}:{saat}",
              f"{baglam.ogrenci_etiketi(ogrenci)} — {gun.strftime('%d.%m.%Y')} "
              f"{saat.strftime('%H:%M')} saatinde aynı anda iki sınavda: "
              + ", ".join(sorted(o.ders_adi for o in oturumlar)),
              Ciddiyet.ENGEL)
        for (ogrenci, gun, saat), oturumlar in sorted(yerlesim.items(), key=lambda x: str(x[0]))
        if len(oturumlar) > 1
    ]


def _sp04_birlestirme(plan: Plan) -> list[Ihlal]:
    ihlaller = []
    for oturum in plan.oturumlar:
        okul_nolari = [a.split("|", 1)[0] for a in oturum.ogrenci_anahtarlari]
        if len(okul_nolari) != len(set(okul_nolari)):
            ihlaller.append(ihlal(
                "SP-04", oturum.anahtar,
                f"{oturum.ders_adi} birleşik oturumunda aynı öğrenci iki düzeyden yer alıyor; "
                "bu öğrenciler ayrı ayrı sınava alınmalıdır."))
        if oturum.ogrenci_sayisi > BIRLESTIRME_UST_SINIRI and len(oturum.duzeyler) > 1:
            ihlaller.append(ihlal(
                "SP-04", oturum.anahtar,
                f"{oturum.ders_adi} için birleştirilen {len(oturum.duzeyler)} düzeyde toplam "
                f"{oturum.ogrenci_sayisi} öğrenci var; birleştirme sınırı "
                f"{BIRLESTIRME_UST_SINIRI} öğrencidir."))
    return ihlaller


def _sp06_iki_asamali(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    ihlaller = []
    birimler: dict[str, list[Oturum]] = defaultdict(list)
    for oturum in plan.oturumlar:
        if oturum.ders_adi in baglam.iki_asamali_dersler:
            birimler[oturum.birim_anahtari or oturum.anahtar].append(oturum)

    beklenen = Counter({OturumTuru.YAZILI: 1, OturumTuru.UYGULAMA: 1})
    for birim, oturumlar in sorted(birimler.items()):
        turler = Counter(o.oturum_turu for o in oturumlar)
        ders = oturumlar[0].ders_adi
        if turler != beklenen:
            ihlaller.append(ihlal(
                "SP-06", birim,
                f"{ders} iki aşamalı bir derstir; bir yazılı ve bir uygulama oturumu zorunludur "
                f"(bulunan: {', '.join(sorted(t.value for t in turler.elements()))})."))
            continue
        # Komisyonların aynı üyelerden oluşturulması esastır.
        komisyonlar = [
            frozenset(g.personel_kimligi for g in plan.oturum_gorevleri(o.anahtar)
                      if g.rol is GorevRolu.KOMISYON_UYESI)
            for o in oturumlar
        ]
        if all(komisyonlar) and len(set(komisyonlar)) > 1:
            ihlaller.append(ihlal(
                "SP-06", birim,
                f"{ders} dersinin yazılı ve uygulama komisyonları farklı; "
                "komisyonların aynı üyelerden oluşturulması esastır.",
                Ciddiyet.UYARI))
    return ihlaller


def _sp02_sp03_gorevlendirme(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    ihlaller = []
    for oturum in sorted(plan.oturumlar, key=lambda o: (o.tarih, o.saat, o.anahtar)):
        gorevler = plan.oturum_gorevleri(oturum.anahtar)
        komisyon = [g for g in gorevler if g.rol is GorevRolu.KOMISYON_UYESI]
        gozcu = [g for g in gorevler if g.rol is GorevRolu.GOZCU]

        if len(komisyon) != KOMISYON_UYE_SAYISI:
            ihlaller.append(ihlal(
                "SP-02", oturum.anahtar,
                f"{oturum.ders_adi} sınavında {len(komisyon)} komisyon üyesi var; "
                f"{KOMISYON_UYE_SAYISI} sınav öğretmeni zorunludur."))
        if len(gozcu) != oturum.salon_sayisi:
            ihlaller.append(ihlal(
                "SP-03", oturum.anahtar,
                f"{oturum.ders_adi} sınavı {oturum.salon_sayisi} salonda yapılıyor ama "
                f"{len(gozcu)} gözcü atanmış."))

        kabul_edilen = {esitle(b) for b in oturum.alan_branslari if b}
        alan_sayisi = sum(
            1 for g in komisyon
            if g.personel_kimligi in baglam.personel
            and esitle(baglam.personel[g.personel_kimligi].brans) in kabul_edilen)
        if alan_sayisi < 1:
            ihlaller.append(ihlal(
                "SP-02", oturum.anahtar,
                f"{oturum.ders_adi} komisyonunda {oturum.alan_bransi} alanından öğretmen yok; "
                "en az bir alan öğretmeni zorunludur."))
        elif alan_sayisi < KOMISYON_UYE_SAYISI and not any(g.gerekce.strip() for g in komisyon):
            ihlaller.append(ihlal(
                "SP-02", oturum.anahtar,
                f"{oturum.ders_adi} komisyonunda tek alan öğretmeni var; ikinci alan "
                "öğretmeninin neden bulunamadığı gerekçe alanına yazılmalıdır."))

        # EK-03: aynı kişi aynı oturumda iki rol alamaz.
        for kimlik, adet in Counter(g.personel_kimligi for g in gorevler).items():
            if adet > 1:
                kisi = baglam.personel.get(kimlik)
                ihlaller.append(ihlal(
                    "EK-03", f"{oturum.anahtar}:{kimlik}",
                    f"{kisi.ad if kisi else kimlik} {oturum.ders_adi} sınavında "
                    f"{adet} görev alıyor; bir sınavda hem komisyon üyeliği hem gözcülük olmaz."))

        # Müdür ve rehber öğretmen sınav görevi almaz (okul kararı).
        for gorev in gorevler:
            kisi = baglam.personel.get(gorev.personel_kimligi)
            if kisi and not kisi.gorev_alabilir_mi:
                sebep = "Müdüre" if kisi.mudur_mu else "Rehber öğretmene"
                ihlaller.append(ihlal(
                    "SP-02", f"{oturum.anahtar}:{gorev.personel_kimligi}",
                    f"{sebep} sınav görevi verilemez: {kisi.ad} — {oturum.ders_adi}."))
    return ihlaller


def _personel_slot_cakismasi(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    """Bir görevli aynı tarih ve saatte iki oturumda görevli olamaz."""
    oturumlar = {o.anahtar: o for o in plan.oturumlar}
    yerlesim: dict[tuple[int, date, object], list[str]] = defaultdict(list)
    for gorev in plan.gorevlendirmeler:
        oturum = oturumlar.get(gorev.oturum_anahtari)
        if oturum is not None:
            yerlesim[(gorev.personel_kimligi, oturum.tarih, oturum.saat)].append(oturum.ders_adi)
    ihlaller = []
    for (kimlik, gun, saat), dersler in sorted(yerlesim.items(), key=lambda x: str(x[0])):
        if len(dersler) > 1:
            kisi = baglam.personel.get(kimlik)
            ihlaller.append(ihlal(
                "SP-02", f"{kimlik}:{gun.isoformat()}:{saat}",
                f"{kisi.ad if kisi else kimlik} — {gun.strftime('%d.%m.%Y')} "
                f"{saat.strftime('%H:%M')} saatinde aynı anda iki sınavda görevli: "
                + ", ".join(sorted(dersler))))
    return ihlaller


def _salon_cakismasi(plan: Plan, salonlar: dict[int, Salon]) -> list[Ihlal]:
    yerlesim: dict[tuple[int, date, object], list[str]] = defaultdict(list)
    for oturum in plan.oturumlar:
        for salon_id in oturum.salon_kimlikleri:
            yerlesim[(salon_id, oturum.tarih, oturum.saat)].append(oturum.ders_adi)
    ihlaller = []
    for (salon_id, gun, saat), dersler in sorted(yerlesim.items(), key=lambda x: str(x[0])):
        if len(dersler) > 1:
            salon = salonlar.get(salon_id)
            ihlaller.append(ihlal(
                "SP-03", f"salon{salon_id}:{gun.isoformat()}:{saat}",
                f"{salon.ad if salon else salon_id} salonu {gun.strftime('%d.%m.%Y')} "
                f"{saat.strftime('%H:%M')} saatinde iki sınava birden ayrılmış: "
                + ", ".join(sorted(dersler)),
                Ciddiyet.ENGEL))
    return ihlaller


def _ek05_sayac(plan: Plan, baglam: DogrulamaBaglami) -> list[Ihlal]:
    if baglam.ogretim_yili in SINIRSIZ_OGRETIM_YILLARI:
        return []
    sayac: dict[int, Counter] = defaultdict(Counter)
    for gorev in plan.gorevlendirmeler:
        sayac[gorev.personel_kimligi][gorev.rol] += 1
    ihlaller = []
    for kimlik, adetler in sorted(sayac.items()):
        komisyon = adetler[GorevRolu.KOMISYON_UYESI]
        gozcu = adetler[GorevRolu.GOZCU]
        if yillik_sayac_asildi_mi(baglam.ogretim_yili, komisyon, gozcu):
            kisi = baglam.personel.get(kimlik)
            ihlaller.append(ihlal(
                "EK-05", str(kimlik),
                f"{kisi.ad if kisi else kimlik}: {komisyon} komisyon üyeliği, {gozcu} gözcülük. "
                f"Sınır {YILLIK_KOMISYON_SINIRI}/{YILLIK_GOZCU_SINIRI}; aşan görevler için "
                "ücret ödenmez."))
    return ihlaller


def dogrula_plan(plan: Plan, baglam: DogrulamaBaglami,
                 salonlar: dict[int, Salon] | None = None) -> list[Ihlal]:
    """Planı bütün kurallara karşı doğrular.

    Hem planlayıcının ürettiği hem de elle düzenlenen plan buradan geçer;
    çözücüden bağımsızdır.
    """
    ihlaller: list[Ihlal] = []
    ihlaller += _sp01_pencere(plan, baglam)
    ihlaller += _sp04_birlestirme(plan)
    ihlaller += _sp05_hafta_sonu(plan)
    ihlaller += _sp06_iki_asamali(plan, baglam)
    ihlaller += _sp10_sure(plan)
    ihlaller += _ogrenci_slot_cakismasi(plan, baglam)
    ihlaller += _sp11_gunluk_yuk(plan, baglam)
    if plan.gorevlendirmeler:
        ihlaller += _sp02_sp03_gorevlendirme(plan, baglam)
        ihlaller += _personel_slot_cakismasi(plan, baglam)
        ihlaller += _ek05_sayac(plan, baglam)
    ihlaller += _salon_cakismasi(plan, salonlar or {})
    return sorted(ihlaller, key=lambda i: (
        {"ENGEL": 0, "UYARI": 1, "BILGI": 2}[i.ciddiyet.value],
        i.kural_kimligi,
        siralama_anahtari(i.aciklama),
    ))


def engelleri_ayikla(ihlaller: list[Ihlal]) -> list[Ihlal]:
    return [i for i in ihlaller if i.engel_mi]
