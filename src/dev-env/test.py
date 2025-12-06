from protontricks.cli.main import main as protontricks_main
from protontricks import steam
from pathlib import Path

library_root = Path('/home/tim/Temp/test')

def steam.find_steam_compat_tool_app(**_):
    return {'is_proton': True}

protontricks_main(('--no-runtime', '-c', 'echo $WINEPREFIX', '397540'), library_root, library_root)