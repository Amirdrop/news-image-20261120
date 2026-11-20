#!/usr/bin/env python3
"""Copy the baked newspaper image to /output/entry.png."""
from pathlib import Path
Path("/output").mkdir(exist_ok=True)
Path("/output/entry.png").write_bytes(Path(__file__).parent.joinpath("entry.png").read_bytes())