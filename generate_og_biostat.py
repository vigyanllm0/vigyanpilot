#!/usr/bin/env python3
"""Generate OG image for Biostatistics Calculator page."""
from PIL import Image, ImageDraw, ImageFont
import os

# Dimensions
WIDTH, HEIGHT = 1200, 630

# Colors (matching biostatistics calculator blue theme)
NAVY_DARK = (15, 23, 42)      # #0f172a
NAVY_MED = (30, 41, 59)       # #1e293b
BLUE = (37, 99, 235)          # #2563eb (accent)
BLUE_LIGHT = (96, 165, 250)   # #60a5fa
WHITE = (255, 255, 255)
GRAY = (148, 163, 184)        # #94a3b8
CYAN = (34, 211, 238)         # #22d3ee

# Create image
img = Image.new('RGB', (WIDTH, HEIGHT), NAVY_DARK)
draw = ImageDraw.Draw(img)

# Background gradient effect (simple horizontal bands)
for y in range(HEIGHT):
    ratio = y / HEIGHT
    if ratio < 0.5:
        r = int(NAVY_DARK[0] + (NAVY_MED[0] - NAVY_DARK[0]) * (ratio * 2))
        g = int(NAVY_DARK[1] + (NAVY_MED[1] - NAVY_DARK[1]) * (ratio * 2))
        b = int(NAVY_DARK[2] + (NAVY_MED[2] - NAVY_DARK[2]) * (ratio * 2))
    else:
        r = int(NAVY_MED[0] + (NAVY_DARK[0] - NAVY_MED[0]) * ((ratio - 0.5) * 2))
        g = int(NAVY_MED[1] + (NAVY_DARK[1] - NAVY_MED[1]) * ((ratio - 0.5) * 2))
        b = int(NAVY_MED[2] + (NAVY_DARK[2] - NAVY_MED[2]) * ((ratio - 0.5) * 2))
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

# Accent bar at top
draw.rectangle([(0, 0), (WIDTH, 6)], fill=BLUE)

# Try to load a font, fallback to default
try:
    font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
    font_med = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
except:
    font_large = ImageFont.load_default()
    font_med = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Title text
title = "Biostatistics Calculator"
bbox = draw.textbbox((0, 0), title, font=font_large)
text_width = bbox[2] - bbox[0]
x = (WIDTH - text_width) // 2
draw.text((x, 180), title, fill=WHITE, font=font_large)

# Subtitle
subtitle = "20+ Statistical Tests · Free · No Login Required"
bbox = draw.textbbox((0, 0), subtitle, font=font_med)
text_width = bbox[2] - bbox[0]
x = (WIDTH - text_width) // 2
draw.text((x, 280), subtitle, fill=GRAY, font=font_med)

# Stats boxes
stats = [
    ("t-test", "ANOVA"),
    ("Chi-square", "Regression"),
    ("Power Analysis", "Effect Size"),
]

box_width = 200
box_height = 60
start_x = (WIDTH - (3 * box_width + 2 * 20)) // 2
y = 380

for i, (stat1, stat2) in enumerate(stats):
    x = start_x + i * (box_width + 20)
    # Box background
    draw.rounded_rectangle([(x, y), (x + box_width, y + box_height)], radius=8, fill=NAVY_MED, outline=BLUE)
    # Text
    draw.text((x + 10, y + 10), stat1, fill=WHITE, font=font_small)
    draw.text((x + 10, y + 35), stat2, fill=CYAN, font=font_small)

# Brand name
brand = "VigyanLLM"
bbox = draw.textbbox((0, 0), brand, font=font_med)
text_width = bbox[2] - bbox[0]
x = (WIDTH - text_width) // 2
draw.text((x, 520), brand, fill=BLUE_LIGHT, font=font_med)

# Save
output_path = "/Users/macbookpro/Desktop/vigyanpilot/frontend/assets/og-biostatistics-calculator.png"
img.save(output_path, "PNG")
print(f"Generated: {output_path}")
