from PIL import Image

from .config import OCRConfig
from .engine import SuryaEngine
from .models import OCRResult
from .preprocess import preprocess


class OCRService:
    def __init__(self, config: OCRConfig = None):
        self.cfg = config or OCRConfig()
        self.engine = SuryaEngine(self.cfg.surya)

    def process(self, img: Image.Image) -> OCRResult:
        preprocessed = preprocess(img, self.cfg.preprocess)
        blocks = self.engine.recognize(preprocessed)
        full_text = "\n".join(b.text for b in blocks)
        return OCRResult(blocks=blocks, full_text=full_text)

    def process_path(self, path: str) -> OCRResult:
        return self.process(Image.open(path))