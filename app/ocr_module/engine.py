from PIL import Image
from typing import List

from .config import SuryaConfig
from .models import TextBlock


class SuryaEngine:
    def __init__(self, cfg: SuryaConfig):
        self.cfg = cfg
        self._det = None
        self._rec = None
        self._foundation = None

    def _init(self) -> None:
        if self._foundation is not None:
            return

        from surya.foundation import FoundationPredictor
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor

        self._foundation = FoundationPredictor()
        self._det = DetectionPredictor()
        self._rec = RecognitionPredictor(self._foundation)

    def recognize(self, img: Image.Image) -> List[TextBlock]:
        self._init()

        predictions = self._rec(
            [img],
            task_names=["ocr_with_boxes"],
            det_predictor=self._det,
        )

        blocks = []
        for pred in predictions:
            for line in pred.text_lines:
                if line.bbox is None:
                    continue
                confidence = getattr(line, "confidence", 1.0)
                if confidence < self.cfg.conf_threshold:
                    continue
                x0, y0, x1, y1 = map(int, line.bbox)
                blocks.append(TextBlock(
                    coords=(x0, y0, x1, y1),
                    text=line.text,
                    confidence=confidence,
                ))

        return blocks