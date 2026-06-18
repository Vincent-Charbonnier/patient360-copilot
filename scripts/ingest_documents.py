"""Ingest generated healthcare PDFs into ChromaDB."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader

from app.models.schemas import RetrievedDocument
from app.rag.vector_store import VectorStore, embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)


def read_pdf(path: Path) -> str:
    """Extract text from a PDF."""
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Chunk text by character count with overlap."""
    cleaned = " ".join(text.split())
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = start + chunk_size
        chunks.append(cleaned[start:end])
        start = max(end - overlap, end) if end >= len(cleaned) else end - overlap
    return [chunk for chunk in chunks if chunk.strip()]


def display_name(path: Path) -> str:
    """Convert a PDF path stem into a readable document name."""
    return path.stem.replace("_", " ").title()


def ingest_directory(directory: Path, collection_name: str, document_type: str, store: VectorStore) -> int:
    """Read PDFs in a directory and write chunks to a Chroma collection."""
    collection = store.reset_collection(collection_name)
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

    for pdf_path in sorted(directory.glob("*.pdf")):
        text = read_pdf(pdf_path)
        for index, chunk in enumerate(chunk_text(text)):
            ids.append(f"{document_type}-{pdf_path.stem}-{index}")
            documents.append(chunk)
            metadatas.append(
                {
                    "document_type": document_type,
                    "document_name": display_name(pdf_path),
                    "source_file": pdf_path.name,
                    "chunk_index": index,
                }
            )

    if documents:
        embeddings = embed_texts(documents, input_type="passage")
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    logger.info("Ingested %s chunks into %s", len(documents), collection_name)
    return len(documents)


def main() -> None:
    """Ingest care programs and guidelines."""
    store = VectorStore()
    program_chunks = ingest_directory(Path("data/care_programs"), "care_programs", "care_program", store)
    guideline_chunks = ingest_directory(Path("data/guidelines"), "guidelines", "guideline", store)
    print(f"Indexed {program_chunks} care program chunks")
    print(f"Indexed {guideline_chunks} guideline chunks")


if __name__ == "__main__":
    main()
