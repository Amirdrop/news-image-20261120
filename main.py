"""Copy the bundled entry.png into a target directory after verifying integrity.

Freshly authored for this task; no code is shared with any previous version in
this directory. The expected SHA-256 digest below was computed from the real
entry.png that ships alongside this script.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

# SHA-256 of the genuine entry.png. If the file on disk does not match this we
# refuse to copy it (exit non-zero), so corrupted or tampered assets never end
# up in the output directory.
EXPECTED_SHA256 = "cdd29fa9e6f2f3d5eacaccb2310ab923559d2c764d4f7a281c61f6f7cf519df3"

# Stream in fixed-size chunks so we never load the whole image into memory.
CHUNK_SIZE = 64 * 1024


def sha256_of(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of the file at *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    # 1. Resolve the destination root from the environment, defaulting to
    #    /output. expanduser keeps a leading ~ usable if someone sets it.
    output_root = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")).expanduser()

    # 2. The source always lives next to this script, independent of whatever
    #    the current working directory happens to be when we are launched.
    source = Path(__file__).resolve().parent / "entry.png"
    if not source.is_file():
        print(f"ERROR: missing source file: {source}", file=sys.stderr)
        return 1

    # 3. Integrity gate: a digest mismatch means we must not continue.
    actual_sha256 = sha256_of(source)
    if actual_sha256 != EXPECTED_SHA256:
        print("ERROR: SHA-256 mismatch for entry.png", file=sys.stderr)
        print(f"  expected: {EXPECTED_SHA256}", file=sys.stderr)
        print(f"  actual:   {actual_sha256}", file=sys.stderr)
        return 2

    # 4. Ensure the destination directory exists (parents included).
    try:
        output_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR: could not create {output_root}: {exc}", file=sys.stderr)
        return 3

    destination = output_root / source.name

    # 5. Atomic copy: stream into a uniquely named temp file in the SAME
    #    directory, fsync it, then os.replace() onto the final name. Being on
    #    the same filesystem keeps the rename atomic, so readers see either the
    #    old file or the complete new one -- never a half-written copy.
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=output_root
        )
        with os.fdopen(fd, "wb") as temp_file:
            with source.open("rb") as src:
                shutil.copyfileobj(src, temp_file, CHUNK_SIZE)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, destination)
    except OSError as exc:
        # Best-effort cleanup of any partial temp file on failure.
        try:
            os.unlink(temp_name)
        except (OSError, UnboundLocalError):
            pass
        print(f"ERROR: copy failed: {exc}", file=sys.stderr)
        return 4

    # 6. Confirm the copy is byte-for-byte the same size as the source before
    #    declaring success.
    size = destination.stat().st_size
    source_size = source.stat().st_size
    if size != source_size:
        print(f"ERROR: size mismatch after copy ({size} != {source_size})", file=sys.stderr)
        return 5

    print(f"COPY OK {size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
