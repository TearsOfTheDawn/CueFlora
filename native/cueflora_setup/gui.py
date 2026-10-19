"""Small on-demand installer UI; never starts a service or configures AI."""
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from .detection import detected_browsers
from .engine import Setup
from .manifests import validate_release
from .distribution import distribution_root
from .terms import TERMS,confirmation


def main():
    window = tk.Tk()
    window.title('CueFlora Setup')
    window.geometry('620x570')
    frame = ttk.Frame(window, padding=18)
    frame.pack(fill='both', expand=True)
    setup = Setup()
    distribution = distribution_root()
    ttk.Label(frame, text='CueFlora Setup', font=('', 18, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Installs the on-demand native runtime. No background companion runs.\n'
              'The matching Chrome extension is placed in a stable folder; you still Load unpacked in Chrome once. AI services are not installed.\n'
              'This installer is unsigned; Windows may show a security warning.', wraplength=490).pack(anchor='w', pady=8)
    ttk.Label(frame, text='Installation: ' + str(setup.root), wraplength=490).pack(anchor='w')
    def show_terms():
        dialog=tk.Toplevel(window); dialog.title('CueFlora third-party terms'); dialog.geometry('650x480')
        body=ttk.Frame(dialog,padding=12); body.pack(fill='both',expand=True)
        scrollbar=ttk.Scrollbar(body); scrollbar.pack(side='right',fill='y')
        text=tk.Text(body,wrap='word',yscrollcommand=scrollbar.set)
        text.insert('1.0',TERMS); text.configure(state='disabled'); text.pack(fill='both',expand=True)
        scrollbar.configure(command=text.yview)
        ttk.Button(dialog,text='Close',command=dialog.destroy).pack(pady=8)
        text.focus_set()
    ttk.Button(frame,text='Third-party terms',command=show_terms).pack(anchor='w',pady=3)
    detected = detected_browsers()
    try:
        configuration = validate_release(json.loads((distribution / 'release.json').read_text(encoding='utf-8')))
        configured = set(configuration['extensionIds'])
    except (ValueError, OSError):
        configured = set()
    selections = {}
    adopted=tk.StringVar(value='')
    def choose_existing():
        selected=filedialog.askdirectory(title='Select the currently loaded CueFlora extension folder (not a Chrome profile)',parent=window)
        if selected:adopted.set(selected)
    ttk.Button(frame,text='Optional: select existing CueFlora extension folder…',command=choose_existing).pack(anchor='w',pady=4)
    ttk.Label(frame,textvariable=adopted,wraplength=560).pack(anchor='w')
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
        if not messagebox.askyesno('Confirm ' + action, confirmation(action), parent=window):
            return
        if action=='install' and adopted.get() and not messagebox.askyesno('Confirm extension adoption',
            'Adopt this folder only if it is the currently loaded CueFlora extension? Setup verifies every file and keeps a recoverable backup. Foreign or modified folders are refused.\n\n'+adopted.get(),parent=window):return
        adopt_path=Path(adopted.get()) if adopted.get() else None
        busy = True
        for button in buttons:
            button.state(['disabled'])
        status.set(action.title() + ' in progress…')

        def worker():
            try:
                payload = distribution / 'runtime'
                if action == 'install':
                    release = json.loads((distribution / 'release.json').read_text(encoding='utf-8'))
                    setup.install(payload, release, browsers, launcher=Path(sys.executable) if getattr(sys, 'frozen', False) else None,
                        extension=distribution/'extension' if release.get('extensionInventorySha256') else None,
                        adopt_extension=adopt_path,confirm_adoption=adopt_path is not None)
                elif action == 'repair':
                    setup.repair(payload, launcher=Path(sys.executable) if getattr(sys, 'frozen', False) else None,
                        extension=distribution/'extension' if (distribution/'extension').is_dir() else None)
                elif action == 'rollback':
                    setup.rollback()
                else:
                    removed = setup.uninstall()
                    results.put((True, 'Unregistered. Runtime preserved for recovery at ' + str(removed)))
                    return
                installed=setup.state();extension=(installed or {}).get('extension')
                results.put((True, action.title() + ' complete. '+('Chrome: Load unpacked once from '+extension['directory']+'. For an adopted folder, click Chrome Reload instead. ' if extension else '')+'Reload open YouTube tabs. Settings, keys and evidence were preserved.'))
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
