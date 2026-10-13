from abc import ABC, abstractmethod
class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, *, system: str, user: str) -> dict:
        """Return a parsed JSON object."""
