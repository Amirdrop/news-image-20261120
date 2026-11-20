#!/usr/bin/env python3
"""Copy entry.png to the build output directory."""
import os
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get('MAKEFUN_OUTPUT_DIR') or '/output')
IMAGE_NAME = "entry.png"
source = Path(__file__).parent.joinpath(IMAGE_NAME)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / IMAGE_NAME).write_bytes(source.read_bytes())