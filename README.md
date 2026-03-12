## Dobór parametrów w morph_params.json

Parametry dobierano iteracyjnie na podstawie obserwacji nagrania. Używany preset to **id=10**.

### Zakresy HSV dla czerwieni

Czerwień w OpenCV HSV zajmuje dwa zakresy:
- `hsv_red1`: H ∈ [0, 5] – czerwień przy 0°
- `hsv_red2`: H ∈ [165, 180] – czerwień przy 180°

Wartości S i V ustalono na podstawie próbek z `hsv_picker.py`:

| Parametr | Wartość (red1 / red2) | Uzasadnienie                                                                                             |
|---|---|----------------------------------------------------------------------------------------------------------|
| H lower | 0 / 165 | Podwyższenie dolnego H wyeliminowało przeskakiwanie detekcji na odbicie w podłodze                       |
| H upper | 5 / 180 | Obniżenie z 10 do 5 wyeliminowało detekcję brązowego                                                     |
| S lower | 130 / 130 | Odcięcie mało nasyconych (szarych/białych) pikseli                                                       |
| V lower | 80 / 60 | Obniżenie dolnego V dla red2 (60 zamiast 100) pozwoliło wykrywać czerwień w cieniu - przy zoom na filmie |
| V upper | 255 / 255 | –                                                                                                        |

| Parametr | Wartość | Uzasadnienie |
|---|---|---|
| `morph_kernel_size` | 9 | Większy kernel wygładza maskę przy dużym obiekcie |
| `morph_open_iter` | 3 | Nie było dużego problemu z szumami, więc wartość pozostała niska |
| `morph_close_iter` | 9 | Zwiększono (względem wcześniejszych prób), bo wyższe close_iter eliminowało dziury w masce w środku detekowanego obiektu |
| `min_moment_area` | 20 | Odrzuca drobne fałszywe wykrycia, nie odrzuca właściwej kropki |

# WMA_lab1

Detekcja czerwonego obiektu  w nagraniu wideo przy użyciu segmentacji w przestrzeni HSV i operacji morfologicznych.
## Pliki

- `hsv_picker.py` – narzędzie do próbkowania wartości HSV z wideo
- `lab1_object_detection.py` – główny skrypt detekcji obiektu
- `morph_params.json` – zestawy parametrów HSV i morfologicznych


### Użycie skryptów

## hsv_picker.py

Narzędzie pomocnicze do wyznaczania zakresów HSV dla śledzonego obiektu.

**Działanie:**
1. Otwiera plik wideo (domyślnie w zwolnionym tempie `--speed 0.5`).
2. Pierwsze kliknięcie lewym przyciskiem myszy **rozpoczyna rejestracje** – skrypt próbkuje wartości HSV (i BGR) piksela pod kursorem z zadaną częstotliwością (`--rate`, domyślnie 5/s).
3. Drugie kliknięcie **zatrzymuje rejestracje**.
4. Po zamknięciu okna (`q` / `ESC`) wszystkie zebrane próbki są zapisywane do pliku CSV (`--out`, domyślnie `hsv_picks.csv`).


**Uruchomienie:**
```
python hsv_picker.py --video F1.MOV [--rate 5] [--speed 0.5] [--out hsv_picks.csv]
```

Zebrane próbki (kolumny: `frame, x, y, H, S, V, B, G, R`) posłużyły do ustalenia przedziałów HSV w `morph_params.json`.

---

## lab1_object_detection.py

Główny skrypt detekcji. Wczytuje preset parametrów z `morph_params.json` (zmienna `PARAMS_ID`) i przetwarza wideo klatka po klatce.

**Potok przetwarzania:**

1. **Segmentacja HSV** (`segment_red_hsv`) – konwersja klatki do HSV, następnie dwa wywołania `cv2.inRange` (dwa zakresy, bo czerwień w HSV leży zarówno blisko 0° jak i 180°). Obie maski łączone operacją `bitwise_or`.

2. **Czyszczenie maski** (`clean_mask`) – operacje morfologiczne na masce binarnej:
   - **Opening** (erozja + dylatacja) – usuwa drobne szumy.
   - **Closing** (dylatacja + erozja) – wypełnia dziury wewnątrz wykrytego obszaru.
   - Jądro morfologiczne: elipsa o rozmiarze `morph_kernel_size`.

3. **Wyznaczenie obiektu** (`find_object`) – momenty obrazu binarnego (`cv2.moments`):
   - `m00` = pole powierzchni (w pikselach × 255); odrzucany jeśli < `min_moment_area`.
   - Centroid: `cx = m10/m00`, `cy = m01/m00`.
   - Szacowany promień: `r = sqrt(m00 / (255 · π))`.

4. **Overlay** (`draw_overlay`) – rysuje na klatce: okrąg wokół obiektu, punkt centroidu, pionową linię środka kadru oraz poziomy pasek HUD z odchyleniem obiektu od środka (lewo/prawo, w pikselach).

5. Wyświetlanie: okno z klatką po lewej i binarną maską po prawej (`np.hstack`).

**Uruchomienie:**
```
python lab1_object_detection.py --video F1.MOV
```

