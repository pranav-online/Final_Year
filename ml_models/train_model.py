import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
import os
import json
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import numpy as np

# ─── Configuration ──────────────────────────────────────────
CONFIG = {
    "data_dir":    "dataset",
    "model_path":  "model.pt",
    "classes_path":"class_names.json",
    "img_size":    224,
    "batch_size":  32,
    "epochs":      10,
    "lr":          0.001,
    "val_split":   0.2
}

# ─── Data Transforms ────────────────────────────────────────
train_transform = transforms.Compose([
    transforms.Resize((CONFIG["img_size"], CONFIG["img_size"])),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((CONFIG["img_size"], CONFIG["img_size"])),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

def train():
    print("🔄 Loading dataset...")

    # Load full dataset
    full_dataset = datasets.ImageFolder(
        CONFIG["data_dir"],
        transform=train_transform
    )

    # Get class names
    class_names = full_dataset.classes
    num_classes = len(class_names)
    print(f"✅ Found {num_classes} classes: {class_names}")

    # Save class names
    with open(CONFIG["classes_path"], "w") as f:
        json.dump(class_names, f)
    print("✅ Class names saved!")

    # Split dataset
    val_size  = int(len(full_dataset) * CONFIG["val_split"])
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size]
    )
    val_dataset.dataset.transform = val_transform

    # Data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=True,
        num_workers=0
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
        num_workers=0
    )

    print(f"📊 Train: {train_size} | Val: {val_size}")

    # ─── Model ──────────────────────────────────────────────
    print("🔄 Loading MobileNetV2...")
    model = models.mobilenet_v2(weights="IMAGENET1K_V1")

    # Freeze base layers
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier
    model.classifier[1] = nn.Linear(
        model.last_channel, num_classes
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Using device: {device}")
    model = model.to(device)

    # ─── Training Setup ─────────────────────────────────────
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(
        model.classifier.parameters(),
        lr=CONFIG["lr"]
    )
    scheduler = optim.lr_scheduler.StepLR(
        optimizer, step_size=3, gamma=0.1
    )

    # ─── Training Loop ──────────────────────────────────────
    best_val_acc  = 0.0
    train_losses  = []
    val_accuracies = []

    for epoch in range(CONFIG["epochs"]):
        model.train()
        running_loss = 0.0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss    = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

            if (batch_idx + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}/{CONFIG['epochs']} "
                      f"Batch {batch_idx+1}/{len(train_loader)} "
                      f"Loss: {loss.item():.4f}")

        avg_loss = running_loss / len(train_loader)
        train_losses.append(avg_loss)

        # Validation
        model.eval()
        correct = total = 0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                total   += labels.size(0)
                correct += (predicted == labels).sum().item()
                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        val_acc = correct / total * 100
        val_accuracies.append(val_acc)
        scheduler.step()

        print(f"\n📊 Epoch {epoch+1}/{CONFIG['epochs']} "
              f"Loss: {avg_loss:.4f} "
              f"Val Accuracy: {val_acc:.2f}%\n")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), CONFIG["model_path"])
            print(f"  💾 Best model saved! Accuracy: {val_acc:.2f}%")

    print(f"\n🎉 Training Complete!")
    print(f"✅ Best Validation Accuracy: {best_val_acc:.2f}%")

    # ─── Confusion Matrix ───────────────────────────────────
    print("\n📊 Generating confusion matrix...")
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        xticklabels=class_names,
        yticklabels=class_names,
        cmap="Blues"
    )
    plt.title("Confusion Matrix")
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png")
    print("✅ Confusion matrix saved!")

    # ─── Classification Report ──────────────────────────────
    print("\n📋 Classification Report:")
    print(classification_report(
        all_labels, all_preds,
        target_names=class_names
    ))

    # ─── Training Curve ─────────────────────────────────────
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(train_losses)
    plt.title("Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")

    plt.subplot(1, 2, 2)
    plt.plot(val_accuracies)
    plt.title("Validation Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy %")
    plt.tight_layout()
    plt.savefig("training_curves.png")
    print("✅ Training curves saved!")

if __name__ == "__main__":
    train()