"""Ana pencerenin açtığı iletişim pencereleri.

Her pencere bir kayda (öğretmen, oturum, dönem) bağlı küçük bir iştir ve ana
ekranı kalabalıklaştırmamalıdır. Pencereler SQL yazmaz, kural bilmez; her şeyi
`veri.hizmet` üzerinden yapar. Sayfalar pencereyi `exec()` ile açar; testler
pencereyi açmadan kurup yöntemlerini doğrudan çağırır.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QGridLayout, QGroupBox, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout,
)

from arayuz.bilesenler import (
    secim_kutusu,
    AramaKutusu, SaatAlani, Serit, Sutun, Tablo, TarihAlani, cip, dugme, etiket, yatay,
)
from arayuz.palet import RENK
from cekirdek.kurallar import GUNLUK_SINAV_TAVANI
from cekirdek.modeller import GorevRolu
from cekirdek.planlayici import sinir_onizlemesi
from cekirdek.takvim import tarih_yaz
from veri import hizmet
from veri.hizmet import HizmetHatasi

if TYPE_CHECKING:
    from arayuz.uygulama import Uygulama

ROL_ADLARI = {GorevRolu.KOMISYON_UYESI: "Komisyon üyesi", GorevRolu.GOZCU: "Gözcü"}
KVKK_UYARISI = "Sağlık bilgisi yazmayın (KVKK özel nitelikli veri); 'izinli', 'derste' yeter."


class Pencere(QDialog):
    def __init__(self, uyg: "Uygulama", baslik: str, genislik: int = 820, yukseklik: int = 560):
        super().__init__(uyg)
        self.uyg = uyg
        self.vt = uyg.vt
        self.setWindowTitle(baslik)
        self.resize(genislik, yukseklik)
        self.setModal(True)
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(20, 18, 20, 16)
        self.duzen.setSpacing(12)

    def hata(self, baslik: str, hata: BaseException | str) -> None:
        self.uyg.ileti.hata(baslik, str(hata), ust=self)

    def uyari(self, baslik: str, metin: str) -> None:
        self.uyg.ileti.uyari(baslik, metin, ust=self)


# ================================================================ müsaitlik

class MusaitlikPenceresi(Pencere):
    """Öğretmenin görev alamayacağı zamanlar (OKY md.58/2-ç)."""

    def __init__(self, uyg: "Uygulama", kisi: dict):
        super().__init__(uyg, f"Müsaitlik — {kisi['ad']}", 860, 620)
        self.kisi = kisi
        self.duzen.addWidget(etiket(
            "Öğretmenin sınav görevi alamayacağı zamanları girin: ders programındaki dolu "
            "saatler, izin, başka görev. Planlayıcı bu saatlere görev vermez; elle verilen görev "
            "engel olarak görünür (SP-09). " + KVKK_UYARISI, "Soluk", sar=True))
        self.tablo = Tablo([Sutun("Zaman", lambda k: k["zaman"], 260),
                            Sutun("Saat", lambda k: k["saat"], 140),
                            Sutun("Açıklama", lambda k: k["aciklama"], uzat=True)],
                           anahtar=lambda k: k["kimlik"], coklu_secim=True,
                           bos_metin="Kayıt yok: öğretmen her saatte görev alabilir.")
        self.duzen.addWidget(self.tablo, 1)
        self.duzen.addLayout(yatay(0, dugme("Seçilenleri sil", "tehlike", "sil",
                                            tiklaninca=self._sil)))

        haftalik = QGroupBox("Her hafta tekrar eden (ör. ders programı) — saat boşsa bütün gün")
        self.gun = secim_kutusu()
        self.gun.addItems(hizmet.HAFTA_GUNLERI)
        self.h_bas, self.h_bit = SaatAlani(), SaatAlani()
        self.h_aciklama = QLineEdit()
        self.h_aciklama.setPlaceholderText("Açıklama (ör. derste)")
        kutu = QVBoxLayout(haftalik)
        kutu.addLayout(yatay(self.gun, QLabel("Saat"), self.h_bas, QLabel("–"), self.h_bit,
                             self.h_aciklama, dugme("Ekle", "ana", "ekle",
                                                    tiklaninca=self._haftalik_ekle)))
        self.duzen.addWidget(haftalik)

        tarihli = QGroupBox("Tarih aralığı (izin, başka görevlendirme) — saat boşsa bütün gün")
        self.t_bas_tarih = TarihAlani()
        self.t_bit_tarih = TarihAlani(bos_olabilir=True)
        self.t_bas, self.t_bit = SaatAlani(), SaatAlani()
        self.t_aciklama = QLineEdit()
        self.t_aciklama.setPlaceholderText("Açıklama (ör. izinli)")
        kutu = QVBoxLayout(tarihli)
        kutu.addLayout(yatay(QLabel("Başlangıç"), self.t_bas_tarih, QLabel("Bitiş (boşsa tek gün)"),
                             self.t_bit_tarih, 0))
        kutu.addLayout(yatay(QLabel("Saat"), self.t_bas, QLabel("–"), self.t_bit, self.t_aciklama,
                             dugme("Ekle", "ana", "ekle", tiklaninca=self._tarihli_ekle)))
        self.duzen.addWidget(tarihli)
        self.duzen.addLayout(yatay(0, dugme("Kapat", tiklaninca=self.accept)))
        self._doldur()

    def _doldur(self) -> None:
        self.tablo.yukle(hizmet.musaitlik_listesi(self.vt, self.kisi["kimlik"]))

    def _haftalik_ekle(self) -> None:
        try:
            hizmet.musaitlik_ekle(self.vt, self.kisi["kimlik"], hafta_gunu=self.gun.currentIndex(),
                                  bas_saat=self.h_bas.saat(), bit_saat=self.h_bit.saat(),
                                  aciklama=self.h_aciklama.text())
        except HizmetHatasi as hata:
            self.hata("Kayıt eklenemedi", hata)
            return
        self.h_aciklama.clear()
        self._doldur()

    def _tarihli_ekle(self) -> None:
        bas = self.t_bas_tarih.tarih()
        try:
            hizmet.musaitlik_ekle(self.vt, self.kisi["kimlik"], bas_tarih=bas,
                                  bit_tarih=self.t_bit_tarih.tarih() or bas,
                                  bas_saat=self.t_bas.saat(), bit_saat=self.t_bit.saat(),
                                  aciklama=self.t_aciklama.text())
        except (HizmetHatasi, ValueError) as hata:
            self.hata("Kayıt eklenemedi", hata)
            return
        self.t_aciklama.clear()
        self._doldur()

    def _sil(self) -> None:
        secili = self.tablo.secili_satirlar()
        if not secili:
            self.uyari("Seçim yok", "Silinecek kaydı seçin.")
            return
        for kayit in secili:
            hizmet.musaitlik_sil(self.vt, kayit["kimlik"])
        self._doldur()


# ========================================================== elle personel ekle

class PersonelEklePenceresi(Pencere):
    """Rapora yansımamış kişiyi elle ekler (ör. yeni atanan öğretmen)."""

    UNVANLAR = ("Öğretmen", "Müdür Yardımcısı", "Müdür Başyardımcısı")

    def __init__(self, uyg: "Uygulama"):
        super().__init__(uyg, "Personeli elle ekle", 520, 260)
        izgara = QGridLayout()
        izgara.setVerticalSpacing(10)
        self.ad = QLineEdit()
        self.brans = secim_kutusu()
        self.brans.setEditable(True)
        self.brans.addItems([ad for _, ad, _ in hizmet.brans_havuzu_listele(self.vt)])
        self.brans.setCurrentText("")
        self.unvan = secim_kutusu()
        self.unvan.addItems(self.UNVANLAR)
        for satir, (ad, girdi) in enumerate((("Adı Soyadı", self.ad), ("Branşı", self.brans),
                                             ("Görevi", self.unvan))):
            izgara.addWidget(QLabel(ad), satir, 0)
            izgara.addWidget(girdi, satir, 1)
        self.duzen.addLayout(izgara)
        self.duzen.addWidget(etiket("Kişi e-Okul raporunda yoksa pasife alınmaz; elle eklendiği "
                                    "listede görünür.", "Soluk", sar=True))
        self.duzen.addStretch(1)
        self.duzen.addLayout(yatay(0, dugme("Vazgeç", tiklaninca=self.reject),
                                   dugme("Ekle", "ana", "ekle", tiklaninca=self.ekle)))
        self.eklenen: int | None = None

    def ekle(self) -> None:
        try:
            self.eklenen = hizmet.personel_ekle(self.vt, self.ad.text(), self.brans.currentText(),
                                                self.unvan.currentText())
        except HizmetHatasi as hata:
            self.hata("Personel eklenemedi", hata)
            return
        self.accept()


# ====================================================== görevli değişikliği

class GorevliDegistirPenceresi(Pencere):
    """Seçili oturumun bir görevlisinin yerine başkasını koyar.

    Taslak planda değişiklik bellekte yapılır ve "Geri al" ile geri alınır;
    kesinleşmiş planda müdür onay numarası ve gerekçe zorunludur, değişiklik
    hemen kaydedilir ve evrakta listelenir.
    """

    def __init__(self, uyg: "Uygulama", plan_sayfasi: Any, oturum_anahtari: str):
        super().__init__(uyg, "Görevliyi değiştir", 920, 640)
        self.plan_sayfasi = plan_sayfasi
        self.plan = plan_sayfasi.plan_sonucu.plan
        self.oturum = self.plan.oturum_bul(oturum_anahtari)
        self.kesin = bool(self.oturum.kilitli_mi)
        self.personel = {p.kimlik: p for p in hizmet.personelleri_getir(self.vt,
                                                                       yalniz_aktif=False)}
        tur = " (uygulama)" if self.oturum.oturum_turu.value == "uygulama" else ""
        self.duzen.addWidget(etiket(
            f"{'/'.join(map(str, self.oturum.duzeyler))} {self.oturum.ders_adi}{tur} • "
            f"{tarih_yaz(self.oturum.tarih)} {self.oturum.saat.strftime('%H:%M')}", "KartBaslik"))
        self.duzen.addWidget(Serit(
            ("Plan kesinleşmiştir: değişiklik müdür onay numarası ve gerekçeyle hemen kaydedilir "
             "ve görevlendirme çizelgesinde listelenir." if self.kesin else
             "Değişiklik plan kaydedilene kadar bellekte kalır; 'Geri al' ile geri alınabilir.")
            + " " + KVKK_UYARISI, "uyari" if self.kesin else "bilgi"))

        self.duzen.addWidget(etiket("1. Değiştirilecek görevli", "Bolum"))
        salonlar = {s.kimlik: s.ad for s in hizmet.salonlari_getir(self.vt)}
        self.mevcut = Tablo(
            [Sutun("Görev", lambda g: ROL_ADLARI[g.rol], 130),
             Sutun("Adı Soyadı", lambda g: self._ad(g.personel_kimligi), 260),
             Sutun("Branşı", lambda g: self._brans(g.personel_kimligi), 200),
             Sutun("Salon", lambda g: salonlar.get(g.salon_kimligi, ""), uzat=True)],
            anahtar=lambda g: f"{g.personel_kimligi}|{g.rol.value}")
        self.mevcut.yukle(self.plan.oturum_gorevleri(oturum_anahtari))
        self.mevcut.setFixedHeight(170)
        self.mevcut.secim_degisti.connect(self.adaylari_doldur)
        self.duzen.addWidget(self.mevcut)

        self.duzen.addWidget(etiket("2. Yerine görevlendirilecek kişi (uygun olanlar üstte)",
                                    "Bolum"))
        self.adaylar = Tablo(
            [Sutun("Adı Soyadı", lambda a: a["ad"], 230), Sutun("Branşı", lambda a: a["brans"], 190),
             Sutun("Alan", lambda a: "evet" if a["alan_mi"] else "", 60, "orta"),
             Sutun("Görev", lambda a: a["gorev_sayisi"], 60, "sag"),
             Sutun("Durum", lambda a: "uygun" if a["uygun_mu"] else a["neden"], uzat=True)],
            anahtar=lambda a: a["kimlik"],
            yazi_rengi=lambda a: None if a["uygun_mu"] else RENK["soluk"],
            bos_metin="Önce yukarıdan değiştirilecek görevliyi seçin.")
        self.duzen.addWidget(self.adaylar, 1)

        self.gerekce = QLineEdit()
        self.gerekce.setPlaceholderText("Gerekçe (ör. izinli)")
        self.onay_no = QLineEdit()
        self.onay_no.setPlaceholderText("Müdür onay no")
        self.onay_no.setVisible(self.kesin)
        self.es_oturum = QCheckBox("Yazılı ve uygulamada birlikte (58/2-e)")
        self.es_oturum.setChecked(True)
        self.es_oturum.setVisible(bool(self.oturum.birim_anahtari))
        self.duzen.addLayout(yatay(self.gerekce, self.onay_no, self.es_oturum, 0,
                                   dugme("Vazgeç", tiklaninca=self.reject),
                                   dugme("Değiştir", "ana", "degistir", tiklaninca=self.degistir)))

    def _ad(self, kimlik: int) -> str:
        kisi = self.personel.get(kimlik)
        return kisi.ad if kisi else str(kimlik)

    def _brans(self, kimlik: int) -> str:
        kisi = self.personel.get(kimlik)
        return kisi.brans if kisi else ""

    def adaylari_doldur(self) -> None:
        gorev = self.mevcut.secili_satir()
        if gorev is None:
            self.adaylar.yukle([])
            return
        self.adaylar.yukle(hizmet.gorevli_adaylari(self.vt, self.plan, self.oturum.anahtar,
                                                   gorev.rol, gorev.personel_kimligi),
                           secimi_koru=False)

    def degistir(self) -> None:
        gorev, aday = self.mevcut.secili_satir(), self.adaylar.secili_satir()
        if gorev is None or aday is None:
            self.uyari("Seçim yok", "Önce değiştirilecek görevliyi, sonra yerine gelecek kişiyi "
                                    "seçin.")
            return
        try:
            if self.kesin:
                sonuc = hizmet.kesin_plan_gorevli_degistir(
                    self.vt, self.plan_sayfasi.aktif_plan_id, self.oturum.anahtar,
                    gorev.personel_kimligi, aday["kimlik"], self.onay_no.text(),
                    self.gerekce.text(), self.es_oturum.isChecked())
                goruntu = None
            else:
                goruntu = hizmet.plan_anlik_goruntusu(self.plan)
                sonuc = hizmet.gorevli_degistir(
                    self.vt, self.plan, self.oturum.anahtar, gorev.personel_kimligi,
                    aday["kimlik"], self.plan_sayfasi.plan_sonucu.yukseltilen_sinirlar,
                    self.gerekce.text(), self.es_oturum.isChecked())
        except HizmetHatasi as hata:
            self.hata("Görevli değiştirilemedi", hata)
            return
        if not sonuc.uygulandi:
            self.uyari("Değişiklik yapılamadı", sonuc.mesaj())
            return
        self.plan_sayfasi.gorevli_degisti(self.oturum.anahtar, goruntu, self.kesin)
        self.accept()


# ==================================================== tek ders sınavı seçimi

class TekDersPenceresi(Pencere):
    """OKY md.58/6 tek ders sınavına girecek öğrenci ve dersin seçimi."""

    def __init__(self, uyg: "Uygulama", pencere_kodu: str):
        super().__init__(uyg, "Tek ders sınavı öğrencileri", 900, 600)
        self.kod = pencere_kodu
        self.duzen.addWidget(etiket(
            "OKY md.58/6: sorumluluk sınavı sonunda tek dersten başarısızlığı bulunan son sınıf "
            "öğrencileri için aynı usulle takip eden hafta içinde bir sınav daha yapılır. Program "
            "sınav sonuçlarını bilmez; e-Okul'daki sonuçlara bakarak öğrencinin başarısız kaldığı "
            "tek dersi işaretleyin. Listede bu dönemin planındaki 12. sınıf öğrencileri vardır.",
            "Soluk", sar=True))
        self.arama = AramaKutusu("Öğrenci, numara ya da ders ara…")
        self.ozet = cip()
        self.duzen.addLayout(yatay(self.arama, 0, self.ozet))
        self.tablo = Tablo(
            [Sutun("Tek ders", lambda s: "", 80, onay=lambda s: s["secili_mi"]),
             Sutun("Okul no", lambda s: s["okul_no"], 90),
             Sutun("Adı Soyadı", lambda s: s["ad_soyad"], 240),
             Sutun("Şube", lambda s: s["sube"], 80),
             Sutun("Ders", lambda s: f"{s['duzey']}. sınıf {s['ders']}", uzat=True)],
            anahtar=lambda s: s["sorumluluk_kaydi_id"],
            zemin=lambda s: RENK["basari_zemin"] if s["secili_mi"] else None,
            bos_metin="Bu dönemin kayıtlı planında 12. sınıf öğrencisi yok. Önce olağan planı "
                      "kaydedin.")
        self.tablo.aramaya_bagla(self.arama)
        self.tablo.onay_degisti.connect(self.secimi_degistir)
        self.tablo.cift_tiklandi.connect(lambda s: self.secimi_degistir(s, 0, not s["secili_mi"]))
        self.duzen.addWidget(self.tablo, 1)
        self.duzen.addLayout(yatay(0, dugme("Kapat", "ana", tiklaninca=self.accept)))
        self._doldur()

    def _doldur(self) -> None:
        satirlar = hizmet.tek_ders_adaylari(self.vt, self.kod)
        self.tablo.yukle(satirlar)
        secili = sum(1 for s in satirlar if s["secili_mi"])
        self.ozet.setText(f"{secili} öğrenci seçili")

    def secimi_degistir(self, satir: dict, _sutun: int = 0, sec: bool = True) -> None:
        try:
            hizmet.tek_ders_sec(self.vt, self.kod, satir["ogrenci_id"],
                                satir["sorumluluk_kaydi_id"] if sec else None)
        except HizmetHatasi as hata:
            self.hata("Seçim kaydedilemedi", hata)
            return
        self._doldur()


# =================================================== numara listesiyle işaret

class NumaraListesiPenceresi(Pencere):
    """e-Okul'dan alınan okul numaralarıyla beklemeli/devamsız işaretini topluca koyar.

    Önce önizleme gösterilir; bulunamayan ya da birden çok kayıtla eşleşen
    numara işaretlenmez, satırda nedeni yazar.
    """

    TURLER = (("mezun_olamayan", "Mezun olamayan 12. sınıf (beklemeli)"),
              ("devamsizlik_tebligati", "Devamsızlık tebligatı yapıldı"))
    DURUMLAR = {"bulundu": "bulundu", "bulunamadi": "bulunamadı",
                "birden_cok": "birden çok kayıt — tabloda elle işaretleyin",
                "sorumlulugu_yok": "aktif sorumluluk kaydı yok"}

    def __init__(self, uyg: "Uygulama"):
        super().__init__(uyg, "Numara listesiyle işaretle", 860, 640)
        self.duzen.addWidget(etiket(
            "Okul numaralarını yapıştırın: her satıra bir numara ya da virgülle ayrılmış liste. "
            "e-Okul'dan ad ve şubeyle birlikte kopyalanan satırlar da olur; yalnız rakamdan oluşan "
            "parçalar numara sayılır.", "Soluk", sar=True))
        self.metin = QPlainTextEdit()
        self.metin.setPlaceholderText("12101\n12102, 12115\n12130 Adı Soyadı 12/A")
        self.metin.setFixedHeight(120)
        self.duzen.addWidget(self.metin)
        self.tur = secim_kutusu()
        for _, ad in self.TURLER:
            self.tur.addItem(ad)
        self.islem = secim_kutusu()
        self.islem.addItems(["İşaret koy", "İşareti kaldır"])
        self.duzen.addLayout(yatay(QLabel("İşaret"), self.tur, self.islem, 0,
                                   dugme("Önizle", "", "liste", tiklaninca=self.onizle)))
        self.tablo = Tablo(
            [Sutun("No", lambda s: s["no"], 90), Sutun("Adı Soyadı", lambda s: s["ad_soyad"], 240),
             Sutun("Şube", lambda s: s["sube"], 110),
             Sutun("Durum", lambda s: self._durum(s), uzat=True)],
            anahtar=lambda s: s["no"],
            zemin=lambda s: None if s["durum"] == "bulundu" else RENK["uyari_zemin"],
            bos_metin="Numaraları yazıp Önizle'ye basın.")
        self.duzen.addWidget(self.tablo, 1)
        self.ozet = etiket("", "Soluk")
        self.uygula_dugmesi = dugme("Uygula", "ana", "onay", tiklaninca=self.uygula)
        self.uygula_dugmesi.setEnabled(False)
        self.duzen.addLayout(yatay(self.ozet, 0, dugme("Vazgeç", tiklaninca=self.reject),
                                   self.uygula_dugmesi))
        self.satirlar: list[dict] = []
        self.degisen = 0

    def _alan(self) -> str:
        return self.TURLER[self.tur.currentIndex()][0]

    def _durum(self, satir: dict) -> str:
        if satir["durum"] != "bulundu":
            return self.DURUMLAR[satir["durum"]]
        isaretli = satir["mezun_olamayan_mi" if self._alan() == "mezun_olamayan"
                         else "devamsizlik_tebligati_mi"]
        koy = self.islem.currentIndex() == 0
        if isaretli == koy:
            return "zaten " + ("işaretli" if koy else "işaretsiz")
        return "işaretlenecek" if koy else "işareti kaldırılacak"

    def onizle(self) -> None:
        self.satirlar = hizmet.numara_listesini_coz(self.vt, self.metin.toPlainText())
        self.tablo.yukle(self.satirlar, secimi_koru=False)
        bulunan = sum(1 for s in self.satirlar if s["durum"] == "bulundu")
        self.ozet.setText(f"{len(self.satirlar)} numara okundu, {bulunan} öğrenci bulundu."
                          if self.satirlar else "Metinde okul numarası bulunamadı.")
        self.uygula_dugmesi.setEnabled(bulunan > 0)

    def uygula(self) -> None:
        kimlikler = [s["ogrenci_id"] for s in self.satirlar if s["durum"] == "bulundu"]
        if not kimlikler:
            return
        deger = self.islem.currentIndex() == 0
        try:
            self.degisen = hizmet.ogrenci_bayraklarini_toplu_guncelle(
                self.vt, kimlikler, **{self._alan(): deger})
        except HizmetHatasi as hata:
            self.hata("İşaretlenemedi", hata)
            return
        self.accept()


# =========================================================== yük çözümlemesi

class YukCozumlemePenceresi(Pencere):
    """Gün sayısı seçeneklerinin öğrenci sınırlarına etkisi, plan üretmeden önce."""

    def __init__(self, uyg: "Uygulama", ozet: Any, slot_sayisi: int):
        super().__init__(uyg, "Öğrenci yükü çözümlemesi", 760, 460)
        sayilar = QGridLayout()
        for sira, (ad, deger) in enumerate((
                ("Öğrenci", len(ozet.ogrenci_yukleri)),
                ("Çoğunluğun sınav yükü", ozet.cogunluk_yuku),
                ("En yüklü öğrenci", ozet.azami_yuk),
                ("Önerilen gün sayısı", ozet.onerilen_gun_sayisi(slot_sayisi)))):
            kutu = QVBoxLayout()
            kutu.addWidget(etiket(str(deger), "Deger"))
            kutu.addWidget(etiket(ad, "Soluk"))
            sayilar.addLayout(kutu, 0, sira)
        self.duzen.addLayout(sayilar)
        self.duzen.addWidget(etiket(
            f"Bir öğrenci günde en çok {GUNLUK_SINAV_TAVANI} sınava girebilir; ikiyi geçmemesi "
            "esastır (ÖDY md.5/1-k). Kısa takvimde sığmayan öğrencinin sınırı yükseltilir.",
            "Soluk", sar=True))
        tablo = Tablo([Sutun("Gün sayısı", lambda o: o.gun_sayisi, 100, "sag"),
                       Sutun("Sınırı yükselen", lambda o: o.etkilenen_ogrenci_sayisi, 130, "sag"),
                       Sutun("En yüksek sınır", lambda o: o.en_yuksek_sinir or "—", 130, "sag"),
                       Sutun("Sonuç", lambda o: o.ozet(), uzat=True)],
                      anahtar=lambda o: o.gun_sayisi,
                      zemin=lambda o: None if o.uygulanabilir_mi else RENK["engel_zemin"])
        tablo.yukle(sinir_onizlemesi(ozet, [5, 10, 14, ozet.onerilen_gun_sayisi(slot_sayisi)],
                                     slot_sayisi))
        self.duzen.addWidget(tablo, 1)
        self.duzen.addLayout(yatay(0, dugme("Kapat", "ana", tiklaninca=self.accept)))


__all__ = ["GorevliDegistirPenceresi", "MusaitlikPenceresi", "NumaraListesiPenceresi",
           "Pencere", "PersonelEklePenceresi", "TekDersPenceresi", "YukCozumlemePenceresi"]
