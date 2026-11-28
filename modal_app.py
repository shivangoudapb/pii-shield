"""Modal wrapper for the existing FastAPI service.

The local module intentionally imports only Modal. Project dependencies and the
FastAPI application are imported inside the Modal container function.
"""

import modal

APP_ROOT = "/root/pii_shield"
CPU_TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
app = modal.App("pii-shield")


def _download_model_and_tokenizer() -> None:
    """Cache GLiNER and its tokenizer in the image while it is being built."""
    import json
    from pathlib import Path

    from huggingface_hub import snapshot_download

    model_dir = Path(snapshot_download("urchade/gliner_multi_pii-v1"))
    tokenizer_dir = snapshot_download(
        "microsoft/mdeberta-v3-base",
        allow_patterns=(
            "config.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "spm.model",
            "sentencepiece.bpe.model",
            "tokenizer.json",
            "added_tokens.json",
        ),
    )
    # Point Transformers at the build-cached local files so offline startup
    # never queries the Hugging Face API for tokenizer metadata.
    gliner_config_path = model_dir / "gliner_config.json"
    gliner_config = json.loads(gliner_config_path.read_text(encoding="utf-8"))
    gliner_config["model_name"] = tokenizer_dir
    gliner_config_path.write_text(
        json.dumps(gliner_config, indent=2) + "\n", encoding="utf-8"
    )


image = (
    modal.Image.debian_slim(python_version="3.11")
    # Install CPU torch first. The pinned requirements then reuse this version.
    .pip_install("torch==2.11.0", index_url=CPU_TORCH_INDEX)
    .pip_install_from_requirements("requirements.txt")
    .run_function(_download_model_and_tokenizer)
    .add_local_dir("engine", remote_path=f"{APP_ROOT}/engine", copy=True)
    .add_local_dir("api", remote_path=f"{APP_ROOT}/api", copy=True)
    .add_local_dir("web", remote_path=f"{APP_ROOT}/web", copy=True)
    .add_local_dir("extension", remote_path=f"{APP_ROOT}/extension", copy=True, ignore=["tests", "tests/**"])
    .add_local_dir("eval", remote_path=f"{APP_ROOT}/eval", copy=True, ignore=["*"])
    .add_local_file(
        "eval/config.json",
        remote_path=f"{APP_ROOT}/eval/config.json",
        copy=True,
    )
    .add_local_file("redactor.py", remote_path=f"{APP_ROOT}/redactor.py", copy=True)
    .env(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
)


@app.function(
    image=image,
    cpu=2,
    memory=4096,
    gpu=None,
    min_containers=0,
    max_containers=2,
    scaledown_window=300,
    timeout=150,
)
@modal.concurrent(max_inputs=4)
@modal.asgi_app()
def web_app():
    """Return the existing FastAPI app; its lifespan warms GLiNER once."""
    import importlib
    import sys

    if APP_ROOT not in sys.path:
        sys.path.insert(0, APP_ROOT)
    return importlib.import_module("api.main").app
