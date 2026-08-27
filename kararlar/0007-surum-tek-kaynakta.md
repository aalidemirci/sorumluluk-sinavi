# 0007 — Sürüm tek kaynakta tutulur

**Durum:** Kabul — 28.08.2026

## Bağlam

Sürüm numarası üç yerde elle yazılıydı: `pyproject.toml`, arayüzdeki `SURUM`
sabiti ve Inno Setup betiğindeki `#define Surum`. Üçü birbirine bakmıyordu
ve kaymıştı: pyproject 0.2.0'da unutulmuşken diğer ikisi 0.3.0 diyordu.

## Karar

Numara yalnızca `cekirdek/surum.py` içinde yazılır. Dört okuyucu oradan alır:
arayüz içe aktarır, `pyproject.toml` `dynamic version` ile okur,
`SorumlulukSinavi.spec` exe'ye gömülen sürüm kaynağını üretir, Inno Setup
betiği dosyayı ayrıştırır.

## Gerekçe

Değerleri elle eşitlemek kaymayı bir kez düzeltir, tekrarını engellemez.

## Sonuçlar

- Inno Setup `surum.py`'yi Python olarak çalıştıramaz; satırı **metin
  olarak** okur. Bu yüzden `SURUM = "x.y.z"` satırının biçimi sözleşmenin
  parçasıdır ve `testler/test_surum.py` tarafından korunur.
- ISPP'de `#sub` içindeki `#define` yereldir; sürümü dışarı taşımak için
  `public` değiştiricisi gerekir. Bu olmadan betik sessizce boş sürüm üretir.
- Uygulama adı ve geliştirici hem `.spec` hem `.iss` içinde geçer; ikisinin
  ayrışmasını yine `test_surum.py` engeller.
