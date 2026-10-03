"""Sürükle-bırak sınav takvimi.

Sütunlar gün, satırlar oturum saatidir. Aynı hücrede birden fazla kart
bulunabilir; motor paralel oturuma izin verdiği için bu normaldir. Kart
bırakıldığında taşımayı çağıran katman denetler ve gerekirse geri alır.
Kart sürüklenmeden bırakılırsa bu bir seçimdir; çağıran katman oturumun
ayrıntısını gösterir.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from datetime import date, time
from tkinter import ttk
import tkinter as tk

from arayuz.palet import RENK as _P


GUN_KISALTMALARI = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")

# Izgaranın kendi ad kümesi var ama renkler tek yerden, arayuz.palet'ten
# gelir; site paletiyle uyumu orada tutulur.
RENK = {
    "zemin": _P["kart"],
    "izgara": _P["cizgi"],
    "baslik": _P["tint"],
    "baslik_yazi": _P["yazi"],
    "hafta_sonu": _P["uyari_zemin"],
    "kart": _P["chip"],
    "kart_kenar": _P["takvim_kart_kenar"],
    "kart_yazi": _P["yazi"],
    "kilit": _P["pasif_zemin"],
    "kilit_kenar": _P["takvim_kilit_kenar"],
    "uygulama": _P["basari_zemin"],
    "uygulama_kenar": _P["takvim_uygulama_kenar"],
    "hedef": _P["takvim_hedef"],
    "secili_kenar": _P["kenar"],
}


class SurukleBirakTakvim(ttk.Frame):
    SOL = 84
    UST = 46
    GUN_GENISLIK = 168
    SATIR_YUKSEKLIK = 96
    KART_YUKSEKLIK = 26
    KART_ARASI = 3
    # Bundan kısa fare hareketi sürükleme değil tıklamadır.
    SURUKLEME_ESIGI = 6

    def __init__(self, parent, gunler: list[date], saatler: list[time],
                 kartlar: list[dict], birak_geri_cagirimi, sec_geri_cagirimi=None):
        super().__init__(parent)
        self.gunler = list(gunler)
        self.saatler = list(saatler)
        self.kartlar = list(kartlar)
        self.birak = birak_geri_cagirimi
        self.sec = sec_geri_cagirimi
        self.suruklenen: str | None = None
        self.hedef_hucre: tuple[int, int] | None = None
        self.basis_noktasi: tuple[float, float] | None = None
        self.surukleniyor = False
        self.secili: str | None = None

        self.canvas = tk.Canvas(self, bg=RENK["zemin"], highlightthickness=1,
                                highlightbackground=RENK["izgara"])
        yatay = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        dikey = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=yatay.set, yscrollcommand=dikey.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        dikey.grid(row=0, column=1, sticky="ns")
        yatay.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.canvas.bind("<ButtonPress-1>", self._basildi)
        self.canvas.bind("<B1-Motion>", self._suruklendi)
        self.canvas.bind("<ButtonRelease-1>", self._birakildi)
        self.ciz()

    # ------------------------------------------------------------- çizim

    def _satir_yukseklikleri(self) -> list[int]:
        """Her saat satırı, o saatteki en kalabalık hücrenin kartlarını alır.

        Eski sürüm satır yüksekliğini sabit tutuyordu; bir hücreye üçten fazla
        paralel oturum düşünce fazlası hiç çizilmiyor, sürüklenemiyordu.
        """
        doluluk = Counter()
        for kart in self.kartlar:
            yer = self._hucre_indisi(kart["tarih"], kart["saat"])
            if yer is not None:
                doluluk[yer] += 1
        yukseklikler = []
        for satir in range(len(self.saatler)):
            en_cok = max((adet for (_, s), adet in doluluk.items() if s == satir), default=0)
            gereken = 8 + en_cok * (self.KART_YUKSEKLIK + self.KART_ARASI)
            yukseklikler.append(max(self.SATIR_YUKSEKLIK, gereken))
        return yukseklikler

    def ciz(self) -> None:
        c = self.canvas
        c.delete("all")
        yukseklikler = self._satir_yukseklikleri()
        self._satir_ustleri = [self.UST]
        for yukseklik in yukseklikler:
            self._satir_ustleri.append(self._satir_ustleri[-1] + yukseklik)
        genislik = self.SOL + len(self.gunler) * self.GUN_GENISLIK
        toplam = self._satir_ustleri[-1]
        c.configure(scrollregion=(0, 0, genislik, toplam))

        c.create_rectangle(0, 0, genislik, self.UST, fill=RENK["baslik"], outline="")
        for sutun, gun in enumerate(self.gunler):
            x = self.SOL + sutun * self.GUN_GENISLIK
            if gun.weekday() >= 5:
                c.create_rectangle(x, self.UST, x + self.GUN_GENISLIK, toplam,
                                   fill=RENK["hafta_sonu"], outline="")
            c.create_text(x + self.GUN_GENISLIK / 2, self.UST / 2,
                          text=f"{GUN_KISALTMALARI[gun.weekday()]}  {gun.strftime('%d.%m')}",
                          font=("Segoe UI Semibold", 9), fill=RENK["baslik_yazi"])
            c.create_line(x, 0, x, toplam, fill=RENK["izgara"])
        for satir, saat in enumerate(self.saatler):
            y = self._satir_ustleri[satir]
            c.create_line(0, y, genislik, y, fill=RENK["izgara"])
            c.create_text(self.SOL / 2, y + 14, text=saat.strftime("%H:%M"),
                          font=("Segoe UI", 9), fill=RENK["baslik_yazi"])
        c.create_line(self.SOL, 0, self.SOL, toplam, fill=RENK["izgara"])

        hucre_sayaci: dict[tuple[int, int], int] = {}
        for kart in self.kartlar:
            yer = self._hucre_indisi(kart["tarih"], kart["saat"])
            if yer is None:
                continue
            sutun, satir = yer
            sira = hucre_sayaci.get(yer, 0)
            hucre_sayaci[yer] = sira + 1
            self._kart_ciz(kart, sutun, satir, sira)

    def _kart_ciz(self, kart: dict, sutun: int, satir: int, sira: int) -> None:
        x = self.SOL + sutun * self.GUN_GENISLIK + 5
        y = self._satir_ustleri[satir] + 4 + sira * (self.KART_YUKSEKLIK + self.KART_ARASI)
        kilitli = kart.get("kilitli")
        uygulama = kart.get("tur") == "uygulama"
        dolgu = RENK["kilit"] if kilitli else (RENK["uygulama"] if uygulama else RENK["kart"])
        kenar = (RENK["kilit_kenar"] if kilitli
                 else (RENK["uygulama_kenar"] if uygulama else RENK["kart_kenar"]))
        etiketler = ("kart", f"kart:{kart['anahtar']}")
        secili = kart["anahtar"] == self.secili
        self.canvas.create_rectangle(x, y, x + self.GUN_GENISLIK - 10, y + self.KART_YUKSEKLIK,
                                     fill=dolgu, outline=RENK["secili_kenar"] if secili else kenar,
                                     width=3 if secili else 1, tags=etiketler)
        # Kilit emojisi (U+1F512) değil: Tk Linux'ta renkli emoji çizemez ve
        # DejaVu'da bu karakter yoktur, Pardus'ta kare görünüyordu.
        yazi = kart["baslik"] + (" ✓" if kilitli else "")
        self.canvas.create_text(x + 7, y + self.KART_YUKSEKLIK / 2, anchor="w", text=yazi,
                                font=("Segoe UI", 8), fill=RENK["kart_yazi"], tags=etiketler)

    def secimi_goster(self, anahtar: str | None) -> None:
        if anahtar != self.secili:
            self.secili = anahtar
            self.ciz()

    # ------------------------------------------------------ yer hesapları

    def _hucre_indisi(self, tarih: date, saat: time) -> tuple[int, int] | None:
        if tarih not in self.gunler or saat not in self.saatler:
            return None
        return self.gunler.index(tarih), self.saatler.index(saat)

    def _koordinattan_hucre(self, x: float, y: float) -> tuple[int, int] | None:
        if x < self.SOL or y < self.UST:
            return None
        sutun = int((x - self.SOL) // self.GUN_GENISLIK)
        satir = bisect_right(self._satir_ustleri, y) - 1
        if 0 <= sutun < len(self.gunler) and 0 <= satir < len(self.saatler):
            return sutun, satir
        return None

    def hucre_merkezi(self, tarih: date, saat: time) -> tuple[float, float]:
        """Bir hücrenin tuval üzerindeki orta noktası (sınama için)."""
        sutun, satir = self._hucre_indisi(tarih, saat)
        return (self.SOL + sutun * self.GUN_GENISLIK + self.GUN_GENISLIK / 2,
                (self._satir_ustleri[satir] + self._satir_ustleri[satir + 1]) / 2)

    # --------------------------------------------------------- olaylar

    def _basildi(self, olay) -> None:
        x, y = self.canvas.canvasx(olay.x), self.canvas.canvasy(olay.y)
        self.basis_noktasi = (x, y)
        self.surukleniyor = False
        for nesne in reversed(self.canvas.find_overlapping(x, y, x, y)):
            for etiket in self.canvas.gettags(nesne):
                if etiket.startswith("kart:"):
                    self.suruklenen = etiket.split(":", 1)[1]
                    return
        self.suruklenen = None

    def _suruklendi(self, olay) -> None:
        if not self.suruklenen:
            return
        x, y = self.canvas.canvasx(olay.x), self.canvas.canvasy(olay.y)
        if self.basis_noktasi and not self.surukleniyor:
            bx, by = self.basis_noktasi
            if abs(x - bx) + abs(y - by) < self.SURUKLEME_ESIGI:
                return
            self.surukleniyor = True
        hucre = self._koordinattan_hucre(x, y)
        if hucre == self.hedef_hucre:
            return
        self.hedef_hucre = hucre
        self.canvas.delete("hedef")
        if hucre:
            sutun, satir = hucre
            hx = self.SOL + sutun * self.GUN_GENISLIK
            ust, alt = self._satir_ustleri[satir], self._satir_ustleri[satir + 1]
            self.canvas.create_rectangle(hx + 2, ust + 2, hx + self.GUN_GENISLIK - 2, alt - 2,
                                         outline=RENK["hedef"], width=3, tags="hedef")

    def _birakildi(self, olay) -> None:
        self.canvas.delete("hedef")
        anahtar, self.suruklenen, self.hedef_hucre = self.suruklenen, None, None
        surukledi, self.surukleniyor = self.surukleniyor, False
        if not anahtar:
            return
        if not surukledi:
            if self.sec is not None:
                self.sec(anahtar)
            return
        hucre = self._koordinattan_hucre(self.canvas.canvasx(olay.x), self.canvas.canvasy(olay.y))
        if hucre is None:
            return
        sutun, satir = hucre
        self.birak(anahtar, self.gunler[sutun], self.saatler[satir])
