import os
import json
from rich import print
from rich.console import Console
from rich.syntax import Syntax
from rich.theme import Theme

from datetime import datetime

def latest(sub):
    directory = f'/home/jamesb/tsd/{sub}/'
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    if not json_files:
        return None
    f = max(json_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return directory + f

def load_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

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
    shelly30 = load_json(latest("shelly30"))
    sungauge40 = load_json(latest("sungauge40"))
    if 0:
        display_json_file({
            "shelly30" : shelly30["switch:0"]["apower"],
            "sungauge40" : sungauge40,
        })
    else:
        apower = shelly30["switch:0"]["apower"]
        now = datetime.now()
        hhmm = now.strftime("%H:%M")

        print(f"{hhmm} inverter: {apower:.1f}  current: {sungauge40['current']:+7.3f}  SOC: {sungauge40['soc']:5.1f}")
