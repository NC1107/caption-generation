from app.config import Settings


def test_defaults_are_fully_local():
    s = Settings()
    assert s.transcribe_engine == "local"
    assert s.whisper_model == "base"
    assert s.llm_enabled is False  # no LLM configured by default


def test_llm_enabled_follows_base_url():
    assert Settings(llm_base_url="http://ollama:11434/v1").llm_enabled is True
    assert Settings(llm_base_url="   ").llm_enabled is False


def test_cors_origins_parsing():
    s = Settings(caption_cors_origins="http://a.test, http://b.test ,")
    assert s.cors_origins == ["http://a.test", "http://b.test"]


def test_derived_paths_under_data_dir(tmp_path):
    s = Settings(data_dir=tmp_path)
    assert s.uploads_dir == tmp_path / "uploads"
    assert s.outputs_dir == tmp_path / "outputs"
    assert s.db_path == tmp_path / "caption.sqlite"
