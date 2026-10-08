import os
import shutil

# Source folder
SOURCE = "PlantVillage-Dataset-master/raw/color"

# Selected classes
SELECTED_CLASSES = [
    "Tomato___healthy",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Bacterial_spot",
    "Potato___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Corn_(maize)___healthy",
    "Corn_(maize)___Common_rust_",
    "Pepper,_bell___healthy"
]

# Destination folder
DEST = "dataset"

print("🔄 Preparing dataset...")

for cls in SELECTED_CLASSES:
    src_path  = os.path.join(SOURCE, cls)
    dest_path = os.path.join(DEST, cls)

    if not os.path.exists(src_path):
        print(f"❌ Not found: {src_path}")
        continue

    os.makedirs(dest_path, exist_ok=True)

    # Copy all images
    images = os.listdir(src_path)
    for img in images:
        shutil.copy(
            os.path.join(src_path, img),
            os.path.join(dest_path, img)
        )

    print(f"✅ {cls}: {len(images)} images copied")

print("\n✅ Dataset ready!")

# Count total
total = sum(
    len(os.listdir(os.path.join(DEST, cls)))
    for cls in os.listdir(DEST)
    if os.path.isdir(os.path.join(DEST, cls))
)
print(f"📊 Total images: {total}")