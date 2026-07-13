"""
Tests for the multilingual AI assistant (services/language.py +
services/ai_provider.py). Network calls to Gemini/OpenAI are mocked —
these tests check language detection, history handling, and that the
right provider function gets called, not real model output.
"""

from services.language import detect_language
import services.ai_provider as ai_provider


# ---------------------------------------------------
# Language detection
# ---------------------------------------------------

def test_detect_language_english():
    code, name = detect_language("What programming languages do you know?")
    assert code == "en"
    assert name == "English"


def test_detect_language_hindi():
    code, name = detect_language("नमस्ते, आप कैसे हैं?")
    assert code == "hi"
    assert name == "Hindi"


def test_detect_language_short_text_falls_back_to_english():
    code, name = detect_language("ok")
    assert code == "en"
    assert name == "English"


def test_detect_language_empty_text_falls_back_to_english():
    code, name = detect_language("")
    assert code == "en"
    assert name == "English"


# ---------------------------------------------------
# ask_ai() provider routing + history
# ---------------------------------------------------

def test_ask_ai_routes_to_gemini(monkeypatch):
    monkeypatch.setattr(ai_provider.Config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_provider, "_ask_gemini", lambda q, sp, turns: "gemini answer")

    result = ai_provider.ask_ai("Explain Python decorators")
    assert result["answer"] == "gemini answer"
    assert result["language"] == "en"


def test_ask_ai_routes_to_openai(monkeypatch):
    monkeypatch.setattr(ai_provider.Config, "AI_PROVIDER", "openai")
    monkeypatch.setattr(ai_provider, "_ask_openai", lambda q, sp, turns: "openai answer")

    result = ai_provider.ask_ai("Explain SQL injection")
    assert result["answer"] == "openai answer"


def test_ask_ai_unknown_provider_raises(monkeypatch):
    monkeypatch.setattr(ai_provider.Config, "AI_PROVIDER", "not-a-real-provider")
    try:
        ai_provider.ask_ai("hello there")
        assert False, "expected AIProviderError"
    except ai_provider.AIProviderError:
        pass


def test_ask_ai_passes_history_to_provider(monkeypatch):
    captured = {}

    def fake_gemini(question, system_prompt, turns):
        captured["turns"] = turns
        return "ok"

    monkeypatch.setattr(ai_provider.Config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_provider, "_ask_gemini", fake_gemini)

    history = [{"question": "hi", "answer": "hello!"}]
    ai_provider.ask_ai("follow up question", history=history)

    assert captured["turns"] == history


def test_ask_ai_history_is_truncated_to_max_turns(monkeypatch):
    captured = {}

    def fake_gemini(question, system_prompt, turns):
        captured["turns"] = turns
        return "ok"

    monkeypatch.setattr(ai_provider.Config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_provider, "_ask_gemini", fake_gemini)

    long_history = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    ai_provider.ask_ai("new question", history=long_history)

    assert len(captured["turns"]) == ai_provider.MAX_HISTORY_TURNS
    assert captured["turns"][-1]["question"] == "q19"
