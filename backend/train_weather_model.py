import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score
import joblib, os

X = np.array([
    [38,40,10,0],[39,35,8,0],[40,45,12,0],[36,50,15,0],
    [37,42,11,0],[41,38,9,0],[35,48,13,0],[38,44,10,0],
    [8,60,5,0],[7,55,8,0],[9,65,6,0],[5,70,4,0],
    [6,58,7,0],[10,62,5,0],[8,67,6,0],[7,60,8,0],
    [25,85,8,0],[27,90,6,0],[24,88,10,5],[26,82,9,0],
    [23,86,7,0],[28,91,8,0],[25,84,11,0],[26,89,6,0],
    [28,55,35,0],[30,50,40,0],[25,60,32,5],[27,58,38,0],
    [29,52,36,0],[26,56,33,0],[28,54,37,0],[30,51,35,0],
    [22,90,15,55],[24,95,20,70],[20,88,18,60],[23,92,16,80],
    [21,91,17,65],[24,94,19,75],[22,89,16,58],[23,93,18,72],
    [26,75,10,25],[28,70,12,30],[25,72,8,22],[27,68,14,35],
    [26,74,11,28],[28,71,13,32],[25,73,9,24],[27,69,12,33],
    [28,55,12,0],[30,50,10,0],[27,60,14,2],[29,58,11,0],
    [26,52,13,1],[31,48,9,0],[28,56,12,0],[29,54,11,0],
])

y = (
    ['high_temp']*8 +
    ['low_temp']*8 +
    ['fungal_risk']*8 +
    ['high_wind']*8 +
    ['heavy_rain']*8 +
    ['moderate_rain']*8 +
    ['normal']*8
)

model = DecisionTreeClassifier(max_depth=5, random_state=42)
cv_scores = cross_val_score(model, X, y, cv=5)
print(f'5-Fold CV Accuracy: {cv_scores.mean()*100:.2f}% +/- {cv_scores.std()*100:.2f}%')
model.fit(X, y)
os.makedirs('data', exist_ok=True)
joblib.dump(model, 'data/weather_model.pkl')
print('Weather ML model saved!')
print('Classes:', model.classes_)
