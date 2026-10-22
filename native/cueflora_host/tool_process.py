"""External tools must never share the native-messaging control streams."""
import os
import subprocess


def tool_process_options(*, detach_output=False):
    # The host's input reader remains active while tools run. Inheriting that
    # pipe can stall a frozen child at startup and can expose protocol input.
    options = {'stdin': subprocess.DEVNULL}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    if detach_output:
        options.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return options
