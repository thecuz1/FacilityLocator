from pathlib import Path

COG_DIR = Path("cogs")

EXTENSIONS = [
    f"{COG_DIR}.{result.stem}"
    for result in COG_DIR.iterdir()
    if result.is_file() and result.suffix == ".py" and not result.stem.startswith("_")
]
EXTENSIONS.append("jishaku")
