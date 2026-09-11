"""
scripts/download_kits21_model.py

Downloads and extracts the verified KiTS21 3D Full-Resolution U-Net model checkpoint
directly from Zenodo (DOI: 10.5281/zenodo.5126443, Record 5126443).

Avoids downloading the entire 3.5 GB Task135_KiTS2021.zip by using HTTP Range requests
to stream and decompress fold_0/model_final_checkpoint.model (249,826,698 bytes uncompressed,
232,461,804 bytes compressed) directly into weights/kits21/.
"""

import os
import sys
import time
import struct
import zlib
import hashlib
from pathlib import Path
import urllib.request
import torch

ZENODO_RECORD_URL = "https://zenodo.org/api/records/5126443/files/Task135_KiTS2021.zip/content"
HEADER_OFFSET = 1166702190
DATA_OFFSET = 1166702316
COMPRESSED_SIZE = 232461804
UNCOMPRESSED_SIZE = 249826698

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB per HTTP range request

TARGET_DIR = Path("weights/kits21")
TARGET_FILE = TARGET_DIR / "model_final_checkpoint.model"


def download_and_extract_checkpoint():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET_FILE.exists() and TARGET_FILE.stat().st_size == UNCOMPRESSED_SIZE:
        print(f"Target file already exists and has expected size ({UNCOMPRESSED_SIZE} bytes): {TARGET_FILE}")
        return verify_checkpoint(TARGET_FILE)

    print(f"Starting acquisition of KiTS21 3D Full-Res checkpoint from Zenodo...")
    print(f"URL: {ZENODO_RECORD_URL}")
    print(f"Offset: {DATA_OFFSET}, Compressed size: {COMPRESSED_SIZE / (1024*1024):.2f} MB")
    print(f"Destination: {TARGET_FILE}")

    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    sha256 = hashlib.sha256()

    downloaded_comp = 0
    total_uncompressed = 0
    start_time = time.time()

    temp_file = TARGET_FILE.with_suffix(".tmp")

    with open(temp_file, "wb") as f_out:
        while downloaded_comp < COMPRESSED_SIZE:
            chunk_start = DATA_OFFSET + downloaded_comp
            chunk_end = min(DATA_OFFSET + COMPRESSED_SIZE - 1, chunk_start + CHUNK_SIZE - 1)
            req_size = chunk_end - chunk_start + 1

            # Retry loop for resilient download
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    req = urllib.request.Request(
                        ZENODO_RECORD_URL,
                        headers={"Range": f"bytes={chunk_start}-{chunk_end}"},
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        comp_data = resp.read()
                    if len(comp_data) != req_size:
                        raise IOError(f"Expected {req_size} bytes, received {len(comp_data)}")
                    break
                except Exception as e:
                    print(f"Attempt {attempt+1}/{max_retries} failed for range {chunk_start}-{chunk_end}: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2 * (attempt + 1))

            decompressed = decompressor.decompress(comp_data)
            f_out.write(decompressed)
            sha256.update(decompressed)

            downloaded_comp += len(comp_data)
            total_uncompressed += len(decompressed)

            elapsed = time.time() - start_time
            rate = (downloaded_comp / (1024 * 1024)) / max(elapsed, 0.001)
            pct = (downloaded_comp / COMPRESSED_SIZE) * 100.0
            print(
                f"Progress: {pct:5.1f}% | {downloaded_comp / (1024*1024):6.1f} / {COMPRESSED_SIZE / (1024*1024):.1f} MB "
                f"| Decompressed: {total_uncompressed / (1024*1024):6.1f} MB | Rate: {rate:4.2f} MB/s | Elapsed: {elapsed:5.1f}s",
                flush=True
            )

        # Flush any remaining uncompressed bytes
        tail = decompressor.flush()
        if tail:
            f_out.write(tail)
            sha256.update(tail)
            total_uncompressed += len(tail)

    if total_uncompressed != UNCOMPRESSED_SIZE:
        if temp_file.exists():
            temp_file.unlink()
        raise ValueError(
            f"Extraction size mismatch! Expected {UNCOMPRESSED_SIZE} bytes, got {total_uncompressed}"
        )

    if TARGET_FILE.exists():
        TARGET_FILE.unlink()
    temp_file.rename(TARGET_FILE)

    digest = sha256.hexdigest()
    print(f"\nSuccessfully downloaded and extracted {TARGET_FILE}")
    print(f"File size: {TARGET_FILE.stat().st_size} bytes")
    print(f"SHA256: {digest}")

    return verify_checkpoint(TARGET_FILE)


def verify_checkpoint(ckpt_path: Path):
    print(f"\nVerifying checkpoint: {ckpt_path}")
    assert ckpt_path.exists(), f"File does not exist: {ckpt_path}"
    size = ckpt_path.stat().st_size
    print(f"File size: {size} bytes ({size / (1024*1024):.2f} MB)")

    # Load with torch on CPU
    print("Loading with torch.load(..., map_location='cpu')...")
    ckpt = torch.load(str(ckpt_path), map_location="cpu")
    print(f"Checkpoint object type: {type(ckpt)}")
    if isinstance(ckpt, dict):
        print(f"Checkpoint keys: {list(ckpt.keys())}")
        if "state_dict" in ckpt:
            sd = ckpt["state_dict"]
            print(f"State dict keys count: {len(sd)}")
            first_5 = list(sd.keys())[:5]
            print(f"First 5 layer keys: {first_5}")
            last_layer = list(sd.keys())[-2] if len(sd) > 1 else list(sd.keys())[-1]
            print(f"Sample layer ({last_layer}) shape: {sd[last_layer].shape}")
    print("Verification completed successfully!")
    return True


if __name__ == "__main__":
    download_and_extract_checkpoint()
