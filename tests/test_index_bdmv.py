"""Tests for index.bdmv parser."""

import pytest

from bdpl.bdmv.index_bdmv import parse_index_bdmv


@pytest.fixture
def index_file(bdmv_path):
    f = bdmv_path / "index.bdmv"
    if not f.is_file():
        pytest.skip("index.bdmv not found")
    return f


def test_parse_index_returns_titles(index_file):
    idx = parse_index_bdmv(index_file)
    assert len(idx.titles) > 0


def test_first_playback_and_menu(index_file):
    idx = parse_index_bdmv(index_file)
    assert idx.first_playback_obj >= 0
    assert idx.top_menu_obj >= 0


def test_title_numbers_are_sequential(index_file):
    idx = parse_index_bdmv(index_file)
    nums = [t.title_num for t in idx.titles]
    assert nums == list(range(len(nums)))


def test_movie_object_ids_are_nonnegative(index_file):
    idx = parse_index_bdmv(index_file)
    for t in idx.titles:
        assert t.movie_object_id >= 0
