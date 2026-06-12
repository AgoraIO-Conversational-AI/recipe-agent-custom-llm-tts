"""The custom audio LLM endpoint is mounted into the server app and stays agora-free."""


def test_audio_health_is_mounted_under_slash_audio(client):
    response = client.get("/audio/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_audio_chat_completions_reachable_through_mount(client):
    response = client.post(
        "/audio/chat/completions",
        json={
            "model": "audio-mock",
            "messages": [{"role": "user", "content": "hi"}],
            "modalities": ["text", "audio"],
            "stream": True,
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    # Required transcript chunk — Agora cloud stores it as agent context.
    assert '"transcript"' in body
    # At least one base64 PCM audio data chunk.
    assert '"data"' in body
    # Stream terminates with the SSE sentinel.
    assert body.rstrip().endswith("data: [DONE]")


def test_audio_chat_completions_rejects_non_streaming(client):
    response = client.post(
        "/audio/chat/completions",
        json={
            "model": "audio-mock",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
    )
    assert response.status_code == 400


def test_llm_module_has_no_agora_dependency():
    """llm.py must stay provider-agnostic — no Agora SDK import.

    Checks actual import statements via AST (not prose): an Agora mention in a
    docstring or demo string is fine; importing an agora_* package is not.
    """
    import ast
    import inspect

    import llm

    tree = ast.parse(inspect.getsource(llm))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_roots.add(node.module.split(".")[0])

    agora_imports = sorted(r for r in imported_roots if r.startswith("agora"))
    assert not agora_imports, f"llm.py must not import an Agora SDK; found: {agora_imports}"
