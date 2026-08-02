import sys
from pathlib import Path

# Ensures `import budget_mcp` works regardless of whether the editable
# install's .pth file is being honored (see the iCloud Drive gotcha in
# the README) — pytest loads this before collecting any test module.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
