"""Tests for splitting text into chunks."""

import pytest

from app.chunking import chunk_text


def test_empty_text_gives_no_chunks():
    assert chunk_text("   ") == []


def test_short_text_is_one_chunk():
    assert chunk_text("just a few words") == ["just a few words"]


def test_long_text_is_split_with_overlap():
    words = [f"w{i}" for i in range(25)]
    chunks = chunk_text(" ".join(words), chunk_words=10, overlap=2)

    assert chunks[0].split() == words[0:10]
    assert chunks[1].split() == words[8:18]  # starts 2 words before the previous chunk ended
    assert chunks[-1].split()[-1] == "w24"   # nothing at the end is lost


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_words=5, overlap=5)
