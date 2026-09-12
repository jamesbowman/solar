import os
import json
from rich import print
from rich.console import Console
from rich.syntax import Syntax
from rich.theme import Theme

from datetime import datetime

def latest(sub):
    directory = os.path.expanduser(f'~/tsd/{sub}/')
    if not os.path.isdir(directory):
        return None
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    if not json_files:
        return None
    f = max(json_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return directory + f

def load_json(file_path):
    if file_path is None:
        return dict()
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return dict()

def display_json_file(data):

    custom_theme = Theme({
        "key": "bold blue",
        "string": "white",
        "number": "white",
        "boolean": "white",
        "null": "white"
    })

    console = Console()
    json_str = json.dumps(data, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)

if __name__ == "__main__":
    shelly30 = load_json(latest("shellyplugus-d4d4da092de4/status/switch:0"))
    litime = load_json(latest("litime"))
    try:
        apower = shelly30["aenergy"]["by_minute"][1] * 0.06
    except (KeyError, IndexError, TypeError):
        apower = None
    hhmm = datetime.now().strftime("%H:%M")
    spower = litime.get('battery_power_w')
    charging = f"{spower:.0f} W" if spower is not None else "N/A"
    inverter = f"{apower:.1f} W" if apower is not None else "N/A"
    print(f"{hhmm} charging: {charging} inverter: {inverter}")
