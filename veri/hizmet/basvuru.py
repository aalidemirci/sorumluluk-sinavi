"""Başvuru kapısı (OKY md.58/2-d): duyuru, işaretler, başvurular ve plan
dışı bırakılanlar.
"""

from __future__ import annotations

from datetime import date

from cekirdek.takvim import is_gunu_ekle, is_gunu_farki, pencere_adi
from ..veritabani import Veritabani, simdi

from .ortak import HizmetHatasi, ayarlari_getir, ogretim_yili, pencereleri_getir, tatilleri_getir
from .plan_kayitlari import son_plani_getir


# ================================================= başvuru kapısı (md.58/2-d)

# Okulun duyuruyu pencereden kaç gün önce yayımlaması gerektiği. Mevzuatta
# böyle bir süre YOKTUR; bu okul uygulamasıdır ve uyarı üretir, engellemez.
DUYURU_ONCE_GUN = 15

# Mevzuattaki tek bağlayıcı süre: başvuru, sınav tarihinden en az bu kadar
# iş günü önce yapılmış olmalıdır (OKY md.58/2-d).
BASVURU_IS_GUNU = 5

# Liste tazeliği hatırlatması yalnız bu pencerelerde anlamlıdır: Eylül planı
# içe aktarmanın hemen ardından yapılır, Şubat ve Haziran aylar sonra gelir.
LISTE_HATIRLATMA_PENCERELERI = frozenset({"P2", "P3"})


def basvuru_kapsamindaki_ogrenciler(vt: Veritabani) -> dict[str, tuple[int, str]]:
    """Bayraklı öğrenciler: anahtar -> (kimlik, grup adı)."""
    with vt.baglan() as b:
        satirlar = b.execute(
            "SELECT id,okul_no,sube,mezun_olamayan_mi,devamsizlik_tebligati_mi"
            " FROM v_ogrenci WHERE mezun_olamayan_mi=1 OR devamsizlik_tebligati_mi=1").fetchall()
    return {f"{r[1]}|{r[2]}": (r[0], _grup_adi(r[3], r[4])) for r in satirlar}


def _grup_adi(mezun_olamayan: int, devamsiz: int) -> str:
    if mezun_olamayan and devamsiz:
        return "Beklemeli + devamsızlık tebligatı"
    if mezun_olamayan:
        return "Mezun olamayan 12. sınıf"
    return "Devamsızlık tebligatı yapılan"


def gecerli_basvurular(vt: Veritabani, pencere_kodu: str) -> frozenset[str]:
    """Plana alınabilecek bayraklı öğrencilerin anahtarları.

    Geç başvuru müdür onayı taşımıyorsa geçerli sayılmaz.
    """
    ogretim_yili = ayarlari_getir(vt).get("ogretim_yili", "")
    with vt.baglan() as b:
        return frozenset(f"{r[0]}|{r[1]}" for r in b.execute("""
            SELECT o.okul_no,o.sube FROM v_basvuru bv
            JOIN v_ogrenci o ON o.id = bv.ogrenci_id
            WHERE bv.ogretim_yili=? AND bv.pencere_kodu=? AND bv.durum='basvurdu'
              AND (bv.gec_basvuru_mu=0 OR COALESCE(TRIM(bv.mudur_onay_no),'') <> '')""",
            (ogretim_yili, pencere_kodu)))


def ogrenci_etiketleri(vt: Veritabani) -> dict[str, str]:
    """Öğrenci anahtarı -> ihlal metinlerinde görünecek okunur etiket."""
    with vt.baglan() as b:
        return {f"{r[0]}|{r[1]}": f"{r[2]} (No: {r[0]}, {r[1]})" for r in b.execute(
            "SELECT okul_no,sube,ad_soyad FROM v_ogrenci")}


def duyuru_kaydet(vt: Veritabani, pencere_kodu: str, duyuru_tarihi: date,
                  basvuru_son_gunu: date, belge_referansi: str,
                  yayim_yeri: str = "") -> list[str]:
    """Pencere başvuru duyurusunu kaydeder; okul uygulaması uyarılarını döndürür.

    Mevzuat süreyi sınav tarihine bağlar. Başvuru tek bir son güne bağlandığında
    şart, pencerenin EN ERKEN günü esas alınarak sağlanır: son güne kadar
    başvuran herkes kendi sınav tarihinden en az 5 iş günü önce başvurmuş olur.
    """
    if not belge_referansi.strip():
        raise HizmetHatasi("Duyurunun belge referansı zorunludur; ilan edildiğinin ispatıdır.")
    if duyuru_tarihi > basvuru_son_gunu:
        raise HizmetHatasi("Duyuru tarihi başvuru son gününden sonra olamaz.")
    pencere_bas = pencereleri_getir(vt)[pencere_kodu][0]
    tatiller = tatilleri_getir(vt)
    if is_gunu_farki(basvuru_son_gunu, pencere_bas, tatiller) < BASVURU_IS_GUNU:
        en_gec = is_gunu_ekle(pencere_bas, -BASVURU_IS_GUNU, tatiller)
        raise HizmetHatasi(
            f"Başvuru son günü en geç {en_gec.strftime('%d.%m.%Y')} olabilir: "
            f"{pencere_adi(pencere_kodu)} penceresi {pencere_bas.strftime('%d.%m.%Y')} "
            f"tarihinde başlıyor ve mevzuat 5 iş günü ister (OKY md.58/2-d).")
    uyarilar: list[str] = []
    onceden = (pencere_bas - duyuru_tarihi).days
    if onceden < DUYURU_ONCE_GUN:
        uyarilar.append(
            f"Duyuru pencere başlangıcından {onceden} gün önce yayımlanmış. Okul uygulaması "
            f"{DUYURU_ONCE_GUN} gündür; mevzuatta duyuru süresi yoktur.")
    ogretim_yili = ayarlari_getir(vt).get("ogretim_yili", "")
    with vt.baglan() as b:
        b.execute("""
            INSERT INTO pencere_duyurusu(ogretim_yili,pencere_kodu,duyuru_tarihi,
                basvuru_son_gunu,duyuru_referansi,yayim_yeri,olusturuldu_at)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(ogretim_yili,pencere_kodu) DO UPDATE SET
                duyuru_tarihi=excluded.duyuru_tarihi,
                basvuru_son_gunu=excluded.basvuru_son_gunu,
                duyuru_referansi=excluded.duyuru_referansi,
                yayim_yeri=excluded.yayim_yeri, silindi_mi=0""",
            (ogretim_yili, pencere_kodu, duyuru_tarihi.isoformat(),
             basvuru_son_gunu.isoformat(), belge_referansi.strip(), yayim_yeri.strip(), simdi()))
        vt.denetim_yaz(b, "pencere_duyurusu", 0, "duyuru_kaydedildi",
                       f"{pencere_kodu} son gün {basvuru_son_gunu.isoformat()}")
    return uyarilar


def duyuru_getir(vt: Veritabani, pencere_kodu: str) -> dict | None:
    ogretim_yili = ayarlari_getir(vt).get("ogretim_yili", "")
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT duyuru_tarihi,basvuru_son_gunu,duyuru_referansi,yayim_yeri"
            " FROM v_pencere_duyurusu WHERE ogretim_yili=? AND pencere_kodu=?",
            (ogretim_yili, pencere_kodu)).fetchone()
    if not satir:
        return None
    return {"duyuru_tarihi": date.fromisoformat(satir[0]),
            "basvuru_son_gunu": date.fromisoformat(satir[1]),
            "belge_referansi": satir[2], "yayim_yeri": satir[3]}


def ogrenci_bayrak_guncelle(vt: Veritabani, ogrenci_id: int, mezun_olamayan: bool,
                            devamsizlik_tebligati: bool) -> None:
    """md.58/2-d'deki iki grubu işaretler.

    OOK12001R010 bu ayrımı taşımadığı için işaretleme elle yapılır. Bayrak
    öğrenciye aittir ve öğretim yılı boyunca kalır; başvuru ise pencere başına
    yenilenir.
    """
    yil = ogretim_yili(vt) if (mezun_olamayan or devamsizlik_tebligati) else ""
    with vt.baglan() as b:
        if not b.execute("SELECT 1 FROM v_ogrenci WHERE id=?", (ogrenci_id,)).fetchone():
            raise HizmetHatasi("Öğrenci bulunamadı.")
        b.execute("UPDATE ogrenci SET mezun_olamayan_mi=?,devamsizlik_tebligati_mi=?,"
                  "isaret_ogretim_yili=? WHERE id=?",
                  (int(bool(mezun_olamayan)), int(bool(devamsizlik_tebligati)), yil,
                   ogrenci_id))
        vt.denetim_yaz(b, "ogrenci", ogrenci_id, "basvuru_bayragi_guncellendi")


def eski_yildan_isaretler(vt: Veritabani) -> list[dict]:
    """Önceki öğretim yılında konmuş md.58/2-d işaretleri.

    Devamsızlık tebligatı o yılın durumudur; eski yılın işareti sessizce
    taşınırsa öğrenci yeni yılda da başvurusuz plan dışı kalır. İşaret
    silinmez (mezun olamayan öğrenci hâlâ mezun olamamış olabilir), gözden
    geçirilmesi istenir: işaretin yeniden kaydedilmesi yılını günceller.
    """
    yil = ogretim_yili(vt)
    with vt.baglan() as b:
        return [{"ogrenci_id": r[0], "okul_no": r[1], "ad_soyad": r[2], "sube": r[3],
                 "isaret_yili": r[4] or "bilinmiyor"}
                for r in b.execute(
                    "SELECT id,okul_no,ad_soyad,sube,isaret_ogretim_yili FROM v_ogrenci"
                    " WHERE (mezun_olamayan_mi=1 OR devamsizlik_tebligati_mi=1)"
                    " AND isaret_ogretim_yili<>? ORDER BY sube,ad_soyad", (yil,))]


def isaret_tazeligi_uyarisi(vt: Veritabani) -> str:
    eskiler = eski_yildan_isaretler(vt)
    if not eskiler:
        return ""
    return (f"{len(eskiler)} öğrencinin beklemeli/devamsız işareti önceki öğretim yılından "
            "kalma. Bu öğrenciler başvuru yapmadıkça plana alınmaz (OKY md.58/2-d). "
            "Başvuru adımında işaretleri gözden geçirin; doğru olanı yeniden kaydetmek "
            "yılını günceller, yanlış olanı kaldırın.")


def basvuru_kaydet(vt: Veritabani, ogrenci_id: int, pencere_kodu: str, durum: str,
                   basvuru_tarihi: date | None = None, belge_referansi: str = "",
                   mudur_onay_no: str = "") -> None:
    """Bayraklı öğrencinin pencere başvurusunu kaydeder (OKY md.58/2-d)."""
    if durum not in {"basvurdu", "basvurmadi"}:
        raise HizmetHatasi("Başvuru durumu 'basvurdu' ya da 'basvurmadi' olmalıdır.")
    ogretim_yili = ayarlari_getir(vt).get("ogretim_yili", "")
    duyuru = duyuru_getir(vt, pencere_kodu)
    if not duyuru:
        raise HizmetHatasi(
            f"{pencere_adi(pencere_kodu)} penceresi için başvuru duyurusu kaydedilmeden "
            "başvuru alınamaz; duyuru kapının hukuki dayanağıdır.")
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT mezun_olamayan_mi,devamsizlik_tebligati_mi FROM v_ogrenci WHERE id=?",
            (ogrenci_id,)).fetchone()
    if not satir:
        raise HizmetHatasi("Öğrenci bulunamadı.")
    if not (satir[0] or satir[1]):
        raise HizmetHatasi(
            "Başvuru yalnız mezun olamayan 12. sınıf ya da devamsızlık tebligatı yapılmış "
            "öğrenci için kaydedilir (OKY md.58/2-d). Diğer öğrenciler başvurusuz plana girer.")
    gec = 0
    if durum == "basvurdu":
        if basvuru_tarihi is None:
            raise HizmetHatasi("Başvuru tarihi zorunludur.")
        if not belge_referansi.strip():
            raise HizmetHatasi("Başvurunun belge referansı (dilekçe tarih/sayı) zorunludur.")
        gec = int(basvuru_tarihi > duyuru["basvuru_son_gunu"])
        if gec and not mudur_onay_no.strip():
            raise HizmetHatasi(
                "Son günden sonra alınan başvurunun plana eklenmesi müdür onayına bağlıdır. "
                "Mevzuat 'bildirmeleri hâlinde plana dâhil edilir' der; okulun ilan ettiği "
                "son gün iç düzenlemedir ve bu hakkı ortadan kaldırmaz (OKY md.58/2-d).")
        if gec:
            _gec_basvuru_suresini_denetle(vt, ogrenci_id, pencere_kodu, basvuru_tarihi)
    with vt.baglan() as b:
        b.execute("""
            INSERT INTO basvuru(ogrenci_id,ogretim_yili,pencere_kodu,durum,basvuru_tarihi,
                belge_referansi,gec_basvuru_mu,mudur_onay_no,olusturuldu_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(ogrenci_id,ogretim_yili,pencere_kodu) DO UPDATE SET
                durum=excluded.durum, basvuru_tarihi=excluded.basvuru_tarihi,
                belge_referansi=excluded.belge_referansi,
                gec_basvuru_mu=excluded.gec_basvuru_mu,
                mudur_onay_no=excluded.mudur_onay_no, silindi_mi=0""",
            (ogrenci_id, ogretim_yili, pencere_kodu, durum,
             basvuru_tarihi.isoformat() if basvuru_tarihi else None,
             belge_referansi.strip(), gec, mudur_onay_no.strip() or None, simdi()))
        vt.denetim_yaz(b, "basvuru", ogrenci_id, f"basvuru_{durum}", pencere_kodu)


def _gec_basvuru_suresini_denetle(vt: Veritabani, ogrenci_id: int, pencere_kodu: str,
                                  basvuru_tarihi: date) -> None:
    """Geç başvuruda 5 iş günü şartı fiilî sınav tarihine göre denetlenir."""
    plan_id = son_plani_getir(vt, pencere_kodu)
    with vt.baglan() as b:
        satir = b.execute("""
            SELECT MIN(o.tarih) FROM v_oturum o
            JOIN v_sorumluluk_kaydi s ON s.ders_id = o.ders_id
                 AND s.ogrenci_id = ? AND s.durum = 'aktif'
            WHERE o.plan_id = ?""",
            (ogrenci_id, plan_id or -1)).fetchone()
    if not satir or not satir[0]:
        return
    sinav = date.fromisoformat(satir[0])
    if is_gunu_farki(basvuru_tarihi, sinav, tatilleri_getir(vt)) < BASVURU_IS_GUNU:
        raise HizmetHatasi(
            f"Geç başvuru, {sinav.strftime('%d.%m.%Y')} tarihli sınavdan en az "
            f"{BASVURU_IS_GUNU} iş günü önce yapılmış olmalıdır (OKY md.58/2-d).")


def basvuru_tablosu(vt: Veritabani, pencere_kodu: str) -> list[dict]:
    """Aktif sorumluluğu olan öğrenciler, bayrakları ve o pencerede durumları."""
    ogretim_yili = ayarlari_getir(vt).get("ogretim_yili", "")
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT o.id,o.okul_no,o.ad_soyad,o.sube,o.mezun_olamayan_mi,
                   o.devamsizlik_tebligati_mi, COUNT(DISTINCT s.id) AS ders_sayisi,
                   bv.durum, bv.basvuru_tarihi, bv.belge_referansi,
                   bv.gec_basvuru_mu, bv.mudur_onay_no, o.isaret_ogretim_yili
            FROM v_ogrenci o
            JOIN v_sorumluluk_kaydi s ON s.ogrenci_id = o.id AND s.durum = 'aktif'
            LEFT JOIN v_basvuru bv ON bv.ogrenci_id = o.id
                 AND bv.ogretim_yili = ? AND bv.pencere_kodu = ?
            GROUP BY o.id
            ORDER BY (o.mezun_olamayan_mi = 0 AND o.devamsizlik_tebligati_mi = 0),
                     o.sube, o.ad_soyad""", (ogretim_yili, pencere_kodu)).fetchall()
    sonuc = []
    for r in satirlar:
        bayrakli = bool(r[4] or r[5])
        eski = bayrakli and (r[12] or "") != ogretim_yili
        grup = _grup_adi(r[4], r[5]) if bayrakli else "—"
        sonuc.append({
            "ogrenci_id": r[0], "okul_no": r[1], "ad_soyad": r[2], "sube": r[3],
            "mezun_olamayan_mi": bool(r[4]), "devamsizlik_tebligati_mi": bool(r[5]),
            "bayrakli_mi": bayrakli,
            "isaret_yili": r[12] or "", "eski_isaret_mi": eski,
            # Tutanağa giden "grup" sade kalır; yıl uyarısı yalnız ekrandadır.
            "grup": grup,
            "grup_ekran": grup + (f" — işaret {r[12] or 'önceki yıl'}, gözden geçirin"
                                  if eski else ""),
            "ders_sayisi": r[6],
            "basvuru_durumu": r[7],
            "basvuru_tarihi": date.fromisoformat(r[8]) if r[8] else None,
            "belge_referansi": r[9] or "",
            "gec_basvuru_mu": bool(r[10]),
            "mudur_onay_no": r[11] or "",
            "ozet": _basvuru_ozeti(bayrakli, r[7], r[10], r[11]),
        })
    return sonuc


def _basvuru_ozeti(bayrakli: bool, durum: str | None, gec: int | None,
                   onay: str | None) -> str:
    if not bayrakli:
        return "Başvuru aranmaz"
    if durum == "basvurdu" and gec:
        return f"Başvurdu (geç, onay: {onay or 'YOK'})"
    if durum == "basvurdu":
        return "Başvurdu"
    if durum == "basvurmadi":
        return "Başvurmadı — plan dışı"
    return "KARAR BEKLİYOR"


def basvuru_bekleyenler(vt: Veritabani, pencere_kodu: str) -> list[dict]:
    """Bayraklı olup o pencerede henüz karar girilmemiş öğrenciler."""
    return [s for s in basvuru_tablosu(vt, pencere_kodu)
            if s["bayrakli_mi"] and s["basvuru_durumu"] is None]


def plan_disi_birakilanlar(vt: Veritabani, pencere_kodu: str) -> list[dict]:
    """Tutanağa girecek satırlar: bayraklı olup plana alınmayanlar."""
    return [s for s in basvuru_tablosu(vt, pencere_kodu)
            if s["bayrakli_mi"] and s["ozet"] in {"Başvurmadı — plan dışı", "KARAR BEKLİYOR"}]


def liste_tazeligi_uyarisi(vt: Veritabani, pencere_kodu: str) -> str:
    """SP-15: Şubat ve Haziran planlarında güncel liste hatırlatması.

    Eylül planı içe aktarmanın hemen ardından yapılır; hatırlatma gerekmez.
    """
    if pencere_kodu not in LISTE_HATIRLATMA_PENCERELERI:
        return ""
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT MAX(onaylandi_at) FROM ice_aktarim"
            " WHERE tur='sorumluluk' AND durum='onaylandi'").fetchone()
    if not satir or not satir[0]:
        return ("Onaylanmış bir sorumluluk listesi aktarımı yok. "
                "Plan üretmeden önce OOK12001R010 raporunu içe aktarın (SP-15).")
    son = date.fromisoformat(satir[0][:10])
    pencere_bas = pencereleri_getir(vt)[pencere_kodu][0]
    if (pencere_bas - son).days <= DUYURU_ONCE_GUN:
        return ""
    return (f"{pencere_adi(pencere_kodu)} planı üretiliyor; son onaylı liste aktarımı "
            f"{son.strftime('%d.%m.%Y')} tarihli. Nakil giden, açık öğretime geçen ya da "
            "sorumluluğu kalkan öğrenciler ancak yeniden aktarılan listeyle plandan düşer. "
            "OOK12001R010 raporunu yeniden indirip aktarmanız önerilir (SP-15).")
