# 0001 — Çevrimdışı çalışma, veri kurumda kalır

**Durum:** Kabul — 26.08.2026

## Bağlam

Uygulama öğrenci ve personel verisiyle çalışır; bu veri KVKK kapsamındadır.
Okulda kurulacak, çoğu zaman tek bir bilgisayarda çalışacak. Bulut tabanlı
bir çözüm veri sorumluluğunu okulun dışına taşır ve okul yönetiminin
denetleyemeyeceği bir yere koyar.

## Karar

Uygulama hiçbir ağ isteği yapmaz. e-Okul, MEBBİS, DYS dâhil hiçbir resmî
sisteme bağlanmaz; kullanıcı adı ya da şifre istemez. Yalnız kullanıcının
dışa aktardığı dosyaları okur. Çalışma zamanı verisi
`%LOCALAPPDATA%\SorumlulukSinavi\plan` altında durur.

## Gerekçe

Veri kurumun cihazından hiç çıkmazsa aktarım güvenliği, saklama süresi,
işleyen sıfatı ve veri işleme sözleşmesi tartışmalarının çoğu baştan ortadan
kalkar. Ayrıca okul ağının çalışmadığı anlarda da uygulama çalışır.

## Sonuçlar

- Telemetri, çevrimiçi güncelleme denetimi, uzak yedek ve hata bildirimi
  eklenemez. Bunlar istenirse yeni bir karar kaydı gerekir.
- e-Okul girişi kullanıcı tarafından elle yapılır; otomasyon yoktur.
- Yedekleme kullanıcının sorumluluğundadır; KURULUM.md bunu anlatır.
- Saat dilimi verisi (`tzdata`) pakete gömülmek zorundadır; Windows Python
  dağıtımı IANA verisi taşımaz.
