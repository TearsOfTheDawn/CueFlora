"""Small on-demand installer UI; never starts a service or configures AI."""
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from .detection import detected_browsers
from .engine import Setup
from .manifests import validate_release
from .distribution import distribution_root


def main():
    window = tk.Tk()
    window.title('CueFlora Setup')
    window.geometry('540x380')
    frame = ttk.Frame(window, padding=18)
    frame.pack(fill='both', expand=True)
    setup = Setup()
    distribution = distribution_root()
    ttk.Label(frame, text='CueFlora Setup', font=('', 18, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Installs the on-demand native runtime. No background companion runs.\n'
              'AI services and browser extensions are not installed by this tool.\n'
              'This installer is unsigned; Windows may show a security warning.', wraplength=490).pack(anchor='w', pady=8)
    ttk.Label(frame, text='Installation: ' + str(setup.root), wraplength=490).pack(anchor='w')
    detected = detected_browsers()
    try:
        configuration = validate_release(json.loads((distribution / 'release.json').read_text(encoding='utf-8')))
        configured = set(configuration['extensionIds'])
    except (ValueError, OSError):
        configured = set()
    selections = {}
    for browser in ['chrome', 'firefox']:
        selected = tk.BooleanVar(value=False)
        selections[browser] = selected
        suffix = ' — not configured' if browser not in configured else ('' if browser in detected else ' — not detected')
        checkbox = ttk.Checkbutton(frame, text=browser.title() + suffix, variable=selected)
        checkbox.pack(anchor='w', pady=2)
        if browser not in detected or browser not in configured:
            checkbox.state(['disabled'])
    status = tk.StringVar(value='Select browsers explicitly before installing. Existing settings and evidence are preserved.')
    ttk.Label(frame, textvariable=status, wraplength=490).pack(anchor='w', pady=12)
    actions = ttk.Frame(frame)
    actions.pack(fill='x')
    buttons = []
    results = queue.Queue()
    busy = False

    def poll():
        nonlocal busy
        try:
            ok, result = results.get_nowait()
        except queue.Empty:
            window.after(100, poll)
            return
        busy = False
        for button in buttons:
            button.state(['!disabled'])
        status.set(result)
        if not ok:
            messagebox.showerror('CueFlora Setup', result, parent=window)

    def perform(action):
        nonlocal busy
        if busy:
            return
        browsers = [name for name, selected in selections.items() if selected.get()]
        if action == 'install' and not browsers:
            status.set('Select at least one detected browser.')
            return
        if not messagebox.askyesno('Confirm ' + action, action.title() + ' the CueFlora native runtime?\n'
                                  'Browser/provider settings and evidence remain unchanged.', parent=window):
            return
        busy = True
        for button in buttons:
            button.state(['disabled'])
        status.set(action.title() + ' in progress…')

        def worker():
            try:
                payload = distribution / 'runtime'
                if action == 'install':
                    release = json.loads((distribution / 'release.json').read_text(encoding='utf-8'))
                    setup.install(payload, release, browsers, launcher=Path(sys.executable) if getattr(sys, 'frozen', False) else None)
                elif action == 'repair':
                    setup.repair(payload, launcher=Path(sys.executable) if getattr(sys, 'frozen', False) else None)
                elif action == 'rollback':
                    setup.rollback()
                else:
                    removed = setup.uninstall()
                    results.put((True, 'Unregistered. Runtime preserved for recovery at ' + str(removed)))
                    return
                results.put((True, action.title() + ' complete. Use Check connection in extension settings to verify browser registration.'))
            except Exception as error:
                results.put((False, str(error)))
        threading.Thread(target=worker, daemon=True).start()
        window.after(100, poll)

    for action, label in [('install', 'Install / Upgrade'), ('repair', 'Repair'), ('rollback', 'Roll back'), ('uninstall', 'Uninstall')]:
        button = ttk.Button(actions, text=label, command=lambda action=action: perform(action))
        button.pack(side='left', padx=2)
        buttons.append(button)
    window.protocol('WM_DELETE_WINDOW', lambda: None if busy else window.destroy())
    window.mainloop()
