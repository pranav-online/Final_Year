"""
ALIP - System Workflow Diagram Generator
Run: python generate_workflow.py
Output: journal_figures/fig5_system_workflow.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import os

os.makedirs("journal_figures", exist_ok=True)

fig, ax = plt.subplots(1, 1, figsize=(12, 16))
ax.set_xlim(0, 10)
ax.set_ylim(0, 20)
ax.axis('off')

# ─── Color Palette ──────────────────────────────────────────
C = {
    'start':    '#2C3E50',
    'auth':     '#E67E22',
    'decision': '#8E44AD',
    'farmer':   '#1D9E75',
    'broker':   '#3266AD',
    'module':   '#ECF0F1',
    'output':   '#27AE60',
    'arrow':    '#555555',
    'text_w':   'white',
    'text_d':   '#2C3E50',
}

def draw_rounded_box(ax, x, y, w, h, color, text,
                      fontsize=9, text_color='white',
                      bold=False, radius=0.25):
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0.05,rounding_size={radius}",
        facecolor=color, edgecolor='white',
        linewidth=1.2, zorder=3
    )
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, text,
            ha='center', va='center',
            fontsize=fontsize, color=text_color,
            fontweight=weight, zorder=4,
            wrap=True)

def draw_diamond(ax, x, y, w, h, color, text, fontsize=9):
    diamond = plt.Polygon(
        [[x, y+h/2], [x+w/2, y],
         [x, y-h/2], [x-w/2, y]],
        facecolor=color, edgecolor='white',
        linewidth=1.2, zorder=3
    )
    ax.add_patch(diamond)
    ax.text(x, y, text,
            ha='center', va='center',
            fontsize=fontsize, color='white',
            fontweight='bold', zorder=4)

def arrow(ax, x1, y1, x2, y2, label='', color='#555'):
    ax.annotate('',
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle='->', color=color,
            lw=1.5, connectionstyle='arc3,rad=0.0'
        ), zorder=2
    )
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.15, my, label,
                fontsize=8, color=color,
                fontweight='bold', zorder=5)

# ═══════════════════════════════════════════════════════════
# STEP 1 — START
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 5, 19.2, 3.5, 0.7,
                 C['start'], 'START: User Opens ALIP',
                 fontsize=10, bold=True, radius=0.35)

arrow(ax, 5, 18.85, 5, 18.35)

# ═══════════════════════════════════════════════════════════
# STEP 2 — LOGIN
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 5, 18.0, 3.5, 0.65,
                 C['auth'], 'User Login\n(Email + Password)',
                 fontsize=9, bold=True)

arrow(ax, 5, 17.67, 5, 17.17)

# ═══════════════════════════════════════════════════════════
# STEP 3 — JWT AUTH
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 5, 16.85, 3.8, 0.6,
                 C['auth'],
                 'JWT Authentication + bcrypt Verification',
                 fontsize=8.5, bold=False)

arrow(ax, 5, 16.55, 5, 16.05)

# ═══════════════════════════════════════════════════════════
# STEP 4 — ROLE CHECK DIAMOND
# ═══════════════════════════════════════════════════════════
draw_diamond(ax, 5, 15.6, 3.2, 0.85,
             C['decision'], 'Role Check?',
             fontsize=10)

# Branch arrows
arrow(ax, 3.4, 15.6, 2.2, 15.6, 'Farmer', C['farmer'])
arrow(ax, 6.6, 15.6, 7.8, 15.6, 'Broker', C['broker'])

# ═══════════════════════════════════════════════════════════
# FARMER BRANCH (Left)
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 1.8, 15.0, 2.8, 0.6,
                 C['farmer'], 'Farmer Dashboard',
                 fontsize=9, bold=True)

arrow(ax, 1.8, 14.7, 1.8, 14.2)

# Farmer Module 1
draw_rounded_box(ax, 1.8, 13.9, 2.6, 0.55,
                 C['farmer'],
                 '1. Upload Leaf Image',
                 fontsize=8.5)
arrow(ax, 1.8, 13.62, 1.8, 13.15)

draw_rounded_box(ax, 1.8, 12.85, 2.6, 0.55,
                 C['module'],
                 'MobileNetV2 CNN\nDisease Classification',
                 fontsize=8, text_color=C['text_d'])
arrow(ax, 1.8, 12.57, 1.8, 12.1)

draw_rounded_box(ax, 1.8, 11.8, 2.6, 0.55,
                 '#E8F8F5',
                 'Disease + Confidence\n+ Treatment Advice',
                 fontsize=8, text_color=C['text_d'])

arrow(ax, 1.8, 11.52, 1.8, 11.05)

# Farmer Module 2
draw_rounded_box(ax, 1.8, 10.75, 2.6, 0.55,
                 C['farmer'],
                 '2. Enter Location',
                 fontsize=8.5)
arrow(ax, 1.8, 10.47, 1.8, 10.0)

draw_rounded_box(ax, 1.8, 9.7, 2.6, 0.55,
                 C['module'],
                 'OpenWeatherMap API\n+ Rule Engine',
                 fontsize=8, text_color=C['text_d'])
arrow(ax, 1.8, 9.42, 1.8, 8.95)

draw_rounded_box(ax, 1.8, 8.65, 2.6, 0.55,
                 '#EBF5FB',
                 'Weather + Farming\nAdvisory',
                 fontsize=8, text_color=C['text_d'])

arrow(ax, 1.8, 8.37, 1.8, 7.9)

# Farmer Module 3
draw_rounded_box(ax, 1.8, 7.6, 2.6, 0.55,
                 C['farmer'],
                 '3. Select Location + Season',
                 fontsize=8)
arrow(ax, 1.8, 7.32, 1.8, 6.85)

draw_rounded_box(ax, 1.8, 6.55, 2.6, 0.55,
                 C['module'],
                 'Random Forest\n+ Soil Profile DB',
                 fontsize=8, text_color=C['text_d'])
arrow(ax, 1.8, 6.27, 1.8, 5.8)

draw_rounded_box(ax, 1.8, 5.5, 2.6, 0.55,
                 '#EAFAF1',
                 'Top-3 Crop\nRecommendations',
                 fontsize=8, text_color=C['text_d'])

# ═══════════════════════════════════════════════════════════
# BROKER BRANCH (Right)
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 8.2, 15.0, 2.8, 0.6,
                 C['broker'], 'Broker Dashboard',
                 fontsize=9, bold=True)

arrow(ax, 8.2, 14.7, 8.2, 14.2)

# Broker Module 1
draw_rounded_box(ax, 8.2, 13.9, 2.6, 0.55,
                 C['broker'],
                 '1. Select Region',
                 fontsize=8.5)
arrow(ax, 8.2, 13.62, 8.2, 13.15)

draw_rounded_box(ax, 8.2, 12.85, 2.6, 0.55,
                 C['module'],
                 'Threshold-Based\nDemand Analysis',
                 fontsize=8, text_color=C['text_d'])
arrow(ax, 8.2, 12.57, 8.2, 12.1)

draw_rounded_box(ax, 8.2, 11.8, 2.6, 0.55,
                 '#EBF5FB',
                 'Oversupply / Undersupply\nAlerts Generated',
                 fontsize=8, text_color=C['text_d'])

arrow(ax, 8.2, 11.52, 8.2, 11.05)

# Broker Module 2
draw_rounded_box(ax, 8.2, 10.75, 2.6, 0.55,
                 C['broker'],
                 '2. View Regional Supply',
                 fontsize=8.5)
arrow(ax, 8.2, 10.47, 8.2, 10.0)

draw_rounded_box(ax, 8.2, 9.7, 2.6, 0.55,
                 C['module'],
                 'MongoDB Aggregation\n+ Supply Charts',
                 fontsize=8, text_color=C['text_d'])
arrow(ax, 8.2, 9.42, 8.2, 8.95)

draw_rounded_box(ax, 8.2, 8.65, 2.6, 0.55,
                 '#EBF5FB',
                 'Regional Crop Supply\nVisualization',
                 fontsize=8, text_color=C['text_d'])

arrow(ax, 8.2, 8.37, 8.2, 7.9)

# Broker Module 3
draw_rounded_box(ax, 8.2, 7.6, 2.6, 0.55,
                 C['broker'],
                 '3. Check Notifications',
                 fontsize=8.5)
arrow(ax, 8.2, 7.32, 8.2, 6.85)

draw_rounded_box(ax, 8.2, 6.55, 2.6, 0.55,
                 C['module'],
                 'Real-Time Alert\nEngine',
                 fontsize=8, text_color=C['text_d'])
arrow(ax, 8.2, 6.27, 8.2, 5.8)

draw_rounded_box(ax, 8.2, 5.5, 2.6, 0.55,
                 '#EBF5FB',
                 'Market Redistribution\nRecommendations',
                 fontsize=8, text_color=C['text_d'])

# ═══════════════════════════════════════════════════════════
# CONVERGE TO OUTPUT
# ═══════════════════════════════════════════════════════════
# Lines from both branches to center output
ax.annotate('',
    xy=(5, 4.55), xytext=(1.8, 5.22),
    arrowprops=dict(
        arrowstyle='->', color=C['output'],
        lw=1.5,
        connectionstyle='arc3,rad=-0.2'
    ), zorder=2
)
ax.annotate('',
    xy=(5, 4.55), xytext=(8.2, 5.22),
    arrowprops=dict(
        arrowstyle='->', color=C['output'],
        lw=1.5,
        connectionstyle='arc3,rad=0.2'
    ), zorder=2
)

# ═══════════════════════════════════════════════════════════
# OUTPUT BOX
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 5, 4.2, 4.5, 0.65,
                 C['output'],
                 'Actionable Insights Delivered\nto Farmer / Broker',
                 fontsize=9.5, bold=True, radius=0.3)

arrow(ax, 5, 3.87, 5, 3.37)

# ═══════════════════════════════════════════════════════════
# MONGODB FEEDBACK
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 5, 3.1, 3.8, 0.55,
                 '#7F8C8D',
                 'Results Stored in MongoDB Atlas',
                 fontsize=8.5)

arrow(ax, 5, 2.82, 5, 2.35)

# ═══════════════════════════════════════════════════════════
# END
# ═══════════════════════════════════════════════════════════
draw_rounded_box(ax, 5, 2.05, 3.5, 0.65,
                 C['start'], 'END',
                 fontsize=11, bold=True, radius=0.35)

# ═══════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════
legend_items = [
    (C['auth'],    'Authentication Step'),
    (C['decision'],'Decision / Role Check'),
    (C['farmer'],  'Farmer Module'),
    (C['broker'],  'Broker Module'),
    (C['module'],  'AI Processing'),
    (C['output'],  'Output / Result'),
]
for i, (color, label) in enumerate(legend_items):
    bx = 0.3
    by = 2.5 - i * 0.38
    rect = FancyBboxPatch(
        (bx, by - 0.13), 0.35, 0.28,
        boxstyle="round,pad=0.02",
        facecolor=color,
        edgecolor='#999', linewidth=0.8
    )
    ax.add_patch(rect)
    tc = 'white' if color != C['module'] else C['text_d']
    ax.text(bx + 0.75, by + 0.01, label,
            fontsize=7.5, va='center',
            color='#333333')

ax.text(0.3, 2.65, 'Legend:',
        fontsize=8.5, fontweight='bold',
        color='#333')

# ═══════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════
ax.set_title(
    'Fig. 5: End-to-End Operational Workflow of the\n'
    'ALIP System — From Authentication to Insight Delivery',
    fontsize=11, fontweight='bold', pad=10,
    color='#2C3E50'
)

plt.tight_layout()
plt.savefig('journal_figures/fig5_system_workflow.png',
            dpi=300, bbox_inches='tight',
            facecolor='white')
plt.savefig('journal_figures/fig5_system_workflow.pdf',
            bbox_inches='tight',
            facecolor='white')
plt.close()

print("✅ Workflow diagram saved!")
print("📁 journal_figures/fig5_system_workflow.png")
print("📁 journal_figures/fig5_system_workflow.pdf")