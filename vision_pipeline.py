from typing import Dict, Optional, Any
import yaml
import time
import cv2
import numpy as np
from dataclasses import dataclass, field
from transformers import pipeline
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import io

@dataclass
class ProcessingResult:
    processing_time: float
    confidence: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'processing_time': self.processing_time,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }

@dataclass
class EmotionResult:
    emotion: str
    processing_time: float
    confidence: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'emotion': self.emotion,
            'processing_time': self.processing_time,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }

@dataclass
class MaskResult:
    wearing_mask: bool
    processing_time: float
    confidence: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'wearing_mask': self.wearing_mask,
            'processing_time': self.processing_time,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }

class BaseVisionModel:
    def __init__(self):
        self._enabled = True
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._last_result: Optional[Any] = None
        self._cache_duration = 5.0  # Default cache duration in seconds

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def get_cached_result(self) -> Optional[Any]:
        if self._last_result is None:
            return None
        
        if time.time() - self._last_result.timestamp <= self._cache_duration:
            return self._last_result
        return None

    async def process(self, frame) -> Optional[Any]:
        raise NotImplementedError

class EmotionDetector(BaseVisionModel):
    def __init__(self):
        super().__init__()
        print("Initializing Emotion Detector...")
        
        self.classifier = pipeline(
            "image-classification",
            model="dima806/facial_emotions_image_detection",
            top_k=7
        )
        
        self.last_process_time = 0
        self.process_interval = 1.0  # Process every 1 second
        self._cache_duration = 1.5  # Cache results for 1.5 seconds
        print("Emotion Detector initialized")
    
    def should_process_frame(self) -> bool:
        current_time = time.time()
        return (current_time - self.last_process_time) >= self.process_interval
    
    async def process(self, frame) -> Optional[EmotionResult]:
        cached_result = self.get_cached_result()
        if cached_result is not None:
            return cached_result
            
        if not self.should_process_frame():
            return self._last_result
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._process_frame, frame)
        
        if result is not None:
            self._last_result = result
            self.last_process_time = time.time()
            
        return result or self._last_result
    
    def _process_frame(self, frame) -> Optional[EmotionResult]:
        try:
            start_time = time.time()
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            predictions = self.classifier(pil_image)
            top_prediction = max(predictions, key=lambda x: x['score'])
            
            processing_time = time.time() - start_time
            
            return EmotionResult(
                emotion=top_prediction['label'],
                confidence=float(top_prediction['score']),
                processing_time=processing_time
            )
            
        except Exception as e:
            print(f"Error in emotion detection: {e}")
            return None

class MaskDetector(BaseVisionModel):
    def __init__(self):
        super().__init__()
        print("Initializing Mask Detector...")
        
        self.classifier = pipeline(
            "image-classification",
            model="mrm8488/mask-detection",
            top_k=2
        )
        
        self.last_process_time = 0
        self.process_interval = 1.0  # Process every 1 second
        self._cache_duration = 1.5  # Cache results for 1.5 seconds
        print("Mask Detector initialized")
    
    def should_process_frame(self) -> bool:
        current_time = time.time()
        return (current_time - self.last_process_time) >= self.process_interval
    
    async def process(self, frame) -> Optional[MaskResult]:
        cached_result = self.get_cached_result()
        if cached_result is not None:
            return cached_result
            
        if not self.should_process_frame():
            return self._last_result
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._process_frame, frame)
        
        if result is not None:
            self._last_result = result
            self.last_process_time = time.time()
            
        return result or self._last_result
    
    def _process_frame(self, frame) -> Optional[MaskResult]:
        try:
            start_time = time.time()
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            predictions = self.classifier(pil_image)
            
            # Model returns 'with_mask' and 'without_mask' predictions
            wearing_mask = any(pred['label'] == 'with_mask' and pred['score'] > 0.5 for pred in predictions)
            confidence = max(pred['score'] for pred in predictions)
            
            processing_time = time.time() - start_time
            
            return MaskResult(
                wearing_mask=wearing_mask,
                confidence=float(confidence),
                processing_time=processing_time
            )
            
        except Exception as e:
            print(f"Error in mask detection: {e}")
            return None

class VisionPipeline:
    def __init__(self, config_path: str = "pipeline_config.yml"):
        self.models: Dict[str, BaseVisionModel] = {}
        self.load_config(config_path)
    
    def load_config(self, config_path: str):
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            print("Config file not found, using default configuration")
            self.config = {'models': {'emotion': {'enabled': True}, 'mask': {'enabled': True}}}
        
        # Initialize enabled models
        if self.config['models'].get('emotion', {}).get('enabled', False):
            self.models['emotion'] = EmotionDetector()
        if self.config['models'].get('mask', {}).get('enabled', False):
            self.models['mask'] = MaskDetector()
    
    async def process_frame(self, frame) -> Dict[str, Dict[str, Any]]:
        results = {}
        for model_name, model in self.models.items():
            if model.is_enabled():
                result = await model.process(frame)
                if result:
                    results[model_name] = result.to_dict()
        return results