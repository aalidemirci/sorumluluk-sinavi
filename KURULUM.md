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

1. **Kurum Ayarları** — okul bilgileri ve üç dönem tarihi. Sınav pencereleri
   (P1/P2/P3) bu tarihlerden hesaplanır ve ekranın altında gösterilir.
2. **Öğretmen Listesi** — e-Okul'dan `OOK01001R1` raporunu alın (aşağıdaki
   indirme yönergesine uyun). Önce **önizleme** açılır; onaylamadan hiçbir
   kayıt değişmez. Branş havuzu bu rapordan kurulur. Rapora yansımamış bir
   kişiyi elle ekleyebilir, ayrılan kişiyi pasife alabilirsiniz; görevi olan
   kişi silinemez.
3. **Salonlar** — sınav salonlarını ve kapasitelerini girin. Salon sayısı,
   aynı saatte kaç sınav yapılabileceğini belirler.
4. **e-Okul Sorumluluk** — `OOK12001R010` raporunu seçin. Rapor okulun
   tamamını kapsıyorsa "tam listedir" işaretli kalsın; kısmi bir liste
   aktarıyorsanız işareti kaldırın, yoksa dosyada olmayan kayıtlar pasife
   alınır.
5. **Ders / Branş** — her dersi bir branşa eşleyin. Türk dili ve edebiyatı ile
   yabancı dil derslerini **iki aşamalı** işaretleyin (OKY md.58/2-e); uygulama
   ders adına bakarak öneri getirir ama kararı siz verirsiniz. Birleşik
   derslerde (ör. Görsel Sanatlar/Müzik) ikinci alanı da seçin. Okulda
   öğretmeni olmayan bir branş gerekiyorsa branş havuzuna elle ekleyin.
6. **Sınav Planı** — parametreleri seçin, isterseniz önce **Yükü çözümle** ile
   gün seçeneklerinin sonucunu görün, sonra **Planı üret**.
7. **Evrak ve Teslim** — planı kaydettikten sonra belgeleri üretin; sınavlardan
   sonra geri alınan evrakı teslim çizelgesine işleyin.
8. **Yardım** — mevzuat hükümleri, kullanım ve çalışma mantığı bu sayfadadır.
9. **Lisans** — program bilgisi, geliştirici ve kullanım koşulları.

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

- Kartı başka bir gün/saat hücresine **sürükleyip bırakın.** Öğrenci,
  öğretmen ve salon çakışmaları ayrı ayrı denetlenir; engel doğuran taşıma
  otomatik geri alınır ve kimin çakıştığı yazılır.
- İki aşamalı dersin yazılı ve uygulama oturumu birlikte taşınır.
- **Geri Al / İleri Al** ile adım adım gezinebilirsiniz.
- Plan **Kaydet** denene kadar veritabanına yazılmaz.
- **Müdür onayıyla kesinleştir** planı kilitler; kesinleşmiş oturum taşınamaz
  ve kesinleşmiş plan silinemez.

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

**Görevlendirme çizelgesi** komisyon bazlıdır: her satır bir sınav komisyonudur.
İkinci sayfasında görevli her personelin tarih yazıp imzalayacağı
tebliğ-tebellüğ tablosu vardır; çizelge yatay A4 olarak üretilir.

**Teslim çizelgesi** sekmesinde her oturum için beklenen evrak listelenir.
Bir satırı seçip teslim eden ile teslim alan görevliyi ve varsa adedi girerek
**Seçili evrakı teslim al** düğmesine basın. Teslim eden ile alan aynı kişi
olamaz. Yeşil satır teslim alınmış, kırmızı satır süresinde gelmemiş evrakı
gösterir; teslim süresi sınav tarihini izleyen ilk iş günüdür.

## Yedekleme

Uygulamayı kapatın ve veri klasöründeki `sorumluluk.db` dosyasını kurumun
yedek ortamına kopyalayın. Şema yükseltmelerinde uygulama göç öncesi
otomatik yedek alır (`.yedek` uzantılı); bu yedek WAL içeriğini de kapsar.

Gerçek veriyi e-posta, kişisel bulut veya Git deposuna koymayın.

## Paketi yeniden üretmek

```bash
.venv/Scripts/python -m PyInstaller SorumlulukSinavi.spec --noconfirm
```

Pakete `veri/gocler/*.sql` ve `tzdata` girmek zorundadır: ilki şemayı kurar,
ikincisi olmadan `Europe/Istanbul` saat dilimi Windows'ta çözülemez.

### Sürüm yükseltmek

Sürüm numarası tek yerde durur: `cekirdek/surum.py` içindeki `SURUM`.
Arayüzdeki hakkında penceresi, `pyproject.toml`, PyInstaller betiği (exe'nin
dosya özelliklerine gömülen sürüm kaynağı) ve Inno Setup betiği bu değeri
oradan okur; başka hiçbir dosyada elle yazmayın.

Inno Setup betiği `surum.py`'yi Python olarak çalıştıramaz, satırı **metin
olarak** ayrıştırır. Bu yüzden satırın biçimi (`SURUM = "x.y.z"`, tek satır,
çift tırnak, sonunda yorum yok) sözleşmenin parçasıdır ve
`testler/test_surum.py` tarafından korunur.
