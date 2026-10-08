try:
    import torch
    import torch.nn as nn
    from torchvision import transforms, models
    TORCH_AVAILABLE = True
except Exception:
    torch = None
    nn = None
    transforms = None
    models = None
    TORCH_AVAILABLE = False

from PIL import Image
from PIL import UnidentifiedImageError
import io
import os
import json
import gdown
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ─────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(__file__)
MODEL_PATH       = os.path.join(BASE_DIR, "../../ml_models/model.pt")
CLASS_NAMES_PATH = os.path.join(BASE_DIR, "../../ml_models/class_names.json")

# ─── Google Drive IDs ───────────────────────────────────────
MODEL_GDRIVE_ID      = "1ncAsRz5y1g6QlifZASx5nsOWfApusZFc"
CLASS_NAMES_GDRIVE_ID = "1JTrlKYt1N5pc_AlbatrZjG1IdR1mrj9a"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
MODEL_WEIGHTS_LOADED = False

# ─── Download Files if Not Found ───────────────────────────
def download_files_if_needed():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    # Download model.pt
    if not os.path.exists(MODEL_PATH):
        print("Downloading model.pt from Google Drive...")
        try:
            gdown.download(
                f"https://drive.google.com/uc?id={MODEL_GDRIVE_ID}",
                MODEL_PATH,
                quiet=False
            )
            print("model.pt downloaded!")
        except Exception as e:
            print(f"model.pt download failed: {e}")

    # Download class_names.json
    if not os.path.exists(CLASS_NAMES_PATH):
        print("Downloading class_names.json from Google Drive...")
        try:
            gdown.download(
                f"https://drive.google.com/uc?id={CLASS_NAMES_GDRIVE_ID}",
                CLASS_NAMES_PATH,
                quiet=False
            )
            print("class_names.json downloaded!")
        except Exception as e:
            print(f"class_names.json download failed: {e}")

# Download on startup
download_files_if_needed()

# ─── Load Class Names ───────────────────────────────────────
# Try multiple paths
possible_class_paths = [
    CLASS_NAMES_PATH,
    r"D:\ALIP-TOTAL\ALIP\ml_models\class_names.json",
    os.path.join(BASE_DIR, "../ml_models/class_names.json")
]

CLASS_NAMES = None
for path in possible_class_paths:
    if os.path.exists(path):
        with open(path, "r") as f:
            CLASS_NAMES = json.load(f)
        print(f"Loaded {len(CLASS_NAMES)} disease classes")
        break

if CLASS_NAMES is None:
    CLASS_NAMES = [
        "Corn_(maize)___Common_rust_",
        "Corn_(maize)___healthy",
        "Pepper,_bell___healthy",
        "Potato___Early_blight",
        "Potato___Late_blight",
        "Potato___healthy",
        "Tomato___Bacterial_spot",
        "Tomato___Early_blight",
        "Tomato___Late_blight",
        "Tomato___healthy"
    ]
    print("Using default class names")

# ─── Treatment Recommendations ─────────────────────────────
TREATMENTS = {
    "Tomato___healthy": {
        "status":    "healthy",
        "severity":  "None",
        "treatment": "Your tomato crop is healthy! Continue regular care.",
        "prevention":"Maintain proper irrigation and inspect regularly."
    },
    "Tomato___Early_blight": {
        "status":    "diseased",
        "severity":  "Medium",
        "treatment": "Apply Mancozeb or Chlorothalonil fungicide every 7 days.",
        "prevention":"Avoid overhead irrigation. Remove infected leaves immediately."
    },
    "Tomato___Late_blight": {
        "status":    "diseased",
        "severity":  "High",
        "treatment": "Apply Metalaxyl or Cymoxanil fungicide urgently.",
        "prevention":"Plant resistant varieties. Avoid wet and humid conditions."
    },
    "Tomato___Bacterial_spot": {
        "status":    "diseased",
        "severity":  "High",
        "treatment": "Apply copper-based bactericides immediately.",
        "prevention":"Use disease-free seeds. Avoid working in wet conditions."
    },
    "Potato___healthy": {
        "status":    "healthy",
        "severity":  "None",
        "treatment": "Your potato crop is healthy! Continue regular care.",
        "prevention":"Monitor regularly for early signs of disease."
    },
    "Potato___Early_blight": {
        "status":    "diseased",
        "severity":  "Medium",
        "treatment": "Apply Mancozeb fungicide. Remove infected leaves.",
        "prevention":"Rotate crops. Avoid excess nitrogen fertilization."
    },
    "Potato___Late_blight": {
        "status":    "diseased",
        "severity":  "High",
        "treatment": "Apply Metalaxyl-based fungicide immediately. Spreads fast!",
        "prevention":"Plant certified disease-free seed tubers. Ensure good drainage."
    },
    "Corn_(maize)___healthy": {
        "status":    "healthy",
        "severity":  "None",
        "treatment": "Your corn crop is healthy! Continue regular care.",
        "prevention":"Maintain proper spacing and fertilization schedule."
    },
    "Corn_(maize)___Common_rust_": {
        "status":    "diseased",
        "severity":  "Medium",
        "treatment": "Apply Propiconazole or Azoxystrobin fungicide.",
        "prevention":"Plant rust-resistant varieties. Monitor humidity levels."
    },
    "Pepper,_bell___healthy": {
        "status":    "healthy",
        "severity":  "None",
        "treatment": "Your pepper crop is healthy! Continue regular care.",
        "prevention":"Ensure proper drainage and avoid overwatering."
    }
}

# ─── Image Preprocessing ───────────────────────────────────
if TORCH_AVAILABLE:
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
else:
    transform = None

# ─── Load Model ────────────────────────────────────────────
def load_disease_model():
    global MODEL_WEIGHTS_LOADED
    MODEL_WEIGHTS_LOADED = False

    if not TORCH_AVAILABLE:
        print("Disease prediction is unavailable: PyTorch/TorchVision is not installed in this environment.")
        return None

    print("Loading disease model...")

    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(
        model.last_channel, len(CLASS_NAMES)
    )

    # Try multiple paths
    possible_paths = [
        MODEL_PATH,
        r"D:\ALIP-TOTAL\ALIP\ml_models\model.pt",
        os.path.join(BASE_DIR, "../../ml_models/model.pt")
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                state_dict = torch.load(
                    path,
                    map_location=torch.device("cpu")
                )
                model.load_state_dict(state_dict)
                print(f"Disease model loaded from: {path}")
                MODEL_WEIGHTS_LOADED = True
                break
            except Exception as e:
                print(f"Error loading from {path}: {e}")

    if not MODEL_WEIGHTS_LOADED:
        print("Disease prediction is unavailable: trained model weights are missing or invalid.")
        return None

    model.eval()
    return model

# Load model at startup
disease_model = load_disease_model()


def get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key.lower() in {
        "",
        "your_gemini_api_key",
        "your-gemini-api-key",
        "your_api_key",
        "replace_me",
    }:
        return ""
    return api_key


def get_disease_service_status() -> dict:
    api_key = get_gemini_api_key()
    gemini_configured = bool(api_key)
    local_prediction_available = bool(
        TORCH_AVAILABLE and MODEL_WEIGHTS_LOADED and disease_model is not None
    )
    prediction_available = local_prediction_available or gemini_configured

    if local_prediction_available:
        prediction_source = "local_model"
        prediction_message = "Trained disease prediction model is ready."
    elif gemini_configured:
        prediction_source = "gemini"
        prediction_message = "Gemini image classification is ready; the result will be AI-estimated."
    else:
        prediction_source = None
        missing_requirements = []
        if not TORCH_AVAILABLE:
            missing_requirements.append("PyTorch/TorchVision is not installed")
        else:
            missing_requirements.append("trained disease model weights are missing or invalid")
        missing_requirements.append(
            "add GEMINI_API_KEY to the backend environment to enable Gemini image analysis"
        )
        prediction_message = "; ".join(missing_requirements) + "."

    return {
        "success": True,
        "prediction_available": prediction_available,
        "prediction_source": prediction_source,
        "prediction_message": prediction_message,
        "gemini_configured": gemini_configured,
        "gemini_model": GEMINI_MODEL,
        "gemini_fallback_model": GEMINI_FALLBACK_MODEL,
    }


def classify_image_with_gemini(
    image: Image.Image,
    client,
    model_name: str = GEMINI_MODEL,
) -> tuple[str, float]:
    allowed_classes = "\n".join(f"- {name}" for name in CLASS_NAMES)
    prompt = f"""Classify the crop leaf in this image. Choose exactly one class from the allowed classes below.
Return only a JSON object with this shape:
{{"class_name": "one exact allowed class", "confidence": 0}}
Confidence must be a number from 0 to 100 and should reflect uncertainty; do not claim certainty when the image is unclear.
If the image does not clearly show a crop leaf or the disease is not distinguishable, use the exact class name "uncertain" and set confidence to 0.

Allowed classes:
{allowed_classes}"""

    response = client.models.generate_content(
        model=model_name,
        contents=[prompt, image],
    )
    response_text = (response.text or "").strip()
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        classification = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned an unreadable classification.") from exc

    class_name = classification.get("class_name")
    confidence = classification.get("confidence")
    if class_name == "uncertain":
        raise ValueError("Gemini could not confidently identify a supported crop disease.")
    if class_name not in CLASS_NAMES:
        raise ValueError("Gemini returned a class that is not supported by this disease model.")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("Gemini returned an invalid confidence value.")
    if not 0 <= confidence <= 100:
        raise ValueError("Gemini confidence must be between 0 and 100.")

    return class_name, round(float(confidence), 2)


# ─── Predict Disease ───────────────────────────────────────
async def predict_disease(image_bytes: bytes) -> dict:
    try:
        local_prediction_available = bool(
            TORCH_AVAILABLE and disease_model is not None
            and transform is not None and MODEL_WEIGHTS_LOADED
        )
        api_key = get_gemini_api_key()
        gemini_configured = bool(api_key)
        if not local_prediction_available and not gemini_configured:
            return {
                "success": False,
                "error_code": "model_unavailable",
                "error": (
                    "Disease analysis is unavailable: trained model weights are missing "
                    "and GEMINI_API_KEY is not configured."
                )
            }

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except (UnidentifiedImageError, OSError):
            return {
                "success": False,
                "error_code": "invalid_image",
                "error": "The uploaded file is not a valid or readable image."
            }

        if local_prediction_available:
            input_tensor = transform(image).unsqueeze(0)
            with torch.no_grad():
                outputs = disease_model(input_tensor)
                probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
                confidence, predicted_idx = torch.max(probabilities, 0)

            predicted_class = CLASS_NAMES[predicted_idx.item()]
            confidence_score = round(confidence.item() * 100, 2)
            prediction_source = "local_model"
        else:
            client = genai.Client(api_key=api_key)
            classification_models = [GEMINI_MODEL]
            if GEMINI_FALLBACK_MODEL != GEMINI_MODEL:
                classification_models.append(GEMINI_FALLBACK_MODEL)

            prediction_model = None
            for model_name in classification_models:
                try:
                    predicted_class, confidence_score = classify_image_with_gemini(
                        image,
                        client,
                        model_name,
                    )
                    prediction_model = model_name
                    break
                except Exception as exc:
                    print(f"Gemini image classification failed with {model_name}: {exc}")

            if prediction_model is None:
                error_message = (
                    "Gemini image classification failed with the configured primary "
                    "and fallback models. Check Gemini service availability and model access."
                )
                return {
                    "success": False,
                    "error_code": "classification_failed",
                    "error": error_message,
                }
            prediction_source = "gemini"

        treatment_info = TREATMENTS.get(predicted_class, {
            "status":    "unknown",
            "severity":  "Unknown",
            "treatment": "Please consult an agricultural expert.",
            "prevention":"Monitor your crop regularly."
        })

        display_name = predicted_class.replace(
            "___", " - "
        ).replace("_", " ")

        detailed_report = ""
        ai_report_status = "unconfigured"
        try:
            if api_key:
                client = genai.Client(api_key=api_key)
                
                system_prompt = """You are an expert agricultural AI assistant. Your goal is to help farmers quickly understand their crop disease and take action.

Your response MUST be divided into exactly three sections using these EXACT markers:

---FIRST_SCREEN---
---SECOND_SCREEN---
---THIRD_SCREEN---

Generate ALL three sections. Here is the structure:

---FIRST_SCREEN---

# 🚨 Action Required

• Immediate Treatment Required
• Disease Can Spread Quickly
• Start Treatment Within [recommended timeframe based on severity]

# 💊 Recommended Medicines

🥇 **[Best Medicine Name]**
- Effectiveness: ⭐⭐⭐⭐⭐

🥈 **[Second Medicine Name]**
- Effectiveness: ⭐⭐⭐⭐⭐

🥉 **[Third Medicine Name]**
- Effectiveness: ⭐⭐⭐⭐

# ✅ Today's Action Plan

1️⃣ [First urgent step]

2️⃣ [Second step]

3️⃣ [Third step]

4️⃣ [Fourth step]

5️⃣ [Fifth step - monitoring]

Maximum 5 steps. No paragraphs. Short actionable sentences only.

---SECOND_SCREEN---

# ☁ Why This Happened

Generate simple bullet points with icons. Maximum 5 causes.

Example format:
- ☁ High humidity
- 🌧 Recent rainfall
- 💧 Excess leaf wetness
- 🌱 Poor air circulation
- 🌾 Dense planting

# ✅ Prevent Next Time

Generate a checklist. Maximum 6 points.

Example format:
- ✔ Use disease-resistant seeds
- ✔ Avoid watering leaves
- ✔ Maintain proper spacing
- ✔ Remove infected debris
- ✔ Inspect plants weekly

# 🛒 Recommended Products

🥇 **[Product Name]**
- Active Ingredient: [ingredient]
- Best For: [usage]
- Effectiveness: ⭐⭐⭐⭐⭐

🥈 **[Product Name]**
- Active Ingredient: [ingredient]
- Best For: [usage]
- Effectiveness: ⭐⭐⭐⭐⭐

🥉 **[Product Name]**
- Active Ingredient: [ingredient]
- Best For: [usage]
- Effectiveness: ⭐⭐⭐⭐

# 💰 Economic Impact

**Without Treatment:**
- 💰 Yield Loss: [XX]%
- ⚠ Risk: High

**With Treatment:**
- 💰 Yield Loss: [XX]%
- ✅ Risk: Low

[One short sentence summary, e.g. "Timely treatment can save most of the crop."]

# ❓ Frequently Asked Questions

**❓ What is this disease?**
- [Short bullet answer]

**❓ Why did this happen?**
- [Short bullet answer]

**❓ Can it spread to nearby plants?**
- [Short bullet answer]

**❓ Which medicine is best?**
- [Short bullet answer]

**❓ When should I spray?**
- [Short bullet answer]

**❓ How often should I spray?**
- [Short bullet answer]

**❓ Will my yield be affected?**
- [Short bullet answer]

**❓ Is it safe after rain?**
- [Short bullet answer]

**❓ Can I use organic treatment?**
- [Short bullet answer]

**❓ What should I do next season?**
- [Short bullet answer]

Maximum 5 bullets per answer. Keep answers short, practical, farmer-friendly.

---THIRD_SCREEN---

# 🔬 Detailed AI Report

- Infection Stage: [Early / Mid / Advanced]
- Damage Percentage: [XX]%
- Disease Spread Risk: [XX]%
- Urgency Level: [Low / Medium / High / Critical]
- Affected Plant Parts: [list]

# 🧬 Scientific Explanation

- Scientific Name: [name]
- Pathogen Type: [Fungal / Bacterial / Viral]
- Disease Lifecycle: [brief explanation]
- Conditions Favoring Disease: [brief explanation]

# 📅 Disease Spread Forecast (7-Day)

| Day | Risk Level | Reason |
|-----|-----------|--------|
| Day 1 | [High/Medium/Low] | [short reason] |
| Day 2 | [High/Medium/Low] | [short reason] |
| Day 3 | [High/Medium/Low] | [short reason] |
| Day 4 | [High/Medium/Low] | [short reason] |
| Day 5 | [High/Medium/Low] | [short reason] |
| Day 6 | [High/Medium/Low] | [short reason] |
| Day 7 | [High/Medium/Low] | [short reason] |

# 🔍 Advanced Analysis

- Leaf Damage Analysis: [description]
- Color Analysis: [description]
- Pattern Analysis: [description]
- Confidence Breakdown: [description]
- Similar Disease Comparison: [list similar diseases and why this one was chosen]

# 📋 Full Treatment Procedure

- Mixing Ratio: [specific ratio]
- Spray Method: [method]
- Best Time To Spray: [time]
- Repeat Interval: [interval]
- Safety Precautions: [list]

STRICT RULES:
- Use simple farmer-friendly language everywhere.
- Use icons and emojis for visual clarity.
- Use bullet points, NOT paragraphs.
- Keep the FIRST SCREEN short and actionable.
- Do NOT use technical tables on the first screen.
- Every recommendation must be specific to the detected crop and disease.
- Do NOT generate generic advice.
- The three section markers (---FIRST_SCREEN---, ---SECOND_SCREEN---, ---THIRD_SCREEN---) MUST appear exactly as shown."""
                
                ai_prompt = f"Detected Crop and Disease: {display_name}\nConfidence Score: {confidence_score}%\nInitial Severity Assessment: {treatment_info['severity']}\n\n{system_prompt}"
                try:
                    ai_response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=[ai_prompt, image]
                    )
                except Exception as e:
                    print(f"{GEMINI_MODEL} failed ({e}). Falling back to {GEMINI_FALLBACK_MODEL}...")
                    ai_response = client.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=[ai_prompt, image]
                    )
                detailed_report = ai_response.text or ""
                if detailed_report.strip():
                    ai_report_status = "generated"
                else:
                    ai_report_status = "failed"
                    detailed_report = "Gemini returned an empty report. Showing the classifier treatment guidance instead."
            else:
                detailed_report = "Gemini report generation is not configured. Showing the classifier treatment guidance instead."
        except Exception as ai_e:
            print(f"AI generation failed: {ai_e}")
            ai_report_status = "failed"
            detailed_report = "Gemini report generation failed. Showing the classifier treatment guidance instead."

        return {
            "success":    True,
            "disease":    display_name,
            "raw_class":  predicted_class,
            "confidence": confidence_score,
            "prediction_source": prediction_source,
            "prediction_model": (
                prediction_model if prediction_source == "gemini" else None
            ),
            "severity":   treatment_info["severity"],
            "status":     treatment_info["status"],
            "treatment":  treatment_info["treatment"],
            "prevention": treatment_info["prevention"],
            "detailed_report": detailed_report,
            "ai_report_status": ai_report_status,
        }

    except Exception as e:
        return {
            "success": False,
            "error":   str(e)
        }
