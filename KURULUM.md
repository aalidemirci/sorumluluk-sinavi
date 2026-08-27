# Kurulum ve deneme

## Deneme sürümü (Windows)

`dist/SorumlulukSinavi/SorumlulukSinavi.exe` dosyasını çift tıklayın. Kurulum
gerekmez, yönetici hakkı istemez, Python kurulu olmasına gerek yoktur.

Klasörün tamamını taşıyın — `SorumlulukSinavi.exe` yanındaki `_internal`
klasörü olmadan çalışmaz.

İlk açılışta veritabanı `%LOCALAPPDATA%\SorumlulukSinavi\veri\sorumluluk.db`
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
2. **Öğretmen Listesi** — e-Okul'dan `OOK01001R1` raporunu `.xls`/`.xlsx`
   olarak dışa aktarın. Önce **önizleme** açılır; onaylamadan hiçbir kayıt
   değişmez. Branş havuzu bu rapordan kurulur.
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
