from dataclasses import dataclass
from typing import List, Tuple
import json


@dataclass
class TextBlock:
    coords: Tuple[int, int, int, int] 
    text: str
    confidence: float = 1.0


@dataclass
class OCRResult:
    blocks: List[TextBlock]
    full_text: str  

    def to_json(self, **kwargs) -> str:
        data = {
            "full_text": self.full_text,
            "blocks": [
                {
                    "text": b.text,
                    "bbox": list(b.coords),
                    "confidence": b.confidence,
                }
                for b in self.blocks
            ],
        }
        return json.dumps(data, ensure_ascii=False, **kwargs)