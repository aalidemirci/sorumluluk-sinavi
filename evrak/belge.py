"""Resmî evrak için .docx yapı taşları.

Belgeler şablon dosyasından değil doğrudan koddan üretilir: depoda ikili
dosya durmaz, şablon ile kod birbirinden kopmaz ve sayfa düzeni tek yerde
tanımlanır.

Düzen Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik'e
(RG 10.06.2020/31151) göredir: A4 (md.6), Times New Roman 12 punto, tabloda
gerektiğinde 9 puntoya kadar (md.7), üst/sol/sağ 1,5 cm kenar (md.8),
"T.C. / İDARE / Birim" başlığı (md.10). Renk kullanılmaz: evrak çoğunlukla
siyah-beyaz yazıcıdan çıkar. Gerekçe: kararlar/0011.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cekirdek.metin import buyult


YAZI_TIPI = "Times New Roman"
SIYAH = "000000"
BASLIK_ZEMINI = "D9D9D9"
CIZGI = "000000"
SOLUK = "404040"
UYARI_ZEMINI = "EDEDED"


def tr_tarih(deger: date | str | None) -> str:
    """Tarihi gg.aa.yyyy biçiminde yazar."""
    if deger is None or deger == "":
        return ""
    if isinstance(deger, str):
        try:
            deger = date.fromisoformat(deger[:10])
        except ValueError:
            return deger
    return deger.strftime("%d.%m.%Y")


@dataclass(frozen=True)
class Imzaci:
    """İmza bloğundaki bir sütun.

    OLUR sütununda onay tarihi elle yazılır; bu yüzden "…/…/20…" satırı
    bırakılır. Ad boşsa imzalayacak kişi elle yazar.
    """

    rol: str
    ad: str = ""
    unvan: str = ""
    tarih_satiri: bool = False


class Belge:
    """Tek bir resmî evrakı kuran yardımcı."""

    def __init__(self, antet: str | tuple[str, ...], baslik: str, alt_baslik: str = "",
                 yatay: bool = False):
        from docx import Document
        from docx.enum.section import WD_ORIENT
        from docx.shared import Mm, Pt, RGBColor

        self.belge = Document()
        bolum = self.belge.sections[0]
        if yatay:
            bolum.orientation = WD_ORIENT.LANDSCAPE
            bolum.page_width, bolum.page_height = Mm(297), Mm(210)
        else:
            bolum.orientation = WD_ORIENT.PORTRAIT
            bolum.page_width, bolum.page_height = Mm(210), Mm(297)
        bolum.left_margin = bolum.right_margin = Mm(15)
        bolum.top_margin = bolum.bottom_margin = Mm(15)
        bolum.header_distance = bolum.footer_distance = Mm(8)

        normal = self.belge.styles["Normal"]
        normal.font.name = YAZI_TIPI
        normal.font.size = Pt(12)
        normal.font.color.rgb = RGBColor.from_string(SIYAH)
        normal.paragraph_format.space_before = Pt(0)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.0

        self._altbilgi()
        self._antet((antet,) if isinstance(antet, str) else tuple(antet))
        self._baslik(baslik, alt_baslik)

    # ------------------------------------------------------------ düzen

    def _yazi(self, run, boyut=12.0, kalin=False, renk=SIYAH, italik=False):
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor
        run.font.name = YAZI_TIPI
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.get_or_add_rFonts()
        for nitelik in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(nitelik), YAZI_TIPI)
        run.font.size = Pt(boyut)
        run.bold = kalin
        run.italic = italik
        run.font.color.rgb = RGBColor.from_string(renk)
        return run

    def _kenarlik(self, paragraf, yer="bottom", renk=CIZGI, kalinlik="6"):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        ppr = paragraf._p.get_or_add_pPr()
        bdr = ppr.find(qn("w:pBdr"))
        if bdr is None:
            bdr = OxmlElement("w:pBdr")
            ppr.append(bdr)
        el = bdr.find(qn("w:" + yer))
        if el is None:
            el = OxmlElement("w:" + yer)
            bdr.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), kalinlik)
        el.set(qn("w:space"), "4")
        el.set(qn("w:color"), renk)

    @staticmethod
    def _golgele(nesne, renk):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        pr = (nesne._p.get_or_add_pPr() if hasattr(nesne, "_p")
              else nesne._tc.get_or_add_tcPr())
        shd = pr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            pr.append(shd)
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), renk)

    def _antet(self, satirlar: tuple[str, ...]) -> None:
        """Yönetmelik md.10: "T.C." / idarenin adı / birimin adı, ortalı.

        Evrakta program logosu yoktur: belge okulun evrakıdır, yazılımın
        tanıtımı değildir.
        """
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
        for sira, satir in enumerate(s for s in satirlar if s):
            paragraf = self.belge.add_paragraph()
            paragraf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraf.paragraph_format.space_after = Pt(0)
            self._yazi(paragraf.add_run(satir), 12, True)
        self.belge.add_paragraph().paragraph_format.space_after = Pt(2)

    def _altbilgi(self) -> None:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        paragraf = self.belge.sections[0].footer.paragraphs[0]
        paragraf.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        self._yazi(paragraf.add_run("Sayfa "), 8, False, SOLUK)
        alan = OxmlElement("w:fldSimple")
        alan.set(qn("w:instr"), "PAGE")
        paragraf._p.append(alan)

    def _baslik(self, baslik: str, alt_baslik: str) -> None:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
        paragraf = self.belge.add_paragraph()
        paragraf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraf.paragraph_format.space_after = Pt(2)
        # Yerleşik upper() Türkçede 'i' harfini bozar: LISTESI / LİSTESİ.
        self._yazi(paragraf.add_run(buyult(baslik)), 12, True)
        if alt_baslik:
            alt = self.belge.add_paragraph()
            alt.alignment = WD_ALIGN_PARAGRAPH.CENTER
            alt.paragraph_format.space_after = Pt(10)
            self._yazi(alt.add_run(alt_baslik), 10.5)

    def yeni_bolum_basligi(self, baslik: str, alt_baslik: str = '') -> None:
        """Sayfa sonrasında başlığı yeniden yazar; çok sayfalı evraklar için."""
        self._baslik(baslik, alt_baslik)

    # ------------------------------------------------------------ içerik

    def paragraf(self, metin: str, kalin: bool = False, boyut: float = 12,
                 renk: str = SIYAH, ortala: bool = False, bosluk: int = 6):
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
        paragraf = self.belge.add_paragraph()
        paragraf.paragraph_format.space_after = Pt(bosluk)
        paragraf.alignment = WD_ALIGN_PARAGRAPH.CENTER if ortala else WD_ALIGN_PARAGRAPH.JUSTIFY
        self._yazi(paragraf.add_run(metin), boyut, kalin, renk)
        return paragraf

    def bilgi_satirlari(self, ciftler: list[tuple[str, str]]) -> None:
        """Etiket/değer çiftlerini çerçevesiz bir bloğa yazar."""
        from docx.shared import Pt
        for etiket, deger in ciftler:
            paragraf = self.belge.add_paragraph()
            paragraf.paragraph_format.space_after = Pt(2)
            self._yazi(paragraf.add_run(f"{etiket}: "), 11, True)
            self._yazi(paragraf.add_run(str(deger)), 11)

    def tablo(self, basliklar: list[str], satirlar: list[tuple],
              genislikler: list[int] | None = None, bos_metin: str = "Kayıt yok"):
        """Başlık satırı gri zeminli, ince siyah çerçeveli bir tablo ekler.

        `genislikler` göreli oranlardır; kullanılabilir genişliğe ölçeklenir.
        Yazı 10 punto, yedi ve daha çok sütunda 9 puntodur (Yönetmelik md.7
        gerektiğinde 9 puntoya izin verir).
        """
        from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt

        sutun_sayisi = len(basliklar)
        tablo = self.belge.add_table(rows=1, cols=sutun_sayisi)
        tablo.alignment = WD_TABLE_ALIGNMENT.CENTER
        tablo.autofit = False

        bolum = self.belge.sections[0]
        kullanilabilir = int((bolum.page_width - bolum.left_margin - bolum.right_margin) / 635)
        if not genislikler or len(genislikler) != sutun_sayisi:
            taban = kullanilabilir // sutun_sayisi
            genislikler = [taban] * (sutun_sayisi - 1) + [kullanilabilir - taban * (sutun_sayisi - 1)]
        else:
            toplam = sum(genislikler)
            genislikler = [int(g * kullanilabilir / toplam) for g in genislikler]

        pr = tablo._tbl.tblPr
        tblw = OxmlElement("w:tblW")
        tblw.set(qn("w:w"), str(kullanilabilir))
        tblw.set(qn("w:type"), "dxa")
        pr.append(tblw)
        bordur = OxmlElement("w:tblBorders")
        for yon in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement("w:" + yon)
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), CIZGI)
            bordur.append(el)
        pr.append(bordur)
        for sutun, genislik in zip(tablo._tbl.tblGrid.gridCol_lst, genislikler):
            sutun.set(qn("w:w"), str(genislik))

        for hucre, baslik in zip(tablo.rows[0].cells, basliklar):
            hucre.text = baslik
        for veri in (satirlar or [(bos_metin,) + ("",) * (sutun_sayisi - 1)]):
            hucreler = tablo.add_row().cells
            for hucre, deger in zip(hucreler, list(veri) + [""] * sutun_sayisi):
                metin = "" if deger is None else str(deger)
                # Hücre içindeki satır sonu Word'de kendiliğinden alt satıra
                # geçmez; her satır ayrı paragraf olmalıdır (ör. komisyon üyeleri).
                satir_metinleri = metin.split("\n")
                hucre.text = satir_metinleri[0]
                for ek in satir_metinleri[1:]:
                    hucre.add_paragraph(ek)

        boyut = 9 if sutun_sayisi >= 7 else 10
        for satir_no, satir in enumerate(tablo.rows):
            trpr = satir._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if satir_no == 0:
                tekrar = OxmlElement("w:tblHeader")
                tekrar.set(qn("w:val"), "true")
                trpr.append(tekrar)
            for sutun_no, (hucre, genislik) in enumerate(zip(satir.cells, genislikler)):
                hucre.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                if satir_no == 0:
                    self._golgele(hucre, BASLIK_ZEMINI)
                tcw = hucre._tc.get_or_add_tcPr().get_or_add_tcW()
                tcw.set(qn("w:w"), str(genislik))
                tcw.set(qn("w:type"), "dxa")
                for paragraf in hucre.paragraphs:
                    paragraf.paragraph_format.space_before = Pt(1)
                    paragraf.paragraph_format.space_after = Pt(1)
                    paragraf.paragraph_format.line_spacing = 1.0
                    if satir_no == 0 or sutun_no == 0:
                        paragraf.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraf.runs:
                        self._yazi(run, boyut, satir_no == 0)
        self.belge.add_paragraph()
        return tablo

    def dayanak_notu(self, metin: str) -> None:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
        paragraf = self.belge.add_paragraph()
        paragraf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraf.paragraph_format.space_before = Pt(4)
        self._yazi(paragraf.add_run(metin), 9, False, SOLUK, italik=True)

    def imza_blogu(self, imzacilar: list[Imzaci]) -> None:
        """İmzacıları sekme duraklarıyla yan yana dizer; tablo kullanılmaz.

        Her sütun: rol, (OLUR'da) …/…/20… tarih satırı, imza boşluğu, ad,
        unvan. Ad ya da unvan boşsa elle yazılacak noktalı yer bırakılır.
        """
        from docx.enum.text import WD_TAB_ALIGNMENT
        from docx.shared import Mm, Pt

        if not imzacilar:
            return
        bolum = self.belge.sections[0]
        genislik = bolum.page_width - bolum.left_margin - bolum.right_margin
        adim = genislik / len(imzacilar)
        tarihli = any(i.tarih_satiri for i in imzacilar)
        satirlar = [
            ([i.rol for i in imzacilar], True, Pt(18)),
            *([([("…/…/20…" if i.tarih_satiri else "") for i in imzacilar], False, Pt(2))]
              if tarihli else []),
            ([i.ad or "…………………………" for i in imzacilar], False, Pt(28)),
            ([i.unvan for i in imzacilar], False, Pt(0)),
        ]
        for degerler, kalin, bosluk in satirlar:
            paragraf = self.belge.add_paragraph()
            paragraf.paragraph_format.space_before = bosluk
            paragraf.paragraph_format.space_after = Pt(0)
            paragraf.paragraph_format.keep_with_next = True
            for sira in range(len(imzacilar)):
                paragraf.paragraph_format.tab_stops.add_tab_stop(
                    Mm(int((adim * sira + adim / 2) / 36000)), WD_TAB_ALIGNMENT.CENTER)
            self._yazi(paragraf.add_run("\t" + "\t".join(degerler)), 11, kalin)

    def makam_satiri(self, metin: str) -> None:
        """Belgeyi çıkaran makamı sağa yaslı yazar; kişi adı içermez.

        İlan belgelerinde imza bloğu yerine bu kullanılır: çıktı herkese açık
        bir sayfada yayımlanacağı için imzalayanın adı yazılmaz.
        """
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
        paragraf = self.belge.add_paragraph()
        paragraf.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraf.paragraph_format.space_before = Pt(22)
        paragraf.paragraph_format.keep_together = True
        self._yazi(paragraf.add_run(metin), 12, True)

    def uyari(self, metin: str) -> None:
        """Siyah-beyaz yazıcıda da seçilen, çerçeveli uyarı satırı."""
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
        paragraf = self.belge.add_paragraph()
        paragraf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraf.paragraph_format.space_after = Pt(8)
        self._golgele(paragraf, UYARI_ZEMINI)
        for yer in ("top", "bottom", "left", "right"):
            self._kenarlik(paragraf, yer, CIZGI, "8")
        self._yazi(paragraf.add_run(metin), 11, True)

    def sayfa_sonu(self) -> None:
        from docx.enum.text import WD_BREAK
        self.belge.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------- kayıt

    def icerik_ozeti(self) -> str:
        """Belgenin görünen metninden SHA-256 özeti üretir.

        Dosya baytları kullanılamaz: .docx bir zip arşividir ve içindeki zaman
        damgaları her üretimde değiştiği için aynı içerik farklı bayt özeti
        verir. Sürüm numarası bu yüzden metne bağlanır — içerik değişmediyse
        yeni sürüm açılmaz.
        """
        parcalar: list[str] = []
        for bolum in self.belge.sections:
            for parca in (bolum.header, bolum.footer):
                parcalar.extend(p.text for p in parca.paragraphs)
        parcalar.extend(p.text for p in self.belge.paragraphs)
        for tablo in self.belge.tables:
            for satir in tablo.rows:
                parcalar.extend(h.text for h in satir.cells)
        metin = "\n".join(" ".join(p.split()) for p in parcalar)
        return hashlib.sha256(metin.encode("utf-8")).hexdigest()

    def kaydet(self, hedef: Path) -> str:
        """Belgeyi yazar ve içerik özetini döndürür."""
        hedef = Path(hedef)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        ozet = self.icerik_ozeti()
        self.belge.save(hedef)
        return ozet
