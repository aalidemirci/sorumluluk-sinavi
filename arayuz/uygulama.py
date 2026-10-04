"""Ana pencere (Qt).

Adımlar soldaki şeritte sıralıdır (bkz. ADIMLAR). Arayüz SQL yazmaz, kural
bilmez; her şeyi `veri.hizmet` üzerinden yapar. Sayfalar `arayuz.sayfalar`
altındadır ve ilk açıldıklarında kurulur, sonra yaşamaya devam eder.

Karar 0016: arayüz Tkinter'dan Qt'ye (PySide6) taşındı. Karar 0015:
pencere açıldıktan sonra arka planda bir kez yayımlanan son sürüme bakılır;
ağ yoksa sessiz kalınır.
"""

from __future__ import annotations

import importlib
import logging
import os
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, Callable

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from arayuz.bilesenler import (
    Bildirim, Iletisim, MesgulOrtusu, Serit, arka_planda, etiket, suren_is_var_mi,
)
from arayuz.palet import RENK
from arayuz.simgeler import pixmap, simge
from cekirdek.kaynak import varlik_yolu
from cekirdek.surum import SURUM
from veri import guncelleme
from veri.hizmet import HizmetHatasi
from veri.rapor_okuma import RaporHatasi
from veri.veritabani import Veritabani

# (no, ad, açıklama, simge). Sıra çalışma akışıdır; testler ve site ekranları
# sayfaları adıyla bulur, sıra numarasıyla değil.
ADIMLAR = (
    ("01", "Kurum Ayarları", "Okul bilgileri, dönem tarihleri ve tatil günleri", "kurum"),
    ("02", "Öğretmen Listesi", "e-Okul OOK01001R1 personel raporu ve öğretmen müsaitliği",
     "ogretmen"),
    ("03", "Salonlar", "Sınav salonları ve kapasiteleri", "salon"),
    ("04", "e-Okul Sorumluluk", "OOK12001R010 sorumluluk raporu", "rapor"),
    ("05", "Başvuru", "Beklemeli ve devamsız öğrencilerin başvuruları — OKY md.58/2-d",
     "basvuru"),
    ("06", "Ders / Branş", "Alan eşleştirme ve iki aşamalı dersler", "ders"),
    ("07", "Sınav Planı", "Plan üretme, düzenleme ve kesinleştirme", "plan"),
    ("08", "Evrak ve Teslim", "Belge üretimi ve sınav evrakının teslim takibi", "evrak"),
    ("09", "Yardım", "Mevzuat hükümleri, kullanım ve çalışma mantığı", "yardim"),
    ("10", "Hakkında", "Sürüm, güncelleme ve kullanım koşulları", "bilgi"),
)
# Bu sıradan itibaren adımlar "bilgi" başlığı altında gösterilir.
BILGI_BASLANGICI = 8
# Sayfa modülü ve sınıfı; modül sayfa ilk açıldığında yüklenir.
SAYFA_SINIFLARI = (
    ("kurum", "KurumSayfasi"), ("personel", "PersonelSayfasi"), ("salon", "SalonSayfasi"),
    ("sorumluluk", "SorumlulukSayfasi"), ("basvuru", "BasvuruSayfasi"), ("ders", "DersSayfasi"),
    ("plan", "PlanSayfasi"), ("evrak", "EvrakSayfasi"), ("yardim", "YardimSayfasi"),
    ("hakkinda", "HakkindaSayfasi"),
)


def sayfa_sirasi(ad: str) -> int:
    return next(i for i, adim in enumerate(ADIMLAR) if adim[1] == ad)


def veri_klasoru() -> Path:
    """Veritabanının bulunduğu klasör.

    Alt klasör adı bilinçli olarak "plan": önceki sürümün veritabanı
    `…/SorumlulukSinavi/veri` altındadır ve şeması bununla uyuşmaz. Ayrı
    klasör, eski dosyaya hiç dokunmadan yan yana durmayı sağlar.
    """
    ozel = os.environ.get("SORUMLULUK_VERI_KLASORU")
    if ozel:
        return Path(ozel)
    if os.name == "nt":
        taban = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return taban / "SorumlulukSinavi" / "plan"
    return Path.home() / ".local" / "share" / "sorumluluk-sinavi" / "plan"


def kurum_denetimi_kapatmis_mi() -> bool:
    """SORUMLULUK_GUNCELLEME_DENETIMI=0: kurum politikası (ya da testler)."""
    return os.environ.get("SORUMLULUK_GUNCELLEME_DENETIMI", "1").strip() == "0"


def beklenmeyen_hata_kancasi(
        pencere: "Uygulama") -> Callable[[type[BaseException], BaseException,
                                           TracebackType | None], None]:
    """sys.excepthook yerine geçen işlev.

    Sayfalar beklenen hatayı kendisi gösterir, beklenmeyeni yeniden fırlatır.
    Qt yuvasında fırlatılan hata yalnız stderr'e yazılır; paketlenmiş
    programda konsol olmadığı için kullanıcı hiçbir şey görmüyordu (Tk
    sürümünde de böyleydi). Günlüğe çağrı yığını ve hata türü yazılır; hata
    iletisi öğrenci adı taşıyabileceği için yazılmaz (KVKK), yalnız ekranda
    gösterilir.
    """
    def kanca(tur: type[BaseException], deger: BaseException,
              iz: TracebackType | None) -> None:
        logging.error("Beklenmeyen hata: %s\n%s", tur.__name__,
                      "".join(traceback.format_tb(iz)).rstrip())
        try:
            pencere.mesgul_kapat()
            pencere.ileti.hata(
                "Beklenmeyen hata",
                f"İşlem tamamlanamadı: {deger or tur.__name__}\n\nSorun sürerse veri "
                "klasöründeki uygulama.log dosyasını geliştiriciye iletin; dosya kişisel "
                "veri içermez.")
        except Exception:                              # pragma: no cover
            logging.exception("Hata penceresi gösterilemedi")
    return kanca


def acilis_denetimi_acik_mi(ayarlar: QSettings) -> bool:
    """Ortam değişkeni kullanıcı tercihinden önce gelir."""
    if kurum_denetimi_kapatmis_mi():
        return False
    return bool(ayarlar.value("guncelleme/acilista_denetle", True, type=bool))


class Uygulama(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sorumluluk Sınavı • Planlama ve Görevlendirme")
        logo = varlik_yolu("logo.png")
        if logo is not None:
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(logo)))

        klasor = veri_klasoru()
        klasor.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=klasor / "uygulama.log", level=logging.INFO, encoding="utf-8",
            format="%(asctime)s %(levelname)s %(message)s")
        self.vt = Veritabani(klasor / "sorumluluk.db")
        self.vt.gocleri_uygula()
        # Arayüz tercihleri (pencere boyutu, son klasör, ertelenen sürüm)
        # veri klasöründe durur; kayıt defterine ya da başka yere yazılmaz.
        self.ayarlar = QSettings(str(klasor / "arayuz.ini"), QSettings.Format.IniFormat)
        self.ileti = Iletisim(self)
        self.guncelleme_durumu: dict[str, Any] | None = None
        self.sayfalar: dict[int, QWidget] = {}
        self.etkin_sira = -1

        self._kabuk()
        self._kisayollar()
        self._boyutlandir()
        self.sayfa_goster(0)
        QTimer.singleShot(2500, self._eski_kurulumlari_temizle)
        QTimer.singleShot(2500, self._acilis_guncelleme_denetimi)

    # ------------------------------------------------------------------ kabuk
    def _kabuk(self) -> None:
        govde = QWidget()
        duzen = QHBoxLayout(govde)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(0)
        duzen.addWidget(self._kenar_cubugu())

        self.icerik = QWidget()
        self.icerik.setObjectName("Icerik")
        icerik_duzeni = QVBoxLayout(self.icerik)
        icerik_duzeni.setContentsMargins(28, 22, 28, 20)
        icerik_duzeni.setSpacing(12)

        self.guncelleme_seridi = Serit("", "bilgi", kapatilabilir=False)
        self.guncelleme_seridi.dugme_ekle("Ayrıntılar",
                                          lambda: self.sayfa_goster(sayfa_sirasi("Hakkında")))
        self.guncelleme_seridi.dugme_ekle("Daha sonra", self._guncellemeyi_ertele)
        self.guncelleme_seridi.hide()
        icerik_duzeni.addWidget(self.guncelleme_seridi)

        self.baslik = etiket("", "SayfaBaslik")
        self.alt_baslik = etiket("", "SayfaAlt")
        icerik_duzeni.addWidget(self.baslik)
        icerik_duzeni.addWidget(self.alt_baslik)
        icerik_duzeni.addSpacing(4)
        self.yigin = QStackedWidget()
        icerik_duzeni.addWidget(self.yigin, 1)
        duzen.addWidget(self.icerik, 1)
        self.setCentralWidget(govde)

        self.bildirim = Bildirim(self.icerik)
        self.mesgul = MesgulOrtusu(self.icerik)

    def _kenar_cubugu(self) -> QFrame:
        kenar = QFrame()
        kenar.setObjectName("KenarCubugu")
        kenar.setFixedWidth(236)
        duzen = QVBoxLayout(kenar)
        duzen.setContentsMargins(0, 18, 0, 14)
        duzen.setSpacing(0)

        marka = QHBoxLayout()
        marka.setContentsMargins(18, 0, 14, 6)
        marka.setSpacing(10)
        logo = varlik_yolu("logo.png")
        if logo is not None:
            from PySide6.QtGui import QPixmap
            simge_etiketi = QLabel()
            resim = QPixmap(str(logo))
            if not resim.isNull():
                simge_etiketi.setPixmap(resim.scaled(
                    36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                marka.addWidget(simge_etiketi)
        adlar = QVBoxLayout()
        adlar.setSpacing(0)
        adlar.addWidget(etiket("Sorumluluk Sınavı", "Marka"))
        adlar.addWidget(etiket(f"Sürüm {SURUM}", "MarkaAlt"))
        marka.addLayout(adlar, 1)
        duzen.addLayout(marka)

        self.nav_grubu = QButtonGroup(self)
        self.nav_grubu.setExclusive(True)
        self.nav: list[QPushButton] = []
        duzen.addWidget(etiket("ÇALIŞMA AKIŞI", "KenarBaslik"))
        for sira, (no, ad, aciklama, simge_adi) in enumerate(ADIMLAR):
            if sira == BILGI_BASLANGICI:
                duzen.addWidget(etiket("BİLGİ", "KenarBaslik"))
            dugme = QPushButton(f"  {ad}")
            dugme.setObjectName("NavDugme")
            dugme.setCheckable(True)
            dugme.setIcon(simge(simge_adi, RENK["panel_soluk"], 18))
            dugme.setIconSize(QSize(18, 18))
            dugme.setToolTip(f"{no} • {aciklama}  (Ctrl+{int(no) % 10})")
            dugme.setCursor(Qt.CursorShape.PointingHandCursor)
            dugme.clicked.connect(lambda _=False, s=sira: self.sayfa_goster(s))
            self.nav_grubu.addButton(dugme, sira)
            self.nav.append(dugme)
            duzen.addWidget(dugme)
        duzen.addStretch(1)

        alt = QFrame()
        alt.setObjectName("KenarAlt")
        alt_duzen = QVBoxLayout(alt)
        alt_duzen.setContentsMargins(12, 9, 12, 10)
        alt_duzen.setSpacing(2)
        ust = QHBoxLayout()
        ust.setSpacing(6)
        nokta = QLabel()
        nokta.setPixmap(pixmap("basari", RENK["vurgu2"], 14))
        ust.addWidget(nokta)
        ust.addWidget(etiket("Çevrimdışı çalışır", "KenarAltBaslik"), 1)
        alt_duzen.addLayout(ust)
        alt_duzen.addWidget(etiket("Veriler yalnız bu bilgisayarda", "KenarAltMetin"))
        cerceve = QHBoxLayout()
        cerceve.setContentsMargins(12, 0, 12, 0)
        cerceve.addWidget(alt)
        duzen.addLayout(cerceve)
        return kenar

    def _kisayollar(self) -> None:
        for sira in range(len(ADIMLAR)):
            tus = QKeySequence(f"Ctrl+{(sira + 1) % 10}")
            QShortcut(tus, self, lambda s=sira: self.sayfa_goster(s))
        QShortcut(QKeySequence("F1"), self, lambda: self.sayfa_goster(sayfa_sirasi("Yardım")))
        QShortcut(QKeySequence.StandardKey.Find, self, self._aramaya_git)
        for tus, ad in ((QKeySequence.StandardKey.Save, "kisayol_kaydet"),
                        (QKeySequence.StandardKey.Undo, "kisayol_geri"),
                        (QKeySequence.StandardKey.Redo, "kisayol_ileri"),
                        (QKeySequence("Ctrl+Y"), "kisayol_ileri")):
            QShortcut(tus, self, lambda a=ad: self._sayfaya_ilet(a))

    def _sayfaya_ilet(self, yontem: str) -> None:
        sayfa = self.sayfalar.get(self.etkin_sira)
        if sayfa is not None and hasattr(sayfa, yontem):
            getattr(sayfa, yontem)()

    def _aramaya_git(self) -> None:
        sayfa = self.sayfalar.get(self.etkin_sira)
        kutu = getattr(sayfa, "arama_kutusu", None)
        if kutu is not None and kutu.isVisible():
            kutu.setFocus()
            kutu.selectAll()

    def _boyutlandir(self) -> None:
        """Kayıtlı boyut yoksa ekrana sığdırır; küçük ekranda tam ekran açılır.

        Tk sürümü 1380×860 sabitti ve okullarda yaygın 1366×768 ekrana
        sığmıyordu.
        """
        self.setMinimumSize(1000, 620)
        kayitli = self.ayarlar.value("pencere/geometri")
        if kayitli is not None and self.restoreGeometry(kayitli):
            return
        ekran = QGuiApplication.primaryScreen()
        alan = ekran.availableGeometry() if ekran else None
        if alan is None:
            self.resize(1360, 860)
            return
        genislik = min(1440, alan.width() - 40)
        yukseklik = min(900, alan.height() - 40)
        self.resize(max(genislik, 1000), max(yukseklik, 620))
        if alan.width() < 1500 or alan.height() < 880:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    # ---------------------------------------------------------------- sayfalar
    def sayfa(self, sira: int) -> QWidget:
        """Sayfayı (gerekirse kurarak) döndürür."""
        if sira not in self.sayfalar:
            modul, sinif = SAYFA_SINIFLARI[sira]
            sayfa = getattr(importlib.import_module(f"arayuz.sayfalar.{modul}"), sinif)(self)
            self.sayfalar[sira] = sayfa
            self.yigin.addWidget(sayfa)
        return self.sayfalar[sira]

    def sayfa_goster(self, sira: int) -> None:
        sayfa = self.sayfa(sira)
        self.etkin_sira = sira
        self.nav[sira].setChecked(True)
        for i, dugme in enumerate(self.nav):
            renk = RENK["vurgu_yazi"] if i == sira else RENK["panel_soluk"]
            dugme.setIcon(simge(ADIMLAR[i][3], renk, 18))
        _no, ad, aciklama, _ = ADIMLAR[sira]
        self.baslik.setText(ad)
        self.alt_baslik.setText(aciklama)
        self.yigin.setCurrentWidget(sayfa)
        try:
            sayfa.goster()
        except (HizmetHatasi, RaporHatasi, ValueError, OSError) as hata:
            self.hata_goster(f"{ad} açılamadı", hata)

    # ----------------------------------------------------------- geri bildirim
    def bildir(self, metin: str, eylem_metni: str = "",
               eylem: Callable[[], Any] | None = None) -> None:
        self.bildirim.goster(metin, eylem_metni, eylem)

    def hata_goster(self, baslik: str, hata: BaseException | str, kim: str = "") -> None:
        """Hatayı ekranda gösterir, günlüğe yalnız başlığı ve hata türünü yazar.

        Günlük sorun bildiriminde geliştiriciye gönderilir ve kişisel veri
        içermediği söylenir (KVKK). Bu yüzden ileti günlüğe girmez; başlık da
        sabit olmalıdır. Ad ya da numara `kim` ile yalnız ekrandaki iletiye
        eklenir: "… silinemedi" başlıklarına öğretmen adı konuyordu ve ad
        günlüğe yazılıyordu (04.10.2026).
        """
        logging.warning("%s: %s", baslik, type(hata).__name__ if isinstance(hata, BaseException)
                        else "ileti")
        self.ileti.hata(baslik, f"{kim}: {hata}" if kim else str(hata))

    def mesgul_ac(self, metin: str) -> None:
        self.mesgul.ac(metin)

    def mesgul_kapat(self) -> None:
        self.mesgul.kapat()

    # ------------------------------------------------------------- güncelleme
    def _eski_kurulumlari_temizle(self) -> None:
        """Kurulumdan sonra indirilen dosya önbellekte kalmasın.

        Açılıştan birkaç saniye sonra yapılır: kurulum sihirbazı "Bitti" ile
        programı açtığında kurulum dosyası bir süre daha kilitlidir. Ağa
        çıkmadığı için güncelleme denetimi kapalıyken de yapılır.
        """
        silinen = guncelleme.eski_kurulumlari_temizle()
        if silinen:
            logging.info("Güncelleme önbelleğinden %d eski kurulum dosyası silindi.", silinen)

    def _acilis_guncelleme_denetimi(self) -> None:
        if not acilis_denetimi_acik_mi(self.ayarlar):
            return

        def geldi(durum: dict[str, Any]) -> None:
            # Günlükte yalnız sürüm numaraları durur; sorun bildiriminde
            # denetimin ağa çıkıp çıkamadığı buradan görülür.
            logging.info("Açılış güncelleme denetimi: kurulu %s, yayımlanan %s",
                         durum.get("calisan_surum"), durum.get("son_surum"))
            self.guncelleme_durumu_geldi(durum)

        arka_planda(guncelleme.guncelleme_durumu, geldi,
                    lambda hata: logging.info("Açılış güncelleme denetimi: %s",
                                              type(hata).__name__))

    def guncelleme_durumu_geldi(self, durum: dict[str, Any]) -> None:
        self.guncelleme_durumu = durum
        ertelenen = str(self.ayarlar.value("guncelleme/ertelenen_surum", ""))
        if durum.get("guncelleme_var") and ertelenen != durum.get("son_surum"):
            ek = (" Yeni .deb paketini indirme sayfasından alıp kurun."
                  if durum.get("platform") == "linux" else "")
            self.guncelleme_seridi.ayarla(
                f"Sorumluluk Sınavı {durum['son_surum']} hazır. Kurulu sürüm: "
                f"{durum['calisan_surum']}.{ek}", "bilgi")
            self.guncelleme_seridi.show()
        hakkinda = self.sayfalar.get(sayfa_sirasi("Hakkında"))
        if hakkinda is not None:
            hakkinda.durumu_goster(durum)

    def _guncellemeyi_ertele(self) -> None:
        if self.guncelleme_durumu:
            self.ayarlar.setValue("guncelleme/ertelenen_surum",
                                  self.guncelleme_durumu.get("son_surum", ""))
        self.guncelleme_seridi.hide()

    # ---------------------------------------------------------------- kapanış
    def closeEvent(self, olay: QCloseEvent) -> None:  # noqa: N802
        for sayfa in self.sayfalar.values():
            if not sayfa.kapanabilir_mi():
                olay.ignore()
                return
        if suren_is_var_mi() and not self.ileti.soru(
                "Süren işlem", "Arka planda süren bir işlem var. Bitmesi beklenmeden "
                "kapatılırsa sonucu kaydedilmez. Yine de kapatılsın mı?",
                "Kapat", "Bekle", uyari=True):
            olay.ignore()
            return
        self.ayarlar.setValue("pencere/geometri", self.saveGeometry())
        self.ayarlar.sync()
        super().closeEvent(olay)
