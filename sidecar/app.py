#!/usr/bin/env python3
"""
app.py — the PAPeR companion window (native, cross-surface).

Same idea as opening the sidecar UI in a browser, but in a small native
always-on-top window instead of a browser tab — so it feels like a companion
widget beside your editor/terminal. It is surface-independent: it stands next to
the CLI, the VS Code Claude extension, or JetBrains, all of which feed it through
the same hook. That's why a standalone app beats a VS Code-only extension.

It reuses the exact HTML + /state server from server.py — the window just renders
that instead of a browser.

DEV (no install needed — uv fetches pywebview into a throwaway env):
    uv run --python 3.11 --with pywebview python sidecar/app.py --demo

PACKAGE to a Mac .app (later, once we like it):
    uv run --python 3.11 --with pywebview --with pyinstaller \
        pyinstaller --windowed --name PAPeR \
        --add-data "sidecar/ui:sidecar/ui" sidecar/app.py
"""

import sys
import threading
import time
from http.server import ThreadingHTTPServer

import server  # sibling module: Handler, PORT, and its .env/db wiring

# Compact = a small companion widget to glance at while coding.
# Full = expanded for reading history. Toggled by the ⤢ button.
COMPACT_W, COMPACT_H = 320, 400
FULL_W, FULL_H = 460, 720


def _start_server():
    """Start the /state + UI server on a FREE port (0 = OS picks one), so a
    leftover instance on the default port never blocks us. Returns the port."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port


def _dispatch_main(fn):
    """Run fn() on the Cocoa MAIN thread. Every AppKit/NSWindow mutation must go
    through here — doing it on a worker thread crashes the process."""
    try:
        from Foundation import NSOperationQueue
        NSOperationQueue.mainQueue().addOperationWithBlock_(fn)
    except Exception as exc:
        sys.stderr.write(f"[app] main-thread dispatch failed: {exc}\n")


def _apply_pin(pinned):
    """Set (pinned) or clear (not) always-on-top over ALL apps, Spaces, and
    fullscreen. MAIN THREAD ONLY — call via _dispatch_main.

    NSFloatingWindowLevel keeps it above normal windows even when another app is
    focused; canJoinAllSpaces + fullScreenAuxiliary keep it visible over other
    Spaces and over a fullscreen terminal/VS Code (Picture-in-Picture style)."""
    try:
        from AppKit import (
            NSApp,
            NSApplicationActivationPolicyAccessory,
            NSApplicationActivationPolicyRegular,
            NSFloatingWindowLevel,
            NSNormalWindowLevel,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowCollectionBehaviorStationary,
        )
    except Exception as exc:
        sys.stderr.write(f"[app] AppKit unavailable, can't pin: {exc}\n")
        return
    app = NSApp()
    if not app:
        return
    if pinned:
        level = NSFloatingWindowLevel
        behavior = (NSWindowCollectionBehaviorCanJoinAllSpaces
                    | NSWindowCollectionBehaviorFullScreenAuxiliary
                    | NSWindowCollectionBehaviorStationary)
        # Accessory (agent) app: its floating window overlays another app's
        # fullscreen Space WITHOUT switching you out of it. This is the key to
        # floating over native-fullscreen VS Code — canJoinAllSpaces alone isn't
        # enough while the app activates as a regular app.
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    else:
        level = NSNormalWindowLevel
        behavior = 0  # NSWindowCollectionBehaviorDefault
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    for w in app.windows():
        w.setLevel_(level)
        w.setCollectionBehavior_(behavior)


def _apply_opacity(value):
    """Set NSWindow alphaValue on ALL windows. MAIN THREAD ONLY."""
    try:
        from AppKit import NSApp
    except Exception:
        return
    app = NSApp()
    if not app:
        return
    for w in app.windows():
        w.setAlphaValue_(value)


def _pin_on_start():
    """Runs on a worker thread (from webview.start(func)); waits for the window,
    then dispatches the pin to the main thread. Pinned by default."""
    try:
        from AppKit import NSApp
    except Exception as exc:
        sys.stderr.write(f"[app] AppKit unavailable: {exc}\n")
        return
    for _ in range(60):
        app = NSApp()
        if app and app.windows():
            _dispatch_main(lambda: _apply_pin(True))
            return
        time.sleep(0.1)


class PinApi:
    """Exposed to the page as window.pywebview.api — Pin + expand/collapse."""

    def __init__(self):
        self.pinned = True
        self.compact = True
        self.window = None  # set to the pywebview Window after creation

    def toggle_pin(self):
        self.pinned = not self.pinned
        state = self.pinned
        _dispatch_main(lambda: _apply_pin(state))
        return self.pinned

    def toggle_size(self):
        self.compact = not self.compact
        if self.window is not None:
            w, h = (COMPACT_W, COMPACT_H) if self.compact else (FULL_W, FULL_H)
            try:
                self.window.resize(w, h)
            except Exception as exc:
                sys.stderr.write(f"[app] resize failed: {exc}\n")
        return self.compact

    def set_opacity(self, value):
        """Set the whole window's opacity (0.3–1.0) so you can see the app
        behind it while coding. Dispatched to the main thread."""
        try:
            v = max(0.3, min(1.0, float(value)))
        except (TypeError, ValueError):
            v = 1.0
        _dispatch_main(lambda: _apply_opacity(v))
        return v


def main():
    try:
        import webview  # pip: pywebview (bundled in the packaged .app)
    except ImportError:
        sys.stderr.write(
            "pywebview is not installed.\n"
            "Run the dev command instead:\n"
            "  uv run --python 3.11 --with pywebview python sidecar/app.py --demo\n"
        )
        sys.exit(1)

    if "--demo" in sys.argv:
        conn = server.store.connect()
        server.store.seed_demo(conn)
        conn.close()

    port = _start_server()

    api = PinApi()
    window = webview.create_window(
        "PAPeR",
        f"http://localhost:{port}",
        width=COMPACT_W,
        height=COMPACT_H,
        min_size=(280, 300),
        on_top=True,
        js_api=api,               # backs the Pin + expand/collapse toggles
    )
    api.window = window           # let the API resize the real window
    # _pin_on_start runs on a worker thread, then dispatches the NSWindow tweak
    # to the MAIN thread (the safe way — the old direct call crashed here).
    webview.start(_pin_on_start)


if __name__ == "__main__":
    main()
