"""Integration tests for disc6 fixture scan behavior (TDD expectations).

Disc6 is a Gundam UC bonus disc with 2 unique episodes:
- Clip 00006 (~58min) referenced by 4 playlist variants (00003, 00004, 00006, 00007)
  with different audio PIDs and subtitle presence/absence.
- Clip 00007 (~59min) referenced by 1 playlist (00005).

The analysis correctly identifies 2 episodes (00003 + 00005 as representatives)
and 3 special features (the remaining stream variants).
"""

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


def test_disc6_last_scene_is_substantial(disc6_analysis: DiscAnalysis) -> None:
    """Final scene should be substantial (credits), not a near-zero tail."""
    for episode in disc6_analysis.episodes:
        assert episode.scenes, f"Episode {episode.episode} has no scenes"
        assert episode.scenes[-1].duration_ms >= 120_000, (
            f"Episode {episode.episode} final scene too short: "
            f"{episode.scenes[-1].duration_ms / 1000.0:.3f}s"
        )


def test_disc6_has_three_special_features(disc6_analysis: DiscAnalysis) -> None:
    """Disc6 should expose exactly three special features (stream variants)."""
    assert len(disc6_analysis.special_features) == 3


def test_disc6_disc_title(disc6_analysis: DiscAnalysis) -> None:
    """Disc title should be extracted from META/DL/bdmt_eng.xml."""
    assert disc6_analysis.disc_title == "TEST DISC 6"
