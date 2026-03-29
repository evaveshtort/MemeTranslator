from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PreprocessConfig:
    invert: bool = True
    clahe: bool = False
    morph: Optional[str] = "erode" 
    blur: Optional[str] = "median"   
    grayscale: bool = False
    resize: Optional[float] = None
    threshold: Optional[str] = None 
    edge_enhance: bool = False
    sharpen: bool = False
    denoise: bool = False


@dataclass
class SuryaConfig:
    conf_threshold: float = 0.9
    languages: list = field(default_factory=lambda: ["ru"])


@dataclass
class OCRConfig:
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    surya: SuryaConfig = field(default_factory=SuryaConfig)