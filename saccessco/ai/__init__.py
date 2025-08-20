from typing import Dict, Any

from .gemini import AIEngine as GeminiAIEngine
from .chtgpt import AIEngine as ChtgptAIEngine
# ---- Roles (kept identical for drop-in compatibility) ----
class Role:
    def __init__(self, name: str):
        self.name = name

    @property
    def cap_name(self) -> str:
        return self.name.upper()


User = Role("user")
Model = Role("model")
ROLES = {"User": User, "Model": Model}


class Message:
    """
    Same helper as your Gemini version. We preserve it for compatibility.
    """
    def __init__(self, role: Role, content: str):
        self.role = role.name if isinstance(role, Role) else role
        self.content = content

    @property
    def to_gemini_content_dict(self) -> Dict[str, Any]:
        # Kept for compatibility with existing code that might call it.
        return {"role": self.role, "parts": [{"text": self.content}]}
