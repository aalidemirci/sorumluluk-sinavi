"""Sorumluluk aktarımı (OOK12001R010), sorumluluk kayıtları ve ders ayarları.

Başvuru kapısı tek noktada, `sorumluluk_kayitlari` içinde uygulanır
(kararlar/0006).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from cekirdek.metin import esitle
from cekirdek.modeller import DersAyari, SorumlulukKaydi
from ..rapor_okuma import sorumluluk_raporu_oku
from ..veritabani import Veritabani, simdi

from .ortak import AktarimOzeti, HizmetHatasi
from .basvuru import basvuru_kapsamindaki_ogrenciler, gecerli_basvurular


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
        if rapor.okunmayan_basliklar:
            # SG-05: nakil/geçiş kaynağının raporda bir sütunu olup olmadığı
            # gerçek bir dosyada henüz görülmedi; görülene kadar kullanıcıya
            # okunmayan başlıklar gösterilir. Yalnız başlık adı, kişisel veri değil.
            ozet.uyarilar.append(
                "Raporda programın okumadığı sütunlar var: "
                + ", ".join(rapor.okunmayan_basliklar)
                + ". Biri nakil ya da geçiş kaynağını gösteriyorsa geliştiriciye yalnız "
                "sütun adını bildirin; program şimdilik bütün kayıtları başarısızlık "
                "kaynaklı sayar (SG-05).")
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
            # Öğrenciyi tanımlayan okul numarasıdır; şube bir özniteliktir.
            # Şube değişiminde yeni satır açılırsa md.58/2-d bayrakları
            # varsayılan 0 ile başlar ve başvuru kapısı sessizce devre dışı
            # kalır: eylülde işaretlenen öğrenci şubatta işaretsiz görünür.
            # Bu yüzden önce okul numarasıyla aranır, bulunursa güncellenir.
            mevcut = b.execute("SELECT id FROM ogrenci WHERE okul_no=?", (okul_no,)).fetchone()
            if mevcut:
                b.execute(
                    "UPDATE ogrenci SET ad_soyad=?,sube=?,sinif_duzeyi=?,silindi_mi=0"
                    " WHERE id=?",
                    (ad_soyad, sube, int(str(sube).split("/", 1)[0]), mevcut[0]))
            else:
                b.execute(
                    "INSERT INTO ogrenci(okul_no,ad_soyad,sube,sinif_duzeyi) VALUES(?,?,?,?)"
                    " ON CONFLICT(okul_no,sube) DO UPDATE SET ad_soyad=excluded.ad_soyad,"
                    " silindi_mi=0",
                    (okul_no, ad_soyad, sube, int(str(sube).split("/", 1)[0])))
            b.execute(
                "INSERT INTO ders(ad,ad_anahtari) VALUES(?,?)"
                " ON CONFLICT(ad_anahtari) DO UPDATE SET silindi_mi=0",
                (ders_adi, esitle(ders_adi)))
            ogrenci_id = b.execute("SELECT id FROM ogrenci WHERE okul_no=?",
                                   (okul_no,)).fetchone()[0]
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


def sorumluluk_kayitlari(vt: Veritabani, pencere_kodu: str | None = None) -> list[SorumlulukKaydi]:
    """Plana girecek sorumluluk kayıtları.

    `pencere_kodu` verilirse OKY md.58/2-d kapısı uygulanır: mezun olamayan
    12. sınıf ve devamsızlık tebligatı yapılmış öğrenciler ancak o pencerede
    geçerli başvuruları varsa listeye girer. Kapı burada, tek noktada
    uygulanır; planlayıcı zincirinin tamamı buradan beslenir.
    """
    with vt.baglan() as b:
        kayitlar = [SorumlulukKaydi(r[0], r[1], r[2], r[3], r[4], r[5]) for r in b.execute("""
            SELECT o.okul_no,o.ad_soyad,o.sube,s.duzey,d.ad,s.kaynak
            FROM v_sorumluluk_kaydi s
            JOIN v_ogrenci o ON o.id=s.ogrenci_id
            JOIN v_ders d ON d.id=s.ders_id
            WHERE s.durum='aktif' ORDER BY d.ad,s.duzey,o.okul_no""")]
    if pencere_kodu is None:
        return kayitlar
    kapsam = set(basvuru_kapsamindaki_ogrenciler(vt))
    if not kapsam:
        return kayitlar
    gecerli = gecerli_basvurular(vt, pencere_kodu)
    return [k for k in kayitlar
            if k.ogrenci_anahtari not in kapsam or k.ogrenci_anahtari in gecerli]


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


# e-Okul ders adlarında geçen yabancı dil adları. Eski öneri yalnız İngilizceyi
# tanıyordu; Almanca ve diğer ikinci yabancı diller tek aşamalı kalıyordu.
_YABANCI_DILLER = ("yabancı dil", "ingilizce", "almanca", "fransızca", "ispanyolca",
                   "italyanca", "rusça", "arapça", "çince", "japonca", "korece", "farsça")


def yabanci_dil_mi(ders_adi: str) -> bool:
    ad = esitle(ders_adi)
    return any(dil in ad for dil in _YABANCI_DILLER)


def iki_asamali_onerisi(ders_adi: str) -> bool:
    """OKY md.58/2-e için ad temelli öneri; kullanıcı onaylar ya da değiştirir."""
    return yabanci_dil_mi(ders_adi) or esitle(ders_adi) == "türk dili ve edebiyatı"
