"""Package the Chrome Extension (extension/) into dist/pii-shield-extension.zip."""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXT_DIR = ROOT / "extension"
DIST_ZIP = ROOT / "dist" / "pii-shield-extension.zip"
EXCLUDED_PARTS = {"tests", "__pycache__", ".DS_Store"}


def build_extension_zip(out_path: Path = DIST_ZIP) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(EXT_DIR.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(EXT_DIR)
            if any(part in EXCLUDED_PARTS for part in rel.parts):
                continue
            archive.write(file_path, arcname=f"pii-shield-extension/{rel.as_posix()}")
    return out_path


if __name__ == "__main__":
    created = build_extension_zip()
    print(f"Created {created} ({created.stat().st_size:,} bytes)")
