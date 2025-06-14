from fastapi import UploadFile
import os
import pytest
from utils.utils import get_wav_bytes_from_m4a
from utils.utils import (
    extract_file_ext,
    file_ext_is_valid,
    get_audio_duration,
    is_audio_duration_longer_than_allowed,
    is_consent_given,
)


def get_bytes(path: str):
    base_dir = os.path.dirname(__file__)
    full_path = os.path.join(base_dir, "assets", path)
    with open(full_path, "rb") as f:
            return f.read()

def test_extract_file_ext():

    class DummyFile(UploadFile):
        def __init__(self):
            pass
        filename = "example.m4a"

    ext = extract_file_ext(DummyFile())
    assert ext == ".m4a"


def test_file_ext_is_valid():
    assert file_ext_is_valid(".m4a", [".m4a"]) is True
    assert file_ext_is_valid(".mp3", [".m4a"]) is False


def test_get_audio_duration():
    duration = get_audio_duration(get_bytes("test_5s_audio.m4a"))
    assert 4.9 < duration < 5.1


def test_is_audio_duration_longer_than_allowed():
    too_long, dur1 = is_audio_duration_longer_than_allowed(get_bytes("test_5s_audio.m4a"))
    assert too_long is False
    assert dur1 < 30

    too_long, dur2 = is_audio_duration_longer_than_allowed(get_bytes("test_35s_audio.m4a"))
    assert too_long is True
    assert dur2 > 30


@pytest.mark.parametrize("consent_str, expected", [
    ("true", True),
    ("True", True),
    (" TRUE ", True),
    ("false", False),
    ("no", False),
    ("", False),
])
def test_is_consent_given(consent_str, expected):
    assert is_consent_given(consent_str) == expected

def test_m4a_2_wav_does_not_crash():
    get_wav_bytes_from_m4a(get_bytes("test_5s_audio.m4a"))

