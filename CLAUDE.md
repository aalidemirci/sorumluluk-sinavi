# CLAUDE.md — Sorumluluk Sınavı

Bu dosya projede çalışan yapay zekâ asistanı içindir. Uygulamanın **ne
yaptığı** BENIOKU.md'de, **nasıl kurulduğu** KURULUM.md'de anlatılır; burada
tekrarlanmaz. Burada yalnızca projede çalışırken uyulması gereken kurallar
vardır.

Kullanıcı seviyesindeki `~/.claude/CLAUDE.md` ile çelişki olursa **bu dosya
kazanır**; tutarsızlık görürseniz sorun.

## Değişmezler

Bunlar tartışmaya açık değildir. Bir değişiklik bunlardan birini bozuyorsa
değişiklik yanlıştır.

1. **Çevrimdışı.** Uygulama hiçbir ağ isteği yapmaz. `requests`, `urllib`,
   telemetri, güncelleme denetimi, bulut yedeği eklenmez.
2. **Veri kurumda kalır.** Çalışma zamanı verisi
   `%LOCALAPPDATA%\SorumlulukSinavi\plan` altındadır, depoda değildir.
3. **Kural motoru veritabanı görmez.** `cekirdek/` katmanı `veri/`yi içe
   aktarmaz; ihtiyacı olan bilgi `DogrulamaBaglami` gibi taşıyıcılarla
   dışarıdan verilir. Bu, kuralların veritabanı olmadan test edilebilmesini
   sağlar.
4. **Mevzuat dayanağı yazılır.** Bir kural ekliyorsanız hangi maddeye
   dayandığı kodda ve testte geçer (ör. `OKY md.58/2-d`). Dayanağı olmayan
   kural eklenmez.
5. **Gerçek kişi verisi depoya girmez.** Ayrıntı aşağıda.

## Katmanlar

```
cekirdek/   saf iş kuralları — veritabanı, dosya, arayüz görmez
veri/       şema göçleri, servis katmanı, e-Okul rapor ayrıştırma
evrak/      .docx üretimi; belge düzeni koddan gelir, şablondan değil
arayuz/     Tkinter masaüstü arayüzü
testler/    pytest; her kural olumsuz senaryosuyla birlikte test edilir
yapim/      Inno Setup kurulum betiği
araclar/    tek seferlik yardımcı betikler (logo üretimi gibi)
```

Bağımlılık yönü tek yönlüdür: `arayuz → veri → cekirdek`. `evrak` yalnızca
`veri` ve `cekirdek`e bakar. Ters yönde içe aktarma eklemeyin.

## Dil ve biçim

- Arayüz, belge, kod yorumu, commit mesajı ve konuşma **Türkçedir**.
- **Tanımlayıcılar da Türkçedir**: `veri_klasoru`, `hedef_klasor`,
  `oturum_gorevleri`. Yeni kodda İngilizce ad kullanmayın; mevcut düzen budur.
- Tarih `gg.aa.yyyy`, saat dilimi `Europe/Istanbul`.
- Satır uzunluğu 100 sütun civarında tutulur.
- Modül ve kamuya açık işlevler docstring alır; docstring **ne yaptığını
  değil neden öyle yapıldığını** anlatır.

## Commit mesajı

Özet satırı Türkçe, emir kipi değil bildirme kipi ("… eklendi", "… düzeltildi").
Gövdede **gerekçe** yazılır: hangi seçenek neden elendi, hangi tuzağa
düşülmemesi gerekiyor. Bu deponun geçmişi böyle yazılmıştır, sürdürün.

`Co-Authored-By` satırı **eklenmez**. (28.08.2026 öncesindeki commit'lerde
vardır; geriye dönük temizlenmedi, geçmiş yeniden yazılmadı.)

## Sürüm

Sürüm numarası tek yerde durur: `cekirdek/surum.py` içindeki `SURUM`.
`pyproject.toml`, `SorumlulukSinavi.spec`, `yapim/sorumluluk_sinavi.iss` ve
arayüz bu değeri oradan okur. Ayrıntı ve tuzaklar için KURULUM.md →
"Sürüm yükseltmek".

## KVKK

Öğrenci, veli ve personel verisi depoya, GitHub'a, hata bildirimine ya da
herhangi bir dış hizmete **girmez**. Test ve örnek verisi uydurmadır; bu
depodaki alışkanlık "Uydurma Anadolu Lisesi", "Uydurma Matematikçi" gibi
açıkça sahte adlardır — gerçekçi görünen ad üretmeyin.

`.gitignore` biçim bazlı çalışır: veri taşıyabilecek bütün uzantılar
(tablolar, belgeler, PDF, arşivler, JSON, **görseller**) baştan yoksayılır,
izlenmesi gereken birkaç dosya tek tek beyaz listeye alınır. Gerçek veriyle
denemek gerekiyorsa yoksayılan `/yerel/` klasörünü kullanın.

`.gitignore` tek başına yetmez: git izlenen dosyayı yoksaymaz, yani bir kez
`git add -f` ile giren dosya sonsuza dek push edilir. `testler/test_gizlilik.py`
bu yüzden izlenen dosyaların kendisini denetler. Beyaz listeyi genişletirken o
testteki listeleri de güncelleyin.

## Karar kayıtları

Mimari kararlar `kararlar/` altında numaralı dosyalarda tutulur. Bir
değişmezi ya da katman kuralını değiştiren bir iş yapıyorsanız önce oradaki
ilgili kaydı okuyun; kararı değiştiriyorsanız yeni kayıt yazın, eskisini
silmeyin — durumunu "değiştirildi" yapıp yeni kaydı gösterin.

## Komutlar

Ortam: Windows 11, PowerShell 5.1 (`&&` ve ternary yok), sanal ortam `.venv`.

```bash
.venv/Scripts/python -m pytest
```

```bash
.venv/Scripts/python -m PyInstaller SorumlulukSinavi.spec --noconfirm
```

```bash
iscc yapim/sorumluluk_sinavi.iss
```

Kurulum dosyası Inno Setup 6 ister (`winget install JRSoftware.InnoSetup`);
`iscc` PATH'te olmayabilir, `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`
altındadır.

Türkçe karakterli commit mesajlarını PowerShell'den geçirirken `git commit -F`
kullanın.

## Çalışma alışkanlığı

- Test yazmadan kural eklemeyin; her kuralın olumsuz senaryosu da test edilir.
- Paketi yeniden derlemeden önce testleri çalıştırın.
- Şema değişikliği göç dosyasıyla yapılır (`veri/gocler/NNN_*.sql`); mevcut
  göç dosyaları **değiştirilmez**, yenisi eklenir.
- Kullanıcının kurumunda çalışan bir uygulamadır: geriye dönük uyumluluk ve
  veritabanına dokunmama, hız ve zarafetten önce gelir.
