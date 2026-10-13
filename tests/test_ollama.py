import os
import pytest
import ollama

def test_ollama_connectivity():
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11435")
    client = ollama.Client(host=host)
    models = client.list()
    assert "models" in models
    assert len(models["models"]) > 0
    model_names = [m["model"] for m in models["models"]]
    assert any("qwen2.5" in name for name in model_names)

def test_ollama_inference():
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11435")
    client = ollama.Client(host=host)
    res = client.generate(model="qwen2.5:7b", prompt="Ping test: reply with 'OK'", stream=False)
    assert res.get("response") is not None
    assert len(res["response"]) > 0
