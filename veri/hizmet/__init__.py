"""Servis katmanı — arayüz ile çekirdek/veritabanı arasındaki tek geçit.

Arayüz SQL yazmaz, çekirdek de veritabanı bilmez. Kural denetimi burada
tekrarlanmaz; `cekirdek.kurallar.dogrula_plan` çağrılır.

Katman 03.10.2026'ya kadar tek dosyaydı (~2 400 satır); konulara göre
modüllere bölündü. Dışarıdan erişim değişmedi: `from veri import hizmet`,
`hizmet.plan_hazirla(...)` ve `from veri.hizmet import HizmetHatasi` bu
cepheden geçer. Modüller katmanlıdır, aralarında döngü yoktur (parantez
içinde dayandıkları):

    ortak
    plan_kayitlari     (ortak)
    personel           (ortak)
    basvuru            (ortak, plan_kayitlari)
    tek_ders           (ortak, plan_kayitlari)
    gorev              (personel, plan_kayitlari)
    sorumluluk         (ortak, basvuru)
    personel_yonetimi  (ortak, plan_kayitlari, gorev)
    evrak_sorgulari    (ortak, gorev)
    plan               (yukarıdakilerin çoğu)
    duzenleme          (ortak, personel, gorev, plan)

Bir adı bu cephe üzerinde değiştirmek (ör. testte `monkeypatch.setattr(
hizmet, "varsayilan_pencere", …)`) yalnız cephe üzerinden yapılan çağrıları
etkiler; modüllerin kendi aralarındaki çağrılar özgün işlevi kullanır.
"""

from __future__ import annotations

from .ortak import (
    AktarimOzeti, AYAR_ZORUNLU, DONEM_TARIHLERI, HizmetHatasi, VARSAYILAN_SLOT_SAATLERI,
    ayarlari_getir, ayarlari_kaydet, ogretim_yili, pencereleri_getir, salon_ekle, salon_sil,
    salonlari_getir, tatil_ekle, tatil_listesi, tatil_sil, tatilleri_getir, varsayilan_pencere,
    yedek_al,
)
from .plan_kayitlari import etkin_planlar, kesin_plan, son_plani_getir
from .personel import (
    HAFTA_GUNLERI, brans_havuzu_ekle, brans_havuzu_listele, musaitlik_ekle, musaitlik_listesi,
    musaitlik_sil, musaitsizlikleri_getir, personel_onayla, personel_onizle,
    personelleri_getir,
)
from .gorev import (
    gorev_havuzu_ozeti, onceki_gorev_kayitlari, onceki_gorev_sayaclari, taslak_pencereler,
)
from .personel_yonetimi import (
    personel_ayrintili_liste, personel_durumu_degistir, personel_ekle, personel_sil,
)
from .basvuru import (
    BASVURU_IS_GUNU, DUYURU_ONCE_GUN, LISTE_HATIRLATMA_PENCERELERI, basvuru_bekleyenler,
    basvuru_kapsamindaki_ogrenciler, basvuru_kaydet, basvuru_tablosu, duyuru_getir,
    duyuru_kaydet, eski_yildan_isaretler, gecerli_basvurular, isaret_tazeligi_uyarisi,
    liste_tazeligi_uyarisi, numara_listesini_coz, ogrenci_bayrak_guncelle,
    ogrenci_bayraklarini_toplu_guncelle, ogrenci_etiketleri, plan_disi_birakilanlar,
    sube_duzeyi,
)
from .tek_ders import tek_ders_adaylari, tek_ders_kayitlari, tek_ders_sec
from .sorumluluk import (
    ders_ayarlari, ders_brans_esle, ders_esdeger_branslari, ders_ozellik_guncelle,
    dersleri_listele, iki_asamali_onerisi, sorumluluk_kayitlari, sorumluluk_onayla,
    sorumluluk_onizle, yabanci_dil_mi,
)
from .plan import (
    PlanBaglami, brans_eslemelerini_denetle, pencere_araligi, plan_baglami, plan_hazirla,
    plan_kaydet, plan_kesinlestir, plan_sil, plan_yukle, plani_dogrula, sinav_birimleri,
    slot_saatlerini_coz, yuk_ozetini_getir,
)
from .duzenleme import (
    ELLE_HAFTA_SONU_GEREKCESI, TasimaSonucu, gorevli_adaylari, gorevli_degisiklikleri,
    gorevli_degistir, hafta_sonu_gerekcesi_gerekir_mi, kesin_plan_gorevli_degistir,
    oturum_tasi, plan_anlik_goruntusu, plani_geri_yukle,
)
from .evrak_sorgulari import (
    BEKLENEN_EVRAK, EVRAK_ADLARI, EVRAK_TURLERI, OGRENCI_GOSTERIM_ADLARI, OGRENCI_GOSTERIMI,
    TESLIM_SURESI_IS_GUNU, TeslimSatiri, evrak_gecmisi, evrak_surumu_kaydet, gorev_sayaclari,
    gorevli_listesi, ilan_ogrenci_cizelgesi, ilan_takvimi, kisi_bazli_gorevler,
    ogrenci_etiketi_uret, onayli_belge_degisiklikleri, oturum_ogrencileri,
    plan_oturumlari, teslim_cizelgesi, teslim_geri_al, teslim_kaydet, teslim_ozeti,
)

# Cephe: yeniden verilen adlar (statik denetim bunları kullanılmış sayar).
__all__ = [
    "AktarimOzeti", "AYAR_ZORUNLU", "DONEM_TARIHLERI", "HizmetHatasi",
    "VARSAYILAN_SLOT_SAATLERI", "ayarlari_getir", "ayarlari_kaydet", "ogretim_yili",
    "pencereleri_getir", "salon_ekle", "salon_sil", "salonlari_getir", "tatil_ekle",
    "tatil_listesi", "tatil_sil", "tatilleri_getir", "varsayilan_pencere", "yedek_al",
    "etkin_planlar", "kesin_plan", "son_plani_getir", "HAFTA_GUNLERI", "brans_havuzu_ekle",
    "brans_havuzu_listele", "musaitlik_ekle", "musaitlik_listesi", "musaitlik_sil",
    "musaitsizlikleri_getir", "personel_onayla", "personel_onizle", "personelleri_getir",
    "gorev_havuzu_ozeti", "onceki_gorev_kayitlari", "onceki_gorev_sayaclari",
    "taslak_pencereler", "personel_ayrintili_liste", "personel_durumu_degistir",
    "personel_ekle", "personel_sil", "BASVURU_IS_GUNU", "DUYURU_ONCE_GUN",
    "LISTE_HATIRLATMA_PENCERELERI", "basvuru_bekleyenler", "basvuru_kapsamindaki_ogrenciler",
    "basvuru_kaydet", "basvuru_tablosu", "duyuru_getir", "duyuru_kaydet",
    "eski_yildan_isaretler", "gecerli_basvurular", "isaret_tazeligi_uyarisi",
    "liste_tazeligi_uyarisi", "numara_listesini_coz", "ogrenci_bayrak_guncelle",
    "ogrenci_bayraklarini_toplu_guncelle", "ogrenci_etiketleri", "plan_disi_birakilanlar",
    "sube_duzeyi", "tek_ders_adaylari", "tek_ders_kayitlari", "tek_ders_sec",
    "ders_ayarlari", "ders_brans_esle", "ders_esdeger_branslari", "ders_ozellik_guncelle",
    "dersleri_listele", "iki_asamali_onerisi", "sorumluluk_kayitlari", "sorumluluk_onayla",
    "sorumluluk_onizle", "yabanci_dil_mi", "PlanBaglami", "brans_eslemelerini_denetle",
    "pencere_araligi", "plan_baglami", "plan_hazirla", "plan_kaydet", "plan_kesinlestir",
    "plan_sil", "plan_yukle", "plani_dogrula", "sinav_birimleri", "slot_saatlerini_coz",
    "yuk_ozetini_getir", "ELLE_HAFTA_SONU_GEREKCESI", "TasimaSonucu", "gorevli_adaylari",
    "gorevli_degisiklikleri", "gorevli_degistir", "hafta_sonu_gerekcesi_gerekir_mi",
    "kesin_plan_gorevli_degistir", "oturum_tasi", "plan_anlik_goruntusu", "plani_geri_yukle", "BEKLENEN_EVRAK", "EVRAK_ADLARI", "EVRAK_TURLERI",
    "OGRENCI_GOSTERIM_ADLARI", "OGRENCI_GOSTERIMI", "TESLIM_SURESI_IS_GUNU", "TeslimSatiri",
    "evrak_gecmisi", "evrak_surumu_kaydet", "gorev_sayaclari", "gorevli_listesi",
    "ilan_ogrenci_cizelgesi", "ilan_takvimi", "kisi_bazli_gorevler", "ogrenci_etiketi_uret",
    "onayli_belge_degisiklikleri", "oturum_ogrencileri", "plan_oturumlari",
    "teslim_cizelgesi", "teslim_geri_al", "teslim_kaydet", "teslim_ozeti",
]
