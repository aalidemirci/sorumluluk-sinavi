"""Servis katmanı — arayüz ile çekirdek/veritabanı arasındaki tek geçit.

Arayüz SQL yazmaz, çekirdek de veritabanı bilmez. Kural denetimi burada
tekrarlanmaz; `cekirdek.kurallar.dogrula_plan` çağrılır.

Plan üretimi ile plan kaydı bilinçli olarak ayrılmıştır: `plan_hazirla`
hiçbir şey yazmaz, üretilen plan bellekte düzenlenir (sürükle-bırak, geri
al), `plan_kaydet` ise tek bir işlemde yazar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from cekirdek.kurallar import DogrulamaBaglami, dogrula_plan
from cekirdek.metin import esitle, siralama_anahtari
from cekirdek.modeller import (
    DersAyari, GorevRolu, Gorevlendirme, Ihlal, IkiAsamaliSayim, Oturum, OturumTuru,
    Personel, Plan, PlanParametreleri, Salon, SorumlulukKaydi,
)
from cekirdek.planlayici import PlanlamaSonucu, plan_uret
from cekirdek.takvim import gunleri_listele, sinav_pencereleri
from cekirdek.talep import SinavBirimi, YukOzeti, birimleri_olustur, yuk_ozeti
from .rapor_okuma import (
    PersonelRaporu, SorumlulukRaporu, personel_raporu_oku, sorumluluk_raporu_oku,
)
from .veritabani import Veritabani, simdi


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


def ayarlari_kaydet(vt: Veritabani, ayarlar: dict[str, str]) -> None:
    eksik = [k for k in AYAR_ZORUNLU if not str(ayarlar.get(k, "")).strip()]
    if eksik:
        raise HizmetHatasi("Şu alanlar doldurulmalıdır: " + ", ".join(eksik))
    try:
        tarihler = {k: date.fromisoformat(str(ayarlar[k]).strip())
                    for k in ("birinci_donem_baslangic", "ikinci_donem_baslangic",
                              "ikinci_donem_bitis")}
    except ValueError as hata:
        raise HizmetHatasi("Tarihler YYYY-AA-GG biçiminde girilmelidir.") from hata
    if not (tarihler["birinci_donem_baslangic"] < tarihler["ikinci_donem_baslangic"]
            <= tarihler["ikinci_donem_bitis"]):
        raise HizmetHatasi(
            "Dönem tarihleri kronolojik olmalıdır: 1. dönem başlangıcı < 2. dönem "
            "başlangıcı ≤ 2. dönem bitişi.")
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
    eksik = [k for k in ("birinci_donem_baslangic", "ikinci_donem_baslangic",
                         "ikinci_donem_bitis") if not ayar.get(k)]
    if eksik:
        raise HizmetHatasi("Sınav pencereleri için önce dönem tarihleri kaydedilmelidir.")
    return sinav_pencereleri(*(date.fromisoformat(ayar[k]) for k in (
        "birinci_donem_baslangic", "ikinci_donem_baslangic", "ikinci_donem_bitis")))


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


# ============================================================== branş havuzu

def brans_havuzu_listele(vt: Veritabani) -> list[tuple[int, str, str]]:
    with vt.baglan() as b:
        return [tuple(r) for r in b.execute(
            "SELECT id,ad,kaynak FROM v_brans_havuzu ORDER BY ad")]


def brans_havuzu_ekle(vt: Veritabani, ad: str, kaynak: str = "manuel_ilce_mem") -> int:
    ad = " ".join(str(ad).split())
    if not ad:
        raise HizmetHatasi("Branş adı zorunludur.")
    zaman = simdi()
    with vt.baglan() as b:
        b.execute(
            "INSERT INTO brans_havuzu(ad,ad_anahtari,kaynak,olusturuldu_at,guncellendi_at)"
            " VALUES(?,?,?,?,?) ON CONFLICT(ad_anahtari) DO UPDATE SET"
            " aktif_mi=1,guncellendi_at=excluded.guncellendi_at",
            (ad, esitle(ad), kaynak, zaman, zaman))
        kimlik = int(b.execute("SELECT id FROM brans_havuzu WHERE ad_anahtari=?",
                               (esitle(ad),)).fetchone()[0])
        vt.denetim_yaz(b, "brans_havuzu", kimlik, "eklendi")
        return kimlik


# =========================================================== personel aktarımı

@dataclass
class AktarimOzeti:
    aktarim_id: int
    eklenen: int = 0
    guncellenen: int = 0
    degismedi: int = 0
    cikan: int = 0
    satirlar: list[tuple] = field(default_factory=list)

    @property
    def toplam(self) -> int:
        return self.eklenen + self.guncellenen + self.degismedi


def personel_onizle(vt: Veritabani, yol: Path) -> AktarimOzeti:
    """Personel raporunu okuyup staging'e yazar; ana tabloya dokunmaz."""
    rapor = personel_raporu_oku(Path(yol))
    with vt.baglan() as b:
        onceki = b.execute(
            "SELECT id,durum FROM ice_aktarim WHERE tur='personel' AND sha256=?",
            (rapor.dosya_ozeti,)).fetchone()
        if onceki and onceki[1] == "onaylandi":
            raise HizmetHatasi("Bu personel raporu daha önce onaylanmıştır.")
        if onceki:
            b.execute("DELETE FROM personel_aktarim_satiri WHERE ice_aktarim_id=?", (onceki[0],))
            aktarim_id = int(onceki[0])
        else:
            aktarim_id = int(b.execute(
                "INSERT INTO ice_aktarim(tur,dosya_adi,sha256,olusturuldu_at)"
                " VALUES('personel',?,?,?)",
                (Path(yol).name, rapor.dosya_ozeti, simdi())).lastrowid)

        mevcut = {r["ad_anahtari"]: r for r in b.execute(
            "SELECT ad_anahtari,brans,unvan,personel_tipi,kadro_durumu,aktif_mi"
            " FROM v_personel")}
        ozet = AktarimOzeti(aktarim_id)
        gelen = set()
        for kayit in rapor.kayitlar:
            anahtar = esitle(kayit.ad)
            gelen.add(anahtar)
            eski = mevcut.get(anahtar)
            if eski is None:
                eylem = "eklenecek"
                ozet.eklenen += 1
            elif ((eski["brans"], eski["unvan"], eski["personel_tipi"],
                   eski["kadro_durumu"], eski["aktif_mi"])
                  != (kayit.brans, kayit.unvan, kayit.personel_tipi, kayit.kadro_durumu, 1)):
                eylem = "guncellenecek"
                ozet.guncellenen += 1
            else:
                eylem = "degismedi"
                ozet.degismedi += 1
            b.execute(
                "INSERT INTO personel_aktarim_satiri(ice_aktarim_id,satir_no,ad,unvan,"
                "kadro_durumu,brans,personel_tipi,kurum_sicil_no,eylem)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (aktarim_id, kayit.satir_no, kayit.ad, kayit.unvan, kayit.kadro_durumu,
                 kayit.brans, kayit.personel_tipi, kayit.kurum_sicil_no or None, eylem))
            ozet.satirlar.append((kayit.ad, kayit.unvan, kayit.kadro_durumu, kayit.brans, eylem))
        ozet.cikan = sum(1 for a, r in mevcut.items() if r["aktif_mi"] and a not in gelen)
        b.execute("UPDATE ice_aktarim SET eklenen=?,guncellenen=?,degismedi=?,cikan=?"
                  " WHERE id=?",
                  (ozet.eklenen, ozet.guncellenen, ozet.degismedi, ozet.cikan, aktarim_id))
        return ozet


def personel_onayla(vt: Veritabani, aktarim_id: int) -> AktarimOzeti:
    """Staging'deki personel farkını ana tabloya uygular."""
    with vt.baglan() as b:
        aktarim = b.execute(
            "SELECT durum FROM ice_aktarim WHERE id=? AND tur='personel'",
            (aktarim_id,)).fetchone()
        if not aktarim:
            raise HizmetHatasi("Personel içe aktarımı bulunamadı.")
        if aktarim[0] == "onaylandi":
            raise HizmetHatasi("Bu içe aktarım zaten onaylanmıştır.")
        satirlar = b.execute(
            "SELECT ad,unvan,kadro_durumu,brans,personel_tipi,kurum_sicil_no,eylem"
            " FROM personel_aktarim_satiri WHERE ice_aktarim_id=? ORDER BY satir_no",
            (aktarim_id,)).fetchall()
        if not satirlar:
            raise HizmetHatasi("Onaylanacak satır yok.")

        mevcut = {r[0]: r[1] for r in b.execute(
            "SELECT ad_anahtari,id FROM personel WHERE silindi_mi=0")}
        ozet = AktarimOzeti(aktarim_id)
        gelen = set()
        zaman = simdi()
        for ad, unvan, kadro, brans, tip, sicil, eylem in satirlar:
            anahtar = esitle(ad)
            gelen.add(anahtar)
            if anahtar in mevcut:
                b.execute(
                    "UPDATE personel SET ad=?,brans=?,unvan=?,personel_tipi=?,kadro_durumu=?,"
                    "kurum_sicil_no=?,aktif_mi=1,kaynak_aktarim_id=? WHERE id=?",
                    (ad, brans, unvan, tip, kadro, sicil, aktarim_id, mevcut[anahtar]))
                ozet.guncellenen += int(eylem == "guncellenecek")
                ozet.degismedi += int(eylem == "degismedi")
            else:
                b.execute(
                    "INSERT INTO personel(ad,ad_anahtari,brans,unvan,personel_tipi,"
                    "kadro_durumu,kurum_sicil_no,kaynak_aktarim_id)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (ad, anahtar, brans, unvan, tip, kadro, sicil, aktarim_id))
                ozet.eklenen += 1
            # Branş havuzu personel raporundan beslenir.
            b.execute(
                "INSERT INTO brans_havuzu(ad,ad_anahtari,kaynak,olusturuldu_at,guncellendi_at)"
                " VALUES(?,?,'personel_raporu',?,?) ON CONFLICT(ad_anahtari) DO UPDATE SET"
                " aktif_mi=1,guncellendi_at=excluded.guncellendi_at",
                (brans, esitle(brans), zaman, zaman))
        for anahtar, kimlik in mevcut.items():
            if anahtar not in gelen:
                ozet.cikan += b.execute(
                    "UPDATE personel SET aktif_mi=0 WHERE id=? AND aktif_mi=1",
                    (kimlik,)).rowcount
        b.execute("UPDATE ice_aktarim SET durum='onaylandi',onaylandi_at=?,eklenen=?,"
                  "guncellenen=?,degismedi=?,cikan=? WHERE id=?",
                  (zaman, ozet.eklenen, ozet.guncellenen, ozet.degismedi, ozet.cikan,
                   aktarim_id))
        vt.denetim_yaz(b, "ice_aktarim", aktarim_id, "personel_onaylandi",
                       f"+{ozet.eklenen} ~{ozet.guncellenen} -{ozet.cikan}")
        return ozet


def personelleri_getir(vt: Veritabani, yalniz_aktif: bool = True) -> list[Personel]:
    kosul = " WHERE aktif_mi=1" if yalniz_aktif else ""
    with vt.baglan() as b:
        return [Personel(r[0], r[1], r[2], r[3], bool(r[4])) for r in b.execute(
            f"SELECT id,ad,brans,unvan,aktif_mi FROM v_personel{kosul} ORDER BY id")]


# ======================================================== sorumluluk aktarımı

def sorumluluk_onizle(vt: Veritabani, yol: Path) -> AktarimOzeti:
    rapor = sorumluluk_raporu_oku(Path(yol))
    with vt.baglan() as b:
        onceki = b.execute(
            "SELECT id,durum FROM ice_aktarim WHERE tur='sorumluluk' AND sha256=?",
            (rapor.dosya_ozeti,)).fetchone()
        if onceki and onceki[1] == "onaylandi":
            raise HizmetHatasi("Bu sorumluluk raporu daha önce onaylanmıştır.")
        if onceki:
            b.execute("DELETE FROM sorumluluk_aktarim_satiri WHERE ice_aktarim_id=?",
                      (onceki[0],))
            aktarim_id = int(onceki[0])
        else:
            aktarim_id = int(b.execute(
                "INSERT INTO ice_aktarim(tur,dosya_adi,sha256,olusturuldu_at)"
                " VALUES('sorumluluk',?,?,?)",
                (Path(yol).name, rapor.dosya_ozeti, simdi())).lastrowid)

        mevcut = {(r[0], r[1], r[2], r[3], r[4]): r[5] for r in b.execute("""
            SELECT o.okul_no,o.sube,d.ad,s.duzey,s.kaynak,o.ad_soyad
            FROM v_sorumluluk_kaydi s
            JOIN v_ogrenci o ON o.id=s.ogrenci_id
            JOIN v_ders d ON d.id=s.ders_id WHERE s.durum='aktif'""")}
        ozet = AktarimOzeti(aktarim_id)
        gelen = set()
        for sira, kayit in enumerate(rapor.kayitlar, 1):
            anahtar = (kayit.okul_no, kayit.sube, kayit.ders_adi,
                       kayit.sinif_duzeyi, kayit.kaynak)
            gelen.add(anahtar)
            if anahtar not in mevcut:
                eylem = "eklenecek"
                ozet.eklenen += 1
            elif mevcut[anahtar] != kayit.ad_soyad:
                eylem = "guncellenecek"
                ozet.guncellenen += 1
            else:
                eylem = "degismedi"
                ozet.degismedi += 1
            b.execute(
                "INSERT INTO sorumluluk_aktarim_satiri(ice_aktarim_id,satir_no,okul_no,"
                "ad_soyad,sube,duzey,ders_adi,kaynak,eylem) VALUES(?,?,?,?,?,?,?,?,?)",
                (aktarim_id, sira, kayit.okul_no, kayit.ad_soyad, kayit.sube,
                 kayit.sinif_duzeyi, kayit.ders_adi, kayit.kaynak, eylem))
            ozet.satirlar.append((kayit.okul_no, kayit.ad_soyad, kayit.sube,
                                  kayit.sinif_duzeyi, kayit.ders_adi, eylem))
        ozet.cikan = sum(1 for a in mevcut if a not in gelen)
        b.execute("UPDATE ice_aktarim SET eklenen=?,guncellenen=?,degismedi=?,cikan=?"
                  " WHERE id=?",
                  (ozet.eklenen, ozet.guncellenen, ozet.degismedi, ozet.cikan, aktarim_id))
        return ozet


def sorumluluk_onayla(vt: Veritabani, aktarim_id: int, tam_liste: bool = True) -> AktarimOzeti:
    """Staging'deki sorumluluk farkını ana tabloya uygular.

    `tam_liste` doğruysa dosyada bulunmayan aktif kayıtlar pasife alınır —
    OOK12001R010 okulun tamamını kapsar. Kısmi bir liste aktarılıyorsa
    yanlışlıkla toplu pasife alma olmasın diye bu kapatılabilir.
    """
    with vt.baglan() as b:
        aktarim = b.execute(
            "SELECT durum FROM ice_aktarim WHERE id=? AND tur='sorumluluk'",
            (aktarim_id,)).fetchone()
        if not aktarim:
            raise HizmetHatasi("Sorumluluk içe aktarımı bulunamadı.")
        if aktarim[0] == "onaylandi":
            raise HizmetHatasi("Bu içe aktarım zaten onaylanmıştır.")
        satirlar = b.execute(
            "SELECT okul_no,ad_soyad,sube,duzey,ders_adi,kaynak FROM sorumluluk_aktarim_satiri"
            " WHERE ice_aktarim_id=? ORDER BY satir_no", (aktarim_id,)).fetchall()
        if not satirlar:
            raise HizmetHatasi("Onaylanacak satır yok.")

        ozet = AktarimOzeti(aktarim_id)
        gelen: set[tuple[int, int, int, str]] = set()
        for okul_no, ad_soyad, sube, duzey, ders_adi, kaynak in satirlar:
            b.execute(
                "INSERT INTO ogrenci(okul_no,ad_soyad,sube,sinif_duzeyi) VALUES(?,?,?,?)"
                " ON CONFLICT(okul_no,sube) DO UPDATE SET ad_soyad=excluded.ad_soyad,"
                " silindi_mi=0",
                (okul_no, ad_soyad, sube, int(str(sube).split("/", 1)[0])))
            b.execute(
                "INSERT INTO ders(ad,ad_anahtari) VALUES(?,?)"
                " ON CONFLICT(ad_anahtari) DO UPDATE SET silindi_mi=0",
                (ders_adi, esitle(ders_adi)))
            ogrenci_id = b.execute("SELECT id FROM ogrenci WHERE okul_no=? AND sube=?",
                                   (okul_no, sube)).fetchone()[0]
            ders_id = b.execute("SELECT id FROM ders WHERE ad_anahtari=?",
                                (esitle(ders_adi),)).fetchone()[0]
            b.execute(
                "INSERT INTO sorumluluk_kaydi(ogrenci_id,ders_id,duzey,kaynak,ice_aktarim_id)"
                " VALUES(?,?,?,?,?) ON CONFLICT(ogrenci_id,ders_id,duzey,kaynak) DO UPDATE SET"
                " durum='aktif',silindi_mi=0,ice_aktarim_id=excluded.ice_aktarim_id",
                (ogrenci_id, ders_id, duzey, kaynak, aktarim_id))
            gelen.add((ogrenci_id, ders_id, duzey, kaynak))
        if tam_liste:
            for r in b.execute(
                    "SELECT id,ogrenci_id,ders_id,duzey,kaynak FROM v_sorumluluk_kaydi"
                    " WHERE durum='aktif'").fetchall():
                if (r[1], r[2], r[3], r[4]) not in gelen:
                    ozet.cikan += b.execute(
                        "UPDATE sorumluluk_kaydi SET durum='pasif_aktarim' WHERE id=?",
                        (r[0],)).rowcount
        ozet.eklenen = len(satirlar)
        b.execute("UPDATE ice_aktarim SET durum='onaylandi',onaylandi_at=?,cikan=? WHERE id=?",
                  (simdi(), ozet.cikan, aktarim_id))
        vt.denetim_yaz(b, "ice_aktarim", aktarim_id, "sorumluluk_onaylandi",
                       f"{len(satirlar)} satır, -{ozet.cikan}")
        return ozet


def sorumluluk_kayitlari(vt: Veritabani) -> list[SorumlulukKaydi]:
    with vt.baglan() as b:
        return [SorumlulukKaydi(r[0], r[1], r[2], r[3], r[4], r[5]) for r in b.execute("""
            SELECT o.okul_no,o.ad_soyad,o.sube,s.duzey,d.ad,s.kaynak
            FROM v_sorumluluk_kaydi s
            JOIN v_ogrenci o ON o.id=s.ogrenci_id
            JOIN v_ders d ON d.id=s.ders_id
            WHERE s.durum='aktif' ORDER BY d.ad,s.duzey,o.okul_no""")]


def ogrenci_etiketleri(vt: Veritabani) -> dict[str, str]:
    """Öğrenci anahtarı -> ihlal metinlerinde görünecek okunur etiket."""
    with vt.baglan() as b:
        return {f"{r[0]}|{r[1]}": f"{r[2]} (No: {r[0]}, {r[1]})" for r in b.execute(
            "SELECT okul_no,sube,ad_soyad FROM v_ogrenci")}


# ====================================================================== ders

def dersleri_listele(vt: Veritabani) -> list[tuple]:
    with vt.baglan() as b:
        return [tuple(r) for r in b.execute("""
            SELECT d.id,d.ad,COALESCE(d.brans,''),d.iki_asamali_mi,d.yabanci_dil_mi,
                   (SELECT count(*) FROM v_sorumluluk_kaydi s
                     WHERE s.ders_id=d.id AND s.durum='aktif'),
                   d.esdeger_branslar
            FROM v_ders d ORDER BY d.ad""")]


def ders_esdeger_branslari(kayit) -> tuple[str, ...]:
    """`dersleri_listele` satırındaki JSON eşdeğer branş listesini çözer."""
    import json
    try:
        return tuple(json.loads(kayit[6] or "[]"))
    except (ValueError, IndexError):
        return ()


def ders_brans_esle(vt: Veritabani, ders_id: int, brans: str, karar: str,
                    esdeger_branslar: tuple[str, ...] = ()) -> None:
    brans = " ".join(str(brans).split())
    if not brans:
        raise HizmetHatasi("Branş seçilmelidir.")
    if not str(karar).strip():
        raise HizmetHatasi("Eşleme kararının gerekçesi zorunludur; denetimde sorulur.")
    with vt.baglan() as b:
        for ad in (brans, *esdeger_branslar):
            if not b.execute("SELECT 1 FROM v_brans_havuzu WHERE ad_anahtari=?",
                             (esitle(ad),)).fetchone():
                raise HizmetHatasi(
                    f"'{ad}' branş havuzunda yok. Önce branş havuzuna ekleyin.")
        # Ayırıcıyla birleştirilmez: branş adının kendisinde eğik çizgi
        # bulunabilir ("Kimya / Kimya Teknolojisi" tek branştır).
        import json
        ek = json.dumps(list(esdeger_branslar), ensure_ascii=False)
        okunur = " + ".join((brans, *esdeger_branslar))
        surum = b.execute("SELECT COALESCE(MAX(surum),0)+1 FROM ders_brans WHERE ders_id=?",
                          (ders_id,)).fetchone()[0]
        b.execute(
            "INSERT INTO ders_brans(ders_id,brans,surum,karar_metni,etkin_baslangic)"
            " VALUES(?,?,?,?,?)",
            (ders_id, okunur, surum, str(karar).strip(), date.today().isoformat()))
        b.execute("UPDATE ders SET brans=?,esdeger_branslar=? WHERE id=?",
                  (brans, ek, ders_id))
        vt.denetim_yaz(b, "ders", ders_id, "brans_eslendi", okunur)


def ders_ozellik_guncelle(vt: Veritabani, ders_id: int, iki_asamali_mi: bool,
                          yabanci_dil_mi: bool) -> None:
    """OKY md.58/2-e bayrağını kullanıcı kararıyla ayarlar."""
    with vt.baglan() as b:
        b.execute("UPDATE ders SET iki_asamali_mi=?,yabanci_dil_mi=? WHERE id=?",
                  (int(iki_asamali_mi), int(yabanci_dil_mi), ders_id))
        vt.denetim_yaz(b, "ders", ders_id, "ozellik_guncellendi",
                       f"iki_asamali={int(iki_asamali_mi)}")


def ders_ayarlari(vt: Veritabani) -> dict[str, DersAyari]:
    """Planlayıcının beklediği ders → ayar sözlüğü."""
    import json
    ayarlar: dict[str, DersAyari] = {}
    with vt.baglan() as b:
        for ad, brans, iki, yabanci, ek in b.execute(
                "SELECT ad,COALESCE(brans,''),iki_asamali_mi,yabanci_dil_mi,"
                "esdeger_branslar FROM v_ders"):
            try:
                esdeger = tuple(json.loads(ek or "[]"))
            except ValueError:
                esdeger = ()
            ayarlar[ad] = DersAyari(
                brans=str(brans).strip(),
                iki_asamali_mi=bool(iki),
                yabanci_dil_mi=bool(yabanci),
                esdeger_branslar=esdeger,
            )
    return ayarlar


def iki_asamali_onerisi(ders_adi: str) -> bool:
    """OKY md.58/2-e için ad temelli öneri; kullanıcı onaylar ya da değiştirir."""
    ad = esitle(ders_adi)
    return "yabancı dil" in ad or ad == "türk dili ve edebiyatı" or "ngilizce" in ad


# ===================================================================== plan

@dataclass
class PlanBaglami:
    """Doğrulama ve gösterim için gereken dış bilgiler."""

    pencere: tuple[date, date]
    personel: dict[int, Personel]
    salonlar: dict[int, Salon]
    ogrenci_adlari: dict[str, str]
    iki_asamali_dersler: frozenset[str]
    ogretim_yili: str
    kisisel_sinirlar: dict[str, int] = field(default_factory=dict)

    def dogrulama_baglami(self) -> DogrulamaBaglami:
        return DogrulamaBaglami(
            pencere=self.pencere,
            personel=self.personel,
            ogrenci_adlari=self.ogrenci_adlari,
            iki_asamali_dersler=self.iki_asamali_dersler,
            ogretim_yili=self.ogretim_yili,
            kisisel_gunluk_sinir=self.kisisel_sinirlar,
        )

    def personel_adi(self, kimlik: int) -> str:
        kisi = self.personel.get(kimlik)
        return kisi.ad if kisi else f"#{kimlik}"

    def salon_adi(self, kimlik: int) -> str:
        salon = self.salonlar.get(kimlik)
        return salon.ad if salon else f"#{kimlik}"


def plan_baglami(vt: Veritabani, pencere_kodu: str,
                 kisisel_sinirlar: dict[str, int] | None = None) -> PlanBaglami:
    ayar = ayarlari_getir(vt)
    with vt.baglan() as b:
        iki_asamali = frozenset(
            r[0] for r in b.execute("SELECT ad FROM v_ders WHERE iki_asamali_mi=1"))
    return PlanBaglami(
        pencere=pencereleri_getir(vt)[pencere_kodu],
        personel={p.kimlik: p for p in personelleri_getir(vt, yalniz_aktif=False)},
        salonlar={s.kimlik: s for s in salonlari_getir(vt)},
        ogrenci_adlari=ogrenci_etiketleri(vt),
        iki_asamali_dersler=iki_asamali,
        ogretim_yili=ayar.get("ogretim_yili", ""),
        kisisel_sinirlar=kisisel_sinirlar or {},
    )


def brans_eslemelerini_denetle(vt: Veritabani, dersler: set[str]) -> None:
    """Eşlenen branşların havuzda gerçekten bulunduğunu doğrular.

    Eşleme havuzdaki bir adla tutmuyorsa o derse hiçbir öğretmen atanamaz.
    Bu sessizce "öğretmen yok" hatasına dönüşmesin diye önden söylenir;
    eski sürümlerden kalan bozuk eşlemeler de böyle yakalanır.
    """
    havuz = {esitle(ad) for _, ad, _ in brans_havuzu_listele(vt)}
    hatali = []
    for ders, ayar in ders_ayarlari(vt).items():
        if ders not in dersler:
            continue
        for brans in ayar.alan_branslari:
            if brans and esitle(brans) not in havuz:
                hatali.append(f"{ders} → '{brans}'")
    if hatali:
        raise HizmetHatasi(
            "Şu derslerin branş eşlemesi branş havuzundaki hiçbir alanla tutmuyor. "
            "Ders / Branş ekranından yeniden eşleyin:\n\n"
            + "\n".join(f"  • {satir}" for satir in sorted(hatali)[:10]))


def sinav_birimleri(vt: Veritabani) -> list[SinavBirimi]:
    kayitlar = sorumluluk_kayitlari(vt)
    if not kayitlar:
        raise HizmetHatasi(
            "Aktif sorumluluk kaydı yok. Önce e-Okul sorumluluk raporunu içe aktarın.")
    salonlar = salonlari_getir(vt)
    if not salonlar:
        raise HizmetHatasi("Önce en az bir sınav salonu tanımlayın.")
    brans_eslemelerini_denetle(vt, {k.ders_adi for k in kayitlar})
    return birimleri_olustur(kayitlar, ders_ayarlari(vt), salonlar)


def yuk_ozetini_getir(vt: Veritabani, sayim: IkiAsamaliSayim,
                      gunluk_sinir: int) -> YukOzeti:
    return yuk_ozeti(sinav_birimleri(vt), sayim, gunluk_sinir)


def plan_hazirla(vt: Veritabani, parametreler: PlanParametreleri) -> PlanlamaSonucu:
    """Planı üretir; **veritabanına hiçbir şey yazmaz.**

    Üretilen plan arayüzde düzenlenir (sürükle-bırak, geri al) ve ancak
    `plan_kaydet` çağrıldığında yazılır.
    """
    pencere = pencereleri_getir(vt)[parametreler.pencere_kodu]
    gunler = gunleri_listele(pencere[0], pencere[1], parametreler.hafta_sonu_kullan)
    ayar = ayarlari_getir(vt)
    return plan_uret(
        birimler=sinav_birimleri(vt),
        parametreler=parametreler,
        gunler=gunler,
        personel=personelleri_getir(vt),
        salonlar=salonlari_getir(vt),
        pencere=pencere,
        ogretim_yili=ayar.get("ogretim_yili", ""),
        ogrenci_adlari=ogrenci_etiketleri(vt),
    )


def plani_dogrula(vt: Veritabani, plan: Plan,
                  kisisel_sinirlar: dict[str, int] | None = None) -> list[Ihlal]:
    """Elle düzenlenmiş planı da aynı kurallardan geçirir."""
    baglam = plan_baglami(vt, plan.parametreler.pencere_kodu, kisisel_sinirlar)
    return dogrula_plan(plan, baglam.dogrulama_baglami(), baglam.salonlar)


def plan_kaydet(vt: Veritabani, sonuc: PlanlamaSonucu) -> int:
    """Planı, oturumları, öğrenci yerleşimini ve görevleri tek işlemde yazar."""
    plan = sonuc.plan
    parametreler = plan.parametreler
    ogrenci_kimlikleri = {}
    with vt.baglan() as b:
        for okul_no, sube, kimlik in b.execute("SELECT okul_no,sube,id FROM v_ogrenci"):
            ogrenci_kimlikleri[f"{okul_no}|{sube}"] = kimlik
        ders_kimlikleri = {r[0]: r[1] for r in b.execute("SELECT ad,id FROM v_ders")}

        # Aynı pencere için önceki taslak plan varsa yerine yenisi geçer;
        # kesinleşmiş plan korunur.
        b.execute("UPDATE plan SET silindi_mi=1 WHERE pencere_kodu=? AND durum='taslak'"
                  " AND silindi_mi=0", (parametreler.pencere_kodu,))
        # Yükseltilmiş kişisel sınırlar planın parçasıdır; saklanmazsa
        # kaydedilen plan yeniden açıldığında varsayılan sınırla doğrulanır ve
        # kurallara uyan plan SP-11 ihlalleriyle dolu görünür.
        import json
        plan_id = int(b.execute(
            "INSERT INTO plan(pencere_kodu,parametreler_json,kisisel_sinirlar_json,uretildi_at)"
            " VALUES(?,?,?,?)",
            (parametreler.pencere_kodu, _parametreleri_yaz(parametreler),
             json.dumps(sonuc.yukseltilen_sinirlar, ensure_ascii=False, sort_keys=True),
             simdi())).lastrowid)

        for oturum in plan.oturumlar:
            ders_id = ders_kimlikleri.get(oturum.ders_adi)
            if ders_id is None:
                raise HizmetHatasi(f"'{oturum.ders_adi}' dersi veritabanında bulunamadı.")
            oturum_id = int(b.execute(
                "INSERT INTO oturum(plan_id,anahtar,ders_id,duzey_kumesi,oturum_turu,"
                "birim_anahtari,tarih,saat,sure,hafta_sonu_gerekcesi,kilitli_mi)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (plan_id, oturum.anahtar, ders_id,
                 ",".join(str(d) for d in oturum.duzeyler), oturum.oturum_turu.value,
                 oturum.birim_anahtari, oturum.tarih.isoformat(),
                 oturum.saat.strftime("%H:%M"), oturum.sure_dakika,
                 oturum.hafta_sonu_gerekcesi, int(oturum.kilitli_mi))).lastrowid)
            for sira, salon_id in enumerate(oturum.salon_kimlikleri, 1):
                b.execute("INSERT INTO oturum_salon(oturum_id,salon_id,sira) VALUES(?,?,?)",
                          (oturum_id, salon_id, sira))
            for sira, anahtar in enumerate(oturum.ogrenci_anahtarlari, 1):
                ogrenci_id = ogrenci_kimlikleri.get(anahtar)
                if ogrenci_id is None:
                    raise HizmetHatasi(f"'{anahtar}' öğrencisi veritabanında bulunamadı.")
                salon_id = (oturum.salon_kimlikleri[(sira - 1) % len(oturum.salon_kimlikleri)]
                            if oturum.salon_kimlikleri else None)
                b.execute(
                    "INSERT INTO oturum_ogrenci(oturum_id,ogrenci_id,salon_id,sira)"
                    " VALUES(?,?,?,?)", (oturum_id, ogrenci_id, salon_id, sira))
            for gorev in plan.oturum_gorevleri(oturum.anahtar):
                kisi = b.execute("SELECT unvan FROM v_personel WHERE id=?",
                                 (gorev.personel_kimligi,)).fetchone()
                yonetici = Personel(0, "", "", kisi[0]).yonetici_mi if kisi else False
                b.execute(
                    "INSERT INTO gorevlendirme(oturum_id,personel_id,rol,"
                    "ucretlendirilebilir_mi,gerekce,kilitli_mi) VALUES(?,?,?,?,?,?)",
                    (oturum_id, gorev.personel_kimligi, gorev.rol.value,
                     int(not yonetici), gorev.gerekce, int(gorev.kilitli_mi)))
        vt.denetim_yaz(b, "plan", plan_id, "kaydedildi",
                       f"{len(plan.oturumlar)} oturum")
        return plan_id


def plan_yukle(vt: Veritabani, plan_id: int) -> tuple[Plan, dict[str, int]]:
    """Kaydedilmiş planı bellek modeline geri okur."""
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT pencere_kodu,parametreler_json,durum,mudur_onay_no,kisisel_sinirlar_json"
            " FROM v_plan WHERE id=?", (plan_id,)).fetchone()
        if not satir:
            raise HizmetHatasi("Plan bulunamadı.")
        parametreler = _parametreleri_oku(satir[1], satir[0])
        plan = Plan(parametreler)
        oturum_anahtarlari = {}
        for r in b.execute("""
                SELECT o.id,o.anahtar,d.ad,o.duzey_kumesi,o.oturum_turu,o.birim_anahtari,
                       o.tarih,o.saat,o.sure,o.hafta_sonu_gerekcesi,o.kilitli_mi,
                       COALESCE(d.brans,''),d.esdeger_branslar
                FROM v_oturum o JOIN v_ders d ON d.id=o.ders_id
                WHERE o.plan_id=? ORDER BY o.tarih,o.saat,d.ad""", (plan_id,)):
            ogrenciler = tuple(x[0] for x in b.execute(
                "SELECT og.okul_no||'|'||og.sube FROM v_oturum_ogrenci oo"
                " JOIN v_ogrenci og ON og.id=oo.ogrenci_id"
                " WHERE oo.oturum_id=? ORDER BY oo.sira", (r[0],)))
            salonlar = tuple(x[0] for x in b.execute(
                "SELECT salon_id FROM v_oturum_salon WHERE oturum_id=? ORDER BY sira", (r[0],)))
            import json
            try:
                esdeger = tuple(json.loads(r[12] or "[]"))
            except ValueError:
                esdeger = ()
            plan.oturumlar.append(Oturum(
                anahtar=r[1], ders_adi=r[2],
                duzeyler=tuple(int(x) for x in str(r[3]).split(",") if x),
                ogrenci_anahtarlari=ogrenciler, oturum_turu=OturumTuru(r[4]),
                tarih=date.fromisoformat(r[6]), saat=time.fromisoformat(r[7]),
                sure_dakika=r[8], salon_kimlikleri=salonlar,
                alan_bransi=str(r[11]).strip(),
                esdeger_branslar=esdeger,
                birim_anahtari=r[5], hafta_sonu_gerekcesi=r[9], kilitli_mi=bool(r[10])))
            oturum_anahtarlari[r[0]] = r[1]
        for oturum_id, personel_id, rol, gerekce, kilitli in b.execute("""
                SELECT g.oturum_id,g.personel_id,g.rol,g.gerekce,g.kilitli_mi
                FROM v_gorevlendirme g JOIN v_oturum o ON o.id=g.oturum_id
                WHERE o.plan_id=? ORDER BY g.id""", (plan_id,)):
            plan.gorevlendirmeler.append(Gorevlendirme(
                oturum_anahtarlari[oturum_id], personel_id, GorevRolu(rol),
                gerekce or "", bool(kilitli)))
        import json
        try:
            kisisel_sinirlar = dict(json.loads(satir[4] or "{}"))
        except ValueError:
            kisisel_sinirlar = {}
        return plan, {"plan_id": plan_id, "kesin_mi": int(satir[2] == "kesin"),
                      "mudur_onay_no": satir[3] or "",
                      "kisisel_sinirlar": kisisel_sinirlar}


def son_plani_getir(vt: Veritabani, pencere_kodu: str) -> int | None:
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT id FROM v_plan WHERE pencere_kodu=? ORDER BY id DESC LIMIT 1",
            (pencere_kodu,)).fetchone()
        return int(satir[0]) if satir else None


def plan_kesinlestir(vt: Veritabani, plan_id: int, mudur_onay_no: str) -> None:
    """SP-05: plan müdür onayıyla kesinleşir ve oturumlar kilitlenir."""
    if not str(mudur_onay_no).strip():
        raise HizmetHatasi("Planı kesinleştirmek için müdür onay numarası zorunludur (SP-05).")
    plan, bilgi = plan_yukle(vt, plan_id)
    engeller = [i for i in plani_dogrula(vt, plan, bilgi["kisisel_sinirlar"]) if i.engel_mi]
    if engeller:
        raise HizmetHatasi(
            "Engelli plan kesinleştirilemez:\n" +
            "\n".join(f"• {i.kural_kimligi} {i.aciklama}" for i in engeller[:5]))
    with vt.baglan() as b:
        b.execute("UPDATE plan SET durum='kesin',mudur_onay_no=?,kesinlesti_at=? WHERE id=?",
                  (str(mudur_onay_no).strip(), simdi(), plan_id))
        b.execute("UPDATE oturum SET kilitli_mi=1 WHERE plan_id=?", (plan_id,))
        vt.denetim_yaz(b, "plan", plan_id, "kesinlestirildi")


def plan_sil(vt: Veritabani, plan_id: int) -> None:
    with vt.baglan() as b:
        durum = b.execute("SELECT durum FROM v_plan WHERE id=?", (plan_id,)).fetchone()
        if not durum:
            raise HizmetHatasi("Plan bulunamadı.")
        if durum[0] == "kesin":
            raise HizmetHatasi("Kesinleşmiş plan silinemez; kayıt denetim izindedir.")
        b.execute("UPDATE plan SET silindi_mi=1 WHERE id=?", (plan_id,))
        b.execute("UPDATE oturum SET silindi_mi=1 WHERE plan_id=?", (plan_id,))
        vt.denetim_yaz(b, "plan", plan_id, "silindi")


# ------------------------------------------------------ parametre serileştirme

def _parametreleri_yaz(p: PlanParametreleri) -> str:
    import json
    return json.dumps({
        "pencere_kodu": p.pencere_kodu,
        "hafta_sonu_kullan": p.hafta_sonu_kullan,
        "ogrenci_gunluk_sinav_siniri": p.ogrenci_gunluk_sinav_siniri,
        "iki_asamali_sayim": p.iki_asamali_sayim.value,
        "slot_saatleri": [s.strftime("%H:%M") for s in p.slot_saatleri],
        "oturum_suresi_dakika": p.oturum_suresi_dakika,
        "hedef_gun_sayisi": p.hedef_gun_sayisi,
    }, ensure_ascii=False, sort_keys=True)


def _parametreleri_oku(metin: str, pencere_kodu: str) -> PlanParametreleri:
    import json
    try:
        veri = json.loads(metin)
    except ValueError:
        return PlanParametreleri(pencere_kodu=pencere_kodu)
    return PlanParametreleri(
        pencere_kodu=veri.get("pencere_kodu", pencere_kodu),
        hafta_sonu_kullan=bool(veri.get("hafta_sonu_kullan", False)),
        ogrenci_gunluk_sinav_siniri=int(veri.get("ogrenci_gunluk_sinav_siniri", 2)),
        iki_asamali_sayim=IkiAsamaliSayim(veri.get("iki_asamali_sayim", "tek")),
        slot_saatleri=tuple(datetime.strptime(s, "%H:%M").time()
                            for s in veri.get("slot_saatleri", VARSAYILAN_SLOT_SAATLERI)),
        oturum_suresi_dakika=int(veri.get("oturum_suresi_dakika", 40)),
        hedef_gun_sayisi=veri.get("hedef_gun_sayisi"),
    )


def slot_saatlerini_coz(metin: str) -> tuple[time, ...]:
    """'08:00, 09:00' biçimindeki girdiyi saat demetine çevirir."""
    parcalar = [p.strip() for p in str(metin).replace(";", ",").split(",") if p.strip()]
    if not parcalar:
        raise HizmetHatasi("En az bir oturum saati girilmelidir.")
    try:
        saatler = tuple(datetime.strptime(p, "%H:%M").time() for p in parcalar)
    except ValueError as hata:
        raise HizmetHatasi(
            "Oturum saatleri SS:DD biçiminde ve virgülle ayrılmış olmalıdır.") from hata
    if len(set(saatler)) != len(saatler):
        raise HizmetHatasi("Oturum saatleri yinelenemez.")
    if any(a >= b for a, b in zip(saatler, saatler[1:])):
        raise HizmetHatasi("Oturum saatleri artan sırada girilmelidir.")
    return saatler


# ------------------------------------------------------- elle düzenleme

@dataclass
class TasimaSonucu:
    """Sürükle-bırak denemesinin sonucu."""

    uygulandi: bool
    ogrenci_engelleri: list[Ihlal] = field(default_factory=list)
    ogretmen_engelleri: list[Ihlal] = field(default_factory=list)
    salon_engelleri: list[Ihlal] = field(default_factory=list)
    diger_engeller: list[Ihlal] = field(default_factory=list)
    uyarilar: list[Ihlal] = field(default_factory=list)

    @property
    def engeller(self) -> list[Ihlal]:
        return (self.ogrenci_engelleri + self.ogretmen_engelleri
                + self.salon_engelleri + self.diger_engeller)

    def mesaj(self) -> str:
        bolumler = []
        for baslik, liste in (("Öğrenci çakışması", self.ogrenci_engelleri),
                              ("Öğretmen çakışması", self.ogretmen_engelleri),
                              ("Salon çakışması", self.salon_engelleri),
                              ("Kural ihlali", self.diger_engeller)):
            if liste:
                bolumler.append(baslik + ":\n" + "\n".join(f"  • {i.aciklama}" for i in liste))
        return "\n\n".join(bolumler)


def _engel_turu(ihlal: Ihlal) -> str:
    """İhlali kullanıcıya ayrı ayrı gösterebilmek için sınıflandırır."""
    metin = ihlal.aciklama
    if "aynı anda iki sınavda görevli" in metin or "sınav görevi verilemez" in metin:
        return "ogretmen"
    if "salonu" in metin and "ayrılmış" in metin:
        return "salon"
    if "aynı anda iki sınavda" in metin or ihlal.kural_kimligi == "SP-11":
        return "ogrenci"
    return "diger"


def oturum_tasi(vt: Veritabani, plan: Plan, anahtar: str, yeni_tarih: date, yeni_saat: time,
                kisisel_sinirlar: dict[str, int] | None = None) -> TasimaSonucu:
    """Oturumu yeni gün/saate taşır; yeni engel doğuruyorsa geri alır.

    Öğrenci, öğretmen ve salon çakışmaları ayrı ayrı raporlanır. Uyarı
    düzeyindeki ihlaller taşımayı engellemez, yalnız panelde görünür.
    """
    oturum = plan.oturum_bul(anahtar)
    if oturum is None:
        raise HizmetHatasi("Taşınacak oturum bulunamadı.")
    if oturum.kilitli_mi:
        raise HizmetHatasi("Kesinleşmiş veya kilitli oturum taşınamaz.")

    onceki = {(i.kural_kimligi, i.etkilenen_kayit)
              for i in plani_dogrula(vt, plan, kisisel_sinirlar) if i.engel_mi}
    eski_tarih, eski_saat = oturum.tarih, oturum.saat
    esler = [o for o in plan.oturumlar
             if oturum.birim_anahtari and o.birim_anahtari == oturum.birim_anahtari]
    # İki aşamalı dersin iki oturumu aynı günde kalmalıdır; yazılı taşınırsa
    # uygulama da aynı gün farkıyla birlikte taşınır.
    gun_farki = (yeni_tarih - eski_tarih)
    eski_durum = [(o, o.tarih, o.saat) for o in esler] or [(oturum, eski_tarih, eski_saat)]
    oturum.tarih, oturum.saat = yeni_tarih, yeni_saat
    for es in esler:
        if es is not oturum:
            es.tarih = es.tarih + gun_farki

    sonrasi = plani_dogrula(vt, plan, kisisel_sinirlar)
    yeni_engeller = [i for i in sonrasi
                     if i.engel_mi and (i.kural_kimligi, i.etkilenen_kayit) not in onceki]
    if yeni_engeller:
        for nesne, tarih, saat in eski_durum:
            nesne.tarih, nesne.saat = tarih, saat
        gruplar: dict[str, list[Ihlal]] = {"ogrenci": [], "ogretmen": [], "salon": [], "diger": []}
        for ihlal in yeni_engeller:
            gruplar[_engel_turu(ihlal)].append(ihlal)
        return TasimaSonucu(False, gruplar["ogrenci"], gruplar["ogretmen"],
                            gruplar["salon"], gruplar["diger"])
    return TasimaSonucu(True, uyarilar=[i for i in sonrasi if not i.engel_mi])


def plan_anlik_goruntusu(plan: Plan) -> list[tuple[str, date, time, tuple[int, ...]]]:
    """Geri al yığını için planın değişebilen durumunu kopyalar."""
    return [(o.anahtar, o.tarih, o.saat, o.salon_kimlikleri) for o in plan.oturumlar]


def plani_geri_yukle(plan: Plan, goruntu: list[tuple[str, date, time, tuple[int, ...]]]) -> None:
    durumlar = {anahtar: (tarih, saat, salonlar) for anahtar, tarih, saat, salonlar in goruntu}
    for oturum in plan.oturumlar:
        if oturum.anahtar in durumlar:
            oturum.tarih, oturum.saat, oturum.salon_kimlikleri = durumlar[oturum.anahtar]
