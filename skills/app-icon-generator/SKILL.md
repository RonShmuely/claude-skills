---
name: app-icon-generator
description: Generate app/folder icons from a design philosophy. Use when user asks for an icon, app icon, folder icon, or logo for a project. Takes the app's color palette and concept to produce a 512px + 256px PNG icon.
---

# App Icon Generator

Generate polished app icons using Python + Pillow. Produces 512px and 256px PNGs.

## Approach: Signal Architecture

The icon generation follows a "Signal Architecture" philosophy — dark fields with luminous accent traces, concentric propagation arcs, layered waveform lines, and subtle monospace typography. Adapt the visual language to match whatever app is being designed for.

## Steps

1. **Extract the app's visual DNA**: Read any existing CSS/config for colors, fonts, accent colors. If none exist, ask the user.

2. **Generate using this Python pattern**:

```python
from PIL import Image, ImageDraw, ImageFont
import math, os

SIZE = 512
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Rounded rectangle background
draw.rounded_rectangle([(0, 0), (SIZE-1, SIZE-1)], radius=90, fill=BG_COLOR, outline=BORDER_COLOR, width=2)

# Layer compositing for alpha transparency:
# Create temp RGBA images for each layer, then Image.alpha_composite()

# Elements to include (adapt to the app's concept):
# - Concentric arcs (signal/propagation feel)
# - Waveform/data lines with sine-wave math
# - Glowing center point (radial gradient via nested ellipses)
# - Subtle grid lines
# - Monospace monogram (2 letters, bottom-right, dim)

# Save both sizes
img.save("icon.png", "PNG")
img.resize((256, 256), Image.LANCZOS).save("icon-256.png", "PNG")
```

3. **Fonts available** at:
```
C:/Users/ronsh/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/5e36e0ae-4d61-482b-acba-30149c1b4101/a877e53e-29ce-4b21-983b-eace10cfa817/skills/canvas-design/canvas-fonts/
```
Key fonts: `IBMPlexMono-Regular.ttf`, `GeistMono-Regular.ttf`, `Jura-Light.ttf`, `Tektur-Regular.ttf`

4. **Open the result** for the user using the CLAUDE.md file-open PowerShell command.

5. **Keep the generator script** in the project as `generate-icon.py` for iteration, or offer to save it. Don't delete it.

## Color extraction pattern

For VoiceLayer-style apps (dark industrial):
- BG: `(8, 8, 8)` / `#080808`
- Accent: `(61, 217, 160)` / `#3dd9a0`
- Accent dim: `(26, 92, 74)` / `#1a5c4a`
- Border: `(30, 30, 30)` / `#1e1e1e`

For other apps, read `index.css` or theme files to extract the palette.

## Requirements
- Python 3 + Pillow (`pip install Pillow`)
- Both already confirmed available on Ron's machine
