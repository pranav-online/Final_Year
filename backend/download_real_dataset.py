# download_real_dataset.py
import urllib.request
import os

os.makedirs("data", exist_ok=True)

# Real dataset URL (not our synthetic one)
urls = [
    "https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv",
    "https://raw.githubusercontent.com/coderpradp/crop-recommendation/main/Crop_recommendation.csv"
]

for url in urls:
    try:
        print(f"Trying: {url}")
        urllib.request.urlretrieve(url, "data/Crop_recommendation.csv")
        import pandas as pd
        df = pd.read_csv("data/Crop_recommendation.csv")
        print(f"✅ Downloaded! Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        print(df.head(3))
        break
    except Exception as e:
        print(f"❌ Failed: {e}")
        continue