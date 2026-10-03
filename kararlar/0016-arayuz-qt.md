# 0016 — Arayüz Qt for Python (PySide6) ile yazılır

**Durum:** Kabul — 03.10.2026

## Bağlam

Arayüz Tkinter/ttk ile yazılmıştı. Kullanıcı değerlendirmesi (03.10.2026):
beklemeli ya da devamsız öğrenci seçmek çok zor, arayüz tasarımı ilkel.
Somut sorunlar:

- `ttk.Treeview` hücrede onay kutusu, süzülmüş ya da sıralanmış görünüm
  sunmaz. Başvuru işareti "öğrenciyi seç → kutuyu işaretle → Kaydet" diye üç
  adımdı ve yüzlerce satırlık, aranamayan listede yapılıyordu. Her kayıttan
  sonra sayfa baştan çiziliyor, seçim ve kaydırma kayboluyordu.
- Tk 8.6 Linux'ta emoji ve yazı tipi yedeği bilmez: Pardus'un DejaVu yazı
  tipinde düğmeler taştı, kilit emojisi kare çıktı (03.10.2026).
- Pencere 1380×860 sabitti ve okullarda yaygın 1366×768 ekrana sığmıyordu.
- Plan üretimi arayüz iş parçacığında yürüyor, bir dakikaya kadar pencereyi
  donduruyordu.
- Bütün ekranlar tek bir 1.850 satırlık modüldeydi (`arayuz/uygulama.py`).

Kullanıcı kararı: Qt'ye geçilsin, bütün ekranlar elden geçsin.

## Karar

- Arayüz PySide6-Essentials (Qt 6) ile yazılır. Görünüm Fusion stili ve
  koddan üretilen stil sayfasıdır; renkler yalnız `arayuz/palet.py`'dedir.
  Simgeler koda gömülü SVG çizimleridir; emoji ve simge yazı tipi
  kullanılmaz.
- Her adım `arayuz/sayfalar/` altında ayrı bir modüldür ve ilk açılışta
  yüklenir. Ortak parçalar `arayuz/bilesenler.py`'dedir: model/görünüm
  tabloları Türk alfabesine göre sıralar, Türkçe karakterden bağımsız arar,
  onay kutusu sütunu taşır ve yenilemede seçimi korur.
- Uzun işler (plan ve evrak üretimi, içe aktarma, güncelleme denetimi)
  `QThreadPool`'da yürür. Veritabanı bağlantısı çağrı başına açıldığı için
  iş parçacığı güvenlidir.
- Yalnız QtCore, QtGui, QtWidgets ve QtSvg kullanılır. Qt'nin ağ modülü
  pakete girmez, içe aktarılması `testler/test_ag_yalitimi.py` ile yasaktır
  (bkz. [0015](0015-guncelleme-denetimi.md)).
- Qt burada GNU LGPL sürüm 3 ile kullanılır. Kitaplıklar değiştirilmez ve
  ayrı paylaşımlı dosyalar olarak dağıtılır (PyInstaller'ın klasör çıktısı);
  kullanıcı onları uyumlu bir sürümle değiştirebilir. LGPL ve GPL metinleri
  `LICENSES/` klasöründe pakete girer, NOTICE dağıtılan sürümün kaynak
  kodu adresini yazar, Hakkında sayfası Qt'nin telif bildirimini gösterir.
  Sürüm `pyproject.toml`'da tam sabittir; `testler/test_lisans.py` NOTICE ile
  sabitlemenin ayrışmasını engeller.
- Katman kuralı değişmez: `arayuz → veri → cekirdek`.
- Arayüz testleri pytest-qt ile ekransız (`offscreen`) koşar; sanal ekran
  gerekmez.

## Gerekçe

Elenen seçenekler:

1. **Tk'yi iyileştirmek** (ttk teması, sv-ttk, CustomTkinter). Görünüm
   düzelir ama tablo içi onay kutusu, süzgeçli model/görünüm, yazı tipi
   yedeği ve DPI sorunları kalır; CustomTkinter'da tablo bileşeni yoktur.
2. **Web arayüzü** (yerel sunucu ve tarayıcı, pywebview ya da Electron).
   Kardeş projeler web tabanlıdır, ama bu program tek bilgisayarda çalışan
   masaüstü uygulamasıdır: yerel HTTP sunucusu 0001'in ağsız çalışma
   ilkesine ters düşer, Electron paketi Qt'den büyüktür, pywebview Pardus'ta
   WebKitGTK'ye bağımlıdır.
3. **PyQt6.** Aynı Qt, ama GPL ya da ticari lisanslıdır. Program PolyForm
   Noncommercial ile yayımlandığı için GPL'li bir kitaplıkla birleştirilemez.
   PySide6 LGPL'dir ve Qt'nin resmî Python bağıdır.
4. **wxPython.** Yerel görünüm verir ama Linux'ta GTK3'e bağlıdır, tablo
   bileşeni (`wx.grid`) Qt'nin model/görünümünden zayıftır, Pardus için
   paketlemesi daha zordur.

Qt'nin bedeli paket boyutudur. Kullanılmayan parçalar ayıklanır (öbür
dillerin çevirileri, ağ modülü, OpenGL yazılım yedeği, gömülü sistem ve
Wayland eklentileri, açılmayan resim biçimleri); gerekçeleri
`SorumlulukSinavi.spec` içindedir.

## Sonuçlar

- Windows kurulum dosyası ~15 MB'den ~25 MB'ye çıktı, kurulu hâli ~73 MB.
  Pardus paketi ~16 MB'den ~39 MB'ye, kurulu hâli ~45 MB'den ~135 MB'ye
  çıktı; Linux'ta Qt'nin ICU verisi (30 MB) tek başına büyük paydır.
- Pardus paketi Qt'nin X11 eklentisini ve onun istediği xcb kitaplıklarını
  taşır; sistemden yalnız her masaüstünde kurulu olan `libgl1`, `libegl1`,
  `libxcb1` ve `libfontconfig1` istenir. `yapim/deb_paketi.py` paketin
  bunların dışında bir sistem kitaplığına bağlanmasına izin vermez; paket
  ayrıca temiz bir Debian 12'ye kurularak denenir (bkz.
  [0009](0009-pardus-paketi-pyinstaller-ile.md)).
- Linux'ta yalnız X11 (xcb) platformu pakettedir; Wayland oturumunda
  program XWayland üzerinden açılır.
- Windows kurulumu yükseltmede eski `_internal` klasörünü siler; Tk
  sürümünden kalan Tcl/Tk dosyaları geride kalmaz.
- Pencere boyu ve güncelleme tercihleri veri klasöründeki `arayuz.ini`
  dosyasında durur; Windows kayıt defterine yazılmaz.
- Qt sürümü yükseltilirken NOTICE, yardım metnindeki bildirim ve
  `pyproject.toml` birlikte değişir; Pardus derlemesi yeni bir sistem
  bağımlılığını yakalar.
