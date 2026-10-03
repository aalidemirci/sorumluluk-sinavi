"""Ana pencerenin açtığı iletişim pencereleri.

Müsaitlik, görevli değişikliği ve tek ders sınavı öğrenci seçimi ayrı
pencerelerde yapılır: üçü de bir kayda (öğretmen, oturum, dönem) bağlı küçük
işlerdir ve ana ekranı kalabalıklaştırmamalıdır. Pencereler SQL yazmaz, kural
bilmez; her şeyi `veri.hizmet` üzerinden yapar.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, time
from tkinter import BOTH, END, LEFT, RIGHT, X, messagebox, ttk

from arayuz.palet import RENK
from cekirdek.modeller import GorevRolu
from cekirdek.takvim import tarih_coz, tarih_yaz
from veri import hizmet
from veri.hizmet import HizmetHatasi

ROL_ADLARI = {GorevRolu.KOMISYON_UYESI: "Komisyon üyesi", GorevRolu.GOZCU: "Gözcü"}
KVKK_UYARISI = "Sağlık bilgisi yazmayın (KVKK özel nitelikli veri); 'izinli', 'derste' yeter."


def saat_coz(metin: str) -> time | None:
    """Boş metin "bütün gün" demektir ve None döner."""
    metin = str(metin or "").strip()
    if not metin:
        return None
    try:
        return datetime.strptime(metin, "%H:%M").time()
    except ValueError as hata:
        raise HizmetHatasi(f"'{metin}' geçerli bir saat değil; SS:DD yazın (ör. 08:30).") from hata


class _Pencere(tk.Toplevel):
    def __init__(self, uygulama, baslik: str, boyut: str):
        super().__init__(uygulama.kok)
        self.uygulama = uygulama
        self.vt = uygulama.vt
        self.title(baslik)
        self.configure(bg=RENK["kart"])
        self.geometry(boyut)
        self.transient(uygulama.kok)
        try:
            self.grab_set()
        except tk.TclError:          # ekransız sınama ortamı
            pass

    def _etiket(self, ana, metin: str, soluk: bool = False, **paket) -> ttk.Label:
        etiket = ttk.Label(ana, text=metin, style="Soluk.TLabel" if soluk else "Kart.TLabel",
                           wraplength=760, justify=LEFT)
        etiket.pack(anchor="w", **paket)
        return etiket

    def _tablo(self, sutunlar, basliklar, genislikler, yukseklik=8) -> ttk.Treeview:
        sarmal = tk.Frame(self, bg=RENK["kart"])
        sarmal.pack(fill=BOTH, expand=True, padx=12, pady=(4, 6))
        tablo = ttk.Treeview(sarmal, columns=sutunlar, show="headings", height=yukseklik)
        for sutun, baslik, genislik in zip(sutunlar, basliklar, genislikler):
            tablo.heading(sutun, text=baslik)
            tablo.column(sutun, width=genislik, anchor="w")
        kaydirma = ttk.Scrollbar(sarmal, orient="vertical", command=tablo.yview)
        tablo.configure(yscrollcommand=kaydirma.set)
        tablo.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill="y")
        return tablo

    def _hata(self, baslik: str, hata: Exception) -> None:
        messagebox.showerror(baslik, str(hata), parent=self)


# ================================================================ müsaitlik

class MusaitlikPenceresi(_Pencere):
    """Öğretmenin görev alamayacağı zamanlar (OKY md.58/2-ç)."""

    def __init__(self, uygulama, kisi: dict):
        super().__init__(uygulama, f"Müsaitlik — {kisi['ad']}", "820x560")
        self.kisi = kisi
        self._etiket(self, "Öğretmenin sınav görevi alamayacağı zamanları girin: ders "
                           "programındaki dolu saatler, izin, başka görev. Planlayıcı bu "
                           "saatlere görev vermez; elle verilen görev engel olarak "
                           "görünür (SP-09). " + KVKK_UYARISI,
                     soluk=True, padx=12, pady=(10, 4))
        self.tablo = self._tablo(("zaman", "saat", "aciklama"), ("Zaman", "Saat", "Açıklama"),
                                 (230, 130, 360))
        sil = tk.Frame(self, bg=RENK["kart"])
        sil.pack(fill=X, padx=12)
        ttk.Button(sil, text="Seçili kaydı sil", style="Ikincil.TButton",
                   command=self._sil).pack(side=LEFT)

        haftalik = self._cerceve("Her hafta tekrar eden (ör. ders programı) — saat boşsa "
                                 "bütün gün", (10, 4))
        satir = tk.Frame(haftalik, bg=RENK["kart"])
        satir.pack(fill=X, padx=6, pady=4)
        # Kutu satırın içinde kurulur: başka çerçevede kurulup buraya
        # yerleştirilseydi sonradan kurulan satırın arkasında kalırdı.
        self.gun = ttk.Combobox(satir, values=hizmet.HAFTA_GUNLERI, width=10, state="readonly")
        self.gun.current(0)
        self.gun.pack(side=LEFT, padx=(0, 10))
        self.h_bas, self.h_bit, self.h_aciklama = self._saat_satiri(satir, self._haftalik_ekle)

        tarihli = self._cerceve("Tarih aralığı (izin, başka görevlendirme) — saat boşsa "
                                "bütün gün", (6, 12))
        ust = tk.Frame(tarihli, bg=RENK["kart"])
        ust.pack(fill=X, padx=6, pady=(4, 0))
        ttk.Label(ust, text="Başlangıç (gg.aa.yyyy)", style="Kart.TLabel").pack(side=LEFT)
        self.t_bas_tarih = ttk.Entry(ust, width=11)
        self.t_bas_tarih.pack(side=LEFT, padx=(4, 10))
        ttk.Label(ust, text="Bitiş (boşsa tek gün)", style="Kart.TLabel").pack(side=LEFT)
        self.t_bit_tarih = ttk.Entry(ust, width=11)
        self.t_bit_tarih.pack(side=LEFT, padx=4)
        alt = tk.Frame(tarihli, bg=RENK["kart"])
        alt.pack(fill=X, padx=6, pady=4)
        self.t_bas, self.t_bit, self.t_aciklama = self._saat_satiri(alt, self._tarihli_ekle)
        self._doldur()
        self.protocol("WM_DELETE_WINDOW", self._kapat)

    def _cerceve(self, baslik: str, bosluk: tuple[int, int]) -> tk.LabelFrame:
        cerceve = tk.LabelFrame(self, text=baslik, bg=RENK["kart"], fg=RENK["yazi"],
                                font=("Segoe UI", 9))
        cerceve.pack(fill=X, padx=12, pady=bosluk)
        return cerceve

    def _saat_satiri(self, satir, komut):
        ttk.Label(satir, text="Saat", style="Kart.TLabel").pack(side=LEFT)
        bas = ttk.Entry(satir, width=6)
        bas.pack(side=LEFT, padx=(4, 2))
        ttk.Label(satir, text="–", style="Kart.TLabel").pack(side=LEFT)
        bit = ttk.Entry(satir, width=6)
        bit.pack(side=LEFT, padx=(2, 10))
        ttk.Label(satir, text="Açıklama", style="Kart.TLabel").pack(side=LEFT)
        aciklama = ttk.Entry(satir, width=20)
        aciklama.pack(side=LEFT, padx=4)
        ttk.Button(satir, text="Ekle", style="Ana.TButton", command=komut).pack(side=LEFT, padx=6)
        return bas, bit, aciklama

    def _doldur(self) -> None:
        self.tablo.delete(*self.tablo.get_children())
        for kayit in hizmet.musaitlik_listesi(self.vt, self.kisi["kimlik"]):
            self.tablo.insert("", END, iid=str(kayit["kimlik"]),
                              values=(kayit["zaman"], kayit["saat"], kayit["aciklama"]))

    def _haftalik_ekle(self) -> None:
        try:
            hizmet.musaitlik_ekle(self.vt, self.kisi["kimlik"], hafta_gunu=self.gun.current(),
                                  bas_saat=saat_coz(self.h_bas.get()),
                                  bit_saat=saat_coz(self.h_bit.get()),
                                  aciklama=self.h_aciklama.get())
        except HizmetHatasi as hata:
            self._hata("Kayıt eklenemedi", hata)
            return
        self._doldur()

    def _tarihli_ekle(self) -> None:
        try:
            bas = tarih_coz(self.t_bas_tarih.get())
            bit = tarih_coz(self.t_bit_tarih.get()) if self.t_bit_tarih.get().strip() else bas
            hizmet.musaitlik_ekle(self.vt, self.kisi["kimlik"], bas_tarih=bas, bit_tarih=bit,
                                  bas_saat=saat_coz(self.t_bas.get()),
                                  bit_saat=saat_coz(self.t_bit.get()),
                                  aciklama=self.t_aciklama.get())
        except (HizmetHatasi, ValueError) as hata:
            self._hata("Kayıt eklenemedi", hata)
            return
        self._doldur()

    def _sil(self) -> None:
        if not self.tablo.selection():
            messagebox.showwarning("Seçim yok", "Silinecek kaydı seçin.", parent=self)
            return
        hizmet.musaitlik_sil(self.vt, int(self.tablo.selection()[0]))
        self._doldur()

    def _kapat(self) -> None:
        self.destroy()
        if hasattr(self.uygulama, "personel_tablosu"):
            try:
                self.uygulama._personel_listesini_doldur()
            except tk.TclError:
                pass


# ====================================================== görevli değişikliği

class GorevliDegistirPenceresi(_Pencere):
    """Seçili oturumun bir görevlisinin yerine başkasını koyar.

    Taslak planda değişiklik bellekte yapılır ve "Geri Al" ile geri alınır;
    kesinleşmiş planda müdür onay numarası ve gerekçe zorunludur, değişiklik
    hemen kaydedilir ve evrakta listelenir.
    """

    def __init__(self, uygulama, oturum_anahtari: str):
        super().__init__(uygulama, "Görevliyi değiştir", "880x600")
        self.plan = uygulama.plan_sonucu.plan
        self.oturum = self.plan.oturum_bul(oturum_anahtari)
        self.kesin = bool(self.oturum.kilitli_mi)
        personel = {p.kimlik: p for p in hizmet.personelleri_getir(self.vt, yalniz_aktif=False)}
        self.personel = personel
        tur = " (uygulama)" if self.oturum.oturum_turu.value == "uygulama" else ""
        self._etiket(self, f"{'/'.join(map(str, self.oturum.duzeyler))} {self.oturum.ders_adi}"
                           f"{tur} • {tarih_yaz(self.oturum.tarih)} "
                           f"{self.oturum.saat.strftime('%H:%M')}", padx=12, pady=(10, 0))
        self._etiket(self, ("Plan kesinleşmiştir: değişiklik müdür onay numarası ve gerekçeyle "
                            "hemen kaydedilir ve görevlendirme çizelgesinde listelenir."
                            if self.kesin else
                            "Değişiklik plan kaydedilene kadar bellekte kalır; 'Geri Al' ile "
                            "geri alınabilir.") + " " + KVKK_UYARISI,
                     soluk=True, padx=12, pady=(2, 4))

        self._etiket(self, "1. Değiştirilecek görevli", padx=12)
        self.mevcut = self._tablo(("rol", "ad", "brans", "salon"),
                                  ("Görev", "Adı Soyadı", "Branşı", "Salon"),
                                  (120, 260, 220, 120), 4)
        salon_adlari = {s.kimlik: s.ad for s in hizmet.salonlari_getir(self.vt)}
        for gorev in self.plan.oturum_gorevleri(oturum_anahtari):
            kisi = personel.get(gorev.personel_kimligi)
            self.mevcut.insert("", END, iid=f"{gorev.personel_kimligi}|{gorev.rol.value}", values=(
                ROL_ADLARI[gorev.rol], kisi.ad if kisi else gorev.personel_kimligi,
                kisi.brans if kisi else "", salon_adlari.get(gorev.salon_kimligi, "")))
        self.mevcut.bind("<<TreeviewSelect>>", lambda _o: self._adaylari_doldur())

        self._etiket(self, "2. Yerine görevlendirilecek kişi (uygun olanlar üstte)", padx=12)
        self.adaylar = self._tablo(("ad", "brans", "alan", "yuk", "durum"),
                                   ("Adı Soyadı", "Branşı", "Alan", "Görev", "Durum"),
                                   (230, 200, 60, 60, 240), 8)
        self.adaylar.tag_configure("uygun_degil", foreground=RENK["soluk"])

        alt = tk.Frame(self, bg=RENK["kart"])
        alt.pack(fill=X, padx=12, pady=(4, 12))
        ttk.Label(alt, text="Gerekçe", style="Kart.TLabel").pack(side=LEFT)
        self.gerekce = ttk.Entry(alt, width=30)
        self.gerekce.pack(side=LEFT, padx=(4, 10))
        self.onay_no = ttk.Entry(alt, width=14)
        if self.kesin:
            ttk.Label(alt, text="Müdür onay no", style="Kart.TLabel").pack(side=LEFT)
            self.onay_no.pack(side=LEFT, padx=(4, 10))
        self.es_oturum = tk.BooleanVar(value=True)
        if self.oturum.birim_anahtari:
            ttk.Checkbutton(alt, text="Yazılı ve uygulamada birlikte (58/2-e)",
                            variable=self.es_oturum).pack(side=LEFT)
        ttk.Button(alt, text="Değiştir", style="Ana.TButton",
                   command=self._degistir).pack(side=RIGHT)

    def _secili_gorev(self) -> tuple[int, GorevRolu] | None:
        if not self.mevcut.selection():
            return None
        kimlik, rol = self.mevcut.selection()[0].split("|")
        return int(kimlik), GorevRolu(rol)

    def _adaylari_doldur(self) -> None:
        self.adaylar.delete(*self.adaylar.get_children())
        secim = self._secili_gorev()
        if secim is None:
            return
        for aday in hizmet.gorevli_adaylari(self.vt, self.plan, self.oturum.anahtar,
                                            secim[1], secim[0]):
            self.adaylar.insert("", END, iid=str(aday["kimlik"]), values=(
                aday["ad"], aday["brans"], "evet" if aday["alan_mi"] else "",
                aday["gorev_sayisi"], "uygun" if aday["uygun_mu"] else aday["neden"]),
                tags=() if aday["uygun_mu"] else ("uygun_degil",))

    def _degistir(self) -> None:
        secim = self._secili_gorev()
        if secim is None or not self.adaylar.selection():
            messagebox.showwarning("Seçim yok", "Önce değiştirilecek görevliyi, sonra yerine "
                                   "gelecek kişiyi seçin.", parent=self)
            return
        eski, _ = secim
        yeni = int(self.adaylar.selection()[0])
        try:
            if self.kesin:
                sonuc = hizmet.kesin_plan_gorevli_degistir(
                    self.vt, self.uygulama.aktif_plan_id, self.oturum.anahtar, eski, yeni,
                    self.onay_no.get(), self.gerekce.get(), self.es_oturum.get())
            else:
                goruntu = hizmet.plan_anlik_goruntusu(self.plan)
                sonuc = hizmet.gorevli_degistir(
                    self.vt, self.plan, self.oturum.anahtar, eski, yeni,
                    self.uygulama.plan_sonucu.yukseltilen_sinirlar, self.gerekce.get(),
                    self.es_oturum.get())
        except HizmetHatasi as hata:
            self._hata("Görevli değiştirilemedi", hata)
            return
        if not sonuc.uygulandi:
            messagebox.showwarning("Değişiklik yapılamadı", sonuc.mesaj(), parent=self)
            return
        self.destroy()
        if self.kesin:
            self.uygulama._son_plani_yukle()
        else:
            self.uygulama.geri_yigini.append(goruntu)
            self.uygulama.ileri_yigini.clear()
            self.uygulama.kaydedilmemis = True
            self.uygulama._takvimi_ciz()
        self.uygulama._kart_secildi(self.oturum.anahtar)


# ==================================================== tek ders sınavı seçimi

class TekDersPenceresi(_Pencere):
    """OKY md.58/6 tek ders sınavına girecek öğrenci ve dersin seçimi."""

    def __init__(self, uygulama, pencere_kodu: str):
        super().__init__(uygulama, "Tek ders sınavı öğrencileri", "860x560")
        self.kod = pencere_kodu
        self._etiket(self, "OKY md.58/6: sorumluluk sınavı sonunda tek dersten başarısızlığı "
                           "bulunan son sınıf öğrencileri için aynı usulle takip eden hafta "
                           "içinde bir sınav daha yapılır. Program sınav sonuçlarını bilmez; "
                           "e-Okul'daki sonuçlara bakarak öğrencinin başarısız kaldığı tek "
                           "dersi seçin. Listede bu dönemin planındaki 12. sınıf öğrencileri "
                           "vardır. Satıra çift tıklamak seçimi açar ya da kapatır.",
                     soluk=True, padx=12, pady=(10, 4))
        self.tablo = self._tablo(("no", "ad", "sube", "ders", "secim"),
                                 ("Okul no", "Adı Soyadı", "Şube", "Ders", "Tek ders"),
                                 (80, 250, 70, 280, 90), 14)
        self.tablo.tag_configure("secili", background=RENK["basari_zemin"])
        self.tablo.bind("<Double-1>", lambda _o: self._degistir())
        alt = tk.Frame(self, bg=RENK["kart"])
        alt.pack(fill=X, padx=12, pady=(4, 12))
        ttk.Button(alt, text="Seç / kaldır", style="Ana.TButton",
                   command=self._degistir).pack(side=LEFT)
        self.ozet = ttk.Label(alt, text="", style="Soluk.TLabel")
        self.ozet.pack(side=LEFT, padx=10)
        ttk.Button(alt, text="Kapat", style="Ikincil.TButton",
                   command=self.destroy).pack(side=RIGHT)
        self._doldur()

    def _doldur(self) -> None:
        self.tablo.delete(*self.tablo.get_children())
        self.satirlar = {str(s["sorumluluk_kaydi_id"]): s
                         for s in hizmet.tek_ders_adaylari(self.vt, self.kod)}
        for anahtar, satir in self.satirlar.items():
            self.tablo.insert("", END, iid=anahtar, values=(
                satir["okul_no"], satir["ad_soyad"], satir["sube"],
                f"{satir['duzey']}. sınıf {satir['ders']}", "✓ seçili" if satir["secili_mi"] else ""),
                tags=("secili",) if satir["secili_mi"] else ())
        secili = sum(1 for s in self.satirlar.values() if s["secili_mi"])
        self.ozet.configure(text=(f"{secili} öğrenci seçili." if self.satirlar else
                                  "Bu dönemin kayıtlı planında 12. sınıf öğrencisi yok. Önce "
                                  "olağan planı kaydedin."))

    def _degistir(self) -> None:
        if not self.tablo.selection():
            return
        satir = self.satirlar[self.tablo.selection()[0]]
        try:
            hizmet.tek_ders_sec(self.vt, self.kod, satir["ogrenci_id"],
                                None if satir["secili_mi"] else satir["sorumluluk_kaydi_id"])
        except HizmetHatasi as hata:
            self._hata("Seçim kaydedilemedi", hata)
            return
        self._doldur()
