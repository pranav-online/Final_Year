"""
Crop Recommendation Model — Proper Evaluation
Run: python evaluate_crop_model.py
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    cross_val_score, StratifiedKFold,
    train_test_split
)
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os

os.makedirs("journal_figures", exist_ok=True)

print("Loading dataset...")
df = pd.read_csv("data/Crop_recommendation.csv")

X = df[["N","P","K","temperature","humidity","ph","rainfall"]]
y = df["label"]

le = LabelEncoder()
y_enc = le.fit_transform(y)

# ─── Proper Train/Test Split ────────────────────────────
# Use 70/30 instead of 80/20 for more honest evaluation
X_train, X_test, y_train, y_test = train_test_split(
    X, y_enc, test_size=0.30,
    random_state=42, stratify=y_enc
)

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
model.fit(X_train, y_train)

# ─── Test Set Accuracy ──────────────────────────────────
y_pred = model.predict(X_test)
test_acc = accuracy_score(y_test, y_pred)
print(f"\n📊 Test Set Accuracy: {test_acc*100:.2f}%")

# ─── 10-Fold Cross Validation ──────────────────────────
print("\n🔄 Running 10-Fold Cross-Validation...")
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
cv_scores = cross_val_score(
    model, X, y_enc,
    cv=cv, scoring='accuracy'
)

print(f"\n📊 10-Fold Cross-Validation Results:")
print(f"   Fold Scores: {[f'{s*100:.2f}%' for s in cv_scores]}")
print(f"   Mean Accuracy: {cv_scores.mean()*100:.2f}%")
print(f"   Std Dev:       {cv_scores.std()*100:.2f}%")
print(f"   95% CI:        [{(cv_scores.mean()-1.96*cv_scores.std())*100:.2f}%"
      f" - {(cv_scores.mean()+1.96*cv_scores.std())*100:.2f}%]")

# ─── Classification Report ─────────────────────────────
print("\n📋 Classification Report:")
print(classification_report(
    y_test, y_pred,
    target_names=le.classes_
))

# ─── Confusion Matrix ──────────────────────────────────
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(14, 12))
sns.heatmap(
    cm, annot=True, fmt='d',
    cmap='Blues',
    xticklabels=le.classes_,
    yticklabels=le.classes_,
    linewidths=0.5
)
plt.title(
    f'Crop Recommendation Model — Confusion Matrix\n'
    f'(30% Test Set, Accuracy: {test_acc*100:.2f}%)',
    fontweight='bold'
)
plt.xlabel('Predicted', fontweight='bold')
plt.ylabel('Actual', fontweight='bold')
plt.xticks(rotation=45, ha='right', fontsize=8)
plt.yticks(rotation=0, fontsize=8)
plt.tight_layout()
plt.savefig('journal_figures/fig_crop_confusion_matrix.png', dpi=300)
plt.close()
print("✅ Crop confusion matrix saved!")

# ─── Cross-Validation Plot ─────────────────────────────
plt.figure(figsize=(10, 5))
folds = range(1, 11)
plt.bar(folds, cv_scores*100,
        color='#1D9E75', edgecolor='#0F6E56',
        linewidth=0.8)
plt.axhline(y=cv_scores.mean()*100,
            color='#E07B39', linestyle='--',
            linewidth=2, label=f'Mean: {cv_scores.mean()*100:.2f}%')
plt.fill_between(
    [0.5, 10.5],
    [(cv_scores.mean()-cv_scores.std())*100]*2,
    [(cv_scores.mean()+cv_scores.std())*100]*2,
    alpha=0.2, color='#E07B39', label='±1 Std Dev'
)
plt.xlabel('Fold Number', fontweight='bold')
plt.ylabel('Accuracy (%)', fontweight='bold')
plt.title(
    'Crop Recommendation Model — 10-Fold Cross-Validation\n'
    f'Mean: {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%',
    fontweight='bold'
)
plt.legend()
plt.xticks(folds)
plt.ylim(85, 105)
plt.tight_layout()
plt.savefig('journal_figures/fig_crop_crossval.png', dpi=300)
plt.close()
print("✅ Cross-validation plot saved!")

# ─── Feature Importance ────────────────────────────────
importances = model.feature_importances_
features = ["N", "P", "K", "Temperature",
            "Humidity", "pH", "Rainfall"]
sorted_idx = np.argsort(importances)[::-1]

plt.figure(figsize=(8, 5))
plt.bar(
    [features[i] for i in sorted_idx],
    importances[sorted_idx],
    color='#3266AD', edgecolor='#1A4A8A',
    linewidth=0.8
)
plt.xlabel('Feature', fontweight='bold')
plt.ylabel('Importance Score', fontweight='bold')
plt.title('Random Forest Feature Importance\nfor Crop Recommendation',
          fontweight='bold')
plt.tight_layout()
plt.savefig('journal_figures/fig_crop_feature_importance.png', dpi=300)
plt.close()
print("✅ Feature importance plot saved!")

# Save updated model
joblib.dump(model, 'data/crop_model.pkl')
joblib.dump(le,    'data/label_encoder.pkl')
print("\n✅ Updated model saved!")

print(f"""
{'='*55}
📋 SUMMARY FOR JOURNAL PAPER
{'='*55}
Test Set Accuracy (30% holdout): {test_acc*100:.2f}%
10-Fold CV Mean Accuracy:        {cv_scores.mean()*100:.2f}%
10-Fold CV Std Dev:              {cv_scores.std()*100:.2f}%
95% Confidence Interval:
  Lower: {(cv_scores.mean()-1.96*cv_scores.std())*100:.2f}%
  Upper: {(cv_scores.mean()+1.96*cv_scores.std())*100:.2f}%

Use these numbers in your paper instead of 100%!
{'='*55}
""")