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

from cekirdek.modeller import IkiAsamaliSayim, PlanParametreleri
from cekirdek.planlayici import PlanlamaBasarisiz, sinir_onizlemesi
from veri import hizmet
from veri.hizmet import HizmetHatasi
from veri.rapor_okuma import RaporHatasi
from veri.veritabani import Veritabani
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


def veri_klasoru() -> Path:
    ozel = os.environ.get("SORUMLULUK_VERI_KLASORU")
    if ozel:
        return Path(ozel)
    if os.name == "nt":
        taban = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return taban / "SorumlulukSinavi" / "veri"
    return Path.home() / ".local" / "share" / "sorumluluk-sinavi"


class Uygulama:
    def __init__(self) -> None:
        self.kok = tk.Tk()
        self.kok.title("Sorumluluk Sınavı • Planlama ve Görevlendirme")
        self.kok.geometry("1380x860")
        self.kok.minsize(1100, 700)
        self.kok.configure(bg=RENK["zemin"])

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
         self._sayfa_sorumluluk, self._sayfa_ders, self._sayfa_plan)[sira]()

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
            f"{kod}: {bas.strftime('%d.%m.%Y')}–{bit.strftime('%d.%m.%Y')}"
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
        kart = self._kart(
            "e-Okul personel listesi",
            "OOK01001R1 raporunu seçin. Önizleme onaylanmadan hiçbir kayıt değişmez. "
            "Branş havuzu bu rapordan beslenir.")
        ust = tk.Frame(kart, bg=RENK["kart"])
        ust.pack(fill=X, padx=15, pady=8)
        ttk.Button(ust, text="Rapor seç ve önizle", style="Ana.TButton",
                   command=self._personel_sec).pack(side=LEFT)
        ttk.Button(ust, text="Farkları onayla", style="Ikincil.TButton",
                   command=self._personel_onayla).pack(side=LEFT, padx=8)
        self.personel_durum = ttk.Label(ust, text="Henüz rapor seçilmedi.", style="Kart.TLabel")
        self.personel_durum.pack(side=LEFT, padx=10)

        self.personel_tablosu = self._tablo(
            kart, ("ad", "unvan", "kadro", "brans", "eylem"),
            ("Adı Soyadı", "Görevi", "Kadro", "Branşı", "Değişiklik"),
            (240, 190, 130, 210, 120))
        for etiket, renk in (("eklenecek", "#E8F6EF"), ("guncellenecek", "#FFF3DC")):
            self.personel_tablosu.tag_configure(etiket, background=renk)
        for kisi in hizmet.personelleri_getir(self.vt):
            self.personel_tablosu.insert(
                "", END, values=(kisi.ad, kisi.unvan, "", kisi.brans, "kayıtlı"))

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
        kart = self._kart(
            "e-Okul sorumluluk kayıtları",
            "OOK12001R010 raporunu seçin. Rapor okulun tamamını kapsıyorsa, dosyada "
            "bulunmayan aktif kayıtlar pasife alınır.")
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
        for ders_id, ad, brans, iki, _yabanci, kayit_sayisi in dersler:
            tablo.insert("", END, iid=str(ders_id),
                         values=(ad, brans or "— eşlenmedi —", "Evet" if iki else "Hayır",
                                 kayit_sayisi),
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
            for kimlik, ad, brans, iki, _yd, _s in dersler:
                if kimlik == ders_id:
                    parcalar = [p.strip() for p in str(brans or "").split("/") if p.strip()]
                    if parcalar and parcalar[0] in branslar:
                        brans_secimi.set(parcalar[0])
                    esdeger_secimi.set(parcalar[1] if len(parcalar) > 1 else "—")
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
            values=[f"{kod}  {bas.strftime('%d.%m.%Y')}–{bit.strftime('%d.%m.%Y')}"
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
        return self.pencere_secimi.get().split()[0]

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
        ihlaller = hizmet.plani_dogrula(self.vt, plan)
        self.plan_sonucu = PlanlamaSonucu(plan, ihlaller, {},
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
