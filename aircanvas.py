import sys
import threading
import time

import constants as C


class AirCanvasThread(threading.Thread):
    """Background thread: captures webcam, runs MediaPipe hand tracking,
    and detects a pinch gesture (index + thumb) to control drawing."""

    # pinch detection thresholds (normalised landmark distance)
    # hysteresis: must close tighter than the release distance to start,
    # which prevents rapid on/off flickering near the boundary
    PINCH_ON  = 0.06
    PINCH_OFF = 0.09

    # center-crop region of the webcam frame
    # only landmarks inside this normalised box are mapped to the canvas,
    # so the user can reach screen edges without stretching to the webcam edges
    CROP_X0 = 0.15
    CROP_X1 = 0.85
    CROP_Y0 = 0.15
    CROP_Y1 = 0.85

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._point:     tuple | None = None
        self._pinching:  bool         = False
        self._frame:     object       = None
        self._lock:      threading.Lock = threading.Lock()
        self._running:   bool = False
        self._ready:     bool = False
        self._error_msg: str  = ""

    def start(self) -> None:
        self._running = True
        super().start()

    def stop(self) -> None:
        self._running = False

    @property
    def point(self) -> tuple | None:
        """Returns the finger position (thread-safe)."""
        with self._lock:
            return self._point

    @property
    def pinching(self) -> bool:
        """True when thumb and index finger are pressed together."""
        with self._lock:
            return self._pinching

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error_msg(self) -> str:
        return self._error_msg

    def get_frame_surface(self, width: int, height: int):
        import pygame
        import cv2
        with self._lock:
            frame = self._frame
        if frame is None:
            return None
        resized = cv2.resize(frame, (width, height))
        rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))

    # remap a normalised landmark coordinate from the center-crop region onto the canvas
    @staticmethod
    def _remap(value: float, lo: float, hi: float, out_max: int) -> int:
        t = (value - lo) / (hi - lo)
        return int(max(0, min(out_max - 1, t * out_max)))

    def run(self) -> None:
        try:
            import cv2
            import mediapipe as mp
        except ImportError as e:
            self._error_msg = f"Install opencv-python & mediapipe  ({e})"
            return

        # model_complexity=0 (lite) — faster inference, more frames processed per second;
        # lower confidence thresholds so the hand is not lost in dim lighting
        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.50,
            min_tracking_confidence=0.40,
        )
        INDEX_TIP = mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP
        THUMB_TIP = mp.solutions.hands.HandLandmark.THUMB_TIP

        # on Windows, try DirectShow first (faster init), fall back to default
        if sys.platform == "win32":
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
        else:
            cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            self._error_msg = "Webcam not found — check connection / permissions."
            return

        # request 640×480 and a small buffer — best-effort
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE,     1)
        except Exception:
            pass

        # drain a couple of frames so the auto-exposure settles before we
        # start tracking — also confirms the camera is actually streaming
        for _ in range(3):
            cap.read()

        self._ready = True

        while self._running:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            # try to grab one newer frame to skip a potentially stale buffer
            if cap.grab():
                ok2, newer = cap.retrieve()
                if ok2:
                    frame = newer

            # mirror the frame so left/right feel natural to the user
            frame  = cv2.flip(frame, 1)
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            point    = None
            pinching = False

            if result.multi_hand_landmarks:
                hand  = result.multi_hand_landmarks[0]
                index = hand.landmark[INDEX_TIP]
                thumb = hand.landmark[THUMB_TIP]

                # --- pinch detection with hysteresis ---
                dx_n = index.x - thumb.x
                dy_n = index.y - thumb.y
                pinch_dist = (dx_n * dx_n + dy_n * dy_n) ** 0.5

                if self._pinching:
                    pinching = pinch_dist < self.PINCH_OFF   # stays on until fingers separate
                else:
                    pinching = pinch_dist < self.PINCH_ON    # only turns on when very close

                # --- position tracking with center-crop remapping ---
                # only the centre 70% of the webcam is mapped to the canvas,
                # so the user can reach screen edges without stretching to the webcam edges
                px = self._remap(index.x, self.CROP_X0, self.CROP_X1, C.CANVAS_W)
                py = self._remap(index.y, self.CROP_Y0, self.CROP_Y1, C.CANVAS_H)
                point = (px, py)

            with self._lock:
                self._point    = point
                self._pinching = pinching
                self._frame    = frame

        cap.release()
        hands.close()