# Kurulum ve kullanım

## Kurulum (Windows)

`dist-kurulum/` klasöründeki `SorumlulukSinavi-Kurulum-<sürüm>.exe`
dosyasını çalıştırın.

- Kurulum **kullanıcı başınadır**: yönetici hakkı istemez, Program Files'a
  yazmaz. Varsayılan yer `%LOCALAPPDATA%\SorumlulukSinavi\uygulama`.
- Başlat menüsüne kısayol eklenir; masaüstü kısayolu isteğe bağlıdır.
- Python kurulu olmasına gerek yoktur.
- Yeni sürüm eskisinin üzerine kurulur ve **veritabanınıza dokunmaz.** Eski
  sürümün program dosyaları (`_internal` klasörü) kurulumdan önce silinir;
  veri ayrı klasördedir.
- Kaldırma Başlat menüsünden ya da Ayarlar → Uygulamalar üzerinden yapılır;
  kaldırma da veritabanını silmez.

Kurulum dosyasını yeniden üretmek için Inno Setup 6 gerekir
(`winget install JRSoftware.InnoSetup`):

```bash
python -m PyInstaller SorumlulukSinavi.spec --noconfirm
iscc yapim/sorumluluk_sinavi.iss
```

## Kurulum (Pardus)

`sorumluluk-sinavi_<sürüm>_amd64.deb` dosyasını indirin ve kurun:

```bash
sudo apt install ./sorumluluk-sinavi_0.5.0_amd64.deb
```

- Pardus 23 ve üzeri (Debian 12 tabanlı her dağıtım) desteklenir. Paket
  Debian 12 kabında derlenir; daha yeni bir dağıtımda da çalışır, daha
  eskisinde çalışmaz.
- **Python kurulu olmasına gerek yoktur**; yorumlayıcı, Qt ve bütün
  kitaplıklar paketin içindedir. Kurulum internet istemez: paketin sistemden
  beklediği kitaplıklar (`libgl1`, `libegl1`, `libxcb1`, `libfontconfig1`)
  her masaüstü kurulumunda zaten yüklüdür.
- Program X11 üzerinde çalışır; Wayland oturumunda XWayland üzerinden açılır.
- Uygulama menüde **Ofis** ve **Eğitim** altında görünür; uçbirimden
  `sorumluluk-sinavi` komutuyla da açılır.
- Veritabanı `~/.local/share/sorumluluk-sinavi/plan` altındadır. Veri
  **kullanıcı başınadır**; paketi kaldırmak veriye dokunmaz.
- Yeni sürüm eskisinin üzerine kurulur:
  `sudo apt install ./sorumluluk-sinavi_<yeni sürüm>_amd64.deb`.
- Kaldırmak için: `sudo apt remove sorumluluk-sinavi`.

İndirilen dosyayı doğrulamak için yayımdaki `SHA256SUMS-<sürüm>-pardus.txt`
dosyasını yanına koyup:

```bash
sha256sum -c SHA256SUMS-0.5.0-pardus.txt
```

## Kurulu makineleri güncelleme

Yeni sürüm eskisinin üzerine kurulur; önce kaldırmaya gerek yoktur.
Veritabanı kurulum klasöründe değil ayrı bir yerde durduğu için güncelleme
**veriye dokunmaz**: ilk açılışta gereken şema göçü uygulanır, öncesinde de
otomatik yedek alınır.

Kurulum dosyasını hedef makineye götürüp çalıştırmak yeterlidir. Yönetici
hakkı gerekmez.

Aşağıdaki iki komut **PowerShell** içindir; kurulum dosyasının bulunduğu
klasörde çalıştırın.

Soru sormadan kurulması için:

```powershell
.\SorumlulukSinavi-Kurulum-0.5.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Kurulu sürümü doğrulamak için:

```powershell
(Get-Item "$env:LOCALAPPDATA\SorumlulukSinavi\uygulama\SorumlulukSinavi.exe").VersionInfo.FileVersion
```

Bilinmesi gerekenler:

- **Kurulum kullanıcı başınadır.** Bir bilgisayarı birden çok kişi kendi
  Windows hesabıyla kullanıyorsa her hesapta ayrı kurulum gerekir; her
  hesabın verisi de ayrıdır.
- **Sürüm numarası 0.4.0'dan itibaren güvenilirdir.** 0.3.0 numarasıyla iki
  farklı paket derlendi; o numarayı taşıyan bir kurulum gördüğünüzde hangi
  içerik olduğunu ayırt etmeye uğraşmayın, üzerine 0.4.0 kurun. 0.4.0'dan
  sonra sürüm exe'nin dosya özelliklerinde de yazılıdır.
- **Hayalet kayıt.** Kurulum klasörü, kaldırma yapılmadan elle silinmişse
  Ayarlar → Uygulamalar listesinde kaldırılamayan bir kayıt kalır
  (`unins000.exe` bulunamaz). Üzerine yeni sürüm kurmak bu kaydı düzeltir;
  ayrıca bir şey yapmanız gerekmez.
- **Kurulum günlüğü.** 0.8.5'ten beri her kurulum `%TEMP%` altına
  `Setup Log …` adlı bir günlük bırakır; kurulumda bir sorun olursa nedeni
  oradan görülür. Günlükte öğrenci verisi yoktur, Windows kullanıcı adı geçer.
- **Kaldırma veritabanını silmez.** Veri `%LOCALAPPDATA%\SorumlulukSinavi\plan`
  altında kalır. Makineyi tamamen temizlemek istiyorsanız o klasörü elle
  silin — öncesinde aşağıdaki Yedekleme bölümünü okuyun.

## Güncelleme denetimi

Program açıldıktan birkaç saniye sonra yayımlanan son sürümün numarasını
sorar. Yeni sürüm varsa pencerenin üstünde bir şerit çıkar; **Daha sonra** o
sürüm için şeridi kapatır. İstek yalnız sürüm bilgisini alır; öğrenci,
personel ya da okul verisi gönderilmez. İnternet yoksa ya da ağ GitHub'ı
engelliyorsa denetim sessizce geçer, program çalışmaya devam eder.

- **Windows:** Hakkında sayfasındaki **Doğrula ve indir**, kurulum dosyasını
  `%LOCALAPPDATA%\SorumlulukSinavi\guncelleme` altına indirir ve yayımlanan
  SHA-256 özetiyle karşılaştırır; özet tutmayan dosya kullanılmaz. İndirme
  sürerken inen ve toplam boyut görünür. **Kurulumu başlat** programı
  kapatıp kurulumu açar. Program açılırken bu klasördeki, kurulu sürümden
  yeni olmayan kurulum dosyalarını siler; klasörde birikme olmaz.
- **Pardus:** yeni paket indirme sayfasından alınıp yukarıdaki gibi kurulur;
  `sudo` gerektiren kurulumu program kendisi yapmaz.

Denetimi kapatmak için Hakkında sayfasındaki **Program açılırken yeni sürümü
denetle** seçeneğini kaldırın. Kurum genelinde kapatmak için
`SORUMLULUK_GUNCELLEME_DENETIMI` ortam değişkenini `0` yapın; o zaman
Hakkında sayfasındaki seçenek kapalı ve değiştirilemez görünür. Windows'ta
kullanıcı için:

```powershell
setx SORUMLULUK_GUNCELLEME_DENETIMI 0
```

Pardus'ta aynı satır (`SORUMLULUK_GUNCELLEME_DENETIMI=0`) `/etc/environment`
dosyasına eklenir. Programın internete çıkan tek isteği budur; gerekçe
[kararlar/0015](kararlar/0015-guncelleme-denetimi.md).

## Kurulumsuz deneme

`dist/SorumlulukSinavi/SorumlulukSinavi.exe` doğrudan çalıştırılabilir.
Klasörün tamamını taşıyın — `_internal` olmadan çalışmaz.

İlk açılışta veritabanı `%LOCALAPPDATA%\SorumlulukSinavi\plan\sorumluluk.db`
altında kendiliğinden oluşur.

### Denemeyi ayrı bir klasörde yapmak

Gerçek verinizi bozmadan denemek isterseniz, uygulamayı başlatmadan önce
veri klasörünü değiştirin:

```bash
set SORUMLULUK_VERI_KLASORU=C:\Users\%USERNAME%\Desktop\sorumluluk-deneme
```

## Kullanım sırası

Soldaki adımlar sırayla tamamlanmalıdır; her adım bir sonrakinin girdisidir.

1. **Kurum Ayarları** — okul bilgileri ve üç dönem tarihi (gg.aa.yyyy). Sınav
   pencereleri (Eylül/Şubat/Haziran) bu tarihlerden hesaplanır ve ekranın
   altında gösterilir. Evrak anteti (boşsa ilçeden türetilir) ile düzenleyenin
   adı ve unvanı da buradadır. Aynı ekranda **tatil ve idari izin günlerini**
   girin ve **Yedek al** düğmesiyle veritabanını yedekleyin.
2. **Öğretmen Listesi** — e-Okul'dan `OOK01001R1` raporunu alın (aşağıdaki
   indirme yönergesine uyun). Önce **önizleme** açılır; onaylamadan hiçbir
   kayıt değişmez. Branş havuzu bu rapordan kurulur. Rapora yansımamış bir
   kişiyi elle ekleyebilir, ayrılan kişiyi pasife alabilirsiniz; görevi olan
   kişi silinemez. Seçili öğretmenin dersi, izni ya da başka görevi olan
   saatlerini **Müsaitlik…** penceresine girin; planlayıcı bu saatlere görev
   vermez (OKY md.58/2-ç). Açıklamaya sağlık bilgisi yazmayın.
3. **Salonlar** — sınav salonlarını ve kapasitelerini girin. Salon sayısı,
   aynı saatte kaç sınav yapılabileceğini belirler.
4. **e-Okul Sorumluluk** — `OOK12001R010` raporunu seçin. Rapor okulun
   tamamını kapsıyorsa "tam listedir" işaretli kalsın; kısmi bir liste
   aktarıyorsanız işareti kaldırın, yoksa dosyada olmayan kayıtlar pasife
   alınır.
5. **Başvuru** — üç sekmede yürür (OKY md.58/2-d):
   - **İşaretler:** beklemeli ve devamsız öğrencileri işaretleyin. Listede ad,
     okul numarası ya da şubeyle arayın (Türkçe karakter yazmanız gerekmez);
     şube, "Yalnız 12. sınıflar" ve "Yalnız işaretliler" süzgeçleri vardır.
     Satırdaki kutucuğu tıklamak hemen kaydeder; alttaki bildirimdeki **Geri
     al** işareti kaldırır. Birden çok satırı Ctrl ya da Shift ile seçip
     **Beklemeli işaretle** / **Devamsız işaretle** ile toplu işaretleyebilir,
     e-Okul'dan kopyaladığınız okul numaralarını **Numara listesiyle
     işaretle…** penceresine yapıştırabilirsiniz; pencere önce hangi numaranın
     kime karşılık geldiğini, bulunamayanları ve iki şubede geçenleri
     gösterir. Önceki öğretim yılından kalan işaretler sarı görünür; gözden
     geçirip yeniden işaretleyin.
   - **Duyuru:** başvuru duyurusunu kaydedin. Son gün, sınav penceresinin
     ilk gününden en az 5 iş günü önce olmalıdır; ekran en geç günü gösterir.
   - **Başvuru kararları:** her öğrencinin başvuru tarihini ve dilekçe
     bilgisini girin; **Kaydet ve sonrakine geç** sıradaki öğrenciyi açar.
     Son günden sonraki başvuru müdür onayıyla kabul edilir; onay alanı
     ancak o zaman açılır.
6. **Ders / Branş** — her dersi bir branşa eşleyin. Türk dili ve edebiyatı ile
   yabancı dil derslerini **iki aşamalı** işaretleyin (OKY md.58/2-e); uygulama
   ders adına bakarak öneri getirir ama kararı siz verirsiniz. Birleşik
   derslerde (ör. Görsel Sanatlar/Müzik) ikinci alanı da seçin. Okulda
   öğretmeni olmayan bir branş gerekiyorsa branş havuzuna elle ekleyin.
7. **Sınav Planı** — dönemi ve parametreleri seçin, isterseniz önce **Yükü
   çözümle** ile gün seçeneklerinin sonucunu görün, sonra **Planı üret**.
8. **Evrak ve Teslim** — planı kaydettikten sonra belgeleri üretin; sınavlardan
   sonra geri alınan evrakı teslim çizelgesine işleyin.
9. **Yardım** — mevzuat hükümleri, kullanım ve çalışma mantığı bu sayfadadır.
10. **Hakkında** — sürüm, güncelleme denetimi, geliştirici ve kullanım
    koşulları.

Kısayollar: **Ctrl+1 … Ctrl+0** adımlar arasında geçer, **Ctrl+F** sayfadaki
aramaya gider, **Ctrl+S** kaydeder, plan ekranında **Ctrl+Z / Ctrl+Y**
taşımayı geri ve ileri alır, **F1** yardımı açar.

Tek ders sınavı (OKY md.58/6): olağan sınavların sonucu e-Okul'a girildikten
sonra Sınav Planı ekranında dönem kutusundan "… — tek ders (58/6)" seçeneğini
seçin, **Tek ders öğrencileri…** penceresinde öğrencinin başarısız kaldığı tek
dersi işaretleyin ve planı üretin. Plan, olağan plandaki son sınavın haftasından
sonraki haftaya kurulur.

## e-Okul raporlarını indirme

Raporu doğrudan "Excel'e aktar" ile indirmeyin: biçimlendirilmiş çıktı birleşik
hücreler ve tekrarlanan başlıklar içerir, program bunu okuyamaz.

1. Raporu e-Okul'da açın, görüntüleyici seçeneklerinden **HTML5 görüntüleyiciyi**
   seçin.
2. Görüntüleyicinin dışa aktarma menüsünden **Excel** biçimini seçin.
3. Açılan seçeneklerde **SADECE VERİ** (yalnızca veri / data only) seçeneğini
   işaretleyin.
4. İnen `.xls` ya da `.xlsx` dosyasını açıp kaydetmeden programa yükleyin.

Aynı yönerge ilgili ekranların üstünde ve Yardım sayfasında da yazılıdır.

| Ekran | Rapor |
|---|---|
| 02 Öğretmen Listesi | `OOK01001R1` — Kurum Personel Listesi |
| 04 e-Okul Sorumluluk | `OOK12001R010` — Sorumluluk Sınavına Girecek Öğrenci Listesi |

## Plan ekranı

- Dönem kutusu açılışta bugüne göre seçilir (içinde bulunulan ya da sıradaki
  dönem). Dönem değiştirilince o dönemin kayıtlı planı açılır.
- Kartı başka bir gün/saat hücresine **sürükleyip bırakın.** Öğrenci,
  öğretmen ve salon çakışmaları ayrı ayrı denetlenir; engel doğuran taşıma
  otomatik geri alınır ve kimin çakıştığı yazılır. Hedef saatte sınavın
  salonu doluysa sınav aynı sayıda boş salona geçirilir; bildirim bunu
  söyler.
- Hafta sonuna bırakılan kart için **gerekçe** sorulur (OKY md.58/2-ç);
  önerilen metni değiştirebilirsiniz, vazgeçerseniz kart yerinde kalır.
- İki aşamalı derste yazılı kartı taşınınca uygulama da aynı gün ve saat
  farkıyla gelir; uygulama kartı ise tek başına başka bir güne taşınabilir
  (OKY md.58/2-e: farklı günlerde de yapılabilir).
- Karta **tıklayınca** sınavın görevlileri sağdaki **Seçili sınav** kartında
  görünür.
  **Görevliyi değiştir…** penceresinde değiştirilecek kişiyi ve yerine gelecek
  kişiyi seçersiniz; uygun olmayanlar nedeniyle listelenir. Taslak planda
  değişiklik bellekte kalır, kesinleşmiş planda müdür onay numarası ve
  gerekçeyle hemen kaydedilir ve görevlendirme çizelgesinde listelenir.
- **Geri al / İleri al** (Ctrl+Z / Ctrl+Y) ile adım adım gezinebilirsiniz
  (görevli değişikliği dâhil). Kaydedilmemiş plan başka sayfaya gidip dönünce
  kaybolmaz; program kapatılırken sorulur.
- Plan **Kaydet** (Ctrl+S) denene kadar veritabanına yazılmaz.
- Plan arka planda üretilir; üretim sürerken pencere donmaz.
- **Müdür onayıyla kesinleştir** planı kilitler; kesinleşmiş oturum taşınamaz,
  kesinleşmiş plan silinemez ve yerine yeni plan kaydedilemez.

Sağdaki **Kural denetimi** listesi kural ihlallerini gösterir: kırmızı
satırlar engel, sarı satırlar uyarıdır. Engelli plan taslak olarak
kaydedilebilir ama kesinleştirilemez.

## Evrak ve teslim ekranı

**Evrak üretimi** sekmesinde üretmek istediğiniz belgeleri işaretleyip klasör
seçersiniz; belgeler .docx olarak oraya yazılır. Aynı içerik yeniden
üretilirse sürüm numarası artmaz.

Listedeki **İLAN** başlıklı iki belge okul web sayfasında yayımlanmak içindir.
Bunları üretmeden önce aynı sekmedeki **öğrenci gösterimi** seçeneğini gözden
geçirin; öğrencinin açık adı hiçbir seçenekte yayımlanmaz.

**Görevlendirme çizelgesi** komisyon bazlıdır: her satır bir sınav komisyonudur,
gözcüler salonlarıyla yazılır. İkinci sayfasında görevli her personelin tarih
yazıp imzalayacağı tebliğ-tebellüğ tablosu vardır; çizelge yatay A4 olarak
üretilir. **Kişi bazlı görev çizelgesi** her görevlinin kendi görevlerini
(tarih, saat, sınav, görev, salon) ve tebellüğ imzasını tek satırda toplar.

Evrak Resmî Yazışma Yönetmeliği biçimindedir (T.C. başlığı, Times New Roman,
siyah-beyaz). Antetin ikinci satırı ve düzenleyen bilgisi Kurum Ayarları'ndan
gelir.

**Teslim çizelgesi** sekmesinde her oturum için beklenen evrak listelenir.
Bir ya da birden çok satırı seçip teslim eden ile teslim alan görevliyi,
varsa adedi ve teslim tarihini (varsayılan bugün) girerek **Seçilenleri
teslim al** düğmesine basın; yanlış işlenen teslim **Teslimi geri al** ile
kaldırılır. Teslim eden ile alan aynı kişi olamaz. Yeşil satır teslim alınmış,
kırmızı satır süresinde gelmemiş evrakı gösterir; teslim süresi sınav tarihini
izleyen ilk iş günüdür (tatil günleri iş günü sayılmaz).

## Yedekleme

Kurum Ayarları ekranındaki **Yedek al…** düğmesi veritabanının tam yedeğini
(WAL dâhil) seçtiğiniz klasöre `sorumluluk-yedek-<tarih>.db` adıyla alır;
uygulamayı kapatmanız gerekmez. Elle yedeklemek isterseniz uygulamayı kapatıp
veri klasöründeki `sorumluluk.db` dosyasını kurumun yedek ortamına kopyalayın.
Şema yükseltmelerinde uygulama göç öncesi otomatik yedek alır (`.yedek`
uzantılı); bu yedek WAL içeriğini de kapsar.

Gerçek veriyi e-posta, kişisel bulut veya Git deposuna koymayın.

## Paketi yeniden üretmek

```bash
.venv/Scripts/python -m PyInstaller SorumlulukSinavi.spec --noconfirm
```

Pakete `veri/gocler/*.sql`, `tzdata` ve `LICENSES/` girmek zorundadır: ilki
şemayı kurar, ikincisi olmadan `Europe/Istanbul` saat dilimi Windows'ta
çözülemez, üçüncüsü Qt'nin LGPL-3.0 koşuludur. Qt'nin kullanılmayan parçaları
(öbür dillerin çevirileri, ağ modülü, gömülü sistem ve Wayland eklentileri)
betikte süzülür; gerekçeleri `SorumlulukSinavi.spec` içinde yazılıdır.

### Pardus paketini üretmek

Paket, GitHub Actions'ta `debian:12` kabında kendiliğinden üretilir
(`.github/workflows/pardus-paketi.yml`); elle üretmek gerekirse aynı kap
kullanılır. Ubuntu ya da başka bir dağıtımda derlemeyin: **glibc ileriye
uyumludur, geriye değil** — daha yeni bir tabanda derlenen ikili Pardus
23'te açılmaz. Gerekçenin tamamı
[kararlar/0009](kararlar/0009-pardus-paketi-pyinstaller-ile.md).

Docker kurulu bir makinede, depo kökünde:

```bash
docker run --rm -v "$PWD:/kaynak" -w /kaynak debian:12 bash -c "apt-get update && apt-get install -y --no-install-recommends python3-venv libpython3.11 dpkg-dev binutils libgl1 libegl1 libfontconfig1 libdbus-1-3 libglib2.0-0 libxkbcommon0 libxkbcommon-x11-0 libx11-xcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 && python3 -m venv /tmp/o && /tmp/o/bin/pip install -e . pyinstaller && /tmp/o/bin/python yapim/deb_paketi.py"
```

Çıktı `dist-kurulum/` altına düşer: `.deb` dosyası ve SHA-256 özeti. Kaptaki
Qt kitaplıkları pakete girer; biri eksikse betik hangi dosyanın neyi
bulamadığını yazıp durur (`bagimlilik_sorunlari`). Depo bu komutta kaba
yazılabilir bağlanır ve `dist/` klasörü Linux çıktısıyla değişir; Windows
paketini derlemeden önce PyInstaller'ı yeniden çalıştırın.

### Testler GitHub'da da koşar

`.github/workflows/testler.yml` her itmede ve her birleştirme isteğinde
takımı üç ortamda koşturur: Windows'ta Python 3.11 ve 3.12, bir de Pardus
23'ün tabanı olan Debian 12 kabında. Arayüz testleri Qt'yi ekransız kipte
kurar, sanal ekran gerekmez. Bu makinedeki `pytest` bunun yerini tutmaz —
özellikle Linux ayağı burada hiç denenmiyor.

Pardus paketi iş akışı (`pardus-paketi.yml`) paketi üretir, sonra **temiz**
bir Debian 12 kabına kurup sanal ekranda açar: derleme kabında Qt'nin bütün
kitaplıkları kurulu olduğundan eksik bir `Depends` satırı ancak orada görünür.

Yalnız `.md`, `LICENSE` ve `NOTICE` değiştiren itmelerde iki iş akışı da
koşmaz (`paths-ignore`). Listeye kod, test, `.gitignore` ya da iş akışı
dosyası eklemeyin.

### Sürüm yükseltmek

Sıra: `SURUM` güncellenir → CHANGELOG'da başlık açılır → testler koşar →
paketler derlenir → commit → `git tag -a vX.Y.Z`.

Yayımdaki dosya adları programın güncelleme denetiminin sözleşmesidir:
etiket `vX.Y.Z`, kurulum dosyası `SorumlulukSinavi-Kurulum-X.Y.Z.exe`, üç
paketi kapsayan özet `SHA256SUMS-X.Y.Z.txt`. Adlar değişirse kurulu programlar
yeni sürümü bulur ama indiremez ([kararlar/0015](kararlar/0015-guncelleme-denetimi.md)).

Sürüm numarası tek yerde durur: `cekirdek/surum.py` içindeki `SURUM`.
Arayüzdeki hakkında penceresi, `pyproject.toml`, PyInstaller betiği (exe'nin
dosya özelliklerine gömülen sürüm kaynağı), Inno Setup betiği ve Pardus
paketi betiği (`.deb` dosyasının adı ile `DEBIAN/control` içindeki `Version`)
bu değeri oradan okur; başka hiçbir dosyada elle yazmayın.

Sıranın sonu şudur: etiketi itin, GitHub'da **yayımı açın** (Windows
paketlerini oraya yükleyerek). Yayım açıldığı anda GitHub Actions Pardus
paketini üretip aynı yayıma ekler.

Tetikleyici bilerek etiket itmesi değil `release: published` olayıdır:
iş akışındaki `paths-ignore` süzgeci `push` olayına takılıdır ve etiket,
main zaten itildikten sonra konduğu için o push'ta değişen dosya yoktur —
süzgeç etiket itmesini sessizce atlar, paket hiç üretilmezdi.

Inno Setup betiği `surum.py`'yi Python olarak çalıştıramaz, satırı **metin
olarak** ayrıştırır. Bu yüzden satırın biçimi (`SURUM = "x.y.z"`, tek satır,
çift tırnak, sonunda yorum yok) sözleşmenin parçasıdır ve
`testler/test_surum.py` tarafından korunur.

### Yayımdan sonra: indirme alanı ve site

MEB ağında GitHub engelli olduğu için okullar paketi okulapp.org'dan indirir;
dosyalar `indir.okulapp.org/sorumluluk-sinavi/` altında, Cloudflare R2'deki
`okulapp-indirme` kovasındadır. Bu depoda R2'ye yükleyen bir iş akışı yoktur,
yükleme elle yapılır:

1. Pardus paketi yayıma eklenince `.deb`'i ve `SHA256SUMS-X.Y.Z-pardus.txt`'yi
   indirip doğrulayın, üç paketi kapsayan `SHA256SUMS-X.Y.Z.txt`'yi yeniden
   üretin ve yayımdaki Windows'a özel özetin yerine koyun
   (`gh release upload vX.Y.Z … --clobber`). Kullanıcı tek paketi indirse de
   doğrulayabilsin diye kılavuz `sha256sum -c --ignore-missing` der.
2. Dört dosyayı yükleyin (bu makinedeki `wrangler login` oturumuyla):

   ```bash
   npx --yes wrangler@4 r2 object put "okulapp-indirme/sorumluluk-sinavi/<ad>" --file="<dosya>" --content-type="<tür>" --remote
   ```

   İçerik türleri: `.exe` → `application/vnd.microsoft.portable-executable`,
   `.zip` → `application/zip`, `.deb` → `application/vnd.debian.binary-package`,
   özet → `text/plain; charset=utf-8`. Özet dosyası sürümlü adla yüklenir;
   sabit ad eski sürümlerin özetini ezer.
3. Canlıdan doğrulayın: dört adres 200 dönmeli, `Content-Length` yerel boyutla
   eşleşmeli, kurulum dosyası indirilip SHA-256'sı karşılaştırılmalı.
   **Kartı bu doğrulamadan önce güncellemeyin** — sitede kırık bağlantı olur.
4. Site (`../okulapp.org`, önce oradaki CLAUDE.md → "Ortak çalışma düzeni"):
   `src/data/ss-release.json` (sürüm, ad, yayım zamanı, dört bağlantı ve
   boyut), `src/content/projects/sorumluluk-sinavi.md` içindeki `badge`, yeni
   özellik varsa `/sorumluluk-sinavi/**` sayfaları. `npm run build`
   `check-releases` ile sürümü GitHub'la karşılaştırır.

Sitedeki ekran görüntüleri ve örnek evrak gerçek veriyle değil örnek bir
okulla ("Örnek Anadolu Lisesi"; kişi yerinde "Adı SOYADI" ya da görev adı)
üretilir: `araclar/site_ornekleri.py` okulu, evrakı ve PDF
önizlemelerini; `araclar/site_ekranlari.py` Debian 12 kabında ekranları
üretir. Komutlar betiklerin başında yazılıdır. Arayüz ya da evrak değiştiyse
yeni sürümle birlikte yeniden üretin; dosyalar sitede
`public/sorumluluk-sinavi/` altındadır.
