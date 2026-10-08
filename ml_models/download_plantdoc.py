"""
ALIP - PlantDoc Field Dataset Downloader & Filter
Downloads PlantDoc dataset and extracts only the 8 classes
that map to ALIP's existing 10 disease classes.

Run this from: D:\ALIP-TOTAL\ALIP\backend\ml_models\
Output: ml_models/plantdoc_field/<class_name>/*.jpg

WINDOWS FIX: Some PlantDoc filenames contain illegal
Windows characters (e.g. '?') left over from web-scraping.
This version uses sparse checkout + skips bad files instead
of a plain git clone, so it works reliably on Windows.
"""

import os
import shutil
import subprocess
import sys
import zipfile
import urllib.request

CLONE_DIR = "plantdoc_raw"
OUTPUT_DIR = "plantdoc_field"
ZIP_URL = "https://github.com/pratikkayal/PlantDoc-Dataset/archive/refs/heads/master.zip"
ZIP_PATH = "plantdoc_master.zip"
EXTRACTED_DIR = "PlantDoc-Dataset-master"

CLASS_MAP = {
    "Tomato leaf":                 "Tomato_healthy",
    "Tomato Early blight leaf":    "Tomato_early_blight",
    "Tomato leaf late blight":     "Tomato_late_blight",
    "Tomato leaf bacterial spot":  "Tomato_bacterial_spot",
    "Potato leaf early blight":    "Potato_early_blight",
    "Potato leaf late blight":     "Potato_late_blight",
    "Corn rust leaf":              "Corn_common_rust",
    "Bell_pepper leaf":            "Pepper_healthy",
}


def download_zip():
    """
    Download as ZIP instead of git clone. ZIP extraction
    handles odd filenames far better than git checkout
    on Windows NTFS.
    """
    if os.path.exists(EXTRACTED_DIR):
        print(f"[SKIP] {EXTRACTED_DIR} already exists, skipping download.")
        return

    print("[INFO] Downloading PlantDoc dataset as ZIP "
          "(more reliable on Windows than git clone)...")
    try:
        urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        print("[INFO] Try downloading manually from:")
        print("       https://github.com/pratikkayal/PlantDoc-Dataset")
        print("       (Code -> Download ZIP), then extract it here")
        print(f"       and rename the folder to '{EXTRACTED_DIR}'")
        sys.exit(1)

    print("[INFO] Extracting ZIP (skipping any files with "
          "illegal Windows characters)...")
    skipped = []
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        for member in zf.namelist():
            # Skip entries with illegal Windows filename chars
            if any(c in member for c in '?*:|"<>'):
                skipped.append(member)
                continue
            try:
                zf.extract(member, ".")
            except Exception as e:
                skipped.append(member)

    if skipped:
        print(f"[WARN] Skipped {len(skipped)} files with "
              f"invalid/odd names (this is expected, these "
              f"are leftover web-scrape artifacts):")
        for s in skipped[:10]:
            print(f"         - {s}")
        if len(skipped) > 10:
            print(f"         ... and {len(skipped) - 10} more")

    print("[OK] Extraction complete.")


def filter_and_copy():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_copied = 0
    summary = {}

    for split in ["train", "test"]:
        split_path = os.path.join(EXTRACTED_DIR, split)
        if not os.path.exists(split_path):
            print(f"[WARN] {split_path} not found, skipping.")
            continue

        for plantdoc_class, alip_class in CLASS_MAP.items():
            src_dir = os.path.join(split_path, plantdoc_class)
            if not os.path.exists(src_dir):
                print(f"[WARN] Class folder not found: {src_dir}")
                continue

            dst_dir = os.path.join(OUTPUT_DIR, alip_class, split)
            os.makedirs(dst_dir, exist_ok=True)

            count = 0
            for fname in os.listdir(src_dir):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    try:
                        src_file = os.path.join(src_dir, fname)
                        dst_file = os.path.join(dst_dir, fname)
                        shutil.copy2(src_file, dst_file)
                        count += 1
                    except Exception as e:
                        print(f"[WARN] Could not copy {fname}: {e}")

            summary.setdefault(alip_class, {"train": 0, "test": 0})
            summary[alip_class][split] = count
            total_copied += count

    print("\n" + "=" * 60)
    print("PlantDoc Field Data — Filtered Summary")
    print("=" * 60)
    for alip_class, counts in summary.items():
        print(f"{alip_class:30s} train={counts['train']:4d}  "
              f"test={counts['test']:4d}")
    print("-" * 60)
    print(f"Total images copied: {total_copied}")
    print("=" * 60)

    print("\n[NOTE] Potato_healthy and Corn_healthy have NO real")
    print("       field images (not present in PlantDoc).")
    print("       These remain augmentation-only — handled in")
    print("       Step 2 (field-style augmentation script).")


if __name__ == "__main__":
    download_zip()
    filter_and_copy()
    print(f"\n[DONE] Filtered field images ready in: ./{OUTPUT_DIR}/")  