"""Download model files into HF_HOME during the Docker build."""

import json
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    model_dir = Path(snapshot_download("urchade/gliner_multi_pii-v1"))
    # GLiNER's config names this tokenizer repository. Cache only the tokenizer
    # artifacts needed at inference, not the base model's unrelated weights.
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
    # Use the cached local tokenizer path so Transformers never needs model
    # metadata from the network when the container starts in offline mode.
    config_path = model_dir / "gliner_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["model_name"] = tokenizer_dir
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
