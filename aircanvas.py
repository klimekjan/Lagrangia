# =============================================================================
# aircanvas.py — Math Curve Explorer
# Background thread: opens the webcam, runs MediaPipe Hands, and publishes
# the index-finger-tip pixel position for the Challenge scene to consume.
# =============================================================================

import threading
import time

import constants as C


class AirCanvasThread(threading.Thread):
    """
    Captures the webcam on a background thread and tracks the tip of the
    index finger using MediaPipe Hands.

    Usage
    -----
        t = AirCanvasThread()
        t.start()

        # every frame:
        pt = t.point          # → (px, py) or None if no hand visible

        t.stop()              # signal the thread to exit, then join

    The thread is a daemon so it will not prevent the process from exiting
    even if stop() is never called.

    Properties
    ----------
    point     : (int, int) | None — latest finger position in canvas pixels
    ready     : bool              — True once the webcam opened successfully
    error_msg : str               — human-readable error if initialisation failed
    """

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._point:     tuple | None = None
        self._lock:      threading.Lock = threading.Lock()
        self._running:   bool = False
        self._ready:     bool = False
        self._error_msg: str  = ""

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        super().start()

    def stop(self) -> None:
        """Signal the thread to stop. Does not block; call join() if needed."""
        self._running = False

    @property
    def point(self) -> tuple | None:
        with self._lock:
            return self._point

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error_msg(self) -> str:
        return self._error_msg

    # ── Thread body ───────────────────────────────────────────────────────────

    def run(self) -> None:
        # Lazy import so missing libraries never crash the main app
        try:
            import cv2
            import mediapipe as mp
        except ImportError as e:
            self._error_msg = f"Install opencv-python & mediapipe  ({e})"
            return

        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.70,
            min_tracking_confidence=0.60,
        )

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._error_msg = "Webcam not found — check connection / permissions."
            return

        self._ready = True

        while self._running:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            # Mirror the frame so left/right feel natural to the user
            frame  = cv2.flip(frame, 1)
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            point = None
            if result.multi_hand_landmarks:
                tip = result.multi_hand_landmarks[0].landmark[
                    mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP
                ]
                # Normalised [0, 1] → canvas pixel, clamped to valid range
                px = int(max(0, min(C.CANVAS_W - 1, tip.x * C.CANVAS_W)))
                py = int(max(0, min(C.CANVAS_H - 1, tip.y * C.CANVAS_H)))
                point = (px, py)

            with self._lock:
                self._point = point

            time.sleep(0.008)   # ~120 fps cap keeps CPU usage low

        cap.release()
        hands.close()
