from pathlib import Path

import chromadb

CHROMA_PERSIST_DIR = "chroma_db"
COLLECTION_NAME = "python_code"
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50


def _split_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _get_collection(persist_dir: str = CHROMA_PERSIST_DIR) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(COLLECTION_NAME)


def index_path(path: str | Path, persist_dir: str = CHROMA_PERSIST_DIR) -> int:
    """Index .py files from a file or directory into ChromaDB.

    Uses upsert so re-indexing the same files is idempotent.
    Returns the total number of chunks stored.
    """
    path = Path(path)
    py_files = (
        [path]
        if path.is_file() and path.suffix == ".py"
        else list(path.rglob("*.py"))
    )

    if not py_files:
        return 0

    collection = _get_collection(persist_dir)
    total = 0

    for file in py_files:
        source = file.read_text(encoding="utf-8", errors="ignore")
        chunks = _split_text(source)
        if not chunks:
            continue
        ids = [f"{file}::{i}" for i in range(len(chunks))]
        metadatas: list[dict[str, str | int]] = [{"source": str(file), "chunk": i} for i in range(len(chunks))]
        collection.upsert(documents=chunks, ids=ids, metadatas=metadatas)  # type: ignore[arg-type]
        total += len(chunks)

    return total


def query_context(
    query: str,
    n_results: int = 5,
    persist_dir: str = CHROMA_PERSIST_DIR,
) -> list[str]:
    """Retrieve the most relevant code chunks for a given query."""
    collection = _get_collection(persist_dir)
    count = collection.count()
    if count == 0:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, count),
    )
    return results["documents"][0] if results["documents"] else []
