"""
ALIP Performance Benchmark — 100 runs per endpoint
Run: python benchmark_performance.py
"""
import requests
import time
import statistics
import numpy as np
import matplotlib.pyplot as plt
import os

os.makedirs("journal_figures", exist_ok=True)
BASE_URL = "http://127.0.0.1:8000"
N_RUNS = 100

print(f"🔄 Running {N_RUNS} requests per endpoint...")
print("Make sure backend is running!\n")

def benchmark(name, func, n=N_RUNS):
    times = []
    errors = 0
    for i in range(n):
        try:
            start = time.time()
            func()
            end = time.time()
            times.append((end - start) * 1000)
        except Exception:
            errors += 1
    return times, errors

def print_stats(name, times):
    arr = np.array(times)
    mean = np.mean(arr)
    std  = np.std(arr)
    ci95 = 1.96 * std / np.sqrt(len(arr))
    print(f"\n📊 {name}")
    print(f"   N runs:   {len(times)}")
    print(f"   Mean:     {mean:.2f} ms")
    print(f"   Std Dev:  {std:.2f} ms")
    print(f"   Min:      {np.min(arr):.2f} ms")
    print(f"   Max:      {np.max(arr):.2f} ms")
    print(f"   95% CI:   [{mean-ci95:.2f}, {mean+ci95:.2f}] ms")
    print(f"   Median:   {np.median(arr):.2f} ms")
    return {
        'mean': mean, 'std': std,
        'min': np.min(arr), 'max': np.max(arr),
        'ci95': ci95, 'median': np.median(arr)
    }

results = {}

# Root
t, e = benchmark("Root", lambda: requests.get(f"{BASE_URL}/"))
results['Root'] = print_stats("Root Endpoint", t)

# Auth
t, e = benchmark("Auth", lambda: requests.post(
    f"{BASE_URL}/auth/login",
    json={"email":"farmer@alip.com","password":"farmer123"}
))
results['Auth'] = print_stats("Authentication", t)

# Crop Recommendation
t, e = benchmark("Crop", lambda: requests.post(
    f"{BASE_URL}/crop/recommend",
    json={"location":"Hyderabad","season":"kharif"}
))
results['Crop'] = print_stats("Crop Recommendation", t)

# Market
t, e = benchmark("Market", lambda: requests.get(
    f"{BASE_URL}/market/summary"
))
results['Market'] = print_stats("Market Summary", t)

# Notifications
t, e = benchmark("Notif", lambda: requests.get(
    f"{BASE_URL}/notifications/alerts"
))
results['Notif'] = print_stats("Notifications", t)

# Weather (fewer runs due to API rate limit)
t, e = benchmark("Weather", lambda: requests.get(
    f"{BASE_URL}/weather/advisory/Hyderabad"
), n=30)
results['Weather'] = print_stats("Weather Advisory (30 runs)", t)

# Disease (fewer runs due to model inference)
img_path = r"D:\ALIP-TOTAL\ALIP\ml_models\dataset\Tomato___Early_blight"
import os as _os
imgs = _os.listdir(img_path)
def disease_req():
    with open(_os.path.join(img_path, imgs[0]), 'rb') as f:
        requests.post(f"{BASE_URL}/disease/predict",
                      files={"file": f})
t, e = benchmark("Disease", disease_req, n=50)
results['Disease'] = print_stats("Disease Detection (50 runs)", t)

# ─── Summary Table ──────────────────────────────────────
print(f"\n{'='*65}")
print(f"{'Module':<22} {'Mean':>8} {'Std':>8} {'95% CI':>20}")
print(f"{'='*65}")
for name, r in results.items():
    ci = f"[{r['mean']-r['ci95']:.1f}, {r['mean']+r['ci95']:.1f}]"
    print(f"{name:<22} {r['mean']:>7.2f}ms {r['std']:>7.2f}ms {ci:>20}")
print(f"{'='*65}")

# ─── Plot with CI error bars ────────────────────────────
modules = list(results.keys())
means   = [results[m]['mean'] for m in modules]
cis     = [results[m]['ci95'] for m in modules]

fig, ax = plt.subplots(figsize=(11, 5.5))
bars = ax.bar(modules, means,
              color='#3266AD', edgecolor='#1A4A8A',
              linewidth=0.8, width=0.55, zorder=3)
ax.errorbar(modules, means, yerr=cis,
            fmt='none', color='#E07B39',
            capsize=5, linewidth=2, zorder=4,
            label='95% Confidence Interval')

for bar, val, ci in zip(bars, means, cis):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + ci + 1,
            f'{val:.1f}ms',
            ha='center', va='bottom',
            fontsize=8.5, fontweight='bold')

ax.set_yscale('log')
ax.set_ylabel('Response Time (ms) — log scale', fontweight='bold')
ax.set_title(
    f'ALIP API Response Time Benchmarks\n'
    f'(100 runs per endpoint, 95% Confidence Intervals)',
    fontweight='bold'
)
ax.legend()
plt.tight_layout()
plt.savefig('journal_figures/fig2_response_time_100runs.png', dpi=300)
plt.close()
print("\n✅ Updated benchmark figure saved!")