"""
Language detection for the multilingual AI assistant. Detects the
language of the visitor's question so the AI can be instructed to
answer in that same language, regardless of which one it is.
"""


import re

HINDI_ROMAN_WORDS = [
    "hai", "ka", "ki","kon", "ke", "kya", "kaise", "bhai",
    "acha", "achha", "haan", "nahi", "mat", "mera",
    "meri", "tum", "aap", "hum", "chal", "kar", "bolo",
    "namaste", "namaskar", "please", "kr", "krna"
]

from langdetect import detect, DetectorFactory, LangDetectException

# langdetect's detection is non-deterministic by default (it samples);
# pinning the seed makes it return the same answer for the same input
# every time, which matters for anything user-facing.
DetectorFactory.seed = 0

# ISO 639-1 code -> human-readable name, covers the major world languages.
# Falls back to "English" for anything not in this table (still passes
# the code through to the model, which usually knows it anyway).
LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "zh-cn": "Chinese", "zh-tw": "Chinese", "ja": "Japanese", "ko": "Korean",
    "ar": "Arabic", "bn": "Bengali", "ur": "Urdu", "tr": "Turkish",
    "vi": "Vietnamese", "th": "Thai", "id": "Indonesian", "nl": "Dutch",
    "pl": "Polish", "uk": "Ukrainian", "el": "Greek", "he": "Hebrew",
    "sv": "Swedish", "fi": "Finnish", "no": "Norwegian", "da": "Danish",
    "cs": "Czech", "ro": "Romanian", "hu": "Hungarian", "ta": "Tamil",
    "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi",
    "ml": "Malayalam", "kn": "Kannada",
}


def detect_language(text: str) -> tuple[str, str]:
    cleaned = (text or "").strip()
    if len(cleaned) < 3:
        return "en", "English"

    try:
        code = detect(cleaned)
    except LangDetectException:
        return "en", "English"

    UNSUPPORTED_LANGS = {
        "lo",
        "sw",
        "so",
        "tl",
        "af",
    }

    if code in UNSUPPORTED_LANGS:
        return "en", "English"

    if code not in LANGUAGE_NAMES:
        return "en", "English"

    return code, LANGUAGE_NAMES[code]
