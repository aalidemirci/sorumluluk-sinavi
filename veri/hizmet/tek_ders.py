"""Tek ders sınavı (OKY md.58/6): adaylar ve seçimler.
"""

from __future__ import annotations

from cekirdek.modeller import SorumlulukKaydi
from ..veritabani import Veritabani, simdi

from .ortak import HizmetHatasi, ogretim_yili
from .plan_kayitlari import son_plani_getir


# ============================================ tek ders sınavı (OKY md.58/6)

def tek_ders_adaylari(vt: Veritabani, pencere_kodu: str) -> list[dict]:
    """Tek ders sınavına alınabilecek öğrenciler ve dersleri.

    OKY md.58/6: sorumluluk sınavı sonunda tek dersten başarısızlığı kalan son
    sınıf öğrencisi. Program sınav sonucunu bilmez (sonuç e-Okul'dadır); bu
    yüzden o dönemin olağan planındaki 12. sınıf öğrencileri ve plandaki
    dersleri listelenir, kullanıcı başarısız kalan tek dersi seçer.
    """
    plan_id = son_plani_getir(vt, pencere_kodu)
    if plan_id is None:
        return []
    yil = ogretim_yili(vt)
    with vt.baglan() as b:
        satirlar = b.execute("""
            SELECT DISTINCT og.id, og.okul_no, og.ad_soyad, og.sube, s.id, d.ad, s.duzey,
                   (SELECT t.sorumluluk_kaydi_id FROM v_tek_ders_secimi t
                     WHERE t.ogrenci_id = og.id AND t.ogretim_yili = ? AND t.pencere_kodu = ?)
            FROM v_oturum_ogrenci oo
            JOIN v_oturum o ON o.id = oo.oturum_id AND o.plan_id = ?
            JOIN v_ogrenci og ON og.id = oo.ogrenci_id AND og.sinif_duzeyi = 12
            JOIN v_sorumluluk_kaydi s ON s.ogrenci_id = og.id AND s.ders_id = o.ders_id
                 AND s.durum = 'aktif'
                 AND (',' || o.duzey_kumesi || ',') LIKE ('%,' || s.duzey || ',%')
            JOIN v_ders d ON d.id = s.ders_id
            ORDER BY og.sube, og.ad_soyad, d.ad""", (yil, pencere_kodu, plan_id)).fetchall()
    return [{"ogrenci_id": r[0], "okul_no": r[1], "ad_soyad": r[2], "sube": r[3],
             "sorumluluk_kaydi_id": r[4], "ders": r[5], "duzey": r[6],
             "secili_mi": r[7] == r[4]} for r in satirlar]


def tek_ders_sec(vt: Veritabani, pencere_kodu: str, ogrenci_id: int,
                 sorumluluk_kaydi_id: int | None) -> None:
    """Öğrencinin tek ders sınavına gireceği dersi seçer; None seçimi kaldırır.

    Öğrenci başına tek ders seçilebilir: hüküm "tek dersten başarısızlığı
    bulunan" öğrenci içindir.
    """
    yil = ogretim_yili(vt)
    with vt.baglan() as b:
        b.execute("UPDATE tek_ders_secimi SET silindi_mi=1 WHERE ogretim_yili=? AND"
                  " pencere_kodu=? AND ogrenci_id=? AND silindi_mi=0",
                  (yil, pencere_kodu, ogrenci_id))
        if sorumluluk_kaydi_id is not None:
            if not b.execute("SELECT 1 FROM v_sorumluluk_kaydi WHERE id=? AND ogrenci_id=?",
                             (sorumluluk_kaydi_id, ogrenci_id)).fetchone():
                raise HizmetHatasi("Seçilen ders bu öğrencinin sorumluluk kaydı değil.")
            b.execute("INSERT INTO tek_ders_secimi(ogretim_yili,pencere_kodu,ogrenci_id,"
                      "sorumluluk_kaydi_id,olusturuldu_at) VALUES(?,?,?,?,?)",
                      (yil, pencere_kodu, ogrenci_id, sorumluluk_kaydi_id, simdi()))
        vt.denetim_yaz(b, "tek_ders_secimi", ogrenci_id,
                       "secildi" if sorumluluk_kaydi_id is not None else "kaldirildi",
                       pencere_kodu)


def tek_ders_kayitlari(vt: Veritabani, pencere_kodu: str) -> list[SorumlulukKaydi]:
    with vt.baglan() as b:
        return [SorumlulukKaydi(r[0], r[1], r[2], r[3], r[4], r[5]) for r in b.execute("""
            SELECT og.okul_no, og.ad_soyad, og.sube, s.duzey, d.ad, s.kaynak
            FROM v_tek_ders_secimi t
            JOIN v_ogrenci og ON og.id = t.ogrenci_id
            JOIN v_sorumluluk_kaydi s ON s.id = t.sorumluluk_kaydi_id
            JOIN v_ders d ON d.id = s.ders_id
            WHERE t.ogretim_yili = ? AND t.pencere_kodu = ?
            ORDER BY d.ad, s.duzey, og.okul_no""", (ogretim_yili(vt), pencere_kodu))]
