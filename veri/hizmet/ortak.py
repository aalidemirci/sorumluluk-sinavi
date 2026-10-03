"""Ortak yapı taşları: hata türü, kurum ayarları, dönem pencereleri, tatil
günleri, salonlar ve yedek. Her modül buna dayanır, bu hiçbirine dayanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from cekirdek.metin import esitle
from cekirdek.modeller import Salon
from cekirdek.takvim import sinav_pencereleri, tarih_coz, varsayilan_pencere_kodu
from ..veritabani import Veritabani, simdi


AYAR_ZORUNLU = (
    "okul_adi", "mudur_adi", "il", "ilce", "ogretim_yili",
    "birinci_donem_baslangic", "ikinci_donem_baslangic", "ikinci_donem_bitis",
)

VARSAYILAN_SLOT_SAATLERI = ("08:00", "09:00", "10:00", "11:00", "13:30", "14:30")


class HizmetHatasi(ValueError):
    """Kullanıcıya gösterilebilir servis hatası."""


# ============================================================ kurum ayarları

def ayarlari_getir(vt: Veritabani) -> dict[str, str]:
    with vt.baglan() as b:
        return {r[0]: r[1] for r in b.execute("SELECT anahtar,deger FROM kurum_ayari")}


DONEM_TARIHLERI = ("birinci_donem_baslangic", "ikinci_donem_baslangic", "ikinci_donem_bitis")


def ayarlari_kaydet(vt: Veritabani, ayarlar: dict[str, str]) -> None:
    """Kurum ayarlarını kaydeder.

    Tarihler arayüzde gg.aa.yyyy yazılır; veritabanında ISO biçiminde
    (YYYY-AA-GG) saklanır ki sıralama ve karşılaştırma metin olarak da doğru
    çalışsın.
    """
    eksik = [k for k in AYAR_ZORUNLU if not str(ayarlar.get(k, "")).strip()]
    if eksik:
        raise HizmetHatasi("Şu alanlar doldurulmalıdır: " + ", ".join(eksik))
    try:
        tarihler = {k: tarih_coz(str(ayarlar[k])) for k in DONEM_TARIHLERI}
    except ValueError as hata:
        raise HizmetHatasi(str(hata)) from hata
    if not (tarihler["birinci_donem_baslangic"] < tarihler["ikinci_donem_baslangic"]
            <= tarihler["ikinci_donem_bitis"]):
        raise HizmetHatasi(
            "Dönem tarihleri kronolojik olmalıdır: 1. dönem başlangıcı < 2. dönem "
            "başlangıcı ≤ 2. dönem bitişi.")
    ayarlar = {**ayarlar, **{k: v.isoformat() for k, v in tarihler.items()}}
    zaman = simdi()
    with vt.baglan() as b:
        for anahtar, deger in ayarlar.items():
            b.execute(
                "INSERT INTO kurum_ayari(anahtar,deger,guncellendi_at) VALUES(?,?,?)"
                " ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger,"
                " guncellendi_at=excluded.guncellendi_at",
                (anahtar, str(deger).strip(), zaman))
        vt.denetim_yaz(b, "kurum_ayari", 0, "kaydedildi")


def pencereleri_getir(vt: Veritabani) -> dict[str, tuple[date, date]]:
    ayar = ayarlari_getir(vt)
    eksik = [k for k in DONEM_TARIHLERI if not ayar.get(k)]
    if eksik:
        raise HizmetHatasi("Sınav pencereleri için önce dönem tarihleri kaydedilmelidir.")
    return sinav_pencereleri(*(tarih_coz(ayar[k]) for k in DONEM_TARIHLERI))


def ogretim_yili(vt: Veritabani) -> str:
    return ayarlari_getir(vt).get("ogretim_yili", "")


def varsayilan_pencere(vt: Veritabani, gecmise_bak: bool = False,
                       bugun: date | None = None) -> str:
    """Ekranların açılışta seçeceği dönem; bkz. takvim.varsayilan_pencere_kodu."""
    try:
        return varsayilan_pencere_kodu(pencereleri_getir(vt), bugun or date.today(), gecmise_bak)
    except HizmetHatasi:
        return "P1"


# ============================================================ tatil günleri

def tatil_ekle(vt: Veritabani, tarih: date, aciklama: str = "") -> int:
    """Resmî tatil ya da idari izin gününü kaydeder (SP-08).

    Plan bu güne sınav koymaz; başvuru ve teslim süresi hesapları bu günü iş
    günü saymaz.
    """
    with vt.baglan() as b:
        mevcut = b.execute("SELECT id FROM v_tatil_gunu WHERE tarih=?",
                           (tarih.isoformat(),)).fetchone()
        if mevcut:
            b.execute("UPDATE tatil_gunu SET aciklama=? WHERE id=?",
                      (aciklama.strip(), mevcut[0]))
            kimlik = int(mevcut[0])
        else:
            kimlik = int(b.execute("INSERT INTO tatil_gunu(tarih,aciklama) VALUES(?,?)",
                                   (tarih.isoformat(), aciklama.strip())).lastrowid)
        vt.denetim_yaz(b, "tatil_gunu", kimlik, "kaydedildi")
        return kimlik


def tatil_sil(vt: Veritabani, tatil_id: int) -> None:
    with vt.baglan() as b:
        b.execute("UPDATE tatil_gunu SET silindi_mi=1 WHERE id=?", (tatil_id,))
        vt.denetim_yaz(b, "tatil_gunu", tatil_id, "silindi")


def tatil_listesi(vt: Veritabani) -> list[dict]:
    with vt.baglan() as b:
        return [{"kimlik": r[0], "tarih": date.fromisoformat(r[1]), "aciklama": r[2]}
                for r in b.execute("SELECT id,tarih,aciklama FROM v_tatil_gunu ORDER BY tarih")]


def tatilleri_getir(vt: Veritabani) -> frozenset[date]:
    return frozenset(t["tarih"] for t in tatil_listesi(vt))


# ===================================================================== salon

def salon_ekle(vt: Veritabani, ad: str, kapasite: int) -> int:
    ad = " ".join(str(ad).split())
    if not ad:
        raise HizmetHatasi("Salon adı zorunludur.")
    if kapasite <= 0:
        raise HizmetHatasi("Salon kapasitesi sıfırdan büyük olmalıdır.")
    with vt.baglan() as b:
        mevcut = b.execute("SELECT id FROM salon WHERE ad_anahtari=?", (esitle(ad),)).fetchone()
        if mevcut:
            b.execute("UPDATE salon SET ad=?,kapasite=?,aktif_mi=1,silindi_mi=0 WHERE id=?",
                      (ad, kapasite, mevcut[0]))
            kimlik = int(mevcut[0])
        else:
            kimlik = int(b.execute(
                "INSERT INTO salon(ad,ad_anahtari,kapasite) VALUES(?,?,?)",
                (ad, esitle(ad), kapasite)).lastrowid)
        vt.denetim_yaz(b, "salon", kimlik, "kaydedildi")
        return kimlik


def salon_sil(vt: Veritabani, salon_id: int) -> None:
    with vt.baglan() as b:
        kullanim = b.execute(
            "SELECT count(*) FROM v_oturum_salon WHERE salon_id=?", (salon_id,)).fetchone()[0]
        if kullanim:
            raise HizmetHatasi(
                f"Bu salon {kullanim} oturumda kullanılıyor; önce planı temizleyin.")
        b.execute("UPDATE salon SET silindi_mi=1 WHERE id=?", (salon_id,))
        vt.denetim_yaz(b, "salon", salon_id, "silindi")


def salonlari_getir(vt: Veritabani) -> list[Salon]:
    with vt.baglan() as b:
        return [Salon(r[0], r[1], r[2]) for r in b.execute(
            "SELECT id,ad,kapasite FROM v_salon WHERE aktif_mi=1 ORDER BY kapasite DESC,id")]


# =========================================================== personel aktarımı

@dataclass
class AktarimOzeti:
    aktarim_id: int
    eklenen: int = 0
    guncellenen: int = 0
    degismedi: int = 0
    cikan: int = 0
    satirlar: list[tuple] = field(default_factory=list)
    # Aktarımı durdurmayan ama kullanıcının görmesi gereken notlar.
    uyarilar: list[str] = field(default_factory=list)

    @property
    def toplam(self) -> int:
        return self.eklenen + self.guncellenen + self.degismedi


# ================================================================== yedek

def yedek_al(vt: Veritabani, hedef_klasor: Path) -> Path:
    """Veritabanının tam yedeğini (WAL dâhil) seçilen klasöre alır."""
    yol = vt.yedek_al(Path(hedef_klasor))
    with vt.baglan() as b:
        vt.denetim_yaz(b, "veritabani", 0, "yedek_alindi")
    return yol
