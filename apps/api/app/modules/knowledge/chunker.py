import re


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_text_into_chunks(
    text: str,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> list[str]:
    normalized_text = normalize_text(text)

    if not normalized_text:
        return []

    paragraphs = [paragraph.strip() for paragraph in normalized_text.split("\n\n") if paragraph.strip()]

    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            sentence_chunks = split_large_paragraph(paragraph, chunk_size)
            for sentence_chunk in sentence_chunks:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.append(sentence_chunk.strip())
            continue

        candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk.strip())

    if chunk_overlap <= 0 or len(chunks) <= 1:
        return chunks

    return add_overlap(chunks, chunk_overlap)


def split_large_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def add_overlap(chunks: list[str], chunk_overlap: int) -> list[str]:
    overlapped_chunks: list[str] = []

    for index, chunk in enumerate(chunks):
        if index == 0:
            overlapped_chunks.append(chunk)
            continue

        previous_chunk = chunks[index - 1]
        overlap_text = previous_chunk[-chunk_overlap:]
        overlapped_chunks.append(f"{overlap_text}\n\n{chunk}")

    return overlapped_chunks


def estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))