import argparse
import json
import sys
import cv2
import numpy as np

PARAMS_FILE = "morph_params.json"
PARAMS_ID   = 10


def load_morph_params(path: str, preset_id: int) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for preset in data["presets"]:
        if preset["id"] == preset_id:
            return preset
    raise ValueError(f"Nie znaleziono zestawu parametrów o id={preset_id} w pliku '{path}'")



# 1. Segmentacja w HSV
def segment_red_hsv(frame: np.ndarray,
                    lower1: np.ndarray, upper1: np.ndarray,
                    lower2: np.ndarray, upper2: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    return cv2.bitwise_or(mask1, mask2)



# 2. Operacje morfologiczne
def clean_mask(mask: np.ndarray,
               kernel_size: int, open_iter: int, close_iter: int) -> np.ndarray:
    """
    Opening  → usuwa szum
    Closing  → wypełnia wewnątrz obiektu
    """
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=open_iter)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=close_iter)
    return mask



# 3. Wyznaczenie pozycji i rozmiaru obiektu
#    – momenty maski binarnej → centroid i pole powierzchni
#    – promień szacowany ze wzoru: r = sqrt(m00 / π)

def find_object(mask: np.ndarray, min_area: float):
    M = cv2.moments(mask)
    if M["m00"] / 255.0 < min_area:
        return None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    radius = int(np.sqrt(M["m00"] / (255.0 * np.pi)))
    return cx, cy, radius


# 4. Rysowanie okręgu i paska odchylenia

def draw_overlay(frame: np.ndarray, cx: int, cy: int, radius: int) -> np.ndarray:
    """
    Rysuje:
    - okrąg otaczający obiekt
    - punkt centroidu
    - pionową linię środka kadru
    - poziomy pasek odchylenia lewo/prawo
    - tekst z wartością odchylenia w pikselach
    """
    h, w = frame.shape[:2]
    x_center = w // 2
    deviation_px = cx - x_center

    # --- Okrąg i centroid ---
    cv2.circle(frame, (cx, cy), radius, (0, 0, 255), 3)
    cv2.circle(frame, (cx, cy), 4,      (255, 255, 255), -1)

    # --- Pionowa linia środka kadru ---
    cv2.line(frame, (x_center, 0), (x_center, h), (255, 255, 0), 1)

    # --- Pasek odchylenia (HUD) ---
    bar_y     = h - 30
    bar_h     = 18
    bar_max_w = w // 2 - 10

    cv2.rectangle(frame,
                  (10, bar_y - bar_h), (w - 10, bar_y),
                  (50, 50, 50), -1)

    fill_w = min(int(abs(deviation_px) / (w / 2) * bar_max_w), bar_max_w)

    if deviation_px >= 0:
        x1, x2 = x_center, x_center + fill_w
        color = (0, 100, 255)
        side_label = "PRAWO"
    else:
        x1, x2 = x_center - fill_w, x_center
        color = (255, 100, 0)
        side_label = "LEWO"

    cv2.rectangle(frame, (x1, bar_y - bar_h), (x2, bar_y), color, -1)

    cv2.line(frame,
             (x_center, bar_y - bar_h - 2),
             (x_center, bar_y + 2),
             (255, 255, 0), 2)

    label = f"Odchylenie: {deviation_px:+d} px  ({side_label})"
    cv2.putText(frame, label,
                (10, bar_y - bar_h - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    return frame


def main():
    parser = argparse.ArgumentParser(description="LAB1 – detekcja czerwonego obiektu")
    parser.add_argument("--video", required=True,
                        help="Ścieżka do pliku wideo, np. --video F1.mp4")
    args = parser.parse_args()

    # parametry z pliku json
    params = load_morph_params(PARAMS_FILE, PARAMS_ID)

    lower1 = np.array(params["hsv_red1_lower"])
    upper1 = np.array(params["hsv_red1_upper"])
    lower2 = np.array(params["hsv_red2_lower"])
    upper2 = np.array(params["hsv_red2_upper"])
    kernel_size = params["morph_kernel_size"]
    open_iter   = params["morph_open_iter"]
    close_iter  = params["morph_close_iter"]
    min_area    = params["min_moment_area"]

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"[BŁĄD] Nie można otworzyć pliku wideo: '{args.video}'")
        sys.exit(1)

    print("[INFO] Wideo otwarte. Naciśnij 'q' lub ESC, aby zakończyć.")

    WINDOW = "LAB1"
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Koniec wideo.")
            break

        display = frame.copy()

        mask_raw   = segment_red_hsv(frame, lower1, upper1, lower2, upper2)
        mask_clean = clean_mask(mask_raw, kernel_size, open_iter, close_iter)

        result = find_object(mask_clean, min_area)
        if result is not None:
            cx, cy, radius = result
            draw_overlay(display, cx, cy, radius)
        else:
            cv2.putText(display, "Brak obiektu",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        mask_bgr = cv2.cvtColor(mask_clean, cv2.COLOR_GRAY2BGR)
        combined = np.hstack([display, mask_bgr])
        cv2.imshow(WINDOW, combined)

        key = cv2.waitKey(30) & 0xFF
        if key in (ord('q'), 27):
            print("[INFO] Zakończono przez użytkownika.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()