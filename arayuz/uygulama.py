"""Tkinter arayüzü.

Altı adım: Kurum Ayarları → Öğretmen Listesi → Salonlar → e-Okul Sorumluluk
→ Ders/Branş → Sınav Planı. Arayüz SQL yazmaz, kural bilmez; her şeyi
`veri.hizmet` üzerinden yapar.

Sınav Planı ekranında plan bellekte tutulur: sürükle-bırakla düzenlenir,
"Geri Al" ile adım adım geri sarılır ve ancak "Kaydet" ile veritabanına
yazılır.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, filedialog, messagebox, ttk

from cekirdek.kaynak import varlik_yolu
from cekirdek.modeller import IkiAsamaliSayim, PlanParametreleri
from cekirdek.planlayici import PlanlamaBasarisiz, sinir_onizlemesi
from cekirdek.takvim import pencere_adi
from veri import hizmet
from veri.hizmet import HizmetHatasi
from veri.rapor_okuma import RaporHatasi
from veri.veritabani import Veritabani
from evrak import uretici
from . import yardim_metni
from .takvim import SurukleBirakTakvim


RENK = {
    "kenar": "#082642", "kenar2": "#0C3454", "vurgu": "#008E92", "vurgu2": "#09A6AA",
    "zemin": "#F6F8FA", "kart": "#FFFFFF", "yazi": "#142739", "soluk": "#536576",
    "cizgi": "#D6DFE6", "basari": "#168B5C", "uyari": "#B7791F", "engel": "#9B1C1C",
}

ADIMLAR = (
    ("01", "Kurum Ayarları", "Okul bilgileri ve dönem tarihleri"),
    ("02", "Öğretmen Listesi", "e-Okul OOK01001R1 personel raporu"),
    ("03", "Salonlar", "Sınav salonları ve kapasiteleri"),
    ("04", "e-Okul Sorumluluk", "OOK12001R010 sorumluluk raporu"),
    ("05", "Ders / Branş", "Alan eşleştirme ve iki aşamalı dersler"),
    ("06", "Sınav Planı", "Plan üretme, düzenleme ve kesinleştirme"),
    ("07", "Evrak ve Teslim", "Belge üretimi ve sınav evrakının teslim takibi"),
    ("08", "Yardım", "Mevzuat hükümleri, kullanım ve çalışma mantığı"),
    ("09", "Lisans", "Program bilgisi, geliştirici ve kullanım koşulları"),
)

AYAR_ALANLARI = (
    ("okul_adi", "Okul adı"),
    ("mudur_adi", "Müdür adı"),
    ("il", "İl"),
    ("ilce", "İlçe"),
    ("ogretim_yili", "Öğretim yılı (ör. 2026-2027)"),
    ("birinci_donem_baslangic", "1. dönem başlangıcı (YYYY-AA-GG)"),
    ("ikinci_donem_baslangic", "2. dönem başlangıcı (YYYY-AA-GG)"),
    ("ikinci_donem_bitis", "2. dönem bitişi (YYYY-AA-GG)"),
)


SURUM = "0.3.0"


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


class Uygulama:
    def __init__(self) -> None:
        self.kok = tk.Tk()
        self.kok.title("Sorumluluk Sınavı • Planlama ve Görevlendirme")
        self.kok.geometry("1380x860")
        self.kok.minsize(1100, 700)
        self.kok.configure(bg=RENK["zemin"])
        self._simgeyi_uygula()

        klasor = veri_klasoru()
        klasor.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=klasor / "uygulama.log", level=logging.INFO, encoding="utf-8",
            format="%(asctime)s %(levelname)s %(message)s")
        self.vt = Veritabani(klasor / "sorumluluk.db")
        self.vt.gocleri_uygula()

        # Plan ekranının bellekteki durumu
        self.plan_sonucu = None
        self.geri_yigini: list = []
        self.ileri_yigini: list = []
        self.kaydedilmemis = False
        self.aktif_plan_id: int | None = None

        self.personel_ozeti = None
        self.sorumluluk_ozeti = None

        self._stil()
        self._kabuk()
        self._sayfa_goster(0)

    def _simgeyi_uygula(self) -> None:
        """Pencere simgesini logodan ayarlar; logo yoksa sessizce geçilir."""
        try:
            ico = varlik_yolu("logo.ico")
            if ico is not None and os.name == "nt":
                self.kok.iconbitmap(default=str(ico))
                return
            png = varlik_yolu("logo.png")
            if png is not None:
                self._simge = tk.PhotoImage(file=str(png))
                self.kok.iconphoto(True, self._simge)
        except tk.TclError:
            pass

    def calistir(self) -> None:
        self.kok.protocol("WM_DELETE_WINDOW", self._kapat)
        self.kok.mainloop()

    def _kapat(self) -> None:
        if self.kaydedilmemis and not messagebox.askyesno(
                "Kaydedilmemiş plan",
                "Kaydedilmemiş plan değişiklikleri var. Yine de çıkılsın mı?", icon="warning"):
            return
        self.kok.destroy()

    # ------------------------------------------------------------- kabuk

    def _stil(self) -> None:
        s = ttk.Style(self.kok)
        s.theme_use("clam")
        s.configure("TFrame", background=RENK["zemin"])
        s.configure("Kart.TFrame", background=RENK["kart"])
        s.configure("TLabel", background=RENK["zemin"], foreground=RENK["yazi"],
                    font=("Segoe UI", 10))
        s.configure("Kart.TLabel", background=RENK["kart"], foreground=RENK["yazi"],
                    font=("Segoe UI", 10))
        s.configure("Soluk.TLabel", background=RENK["kart"], foreground=RENK["soluk"],
                    font=("Segoe UI", 9))
        s.configure("Baslik.TLabel", background=RENK["zemin"], foreground=RENK["yazi"],
                    font=("Segoe UI Semibold", 19))
        s.configure("KartBaslik.TLabel", background=RENK["kart"], foreground=RENK["yazi"],
                    font=("Segoe UI Semibold", 12))
        s.configure("TEntry", fieldbackground="#FBFCFD", padding=6)
        s.configure("TCombobox", fieldbackground="#FBFCFD", padding=5)
        s.configure("TCheckbutton", background=RENK["kart"], font=("Segoe UI", 9))
        s.configure("Ana.TButton", font=("Segoe UI Semibold", 10), foreground="white",
                    background=RENK["vurgu"], borderwidth=0, padding=(15, 9))
        s.map("Ana.TButton", background=[("active", RENK["vurgu2"]), ("disabled", "#9CC3C4")])
        s.configure("Ikincil.TButton", font=("Segoe UI Semibold", 9),
                    foreground=RENK["yazi"], background="#EAF0F4", borderwidth=0,
                    padding=(12, 7))
        s.configure("Treeview", font=("Segoe UI", 9), rowheight=26,
                    background="white", fieldbackground="white")
        s.configure("Treeview.Heading", font=("Segoe UI Semibold", 9),
                    background="#EAF0F4", padding=6)

    def _kabuk(self) -> None:
        sol = tk.Frame(self.kok, bg=RENK["kenar"], width=232)
        sol.pack(side=LEFT, fill=Y)
        sol.pack_propagate(False)
        marka = tk.Frame(sol, bg=RENK["kenar"], height=78)
        marka.pack(fill=X)
        marka.pack_propagate(False)
        png = varlik_yolu("logo.png")
        if png is not None:
            try:
                self._marka_simgesi = tk.PhotoImage(file=str(png)).subsample(12, 12)
                tk.Label(marka, image=self._marka_simgesi, bg=RENK["kenar"]).pack(
                    side=LEFT, padx=(14, 9), pady=12)
            except tk.TclError:
                png = None
        if png is None:
            tk.Label(marka, text="S", font=("Segoe UI Semibold", 19), fg="white",
                     bg=RENK["vurgu"], width=2).pack(side=LEFT, padx=(15, 9), pady=15)
        tk.Label(marka, text="SORUMLULUK\nSINAVI", justify=LEFT,
                 font=("Segoe UI Semibold", 10), fg="#EFF8FC",
                 bg=RENK["kenar"]).pack(side=LEFT)
        tk.Label(sol, text="ÇALIŞMA AKIŞI", font=("Segoe UI Semibold", 8),
                 fg="#A6C1D3", bg=RENK["kenar"]).pack(anchor="w", padx=17, pady=(12, 6))
        self.nav = []
        for sira, (no, ad, _) in enumerate(ADIMLAR):
            dugme = tk.Button(
                sol, text=f"{no}   {ad}", anchor="w", font=("Segoe UI Semibold", 9),
                fg="#A6C1D3", bg=RENK["kenar"], activeforeground="white",
                activebackground=RENK["kenar2"], bd=0, padx=17, pady=9, cursor="hand2",
                command=lambda x=sira: self._sayfa_goster(x))
            dugme.pack(fill=X, padx=7, pady=1)
            self.nav.append(dugme)
        alt = tk.Frame(sol, bg=RENK["kenar2"])
        alt.pack(side=tk.BOTTOM, fill=X, padx=11, pady=11)
        tk.Label(alt, text="●  Çevrimdışı çalışır", font=("Segoe UI Semibold", 9),
                 fg="#62D5A4", bg=RENK["kenar2"]).pack(anchor="w", padx=9, pady=(8, 0))
        tk.Label(alt, text="Veriler yalnız bu bilgisayarda", font=("Segoe UI", 8),
                 fg="#A6C1D3", bg=RENK["kenar2"]).pack(anchor="w", padx=9, pady=(0, 8))

        sag = tk.Frame(self.kok, bg=RENK["zemin"])
        sag.pack(side=RIGHT, fill=BOTH, expand=True)
        self.icerik = tk.Frame(sag, bg=RENK["zemin"])
        self.icerik.pack(fill=BOTH, expand=True, padx=22, pady=18)

    def _sayfa_goster(self, sira: int) -> None:
        for i, dugme in enumerate(self.nav):
            dugme.configure(bg=RENK["vurgu2"] if i == sira else RENK["kenar"],
                            fg="white" if i == sira else "#A6C1D3")
        for cocuk in self.icerik.winfo_children():
            cocuk.destroy()
        ttk.Label(self.icerik, text=ADIMLAR[sira][1], style="Baslik.TLabel").pack(anchor="w")
        ttk.Label(self.icerik, text=ADIMLAR[sira][2],
                  background=RENK["zemin"], foreground=RENK["soluk"],
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(1, 12))
        (self._sayfa_kurum, self._sayfa_personel, self._sayfa_salon,
         self._sayfa_sorumluluk, self._sayfa_ders, self._sayfa_plan,
         self._sayfa_evrak, self._sayfa_yardim, self._sayfa_lisans)[sira]()

    # --------------------------------------------------------- yardımcılar

    def _kart(self, baslik: str = "", aciklama: str = "") -> tk.Frame:
        kart = tk.Frame(self.icerik, bg=RENK["kart"], highlightthickness=1,
                        highlightbackground=RENK["cizgi"])
        kart.pack(fill=BOTH, expand=True)
        if baslik:
            ttk.Label(kart, text=baslik, style="KartBaslik.TLabel").pack(
                anchor="w", padx=15, pady=(13, 0))
        if aciklama:
            ttk.Label(kart, text=aciklama, style="Soluk.TLabel", wraplength=980,
                      justify=LEFT).pack(anchor="w", padx=15, pady=(2, 5))
        return kart

    @staticmethod
    def _tablo(ana, sutunlar, basliklar, genislikler, yukseklik=12) -> ttk.Treeview:
        sarmal = tk.Frame(ana, bg=RENK["kart"])
        sarmal.pack(fill=BOTH, expand=True, padx=15, pady=(6, 12))
        tablo = ttk.Treeview(sarmal, columns=sutunlar, show="headings", height=yukseklik)
        for sutun, baslik, genislik in zip(sutunlar, basliklar, genislikler):
            tablo.heading(sutun, text=baslik)
            tablo.column(sutun, width=genislik, anchor="w")
        kaydirma = ttk.Scrollbar(sarmal, orient="vertical", command=tablo.yview)
        tablo.configure(yscrollcommand=kaydirma.set)
        tablo.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill=Y)
        return tablo

    def _hata(self, baslik: str, hata: Exception) -> None:
        logging.warning("%s: %s", baslik, type(hata).__name__)
        messagebox.showerror(baslik, str(hata))

    # ================================================== 01 kurum ayarları

    def _sayfa_kurum(self) -> None:
        kart = self._kart(
            "Okul ve dönem bilgileri",
            "Sınav pencereleri (P1/P2/P3) bu tarihlerden hesaplanır — OKY md.58/2-a.")
        mevcut = hizmet.ayarlari_getir(self.vt)
        cerceve = tk.Frame(kart, bg=RENK["kart"])
        cerceve.pack(fill=X, padx=15, pady=10)
        self.ayar_girdileri = {}
        for sira, (anahtar, etiket) in enumerate(AYAR_ALANLARI):
            satir, sutun = sira // 2, (sira % 2) * 2
            ttk.Label(cerceve, text=etiket, style="Kart.TLabel").grid(
                row=satir, column=sutun, sticky="w", padx=(0, 8), pady=6)
            girdi = ttk.Entry(cerceve, width=34)
            girdi.insert(0, mevcut.get(anahtar, ""))
            girdi.grid(row=satir, column=sutun + 1, sticky="ew", padx=(0, 24), pady=6)
            self.ayar_girdileri[anahtar] = girdi
        cerceve.columnconfigure(1, weight=1)
        cerceve.columnconfigure(3, weight=1)

        alt = tk.Frame(kart, bg=RENK["kart"])
        alt.pack(fill=X, padx=15, pady=(0, 14))
        self.pencere_etiketi = ttk.Label(alt, text="", style="Soluk.TLabel")
        self.pencere_etiketi.pack(side=LEFT)
        ttk.Button(alt, text="Kaydet", style="Ana.TButton",
                   command=self._kurum_kaydet).pack(side=RIGHT)
        self._pencereleri_goster()

    def _pencereleri_goster(self) -> None:
        try:
            pencereler = hizmet.pencereleri_getir(self.vt)
        except HizmetHatasi:
            self.pencere_etiketi.configure(text="Tarihler girilince sınav pencereleri hesaplanır.")
            return
        metin = "   ".join(
            f"{pencere_adi(kod)}: {bas.strftime('%d.%m.%Y')}–{bit.strftime('%d.%m.%Y')}"
            for kod, (bas, bit) in pencereler.items())
        self.pencere_etiketi.configure(text="Sınav pencereleri →  " + metin)

    def _kurum_kaydet(self) -> None:
        try:
            hizmet.ayarlari_kaydet(
                self.vt, {k: g.get() for k, g in self.ayar_girdileri.items()})
            self._pencereleri_goster()
            messagebox.showinfo("Kurum ayarları", "Ayarlar kaydedildi.")
        except HizmetHatasi as hata:
            self._hata("Kurum ayarları kaydedilemedi", hata)

    # =================================================== 02 öğretmen listesi

    def _sayfa_personel(self) -> None:
        kart = self._kart("e-Okul personel listesi")
        self._rapor_ipucu(
            kart, "OOK01001R1 — Kurum Personel Listesi",
            "Öğretmen listesi bu rapordan kurulur; branş havuzu da buradan beslenir. "
            "Önizleme onaylanmadan hiçbir kayıt değişmez.")
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=8)
        ttk.Button(ust, text="Rapor seç ve önizle", style="Ana.TButton",
                   command=self._personel_sec).pack(side=LEFT)
        ttk.Button(ust, text="Farkları onayla", style="Ikincil.TButton",
                   command=self._personel_onayla).pack(side=LEFT, padx=8)
        self.personel_durum = ttk.Label(ust, text="Henüz rapor seçilmedi.", style="Kart.TLabel")
        self.personel_durum.pack(side=LEFT, padx=10)

        self.personel_tablosu = self._tablo(
            kart, ("ad", "unvan", "kadro", "brans", "durum", "gorev"),
            ("Adı Soyadı", "Görevi", "Kadro", "Branşı", "Durum", "Görev"),
            (215, 165, 115, 185, 115, 55), 10)
        for etiket, renk in (("eklenecek", "#E8F6EF"), ("guncellenecek", "#FFF3DC"),
                             ("pasif", "#EEF1F3")):
            self.personel_tablosu.tag_configure(etiket, background=renk)
        self._personel_listesini_doldur()
        self._personel_yonetim_bolumu(kart)

    def _personel_listesini_doldur(self) -> None:
        self.personel_tablosu.delete(*self.personel_tablosu.get_children())
        self.personel_kayitlari = hizmet.personel_ayrintili_liste(self.vt)
        for kisi in self.personel_kayitlari:
            durum = "aktif" if kisi["aktif_mi"] else "pasif"
            self.personel_tablosu.insert(
                "", END, iid=str(kisi["kimlik"]),
                values=(kisi["ad"], kisi["unvan"], kisi["kadro"], kisi["brans"],
                        f"{durum} - {kisi['kaynak']}", kisi["gorev_sayisi"]),
                tags=() if kisi["aktif_mi"] else ("pasif",))

    def _personel_yonetim_bolumu(self, kart: tk.Frame) -> None:
        islem = tk.Frame(kart, bg=RENK["kart"])
        islem.pack(fill=X, padx=15, pady=(0, 6))
        ttk.Button(islem, text="Pasife al / Etkinleştir", style="Ikincil.TButton",
                   command=self._personel_durum_degistir).pack(side=LEFT)
        ttk.Button(islem, text="Listeden sil", style="Ikincil.TButton",
                   command=self._personel_sil).pack(side=LEFT, padx=6)
        ttk.Label(islem, text="Görevi olan kişi silinemez; pasife alınır.",
                  style="Soluk.TLabel").pack(side=LEFT, padx=8)

        ekle = tk.Frame(kart, bg=RENK["kart"])
        ekle.pack(fill=X, padx=15, pady=(0, 12))
        ttk.Label(ekle, text="Elle ekle -  Ad Soyad", style="Kart.TLabel").pack(side=LEFT)
        self.yeni_ad = ttk.Entry(ekle, width=24)
        self.yeni_ad.pack(side=LEFT, padx=4)
        ttk.Label(ekle, text="Branş", style="Kart.TLabel").pack(side=LEFT)
        branslar = [ad for _, ad, _ in hizmet.brans_havuzu_listele(self.vt)]
        self.yeni_brans = ttk.Combobox(ekle, width=22, values=branslar)
        self.yeni_brans.pack(side=LEFT, padx=4)
        ttk.Label(ekle, text="Görevi", style="Kart.TLabel").pack(side=LEFT)
        self.yeni_unvan = ttk.Combobox(
            ekle, width=17, values=("Öğretmen", "Müdür Yardımcısı", "Müdür Başyardımcısı"))
        self.yeni_unvan.current(0)
        self.yeni_unvan.pack(side=LEFT, padx=4)
        ttk.Button(ekle, text="Ekle", style="Ana.TButton",
                   command=self._personel_elle_ekle).pack(side=LEFT, padx=6)

    def _secili_personel(self):
        if not self.personel_tablosu.selection():
            messagebox.showwarning("Seçim yok", "Listeden bir personel seçin.")
            return None
        kimlik = int(self.personel_tablosu.selection()[0])
        return next((k for k in self.personel_kayitlari if k["kimlik"] == kimlik), None)

    def _personel_durum_degistir(self) -> None:
        kisi = self._secili_personel()
        if kisi is None:
            return
        try:
            hizmet.personel_durumu_degistir(self.vt, kisi["kimlik"], not kisi["aktif_mi"])
        except HizmetHatasi as hata:
            self._hata("Durum değiştirilemedi", hata)
            return
        self._personel_listesini_doldur()

    def _personel_sil(self) -> None:
        kisi = self._secili_personel()
        if kisi is None:
            return
        if not messagebox.askyesno(
                "Personeli sil",
                f"{kisi['ad']} listeden silinecek. Devam edilsin mi?", icon="warning"):
            return
        try:
            hizmet.personel_sil(self.vt, kisi["kimlik"])
        except HizmetHatasi as hata:
            self._hata("Silinemedi", hata)
            return
        self._personel_listesini_doldur()

    def _personel_elle_ekle(self) -> None:
        try:
            hizmet.personel_ekle(self.vt, self.yeni_ad.get(), self.yeni_brans.get(),
                                 self.yeni_unvan.get())
        except HizmetHatasi as hata:
            self._hata("Personel eklenemedi", hata)
            return
        self._sayfa_goster(1)

    def _personel_sec(self) -> None:
        yol = filedialog.askopenfilename(
            title="e-Okul personel raporu",
            filetypes=[("e-Okul personel listesi", "*.xls *.xlsx")])
        if not yol:
            return
        try:
            ozet = hizmet.personel_onizle(self.vt, Path(yol))
        except (HizmetHatasi, RaporHatasi) as hata:
            self._hata("Personel raporu okunamadı", hata)
            return
        self.personel_ozeti = ozet
        self.personel_durum.configure(
            text=f"{ozet.toplam} kişi  •  +{ozet.eklenen} yeni  ~{ozet.guncellenen} değişen  "
                 f"={ozet.degismedi} aynı  −{ozet.cikan} pasife alınacak")
        self.personel_tablosu.delete(*self.personel_tablosu.get_children())
        for ad, unvan, kadro, brans, eylem in ozet.satirlar:
            self.personel_tablosu.insert("", END, values=(ad, unvan, kadro, brans, eylem),
                                         tags=(eylem,))
        logging.info("Personel önizleme: %s satır", ozet.toplam)

    def _personel_onayla(self) -> None:
        if not self.personel_ozeti:
            messagebox.showwarning("Eksik işlem", "Önce bir personel raporu seçin.")
            return
        ozet = self.personel_ozeti
        if not messagebox.askyesno(
                "Onay", f"{ozet.eklenen} kişi eklenecek, {ozet.guncellenen} kişi güncellenecek, "
                        f"{ozet.cikan} kişi pasife alınacak.\n\nDevam edilsin mi?"):
            return
        try:
            sonuc = hizmet.personel_onayla(self.vt, ozet.aktarim_id)
            self.personel_ozeti = None
            messagebox.showinfo(
                "Personel listesi",
                f"{sonuc.eklenen} eklendi, {sonuc.guncellenen} güncellendi, "
                f"{sonuc.cikan} pasife alındı.")
            self._sayfa_goster(1)
        except HizmetHatasi as hata:
            self._hata("Onay verilemedi", hata)

    # ========================================================== 03 salonlar

    def _sayfa_salon(self) -> None:
        kart = self._kart(
            "Sınav salonları",
            "Salon sayısı ve kapasitesi, aynı saatte kaç sınav yapılabileceğini belirler. "
            "Bir salona en çok 30 öğrenci konur — OKY md.58/2-b.")
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=8)
        ttk.Label(ust, text="Salon adı", style="Kart.TLabel").pack(side=LEFT)
        ad_girdisi = ttk.Entry(ust, width=22)
        ad_girdisi.pack(side=LEFT, padx=6)
        ttk.Label(ust, text="Kapasite", style="Kart.TLabel").pack(side=LEFT)
        kapasite_girdisi = ttk.Entry(ust, width=7)
        kapasite_girdisi.insert(0, "30")
        kapasite_girdisi.pack(side=LEFT, padx=6)

        def ekle() -> None:
            try:
                hizmet.salon_ekle(self.vt, ad_girdisi.get(), int(kapasite_girdisi.get() or 0))
                self._sayfa_goster(2)
            except (HizmetHatasi, ValueError) as hata:
                self._hata("Salon eklenemedi", hata)

        ttk.Button(ust, text="Ekle / güncelle", style="Ana.TButton",
                   command=ekle).pack(side=LEFT, padx=6)

        salonlar = hizmet.salonlari_getir(self.vt)
        tablo = self._tablo(kart, ("ad", "kapasite"), ("Salon", "Kapasite"), (280, 120))
        for salon in salonlar:
            tablo.insert("", END, iid=str(salon.kimlik), values=(salon.ad, salon.kapasite))

        alt = tk.Frame(kart, bg=RENK["kart"])
        alt.pack(fill=X, padx=15, pady=(0, 12))
        ttk.Label(alt, text=f"Toplam {len(salonlar)} salon, "
                            f"{sum(s.kapasite for s in salonlar)} kişilik kapasite.",
                  style="Soluk.TLabel").pack(side=LEFT)

        def sil() -> None:
            if not tablo.selection():
                messagebox.showwarning("Seçim yok", "Silinecek salonu seçin.")
                return
            try:
                hizmet.salon_sil(self.vt, int(tablo.selection()[0]))
                self._sayfa_goster(2)
            except HizmetHatasi as hata:
                self._hata("Salon silinemedi", hata)

        ttk.Button(alt, text="Seçili salonu sil", style="Ikincil.TButton",
                   command=sil).pack(side=RIGHT)

    # ================================================= 04 e-Okul sorumluluk

    def _sayfa_sorumluluk(self) -> None:
        kart = self._kart("e-Okul sorumluluk kayıtları")
        self._rapor_ipucu(
            kart, "OOK12001R010 — Sorumluluk Sınavına Girecek Öğrenci Listesi",
            "Hangi öğrencinin hangi derslerden sorumlu olduğu bu rapordan okunur. "
            "Rapor okulun tamamını kapsıyorsa, dosyada bulunmayan aktif kayıtlar "
            "pasife alınır.")
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=8)
        ttk.Button(ust, text="Rapor seç ve önizle", style="Ana.TButton",
                   command=self._sorumluluk_sec).pack(side=LEFT)
        ttk.Button(ust, text="Önizlemeyi onayla", style="Ikincil.TButton",
                   command=self._sorumluluk_onayla).pack(side=LEFT, padx=8)
        self.tam_liste = tk.BooleanVar(value=True)
        ttk.Checkbutton(ust, text="Bu rapor okulun tam listesidir",
                        variable=self.tam_liste).pack(side=LEFT, padx=10)
        self.sorumluluk_durum = ttk.Label(ust, text="Henüz dosya seçilmedi.",
                                          style="Kart.TLabel")
        self.sorumluluk_durum.pack(side=LEFT, padx=10)

        self.sorumluluk_tablosu = self._tablo(
            kart, ("no", "ad", "sube", "duzey", "ders", "eylem"),
            ("Okul no", "Adı Soyadı", "Şube", "Düzey", "Ders", "Değişiklik"),
            (90, 220, 90, 70, 250, 110))
        mevcut = hizmet.sorumluluk_kayitlari(self.vt)
        for kayit in mevcut[:2000]:
            self.sorumluluk_tablosu.insert(
                "", END, values=(kayit.okul_no, kayit.ad_soyad, kayit.sube,
                                 kayit.sinif_duzeyi, kayit.ders_adi, "kayıtlı"))
        if mevcut:
            self.sorumluluk_durum.configure(text=f"Kayıtlı {len(mevcut)} sorumluluk kaydı.")

    def _sorumluluk_sec(self) -> None:
        yol = filedialog.askopenfilename(
            title="e-Okul sorumluluk raporu",
            filetypes=[("e-Okul dosyası", "*.xlsx *.xls *.csv")])
        if not yol:
            return
        try:
            ozet = hizmet.sorumluluk_onizle(self.vt, Path(yol))
        except (HizmetHatasi, RaporHatasi) as hata:
            self._hata("Sorumluluk raporu okunamadı", hata)
            return
        self.sorumluluk_ozeti = ozet
        ogrenciler = len({(s[0], s[2]) for s in ozet.satirlar})
        self.sorumluluk_durum.configure(
            text=f"{ozet.toplam} kayıt  •  {ogrenciler} öğrenci  •  +{ozet.eklenen} yeni  "
                 f"~{ozet.guncellenen} değişen  −{ozet.cikan} düşecek")
        self.sorumluluk_tablosu.delete(*self.sorumluluk_tablosu.get_children())
        for satir in ozet.satirlar[:2000]:
            self.sorumluluk_tablosu.insert("", END, values=satir)

    def _sorumluluk_onayla(self) -> None:
        if not self.sorumluluk_ozeti:
            messagebox.showwarning("Eksik işlem", "Önce bir sorumluluk raporu seçin.")
            return
        ozet = self.sorumluluk_ozeti
        uyari = (f"\n\nDosyada bulunmayan {ozet.cikan} aktif kayıt pasife alınacak."
                 if self.tam_liste.get() and ozet.cikan else "")
        if not messagebox.askyesno(
                "Onay", f"{ozet.toplam} kayıt işlenecek.{uyari}\n\nDevam edilsin mi?"):
            return
        try:
            hizmet.sorumluluk_onayla(self.vt, ozet.aktarim_id, self.tam_liste.get())
            self.sorumluluk_ozeti = None
            messagebox.showinfo("İçe aktarma", "Sorumluluk kayıtları güncellendi.")
            self._sayfa_goster(3)
        except HizmetHatasi as hata:
            self._hata("Onay verilemedi", hata)

    # ======================================================= 05 ders / branş

    def _sayfa_ders(self) -> None:
        kart = self._kart(
            "Ders / branş eşleştirme",
            "Her ders bir alan branşına eşlenmeden plan üretilemez. Türk dili ve edebiyatı "
            "ile yabancı dil dersleri iki aşamalı işaretlenir — OKY md.58/2-e.")
        dersler = hizmet.dersleri_listele(self.vt)
        tablo = self._tablo(
            kart, ("ad", "brans", "iki", "kayit"),
            ("Ders", "Branş", "İki aşamalı", "Sorumluluk kaydı"),
            (300, 250, 110, 130), 10)
        tablo.tag_configure("eksik", background="#FFE6E6")
        for kayit in dersler:
            ders_id, ad, brans, iki, _yabanci, kayit_sayisi = kayit[:6]
            esdeger = hizmet.ders_esdeger_branslari(kayit)
            gosterim = " + ".join((brans, *esdeger)) if brans else "— eşlenmedi —"
            tablo.insert("", END, iid=str(ders_id),
                         values=(ad, gosterim, "Evet" if iki else "Hayır", kayit_sayisi),
                         tags=() if brans else ("eksik",))

        havuz = hizmet.brans_havuzu_listele(self.vt)
        branslar = [ad for _, ad, _ in havuz]
        alt = tk.Frame(kart, bg=RENK["kart"])
        alt.pack(fill=X, padx=15, pady=(0, 6))
        ttk.Label(alt, text="Branş", style="Kart.TLabel").pack(side=LEFT)
        brans_secimi = ttk.Combobox(alt, state="readonly", width=26, values=branslar)
        brans_secimi.pack(side=LEFT, padx=5)
        ttk.Label(alt, text="İkinci alan (birleşik ders)", style="Kart.TLabel").pack(side=LEFT)
        esdeger_secimi = ttk.Combobox(alt, state="readonly", width=20, values=["—"] + branslar)
        esdeger_secimi.current(0)
        esdeger_secimi.pack(side=LEFT, padx=5)
        iki_asamali = tk.BooleanVar(value=False)
        ttk.Checkbutton(alt, text="İki aşamalı (yazılı + uygulama)",
                        variable=iki_asamali).pack(side=LEFT, padx=8)

        alt2 = tk.Frame(kart, bg=RENK["kart"])
        alt2.pack(fill=X, padx=15, pady=(0, 12))
        ttk.Label(alt2, text="Karar / gerekçe", style="Kart.TLabel").pack(side=LEFT)
        karar_girdisi = ttk.Entry(alt2, width=46)
        karar_girdisi.insert(0, "Zümre kararı")
        karar_girdisi.pack(side=LEFT, padx=5)

        def secim_degisti(_olay=None) -> None:
            if not tablo.selection():
                return
            ders_id = int(tablo.selection()[0])
            for kayit in dersler:
                kimlik, ad, brans, iki = kayit[0], kayit[1], kayit[2], kayit[3]
                if kimlik != ders_id:
                    continue
                # Branş adının kendisinde eğik çizgi olabilir; ad hiç bölünmez.
                if brans and brans in branslar:
                    brans_secimi.set(brans)
                esdeger = hizmet.ders_esdeger_branslari(kayit)
                esdeger_secimi.set(esdeger[0] if esdeger else "—")
                iki_asamali.set(bool(iki) if brans else hizmet.iki_asamali_onerisi(ad))
                break

        tablo.bind("<<TreeviewSelect>>", secim_degisti)

        def kaydet() -> None:
            try:
                if not tablo.selection():
                    raise HizmetHatasi("Önce bir ders seçin.")
                if not brans_secimi.get():
                    raise HizmetHatasi("Branş havuzundan bir alan seçin.")
                ders_id = int(tablo.selection()[0])
                esdeger = () if esdeger_secimi.get() in ("", "—") else (esdeger_secimi.get(),)
                hizmet.ders_brans_esle(self.vt, ders_id, brans_secimi.get(),
                                       karar_girdisi.get(), esdeger)
                hizmet.ders_ozellik_guncelle(self.vt, ders_id, iki_asamali.get(),
                                             iki_asamali.get())
                self._sayfa_goster(4)
            except HizmetHatasi as hata:
                self._hata("Eşleme kaydedilemedi", hata)

        ttk.Button(alt2, text="Seçili dersi kaydet", style="Ana.TButton",
                   command=kaydet).pack(side=LEFT, padx=8)

        yeni = tk.Frame(kart, bg=RENK["kart"])
        yeni.pack(fill=X, padx=15, pady=(0, 12))
        ttk.Label(yeni, text="Okulda öğretmeni olmayan branş", style="Kart.TLabel").pack(side=LEFT)
        yeni_girdi = ttk.Entry(yeni, width=26)
        yeni_girdi.pack(side=LEFT, padx=5)

        def brans_ekle() -> None:
            try:
                hizmet.brans_havuzu_ekle(self.vt, yeni_girdi.get())
                self._sayfa_goster(4)
            except HizmetHatasi as hata:
                self._hata("Branş eklenemedi", hata)

        ttk.Button(yeni, text="Branş havuzuna ekle", style="Ikincil.TButton",
                   command=brans_ekle).pack(side=LEFT, padx=5)
        eksik = sum(1 for d in dersler if not d[2])
        ttk.Label(yeni,
                  text=(f"{eksik} ders eşlenmedi." if eksik else "Tüm dersler eşlendi."),
                  style="Soluk.TLabel",
                  foreground=RENK["engel"] if eksik else RENK["basari"]).pack(side=RIGHT)

    # ========================================================= 06 sınav planı

    def _sayfa_plan(self) -> None:
        kart = self._kart("Sınav planı")
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=(10, 4))

        try:
            pencereler = hizmet.pencereleri_getir(self.vt)
        except HizmetHatasi as hata:
            ttk.Label(kart, text=str(hata), style="Kart.TLabel",
                      foreground=RENK["engel"]).pack(anchor="w", padx=15, pady=20)
            return

        ttk.Label(ust, text="Pencere", style="Kart.TLabel").pack(side=LEFT)
        self.pencere_secimi = ttk.Combobox(
            ust, state="readonly", width=30,
            values=[f"{pencere_adi(kod)}  {bas.strftime('%d.%m.%Y')}–"
                    f"{bit.strftime('%d.%m.%Y')}"
                    for kod, (bas, bit) in pencereler.items()])
        self.pencere_secimi.current(0)
        self.pencere_secimi.pack(side=LEFT, padx=6)

        self.hafta_sonu = tk.BooleanVar(value=False)
        ttk.Checkbutton(ust, text="Hafta sonu kullanılabilir",
                        variable=self.hafta_sonu).pack(side=LEFT, padx=8)

        ttk.Label(ust, text="Günlük sınav sınırı", style="Kart.TLabel").pack(side=LEFT, padx=(8, 2))
        self.gunluk_sinir = ttk.Spinbox(ust, from_=1, to=8, width=4)
        self.gunluk_sinir.set(2)
        self.gunluk_sinir.pack(side=LEFT)

        ttk.Label(ust, text="Yazılı+uygulama", style="Kart.TLabel").pack(side=LEFT, padx=(10, 2))
        self.sayim_secimi = ttk.Combobox(ust, state="readonly", width=16,
                                         values=("tek sınav sayılır", "ayrı sayılır"))
        self.sayim_secimi.current(0)
        self.sayim_secimi.pack(side=LEFT)

        ust2 = tk.Frame(kart, bg=RENK["kart"])
        ust2.pack(fill=X, padx=15, pady=4)
        ttk.Label(ust2, text="Oturum saatleri", style="Kart.TLabel").pack(side=LEFT)
        self.saat_girdisi = ttk.Entry(ust2, width=42)
        self.saat_girdisi.insert(0, ", ".join(hizmet.VARSAYILAN_SLOT_SAATLERI))
        self.saat_girdisi.pack(side=LEFT, padx=6)
        ttk.Button(ust2, text="Yükü çözümle", style="Ikincil.TButton",
                   command=self._yuku_cozumle).pack(side=LEFT, padx=6)
        ttk.Button(ust2, text="Planı üret", style="Ana.TButton",
                   command=self._plan_uret).pack(side=LEFT, padx=6)

        self.plan_ozet = ttk.Label(kart, text="Parametreleri seçip planı üretin.",
                                   style="Soluk.TLabel", wraplength=1000, justify=LEFT)
        self.plan_ozet.pack(anchor="w", padx=15, pady=(4, 4))

        self.takvim_alani = tk.Frame(kart, bg=RENK["kart"])
        self.takvim_alani.pack(fill=BOTH, expand=True, padx=15, pady=(0, 4))

        self.ihlal_tablosu = ttk.Treeview(
            kart, columns=("kural", "duzey", "aciklama"), show="headings", height=4)
        for sutun, baslik, genislik in (("kural", "Kural", 70), ("duzey", "Düzey", 70),
                                        ("aciklama", "Açıklama", 900)):
            self.ihlal_tablosu.heading(sutun, text=baslik)
            self.ihlal_tablosu.column(sutun, width=genislik, anchor="w")
        self.ihlal_tablosu.tag_configure("ENGEL", background="#FFE6E6")
        self.ihlal_tablosu.tag_configure("UYARI", background="#FFF3DC")
        self.ihlal_tablosu.pack(fill=X, padx=15, pady=(0, 4))

        alt = tk.Frame(kart, bg=RENK["kart"])
        alt.pack(fill=X, padx=15, pady=(0, 12))
        self.geri_dugmesi = ttk.Button(alt, text="◀ Geri Al", style="Ikincil.TButton",
                                       command=self._geri_al, state="disabled")
        self.geri_dugmesi.pack(side=LEFT)
        self.ileri_dugmesi = ttk.Button(alt, text="İleri Al ▶", style="Ikincil.TButton",
                                        command=self._ileri_al, state="disabled")
        self.ileri_dugmesi.pack(side=LEFT, padx=5)
        self.kaydet_dugmesi = ttk.Button(alt, text="Kaydet", style="Ana.TButton",
                                         command=self._plan_kaydet, state="disabled")
        self.kaydet_dugmesi.pack(side=LEFT, padx=12)
        self.onay_girdisi = ttk.Entry(alt, width=18)
        self.onay_girdisi.pack(side=RIGHT, padx=(6, 0))
        ttk.Button(alt, text="Müdür onayıyla kesinleştir", style="Ikincil.TButton",
                   command=self._plan_kesinlestir).pack(side=RIGHT)
        ttk.Label(alt, text="Onay no:", style="Kart.TLabel").pack(side=RIGHT, padx=(0, 4))

        self._son_plani_yukle()

    # ------------------------------------------------- plan yardımcıları

    def _pencere_kodu(self) -> str:
        """Seçili dönemin kısa kodu. Ekranda ay adı yazar, veritabanında kod durur."""
        secili = self.pencere_secimi.get().split()[0]
        return next((kod for kod in ("P1", "P2", "P3") if pencere_adi(kod) == secili),
                    secili)

    def _parametreleri_topla(self) -> PlanParametreleri:
        return PlanParametreleri(
            pencere_kodu=self._pencere_kodu(),
            hafta_sonu_kullan=self.hafta_sonu.get(),
            ogrenci_gunluk_sinav_siniri=int(self.gunluk_sinir.get()),
            iki_asamali_sayim=(IkiAsamaliSayim.TEK if self.sayim_secimi.current() == 0
                               else IkiAsamaliSayim.AYRI),
            slot_saatleri=hizmet.slot_saatlerini_coz(self.saat_girdisi.get()),
        )

    def _yuku_cozumle(self) -> None:
        try:
            parametreler = self._parametreleri_topla()
            ozet = hizmet.yuk_ozetini_getir(
                self.vt, parametreler.iki_asamali_sayim,
                parametreler.ogrenci_gunluk_sinav_siniri)
        except (HizmetHatasi, ValueError) as hata:
            self._hata("Yük çözümlenemedi", hata)
            return
        slot_sayisi = len(parametreler.slot_saatleri)
        satirlar = [
            f"Öğrenci sayısı: {len(ozet.ogrenci_yukleri)}   "
            f"çoğunluğun sınav yükü: {ozet.cogunluk_yuku}   en yüklü öğrenci: {ozet.azami_yuk}",
            f"Önerilen gün sayısı: {ozet.onerilen_gun_sayisi(slot_sayisi)}",
            "",
        ]
        for onizleme in sinir_onizlemesi(ozet, [5, 10, 14], slot_sayisi):
            satirlar.append("  " + onizleme.ozet())
        messagebox.showinfo("Öğrenci yükü çözümlemesi", "\n".join(satirlar))

    def _plan_uret(self) -> None:
        if self.kaydedilmemis and not messagebox.askyesno(
                "Kaydedilmemiş plan",
                "Kaydedilmemiş değişiklikler var; yeni plan bunların yerine geçecek. "
                "Devam edilsin mi?", icon="warning"):
            return
        try:
            parametreler = self._parametreleri_topla()
            self.kok.configure(cursor="watch")
            self.kok.update_idletasks()
            sonuc = hizmet.plan_hazirla(self.vt, parametreler)
        except (HizmetHatasi, PlanlamaBasarisiz, ValueError) as hata:
            self._hata("Plan üretilemedi", hata)
            return
        finally:
            self.kok.configure(cursor="")
        self.plan_sonucu = sonuc
        self.geri_yigini.clear()
        self.ileri_yigini.clear()
        self.kaydedilmemis = True
        self.aktif_plan_id = None
        self._takvimi_ciz()

    def _son_plani_yukle(self) -> None:
        plan_id = hizmet.son_plani_getir(self.vt, self._pencere_kodu())
        if plan_id is None:
            return
        try:
            plan, bilgi = hizmet.plan_yukle(self.vt, plan_id)
        except HizmetHatasi:
            return
        from cekirdek.planlayici import PlanlamaSonucu
        sinirlar = bilgi["kisisel_sinirlar"]
        ihlaller = hizmet.plani_dogrula(self.vt, plan, sinirlar)
        self.plan_sonucu = PlanlamaSonucu(plan, ihlaller, sinirlar,
                                          len({o.tarih for o in plan.oturumlar}))
        self.aktif_plan_id = plan_id
        self.kaydedilmemis = False
        self._takvimi_ciz()

    def _takvimi_ciz(self) -> None:
        for cocuk in self.takvim_alani.winfo_children():
            cocuk.destroy()
        if not self.plan_sonucu:
            return
        plan = self.plan_sonucu.plan
        try:
            bas, bit = hizmet.pencereleri_getir(self.vt)[plan.parametreler.pencere_kodu]
        except HizmetHatasi:
            return
        from cekirdek.takvim import gunleri_listele
        gunler = gunleri_listele(bas, bit, plan.parametreler.hafta_sonu_kullan)
        saatler = sorted({o.saat for o in plan.oturumlar}
                         | set(plan.parametreler.slot_saatleri))
        kartlar = [{
            "anahtar": o.anahtar,
            "baslik": ("/".join(str(d) for d in o.duzeyler) + " " + o.ders_adi
                       + (" (uyg.)" if o.oturum_turu.value == "uygulama" else "")),
            "tarih": o.tarih, "saat": o.saat, "tur": o.oturum_turu.value,
            "kilitli": o.kilitli_mi,
        } for o in plan.oturumlar]
        SurukleBirakTakvim(self.takvim_alani, gunler, saatler, kartlar,
                           self._kart_birakildi).pack(fill=BOTH, expand=True)
        self._ozeti_tazele()

    def _ozeti_tazele(self) -> None:
        sonuc = self.plan_sonucu
        plan = sonuc.plan
        ihlaller = hizmet.plani_dogrula(self.vt, plan, sonuc.yukseltilen_sinirlar)
        sonuc.ihlaller = ihlaller
        engel = sum(1 for i in ihlaller if i.engel_mi)
        gunler = sorted({o.tarih for o in plan.oturumlar})
        durum = "kaydedilmedi" if self.kaydedilmemis else f"kayıtlı (#{self.aktif_plan_id})"
        satir = (f"{len(plan.oturumlar)} oturum  •  {len(gunler)} gün "
                 f"({gunler[0].strftime('%d.%m.%Y')} – {gunler[-1].strftime('%d.%m.%Y')})  •  "
                 f"{len(plan.gorevlendirmeler)} görev  •  {engel} engel, "
                 f"{len(ihlaller) - engel} uyarı  •  {durum}")
        if sonuc.yukseltilen_sinirlar:
            satir += f"\nGünlük sınırı yükseltilen öğrenci: {len(sonuc.yukseltilen_sinirlar)}"
        for not_metni in sonuc.notlar[:3]:
            satir += "\n" + not_metni
        self.plan_ozet.configure(text=satir)

        self.ihlal_tablosu.delete(*self.ihlal_tablosu.get_children())
        for ihlal in ihlaller[:200]:
            self.ihlal_tablosu.insert(
                "", END, values=(ihlal.kural_kimligi, ihlal.ciddiyet.value, ihlal.aciklama),
                tags=(ihlal.ciddiyet.value,))
        self.geri_dugmesi.configure(state="normal" if self.geri_yigini else "disabled")
        self.ileri_dugmesi.configure(state="normal" if self.ileri_yigini else "disabled")
        self.kaydet_dugmesi.configure(state="normal" if self.kaydedilmemis else "disabled")

    def _kart_birakildi(self, anahtar: str, tarih: date, saat) -> None:
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
            self._hata("Oturum taşınamadı", hata)
            return
        if not sonuc.uygulandi:
            messagebox.showwarning(
                "Taşıma yapılamadı",
                f"{oturum.ders_adi} sınavı {tarih.strftime('%d.%m.%Y')} "
                f"{saat.strftime('%H:%M')} saatine taşınamadı.\n\n" + sonuc.mesaj())
            return
        self.geri_yigini.append(goruntu)
        self.ileri_yigini.clear()
        self.kaydedilmemis = True
        self._takvimi_ciz()

    def _geri_al(self) -> None:
        if not self.geri_yigini or not self.plan_sonucu:
            return
        self.ileri_yigini.append(hizmet.plan_anlik_goruntusu(self.plan_sonucu.plan))
        hizmet.plani_geri_yukle(self.plan_sonucu.plan, self.geri_yigini.pop())
        self.kaydedilmemis = True
        self._takvimi_ciz()

    def _ileri_al(self) -> None:
        if not self.ileri_yigini or not self.plan_sonucu:
            return
        self.geri_yigini.append(hizmet.plan_anlik_goruntusu(self.plan_sonucu.plan))
        hizmet.plani_geri_yukle(self.plan_sonucu.plan, self.ileri_yigini.pop())
        self.kaydedilmemis = True
        self._takvimi_ciz()

    def _plan_kaydet(self) -> None:
        if not self.plan_sonucu:
            return
        engel = [i for i in self.plan_sonucu.ihlaller if i.engel_mi]
        if engel and not messagebox.askyesno(
                "Engelli plan", f"Planda {len(engel)} engel var. Taslak olarak yine de "
                                "kaydedilsin mi?\n\n(Kesinleştirmek için engeller giderilmelidir.)",
                icon="warning"):
            return
        try:
            plan_id = hizmet.plan_kaydet(self.vt, self.plan_sonucu)
        except HizmetHatasi as hata:
            self._hata("Plan kaydedilemedi", hata)
            return
        self.aktif_plan_id = plan_id
        self.kaydedilmemis = False
        self.geri_yigini.clear()
        self.ileri_yigini.clear()
        self._ozeti_tazele()
        messagebox.showinfo("Plan kaydedildi", f"Plan #{plan_id} olarak kaydedildi.")

    def _plan_kesinlestir(self) -> None:
        if self.aktif_plan_id is None:
            messagebox.showwarning("Kaydedilmemiş plan",
                                   "Kesinleştirmeden önce planı kaydedin.")
            return
        if self.kaydedilmemis:
            messagebox.showwarning("Kaydedilmemiş değişiklik",
                                   "Önce değişiklikleri kaydedin.")
            return
        try:
            hizmet.plan_kesinlestir(self.vt, self.aktif_plan_id, self.onay_girdisi.get())
        except HizmetHatasi as hata:
            self._hata("Plan kesinleştirilemedi", hata)
            return
        messagebox.showinfo(
            "Plan kesinleşti",
            "Plan müdür onayıyla kesinleşti ve oturumlar kilitlendi.")
        self._sayfa_goster(5)

    # ==================================================== 07 evrak ve teslim

    def _sayfa_evrak(self) -> None:
        try:
            pencereler = hizmet.pencereleri_getir(self.vt)
        except HizmetHatasi as hata:
            kart = self._kart("Evrak ve teslim")
            ttk.Label(kart, text=str(hata), style="Kart.TLabel",
                      foreground=RENK["engel"]).pack(anchor="w", padx=15, pady=20)
            return

        kart = self._kart()
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=(12, 4))
        ttk.Label(ust, text="Pencere", style="Kart.TLabel").pack(side=LEFT)
        self.evrak_pencere = ttk.Combobox(
            ust, state="readonly", width=12,
            values=[pencere_adi(kod) for kod in pencereler])
        self.evrak_pencere.current(0)
        self._evrak_pencere_kodlari = list(pencereler)
        self.evrak_pencere.pack(side=LEFT, padx=6)
        self.evrak_durum = ttk.Label(ust, text="", style="Soluk.TLabel")
        self.evrak_durum.pack(side=LEFT, padx=12)

        defter = ttk.Notebook(kart)
        defter.pack(fill=BOTH, expand=True, padx=15, pady=(4, 12))
        uretim = tk.Frame(defter, bg=RENK["kart"])
        teslim = tk.Frame(defter, bg=RENK["kart"])
        defter.add(uretim, text="Evrak üretimi")
        defter.add(teslim, text="Teslim çizelgesi")
        self._evrak_uretim_sekmesi(uretim)
        self._evrak_teslim_sekmesi(teslim)
        self.evrak_pencere.bind("<<ComboboxSelected>>", lambda _e: self._sayfa_goster(6))
        self._evrak_plani_bul()

    def _evrak_plani_bul(self) -> int | None:
        kod = self._evrak_pencere_kodlari[self.evrak_pencere.current()]
        plan_id = hizmet.son_plani_getir(self.vt, kod)
        if plan_id is None:
            self.evrak_durum.configure(
                text="Bu pencerede kayıtlı plan yok. Önce Sınav Planı adımında planı kaydedin.",
                foreground=RENK["engel"])
        else:
            ozet = hizmet.teslim_ozeti(self.vt, plan_id)
            self.evrak_durum.configure(
                text=f"Plan #{plan_id}  •  {ozet['teslim']}/{ozet['toplam']} evrak teslim alındı"
                     + (f"  •  {ozet['gecikti']} gecikmiş" if ozet["gecikti"] else ""),
                foreground=RENK["engel"] if ozet["gecikti"] else RENK["soluk"])
        return plan_id

    def _evrak_uretim_sekmesi(self, ana: tk.Frame) -> None:
        ttk.Label(ana, text="Üretilecek evrakı seçin. Belgeler .docx olarak, "
                            "seçtiğiniz klasöre yazılır.",
                  style="Soluk.TLabel").pack(anchor="w", padx=12, pady=(10, 6))
        self.evrak_secimleri = {}
        kutu = tk.Frame(ana, bg=RENK["kart"])
        kutu.pack(fill=X, padx=12)
        for sira, evrak in enumerate(uretici.EVRAKLAR):
            secim = tk.BooleanVar(value=True)
            ttk.Checkbutton(kutu, text=evrak.ad, variable=secim).grid(
                row=sira // 2, column=sira % 2, sticky="w", padx=(0, 30), pady=3)
            self.evrak_secimleri[evrak.anahtar] = secim

        ilan = tk.Frame(ana, bg=RENK["kart"])
        ilan.pack(fill=X, padx=12, pady=(10, 0))
        ttk.Label(ilan, text="İlan çizelgesinde öğrenci gösterimi",
                  style="Kart.TLabel").pack(side=LEFT)
        self.ogrenci_gosterimi = ttk.Combobox(
            ilan, state="readonly", width=42,
            values=[ad for _, ad in hizmet.OGRENCI_GOSTERIMI])
        self.ogrenci_gosterimi.current(0)
        self.ogrenci_gosterimi.pack(side=LEFT, padx=6)
        ttk.Label(ilan, text="Açık ad hiçbir seçenekte yayımlanmaz.",
                  style="Soluk.TLabel").pack(side=LEFT, padx=6)

        alt = tk.Frame(ana, bg=RENK["kart"])
        alt.pack(fill=X, padx=12, pady=12)
        ttk.Button(alt, text="Klasör seç ve üret", style="Ana.TButton",
                   command=self._evrak_uret).pack(side=LEFT)
        ttk.Button(alt, text="Tümünü seç", style="Ikincil.TButton",
                   command=lambda: [s.set(True) for s in self.evrak_secimleri.values()]
                   ).pack(side=LEFT, padx=6)
        ttk.Button(alt, text="Seçimi kaldır", style="Ikincil.TButton",
                   command=lambda: [s.set(False) for s in self.evrak_secimleri.values()]
                   ).pack(side=LEFT)

        self.evrak_sonuc = self._tablo(ana, ("dosya", "ozet"),
                                       ("Üretilen dosya", "İçerik özeti (SHA-256)"),
                                       (360, 300), 8)

    def _evrak_uret(self) -> None:
        plan_id = self._evrak_plani_bul()
        if plan_id is None:
            messagebox.showwarning("Plan yok", "Önce Sınav Planı adımında planı kaydedin.")
            return
        secilenler = [a for a, s in self.evrak_secimleri.items() if s.get()]
        if not secilenler:
            messagebox.showwarning("Seçim yok", "En az bir evrak türü seçin.")
            return
        klasor = filedialog.askdirectory(title="Evrakın yazılacağı klasör")
        if not klasor:
            return
        try:
            self.kok.configure(cursor="watch")
            self.kok.update_idletasks()
            gosterim = hizmet.OGRENCI_GOSTERIMI[self.ogrenci_gosterimi.current()][0]
            uretilenler = uretici.evrak_uret(self.vt, plan_id, Path(klasor), secilenler,
                                             ogrenci_gosterimi=gosterim)
        except (HizmetHatasi, OSError) as hata:
            self._hata("Evrak üretilemedi", hata)
            return
        finally:
            self.kok.configure(cursor="")
        self.evrak_sonuc.delete(*self.evrak_sonuc.get_children())
        for yol, ozet in uretilenler:
            self.evrak_sonuc.insert("", END, values=(yol.name, ozet[:32] + "…"))
        messagebox.showinfo("Evrak üretildi",
                            f"{len(uretilenler)} belge şu klasöre yazıldı:\n{klasor}")

    def _evrak_teslim_sekmesi(self, ana: tk.Frame) -> None:
        ttk.Label(ana, text="Sınav sonrası komisyondan geri alınan evrak burada izlenir. "
                            "Teslim süresi sınav tarihini izleyen ilk iş günüdür.",
                  style="Soluk.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
        self.teslim_tablosu = self._tablo(
            ana, ("sinav", "tarih", "evrak", "adet", "eden", "alan", "durum"),
            ("Sınav", "Tarih", "Evrak", "Adet", "Teslim eden", "Teslim alan", "Durum"),
            (200, 80, 150, 55, 140, 140, 100), 11)
        self.teslim_tablosu.tag_configure("gecikti", background="#FFE6E6")
        self.teslim_tablosu.tag_configure("teslim alındı", background="#E8F6EF")

        form = tk.Frame(ana, bg=RENK["kart"])
        form.pack(fill=X, padx=12, pady=(0, 6))
        personel = [p for p in hizmet.personelleri_getir(self.vt)]
        secenekler = [f"{p.kimlik} | {p.ad}" for p in personel]
        ttk.Label(form, text="Teslim eden", style="Kart.TLabel").pack(side=LEFT)
        self.teslim_eden = ttk.Combobox(form, state="readonly", width=26, values=secenekler)
        self.teslim_eden.pack(side=LEFT, padx=5)
        ttk.Label(form, text="Teslim alan", style="Kart.TLabel").pack(side=LEFT)
        self.teslim_alan = ttk.Combobox(form, state="readonly", width=26, values=secenekler)
        self.teslim_alan.pack(side=LEFT, padx=5)
        ttk.Label(form, text="Adet", style="Kart.TLabel").pack(side=LEFT)
        self.teslim_adet = ttk.Entry(form, width=6)
        self.teslim_adet.pack(side=LEFT, padx=5)

        alt = tk.Frame(ana, bg=RENK["kart"])
        alt.pack(fill=X, padx=12, pady=(0, 12))
        ttk.Label(alt, text="Açıklama", style="Kart.TLabel").pack(side=LEFT)
        self.teslim_aciklama = ttk.Entry(alt, width=44)
        self.teslim_aciklama.pack(side=LEFT, padx=5)
        ttk.Button(alt, text="Seçili evrakı teslim al", style="Ana.TButton",
                   command=self._teslim_kaydet).pack(side=LEFT, padx=8)
        ttk.Button(alt, text="Teslimi geri al", style="Ikincil.TButton",
                   command=self._teslim_geri_al).pack(side=LEFT)
        self._teslim_tazele()

    def _teslim_tazele(self) -> None:
        plan_id = self._evrak_plani_bul()
        self.teslim_tablosu.delete(*self.teslim_tablosu.get_children())
        self.teslim_satirlari = []
        if plan_id is None:
            return
        self.teslim_satirlari = hizmet.teslim_cizelgesi(self.vt, plan_id)
        for sira, satir in enumerate(self.teslim_satirlari):
            durum = satir.durum()
            self.teslim_tablosu.insert(
                "", END, iid=str(sira),
                values=(satir.oturum_etiketi, satir.tarih.strftime("%d.%m.%Y"),
                        satir.evrak_adi, "" if satir.adet is None else satir.adet,
                        satir.teslim_eden, satir.teslim_alan, durum),
                tags=(durum,))

    def _secili_teslim(self):
        if not self.teslim_tablosu.selection():
            messagebox.showwarning("Seçim yok", "Çizelgeden bir evrak satırı seçin.")
            return None
        return self.teslim_satirlari[int(self.teslim_tablosu.selection()[0])]

    def _teslim_kaydet(self) -> None:
        satir = self._secili_teslim()
        if satir is None:
            return
        try:
            if not self.teslim_eden.get() or not self.teslim_alan.get():
                raise HizmetHatasi("Teslim eden ve teslim alan görevliyi seçin.")
            adet_metni = self.teslim_adet.get().strip()
            hizmet.teslim_kaydet(
                self.vt, satir.oturum_id, satir.evrak_turu,
                int(self.teslim_eden.get().split(" | ")[0]),
                int(self.teslim_alan.get().split(" | ")[0]),
                int(adet_metni) if adet_metni else None,
                self.teslim_aciklama.get())
        except (HizmetHatasi, ValueError) as hata:
            self._hata("Teslim kaydedilemedi", hata)
            return
        self._teslim_tazele()

    def _teslim_geri_al(self) -> None:
        satir = self._secili_teslim()
        if satir is None:
            return
        if not satir.teslim_edildi_mi:
            messagebox.showinfo("Kayıt yok", "Bu evrak için teslim kaydı bulunmuyor.")
            return
        try:
            hizmet.teslim_geri_al(self.vt, satir.oturum_id, satir.evrak_turu)
        except HizmetHatasi as hata:
            self._hata("Teslim geri alınamadı", hata)
            return
        self._teslim_tazele()

    # ============================================================ 08 yardım

    def _sayfa_yardim(self) -> None:
        kart = self._kart()
        sarmal = tk.Frame(kart, bg=RENK["kart"])
        sarmal.pack(fill=BOTH, expand=True, padx=15, pady=12)
        metin = tk.Text(sarmal, wrap="word", font=("Segoe UI", 10), bd=0,
                        bg=RENK["kart"], fg=RENK["yazi"], padx=14, pady=10,
                        spacing1=2, spacing3=4, cursor="arrow")
        kaydirma = ttk.Scrollbar(sarmal, orient="vertical", command=metin.yview)
        metin.configure(yscrollcommand=kaydirma.set)
        metin.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill=Y)

        metin.tag_configure("baslik", font=("Segoe UI Semibold", 13),
                            foreground=RENK["kenar"], spacing1=14, spacing3=6)
        metin.tag_configure("paragraf", spacing3=6, lmargin1=2, lmargin2=2)
        metin.tag_configure("madde", spacing3=3, lmargin1=16, lmargin2=30)
        metin.tag_configure("giris", font=("Segoe UI", 10), foreground=RENK["soluk"],
                            spacing3=10)

        metin.insert(END, "Sorumluluk sınavlarına ilişkin mevzuat hükümleri, programın "
                          "kullanımı ve çalışma mantığı.\n", "giris")
        for baslik, paragraflar in yardim_metni.BOLUMLER:
            metin.insert(END, f"\n{baslik}\n", "baslik")
            for paragraf in paragraflar:
                if paragraf.startswith("•"):
                    metin.insert(END, f"{paragraf}\n", "madde")
                else:
                    metin.insert(END, f"{paragraf}\n", "paragraf")
        metin.configure(state="disabled")

    def _rapor_ipucu(self, ana: tk.Frame, rapor_kodu: str, aciklama: str) -> None:
        """İçe aktarma ekranlarında hangi raporun nasıl indirileceğini anlatır."""
        kutu = tk.Frame(ana, bg="#EEF4FA", highlightthickness=1,
                        highlightbackground=RENK["cizgi"])
        kutu.pack(fill=X, padx=15, pady=(4, 8))
        tk.Label(kutu, text=f"e-Okul raporu:  {rapor_kodu}", bg="#EEF4FA",
                 fg=RENK["kenar"], font=("Segoe UI Semibold", 10),
                 anchor="w").pack(fill=X, padx=12, pady=(8, 0))
        tk.Label(kutu, text=aciklama, bg="#EEF4FA", fg=RENK["yazi"],
                 font=("Segoe UI", 9), anchor="w", justify=LEFT,
                 wraplength=980).pack(fill=X, padx=12, pady=(2, 2))
        tk.Label(kutu,
                 text="Raporu HTML5 görüntüleyicide açın → dışa aktarmadan Excel'i seçin → "
                      "SADECE VERİ seçeneğini işaretleyin. Biçimlendirilmiş çıktı okunamaz.",
                 bg="#EEF4FA", fg=RENK["engel"], font=("Segoe UI Semibold", 9),
                 anchor="w", justify=LEFT, wraplength=980).pack(fill=X, padx=12, pady=(0, 9))

    # ============================================================ 09 lisans

    def _sayfa_lisans(self) -> None:
        kart = self._kart()
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=(14, 4))
        png = varlik_yolu("logo.png")
        if png is not None:
            try:
                self._lisans_simgesi = tk.PhotoImage(file=str(png)).subsample(6, 6)
                tk.Label(ust, image=self._lisans_simgesi, bg=RENK["kart"]).pack(
                    side=LEFT, padx=(0, 14))
            except tk.TclError:
                pass
        yazi = tk.Frame(ust, bg=RENK["kart"])
        yazi.pack(side=LEFT, anchor="n")
        tk.Label(yazi, text="Sorumluluk Sınavı", bg=RENK["kart"], fg=RENK["kenar"],
                 font=("Segoe UI Semibold", 16), anchor="w").pack(anchor="w")
        tk.Label(yazi, text=f"Sürüm {SURUM}", bg=RENK["kart"], fg=RENK["soluk"],
                 font=("Segoe UI", 10), anchor="w").pack(anchor="w")
        tk.Label(yazi, text="Ortaöğretim kurumları için çevrimdışı sorumluluk sınavı\n"
                            "planlama ve görevlendirme uygulaması",
                 bg=RENK["kart"], fg=RENK["yazi"], font=("Segoe UI", 10),
                 justify=LEFT, anchor="w").pack(anchor="w", pady=(4, 0))

        sarmal = tk.Frame(kart, bg=RENK["kart"])
        sarmal.pack(fill=BOTH, expand=True, padx=15, pady=(10, 14))
        metin = tk.Text(sarmal, wrap="word", font=("Segoe UI", 10), bd=0,
                        bg=RENK["kart"], fg=RENK["yazi"], padx=12, pady=8,
                        spacing1=2, spacing3=4, cursor="arrow")
        kaydirma = ttk.Scrollbar(sarmal, orient="vertical", command=metin.yview)
        metin.configure(yscrollcommand=kaydirma.set)
        metin.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill=Y)
        metin.tag_configure("baslik", font=("Segoe UI Semibold", 12),
                            foreground=RENK["kenar"], spacing1=12, spacing3=5)
        metin.tag_configure("paragraf", spacing3=6)
        metin.tag_configure("madde", spacing3=3, lmargin1=16, lmargin2=30)

        for baslik, paragraflar in yardim_metni.LISANS_BOLUMLERI:
            metin.insert(END, f"{baslik}\n", "baslik")
            for paragraf in paragraflar:
                etiket = "madde" if paragraf.startswith("•") else "paragraf"
                metin.insert(END, f"{paragraf}\n", etiket)
        metin.configure(state="disabled")
