"""İş günü hesapları ve sorumluluk sınavı pencereleri.

Pencereler OKY md.58/2-a uyarınca dönem tarihlerinden hesaplanır; koda
gömülmez. Resmî tatiller çağıranca verilir: çekirdek tatil listesi tutmaz,
kurumun girdiği liste servis katmanından gelir. Bayram tarihleri her yıl
kaydığı ve idari izinler önceden bilinmediği için gömülü bir liste
eskiyecekti.
"""

from __future__ import annotations

import re
from datetime import date, timedelta


Tatiller = frozenset[date] | set[date]

# Sorumluluk sınavı pencereleri iki takvim haftasıdır: başlangıç günü dâhil
# 14 gün.
PENCERE_GUN_SAYISI = 14

# Pencerelerin kullanıcıya gösterilen adları. Veritabanında kısa kod (P1/P2/P3)
# saklanır; ekranlarda ve evrakta dönemin düştüğü ay adı yazılır.
PENCERE_ADLARI = {"P1": "Eylül", "P2": "Şubat", "P3": "Haziran"}


def pencere_adi(kod: str) -> str:
    return PENCERE_ADLARI.get(kod, kod)


def is_gunu_mu(gun: date, tatiller: Tatiller = frozenset()) -> bool:
    return gun.weekday() < 5 and gun not in tatiller


def is_gunu_farki(baslangic: date, bitis: date, tatiller: Tatiller = frozenset()) -> int:
    """İki tarih arasındaki iş günü sayısı; `bitis` önceyse negatif döner."""
    if bitis < baslangic:
        return -is_gunu_farki(bitis, baslangic, tatiller)
    sayi = 0
    gun = baslangic
    while gun < bitis:
        gun += timedelta(days=1)
        if is_gunu_mu(gun, tatiller):
            sayi += 1
    return sayi


def is_gunu_ekle(baslangic: date, adet: int, tatiller: Tatiller = frozenset()) -> date:
    """`baslangic` tarihine `adet` iş günü ekler; negatif değer geriye sayar."""
    if adet == 0:
        return baslangic
    yon = 1 if adet > 0 else -1
    kalan = abs(adet)
    gun = baslangic
    while kalan:
        gun += timedelta(days=yon)
        if is_gunu_mu(gun, tatiller):
            kalan -= 1
    return gun


def gunleri_listele(baslangic: date, bitis: date, hafta_sonu_dahil: bool,
                    tatiller: Tatiller = frozenset()) -> list[date]:
    """Pencere içindeki planlanabilir günleri sırayla döndürür.

    Tatil günü hafta sonu açık olsa da listeye girmez: hafta sonu izni
    cumartesi ve pazarı açar (OKY md.58/2-ç), bayram ve idari izni değil.
    """
    gunler = []
    gun = baslangic
    while gun <= bitis:
        if gun not in tatiller and (hafta_sonu_dahil or gun.weekday() < 5):
            gunler.append(gun)
        gun += timedelta(days=1)
    return gunler


def sinav_pencereleri(birinci_donem_baslangic: date, ikinci_donem_baslangic: date,
                      ikinci_donem_bitis: date) -> dict[str, tuple[date, date]]:
    """OKY md.58/2-a: birinci dönemin ilk iki haftası, ikinci dönemin ilk iki
    haftası ile son iki haftası."""
    genislik = timedelta(days=PENCERE_GUN_SAYISI - 1)
    return {
        "P1": (birinci_donem_baslangic, birinci_donem_baslangic + genislik),
        "P2": (ikinci_donem_baslangic, ikinci_donem_baslangic + genislik),
        "P3": (ikinci_donem_bitis - genislik, ikinci_donem_bitis),
    }


def tek_ders_penceresi(son_sinav_tarihi: date) -> tuple[date, date]:
    """OKY md.58/6: sorumluluk sınavı sonunda tek dersten başarısızlığı kalan
    son sınıf öğrencisi için "takip eden hafta içinde" bir sınav daha yapılır.

    Takip eden hafta, son sınavın düştüğü takvim haftasından sonraki
    pazartesi–pazar aralığıdır. Hafta sonu kullanımı olağan plandaki gibi
    OKY md.58/2-ç'ye bağlıdır ("aynı usulle").
    """
    pazartesi = son_sinav_tarihi + timedelta(days=7 - son_sinav_tarihi.weekday())
    return pazartesi, pazartesi + timedelta(days=6)


def varsayilan_pencere_kodu(pencereler: dict[str, tuple[date, date]], bugun: date,
                            gecmise_bak: bool = False) -> str:
    """Ekranların açılışta göstereceği dönem.

    Planlama ileriye bakar: içinde bulunulan, yoksa sıradaki dönem. Evrak
    teslimi geriye bakar (`gecmise_bak`): başlamış dönemlerin en sonuncusu,
    çünkü evrak sınavdan sonra toplanır. Eski sürüm her ekranı Eylül'le
    açıyordu; Şubat'ta çalışan kullanıcı dönem kutusunu değiştirmeyi
    unutursa Eylül planı üzerinde işlem yapıyordu.
    """
    if not pencereler:
        raise ValueError("Pencere tanımlı değil.")
    sirali = sorted(pencereler.items(), key=lambda x: x[1][0])
    if gecmise_bak:
        baslamis = [kod for kod, (bas, _) in sirali if bas <= bugun]
        return baslamis[-1] if baslamis else sirali[0][0]
    for kod, (_, bit) in sirali:
        if bugun <= bit:
            return kod
    return sirali[-1][0]


# ------------------------------------------------------------ tarih biçimi

_GG_AA_YYYY = re.compile(r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})\s*$")


def tarih_coz(metin: str) -> date:
    """Kullanıcının yazdığı tarihi çözer.

    Arayüz gg.aa.yyyy ister (proje kuralı); eski sürümün YYYY-AA-GG biçimi de
    kabul edilir ki önceden kaydedilmiş değerler ve alışkanlıklar kırılmasın.
    """
    deger = str(metin or "").strip()
    eslesme = _GG_AA_YYYY.match(deger)
    try:
        if eslesme:
            gun, ay, yil = (int(x) for x in eslesme.groups())
            return date(yil, ay, gun)
        return date.fromisoformat(deger)
    except ValueError as hata:
        raise ValueError(
            f"'{deger}' geçerli bir tarih değil; gg.aa.yyyy biçiminde yazın "
            "(ör. 14.09.2026).") from hata


def tarih_yaz(deger: date | None) -> str:
    return deger.strftime("%d.%m.%Y") if deger else ""
