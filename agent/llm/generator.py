from .prompts import SYSTEM_PROMPT
def generate(validated_message,data,context=None):
 # Deterministic fallback keeps NovaHR fully functional without any external API.
 return validated_message
