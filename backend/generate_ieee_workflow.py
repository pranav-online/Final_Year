"""
ALIP - IEEE Journal Style System Workflow Diagram
Based on style used in:
- Mohanty et al. (Frontiers in Plant Science 2016)
- Kamilaris et al. (Computers Electronics Agriculture 2018)
- Picon et al. (Computers Electronics Agriculture 2019)

Run: python generate_ieee_workflow.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.gridspec as gridspec
import numpy as np
import os

os.makedirs("journal_figures", exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# ─── Color Palette ──────────────────────────────────────────
COLORS = {
    'input':      '#2C3E50',
    'disease':    '#E74C3C',
    'weather':    '#E67E22',
    'crop':       '#27AE60',
    'market':     '#2980B9',
    'output':     '#8E44AD',
    'farmer':     '#1ABC9C',
    'broker':     '#3498DB',
    'arrow':      '#555555',
    'layer_bg':   '#F8F9FA',
    'white':      'white'
}

def rounded_box(ax, x, y, w, h, color, label,
                fontsize=8.5, text_color='white',
                bold=False, alpha=1.0, radius=0.15):
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0.05,rounding_size={radius}",
        facecolor=color, edgecolor='white',
        linewidth=1.5, zorder=3, alpha=alpha
    )
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, label,
            ha='center', va='center',
            fontsize=fontsize,
            color=text_color,
            fontweight=weight,
            zorder=4,
            multialignment='center')

def layer_bg(ax, x, y, w, h, label, color='#ECF0F1'):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.1,rounding_size=0.2",
        facecolor=color,
        edgecolor='#BDC3C7',
        linewidth=1.0, zorder=1, alpha=0.5
    )
    ax.add_patch(box)
    ax.text(x + 0.15, y + h - 0.18, label,
            fontsize=8, color='#7F8C8D',
            fontweight='bold', zorder=2,
            style='italic')

def arrow_down(ax, x, y1, y2, color='#555'):
    ax.annotate('',
        xy=(x, y2), xytext=(x, y1),
        arrowprops=dict(
            arrowstyle='->', color=color,
            lw=1.8,
            connectionstyle='arc3,rad=0.0'
        ), zorder=5)

def arrow_right(ax, x1, x2, y, color='#555'):
    ax.annotate('',
        xy=(x2, y), xytext=(x1, y),
        arrowprops=dict(
            arrowstyle='->', color=color,
            lw=1.5,
            connectionstyle='arc3,rad=0.0'
        ), zorder=5)

# ═══════════════════════════════════════════════════════════
# LAYER 1 — INPUT LAYER
# ═══════════════════════════════════════════════════════════
layer_bg(ax, 0.3, 8.2, 13.4, 1.5,
         'Layer 1: Data Input', '#EBF5FB')

# Input nodes
inputs = [
    (2.0,  9.05, '#2C3E50', 'Leaf Image\n(Upload)'),
    (4.5,  9.05, '#2C3E50', 'GPS Location\n(Farmer Input)'),
    (7.0,  9.05, '#2C3E50', 'Growing Season\n(Kharif/Rabi/Zaid)'),
    (9.5,  9.05, '#2C3E50', 'Real-Time Weather\n(OpenWeatherMap API)'),
    (12.0, 9.05, '#2C3E50', 'Crop Listings\n(Farmer Submit)')
]
for x, y, c, lbl in inputs:
    rounded_box(ax, x, y, 2.2, 0.75, c, lbl,
                fontsize=7.5, bold=False)

# ═══════════════════════════════════════════════════════════
# LAYER 2 — AI PROCESSING LAYER
# ═══════════════════════════════════════════════════════════
layer_bg(ax, 0.3, 5.2, 13.4, 2.7,
         'Layer 2: AI Processing Modules', '#EAF4FB')

# Arrows from input to processing
for x in [2.0, 4.5, 7.0, 9.5, 12.0]:
    arrow_down(ax, x, 8.67, 7.85, '#999')

# Module 1 — Disease Detection
rounded_box(ax, 2.0, 7.4, 2.2, 0.7,
            COLORS['disease'],
            'Disease Detection\nModule',
            fontsize=8, bold=True)
rounded_box(ax, 2.0, 6.6, 2.2, 0.65,
            '#FADBD8',
            'MobileNetV2 CNN\n(Transfer Learning)',
            fontsize=7.5, text_color='#922B21')
rounded_box(ax, 2.0, 5.85, 2.2, 0.6,
            '#F9EBEA',
            '97.34% Accuracy\n10 Disease Classes',
            fontsize=7.5, text_color='#922B21')

# Module 2 — Weather Advisory
rounded_box(ax, 4.8, 7.4, 2.2, 0.7,
            COLORS['weather'],
            'Weather Advisory\nModule',
            fontsize=8, bold=True)
rounded_box(ax, 4.8, 6.6, 2.2, 0.65,
            '#FDEBD0',
            'Decision Tree\nClassifier (ML)',
            fontsize=7.5, text_color='#784212')
rounded_box(ax, 4.8, 5.85, 2.2, 0.6,
            '#FEF9E7',
            '96.67% CV Accuracy\n7 Advisory Classes',
            fontsize=7.5, text_color='#784212')

# Module 3 — Crop Recommendation
rounded_box(ax, 7.5, 7.4, 2.2, 0.7,
            COLORS['crop'],
            'Crop Recommendation\nEngine',
            fontsize=8, bold=True)
rounded_box(ax, 7.5, 6.6, 2.2, 0.65,
            '#D5F5E3',
            'Random Forest\nClassifier (100 Trees)',
            fontsize=7.5, text_color='#1E8449')
rounded_box(ax, 7.5, 5.85, 2.2, 0.6,
            '#EAFAF1',
            '99.59% CV Accuracy\n22 Crop Classes',
            fontsize=7.5, text_color='#1E8449')

# Module 4 — Market Coordination
rounded_box(ax, 10.8, 7.4, 2.2, 0.7,
            COLORS['market'],
            'Market Coordination\nModule',
            fontsize=8, bold=True)
rounded_box(ax, 10.8, 6.6, 2.2, 0.65,
            '#D6EAF8',
            'Threshold-Based\nDemand Analysis',
            fontsize=7.5, text_color='#1A5276')
rounded_box(ax, 10.8, 5.85, 2.2, 0.6,
            '#EBF5FB',
            'Supply/Demand\nImbalance Detection',
            fontsize=7.5, text_color='#1A5276')

# ═══════════════════════════════════════════════════════════
# LAYER 3 — OUTPUT LAYER
# ═══════════════════════════════════════════════════════════
layer_bg(ax, 0.3, 3.4, 13.4, 1.6,
         'Layer 3: Decision Outputs', '#F4ECF7')

for x in [2.0, 4.8, 7.5, 10.8]:
    arrow_down(ax, x, 5.55, 4.85, '#999')

outputs = [
    (2.0,  4.45, COLORS['disease'],
     'Disease Diagnosis\n+ Treatment Advice'),
    (4.8,  4.45, COLORS['weather'],
     'Farming Advisory\n+ Action Plan'),
    (7.5,  4.45, COLORS['crop'],
     'Top-3 Crop\nRecommendations'),
    (10.8, 4.45, COLORS['market'],
     'Supply/Demand\nAlerts + Redistribution')
]
for x, y, c, lbl in outputs:
    rounded_box(ax, x, y, 2.2, 0.8, c, lbl,
                fontsize=7.5, bold=False)

# ═══════════════════════════════════════════════════════════
# LAYER 4 — USER DASHBOARD LAYER
# ═══════════════════════════════════════════════════════════
layer_bg(ax, 0.3, 0.8, 13.4, 2.3,
         'Layer 4: User Interface (Dual Dashboard)',
         '#EAFAF1')

# Arrows from outputs converging
arrow_down(ax, 2.0,  4.05, 2.85, '#999')
arrow_down(ax, 4.8,  4.05, 2.85, '#999')
arrow_down(ax, 7.5,  4.05, 2.85, '#999')
arrow_down(ax, 10.8, 4.05, 2.85, '#999')

# Farmer Dashboard
rounded_box(ax, 4.2, 2.35, 5.0, 1.3,
            COLORS['farmer'],
            'Farmer Dashboard\n\n'
            '  Disease Detection  |  Weather Advisory\n'
            '  Crop Recommendation  |  Crop Listing',
            fontsize=7.5, bold=False)

# Broker Dashboard
rounded_box(ax, 10.2, 2.35, 5.0, 1.3,
            COLORS['broker'],
            'Broker Dashboard\n\n'
            '  Demand Analysis  |  Regional Supply\n'
            '  All Listings  |  Notifications',
            fontsize=7.5, bold=False)

# Labels
ax.text(4.2, 1.35,
        'React.js Frontend  |  FastAPI Backend  |  MongoDB Atlas',
        ha='center', va='center',
        fontsize=8, color='#555',
        fontstyle='italic')
ax.text(10.2, 1.35,
        'JWT Authentication  |  Role-Based Access Control',
        ha='center', va='center',
        fontsize=8, color='#555',
        fontstyle='italic')

# ═══════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════
ax.set_title(
    'Fig. 2: ALIP System Framework — Four-Layer Architecture\n'
    'Showing Data Flow from Input Collection to User-Specific '
    'Dashboard Delivery',
    fontsize=11, fontweight='bold',
    color='#2C3E50', pad=12
)

# ═══════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════
legend_items = [
    (COLORS['disease'], 'Disease Detection'),
    (COLORS['weather'],  'Weather Advisory'),
    (COLORS['crop'],     'Crop Recommendation'),
    (COLORS['market'],   'Market Coordination'),
    (COLORS['farmer'],   'Farmer Dashboard'),
    (COLORS['broker'],   'Broker Dashboard'),
]
legend_patches = [
    mpatches.Patch(color=c, label=l)
    for c, l in legend_items
]
ax.legend(
    handles=legend_patches,
    loc='lower center',
    bbox_to_anchor=(0.5, -0.06),
    ncol=6,
    fontsize=8,
    framealpha=0.9
)

plt.tight_layout()
plt.savefig('journal_figures/fig2_ieee_workflow.png',
            dpi=300, bbox_inches='tight',
            facecolor='white')
plt.savefig('journal_figures/fig2_ieee_workflow.pdf',
            bbox_inches='tight',
            facecolor='white')
plt.close()

print("✅ IEEE-style workflow diagram saved!")
print("📁 journal_figures/fig2_ieee_workflow.png")
print("📁 journal_figures/fig2_ieee_workflow.pdf")