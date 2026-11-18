"""Runs alerts.feature against src/alerts.cpp, built for the host and loaded through ctypes."""

import ctypes
import pathlib
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent.parent / "src"


def pytest_bdd_apply_tag(tag, function):
    if tag == "pending":
        pytest.mark.skip(reason="@pending: the firmware does not do this yet")(function)
        return True
    return None


class CInputs(ctypes.Structure):
    _fields_ = [
        ("up_s", ctypes.c_uint32),
        ("rpm", ctypes.c_float),
        ("oil", ctypes.c_int),
        ("coolant", ctypes.c_int),
        ("alt_fresh", ctypes.c_int),
        ("alt_v", ctypes.c_float),
        ("reset", ctypes.c_char_p),
        ("sk_connected", ctypes.c_int),
        ("largest_block", ctypes.c_uint32),
        ("hours", ctypes.c_float),
    ]


class CWrites(ctypes.Structure):
    _fields_ = [
        ("segment", ctypes.c_int),
        ("pattern", ctypes.c_uint8 * 4),
        ("row6", ctypes.c_int),
        ("row6_text", ctypes.c_char * 40),
        ("row7", ctypes.c_int),
        ("row7_text", ctypes.c_char * 40),
        ("piezo", ctypes.c_int),
    ]


@pytest.fixture(scope="session")
def lib(tmp_path_factory):
    so = tmp_path_factory.mktemp("panel") / "libpanel.so"
    subprocess.run(
        ["g++", "-std=c++17", "-shared", "-fPIC", "-Wall", "-Werror", f"-I{SRC}",
         str(SRC / "alerts.cpp"), str(HERE / "shim.cpp"), "-o", str(so)],
        check=True,
    )
    lib = ctypes.CDLL(str(so))
    lib.panel_new.restype = ctypes.c_void_p
    lib.panel_free.argtypes = [ctypes.c_void_p]
    lib.panel_flame_alarm.argtypes = [ctypes.c_void_p]
    out = ctypes.POINTER(CWrites)
    lib.panel_seen.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, out]
    lib.panel_flame_tick.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int] + [ctypes.c_uint32] * 5 + [out]
    lib.panel_second_tick.argtypes = [ctypes.c_void_p, ctypes.POINTER(CInputs), out]
    return lib


# Segment patterns back to text; FIrE's I is the digit 1's pattern, so words go whole.
WORDS = {
    (0x71, 0x06, 0x50, 0x79): "FIrE",
    (0x00, 0x76, 0x5C, 0x78): " Hot",
    (0x00, 0x79, 0x50, 0x50): " Err",
}
GLYPHS = {0x00: " ", 0x3F: "0", 0x06: "1", 0x5B: "2", 0x4F: "3", 0x66: "4",
          0x6D: "5", 0x7D: "6", 0x07: "7", 0x7F: "8", 0x6F: "9"}


def segment_text(pattern):
    key = tuple(pattern)
    if key in WORDS:
        return WORDS[key]
    return "".join(GLYPHS.get(b, "?") for b in key)


class World:
    """The firmware's inputs and a fake screen, advanced the way main.cpp drives the panel."""

    STEP_MS = 20  # the flame tick

    def __init__(self, lib):
        self.lib = lib
        self.panel = lib.panel_new()
        self.up_s = 15 * 60
        self.ms = 0  # within the current second
        self.rpm = 0.0
        self.oil = self.coolant = False
        self.alt_v = None  # no reading yet
        self.alt_at = 0.0  # uptime of the last reading, seconds
        self.alt_live = False  # readings keep arriving
        self.reset = None
        self.sk = True
        self.block = 100_000
        self.hours = 0.0
        self.seen = False
        self.piezo = False
        self.timing = (150, 150, 6, 4000, 60000)
        self.segment = "    "
        self.row6 = self.row7 = ""
        self.clear()

    def close(self):
        self.lib.panel_free(self.panel)

    def clear(self):
        """Forget what has been watched; keep the state."""
        self.seconds = []  # one record per 1 s tick
        self.steps = []  # one record per 20 ms flame tick

    def now_ms(self):
        return (self.up_s * 1000 + self.ms) & 0xFFFFFFFF

    def apply(self, w):
        if w.segment:
            self.segment = segment_text(w.pattern)
        if w.row6:
            self.row6 = w.row6_text.decode()
        if w.row7:
            self.row7 = w.row7_text.decode()
        if w.piezo >= 0:
            self.piezo = bool(w.piezo)

    def set_seen(self, seen):
        if seen != self.seen:
            self.seen = seen
            w = CWrites()
            self.lib.panel_seen(self.panel, self.now_ms(), int(seen), ctypes.byref(w))
            self.apply(w)

    def alt_fresh(self):
        if self.alt_v is None:
            return False
        if self.alt_live:
            self.alt_at = self.up_s + self.ms / 1000
        return self.up_s + self.ms / 1000 - self.alt_at < 10

    def run(self, seconds):
        for _ in range(int(seconds)):
            for _ in range(1000 // self.STEP_MS):
                self.ms += self.STEP_MS
                if self.ms >= 1000:
                    self.ms -= 1000
                    self.up_s += 1
                w = CWrites()
                self.lib.panel_flame_tick(self.panel, self.now_ms(), int(self.seen), *self.timing, ctypes.byref(w))
                self.apply(w)
                self.steps.append(self.snapshot())
            inputs = CInputs(
                self.up_s, self.rpm, self.oil, self.coolant, self.alt_fresh(),
                self.alt_v or 0.0, self.reset.encode() if self.reset else None,
                self.sk, self.block, self.hours,
            )
            w = CWrites()
            self.lib.panel_second_tick(self.panel, ctypes.byref(inputs), ctypes.byref(w))
            self.apply(w)
            self.seconds.append(self.snapshot())

    def run_until(self, done, limit_s):
        for _ in range(limit_s):
            self.run(1)
            if done():
                return
        raise AssertionError(f"not reached within {limit_s} s")

    @property
    def flame_alarm(self):
        return bool(self.lib.panel_flame_alarm(self.panel))

    def snapshot(self):
        return {"segment": self.segment, "row6": self.row6, "row7": self.row7,
                "rpm": self.rpm, "alarm": self.flame_alarm, "piezo": self.piezo}

    def watched(self):
        """What a Then reads; a scenario with no When gets 8 s of watching."""
        if not self.seconds:
            self.run(8)
        return self.seconds


@pytest.fixture
def world(lib):
    w = World(lib)
    yield w
    w.close()
