"""Arayüz renk paleti — okulapp.org "ss" renk kümesiyle aynı.

Renkler okulapp.org sitesindeki `src/styles/global.css` dosyasının
`:root[data-palette='ss']` bloğundan alınmıştır; sitede Sorumluluk Sınavı
bölümü bu kümeyi kullanır (bordo + sıcak kum). Amaç, siteyi görüp uygulamayı
açan kişinin aynı ürüne baktığını anlaması.

Site açık ve koyu tema tanımlar; masaüstü uygulamasının tema anahtarı yoktur,
bu yüzden yalnız **açık tema** karşılıkları alınmıştır.

Site tokenı doğrudan karşılığı olmayan birkaç değer türetilmiştir; her biri
aşağıda işaretlidir. Yeni renk gerekiyorsa önce sitede karşılığı var mı
bakın; yoksa buraya türetilmiş olarak ekleyin, koda doğrudan yazmayın.
"""

from __future__ import annotations

RENK = {
    # --- Yüzeyler ------------------------------------------------ site
    "zemin": "#F7F1EE",        # --paper    sayfa zemini
    "kart": "#FFFBF9",         # --surface  kart ve panel zemini
    "alan": "#FFFDFC",         # türetilmiş giriş alanı zemini
    "tint": "#F2E6E7",         # --tint     tablo başlığı, ikincil düğme
    "chip": "#F3DFE3",         # --chip     bilgi kutusu

    # --- Yazı ---------------------------------------------------------
    "yazi": "#2A141B",         # --ink
    "soluk": "#6D525A",        # --muted
    "cizgi": "#E8D9DC",        # --line
    "bag": "#9A2F4A",          # --link

    # --- Koyu panel (sol şerit) ---------------------------------------
    "kenar": "#5D1F31",        # --deep
    "kenar2": "#73273C",       # türetilmiş  panel içi ikinci ton
    "panel_yazi": "#FFFFFF",   # --on-deep
    "panel_soluk": "#F4E2E6",  # --on-deep-soft
    "panel_silik": "#E0BCC4",  # --on-deep-faint

    # --- Vurgu (sıcak kum) --------------------------------------------
    # DİKKAT: vurgu açık bir renktir; üstüne beyaz yazı okunmaz.
    # Vurgu zeminli her yerde yazı rengi "vurgu_yazi" olmalıdır.
    "vurgu": "#D9A066",        # --accent
    "vurgu2": "#E5B483",       # --accent-hover  (koyu panelde rozet rengi
                               #             olarak da kullanilir: vurgu
                               #             orada 4.4:1'de kaliyor)
    "vurgu_yazi": "#33190A",   # --accent-ink
    "vurgu_pasif": "#E4CDB4",  # türetilmiş  edilgin düğme

    # --- Durum renkleri ------------------------------------------------
    # Sitede karşılıkları yok; sıcak paletle uyumlu olacak biçimde seçildi.
    # "engel" bilinçli olarak açık kırmızıdır: bordo "kenar" ve "bag" ile
    # karışmaması gerekir.
    "basari": "#1F7A55",
    "uyari": "#B7791F",
    "engel": "#C0392B",
    "basari_zemin": "#E6F2EA",
    "uyari_zemin": "#FDF0E4",  # --warn-bg
    "engel_zemin": "#FAE3E1",
    "pasif_zemin": "#F2E6E7",  # --tint ile aynı

    # --- Takvim ızgarası (arayuz/takvim.py) ---------------------------
    # Sürükle-bırak plan ekranı; kenarlıklar zeminlerinin koyu karşılığıdır.
    "takvim_kart_kenar": "#A8677A",
    "takvim_kilit_kenar": "#C9B3B8",
    "takvim_uygulama_kenar": "#6FA98A",
    "takvim_hedef": "#F5DFC5",

    # --- Qt arayüzü (arayuz/tema.py) -----------------------------------
    # Türetilmiş: tablo satır şeridi ve kaydırma çubuğu; sitede karşılıkları
    # yok, zemin ile kart arasından seçildi.
    "zebra": "#FBF5F3",
    "kaydirma": "#D9C5CA",
    "kaydirma_ust": "#BFA2AA",
    # Durum şeritlerinin kenarı ve uyarı çipinin yazısı: zeminlerinin koyusu.
    "uyari_kenar": "#EBCFAE",
    "engel_kenar": "#EDBDB7",
    "basari_kenar": "#BFDCC9",
    "uyari_yazi": "#8A5A12",
    # Edilgin denetimin yazısı; edilgin ana düğmenin yazısı.
    "pasif_yazi": "#A8949A",
    "vurgu_pasif_yazi": "#7A6250",
    # Yarı saydam katmanlar: meşgul örtüsü (zemin) ve şerit içi düğme.
    "ortu": "rgba(247, 241, 238, 0.82)",
    "serit_dugme": "rgba(255, 255, 255, 0.55)",
}
