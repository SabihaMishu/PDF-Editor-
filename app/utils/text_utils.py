import re

def normalize_whitespace(text: str) -> str:
    """Replaces non-breaking spaces and collapses redundant spaces."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces or tabs into a single space (except newlines)
    text = re.sub(r"[ \t]+", " ", text)
    return text

def clean_paragraph_spacing(raw_text: str) -> str:
    """
    Cleans up PDF text extraction artifacts:
    - Merges artificial hard line breaks within paragraphs into flowing sentences.
    - Resolves hyphenated line splits (e.g., 'trans- \nlated' -> 'translated').
    - Preserves genuine paragraph breaks (double newlines).
    - Preserves bullet points and list markers.
    """
    if not raw_text or not raw_text.strip():
        return ""

    raw_text = normalize_whitespace(raw_text)

    # Split into candidate paragraphs on double or multiple newlines
    raw_blocks = re.split(r"\n\s*\n+", raw_text)
    cleaned_paragraphs: list[str] = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        raw_lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not raw_lines:
            continue

        merged_lines: list[str] = []
        for line in raw_lines:
            # Check if line is a bullet/numbered list item
            is_bullet = bool(re.match(r"^([•\-\*]|\d+[\.\)])\s+", line))

            if merged_lines and not is_bullet:
                prev_line = merged_lines[-1]
                # If previous line ends with a word hyphen (e.g. 'inter-')
                if prev_line.endswith("-") and not prev_line.endswith(" -"):
                    merged_lines[-1] = prev_line[:-1] + line
                else:
                    merged_lines[-1] = f"{prev_line} {line}"
            else:
                merged_lines.append(line)

        for merged in merged_lines:
            cleaned_text = re.sub(r"\s+", " ", merged).strip()
            if cleaned_text:
                cleaned_paragraphs.append(cleaned_text)

    return "\n\n".join(cleaned_paragraphs)
