from __future__ import annotations
import threading
from pynput import keyboard

STOP_EVENT = threading.Event()

def start_kill_switch(on_trigger=None):
    def on_press(key):
        if key == keyboard.Key.f12:
            STOP_EVENT.set()
            if on_trigger:
                try:
                    on_trigger()
                except Exception:
                    pass
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    return listener

def reset_stop():
    STOP_EVENT.clear()

def check_stop():
    if STOP_EVENT.is_set():
        raise RuntimeError("Stopped (F12).")
