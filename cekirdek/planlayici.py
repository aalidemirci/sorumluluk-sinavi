"""Sınav planlama motoru — yerleştirme ve görevlendirme birlikte çözülür.

Eski sürümde yerleştirme ve görevlendirme iki ayrı aşamaydı; yerleştirici
kimin görevlendirilebileceğini bilmediği için her oturuma benzersiz bir slot
vermek zorundaydı ve paralel sınav yapılamıyordu. Burada yerleştirme,
görevlendirmenin yapılabilirliğini kısıt olarak taşır; böylece aynı saatte
birden fazla sınav planlanabilir ve program az sayıda güne sığar.

Fazlar:
    0  Sınav birimleri (bkz. talep.py)
    1  Parametre çözümleme: gün sayısı ve kişisel günlük sınırlar
    2  Yerleştirme: (gün, slot) ızgarasına geri izlemeli arama
    3  Salon dağıtımı ve görevlendirme
    4  Bağımsız doğrulama
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
from time import perf_counter
from typing import Callable

from .kurallar import DogrulamaBaglami, KOMISYON_UYE_SAYISI, dogrula_plan
from .metin import esitle, siralama_anahtari
from .modeller import (
    Gorevlendirme, GorevRolu, Ihlal, Oturum, OturumTuru, Personel, Plan,
    PlanParametreleri, Salon,
)
from .talep import SinavBirimi, YukOzeti, yuk_ozeti


# Arama bütçeleri: arayüz hiçbir koşulda kilitlenmemeli. Bütçe dolarsa plan
# üretilemez ve kullanıcıya hangi kısıtın bağladığı söylenir.
ARAMA_DUGUM_BUTCESI = 300_000
ARAMA_SURE_BUTCESI_SN = 20.0
# Tek bir gün sayısı denemesine ayrılan süre. Uygun bir gün sayısı bulunduğunda
# çözüm saniyenin altında gelir; sığmayan gün sayısında ise arama uzar. Deneme
# başına küçük bir bütçe, toplam bütçeyi ilk birkaç imkânsız denemede tüketmek
# yerine uygun gün sayısına hızla ulaşmayı sağlar.
DENEME_SURE_BUTCESI_SN = 2.0


def _brans_imzasi(birim: SinavBirimi) -> frozenset[str]:
    """Birimin komisyon üyeliği için kabul ettiği branşların anahtar kümesi.

    "Görsel Sanatlar/Müzik" gibi birleşik derslerde küme iki branş taşır;
    slot başına kaç böyle sınav yapılabileceği bu kümedeki öğretmen sayısına
    bağlıdır.
    """
    return frozenset(esitle(b) for b in birim.alan_branslari if b.strip())


class PlanlamaBasarisiz(ValueError):
    """Plan üretilemediğinde hangi kısıtın doyurulamadığını taşır."""

    def __init__(self, mesaj: str, teshis: list[str] | None = None):
        self.teshis = list(teshis or [])
        tam = mesaj if not self.teshis else mesaj + "\n\n" + "\n".join(f"• {t}" for t in self.teshis)
        super().__init__(tam)


@dataclass
class PlanlamaSonucu:
    plan: Plan
    ihlaller: list[Ihlal]
    yukseltilen_sinirlar: dict[str, int]
    kullanilan_gun_sayisi: int
    notlar: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SinirOnizlemesi:
    """Parametre ekranında seçimin sonucunu peşinen göstermek için."""

    gun_sayisi: int
    yukseltilen: dict[str, int]
    slot_sayisi: int

    @property
    def etkilenen_ogrenci_sayisi(self) -> int:
        return len(self.yukseltilen)

    @property
    def en_yuksek_sinir(self) -> int:
        return max(self.yukseltilen.values(), default=0)

    @property
    def uygulanabilir_mi(self) -> bool:
        """Günde slot sayısından fazla sınav gereken öğrenci varsa seçenek
        matematiksel olarak imkânsızdır."""
        return self.en_yuksek_sinir <= self.slot_sayisi

    def ozet(self) -> str:
        if not self.yukseltilen:
            return f"{self.gun_sayisi} gün: kimsenin günlük sınırı yükselmez."
        sinirlar = ", ".join(str(s) for s in sorted(self.yukseltilen.values(), reverse=True))
        durum = "" if self.uygulanabilir_mi else "  — GÜNLÜK OTURUM SAATİ YETMİYOR"
        return (f"{self.gun_sayisi} gün: {self.etkilenen_ogrenci_sayisi} öğrencinin günlük "
                f"sınırı {sinirlar} olur.{durum}")


def sinir_onizlemesi(ozet: YukOzeti, gun_secenekleri: list[int],
                     slot_sayisi: int) -> list[SinirOnizlemesi]:
    """Her gün sayısı seçeneği için hangi öğrencinin sınırının yükseleceğini
    hesaplar. Kullanıcı takası görerek karar verir."""
    return [SinirOnizlemesi(gun, ozet.kisisel_sinirlar(gun), slot_sayisi)
            for gun in sorted(set(gun_secenekleri))]

# ==================================================== Faz 2 — yerleştirme
#
# Arama sıcak döngüdür: 950 sorumluluk kaydı, ~50 birim ve 60 (gün, slot)
# adayıyla çalışır. Bu yüzden durum sözlük yerine düz tamsayı dizilerinde
# tutulur, öğrenciler bir kez indekslenir ve uygunluk kontrolü erken çıkar.


@dataclass
class _Izgara:
    """Yerleştirme sırasında tutulan durum."""

    gun_sayisi: int
    slot_sayisi: int
    salon_adedi: int
    gorevli_adedi: int
    brans_arzi: dict[frozenset[str], int]

    def hazirla(self, birimler: list[SinavBirimi], yuk_fn: Callable[[SinavBirimi], int],
                sinir_fn: Callable[[str], int]) -> None:
        """Birimleri ve öğrencileri tamsayı indekslere çevirir."""
        ogrenciler = sorted({o for b in birimler for o in b.ogrenci_anahtarlari})
        self._ogrenci_indisi = {o: i for i, o in enumerate(ogrenciler)}
        self._ogrenci_sayisi = len(ogrenciler)
        self._ogrenci_siniri = [sinir_fn(o) for o in ogrenciler]

        imzalar = sorted({_brans_imzasi(b) for b in birimler}, key=lambda k: sorted(k))
        self._imza_indisi = {imza: i for i, imza in enumerate(imzalar)}
        self._imza_arzi = [self.brans_arzi.get(imza, 0) for imza in imzalar]

        self.birim_ogrencileri = [
            tuple(self._ogrenci_indisi[o] for o in b.ogrenci_anahtarlari) for b in birimler]
        self.birim_imzasi = [self._imza_indisi[_brans_imzasi(b)] for b in birimler]
        self.birim_yuku = [yuk_fn(b) for b in birimler]
        self.birim_slotu = [b.slot_ihtiyaci for b in birimler]
        self.birim_salonu = [b.salon_sayisi for b in birimler]
        self.birim_gorevlisi = [b.gorevli_ihtiyaci for b in birimler]

        yer_sayisi = self.gun_sayisi * self.slot_sayisi
        self.slot_salon = [0] * yer_sayisi
        self.slot_gorevli = [0] * yer_sayisi
        self.gun_yuku = [0] * self.gun_sayisi
        self.slot_brans = [0] * (yer_sayisi * len(imzalar))
        self.imza_sayisi = len(imzalar)
        self.ogrenci_gun = [0] * (self._ogrenci_sayisi * self.gun_sayisi)
        self.ogrenci_slot = bytearray(self._ogrenci_sayisi * yer_sayisi)

    def sigar_mi(self, birim_no: int, gun: int, ilk_slot: int) -> bool:
        adet = self.birim_slotu[birim_no]
        if ilk_slot + adet > self.slot_sayisi:
            return False
        salon, gorevli = self.birim_salonu[birim_no], self.birim_gorevlisi[birim_no]
        imza, arz = self.birim_imzasi[birim_no], self._imza_arzi[self.birim_imzasi[birim_no]]
        taban = gun * self.slot_sayisi + ilk_slot
        for k in range(adet):
            yer = taban + k
            if self.slot_salon[yer] + salon > self.salon_adedi:
                return False
            if self.slot_gorevli[yer] + gorevli > self.gorevli_adedi:
                return False
            if self.slot_brans[yer * self.imza_sayisi + imza] + 1 > arz:
                return False
        yuk = self.birim_yuku[birim_no]
        gun_taban = gun
        for ogrenci in self.birim_ogrencileri[birim_no]:
            if (self.ogrenci_gun[ogrenci * self.gun_sayisi + gun_taban] + yuk
                    > self._ogrenci_siniri[ogrenci]):
                return False
            satir = ogrenci * self.gun_sayisi * self.slot_sayisi
            for k in range(adet):
                if self.ogrenci_slot[satir + taban + k]:
                    return False
        return True

    def _uygula(self, birim_no: int, gun: int, ilk_slot: int, isaret: int) -> None:
        adet = self.birim_slotu[birim_no]
        salon, gorevli = self.birim_salonu[birim_no], self.birim_gorevlisi[birim_no]
        imza, yuk = self.birim_imzasi[birim_no], self.birim_yuku[birim_no]
        taban = gun * self.slot_sayisi + ilk_slot
        for k in range(adet):
            yer = taban + k
            self.slot_salon[yer] += salon * isaret
            self.slot_gorevli[yer] += gorevli * isaret
            self.slot_brans[yer * self.imza_sayisi + imza] += isaret
        self.gun_yuku[gun] += adet * isaret
        for ogrenci in self.birim_ogrencileri[birim_no]:
            self.ogrenci_gun[ogrenci * self.gun_sayisi + gun] += yuk * isaret
            satir = ogrenci * self.gun_sayisi * self.slot_sayisi
            for k in range(adet):
                self.ogrenci_slot[satir + taban + k] = 1 if isaret > 0 else 0

    def yerlestir(self, birim_no: int, gun: int, ilk_slot: int) -> None:
        self._uygula(birim_no, gun, ilk_slot, 1)

    def geri_al(self, birim_no: int, gun: int, ilk_slot: int) -> None:
        self._uygula(birim_no, gun, ilk_slot, -1)


def _zorluk_sirasi(birimler: list[SinavBirimi], brans_arzi: dict[frozenset[str], int]) -> list[int]:
    """En kısıtlı birim önce denenir.

    Sıra: branşı kıt olan, çok salon isteyen, iki aşamalı, çok öğrencili.
    Kalan alanlar yalnız belirlenimliliği güvenceye almak için.
    """
    return sorted(range(len(birimler)), key=lambda i: (
        brans_arzi.get(_brans_imzasi(birimler[i]), 0),
        -birimler[i].salon_sayisi,
        -birimler[i].slot_ihtiyaci,
        -birimler[i].ogrenci_sayisi,
        siralama_anahtari(birimler[i].ders_adi),
        birimler[i].anahtar,
    ))


def _yerlestirme_ara(birimler: list[SinavBirimi], izgara: _Izgara, sira: list[int],
                     dugum_butcesi: int, sure_butcesi: float) -> list[tuple[int, int]] | None:
    """Sabit sıralı geri izlemeli arama.

    Birimler zorluk sırasına göre denenir; her birim için adaylar erken
    gün/erken slot önceliğiyle gezilir, böylece plan az güne sıkışır. Düğüm
    ve süre bütçesi arayüzün donmasını engeller.
    """
    atama: list[tuple[int, int]] = [(-1, -1)] * len(sira)
    yerler = [(g, s) for g in range(izgara.gun_sayisi) for s in range(izgara.slot_sayisi)]
    bitis = perf_counter() + sure_butcesi
    dugum = 0

    def aday_anahtari(yer: tuple[int, int]) -> tuple[int, int, int, int]:
        """Sınavları pencereye eşit yayar.

        Gün sayısı zaten kademeli aramayla en aza indirildiği için, o günler
        içinde erken günü tercih etmek yerine en az yüklü günü seçmek daha
        okunaklı bir program üretir: ilk güne 17 oturum yığılmaz. İkinci
        ölçüt gün içindeki en az yüklü slot.
        """
        gun, slot = yer
        return (izgara.gun_yuku[gun],
                izgara.slot_gorevli[gun * izgara.slot_sayisi + slot],
                gun, slot)

    def ara(derinlik: int) -> bool:
        nonlocal dugum
        if derinlik == len(sira):
            return True
        dugum += 1
        if dugum > dugum_butcesi or perf_counter() > bitis:
            return False
        birim_no = sira[derinlik]
        for gun, slot in sorted(yerler, key=aday_anahtari):
            if not izgara.sigar_mi(birim_no, gun, slot):
                continue
            izgara.yerlestir(birim_no, gun, slot)
            atama[derinlik] = (gun, slot)
            if ara(derinlik + 1):
                return True
            izgara.geri_al(birim_no, gun, slot)
            atama[derinlik] = (-1, -1)
        return False

    if not ara(0):
        return None
    sonuc: list[tuple[int, int]] = [(-1, -1)] * len(birimler)
    for derinlik, birim_no in enumerate(sira):
        sonuc[birim_no] = atama[derinlik]
    return sonuc


# =========================================== Faz 2 — çözümsüzlük teşhisi

def _teshis_uret(birimler: list[SinavBirimi], izgara: _Izgara, ozet: YukOzeti,
                 gun_sayisi: int, slot_sayisi: int, gunluk_sinir: int) -> list[str]:
    """Plan üretilemediğinde hangi kısıtın bağladığını anlatır."""
    teshis: list[str] = []

    en_buyuk_salon_ihtiyaci = max((b.salon_sayisi for b in birimler), default=0)
    if en_buyuk_salon_ihtiyaci > izgara.salon_adedi:
        darbogaz = max(birimler, key=lambda b: b.salon_sayisi)
        teshis.append(
            f"{darbogaz.etiket()} sınavı {darbogaz.ogrenci_sayisi} öğrenciyle "
            f"{darbogaz.salon_sayisi} salon gerektiriyor; tanımlı salon sayısı "
            f"{izgara.salon_adedi}. Salon ekleyin ya da salon üst sınırını yükseltin.")

    salon_kapasitesi = gun_sayisi * slot_sayisi * izgara.salon_adedi
    gereken_salon_slotu = sum(b.salon_sayisi * b.slot_ihtiyaci for b in birimler)
    if gereken_salon_slotu > salon_kapasitesi:
        teshis.append(
            f"Toplam salon-slot ihtiyacı {gereken_salon_slotu}, {gun_sayisi} gün × "
            f"{slot_sayisi} slot × {izgara.salon_adedi} salon = {salon_kapasitesi} kapasite. "
            "Gün sayısını, günlük slot sayısını veya salon sayısını artırın.")

    gorevli_kapasitesi = gun_sayisi * slot_sayisi * izgara.gorevli_adedi
    gereken_gorevli_slotu = sum(b.gorevli_ihtiyaci * b.slot_ihtiyaci for b in birimler)
    if gereken_gorevli_slotu > gorevli_kapasitesi:
        teshis.append(
            f"Toplam görevli-slot ihtiyacı {gereken_gorevli_slotu}, {gun_sayisi} gün × "
            f"{slot_sayisi} slot × {izgara.gorevli_adedi} görevli = {gorevli_kapasitesi} "
            "kapasite. Gün sayısını veya günlük oturum saatini artırın.")

    # Branş darboğazı: bir slotta aynı branştan en çok o branşın öğretmeni
    # kadar sınav yapılabilir (her sınav en az bir alan öğretmeni ister).
    brans_ihtiyaci: dict[frozenset[str], int] = defaultdict(int)
    brans_adi: dict[frozenset[str], str] = {}
    for birim in birimler:
        imza = _brans_imzasi(birim)
        brans_ihtiyaci[imza] += birim.slot_ihtiyaci
        brans_adi[imza] = " / ".join(birim.alan_branslari)
    for anahtar, ihtiyac in sorted(brans_ihtiyaci.items(), key=lambda x: brans_adi[x[0]]):
        arz = izgara.brans_arzi.get(anahtar, 0)
        if arz == 0:
            teshis.append(
                f"{brans_adi[anahtar]} branşında görev alabilecek öğretmen yok; "
                "ders/branş eşlemesini gözden geçirin veya İlçe MEM'den öğretmen isteyin.")
        elif ihtiyac > arz * gun_sayisi * slot_sayisi:
            teshis.append(
                f"{brans_adi[anahtar]} branşı {ihtiyac} oturum-slot istiyor ama "
                f"{arz} öğretmenle {gun_sayisi} günde en çok "
                f"{arz * gun_sayisi * slot_sayisi} oturum yapılabilir.")

    # Kişisel sınırı yükseltilen öğrenciler engel değildir; yalnız günde slot
    # sayısından fazla sınav gerekenler planı imkânsız kılar.
    for ogrenci, sinir in sorted(ozet.kisisel_sinirlar(gun_sayisi).items()):
        if sinir > slot_sayisi:
            teshis.append(
                f"{ogrenci} öğrencisinin {ozet.ogrenci_yukleri[ogrenci]} sınavı "
                f"{gun_sayisi} güne sığmak için günde {sinir} oturum ister; günde "
                f"{slot_sayisi} oturum saati tanımlı.")

    if not teshis:
        teshis.append(
            "Kısıtlar tek tek sağlanabiliyor ama birlikte sağlanamadı. Gün sayısını "
            "artırmayı, hafta sonunu açmayı ya da günlük sınav sınırını yükseltmeyi deneyin.")
    return teshis


# ================================ Faz 3 — salon dağıtımı ve görevlendirme

@dataclass
class _GorevSayaci:
    """Kişi başına görev sayacı.

    Aynı öğretim yılının önceki dönemlerinde alınmış görevler başlangıç
    değeri olarak verilebilir; böylece yük tek dönemde değil yıl boyunca
    dengelenir.
    """

    komisyon: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    gozcu: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    @classmethod
    def baslangicla(cls, sayaclar: dict[int, tuple[int, int]] | None) -> "_GorevSayaci":
        sayac = cls()
        for kimlik, (komisyon, gozcu) in (sayaclar or {}).items():
            sayac.komisyon[kimlik] = komisyon
            sayac.gozcu[kimlik] = gozcu
        return sayac

    def toplam(self, kimlik: int) -> int:
        return self.komisyon[kimlik] + self.gozcu[kimlik]

    def rol_sayisi(self, kimlik: int, rol: GorevRolu) -> int:
        return (self.komisyon if rol is GorevRolu.KOMISYON_UYESI else self.gozcu)[kimlik]

    def ekle(self, kimlik: int, rol: GorevRolu) -> None:
        if rol is GorevRolu.KOMISYON_UYESI:
            self.komisyon[kimlik] += 1
        else:
            self.gozcu[kimlik] += 1


def _aday_sirala(adaylar: list[Personel], sayac: _GorevSayaci, rol: GorevRolu,
                 tercih: frozenset[int] = frozenset()) -> list[Personel]:
    """Yükü az olan önce; yönetici son çare; iki aşamalı derste önceki
    komisyon tercih edilir."""
    return sorted(adaylar, key=lambda p: (
        0 if p.kimlik in tercih else 1,
        1 if p.yonetici_mi else 0,
        sayac.rol_sayisi(p.kimlik, rol),
        sayac.toplam(p.kimlik),
        p.kimlik,
    ))


def _gorevlendir(oturum: Oturum, birim: SinavBirimi, uygun: list[Personel],
                 sayac: _GorevSayaci, tercih_komisyon: frozenset[int],
                 tercih_gozcu: frozenset[int],
                 gozcu_farkli_brans: bool) -> tuple[list[Gorevlendirme], list[str]]:
    """Bir oturumun komisyonunu ve gözcülerini seçer.

    SP-02: iki sınav öğretmeni, en az biri alan öğretmeni. İkinci alan
    öğretmeni yoksa gerekçe üretilir. Gözcünün sınav branşından farklı
    olması okul kararıdır; sağlanamazsa engel değil, gerekçeli not olur.
    """
    alan_kumesi = _brans_imzasi(birim)
    secilen: set[int] = set()
    gorevler: list[Gorevlendirme] = []
    notlar: list[str] = []

    def kalanlar(kosul=None) -> list[Personel]:
        return [p for p in uygun if p.kimlik not in secilen and (kosul is None or kosul(p))]

    def alanda(kisi: Personel) -> bool:
        return esitle(kisi.brans) in alan_kumesi

    # 1) En az bir alan öğretmeni zorunludur.
    alan_adaylari = _aday_sirala(kalanlar(alanda), sayac,
                                 GorevRolu.KOMISYON_UYESI, tercih_komisyon)
    if not alan_adaylari:
        raise PlanlamaBasarisiz(
            f"{birim.etiket()} sınavı için {' / '.join(birim.alan_branslari)} alanından uygun "
            f"öğretmen bulunamadı "
            f"({oturum.tarih.strftime('%d.%m.%Y')} {oturum.saat.strftime('%H:%M')}).")
    komisyon = [alan_adaylari[0]]
    secilen.add(alan_adaylari[0].kimlik)

    # 2) İkinci üye: tercihen yine alan öğretmeni. Birleşik derste (ör. Görsel
    #    Sanatlar/Müzik) mümkünse ikinci üye diğer alandan seçilir.
    birinci_brans = esitle(komisyon[0].brans)
    ikinci_alan = _aday_sirala(kalanlar(alanda), sayac,
                               GorevRolu.KOMISYON_UYESI, tercih_komisyon)
    if len(alan_kumesi) > 1:
        digerinden = [p for p in ikinci_alan if esitle(p.brans) != birinci_brans]
        if digerinden:
            ikinci_alan = digerinden + [p for p in ikinci_alan if p not in digerinden]
        elif ikinci_alan:
            notlar.append(
                f"{birim.etiket()}: birleşik dersin iki alanından yalnız "
                f"{komisyon[0].brans} alanında uygun öğretmen bulundu.")
    gerekce = ""
    if ikinci_alan:
        komisyon.append(ikinci_alan[0])
    else:
        diger = _aday_sirala(kalanlar(), sayac, GorevRolu.KOMISYON_UYESI, tercih_komisyon)
        if not diger:
            raise PlanlamaBasarisiz(
                f"{birim.etiket()} sınavı için ikinci komisyon üyesi bulunamadı "
                f"({oturum.tarih.strftime('%d.%m.%Y')} {oturum.saat.strftime('%H:%M')}).")
        komisyon.append(diger[0])
        gerekce = (f"Okulda ikinci {' / '.join(birim.alan_branslari)} alan öğretmeni "
                   "bulunmadığından OKY md.58/2-a uyarınca bir alan öğretmeni ve bir "
                   "öğretmen görevlendirildi.")
    for uye in komisyon:
        secilen.add(uye.kimlik)
        ek = gerekce
        if uye.yonetici_mi:
            ek = (ek + " " if ek else "") + (
                "Yeterli uygun öğretmen bulunamadığından yönetici görevlendirildi; "
                "Karar md.12/2-c gereği ücretlendirilmez.")
        gorevler.append(Gorevlendirme(oturum.anahtar, uye.kimlik,
                                      GorevRolu.KOMISYON_UYESI, ek.strip()))
        sayac.ekle(uye.kimlik, GorevRolu.KOMISYON_UYESI)

    # 3) Gözcüler: salon başına bir kişi.
    farkli = _aday_sirala(kalanlar(lambda p: esitle(p.brans) not in alan_kumesi),
                          sayac, GorevRolu.GOZCU, tercih_gozcu)
    havuz = list(farkli)
    if len(havuz) < birim.salon_sayisi:
        yedek = _aday_sirala(kalanlar(lambda p: p.kimlik not in {x.kimlik for x in havuz}),
                             sayac, GorevRolu.GOZCU, tercih_gozcu)
        if gozcu_farkli_brans and yedek:
            notlar.append(
                f"{birim.etiket()}: sınav branşından farklı yeterli gözcü bulunamadığı için "
                "aynı branştan gözcü görevlendirildi.")
        havuz += yedek
    if len(havuz) < birim.salon_sayisi:
        raise PlanlamaBasarisiz(
            f"{birim.etiket()} sınavı {birim.salon_sayisi} salonda yapılıyor ama "
            f"{oturum.tarih.strftime('%d.%m.%Y')} {oturum.saat.strftime('%H:%M')} saatinde "
            f"yalnız {len(havuz)} gözcü uygun.")
    for gozcu in havuz[:birim.salon_sayisi]:
        secilen.add(gozcu.kimlik)
        ek = ("Yeterli uygun öğretmen bulunamadığından yönetici görevlendirildi; "
              "Karar md.12/2-c gereği ücretlendirilmez." if gozcu.yonetici_mi else "")
        gorevler.append(Gorevlendirme(oturum.anahtar, gozcu.kimlik, GorevRolu.GOZCU, ek))
        sayac.ekle(gozcu.kimlik, GorevRolu.GOZCU)
    return gorevler, notlar


# ============================================================ ana akış

def _oturum_anahtari(birim: SinavBirimi, tur: OturumTuru) -> str:
    return sha256(f"{birim.anahtar}|{tur.value}".encode("utf-8")).hexdigest()[:16]


def plan_uret(birimler: list[SinavBirimi], parametreler: PlanParametreleri,
              gunler: list[date], personel: list[Personel], salonlar: list[Salon],
              pencere: tuple[date, date], ogretim_yili: str = "",
              ogrenci_adlari: dict[str, str] | None = None,
              baslangic_sayaclari: dict[int, tuple[int, int]] | None = None,
              gozcu_farkli_brans: bool = True,
              dugum_butcesi: int = ARAMA_DUGUM_BUTCESI,
              sure_butcesi: float = ARAMA_SURE_BUTCESI_SN) -> PlanlamaSonucu:
    """Sınav birimlerinden yerleşmiş ve görevlendirilmiş bir plan üretir."""
    parametreler.dogrula()
    if not birimler:
        raise PlanlamaBasarisiz("Planlanacak aktif sorumluluk kaydı yok.")
    if not salonlar:
        raise PlanlamaBasarisiz("Plan üretmeden önce en az bir sınav salonu tanımlanmalıdır.")

    uygun_personel = sorted((p for p in personel if p.gorev_alabilir_mi),
                            key=lambda p: p.kimlik)
    if not uygun_personel:
        raise PlanlamaBasarisiz(
            "Görev alabilecek personel yok. Müdür ve rehber öğretmenlere sınav görevi "
            "verilmez; e-Okul personel listesini içe aktardığınızdan emin olun.")

    ozet = yuk_ozeti(birimler, parametreler.iki_asamali_sayim,
                     parametreler.ogrenci_gunluk_sinav_siniri)
    # OKY md.58/2-ç: sınavlar dersleri aksatmayacak biçimde hafta içinde
    # planlanır, *gerektiğinde* cumartesi ve pazar da kullanılabilir. Bu yüzden
    # hafta içi günler öne alınır; hafta sonu ancak gün sayısı hafta içine
    # sığmadığında devreye girer.
    gunler = sorted(gunler, key=lambda g: (g.weekday() >= 5, g))
    slot_sayisi = len(parametreler.slot_saatleri)
    istenen_gun = parametreler.hedef_gun_sayisi or ozet.onerilen_gun_sayisi(slot_sayisi)
    gun_sayisi = min(istenen_gun, len(gunler))
    if gun_sayisi <= 0:
        raise PlanlamaBasarisiz("Seçilen pencerede planlanabilir gün yok.")
    try:
        kisisel_sinirlar = ozet.kisisel_sinirlar(gun_sayisi, slot_sayisi)
    except ValueError as hata:
        raise PlanlamaBasarisiz("Sınav planı verilen kısıtlarla üretilemedi.",
                                [str(hata)]) from hata

    def sinir_fn(ogrenci: str) -> int:
        return kisisel_sinirlar.get(ogrenci, parametreler.ogrenci_gunluk_sinav_siniri)

    imzalar = {_brans_imzasi(b) for b in birimler}
    brans_arzi = {imza: sum(1 for p in uygun_personel if esitle(p.brans) in imza)
                  for imza in imzalar}

    # Gün sayısı kademeli artırılır: en kısa program hedeflenir, sığmazsa bir
    # gün eklenip yeniden denenir. Kullanıcı sabit bir hedef verdiyse yalnız o
    # denenir.
    sira = _zorluk_sirasi(birimler, brans_arzi)
    ust_gun = gun_sayisi if parametreler.hedef_gun_sayisi else len(gunler)
    bitis = perf_counter() + sure_butcesi
    yerlesim = None
    for deneme_gun in range(gun_sayisi, ust_gun + 1):
        kalan_sure = bitis - perf_counter()
        if kalan_sure <= 0:
            break
        try:
            deneme_sinirlar = ozet.kisisel_sinirlar(deneme_gun, slot_sayisi)
        except ValueError:
            continue
        izgara = _Izgara(gun_sayisi=deneme_gun, slot_sayisi=slot_sayisi,
                         salon_adedi=len(salonlar), gorevli_adedi=len(uygun_personel),
                         brans_arzi=brans_arzi)
        izgara.hazirla(birimler,
                       lambda b: b.sinav_yuku(parametreler.iki_asamali_sayim),
                       lambda o: deneme_sinirlar.get(
                           o, parametreler.ogrenci_gunluk_sinav_siniri))
        yerlesim = _yerlestirme_ara(birimler, izgara, sira, dugum_butcesi,
                                    min(kalan_sure, DENEME_SURE_BUTCESI_SN))
        if yerlesim is not None:
            gun_sayisi = deneme_gun
            kisisel_sinirlar = deneme_sinirlar
            break
    if yerlesim is None:
        raise PlanlamaBasarisiz(
            "Sınav planı verilen kısıtlarla üretilemedi.",
            _teshis_uret(birimler, izgara, ozet, gun_sayisi, slot_sayisi,
                         parametreler.ogrenci_gunluk_sinav_siniri))

    plan = Plan(parametreler)
    notlar: list[str] = []
    sayac = _GorevSayaci.baslangicla(baslangic_sayaclari)
    salon_sirasi = sorted(salonlar, key=lambda s: (-s.kapasite, s.kimlik))

    # Slot slot ilerlenir; her slotta salonlar ve görevliler paylaştırılır.
    slot_birimleri: dict[tuple[int, int], list[tuple[SinavBirimi, OturumTuru, int]]] = defaultdict(list)
    for birim_no, (gun, ilk_slot) in enumerate(yerlesim):
        birim = birimler[birim_no]
        for adim, tur in enumerate(birim.oturum_turleri):
            slot_birimleri[(gun, ilk_slot + adim)].append((birim, tur, adim))

    birim_komisyonu: dict[str, frozenset[int]] = {}
    birim_gozcusu: dict[str, frozenset[int]] = {}

    for (gun, slot) in sorted(slot_birimleri):
        tarih = gunler[gun]
        saat = parametreler.slot_saatleri[slot]
        kalan_salonlar = list(salon_sirasi)
        slotta_secilen: set[int] = set()
        # Salon ihtiyacı çok olan ve branşı kıt olan sınav önce doyurulur.
        sirali = sorted(slot_birimleri[(gun, slot)], key=lambda x: (
            -x[0].salon_sayisi,
            brans_arzi.get(_brans_imzasi(x[0]), 0),
            siralama_anahtari(x[0].ders_adi),
            x[0].anahtar,
        ))
        for birim, tur, adim in sirali:
            secili_salonlar = tuple(s.kimlik for s in kalan_salonlar[:birim.salon_sayisi])
            kalan_salonlar = kalan_salonlar[birim.salon_sayisi:]
            oturum = Oturum(
                anahtar=_oturum_anahtari(birim, tur),
                ders_adi=birim.ders_adi,
                duzeyler=birim.duzeyler,
                ogrenci_anahtarlari=birim.ogrenci_anahtarlari,
                oturum_turu=tur,
                tarih=tarih,
                saat=saat,
                sure_dakika=parametreler.oturum_suresi_dakika,
                salon_kimlikleri=secili_salonlar,
                alan_bransi=birim.alan_bransi,
                esdeger_branslar=birim.esdeger_branslar,
                birim_anahtari=birim.anahtar if birim.iki_asamali_mi else "",
                hafta_sonu_gerekcesi=(
                    "Hafta içi pencere kapasitesi yetersiz kaldığı için OKY md.58/2-ç "
                    "uyarınca hafta sonuna yerleştirildi." if tarih.weekday() >= 5 else ""),
            )
            uygun = [p for p in uygun_personel if p.kimlik not in slotta_secilen]
            gorevler, gorev_notlari = _gorevlendir(
                oturum, birim, uygun, sayac,
                birim_komisyonu.get(birim.anahtar, frozenset()),
                birim_gozcusu.get(birim.anahtar, frozenset()),
                gozcu_farkli_brans)
            if adim == 0 and birim.iki_asamali_mi:
                # OKY md.58/2-e: komisyonların aynı üyelerden oluşturulması esastır.
                birim_komisyonu[birim.anahtar] = frozenset(
                    g.personel_kimligi for g in gorevler if g.rol is GorevRolu.KOMISYON_UYESI)
                birim_gozcusu[birim.anahtar] = frozenset(
                    g.personel_kimligi for g in gorevler if g.rol is GorevRolu.GOZCU)
            slotta_secilen.update(g.personel_kimligi for g in gorevler)
            plan.oturumlar.append(oturum)
            plan.gorevlendirmeler.extend(gorevler)
            notlar.extend(gorev_notlari)

    plan.oturumlar.sort(key=lambda o: (o.tarih, o.saat, siralama_anahtari(o.ders_adi)))
    baglam = DogrulamaBaglami(
        pencere=pencere,
        personel={p.kimlik: p for p in personel},
        ogrenci_adlari=ogrenci_adlari or {},
        iki_asamali_dersler=frozenset(b.ders_adi for b in birimler if b.iki_asamali_mi),
        ogretim_yili=ogretim_yili,
        kisisel_gunluk_sinir=kisisel_sinirlar,
    )
    ihlaller = dogrula_plan(plan, baglam, {s.kimlik: s for s in salonlar})

    hafta_sonu = sum(1 for o in plan.oturumlar if o.tarih.weekday() >= 5)
    if hafta_sonu:
        notlar.append(f"{hafta_sonu} oturum hafta sonuna yerleştirildi.")
    if kisisel_sinirlar:
        notlar.append(
            f"{len(kisisel_sinirlar)} öğrencinin günlük sınav sınırı yükseltildi; "
            "ayrıntı plan ekranındaki listede.")
    plan.notlar = notlar
    return PlanlamaSonucu(
        plan=plan,
        ihlaller=ihlaller,
        yukseltilen_sinirlar=kisisel_sinirlar,
        kullanilan_gun_sayisi=len({o.tarih for o in plan.oturumlar}),
        notlar=notlar,
    )
