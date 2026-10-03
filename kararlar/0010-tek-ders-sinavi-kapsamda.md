# 0010 — Tek ders sınavı (OKY md.58/6) planlanır

**Durum:** Kabul — 03.10.2026

## Bağlam

OKY md.58/6: "Sorumluluk sınavı sonunda tek dersten başarısızlığı bulunan
son sınıf öğrencileri için aynı usulle takip eden hafta içinde bir sınav daha
yapılır." Program bu sınavı "ek sınav" adıyla sınav sonrası işlemler arasında
sayıyor ve kapsam dışı bırakıyordu (PLAN.md, "Kapsam dışı").

Oysa bu sınav bir sonuç işlemi değil, yeni bir sınavdır: "aynı usulle"
yapılır, yani tarih, komisyon, gözcü, salon ve evrak ister. Okul bunu elle
planladığında programın sağladığı denetimlerin (komisyon, çifte rol, günlük
sınır, yıllık görev sayacı) hiçbiri işlemiyordu.

## Karar

Tek ders sınavı ayrı bir plan türüdür (`plan.tur = 'tek_ders'`), bağlı olduğu
dönemin kodunu taşır. Penceresi "takip eden hafta"dır: o dönemin olağan
planındaki son sınavın haftasından sonraki pazartesi–pazar aralığı
(`cekirdek.takvim.tek_ders_penceresi`). Öğrenci ve dersi kullanıcı seçer
(`tek_ders_secimi`); program sınav sonucunu bilmez, sonuç e-Okul'dadır. Aday
listesi o dönemin olağan planındaki 12. sınıf öğrencileridir.

Kurallar olağan planla aynıdır. Başvuru kapısı (md.58/2-d) uygulanmaz: aday
zaten olağan plandadır, kapıdan geçmiştir. Görevler yıllık sayaca bağlı
olduğu dönemin sütununda girer.

## Gerekçe

"Aynı usulle" ibaresi, bu sınavın olağan sınavın bütün kurallarına tabi
olduğunu söyler; ayrı bir plan türü kuralların ikinci kopyasını gerektirmez,
aynı doğrulayıcıyı kullanır. Pencere koda gömülmez, olağan planın gerçek son
sınav tarihinden türetilir.

Elenen seçenek: tek ders sınavını olağan plana eklenen oturum olarak tutmak.
Olağan plan kesinleştikten sonra değiştirilemez (bkz. kesin plan koruması) ve
pencere dışı tarih SP-01'e takılırdı.

## Sonuçlar

- Sonuç girişi, sorumluluğun kalkması ve diploma işlemleri yine e-Okul'dadır.
- Olağan plan yoksa pencere, dönemin bitişinden sonraki hafta kabul edilir.
- "Son sınıf" 12. sınıf düzeyi olarak alınır (`ogrenci.sinif_duzeyi = 12`).
