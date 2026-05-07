import re


class PromptSanitizer:
    DANGEROUS_PATTERNS = [
        r"import\s+os",
        r"ignore (all|any)? (previous|prior|above) (instructions|prompts|rules)",
        r"you are now",
        r"system override",
        r"reveal (you|the) prompt",
        r"\[SYSTEM\]",
        r"DAN mode"
    ]

    ALLOWED_EXTENSIONS = {".py", ".txt", ".md"}

    def is_safe(self, prompt: str) -> bool:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return False
        return True

    def sanitize(self, prompt: str) -> str:
        return prompt.replace("<", "&lt;").replace(">", "&gt;").strip()

    def validate_extension_file(self, filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in self.ALLOWED_EXTENSIONS)

    def max_length(self, prompt: str, max_chars: int = 100_000) -> bool:
        return len(prompt) <= max_chars
    