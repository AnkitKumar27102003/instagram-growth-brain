
import pytest
from pydantic import ValidationError

from src.models.script import ScriptSegment


def make_segment(voiceover: str) -> dict:
    return {
        "segment_number": 1,
        "voiceover": voiceover,
        "visual_direction": "Show relevant documentary-style visuals",
    }


def test_accepts_18_words():
    voiceover = " ".join(["India"] * 18)
    segment = ScriptSegment(**make_segment(voiceover))
    assert len(segment.voiceover.split()) == 18


def test_accepts_23_words():
    voiceover = " ".join(["India"] * 23)
    segment = ScriptSegment(**make_segment(voiceover))
    assert len(segment.voiceover.split()) == 23


@pytest.mark.parametrize("word_count", [17, 24])
def test_rejects_invalid_word_count(word_count):
    voiceover = " ".join(["India"] * word_count)

    with pytest.raises(ValidationError):
        ScriptSegment(**make_segment(voiceover))
