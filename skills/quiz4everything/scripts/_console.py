"""Console encoding shim. Import and call `setup()` at the start of main().

Why this exists: on Windows the console codepage is often GBK/cp936 (and on some
setups cp1252). Python binds sys.stdout to that codec, so printing a section
title containing '•', an em dash, or Chinese text raises
`UnicodeEncodeError: 'gbk' codec can't encode character ...` and kills the
process. The mojibake is cosmetic; the crash is not, because a learner loses
their place mid-session.

Two-layer fix:
  1. Ask the stream to encode UTF-8 when the underlying console supports it
     (Windows: code page 65001). This is the normal case on Windows 10+.
  2. If the stream cannot be reconfigured, replace unencodable characters
     instead of raising, so output degrades rather than aborting.

Exported ASCII marker is used by callers that want to avoid a bullet: see
DOT, ARROW, and BULLET below. Prefer plain ASCII in console output; use these
only where a symbol genuinely helps.
"""

from __future__ import annotations

import sys

DOT = "  |  "     # ASCII-safe separator for the 'a | b' header line
ARROW = "->"      # ASCII-safe arrow
BULLET = "-"      # ASCII-safe bullet


def setup() -> None:
    """Make stdout/stderr survive a non-UTF-8 console. Never raises."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
            continue
        except (AttributeError, ValueError, OSError):
            pass
        # Pre-3.7 wrappers, or a stream that refuses reconfiguration.
        try:
            if hasattr(stream, "buffer"):
                import codecs

                stream = codecs.getwriter("utf-8")(stream.buffer, "replace")
        except Exception:
            pass


def enable_ansi() -> bool:
    """Turn on VT100 processing on Windows 10+ so status colours work.

    Returns True when ANSI escapes should be emitted. Deliberately conservative:
    anything unexpected returns False, and callers must treat colour as optional.
    """
    if not sys.stdout or not getattr(sys.stdout, "isatty", lambda: False)():
        return False
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        return bool(
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        )
    except Exception:
        return False
