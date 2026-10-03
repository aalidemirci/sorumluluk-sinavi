"""Evrakın ve teslim çizelgesinin veri sorguları; ilan (KVKK) sorguları.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cekirdek.metin import maskele, siralama_anahtari
from cekirdek.takvim import is_gunu_ekle
from ..veritabani import Veritabani, simdi

from .ortak import HizmetHatasi, tatilleri_getir
from .gorev import gorev_havuzu_ozeti


# ============================================================ evrak teslimi

EVRAK_TURLERI = (
    ("sinav_kagitlari", "Sınav kâğıtları"),
    ("komisyon_tutanagi", "Komisyon tutanağı"),
    ("yoklama_listesi", "Yoklama / salon listesi"),
    ("kagit_sarf_tutanagi", "Kâğıt sarf tutanağı"),
    ("kopya_tutanagi", "Kopya tutanağı"),
    ("diger", "Diğer"),
)
EVRAK_ADLARI = dict(EVRAK_TURLERI)

# TS-01: her oturum için geri dönmesi beklenen evrak. Kopya tutanağı yalnız
# olay varsa düzenlendiği için beklenenler arasında değildir.
BEKLENEN_EVRAK = ("sinav_kagitlari", "komisyon_tutanagi", "yoklama_listesi")

# TS-02: sınav tarihinden sonra bu kadar iş günü içinde teslim beklenir.
TESLIM_SURESI_IS_GUNU = 1


@dataclass(frozen=True)
class TeslimSatiri:
    oturum_id: int
    oturum_etiketi: str
    tarih: date
    evrak_turu: str
    adet: int | None = None
    teslim_at: str = ""
    teslim_eden: str = ""
    teslim_alan: str = ""
    aciklama: str = ""
    # Teslim süresi iş günüyle sayılır; tatil günleri iş günü değildir.
    tatiller: frozenset[date] = frozenset()

    @property
    def evrak_adi(self) -> str:
        return EVRAK_ADLARI.get(self.evrak_turu, self.evrak_turu)

    @property
    def teslim_edildi_mi(self) -> bool:
        return bool(self.teslim_at)

    def son_gun(self, tatiller=None) -> date:
        return is_gunu_ekle(self.tarih, TESLIM_SURESI_IS_GUNU,
                            self.tatiller if tatiller is None else tatiller)

    def gecikti_mi(self, bugun: date | None = None) -> bool:
        """TS-02: süresi içinde teslim edilmemiş evrak gecikmiş sayılır."""
        if self.teslim_edildi_mi:
            return False
        return (bugun or date.today()) > self.son_gun()

    def durum(self, bugun: date | None = None) -> str:
        if self.teslim_edildi_mi:
            return "teslim alındı"
        return "gecikti" if self.gecikti_mi(bugun) else "bekleniyor"


def teslim_cizelgesi(vt: Veritabani, plan_id: int) -> list[TeslimSatiri]:
    """Plandaki her oturum için beklenen evrakın durumunu döndürür."""
    with vt.baglan() as b:
        oturumlar = b.execute("""
            SELECT o.id, replace(o.duzey_kumesi,',','/')||' '||d.ad||
                   CASE o.oturum_turu WHEN 'uygulama' THEN ' (uygulama)' ELSE '' END,
                   o.tarih
            FROM v_oturum o JOIN v_ders d ON d.id=o.ders_id
            WHERE o.plan_id=? ORDER BY o.tarih, o.saat, d.ad""", (plan_id,)).fetchall()
        kayitli = {}
        for r in b.execute("""
                SELECT t.oturum_id, t.evrak_turu, t.adet, COALESCE(t.teslim_at,''),
                       COALESCE(eden.ad,''), COALESCE(alan.ad,''), t.aciklama
                FROM v_evrak_teslim t
                JOIN v_oturum o ON o.id=t.oturum_id
                LEFT JOIN v_personel eden ON eden.id=t.teslim_eden_personel_id
                LEFT JOIN v_personel alan ON alan.id=t.teslim_alan_personel_id
                WHERE o.plan_id=?""", (plan_id,)):
            kayitli[(r[0], r[1])] = r

    tatiller = tatilleri_getir(vt)
    cizelge: list[TeslimSatiri] = []
    for oturum_id, etiket, tarih_metin in oturumlar:
        tarih = date.fromisoformat(tarih_metin)
        turler = list(BEKLENEN_EVRAK)
        turler += [tur for (oid, tur) in sorted(kayitli)
                   if oid == oturum_id and tur not in turler]
        for tur in turler:
            kayit = kayitli.get((oturum_id, tur))
            cizelge.append(TeslimSatiri(
                oturum_id=oturum_id, oturum_etiketi=etiket, tarih=tarih, evrak_turu=tur,
                adet=kayit[2] if kayit else None,
                teslim_at=kayit[3] if kayit else "",
                teslim_eden=kayit[4] if kayit else "",
                teslim_alan=kayit[5] if kayit else "",
                aciklama=kayit[6] if kayit else "",
                tatiller=tatiller))
    return cizelge


def teslim_kaydet(vt: Veritabani, oturum_id: int, evrak_turu: str,
                  teslim_eden_personel_id: int, teslim_alan_personel_id: int,
                  adet: int | None = None, aciklama: str = "",
                  teslim_tarihi: date | None = None) -> None:
    """Evrakın teslim alındığını kaydeder."""
    if evrak_turu not in EVRAK_ADLARI:
        raise HizmetHatasi("Geçersiz evrak türü.")
    if not teslim_eden_personel_id or not teslim_alan_personel_id:
        raise HizmetHatasi("Teslim eden ve teslim alan görevli seçilmelidir.")
    if teslim_eden_personel_id == teslim_alan_personel_id:
        raise HizmetHatasi("Evrakı teslim eden ile teslim alan aynı kişi olamaz (TS-03).")
    if adet is not None and adet < 0:
        raise HizmetHatasi("Adet negatif olamaz.")
    zaman = (teslim_tarihi or date.today()).isoformat()
    with vt.baglan() as b:
        if not b.execute("SELECT 1 FROM v_oturum WHERE id=?", (oturum_id,)).fetchone():
            raise HizmetHatasi("Oturum bulunamadı.")
        b.execute(
            "INSERT INTO evrak_teslim(oturum_id,evrak_turu,adet,teslim_eden_personel_id,"
            "teslim_alan_personel_id,teslim_at,aciklama) VALUES(?,?,?,?,?,?,?)"
            " ON CONFLICT(oturum_id,evrak_turu) DO UPDATE SET"
            " adet=excluded.adet,teslim_eden_personel_id=excluded.teslim_eden_personel_id,"
            " teslim_alan_personel_id=excluded.teslim_alan_personel_id,"
            " teslim_at=excluded.teslim_at,aciklama=excluded.aciklama,silindi_mi=0",
            (oturum_id, evrak_turu, adet, teslim_eden_personel_id,
             teslim_alan_personel_id, zaman, aciklama.strip()))
        vt.denetim_yaz(b, "evrak_teslim", oturum_id, "teslim_alindi", evrak_turu)


def teslim_geri_al(vt: Veritabani, oturum_id: int, evrak_turu: str) -> None:
    with vt.baglan() as b:
        b.execute("UPDATE evrak_teslim SET silindi_mi=1 WHERE oturum_id=? AND evrak_turu=?",
                  (oturum_id, evrak_turu))
        vt.denetim_yaz(b, "evrak_teslim", oturum_id, "teslim_geri_alindi", evrak_turu)


def teslim_ozeti(vt: Veritabani, plan_id: int, bugun: date | None = None) -> dict[str, int]:
    cizelge = teslim_cizelgesi(vt, plan_id)
    return {
        "toplam": len(cizelge),
        "teslim": sum(1 for s in cizelge if s.teslim_edildi_mi),
        "gecikti": sum(1 for s in cizelge if s.gecikti_mi(bugun)),
        "bekliyor": sum(1 for s in cizelge
                        if not s.teslim_edildi_mi and not s.gecikti_mi(bugun)),
    }


# ==================================================== evrak veri sorguları

def plan_oturumlari(vt: Veritabani, plan_id: int) -> list[dict]:
    """Evrak üretimi için oturum listesi; görevliler ve salonlar dâhil."""
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT o.id, replace(o.duzey_kumesi,',','/'), d.ad, o.oturum_turu,
                   o.tarih, o.saat, o.sure, COALESCE(d.brans,'')
            FROM v_oturum o JOIN v_ders d ON d.id=o.ders_id
            WHERE o.plan_id=? ORDER BY o.tarih, o.saat, d.ad""", (plan_id,)).fetchall()
        sonuc = []
        for r in satirlar:
            salonlar = [x[0] for x in b.execute(
                "SELECT s.ad FROM v_oturum_salon os JOIN v_salon s ON s.id=os.salon_id"
                " WHERE os.oturum_id=? ORDER BY os.sira", (r[0],))]
            # (ad, rol, branş, gözcünün salonu) — salon eski planlarda boştur.
            gorevliler = [(x[0], x[1], x[2], x[3] or "") for x in b.execute(
                "SELECT p.ad, g.rol, COALESCE(p.brans,''), s.ad FROM v_gorevlendirme g"
                " JOIN v_personel p ON p.id=g.personel_id"
                " LEFT JOIN v_salon s ON s.id=g.salon_id"
                " WHERE g.oturum_id=? ORDER BY g.rol DESC, s.ad, p.ad", (r[0],))]
            ogrenci_sayisi = b.execute(
                "SELECT count(*) FROM v_oturum_ogrenci WHERE oturum_id=?",
                (r[0],)).fetchone()[0]
            sonuc.append({
                "id": r[0], "duzey": r[1], "ders": r[2], "tur": r[3],
                "tarih": date.fromisoformat(r[4]), "saat": r[5], "sure": r[6],
                "brans": r[7], "salonlar": salonlar, "gorevliler": gorevliler,
                "ogrenci_sayisi": ogrenci_sayisi,
                "etiket": f"{r[1]} {r[2]}" + (" (uygulama)" if r[3] == "uygulama" else ""),
            })
        return sonuc


def oturum_ogrencileri(vt: Veritabani, oturum_id: int) -> list[dict]:
    with vt.baglan() as b:
        return [{"sira": r[0], "okul_no": r[1], "ad_soyad": r[2], "sube": r[3],
                 "salon": r[4] or ""}
                for r in b.execute("""
                    SELECT oo.sira, og.okul_no, og.ad_soyad, og.sube, s.ad
                    FROM v_oturum_ogrenci oo
                    JOIN v_ogrenci og ON og.id=oo.ogrenci_id
                    LEFT JOIN v_salon s ON s.id=oo.salon_id
                    WHERE oo.oturum_id=? ORDER BY oo.sira""", (oturum_id,))]


def gorev_sayaclari(vt: Veritabani) -> list[dict]:
    """EK-05 raporu için kişi başına görev sayacı; dönem dökümü dâhil."""
    return gorev_havuzu_ozeti(vt)


def evrak_surumu_kaydet(vt: Veritabani, tur: str, kayit_anahtari: str,
                        dosya_yolu: Path, sha256: str, onayli: bool = False) -> int:
    """Üretilen belgenin sürümünü ve dosya kaydını işler.

    Aynı içerik yeniden üretilirse yeni sürüm açılmaz. Onaylanmış bir belge
    sonradan değişirse yeni sürüm açılır ve değişiklik föyü metni saklanır;
    böylece hangi çıktının hangi içerikten geldiği denetlenebilir.

    `onayli`: belge müdür onayıyla kesinleşmiş plandan üretildi. 0.6.2'ye kadar
    bu bilgi hiç verilmiyordu, onaylı sürüm olmadığı için föy de hiç
    oluşmuyordu. Aynı içerik önce taslakken üretilmişse yeni sürüm açılmaz,
    var olan sürüm onaylı işaretlenir.
    """
    with vt.baglan() as b:
        onceki = b.execute(
            "SELECT id,surum,sha256,onaylandi_mi FROM belge_surumu"
            " WHERE tur=? AND kayit_anahtari=? ORDER BY surum DESC LIMIT 1",
            (tur, kayit_anahtari)).fetchone()
        if onceki and onceki[2] == sha256:
            surum_id = int(onceki[0])
            if onayli and not onceki[3]:
                b.execute("UPDATE belge_surumu SET onaylandi_mi=1 WHERE id=?", (surum_id,))
        else:
            surum = int(onceki[1]) + 1 if onceki else 1
            foy = (f"Onaylanmış belge değişti — önceki sürüm {onceki[1]} "
                   f"(SHA-256 {onceki[2]}), yeni sürüm {surum} (SHA-256 {sha256})"
                   ) if onceki and onceki[3] else None
            surum_id = int(b.execute(
                "INSERT INTO belge_surumu(tur,kayit_anahtari,surum,sha256,kaynak_sha256,"
                "onceki_surum_id,onaylandi_mi,degisiklik_foyu,olusturma_tarihi)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (tur, kayit_anahtari, surum, sha256, sha256,
                 onceki[0] if onceki else None, int(onayli), foy, simdi())).lastrowid)
        b.execute(
            "INSERT INTO evrak_kaydi(tur,kayit_anahtari,dosya_yolu,belge_surumu_id,uretildi_at)"
            " VALUES(?,?,?,?,?)",
            (tur, kayit_anahtari, str(dosya_yolu), surum_id, simdi()))
        vt.denetim_yaz(b, "evrak_kaydi", surum_id, "uretildi", tur)
        return surum_id


def onayli_belge_degisiklikleri(vt: Veritabani, kayit_anahtari: str) -> list[dict]:
    """Onaylı bir sürümden sonra içeriği değişen belgeler (değişiklik föyleri).

    Kesin planda görevli değişikliği gibi bir düzeltmeden sonra evrak yeniden
    üretilince imzalanmış eski çıktı geçerliliğini yitirir; arayüz bu listeyle
    kullanıcıyı uyarır.
    """
    with vt.baglan() as b:
        return [{"tur": r[0], "surum": r[1], "foy": r[2], "tarih": r[3]} for r in b.execute(
            "SELECT tur,surum,degisiklik_foyu,olusturma_tarihi FROM belge_surumu"
            " WHERE kayit_anahtari=? AND degisiklik_foyu IS NOT NULL ORDER BY tur,surum",
            (kayit_anahtari,))]


def evrak_gecmisi(vt: Veritabani, kayit_anahtari: str) -> list[tuple]:
    """Bir plan için üretilmiş belgelerin sürüm geçmişi."""
    with vt.baglan() as b:
        return [tuple(r) for r in b.execute(
            "SELECT tur,surum,sha256,olusturma_tarihi FROM belge_surumu"
            " WHERE kayit_anahtari=? ORDER BY tur,surum", (kayit_anahtari,))]


# ==================================================== ilan (KVKK) sorguları

# Okul web sayfasında ilan edilen çizelgede öğrencinin nasıl gösterileceği.
OGRENCI_GOSTERIMI = (
    ("no_ve_maskeli_ad", "Okul numarası + maskeli ad (A**** D*****)"),
    ("yalniz_no", "Yalnız okul numarası"),
    ("yalniz_maskeli_ad", "Yalnız maskeli ad"),
)
OGRENCI_GOSTERIM_ADLARI = dict(OGRENCI_GOSTERIMI)


def ogrenci_etiketi_uret(okul_no: str, ad_soyad: str, gosterim: str) -> str:
    """İlan çizelgesinde öğrencinin görüneceği biçimi üretir.

    Açık ad hiçbir seçenekte yazılmaz; ilan herkese açık bir sayfada
    yayımlanacağı için ad yalnız maskeli biçimde geçebilir.
    """
    if gosterim not in OGRENCI_GOSTERIM_ADLARI:
        raise HizmetHatasi("Geçersiz öğrenci gösterim biçimi.")
    maskeli = maskele(ad_soyad)
    if gosterim == "yalniz_no":
        return str(okul_no)
    if gosterim == "yalniz_maskeli_ad":
        return maskeli
    return f"{okul_no} — {maskeli}"


def ilan_takvimi(vt: Veritabani, plan_id: int) -> list[dict]:
    """İlan edilecek sınav takvimi; kişisel veri içermez.

    Ne öğrenci ne de görevli adı geçer; yalnız ders, tarih, saat ve salon.
    """
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT replace(o.duzey_kumesi,',','/'), d.ad, o.oturum_turu,
                   o.tarih, o.saat, o.sure,
                   COALESCE((SELECT group_concat(s.ad, ', ')
                             FROM v_oturum_salon os JOIN v_salon s ON s.id=os.salon_id
                             WHERE os.oturum_id=o.id), '')
            FROM v_oturum o JOIN v_ders d ON d.id=o.ders_id
            WHERE o.plan_id=? ORDER BY o.tarih, o.saat, d.ad""", (plan_id,)).fetchall()
    return [{
        "duzey": r[0], "ders": r[1], "tur": r[2],
        "tarih": date.fromisoformat(r[3]), "saat": r[4], "sure": r[5],
        "salonlar": r[6],
        "etiket": f"{r[0]} {r[1]}" + (" (uygulama)" if r[2] == "uygulama" else ""),
    } for r in satirlar]


def ilan_ogrenci_cizelgesi(vt: Veritabani, plan_id: int,
                           gosterim: str = "no_ve_maskeli_ad") -> list[dict]:
    """Öğrenci başına sınav listesi; ad maskelenmiş olarak döner.

    Öğrenci kendi satırını okul numarasından bulur; açık ad yayımlanmaz.
    Birden çok salonlu sınavda öğrencinin kendi salonu yazılır; eski
    sürüm bütün salonları sıralıyordu ve öğrenci nereye gideceğini
    bilemiyordu. Salonu kayıtlı olmayan eski planlarda yine hepsi yazılır.
    """
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT og.okul_no, og.ad_soyad, og.sube,
                   replace(o.duzey_kumesi,',','/'), d.ad, o.oturum_turu,
                   o.tarih, o.saat,
                   COALESCE((SELECT s.ad FROM v_salon s WHERE s.id=oo.salon_id),
                            (SELECT group_concat(s.ad, ', ')
                             FROM v_oturum_salon os JOIN v_salon s ON s.id=os.salon_id
                             WHERE os.oturum_id=o.id), '')
            FROM v_oturum_ogrenci oo
            JOIN v_ogrenci og ON og.id=oo.ogrenci_id
            JOIN v_oturum o ON o.id=oo.oturum_id
            JOIN v_ders d ON d.id=o.ders_id
            WHERE o.plan_id=? ORDER BY og.okul_no, o.tarih, o.saat""", (plan_id,)).fetchall()

    ogrenciler: dict[str, dict] = {}
    for r in satirlar:
        anahtar = f"{r[0]}|{r[2]}"
        kayit = ogrenciler.setdefault(anahtar, {
            "okul_no": r[0],
            "etiket": ogrenci_etiketi_uret(r[0], r[1], gosterim),
            "sube": r[2],
            "sinavlar": [],
        })
        kayit["sinavlar"].append({
            "etiket": f"{r[3]} {r[4]}" + (" (uygulama)" if r[5] == "uygulama" else ""),
            "tarih": date.fromisoformat(r[6]),
            "saat": r[7],
            "salonlar": r[8],
        })
    return sorted(ogrenciler.values(), key=lambda x: (len(x["okul_no"]), x["okul_no"]))


def gorevli_listesi(vt: Veritabani, plan_id: int) -> list[dict]:
    """Tebliğ-tebellüğ bölümü için görevli personelin tekilleştirilmiş listesi."""
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT p.id, p.ad, COALESCE(p.brans,''), p.unvan,
                   SUM(CASE WHEN g.rol='komisyon_uyesi' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN g.rol='gozcu' THEN 1 ELSE 0 END)
            FROM v_gorevlendirme g
            JOIN v_personel p ON p.id=g.personel_id
            JOIN v_oturum o ON o.id=g.oturum_id
            WHERE o.plan_id=? GROUP BY p.id, p.ad, p.brans, p.unvan""", (plan_id,)).fetchall()
    liste = [{"kimlik": r[0], "ad": r[1], "brans": r[2], "unvan": r[3],
              "komisyon": r[4], "gozcu": r[5]} for r in satirlar]
    return sorted(liste, key=lambda x: siralama_anahtari(x["ad"]))


def kisi_bazli_gorevler(vt: Veritabani, plan_id: int) -> list[dict]:
    """Her görevlinin kendi görev listesi: tarih, saat, sınav, rol, salon.

    Görevlendirme çizelgesi sınav başınadır; öğretmen kendi görevlerini
    bulmak için bütün çizelgeyi taramak zorunda kalıyordu. Tebliğ de kişinin
    hangi görevleri tebellüğ ettiğini göstermelidir.
    """
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT p.id, p.ad, COALESCE(p.brans,''), p.unvan, o.tarih, o.saat, o.sure,
                   replace(o.duzey_kumesi,',','/') || ' ' || d.ad ||
                   CASE o.oturum_turu WHEN 'uygulama' THEN ' (uygulama)' ELSE '' END,
                   g.rol,
                   COALESCE(gs.ad, (SELECT group_concat(s.ad, ', ')
                                    FROM v_oturum_salon os JOIN v_salon s ON s.id=os.salon_id
                                    WHERE os.oturum_id=o.id), '')
            FROM v_gorevlendirme g
            JOIN v_personel p ON p.id = g.personel_id
            JOIN v_oturum o ON o.id = g.oturum_id
            JOIN v_ders d ON d.id = o.ders_id
            LEFT JOIN v_salon gs ON gs.id = g.salon_id
            WHERE o.plan_id = ? ORDER BY o.tarih, o.saat""", (plan_id,)).fetchall()
    kisiler: dict[int, dict] = {}
    for kimlik, ad, brans, unvan, tarih, saat, sure, sinav, rol, salon in satirlar:
        kayit = kisiler.setdefault(kimlik, {"kimlik": kimlik, "ad": ad, "brans": brans,
                                            "unvan": unvan, "gorevler": []})
        kayit["gorevler"].append({"tarih": date.fromisoformat(tarih), "saat": saat,
                                  "sure": sure, "sinav": sinav, "rol": rol, "salon": salon})
    return sorted(kisiler.values(), key=lambda x: siralama_anahtari(x["ad"]))
