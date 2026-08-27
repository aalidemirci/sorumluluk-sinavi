"""İş günü hesapları ve sorumluluk sınavı pencereleri.

Pencereler OKY md.58/2-a uyarınca dönem tarihlerinden hesaplanır; koda
gömülmez. Resmî tatiller çağıranca verilir, uygulama kendi tatil listesi
tutmaz.
"""

from __future__ import annotations

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
    """Pencere içindeki planlanabilir günleri sırayla döndürür."""
    gunler = []
    gun = baslangic
    while gun <= bitis:
        if hafta_sonu_dahil or is_gunu_mu(gun, tatiller):
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
