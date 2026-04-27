from pathlib import Path


async def extract_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Uploaded file not found: {file_path}")

    raw = path.read_bytes()
    if not raw:
        raise ValueError("Uploaded invoice is empty")

    # Placeholder OCR: text uploads are decoded directly; binary PDF/image files
    # produce a stable marker so the pipeline remains async and replaceable.
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = ""

    if decoded.strip():
        return decoded.strip()

    suffix = path.suffix.lower().lstrip(".") or "document"
    return f"OCR placeholder extracted from {path.name}. Source type: {suffix}."

