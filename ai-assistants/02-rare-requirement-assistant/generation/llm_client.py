import time

from openai import OpenAI

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
)


class LLMClient:
    """
    LLM client with provider failover.

    Provider order:
        1. Groq   - Primary
        2. Gemini - Fallback

    Once a provider has a permanent failure such as daily quota
    exhaustion, it is skipped for all subsequent generate() calls
    made by this LLMClient instance.
    """

    MAX_RETRIES = 3
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self):
        if not GEMINI_API_KEY and not GROQ_API_KEY:
            raise ValueError(
                "No LLM provider API key configured. "
                "Set GEMINI_API_KEY and/or GROQ_API_KEY in .env."
            )

        self.providers = []

        # Primary provider: Groq
        if GROQ_API_KEY:
            self.providers.append(
                {
                    "name": "Groq",
                    "client": OpenAI(
                        api_key=GROQ_API_KEY,
                        base_url=GROQ_BASE_URL,
                    ),
                    "model": GROQ_MODEL,
                }
            )

        # Fallback provider: Gemini
        if GEMINI_API_KEY:
            self.providers.append(
                {
                    "name": "Gemini",
                    "client": OpenAI(
                        api_key=GEMINI_API_KEY,
                        base_url=GEMINI_BASE_URL,
                    ),
                    "model": GEMINI_MODEL,
                }
            )

        # Providers that are unavailable for this client run.
        self.unavailable_providers = set()

        # Backward compatibility with existing code.
        self.client = self.providers[0]["client"]
        self.model = self.providers[0]["model"]

    @staticmethod
    def _is_daily_quota_error(exc):
        """
        Detect permanent daily/free-tier quota exhaustion.
        """

        status_code = getattr(exc, "status_code", None)

        if status_code != 429:
            return False

        error_text = str(exc).lower()

        quota_indicators = (
            "quota",
            "free_tier",
            "free tier",
            "daily limit",
            "daily quota",
            "quota exceeded",
            "generate_content_free_tier_requests",
            "generaterequestsperdayperproject-freetier",
        )

        return any(
            indicator in error_text
            for indicator in quota_indicators
        )

    def _generate_with_provider(
        self,
        provider,
        prompt,
        temperature,
        max_tokens,
    ):
        """
        Generate using one provider.

        Temporary errors are retried.
        Permanent quota exhaustion is raised immediately.
        """

        last_exception = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content

                if not content:
                    raise RuntimeError(
                        f"{provider['name']} returned an empty response."
                    )

                return content

            except Exception as exc:
                status_code = getattr(exc, "status_code", None)

                # Daily/free-tier quota:
                # do not retry.
                if self._is_daily_quota_error(exc):
                    raise

                # Other non-retryable errors.
                if status_code not in self.RETRYABLE_STATUS_CODES:
                    raise

                last_exception = exc

                if attempt >= self.MAX_RETRIES:
                    raise

                wait_seconds = 2 ** attempt

                print(
                    f"{provider['name']} temporary error "
                    f"(HTTP {status_code}). "
                    f"Retrying in {wait_seconds}s..."
                )

                time.sleep(wait_seconds)

        raise RuntimeError(
            f"{provider['name']} generation failed."
        ) from last_exception

    def generate(
        self,
        prompt,
        temperature=0.2,
        max_tokens=4000,
    ):
        """
        Generate an LLM response.

        Providers are attempted in configured order.

        Once a provider has a permanent failure such as daily quota
        exhaustion, it is marked unavailable and skipped for all
        subsequent generation calls made by this client.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        errors = []

        for provider in self.providers:
            provider_name = provider["name"]

            # IMPORTANT:
            # Do not retry a provider that has already been marked
            # unavailable during this generation run.
            if provider_name in self.unavailable_providers:
                continue

            try:
                print(
                    f"LLM provider: {provider_name} "
                    f"({provider['model']})"
                )

                result = self._generate_with_provider(
                    provider=provider,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                print(
                    f"LLM provider succeeded: {provider_name}"
                )

                return result

            except Exception as exc:
                status_code = getattr(exc, "status_code", None)

                errors.append(
                    f"{provider_name}: "
                    f"HTTP {status_code} - {exc}"
                )

                # Permanent quota exhaustion.
                if self._is_daily_quota_error(exc):
                    self.unavailable_providers.add(
                        provider_name
                    )

                    print(
                        f"{provider_name} daily quota exhausted. "
                        f"Skipping it for the rest of this run."
                    )

                # Try the next available provider.
                continue

        if not errors:
            raise RuntimeError(
                "All configured LLM providers are currently unavailable."
            )

        raise RuntimeError(
            "All configured LLM providers failed.\n"
            + "\n".join(errors)
        ) from None