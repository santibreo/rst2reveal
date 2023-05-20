import os
from pathlib import Path

__version__ = "1.0"

# Package main locations
RST2REVEAL_PATH = Path(__file__).absolute().parent

# Reveal related locations
REVEAL_PATH = RST2REVEAL_PATH / "reveal"
REVEAL_THEME_PATH = REVEAL_PATH / "dist" / "theme"
REVEAL_THEMES = set(map(lambda x: x.stem, REVEAL_THEME_PATH.glob("*.css")))
REVEAL_TRANSITIONS = [
    "default",
    "cube",
    "page",
    "concave",
    "zoom",
    "linear",
    "fade",
    "none",
]

# Custom static files locations
STATIC_PATH = RST2REVEAL_PATH / "static"
STATIC_CSS_PATH = STATIC_PATH / "css"
STATIC_FONT_PATH = STATIC_PATH / "font"
STATIC_TMP_PATH = STATIC_PATH / "tmp"
STATIC_JS_PATH = STATIC_PATH / "js"
PYGMENTS_CSS_PATH = STATIC_CSS_PATH / "pygments"


# Check for pygments
try:
    from pygments.styles import STYLE_MAP

    PYGMENTS_STYLES = set(STYLE_MAP.keys())
except ImportError:
    PYGMENTS_STYLES = set()
    print("Pygments is not installed, code blocks won't be highlighted")

# Check for matplotlib
try:
    from matplotlib import font_manager, rcParams
    import matplotlib.pylab as plt

    HAS_MATPLOTLIB = True
    font_files = font_manager.findSystemFonts(
        fontpaths=[os.path.realpath(STATIC_FONT_PATH)]
    )
    for font_file in font_files:
        font_manager.fontManager.addfont(font_file)

except ImportError:
    HAS_MATPLOTLIB = False
    print(
        "Warning: matplotlib is not installed on your system. Plots will not be generated."
    )
