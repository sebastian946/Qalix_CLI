import pytest

from chains.RAG import index_path, query_context


@pytest.fixture
def chroma_dir(tmp_path) -> str:
    return str(tmp_path / "chroma")


def test_index_processes_python_file(tmp_path, chroma_dir) -> None:
    py_file = tmp_path / "sample.py"
    py_file.write_text(
        "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
    )

    count = index_path(py_file, persist_dir=chroma_dir)

    assert count > 0


def test_query_returns_relevant_chunks(tmp_path, chroma_dir) -> None:
    py_file = tmp_path / "math.py"
    py_file.write_text("def add(a, b):\n    return a + b\n")

    index_path(py_file, persist_dir=chroma_dir)
    chunks = query_context("add function", persist_dir=chroma_dir)

    assert len(chunks) > 0
    assert any("add" in chunk for chunk in chunks)


def test_index_empty_directory_without_error(tmp_path, chroma_dir) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    count = index_path(empty_dir, persist_dir=chroma_dir)

    assert count == 0
