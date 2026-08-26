"""Alan modelleri. Bu modül veritabanı ve Tkinter bilmez."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum

from .metin import kucult


class Ciddiyet(str, Enum):
    ENGEL = "ENGEL"
    UYARI = "UYARI"
    BILGI = "BILGI"


class GorevRolu(str, Enum):
    KOMISYON_UYESI = "komisyon_uyesi"
    GOZCU = "gozcu"


class OturumTuru(str, Enum):
    YAZILI = "yazili"
    UYGULAMA = "uygulama"


class IkiAsamaliSayim(str, Enum):
    """İki aşamalı derste yazılı+uygulama oturumlarının öğrencinin günlük
    sınav sayacına nasıl gireceği."""

    TEK = "tek"    # iki oturum birlikte tek sınav sayılır (varsayılan)
    AYRI = "ayri"  # her oturum ayrı sınav sayılır


# Unvan sınıflandırması. e-Okul personel raporundaki "Görevi" sütunu esas alınır.
_MUDUR_UNVANLARI = frozenset({"müdür", "okul müdürü"})
_YONETICI_UNVANLARI = _MUDUR_UNVANLARI | {"müdür yardımcısı", "müdür başyardımcısı"}


def mudur_mu(unvan: str) -> bool:
    return kucult(unvan or "").strip() in _MUDUR_UNVANLARI


def yonetici_mi(unvan: str) -> bool:
    return kucult(unvan or "").strip() in _YONETICI_UNVANLARI


def rehber_mi(unvan: str, brans: str) -> bool:
    metin = kucult(f"{unvan or ''} {brans or ''}")
    return "rehber" in metin or "psikolojik danışman" in metin


@dataclass(frozen=True)
class Ihlal:
    kural_kimligi: str
    dayanak_metni: str
    etkilenen_kayit: str
    ciddiyet: Ciddiyet
    aciklama: str

    @property
    def engel_mi(self) -> bool:
        return self.ciddiyet is Ciddiyet.ENGEL


@dataclass(frozen=True)
class SorumlulukKaydi:
    okul_no: str
    ad_soyad: str
    sube: str
    sinif_duzeyi: int
    ders_adi: str
    kaynak: str = "basarisizlik"  # basarisizlik | nakil_gecis (OKY md.58/1 son cümle)

    @property
    def ogrenci_anahtari(self) -> str:
        """Öğrenciyi düzeyden bağımsız tanımlayan anahtar."""
        return f"{self.okul_no}|{self.sube}"


@dataclass(frozen=True)
class Personel:
    kimlik: int
    ad: str
    brans: str
    unvan: str
    aktif_mi: bool = True

    @property
    def yonetici_mi(self) -> bool:
        return yonetici_mi(self.unvan)

    @property
    def mudur_mu(self) -> bool:
        return mudur_mu(self.unvan)

    @property
    def rehber_mi(self) -> bool:
        return rehber_mi(self.unvan, self.brans)

    @property
    def gorev_alabilir_mi(self) -> bool:
        """Müdür ve rehber öğretmen sınav görevi almaz; yönetici son çaredir."""
        return self.aktif_mi and not self.mudur_mu and not self.rehber_mi


@dataclass(frozen=True)
class Salon:
    kimlik: int
    ad: str
    kapasite: int


@dataclass(frozen=True)
class DersAyari:
    """Bir dersin planlamayı etkileyen özellikleri.

    `iki_asamali_mi` OKY md.58/2-e kapsamındaki Türk dili ve edebiyatı ile
    yabancı dil derslerini işaretler; bu dersler yazılı ve uygulama olmak
    üzere iki oturumla planlanır.
    """

    brans: str
    iki_asamali_mi: bool = False
    yabanci_dil_mi: bool = False


@dataclass(frozen=True)
class PlanParametreleri:
    """Kullanıcının plan üretmeden önce yanıtladığı sorular."""

    pencere_kodu: str
    hafta_sonu_kullan: bool = False
    ogrenci_gunluk_sinav_siniri: int = 2
    iki_asamali_sayim: IkiAsamaliSayim = IkiAsamaliSayim.TEK
    slot_saatleri: tuple[time, ...] = (
        time(8, 0), time(9, 0), time(10, 0), time(11, 0), time(13, 30), time(14, 30),
    )
    oturum_suresi_dakika: int = 40  # ÖDY md.5/1-l: bir ders saatini aşamaz
    hedef_gun_sayisi: int | None = None  # None ise yükten otomatik belirlenir

    def dogrula(self) -> None:
        if self.ogrenci_gunluk_sinav_siniri < 1:
            raise ValueError("Öğrenci günlük sınav sınırı en az 1 olmalıdır.")
        if not self.slot_saatleri:
            raise ValueError("En az bir oturum saati tanımlanmalıdır.")
        if len(set(self.slot_saatleri)) != len(self.slot_saatleri):
            raise ValueError("Oturum saatleri yinelenemez.")
        if any(onceki >= sonraki for onceki, sonraki in zip(self.slot_saatleri, self.slot_saatleri[1:])):
            raise ValueError("Oturum saatleri artan sırada girilmelidir.")
        if self.oturum_suresi_dakika < 1:
            raise ValueError("Oturum süresi sıfırdan büyük olmalıdır.")
        if self.hedef_gun_sayisi is not None and self.hedef_gun_sayisi < 1:
            raise ValueError("Hedef gün sayısı sıfırdan büyük olmalıdır.")


@dataclass
class Oturum:
    anahtar: str
    ders_adi: str
    duzeyler: tuple[int, ...]
    ogrenci_anahtarlari: tuple[str, ...]
    oturum_turu: OturumTuru
    tarih: date
    saat: time
    sure_dakika: int
    salon_kimlikleri: tuple[int, ...] = ()
    alan_bransi: str = ""
    birim_anahtari: str = ""   # iki aşamalı dersin iki oturumunu birbirine bağlar
    hafta_sonu_gerekcesi: str = ""
    kilitli_mi: bool = False

    @property
    def salon_sayisi(self) -> int:
        return len(self.salon_kimlikleri)

    @property
    def ogrenci_sayisi(self) -> int:
        return len(self.ogrenci_anahtarlari)


@dataclass(frozen=True)
class Gorevlendirme:
    oturum_anahtari: str
    personel_kimligi: int
    rol: GorevRolu
    gerekce: str = ""
    kilitli_mi: bool = False


@dataclass
class Plan:
    """Bir pencere için üretilmiş oturum ve görevlendirme kümesi."""

    parametreler: PlanParametreleri
    oturumlar: list[Oturum] = field(default_factory=list)
    gorevlendirmeler: list[Gorevlendirme] = field(default_factory=list)
    notlar: list[str] = field(default_factory=list)

    def oturum_bul(self, anahtar: str) -> Oturum | None:
        return next((o for o in self.oturumlar if o.anahtar == anahtar), None)

    def oturum_gorevleri(self, anahtar: str) -> list[Gorevlendirme]:
        return [g for g in self.gorevlendirmeler if g.oturum_anahtari == anahtar]

    @property
    def gun_sayisi(self) -> int:
        return len({o.tarih for o in self.oturumlar})
