"""Download model files into HF_HOME during the Docker build."""

from huggingface_hub import snapshot_download


def main() -> None:
    snapshot_download("urchade/gliner_multi_pii-v1")
    # GLiNER's config names this tokenizer repository. Cache only the tokenizer
    # artifacts needed at inference, not the base model's unrelated weights.
    snapshot_download(
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


if __name__ == "__main__":
    main()
