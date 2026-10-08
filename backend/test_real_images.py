"""
ALIP - Real Field Image Evaluation Script
Tests disease detection on real-world field images
Run: python test_real_images.py
"""

import requests
import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

BASE_URL   = "http://127.0.0.1:8000"
IMAGE_DIR  = r"D:\ALIP-TOTAL\ALIP\ml_models\real_field_images"
OUTPUT_DIR = "journal_figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Define Expected Labels ────────────────────────────
# Map your image filenames to expected classes
# Edit this dictionary to match YOUR image filenames!
EXPECTED_LABELS = {
    # Corn Rust
    "corn_rust-1.jpg":              "Corn (maize) - Common rust",
    "corn_rust-2.jpg":              "Corn (maize) - Common rust",
    "corn_rust-3.jpg":              "Corn (maize) - Common rust",

    # Healthy Tomato
    "healthy_tomato-1.jpg":         "Tomato - healthy",
    "healthy_tomato-2.jpg":         "Tomato - healthy",
    "healthy_tomato-3.jpg":         "Tomato - healthy",

    # Potato Early Blight
    "potato_earlt_blight-1.jpg":    "Potato - Early blight",
    "potato_earlt_blight-3.jpg":    "Potato - Early blight",
    "potato_early_blight-2.jpg":    "Potato - Early blight",

    # Tomato Early Blight
    "tomato_early_bright-1.jpg":    "Tomato - Early blight",
    "tomato_early_bright-2.jpg":    "Tomato - Early blight",
    "tomato_early_bright-3.jpg":    "Tomato - Early blight",

    # Tomato Late Blight
    "tomato_late_blight-3.jpg":     "Tomato - Late blight",
    "tomato_light_blight-2.jpg":    "Tomato - Late blight",
    "tomto_late_blight-1.jpg":      "Tomato - Late blight",
}
print("🔬 ALIP Real Field Image Evaluation")
print("="*55)
print(f"📁 Image directory: {IMAGE_DIR}")
print(f"🖼️  Expected images: {len(EXPECTED_LABELS)}\n")

# ─── Get actual images in folder ───────────────────────
available_images = []
if os.path.exists(IMAGE_DIR):
    for f in os.listdir(IMAGE_DIR):
        if f.lower().endswith(
            ('.jpg','.jpeg','.png','.webp')
        ):
            available_images.append(f)

print(f"✅ Found {len(available_images)} images in folder:")
for img in available_images:
    print(f"   → {img}")
print()

if not available_images:
    print("❌ No images found! Check IMAGE_DIR path.")
    exit()

# ─── Test Each Image ───────────────────────────────────
results     = []
correct     = 0
total       = 0
errors      = 0

for filename in available_images:
    filepath = os.path.join(IMAGE_DIR, filename)
    expected = EXPECTED_LABELS.get(
        filename,
        "Unknown"  # if filename not in dict
    )

    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/disease/predict",
                files={"file": (filename, f,
                                "image/jpeg")}
            )

        if response.status_code == 200:
            data       = response.json()
            predicted  = data.get("disease", "Error")
            confidence = data.get("confidence", 0)
            status     = data.get("status", "")

            # Check if correct
            is_correct = (
                expected.lower().replace(" ","")
                in predicted.lower().replace(" ","")
            ) if expected != "Unknown" else None

            if is_correct is True:
                correct += 1
            if expected != "Unknown":
                total += 1

            results.append({
                "filename":   filename,
                "expected":   expected,
                "predicted":  predicted,
                "confidence": confidence,
                "correct":    is_correct,
                "status":     status
            })

            # Print result
            if expected == "Unknown":
                symbol = "🔍"
            elif is_correct:
                symbol = "✅"
            else:
                symbol = "❌"

            print(f"{symbol} {filename}")
            print(f"   Expected:  {expected}")
            print(f"   Predicted: {predicted}")
            print(f"   Confidence:{confidence}%")
            print()

        else:
            print(f"❌ API Error for {filename}: "
                  f"{response.status_code}")
            errors += 1

    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")
        errors += 1

# ─── Summary ───────────────────────────────────────────
print("="*55)
print("📊 EVALUATION SUMMARY")
print("="*55)

if total > 0:
    accuracy = (correct / total) * 100
    print(f"Total images tested:  {len(available_images)}")
    print(f"Images with labels:   {total}")
    print(f"Correctly predicted:  {correct}")
    print(f"Incorrectly predicted:{total - correct}")
    print(f"Errors:               {errors}")
    print(f"\n🎯 Real Field Accuracy: {accuracy:.2f}%")
    print(f"   PlantVillage Acc:   97.34%")
    print(f"   Domain Shift Drop:  {97.34 - accuracy:.2f}%")
else:
    print("No labelled images found.")
    print("Add filenames to EXPECTED_LABELS dict!")
    accuracy = 0

# ─── Save Results to JSON ──────────────────────────────
with open(f"{OUTPUT_DIR}/real_image_results.json", "w") as f:
    json.dump({
        "total_images":   len(available_images),
        "labelled_images":total,
        "correct":        correct,
        "accuracy":       accuracy if total > 0 else None,
        "plantvillage_accuracy": 97.34,
        "results":        results
    }, f, indent=2)
print(f"\n✅ Results saved to {OUTPUT_DIR}/real_image_results.json")

# ─── Visualization ─────────────────────────────────────
if results:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Plot 1 — Accuracy comparison
    ax1 = axes[0]
    bars = ax1.bar(
        ['PlantVillage\n(Controlled)', 'Real Field\n(Natural)'],
        [97.34, accuracy if total > 0 else 0],
        color=['#3266AD', '#1D9E75'],
        edgecolor=['#1A4A8A', '#0F6E56'],
        linewidth=0.8, width=0.5
    )
    for bar, val in zip(bars, [97.34,
                                accuracy if total > 0 else 0]):
        ax1.text(
            bar.get_x() + bar.get_width()/2,
            bar.get_height() + 0.5,
            f'{val:.2f}%',
            ha='center', fontweight='bold', fontsize=11
        )
    ax1.set_ylim(0, 115)
    ax1.set_ylabel('Classification Accuracy (%)',
                   fontweight='bold')
    ax1.set_title(
        'PlantVillage vs Real Field\nImage Accuracy',
        fontweight='bold'
    )

    # Plot 2 — Confidence distribution
    ax2 = axes[1]
    confidences = [r['confidence'] for r in results
                   if r['confidence'] > 0]
    if confidences:
        ax2.hist(confidences, bins=10,
                 color='#3266AD', edgecolor='#1A4A8A',
                 linewidth=0.8)
        ax2.axvline(x=np.mean(confidences),
                    color='#E07B39', linestyle='--',
                    linewidth=2,
                    label=f'Mean: {np.mean(confidences):.1f}%')
        ax2.set_xlabel('Confidence Score (%)',
                       fontweight='bold')
        ax2.set_ylabel('Number of Images',
                       fontweight='bold')
        ax2.set_title('Confidence Score Distribution\n'
                      'on Real Field Images',
                      fontweight='bold')
        ax2.legend()

    plt.suptitle(
        'ALIP Disease Detection — Real Field Image Evaluation',
        fontweight='bold', y=1.02
    )
    plt.tight_layout()
    plt.savefig(
        f'{OUTPUT_DIR}/fig_real_field_evaluation.png',
        dpi=300, bbox_inches='tight'
    )
    plt.close()
    print("✅ Evaluation figure saved!")

print(f"""
{'='*55}
📋 TEXT FOR JOURNAL PAPER (Section V Discussion)
{'='*55}
To evaluate real-world performance beyond the controlled
PlantVillage dataset, the model was tested on
{len(available_images)} real-world field images collected
from online agricultural resources. The model achieved
{accuracy:.2f}% accuracy on these images, compared to
97.34% on the controlled validation set, confirming the
domain shift challenge reported by Barbedo [16].
The {97.34-accuracy:.2f}% performance drop is consistent
with findings in the literature and will be addressed in
future work through field image augmentation.
{'='*55}
""")