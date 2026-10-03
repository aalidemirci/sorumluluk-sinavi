# Kurulum ve kullanım

## Kurulum (Windows)

`dist-kurulum/` klasöründeki `SorumlulukSinavi-Kurulum-<sürüm>.exe`
dosyasını çalıştırın.

- Kurulum **kullanıcı başınadır**: yönetici hakkı istemez, Program Files'a
  yazmaz. Varsayılan yer `%LOCALAPPDATA%\SorumlulukSinavi\uygulama`.
- Başlat menüsüne kısayol eklenir; masaüstü kısayolu isteğe bağlıdır.
- Python kurulu olmasına gerek yoktur.
- Yeni sürüm eskisinin üzerine kurulur ve **veritabanınıza dokunmaz.**
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
- **Python kurulu olmasına gerek yoktur**; yorumlayıcı ve bütün kitaplıklar
  paketin içindedir. Kurulum internet istemez: paketin beklediği dört
  kitaplık (`libx11-6`, `libxext6`, `libxft2`, `libfontconfig1`) her
  masaüstü kurulumunda zaten yüklüdür.
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
- **Kaldırma veritabanını silmez.** Veri `%LOCALAPPDATA%\SorumlulukSinavi\plan`
  altında kalır. Makineyi tamamen temizlemek istiyorsanız o klasörü elle
  silin — öncesinde aşağıdaki Yedekleme bölümünü okuyun.

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
5. **Başvuru** — beklemeli ve devamsız öğrencileri işaretleyin, duyuruyu
   kaydedin, başvuru kararlarını girin (OKY md.58/2-d). Tablodan öğrenci
   seçince mevcut işaretleri ve başvurusu kutulara gelir. Önceki öğretim
   yılından kalan işaretler sarı görünür; gözden geçirip yeniden kaydedin.
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
10. **Lisans** — program bilgisi, geliştirici ve kullanım koşulları.

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
  otomatik geri alınır ve kimin çakıştığı yazılır.
- İki aşamalı derste yazılı kartı taşınınca uygulama da aynı gün ve saat
  farkıyla gelir; uygulama kartı ise tek başına başka bir güne taşınabilir
  (OKY md.58/2-e: farklı günlerde de yapılabilir).
- Karta **tıklayınca** sınavın görevlileri alttaki şeritte görünür.
  **Görevliyi değiştir…** penceresinde değiştirilecek kişiyi ve yerine gelecek
  kişiyi seçersiniz; uygun olmayanlar nedeniyle listelenir. Taslak planda
  değişiklik bellekte kalır, kesinleşmiş planda müdür onay numarası ve
  gerekçeyle hemen kaydedilir ve görevlendirme çizelgesinde listelenir.
- **Geri Al / İleri Al** ile adım adım gezinebilirsiniz (görevli değişikliği
  dâhil). Kaydedilmemiş plan başka sayfaya gidip dönünce kaybolmaz.
- Plan **Kaydet** denene kadar veritabanına yazılmaz.
- **Müdür onayıyla kesinleştir** planı kilitler; kesinleşmiş oturum taşınamaz,
  kesinleşmiş plan silinemez ve yerine yeni plan kaydedilemez.

Alt paneldeki liste kural ihlallerini gösterir: kırmızı satırlar engel,
sarı satırlar uyarıdır. Engelli plan taslak olarak kaydedilebilir ama
kesinleştirilemez.

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
Bir satırı seçip teslim eden ile teslim alan görevliyi, varsa adedi ve teslim
tarihini (varsayılan bugün) girerek **Seçili evrakı teslim al** düğmesine
basın. Teslim eden ile alan aynı kişi olamaz. Yeşil satır teslim alınmış,
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

Pakete `veri/gocler/*.sql` ve `tzdata` girmek zorundadır: ilki şemayı kurar,
ikincisi olmadan `Europe/Istanbul` saat dilimi Windows'ta çözülemez.

### Pardus paketini üretmek

Paket, GitHub Actions'ta `debian:12` kabında kendiliğinden üretilir
(`.github/workflows/pardus-paketi.yml`); elle üretmek gerekirse aynı kap
kullanılır. Ubuntu ya da başka bir dağıtımda derlemeyin: **glibc ileriye
uyumludur, geriye değil** — daha yeni bir tabanda derlenen ikili Pardus
23'te açılmaz. Gerekçenin tamamı
[kararlar/0009](kararlar/0009-pardus-paketi-pyinstaller-ile.md).

Docker kurulu bir makinede, depo kökünde:

```bash
docker run --rm -v "$PWD:/kaynak" -w /kaynak debian:12 bash -c "apt-get update && apt-get install -y --no-install-recommends python3-venv python3-tk libpython3.11 dpkg-dev && python3 -m venv /tmp/o && /tmp/o/bin/pip install -e . pyinstaller && /tmp/o/bin/python yapim/deb_paketi.py"
```

Çıktı `dist-kurulum/` altına düşer: `.deb` dosyası ve SHA-256 özeti.

### Testler GitHub'da da koşar

`.github/workflows/testler.yml` her itmede ve her birleştirme isteğinde
takımı üç ortamda koşturur: Windows'ta Python 3.11 ve 3.12, bir de Pardus
23'ün tabanı olan Debian 12 kabında (arayüz testleri için `xvfb` ile).
Bu makinedeki `pytest` bunun yerini tutmaz — özellikle Linux ayağı burada
hiç denenmiyor.

Yalnız `.md`, `LICENSE` ve `NOTICE` değiştiren itmelerde iki iş akışı da
koşmaz (`paths-ignore`). Listeye kod, test, `.gitignore` ya da iş akışı
dosyası eklemeyin.

### Sürüm yükseltmek

Sıra: `SURUM` güncellenir → CHANGELOG'da başlık açılır → testler koşar →
paketler derlenir → commit → `git tag -a vX.Y.Z`.

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

Sitedeki ekran görüntüleri ve örnek evrak gerçek veriyle değil uydurma bir
okulla üretilir: `araclar/site_ornekleri.py` okulu, evrakı ve PDF
önizlemelerini; `araclar/site_ekranlari.py` Debian 12 kabında ekranları
üretir. Komutlar betiklerin başında yazılıdır. Arayüz ya da evrak değiştiyse
yeni sürümle birlikte yeniden üretin; dosyalar sitede
`public/sorumluluk-sinavi/` altındadır.
