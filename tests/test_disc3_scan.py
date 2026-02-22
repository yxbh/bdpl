"""Integration tests for the disc3 fixture scan results."""

from bdpl.model import DiscAnalysis


def test_disc3_finds_four_episodes(disc3_analysis: DiscAnalysis) -> None:
    """Scan disc3 and verify four episodes are inferred."""
    assert len(disc3_analysis.episodes) == 4


def test_disc3_episode_numbers_are_ordered(disc3_analysis: DiscAnalysis) -> None:
    """Verify inferred episode sequence is 1..4 for disc3."""
    assert [episode.episode for episode in disc3_analysis.episodes] == [1, 2, 3, 4]
