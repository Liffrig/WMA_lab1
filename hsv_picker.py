"""
Pierwsze kliknięcie – start nagrywania HSV pod kursorem (X próbek/s).
Drugie kliknięcie – stop.
Po wyjściu (q / ESC) wszystkie próbki zapisywane do .csv.
Uruchomienie: python hsv_picker.py --video F1.MOV [--rate 5] [--out hsv_picks.csv]
"""
import argparse
import sys
import time
import cv2
import numpy as np
import pandas as pd

current_frame = None
current_frame_no = 0
cursor_x = 0
cursor_y = 0
recording = False
rows = []
last_sample_time = 0.0


def on_mouse(event, x, y, flags, param):
    global cursor_x, cursor_y, recording, last_sample_time
    cursor_x, cursor_y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        recording = not recording
        state = "START" if recording else "STOP"
        print(f"[{state}] klatka={current_frame_no}  x={x}  y={y}  próbek={len(rows)}")
        last_sample_time = 0.0   # od razu pobierz pierwszą próbkę


def sample(rate):
    global last_sample_time
    if current_frame is None:
        return
    now = time.monotonic()
    if now - last_sample_time < 1.0 / rate:
        return
    last_sample_time = now

    hsv = cv2.cvtColor(current_frame, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[cursor_y, cursor_x]
    b, g, r = current_frame[cursor_y, cursor_x]
    rows.append({"frame": current_frame_no,
                 "x": cursor_x, "y": cursor_y,
                 "H": int(h), "S": int(s), "V": int(v),
                 "B": int(b), "G": int(g), "R": int(r)})
    print(f"  #{len(rows):4d}  frame={current_frame_no:5d}  "
          f"HSV=({h:3d},{s:3d},{v:3d})  BGR=({b:3d},{g:3d},{r:3d})")


def main():
    global current_frame, current_frame_no

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--rate", type=float, default=5, help="Próbki na sekundę (domyślnie 5)")
    parser.add_argument("--out",   default="hsv_picks.csv")
    parser.add_argument("--speed", type=float, default=0.5, help="Prędkość odtwarzania (domyślnie 0.5)")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"[BŁĄD] Nie można otworzyć: '{args.video}'")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    cv2.namedWindow("HSV Picker", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("HSV Picker", on_mouse)
    print(f"Kliknij raz = start nagrywania ({args.rate}/s), kliknij ponownie = stop. Wyjście: q/ESC")

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            current_frame_no = 0
            continue

        current_frame    = frame
        current_frame_no = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

        if recording:
            sample(args.rate)

        # Wskaźnik stanu nagrywania na obrazie
        if recording:
            cv2.circle(frame, (20, 20), 10, (0, 0, 255), -1)

        cv2.imshow("HSV Picker", frame)

        if cv2.waitKey(max(1, int(1000 / fps / args.speed))) & 0xFF in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(args.out, index=False)
        print(f"\n[INFO] Zapisano {len(df)} próbek → {args.out}")
    else:
        print("[INFO] Brak próbek")


if __name__ == "__main__":
    main()