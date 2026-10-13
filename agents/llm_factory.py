"""Explicitly labeled deterministic mock; no external LLM providers implemented."""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "HRD Genomic Scar Score"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            f"[{self.system_name} mock]: This is a local demonstration response. "
            "No clinical or scientific analysis, validation, or external inference was performed."
        )


class LLMFactory:
    @staticmethod
    def create(provider: str = "mock", system_name: str = "HRD Genomic Scar Score"):
        if str(provider).lower() in ("mock", "deterministic", "test"):
            return MockLLM(system_name)
        raise ValueError(f"Unsupported model provider: {provider}. Only 'mock' is implemented.")
