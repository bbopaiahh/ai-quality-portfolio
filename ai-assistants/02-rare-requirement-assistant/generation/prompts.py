from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_FILE = BASE_DIR / "prompt.txt"


def load_test_generation_prompt() -> str:
    """
    Load the RARE test-generation prompt from prompt.txt.

    Returns:
        Prompt text.
    """

    if not PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_FILE}"
        )

    prompt = PROMPT_FILE.read_text(
        encoding="utf-8"
    ).strip()

    if not prompt:
        raise ValueError(
            "prompt.txt is empty."
        )

    return prompt