# tests/test_repository.py
import os

import pytest

import mcp_memory.repository as repo
from mcp_memory.repository import fetch_memory, init_db, save_memory, search_memories


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    repo.DB_PATH = db_file
    init_db()
    yield
    os.remove(db_file)


def test_save_and_fetch():
    memory = save_memory("Java GC", "ZGC has sub-millisecond pauses", ["java", "gc"])

    assert memory.memory_id is not None
    assert memory.title == "Java GC"
    assert memory.tags == ["java", "gc"]

    fetched = fetch_memory(memory.memory_id)
    assert fetched is not None
    assert fetched.title == "Java GC"
    assert fetched.content == "ZGC has sub-millisecond pauses"


def test_fetch_nonexistent():
    result = fetch_memory("does-not-exist")
    assert result is None


def test_search_by_title():
    save_memory("Kafka tips", "Use read_committed isolation", ["kafka"])
    save_memory("Python basics", "Indentation matters", ["python"])

    results = search_memories("Kafka")
    assert len(results) == 1
    assert results[0].title == "Kafka tips"


def test_search_by_tag():
    save_memory("Spring Boot", "Auto-config is magic", ["java", "spring"])

    results = search_memories("spring")
    assert len(results) == 1


def test_search_no_results():
    results = search_memories("nonexistent")
    assert len(results) == 0
