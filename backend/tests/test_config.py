from app.config import Settings


def test_defaults_are_fully_local():
    s = Settings()
    assert s.transcribe_engine == "local"
    assert s.whisper_model == "base"
    assert s.llm_enabled is False  # no LLM configured by default


def test_llm_enabled_follows_providers():
    assert Settings(local_llm_url="http://ollama:11434/v1").llm_enabled is True
    assert Settings(openrouter_api_key="sk-or-x").llm_enabled is True
    assert Settings().llm_enabled is False


def test_resolve_llm_routing():
    s = Settings(local_llm_url="http://lan:11434/v1", openrouter_api_key="sk-or-x")
    assert s.resolve_llm("local::qwen3:8b") == ("http://lan:11434/v1", "ollama", "qwen3:8b")
    base, key, model = s.resolve_llm("cloud::openai/gpt-4o-mini")
    assert base == "https://openrouter.ai/api/v1"
    assert key == "sk-or-x"
    assert model == "openai/gpt-4o-mini"
    assert s.resolve_llm("qwen3:8b")[2] == "qwen3:8b"  # plain id → default (local) provider


def test_cors_origins_parsing():
    s = Settings(caption_cors_origins="http://a.test, http://b.test ,")
    assert s.cors_origins == ["http://a.test", "http://b.test"]


def test_derived_paths_under_data_dir(tmp_path):
    s = Settings(data_dir=tmp_path)
    assert s.uploads_dir == tmp_path / "uploads"
    assert s.outputs_dir == tmp_path / "outputs"
    assert s.db_path == tmp_path / "caption.sqlite"
