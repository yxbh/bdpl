"""Integration tests for disc6 fixture scan behavior (TDD expectations)."""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


def test_disc6_finds_two_episodes(disc6_analysis: DiscAnalysis) -> None:
    """Disc6 should infer exactly two episodes."""
    assert len(disc6_analysis.episodes) == 2


@pytest.mark.xfail(
    reason="Disc6 menu labels 4 scenes per episode, but scene extraction is not implemented yet.",
    strict=True,
)
def test_disc6_each_episode_has_four_scenes(disc6_analysis: DiscAnalysis) -> None:
    """Each inferred episode should expose four menu scenes."""
    for episode in disc6_analysis.episodes:
        # Placeholder TDD assertion: there is no scene model yet.
        # Keep this xfail until IG scene extraction is added.
        assert len(episode.segments) == 4, (
            f"Episode {episode.episode} expected 4 scenes, got {len(episode.segments)}"
        )


def test_disc6_has_three_special_features(disc6_analysis: DiscAnalysis) -> None:
    """Disc6 should expose exactly three special features."""
    assert len(disc6_analysis.special_features) == 3
