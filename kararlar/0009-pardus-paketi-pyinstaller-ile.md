# 0009 — Pardus paketi bütünleşiktir, sistem Python'ına dayanmaz

**Durum:** Kabul — 29.08.2026

## Bağlam

Okullardaki bilgisayarların bir bölümü Pardus kullanıyor; etkileşimli
tahtalarda ETAP, masaüstlerinde Pardus 23 var. Uygulama şimdiye kadar
yalnızca Windows için paketlendi.

Pardus 23 Debian 12 (bookworm) tabanlıdır: çekirdek 6.1, glibc 2.36, sistem
Python'ı 3.11. Debian paket biçimi (`.deb`) doğrudan çalışır.

## Karar

Pardus için `.deb` paketi üretilir. Paketin içine, Windows'ta olduğu gibi
PyInstaller çıktısı konur: yorumlayıcı, üçüncü taraf kitaplıklar ve Tcl/Tk
paketin içindedir. Paket `/opt/sorumluluk-sinavi` altına açılır; `/usr/bin`
bağlantısı ve menü girdisi eklenir.

Paket **debian:12 kabında** derlenir — hem yerelde hem GitHub Actions'ta.

## Gerekçe

Elenen seçenek, Debian'ın kendi paketlerine dayanan "ince" bir `.deb`
(`Depends: python3-tk, python3-docx, python3-openpyxl…`) idi. İki nedenle
elendi:

1. **Sürümler tutmuyor.** Debian 12'nin `python3-docx` paketi 0.8.11'dir,
   uygulama 1.1 ister; arada API değişti. `python3-xlrd` 2.0.1'dir, biz
   2.0.2'ye sabitliyoruz. Beş bağımlılığın ikisi daha baştan uymuyor.
2. **Çevrimdışı kurulumu kırıyor.** Deposuna erişemeyen bir okul
   makinesinde `apt install ./paket.deb` eksik bağımlılığı indiremez.
   Windows tarafındaki söz — tek dosya, Python istemez — Pardus tarafında da
   geçerli olmalıdır (bkz. [0001](0001-cevrimdisi-ve-yerel-veri.md)).

Kabın Debian 12 olması zorunludur: **glibc ileriye uyumludur, geriye
değil.** Ubuntu 24.04 koşucusunda (glibc 2.39) derlenen ikili Pardus 23'te
(glibc 2.36) açılmaz; hata da "dosya bulunamadı" gibi yanıltıcı bir biçimde
görünür. Debian 12'de derlenen paket ise Debian 12 ve üzerinin tamamında
çalışır.

## Sonuçlar

- Paket ~16 MB, kurulu hâli ~46 MB'dir. İnce paket ~2 MB olurdu; fark,
  çevrimdışı kurulum ve sürüm bağımsızlığı için ödenen bedeldir.
- Pardus 25 (Debian 13) çıktığında paket **yeniden derlenmeden de çalışır**;
  yalnız yeni tabana geçildiğinde kabın sürümü de yükseltilmelidir.
- `X11` yığını (`libx11-6`, `libxext6`, `libxft2`, `libfontconfig1`) pakete
  konmaz, `Depends` ile istenir. Bu kitaplıklar her Pardus masaüstü
  kurulumunda zaten yüklüdür; çevrimdışı kurulumu engellemezler.
- Windows ve Pardus **aynı `.spec` dosyasını** kullanır. Windows'a özgü iki
  parça (sürüm kaynağı, `.ico` simge) `WINDOWS` koşuluna bağlıdır; ikinci
  bir spec dosyası tutulmaz.
- Uygulama verisi Linux'ta `~/.local/share/sorumluluk-sinavi/plan`
  altındadır; paket kaldırıldığında dokunulmaz.
- Paketleme yolunun bozulmadığı GitHub Actions'ta, belge dışı her itmede
  denetlenir: paket üretilir, kaba kurulur ve xvfb altında açılıp
  açılmadığına bakılır. Yayıma ekleme `release: published` olayına bağlıdır
  (etiket itmesi `paths-ignore` süzgecine takılacağı için).
