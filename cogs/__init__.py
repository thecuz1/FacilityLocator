from pathlib import Path

COG_DIR = Path("cogs")

EXTENSIONS = [
    ".".join(result.with_suffix("").parts) for result in COG_DIR.glob("[!_]*.py")
]
EXTENSIONS.append("jishaku")
