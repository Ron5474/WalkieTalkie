"""Small text helpers for logging previews and safe user-facing error messages."""


def preview(text: str, limit: int = 800) -> str:
    return (text or "")[:limit]


def friendly_error_message(err: Exception, context: str = "chat") -> str:
    """
    Convert provider/internal exceptions into safe user-facing text.
    """
    msg = str(err or "")
    low = msg.lower()
    if "ratelimit" in low or "rate limit" in low or "429" in low:
        return (
            "I'm getting rate-limited right now. Please try again in a bit, "
            "or switch model tier if available."
        )
    if context == "image":
        return "I couldn't process that image right now. Please try another image or try again shortly."
    return "I couldn't complete that request right now. Please try again in a moment."
