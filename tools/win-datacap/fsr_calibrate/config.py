from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[2]

FSR_HOST = "127.0.0.1"
FSR_PORT = 6543
FSR_PACKET_SIZE = 320

FORCE_WS_URL = "ws://127.0.0.1:8765"

HISTORY = 500
UI_TIMER_MS = 16
PLOT_WINDOW_S = 5.0
REF_PLOT_Y_MIN_N = 0.0
REF_PLOT_Y_MAX_N = 300.0
REF_RESIDUAL_Y_AUTO = True
STATUS_UPDATE_INTERVAL_S = 0.2
CSV_FLUSH_EVERY_ROWS = 20
FORCE_ANCHOR_WINDOW_S = 60.0
FORCE_INTERP_MAX_SKEW_S = 2.0
FORCE_DEDUP_INTERVAL_S = 0.3

FORCE_CHANNEL_NAME = "Ch0_Reg0-1"
FORCE_SIGN = -1.0

RECORD_DIR = Path(__file__).resolve().parent.parent / "record"
DEFAULT_CALIB_YAML = RECORD_DIR / "9mm" / "result.yml"

MODEL_UI_TO_YAML: dict[str, str] = {
    "指数函数": "exponential",
    "幂函数": "power",
    "倒数函数": "inverse",
}

BOUNDARY_PAYLOAD_PATH = (
    TOOLS_ROOT / "insoles-boundary" / "reports" / "render_payload.json"
)

# Blur level for the B-spline rendered insole sensor regions (left/right heatmaps).
BOUNDARY_BLUR_SIGMA = 3.0

# Legacy constants for the older 25×60 rectangular grid renderer.
FOOT_GRID_ROWS = 25
FOOT_GRID_COLS = 60
FOOT_SCALE_UP = 8
FOOT_BLUR_SIGMA = 2.0

FOOT_SENSOR_REGIONS: tuple[tuple[int, int, int, int, int], ...] = (
    (12, 2, 6, 3, 13),
    (13, 8, 12, 1, 13),
    (14, 14, 18, 1, 13),
    (15, 20, 24, 3, 13),
    (11, 20, 24, 21, 28),
    (0, 2, 6, 14, 24),
    (1, 8, 12, 14, 24),
    (2, 14, 18, 14, 24),
    (10, 16, 23, 36, 46),
    (4, 6, 12, 25, 35),
    (5, 14, 18, 25, 35),
    (6, 20, 24, 29, 35),
    (8, 16, 23, 47, 57),
    (9, 8, 15, 36, 46),
    (3, 20, 24, 14, 20),
    (7, 8, 15, 47, 57),
)
