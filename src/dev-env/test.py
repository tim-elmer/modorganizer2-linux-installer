from protontricks.cli.main import main as protontricks_main
from pathlib import Path

library_root = Path('/home/timelmer/Tmp/steamdev')

protontricks_main(('--no-runtime', '-c', 'echo $WINEPREFIX', '397540'), library_root, library_root)