#!/usr/bin/env python3
"""Copy entry.png to the build output directory."""
from pathlib import Path
out = Path("/output")
out.mkdir(exist_ok=True)
(out / "entry.png").write_bytes(Path(__file__).parent.joinpath("entry.png").read_bytes())