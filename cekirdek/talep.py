"""Faz 0 — sorumluluk kayıtlarından sınav birimleri ve yük özeti üretme.

Bir *sınav birimi*, aynı gün ardışık slotlara birlikte yerleşmesi gereken bir
veya iki oturumdur. Tek aşamalı derste bir yazılı oturum, iki aşamalı derste
(OKY md.58/2-e) bir yazılı ve bir uygulama oturumu vardır.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from math import ceil

from .kurallar import (
    BIRLESTIRME_UST_SINIRI, GUNLUK_SINAV_TAVANI, SALON_OGRENCI_UST_SINIRI, gereken_salon_sayisi,
)
from .metin import siralama_anahtari
from .modeller import DersAyari, IkiAsamaliSayim, OturumTuru, Salon, SorumlulukKaydi


# Pencere hedefi seçilirken tek tük aşırı yüklü öğrenci sonucu bozmasın diye
# çoğunluk bu yüzdelik dilimden okunur.
COGUNLUK_YUZDELIGI = 95


@dataclass(frozen=True)
class SinavBirimi:
    anahtar: str
    ders_adi: str
    duzeyler: tuple[int, ...]
    alan_bransi: str
    ogrenci_anahtarlari: tuple[str, ...]
    oturum_turleri: tuple[OturumTuru, ...]
    salon_sayisi: int
    esdeger_branslar: tuple[str, ...] = ()

    @property
    def alan_branslari(self) -> tuple[str, ...]:
        """Komisyon üyeliği için kabul edilen branşlar."""
        return (self.alan_bransi, *self.esdeger_branslar)

    @property
    def iki_asamali_mi(self) -> bool:
        return len(self.oturum_turleri) > 1

    @property
    def slot_ihtiyaci(self) -> int:
        """Birimin aynı günde işgal ettiği ardışık slot sayısı."""
        return len(self.oturum_turleri)

    @property
    def ogrenci_sayisi(self) -> int:
        return len(self.ogrenci_anahtarlari)

    @property
    def gorevli_ihtiyaci(self) -> int:
        """Oturum başına 2 komisyon üyesi + salon sayısı kadar gözcü."""
        return 2 + self.salon_sayisi

    def sinav_yuku(self, sayim: IkiAsamaliSayim) -> int:
        """Öğrencinin günlük sınav sayacına katkısı."""
        return self.slot_ihtiyaci if sayim is IkiAsamaliSayim.AYRI else 1

    def etiket(self) -> str:
        duzey = "/".join(str(d) for d in self.duzeyler)
        return f"{duzey} {self.ders_adi}"


def _anahtar_uret(ders: str, duzeyler: tuple[int, ...], ogrenciler: tuple[str, ...]) -> str:
    ham = f"{ders}|{','.join(map(str, duzeyler))}|{'|'.join(ogrenciler)}"
    return sha256(ham.encode("utf-8")).hexdigest()[:16]


def _duzeyleri_birlestir(duzey_ogrencileri: dict[int, list[str]],
                         ust_sinir: int = BIRLESTIRME_UST_SINIRI) -> list[tuple[int, ...]]:
    """OKY md.58/2-c: aynı dersin farklı düzeylerini birleştirir.

    İki koşul birlikte aranır: toplam öğrenci sayısı üst sınırı aşmamalı ve
    paketteki düzeylerde ortak öğrenci bulunmamalı. Ortak öğrenci varsa
    md.58/2-c ek cümlesi uyarınca ayrı ayrı sınava alınırlar.

    Azalan büyüklükte ilk-uyan (first-fit decreasing) yerleştirir; girdi
    sıralı olduğu için sonuç belirlenimlidir.
    """
    paketler: list[list[int]] = []
    paket_ogrencileri: list[set[str]] = []
    for duzey in sorted(duzey_ogrencileri, key=lambda d: (-len(duzey_ogrencileri[d]), d)):
        ogrenciler = set(duzey_ogrencileri[duzey])
        for sira, paket in enumerate(paketler):
            mevcut = paket_ogrencileri[sira]
            if len(mevcut) + len(ogrenciler) <= ust_sinir and not (mevcut & ogrenciler):
                paket.append(duzey)
                mevcut |= ogrenciler
                break
        else:
            paketler.append([duzey])
            paket_ogrencileri.append(set(ogrenciler))
    return sorted(tuple(sorted(paket)) for paket in paketler)


def birimleri_olustur(kayitlar: list[SorumlulukKaydi], ders_ayarlari: dict[str, DersAyari],
                      salonlar: list[Salon],
                      salon_ust_siniri: int = SALON_OGRENCI_UST_SINIRI,
                      birlestirme_ust_siniri: int = BIRLESTIRME_UST_SINIRI) -> list[SinavBirimi]:
    """Aktif sorumluluk kayıtlarından planlanacak sınav birimlerini üretir."""
    if not kayitlar:
        return []

    ders_kayitlari: dict[str, list[SorumlulukKaydi]] = defaultdict(list)
    for kayit in kayitlar:
        ders_kayitlari[kayit.ders_adi].append(kayit)

    eksik_brans = sorted(
        (ders for ders in ders_kayitlari
         if ders not in ders_ayarlari or not ders_ayarlari[ders].brans.strip()),
        key=siralama_anahtari)
    if eksik_brans:
        raise ValueError(
            f"{len(eksik_brans)} dersin branş eşlemesi tamamlanmadan plan üretilemez: "
            + ", ".join(eksik_brans[:5]) + ("…" if len(eksik_brans) > 5 else ""))

    birimler: list[SinavBirimi] = []
    for ders in sorted(ders_kayitlari, key=siralama_anahtari):
        ayar = ders_ayarlari[ders]
        duzey_ogrencileri: dict[int, list[str]] = defaultdict(list)
        for kayit in ders_kayitlari[ders]:
            duzey_ogrencileri[kayit.sinif_duzeyi].append(kayit.ogrenci_anahtari)
        for duzey in duzey_ogrencileri:
            duzey_ogrencileri[duzey] = sorted(set(duzey_ogrencileri[duzey]))

        turler = ((OturumTuru.YAZILI, OturumTuru.UYGULAMA) if ayar.iki_asamali_mi
                  else (OturumTuru.YAZILI,))
        for duzeyler in _duzeyleri_birlestir(duzey_ogrencileri, birlestirme_ust_siniri):
            ogrenciler = tuple(sorted({o for d in duzeyler for o in duzey_ogrencileri[d]}))
            birimler.append(SinavBirimi(
                anahtar=_anahtar_uret(ders, duzeyler, ogrenciler),
                ders_adi=ders,
                duzeyler=duzeyler,
                alan_bransi=ayar.brans,
                ogrenci_anahtarlari=ogrenciler,
                oturum_turleri=turler,
                salon_sayisi=gereken_salon_sayisi(len(ogrenciler), salonlar, salon_ust_siniri),
                esdeger_branslar=ayar.esdeger_branslar,
            ))
    return birimler


# ================================================================ yük özeti

@dataclass(frozen=True)
class YukOzeti:
    """Öğrenci başına sınav yükü ve bundan türeyen pencere önerisi."""

    ogrenci_yukleri: dict[str, int]
    gunluk_sinir: int

    @property
    def azami_yuk(self) -> int:
        return max(self.ogrenci_yukleri.values(), default=0)

    @property
    def cogunluk_yuku(self) -> int:
        """Aşırı yüklü tek tük öğrenciyi dışarıda bırakan yüzdelik dilim."""
        degerler = sorted(self.ogrenci_yukleri.values())
        if not degerler:
            return 0
        indis = min(len(degerler) - 1, int(len(degerler) * COGUNLUK_YUZDELIGI / 100))
        return degerler[indis]

    def gereken_gun(self, yuk: int) -> int:
        return ceil(yuk / self.gunluk_sinir) if yuk else 0

    @staticmethod
    def gunluk_tavan(slot_sayisi: int) -> int:
        """Bir öğrencinin bir günde girebileceği en çok sınav.

        İki sınır birlikte bağlar: günde slot sayısından fazla oturum olmaz ve
        ÖDY md.5/1-k zorunlu hâlde bile günde üç sınavı geçmeye izin vermez.
        """
        if slot_sayisi <= 0:
            raise ValueError("Günlük slot sayısı sıfırdan büyük olmalıdır.")
        return min(slot_sayisi, GUNLUK_SINAV_TAVANI)

    def asgari_gun_sayisi(self, slot_sayisi: int) -> int:
        """En yüklü öğrencinin günlük tavanla bitirebileceği en kısa pencere."""
        tavan = self.gunluk_tavan(slot_sayisi)
        return max((ceil(yuk / tavan) for yuk in self.ogrenci_yukleri.values()), default=1)

    def onerilen_gun_sayisi(self, slot_sayisi: int) -> int:
        """Çoğunluğun sığdığı en kısa standart pencere.

        Bir hafta (5 iş günü) yetmiyorsa iki hafta (10 iş günü), o da
        yetmiyorsa gereken kadar gün kullanılır. Sonuç hiçbir zaman
        `asgari_gun_sayisi` değerinin altına inemez: en yüklü öğrenci de
        günde üç sınavı (ÖDY md.5/1-k) ve slot sayısını aşmadan bitirebilmelidir.
        """
        gereken = self.gereken_gun(self.cogunluk_yuku)
        standart = 5 if gereken <= 5 else (10 if gereken <= 10 else gereken)
        return max(standart, self.asgari_gun_sayisi(slot_sayisi))

    def kisisel_sinirlar(self, gun_sayisi: int, slot_sayisi: int | None = None,
                         etiketler: dict[str, str] | None = None) -> dict[str, int]:
        """Verilen gün sayısına sığmayan öğrencilerin yükseltilmiş sınırı.

        Sınır, o öğrencinin planı bitirebilmesi için gereken *en düşük*
        değere çıkarılır; başkalarının sınırı değişmez. `slot_sayisi`
        verilirse günlük tavanı (en çok 3 sınav, en çok slot sayısı kadar
        oturum) aşması gereken öğrenciler hata olarak bildirilir.
        """
        if gun_sayisi <= 0:
            raise ValueError("Gün sayısı sıfırdan büyük olmalıdır.")
        yukseltilen = {}
        for ogrenci, yuk in sorted(self.ogrenci_yukleri.items()):
            gereken = ceil(yuk / gun_sayisi)
            if gereken > self.gunluk_sinir:
                yukseltilen[ogrenci] = gereken
        if slot_sayisi is not None:
            tavan = self.gunluk_tavan(slot_sayisi)
            asanlar = {o: s for o, s in yukseltilen.items() if s > tavan}
            if asanlar:
                etiketler = etiketler or {}
                detay = "; ".join(f"{etiketler.get(o, o)}: {self.ogrenci_yukleri[o]} sınav, "
                                  f"günde {s} sınav gerekiyor" for o, s in asanlar.items())
                en_az = max(ceil(self.ogrenci_yukleri[o] / tavan) for o in asanlar)
                # Öneri bağlayan sınıra göre verilir: tavan yönetmelikten geliyorsa
                # oturum saati eklemek işe yaramaz. Gerçek veride (04.10.2026) 31
                # sınavlı öğrenci için "oturum saati ekleyin" öneriliyordu.
                if tavan == GUNLUK_SINAV_TAVANI:
                    neden = (f"bir öğrenci günde en çok {GUNLUK_SINAV_TAVANI} sınava girebilir "
                             "(ÖDY md.5/1-k)")
                    oneri = ("Hafta sonunu açın ya da gün sayısını artırın; oturum saati "
                             "eklemek bu sınırı değiştirmez.")
                else:
                    neden = f"günde {slot_sayisi} oturum saati var"
                    oneri = (f"Günlük oturum saati ekleyin (öğrenci başına günde en çok "
                             f"{GUNLUK_SINAV_TAVANI} sınav), hafta sonunu açın ya da gün "
                             "sayısını artırın.")
                raise ValueError(
                    f"{gun_sayisi} günlük planda {neden}; {detay}. Bu yük en az {en_az} gün "
                    f"ister. {oneri}")
        return yukseltilen


def yuk_ozeti(birimler: list[SinavBirimi], sayim: IkiAsamaliSayim,
              gunluk_sinir: int) -> YukOzeti:
    yukler: dict[str, int] = defaultdict(int)
    for birim in birimler:
        katki = birim.sinav_yuku(sayim)
        for ogrenci in birim.ogrenci_anahtarlari:
            yukler[ogrenci] += katki
    return YukOzeti(dict(yukler), gunluk_sinir)
