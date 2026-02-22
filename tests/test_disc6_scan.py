"""Integration tests for disc6 fixture scan behavior (TDD expectations)."""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


def test_disc6_finds_two_episodes(disc6_analysis: DiscAnalysis) -> None:
    """Disc6 should infer exactly two episodes."""
    assert len(disc6_analysis.episodes) == 2


def test_disc6_each_episode_has_four_scenes(disc6_analysis: DiscAnalysis) -> None:
    """Each inferred episode should expose four menu scenes."""
    for episode in disc6_analysis.episodes:
        assert len(episode.scenes) == 4, (
            f"Episode {episode.episode} expected 4 scenes, got {len(episode.scenes)}"
        )


def test_disc6_has_three_special_features(disc6_analysis: DiscAnalysis) -> None:
    """Disc6 should expose exactly three special features."""
    assert len(disc6_analysis.special_features) == 3
