# 0015 — Yeni sürüm GitHub'dan denetlenir; istek veri taşımaz

**Durum:** Kabul — 03.10.2026. [0001](0001-cevrimdisi-ve-yerel-veri.md)'in
"çevrimiçi güncelleme denetimi eklenemez" sonucunu değiştirir; 0001'in geri
kalanı geçerlidir.

## Bağlam

Program yeni sürüm çıktığını kendisi söylemiyordu; kullanıcı ancak siteye
bakarsa öğreniyordu. Mevzuat düzeltmeleri (ör. 0.6.2'deki tutanak cümlesi)
okullara bu yüzden geç ulaşır ya da hiç ulaşmaz.

Aynı geliştiricinin öbür programları (Kelebek Sınav, Disiplin Defteri)
yayımlanan son sürümü GitHub'dan denetliyor. Kullanıcı kararı (03.10.2026):
öbür projelerdeki gibi doğrudan GitHub'dan denetlensin; projeler arası uyum
ve standart da korunur.

## Karar

- Program açıldıktan 2,5 saniye sonra, arka planda, deponun GitHub'daki son
  yayım kaydı (`releases/latest`) okunur. Kararlı sürüm yoksa sürüm
  listesindeki en yüksek ön sürüm alınır.
- İstek yalnız `GET`'tir: gövde, çerez, sorgu dizesi ya da kimlik bilgisi
  yoktur; `User-Agent` sabittir. Kişisel ya da okul verisi gönderilmez.
  Yanıt 15 dakika önbellekte tutulur; zaman aşımı 20 saniye, yanıt boyutu
  sınırlıdır.
- Yalnız `https://github.com` ve `https://api.github.com` adresleri kabul
  edilir. Yol bileşeni taşıyan varlık adı reddedilir.
- Windows'ta kurulum dosyası (`SorumlulukSinavi-Kurulum-x.y.z.exe`) yalnız
  kullanıcı isteyince indirilir ve SHA-256 özetiyle doğrulanır: özet ya
  GitHub'ın varlık özetinden (`digest`) ya da aynı yayımdaki
  `SHA256SUMS-x.y.z.txt` dosyasından gelir. Özet yoksa ya da tutmuyorsa
  dosya kullanılmaz. İndirilen dosya
  `%LOCALAPPDATA%\SorumlulukSinavi\guncelleme` altına konur, veri
  klasöründen (`plan`) ayrıdır.
- Kurulumu kullanıcı başlatır; program önce kapanır. Kendiliğinden ya da
  sessiz kurulum yoktur.
- Pardus'ta indirme yapılmaz: paketi kurmak `sudo` ister, program yönetici
  yetkisi istemez. Kullanıcı indirme sayfasına yönlendirilir.
- Açılış denetiminin hatası (ağ yok, GitHub erişilemez, oran sınırı)
  sessizdir; günlüğe yalnız hata türü yazılır. Elle denetimde hata Hakkında
  sayfasında anlaşılır Türkçeyle gösterilir.
- Denetim Hakkında sayfasından kapatılabilir; `SORUMLULUK_GUNCELLEME_DENETIMI=0`
  ortam değişkeni kurum genelinde kapatır.
- Ağ kodu yalnız `veri/guncelleme.py`'dedir. `testler/test_ag_yalitimi.py`
  başka bir modülün ağ kitaplığı (`urllib`, `http`, `socket`, `ssl`,
  `requests`…) ya da Qt'nin ağ modülünü içe aktarmasını engeller.
- Kullanıcıya görünen metinde "GitHub" ve "Release" geçmez (öbür
  programlarla aynı dil): "yayımlanan son sürüm", "indirme sayfası".

## Gerekçe

Elenen seçenekler:

1. **Hiç denetlememek** (0001'in özgün hâli): okullar eski sürümde kalır,
   mevzuat düzeltmesi ulaşmaz.
2. **okulapp.org'daki sürüm kartını (`ss-release.json`) okumak:** öbür
   programlar GitHub'ı kullanıyor, iki ayrı standart olurdu. Site yayımdan
   sonra elle güncellendiği için arada gecikme de olur.
3. **Kendiliğinden indirip kurmak:** sınav haftasında güncelleme yapılmamalı,
   kurumun BT politikası da araya girebilir. Ne zaman kurulacağına kullanıcı
   karar verir.

0001'in amacı veri kurumda kalsın diyeydi; bu korunur. İstek okul ya da kişi
verisi taşımaz. GitHub'ın gördüğü yalnız IP adresi ve sabit tarayıcı
kimliğidir; bu, bir web sayfasını açmaktan farklı değildir. Program internet
olmadan da eksiksiz çalışır.

## Sonuçlar

- 0001'in "Telemetri, çevrimiçi güncelleme denetimi, uzak yedek ve hata
  bildirimi eklenemez" maddesinden yalnız güncelleme denetimi kalkar.
  Telemetri, uzak yedek ve hata bildirimi yasağı sürer.
- Yayım düzeni bir sözleşmedir. Kurulum dosyasının adı
  `SorumlulukSinavi-Kurulum-x.y.z.exe`, özet dosyası `SHA256SUMS-x.y.z.txt`
  kalmalıdır; değişirse program yeni sürümü bulur ama indiremez. Yalnız
  Pardus paketini kapsayan `…-pardus.txt` yok sayılır.
- Etiket `vX.Y.Z` biçimindedir; sürüm karşılaştırması bu biçime dayanır.
- GitHub'ın engellendiği ağlarda (ör. bazı MEB ağları) denetim sessizce
  susar. Hakkında sayfası indirme sayfasının adresini verir.
- GitHub API'si değişirse yalnız denetim çalışmaz; programın geri kalanı
  etkilenmez.
