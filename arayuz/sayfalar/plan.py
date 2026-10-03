"""07 Sınav planı: üretme, sürükle-bırak düzenleme, görevli değişikliği, kesinleştirme.

Plan bellekte tutulur: sürükle-bırakla ve görevli değişikliğiyle düzenlenir,
"Geri al" ile adım adım geri sarılır ve ancak "Kaydet" ile veritabanına
yazılır. Plan üretimi arka planda yürür; Tk sürümünde en çok bir dakika süren
arama boyunca pencere donuyordu.
"""

from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from arayuz.bilesenler import (
    AkisDuzeni, Kart, Serit, Sutun, Tablo, arka_planda, cip, dugme, etiket, etiketli,
    secim_kutusu, yatay,
)
from arayuz.palet import RENK
from arayuz.pencereler import GorevliDegistirPenceresi, TekDersPenceresi, YukCozumlemePenceresi
from arayuz.sayfalar.temel import Sayfa
from arayuz.takvim import SurukleBirakTakvim
from cekirdek.kurallar import GUNLUK_SINAV_TAVANI, oturum_araligi
from cekirdek.modeller import GorevRolu, IkiAsamaliSayim, PlanParametreleri, PlanTuru
from cekirdek.planlayici import PlanlamaBasarisiz, PlanlamaSonucu
from cekirdek.takvim import gunleri_listele, pencere_adi, tarih_yaz
from veri import hizmet
from veri.hizmet import HizmetHatasi

PLAN_TURU_EKI = {PlanTuru.OLAGAN: "", PlanTuru.TEK_DERS: " — tek ders (58/6)"}
CIDDIYET_ZEMINI = {"ENGEL": RENK["engel_zemin"], "UYARI": RENK["uyari_zemin"]}


def donem_secenekleri(vt) -> list[tuple[str, str, PlanTuru]]:
    """(gösterim, dönem kodu, plan türü). Tek ders sınavı (OKY md.58/6) her
    dönemin olağan planının yanında ayrı bir seçenektir."""
    secenekler = []
    for kod in ("P1", "P2", "P3"):
        for tur in (PlanTuru.OLAGAN, PlanTuru.TEK_DERS):
            try:
                bas, bit = hizmet.pencere_araligi(vt, kod, tur)
            except HizmetHatasi:
                continue
            secenekler.append((f"{pencere_adi(kod)}{PLAN_TURU_EKI[tur]}  "
                               f"{tarih_yaz(bas)}–{tarih_yaz(bit)}", kod, tur))
    return secenekler


def kart_bilgisi(oturum, saatler: list[time], salon_adlari: dict[int, str]) -> dict:
    """Takvim kartı: başlık, alt satır ve uzun uygulamanın sürdüğü saatler."""
    uygulama = oturum.oturum_turu.value == "uygulama"
    baslik = "/".join(str(d) for d in oturum.duzeyler) + " " + oturum.ders_adi
    bitis = oturum_araligi(oturum)[1].time()
    suren = [s for s in saatler if oturum.saat < s < bitis]
    if uygulama:
        # Kart yalnız başladığı satırda durur; sonraki oturum saatine taşan
        # uzun uygulama bitişiyle yazılır ki o hücre boş sanılmasın.
        baslik += f" (uyg. –{bitis:%H:%M})" if suren else " (uyg.)"
    salonlar = ", ".join(salon_adlari.get(s, "?") for s in oturum.salon_kimlikleri)
    return {
        "anahtar": oturum.anahtar, "baslik": baslik,
        "alt": f"{oturum.ogrenci_sayisi} öğrenci • {len(oturum.salon_kimlikleri)} salon",
        "ipucu": f"{baslik}\n{tarih_yaz(oturum.tarih)} {oturum.saat:%H:%M}–{bitis:%H:%M}\n"
                 f"{oturum.ogrenci_sayisi} öğrenci • {salonlar}",
        "tarih": oturum.tarih, "saat": oturum.saat,
        "tur": oturum.oturum_turu.value, "kilitli": oturum.kilitli_mi,
        "suren_saatler": suren,
    }


class PlanSayfasi(Sayfa):
    def __init__(self, uyg) -> None:
        super().__init__(uyg)
        self.plan_sonucu: PlanlamaSonucu | None = None
        self.geri_yigini: list = []
        self.ileri_yigini: list = []
        self.kaydedilmemis = False
        self.aktif_plan_id: int | None = None
        self.secili_oturum: str | None = None
        self.takvim: SurukleBirakTakvim | None = None
        self.secenekler: list[tuple[str, str, PlanTuru]] = []
        self._hazir = False

        self.on_kosul = Serit("", "engel")
        self.on_kosul.hide()
        self.duzen.addWidget(self.on_kosul)
        self.duzen.addWidget(self._parametre_karti())
        bolme = QSplitter(Qt.Orientation.Horizontal)
        bolme.setChildrenCollapsible(False)
        self.takvim_kabi = Kart(kenar=(10, 10, 10, 10))
        self.takvim_kabi.duzen.setSpacing(0)
        self.bos_takvim = etiket("Parametreleri seçip planı üretin.", "Soluk")
        self.bos_takvim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.takvim_kabi.ekle(self.bos_takvim, 1)
        bolme.addWidget(self.takvim_kabi)
        bolme.addWidget(self._yan_panel())
        bolme.setStretchFactor(0, 1)
        self.duzen.addWidget(bolme, 1)
        self.duzen.addLayout(self._alt_cubuk())

    # ---------------------------------------------------------------- kuruluş
    def _parametre_karti(self) -> Kart:
        kart = Kart(kenar=(16, 12, 16, 12))
        self.pencere_secimi = secim_kutusu(en_az=30)
        self.pencere_secimi.currentIndexChanged.connect(lambda _i: self.donem_degisti())
        self.tek_ders_dugmesi = dugme("Tek ders öğrencileri…", "", "kisi",
                                      tiklaninca=self.tek_ders_ac)
        kart.ekle(yatay(QLabel("Dönem"), self.pencere_secimi, self.tek_ders_dugmesi, 0,
                        dugme("Yükü çözümle", "", "cozumle", tiklaninca=self.yuku_cozumle),
                        dugme("Planı üret", "ana", "uret", tiklaninca=self.plan_uret)))
        self.hafta_sonu = QCheckBox("Hafta sonu kullanılabilir")
        self.gunluk_sinir = QSpinBox()
        self.gunluk_sinir.setRange(1, GUNLUK_SINAV_TAVANI)
        self.gunluk_sinir.setValue(2)
        self.gunluk_sinir.setToolTip("ÖDY md.5/1-k: ikiyi geçmemesi esastır, zorunlu hâlde üç.")
        self.sayim_secimi = secim_kutusu(["tek sınav sayılır", "ayrı sayılır"], en_az=14)
        self.uygulama_suresi = QSpinBox()
        self.uygulama_suresi.setRange(10, 180)
        self.uygulama_suresi.setSingleStep(5)
        self.uygulama_suresi.setValue(40)
        self.uygulama_suresi.setSuffix(" dk")
        self.uygulama_suresi.setToolTip("Uygulamalı sınavın süresini zümre belirler "
                                        "(OKY md.45/1-f).")
        self.saat_girdisi = QLineEdit(", ".join(hizmet.VARSAYILAN_SLOT_SAATLERI))
        self.saat_girdisi.setMinimumWidth(300)
        parametreler = QWidget()
        akis = AkisDuzeni(parametreler, 14)
        for oge in (self.hafta_sonu, etiketli("Günlük sınav sınırı", self.gunluk_sinir),
                    etiketli("Yazılı + uygulama", self.sayim_secimi),
                    etiketli("Uygulama süresi", self.uygulama_suresi),
                    etiketli("Oturum saatleri", self.saat_girdisi)):
            akis.addWidget(oge)
        kart.ekle(parametreler)
        self.ozet_cipleri = QHBoxLayout()
        self.ozet_cipleri.setSpacing(6)
        kart.ekle(self.ozet_cipleri)
        self.notlar = etiket("", "Soluk", sar=True)
        kart.ekle(self.notlar)
        return kart

    def _yan_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(330)
        panel.setMaximumWidth(430)
        duzen = QVBoxLayout(panel)
        duzen.setContentsMargins(10, 0, 0, 0)
        duzen.setSpacing(12)
        secim = Kart("Seçili sınav", kenar=(14, 12, 14, 12))
        self.secim_etiketi = etiket("", sar=True)
        secim.ekle(self.secim_etiketi)
        self.gorevli_dugmesi = dugme("Görevliyi değiştir…", "", "degistir",
                                     tiklaninca=self.gorevli_degistir_ac)
        secim.ekle(yatay(self.gorevli_dugmesi, 0))
        duzen.addWidget(secim)

        denetim = Kart("Kural denetimi", kenar=(14, 12, 14, 12))
        self.ihlal_suzgeci = secim_kutusu(["Bütün bulgular", "Yalnız engeller",
                                           "Yalnız uyarılar"], en_az=14)
        self.ihlal_suzgeci.currentIndexChanged.connect(lambda _i: self._ihlal_suzgeci())
        denetim.ekle(yatay(self.ihlal_suzgeci, 0))
        self.ihlal_tablosu = Tablo(
            [Sutun("Kural", lambda i: i.kural_kimligi, 64),
             Sutun("Açıklama", lambda i: i.aciklama, uzat=True,
                   ipucu=lambda i: f"{i.aciklama}\n\nDayanak: {i.dayanak}")],
            anahtar=lambda i: (i.kural_kimligi, i.etkilenen_kayit, i.aciklama),
            zemin=lambda i: CIDDIYET_ZEMINI.get(i.ciddiyet.value),
            bos_metin="Engel ya da uyarı yok.")
        self.ihlal_tablosu.gorunum.setWordWrap(True)
        denetim.ekle(self.ihlal_tablosu, 1)
        duzen.addWidget(denetim, 1)
        self._secimi_temizle()
        return panel

    def _alt_cubuk(self) -> QHBoxLayout:
        self.geri_dugmesi = dugme("Geri al", "", "geri", "Ctrl+Z", self.geri_al)
        self.ileri_dugmesi = dugme("İleri al", "", "ileri", "Ctrl+Y", self.ileri_al)
        self.kaydet_dugmesi = dugme("Kaydet", "ana", "kaydet", "Ctrl+S", self.plan_kaydet)
        self.onay_girdisi = QLineEdit()
        self.onay_girdisi.setPlaceholderText("Müdür onay no")
        self.onay_girdisi.setFixedWidth(170)
        self.kesinlestir_dugmesi = dugme("Müdür onayıyla kesinleştir", "", "kilit",
                                         tiklaninca=self.plan_kesinlestir)
        return yatay(self.geri_dugmesi, self.ileri_dugmesi, self.kaydet_dugmesi, 0,
                     self.onay_girdisi, self.kesinlestir_dugmesi)

    # ------------------------------------------------------------- dönem
    def goster(self) -> None:
        try:
            hizmet.pencereleri_getir(self.vt)
        except HizmetHatasi as hata:
            self.on_kosul.ayarla(str(hata), "engel")
            self.setEnabled_icerik(False)
            return
        self.on_kosul.hide()
        self.setEnabled_icerik(True)
        bellekteki = self._bellekteki_secim()
        self.secenekler = donem_secenekleri(self.vt)
        hedef = bellekteki or getattr(self, "plan_secimi", None) or (
            hizmet.varsayilan_pencere(self.vt), PlanTuru.OLAGAN)
        self.pencere_secimi.blockSignals(True)
        self.pencere_secimi.clear()
        self.pencere_secimi.addItems([s[0] for s in self.secenekler])
        sira = next((i for i, s in enumerate(self.secenekler) if (s[1], s[2]) == tuple(hedef)), 0)
        self.pencere_secimi.setCurrentIndex(sira)
        self.pencere_secimi.blockSignals(False)
        self._tek_ders_dugmesini_ayarla()
        # Kaydedilmemiş plan başka sayfaya gidip dönünce kaybolmamalı.
        if bellekteki and bellekteki == self.plan_secimi_al():
            self.takvimi_ciz()
        elif not self._hazir or self.plan_sonucu is None or not self.kaydedilmemis:
            self.son_plani_yukle()
        self._hazir = True

    def setEnabled_icerik(self, etkin: bool) -> None:  # noqa: N802
        for i in range(1, self.duzen.count()):
            oge = self.duzen.itemAt(i)
            if oge.widget() is not None:
                oge.widget().setEnabled(etkin)
            elif oge.layout() is not None:
                for j in range(oge.layout().count()):
                    alt = oge.layout().itemAt(j).widget()
                    if alt is not None:
                        alt.setEnabled(etkin)

    def _bellekteki_secim(self) -> tuple[str, PlanTuru] | None:
        if not (self.kaydedilmemis and self.plan_sonucu):
            return None
        p = self.plan_sonucu.plan.parametreler
        return p.pencere_kodu, PlanTuru(p.plan_turu)

    def plan_secimi_al(self) -> tuple[str, PlanTuru]:
        if not self.secenekler:
            return hizmet.varsayilan_pencere(self.vt), PlanTuru.OLAGAN
        _, kod, tur = self.secenekler[max(0, self.pencere_secimi.currentIndex())]
        return kod, tur

    def _tek_ders_dugmesini_ayarla(self) -> None:
        self.tek_ders_dugmesi.setEnabled(self.plan_secimi_al()[1] is PlanTuru.TEK_DERS)

    def donem_degisti(self) -> None:
        """Dönem değişince o dönemin kayıtlı planı açılır.

        Eski sürümde kutu değişse de ekranda Eylül planı kalıyordu; "Müdür
        onayıyla kesinleştir" seçili dönemi değil ekrandaki planı
        kesinleştirebiliyordu.
        """
        if self.kaydedilmemis and not self.ileti.soru(
                "Kaydedilmemiş plan", "Ekrandaki planın kaydedilmemiş değişiklikleri var. Dönem "
                "değişirse bunlar kaybolur. Devam edilsin mi?", "Devam et", uyari=True):
            eski = self._bellekteki_secim()
            self.pencere_secimi.blockSignals(True)
            self.pencere_secimi.setCurrentIndex(next(
                (i for i, s in enumerate(self.secenekler) if eski and (s[1], s[2]) == eski), 0))
            self.pencere_secimi.blockSignals(False)
            return
        self.plan_secimi = self.plan_secimi_al()
        self.plan_sonucu = None
        self.aktif_plan_id = None
        self.kaydedilmemis = False
        self.geri_yigini.clear()
        self.ileri_yigini.clear()
        self._tek_ders_dugmesini_ayarla()
        self.son_plani_yukle()

    def tek_ders_ac(self) -> None:
        TekDersPenceresi(self.uyg, self.plan_secimi_al()[0]).exec()

    # ----------------------------------------------------------- parametreler
    def parametreleri_topla(self) -> PlanParametreleri:
        kod, tur = self.plan_secimi_al()
        return PlanParametreleri(
            pencere_kodu=kod,
            hafta_sonu_kullan=self.hafta_sonu.isChecked(),
            ogrenci_gunluk_sinav_siniri=self.gunluk_sinir.value(),
            iki_asamali_sayim=(IkiAsamaliSayim.TEK if self.sayim_secimi.currentIndex() == 0
                               else IkiAsamaliSayim.AYRI),
            slot_saatleri=hizmet.slot_saatlerini_coz(self.saat_girdisi.text()),
            uygulama_suresi_dakika=self.uygulama_suresi.value(),
            plan_turu=tur,
        )

    def yuku_cozumle(self) -> None:
        try:
            p = self.parametreleri_topla()
            ozet = hizmet.yuk_ozetini_getir(self.vt, p.iki_asamali_sayim,
                                            p.ogrenci_gunluk_sinav_siniri, p.pencere_kodu,
                                            p.plan_turu)
        except (HizmetHatasi, ValueError) as hata:
            self.hata("Yük çözümlenemedi", hata)
            return
        YukCozumlemePenceresi(self.uyg, ozet, len(p.slot_saatleri)).exec()

    # ----------------------------------------------------------------- üretim
    def plan_uret(self) -> None:
        if self.kaydedilmemis and not self.ileti.soru(
                "Kaydedilmemiş plan", "Kaydedilmemiş değişiklikler var; yeni plan bunların yerine "
                "geçecek. Devam edilsin mi?", "Yeni plan üret", uyari=True):
            return
        try:
            parametreler = self.parametreleri_topla()
        except (HizmetHatasi, ValueError) as hata:
            self.hata("Plan üretilemedi", hata)
            return
        if parametreler.plan_turu is PlanTuru.OLAGAN:
            # SP-15: Şubat ve Haziran planları aylar önceki listeyle üretilebilir;
            # md.58/2-d işaretleri de önceki yıldan kalmış olabilir.
            for baslik, uyari in (
                    ("Liste güncel mi?",
                     hizmet.liste_tazeligi_uyarisi(self.vt, parametreler.pencere_kodu)),
                    ("Başvuru işaretleri güncel mi?", hizmet.isaret_tazeligi_uyarisi(self.vt))):
                if uyari and not self.ileti.soru(baslik, uyari + "\n\nYine de devam edilsin mi?",
                                                 "Devam et", uyari=True):
                    return
        self.uyg.mesgul_ac("Plan üretiliyor… Büyük okulda bir dakikayı bulabilir.")
        arka_planda(lambda: hizmet.plan_hazirla(self.vt, parametreler), self._plan_uretildi,
                    self._plan_uretilemedi)

    def _plan_uretilemedi(self, hata: BaseException) -> None:
        self.uyg.mesgul_kapat()
        if isinstance(hata, (HizmetHatasi, PlanlamaBasarisiz, ValueError)):
            self.hata("Plan üretilemedi", hata)
        else:
            raise hata

    def _plan_uretildi(self, sonuc: PlanlamaSonucu) -> None:
        self.uyg.mesgul_kapat()
        self.plan_sonucu = sonuc
        self.geri_yigini.clear()
        self.ileri_yigini.clear()
        self.kaydedilmemis = True
        self.aktif_plan_id = None
        self.takvimi_ciz()
        self.bildir(f"Plan üretildi: {len(sonuc.plan.oturumlar)} oturum, "
                    f"{sonuc.kullanilan_gun_sayisi} gün. Kaydetmeyi unutmayın.")

    def son_plani_yukle(self) -> None:
        kod, tur = self.plan_secimi_al()
        plan_id = hizmet.son_plani_getir(self.vt, kod, tur)
        if plan_id is None:
            self.plan_sonucu = None
            self.aktif_plan_id = None
            self.takvimi_ciz()
            return
        try:
            plan, bilgi = hizmet.plan_yukle(self.vt, plan_id)
        except HizmetHatasi as hata:
            self.hata("Plan açılamadı", hata)
            return
        sinirlar = bilgi["kisisel_sinirlar"]
        ihlaller = hizmet.plani_dogrula(self.vt, plan, sinirlar)
        self.plan_sonucu = PlanlamaSonucu(plan, ihlaller, sinirlar,
                                          len({o.tarih for o in plan.oturumlar}))
        self.aktif_plan_id = plan_id
        self.kaydedilmemis = False
        self.takvimi_ciz()

    # ----------------------------------------------------------------- takvim
    def takvimi_ciz(self) -> None:
        if self.takvim is not None:
            self.takvim.setParent(None)
            self.takvim.deleteLater()
            self.takvim = None
        if not self.plan_sonucu:
            self.bos_takvim.setText("Bu dönemde kayıtlı plan yok. Parametreleri seçip planı "
                                    "üretin.")
            self.bos_takvim.show()
            self._secimi_temizle()
            self._ozeti_tazele()
            return
        self.bos_takvim.hide()
        plan = self.plan_sonucu.plan
        try:
            bas, bit = hizmet.pencere_araligi(self.vt, plan.parametreler.pencere_kodu,
                                              plan.parametreler.plan_turu)
        except HizmetHatasi:
            return
        gunler = gunleri_listele(bas, bit, plan.parametreler.hafta_sonu_kullan,
                                 hizmet.tatilleri_getir(self.vt))
        # Kayıtlı plandaki bir oturum sonradan tatil yapılan güne düşüyorsa o gün
        # de gösterilir; yoksa kart görünmez olur (SP-08 engeli zaten yazar).
        gunler = sorted(set(gunler) | {o.tarih for o in plan.oturumlar})
        saatler = sorted({o.saat for o in plan.oturumlar} | set(plan.parametreler.slot_saatleri))
        salon_adlari = {s.kimlik: s.ad for s in hizmet.salonlari_getir(self.vt)}
        kartlar = [kart_bilgisi(o, saatler, salon_adlari) for o in plan.oturumlar]
        self.takvim = SurukleBirakTakvim(gunler, saatler, kartlar, self.kart_birakildi,
                                         self.kart_secildi)
        self.takvim_kabi.ekle(self.takvim, 1)
        if self.secili_oturum and plan.oturum_bul(self.secili_oturum):
            self.kart_secildi(self.secili_oturum)
        else:
            self._secimi_temizle()
        self._ozeti_tazele()

    def _secimi_temizle(self) -> None:
        self.secili_oturum = None
        self.secim_etiketi.setText("Bir sınav kartına tıklayın: komisyon ve gözcüler burada "
                                   "görünür. Kartı sürükleyerek başka gün ya da saate "
                                   "taşıyabilirsiniz.")
        self.gorevli_dugmesi.setEnabled(False)

    def kart_secildi(self, anahtar: str) -> None:
        """Seçili oturumun ayrıntısı; görevli değişikliğinin başlangıcı."""
        if not self.plan_sonucu:
            return
        plan = self.plan_sonucu.plan
        oturum = plan.oturum_bul(anahtar)
        if oturum is None:
            self._secimi_temizle()
            return
        self.secili_oturum = anahtar
        if self.takvim is not None:
            self.takvim.secimi_goster(anahtar)
        kisiler = {p.kimlik: p.ad for p in hizmet.personelleri_getir(self.vt, yalniz_aktif=False)}
        salonlar = {s.kimlik: s.ad for s in hizmet.salonlari_getir(self.vt)}
        gorevler = plan.oturum_gorevleri(anahtar)
        komisyon = ", ".join(kisiler.get(g.personel_kimligi, "?") for g in gorevler
                             if g.rol is GorevRolu.KOMISYON_UYESI) or "atanmadı"
        gozcu = "\n".join(
            "  • " + kisiler.get(g.personel_kimligi, "?")
            + (f" ({salonlar[g.salon_kimligi]})" if g.salon_kimligi in salonlar else "")
            for g in gorevler if g.rol is GorevRolu.GOZCU) or "  atanmadı"
        tur = " (uygulama)" if oturum.oturum_turu.value == "uygulama" else ""
        bitis = oturum_araligi(oturum)[1]
        self.secim_etiketi.setText(
            f"{'/'.join(map(str, oturum.duzeyler))} {oturum.ders_adi}{tur}\n"
            f"{tarih_yaz(oturum.tarih)} {oturum.saat:%H:%M}–{bitis:%H:%M} • "
            f"{oturum.ogrenci_sayisi} öğrenci\n"
            f"Salon: {', '.join(salonlar.get(s, '?') for s in oturum.salon_kimlikleri)}\n"
            f"Komisyon: {komisyon}\nGözcü:\n{gozcu}"
            + ("\n\nKesin plan: değişiklik müdür onayıyla." if oturum.kilitli_mi else ""))
        self.gorevli_dugmesi.setEnabled(True)

    def gorevli_degistir_ac(self) -> None:
        if not self.plan_sonucu or not self.secili_oturum:
            return
        oturum = self.plan_sonucu.plan.oturum_bul(self.secili_oturum)
        if oturum is None:
            return
        if oturum.kilitli_mi and (self.aktif_plan_id is None or self.kaydedilmemis):
            self.ileti.uyari("Kaydedilmemiş plan", "Önce planı kaydedin.")
            return
        GorevliDegistirPenceresi(self.uyg, self, self.secili_oturum).exec()

    def gorevli_degisti(self, anahtar: str, goruntu, kesin: bool) -> None:
        """Görevli değiştirme penceresinin geri çağrısı."""
        if kesin:
            self.son_plani_yukle()
            self.bildir("Görevli değişikliği müdür onayıyla kaydedildi.")
        else:
            self.geri_yigini.append(goruntu)
            self.ileri_yigini.clear()
            self.kaydedilmemis = True
            self.takvimi_ciz()
            self.bildir("Görevli değiştirildi. Kaydetmeyi unutmayın.", "Geri al", self.geri_al)
        self.kart_secildi(anahtar)

    def kart_birakildi(self, anahtar: str, tarih: date, saat: time) -> None:
        if not self.plan_sonucu:
            return
        plan = self.plan_sonucu.plan
        oturum = plan.oturum_bul(anahtar)
        if oturum is None or (oturum.tarih == tarih and oturum.saat == saat):
            return
        goruntu = hizmet.plan_anlik_goruntusu(plan)
        try:
            sonuc = hizmet.oturum_tasi(self.vt, plan, anahtar, tarih, saat,
                                       self.plan_sonucu.yukseltilen_sinirlar)
        except HizmetHatasi as hata:
            self.hata("Oturum taşınamadı", hata)
            return
        if not sonuc.uygulandi:
            self.ileti.uyari("Taşıma yapılamadı",
                             f"{oturum.ders_adi} sınavı {tarih_yaz(tarih)} {saat:%H:%M} saatine "
                             "taşınamadı.\n\n" + sonuc.mesaj())
            return
        self.geri_yigini.append(goruntu)
        self.ileri_yigini.clear()
        self.kaydedilmemis = True
        self.secili_oturum = anahtar
        self.takvimi_ciz()
        self.bildir(f"{oturum.ders_adi} {tarih_yaz(tarih)} {saat:%H:%M} saatine taşındı.",
                    "Geri al", self.geri_al)

    # ---------------------------------------------------------- özet ve ihlal
    def _ozeti_tazele(self) -> None:
        while self.ozet_cipleri.count():
            oge = self.ozet_cipleri.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()
        sonuc = self.plan_sonucu
        if sonuc is None:
            self._kesin_mi = False
            self.notlar.setText("")
            self.ihlal_tablosu.yukle([])
            self._dugmeleri_tazele()
            return
        plan = sonuc.plan
        ihlaller = hizmet.plani_dogrula(self.vt, plan, sonuc.yukseltilen_sinirlar)
        sonuc.ihlaller = ihlaller
        engel = sum(1 for i in ihlaller if i.engel_mi)
        gunler = sorted({o.tarih for o in plan.oturumlar})
        aralik = f" ({gunler[0]:%d.%m} – {gunler[-1]:%d.%m})" if gunler else ""
        kesin = bool(plan.oturumlar) and all(o.kilitli_mi for o in plan.oturumlar)
        self._kesin_mi = kesin and not self.kaydedilmemis
        durum = ("kesin (müdür onaylı)" if kesin and not self.kaydedilmemis
                 else "kaydedilmedi" if self.kaydedilmemis else f"kayıtlı (#{self.aktif_plan_id})")
        for metin, tur in ((f"{len(plan.oturumlar)} oturum", ""),
                           (f"{len(gunler)} gün{aralik}", ""),
                           (f"{len(plan.gorevlendirmeler)} görev", ""),
                           (f"{engel} engel", "engel" if engel else "basari"),
                           (f"{len(ihlaller) - engel} uyarı", "uyari" if len(ihlaller) > engel
                            else ""),
                           (durum, "uyari" if self.kaydedilmemis else "basari")):
            self.ozet_cipleri.addWidget(cip(metin, tur))
        self.ozet_cipleri.addStretch(1)
        notlar = []
        if sonuc.yukseltilen_sinirlar:
            notlar.append(f"Günlük sınırı yükseltilen öğrenci: {len(sonuc.yukseltilen_sinirlar)} "
                          "(ikiyi geçmemesi esastır — ÖDY md.5/1-k; ayrıntı kural denetiminde).")
        notlar += sonuc.notlar[:3]
        self.notlar.setText("\n".join(notlar))
        self.ihlal_tablosu.yukle(ihlaller)
        self._ihlal_suzgeci()
        self._dugmeleri_tazele()

    def _ihlal_suzgeci(self) -> None:
        secim = self.ihlal_suzgeci.currentIndex()
        self.ihlal_tablosu.kosulu_ayarla(
            lambda i: secim == 0 or (secim == 1 and i.engel_mi)
            or (secim == 2 and not i.engel_mi))

    def _dugmeleri_tazele(self) -> None:
        self.geri_dugmesi.setEnabled(bool(self.geri_yigini))
        self.ileri_dugmesi.setEnabled(bool(self.ileri_yigini))
        self.kaydet_dugmesi.setEnabled(self.kaydedilmemis)
        self.kesinlestir_dugmesi.setEnabled(self.aktif_plan_id is not None
                                            and not self.kaydedilmemis
                                            and not getattr(self, "_kesin_mi", False))
        self.onay_girdisi.setEnabled(self.kesinlestir_dugmesi.isEnabled())

    # ----------------------------------------------------- geri/ileri, kayıt
    def geri_al(self) -> None:
        if not self.geri_yigini or not self.plan_sonucu:
            return
        self.ileri_yigini.append(hizmet.plan_anlik_goruntusu(self.plan_sonucu.plan))
        hizmet.plani_geri_yukle(self.plan_sonucu.plan, self.geri_yigini.pop())
        self.kaydedilmemis = True
        self.takvimi_ciz()

    def ileri_al(self) -> None:
        if not self.ileri_yigini or not self.plan_sonucu:
            return
        self.geri_yigini.append(hizmet.plan_anlik_goruntusu(self.plan_sonucu.plan))
        hizmet.plani_geri_yukle(self.plan_sonucu.plan, self.ileri_yigini.pop())
        self.kaydedilmemis = True
        self.takvimi_ciz()

    kisayol_geri = geri_al
    kisayol_ileri = ileri_al

    def plan_kaydet(self) -> None:
        if not self.plan_sonucu or not self.kaydedilmemis:
            return
        engel = [i for i in self.plan_sonucu.ihlaller if i.engel_mi]
        if engel and not self.ileti.soru(
                "Engelli plan", f"Planda {len(engel)} engel var. Taslak olarak yine de "
                "kaydedilsin mi?\n\n(Kesinleştirmek için engeller giderilmelidir.)",
                "Taslak kaydet", uyari=True):
            return
        try:
            plan_id = hizmet.plan_kaydet(self.vt, self.plan_sonucu)
        except HizmetHatasi as hata:
            self.hata("Plan kaydedilemedi", hata)
            return
        self.aktif_plan_id = plan_id
        self.kaydedilmemis = False
        self.geri_yigini.clear()
        self.ileri_yigini.clear()
        self._ozeti_tazele()
        self.bildir(f"Plan #{plan_id} olarak kaydedildi.")

    kisayol_kaydet = plan_kaydet

    def plan_kesinlestir(self) -> None:
        if self.aktif_plan_id is None:
            self.ileti.uyari("Kaydedilmemiş plan", "Kesinleştirmeden önce planı kaydedin.")
            return
        if self.kaydedilmemis:
            self.ileti.uyari("Kaydedilmemiş değişiklik", "Önce değişiklikleri kaydedin.")
            return
        if not self.ileti.soru("Planı kesinleştir",
                               "Plan müdür onayıyla kesinleşecek; oturumlar kilitlenir ve plan "
                               "silinemez. Sonraki görevli değişiklikleri onay numarasıyla "
                               "kaydedilir. Devam edilsin mi?", "Kesinleştir"):
            return
        try:
            hizmet.plan_kesinlestir(self.vt, self.aktif_plan_id, self.onay_girdisi.text())
        except HizmetHatasi as hata:
            self.hata("Plan kesinleştirilemedi", hata)
            return
        self.son_plani_yukle()
        self.bildir("Plan müdür onayıyla kesinleşti ve oturumlar kilitlendi.")

    def kapanabilir_mi(self) -> bool:
        if not self.kaydedilmemis:
            return True
        return self.ileti.soru("Kaydedilmemiş plan", "Kaydedilmemiş plan değişiklikleri var. "
                               "Yine de çıkılsın mı?", "Çık", "Vazgeç", uyari=True)


__all__ = ["PlanSayfasi", "donem_secenekleri", "kart_bilgisi"]
