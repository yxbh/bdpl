"""Tests for MovieObject.bdmv parser."""

import pytest

from bdpl.bdmv.movieobject_bdmv import parse_movieobject_bdmv


@pytest.fixture
def mobj_file(bdmv_path):
    f = bdmv_path / "MovieObject.bdmv"
    if not f.is_file():
        pytest.skip("MovieObject.bdmv not found")
    return f


def test_parse_movieobject_returns_objects(mobj_file):
    mo = parse_movieobject_bdmv(mobj_file)
    assert len(mo.objects) > 0


def test_object_ids_are_sequential(mobj_file):
    mo = parse_movieobject_bdmv(mobj_file)
    ids = [o.object_id for o in mo.objects]
    assert ids == list(range(len(ids)))


def test_first_object_references_playlist(mobj_file):
    mo = parse_movieobject_bdmv(mobj_file)
    # Object 0 (first playback) should reference at least one playlist
    obj0 = mo.objects[0]
    assert len(obj0.referenced_playlists) > 0


def test_playlist_references_are_valid(mobj_file):
    mo = parse_movieobject_bdmv(mobj_file)
    for obj in mo.objects:
        for pl in obj.referenced_playlists:
            assert 0 <= pl < 10000, f"Unlikely playlist number {pl}"
