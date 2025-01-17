from typing import Dict, Optional, Any
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
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._last_result: Optional[Any] = None
        self._cache_duration = 5.0  # Default cache duration in seconds
        self.last_process_time = 0
        self.process_interval = 1.0  # Process every 1 second

    def should_process_frame(self) -> bool:
        current_time = time.time()
        return (current_time - self.last_process_time) >= self.process_interval

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
        self._cache_duration = 1.5  # Cache results for 1.5 seconds
        print("Emotion Detector initialized")
    
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
            model="Hemg/Face-Mask-Detection"
        )
        self._cache_duration = 1.5  # Cache results for 1.5 seconds
        print("Mask Detector initialized")
    
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
            
            # Convert BGR to RGB and resize to 224x224 (common input size for ViT models)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(rgb_frame, (224, 224))
            
            # Convert to PIL Image
            pil_image = Image.fromarray(resized_frame)
            
            # Get prediction
            prediction = self.classifier(pil_image)[0]
            print(prediction)
            
            # Check the label and confidence
            wearing_mask = prediction['label'] == "with_mask"
            confidence = prediction['score']
            
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
    def __init__(self):
        self.models = {
            'emotion': EmotionDetector(),
            'mask': MaskDetector()
        }
        self.current_analysis_type = None
    
    async def process_frame(self, frame, analysis_type: str = None) -> Dict[str, Dict[str, Any]]:
        results = {}
        
        # Update analysis type if provided
        if analysis_type is not None:
            self.set_analysis_type(analysis_type)
        
        # If analysis type is "none" or not set, return empty results
        if not self.current_analysis_type or self.current_analysis_type == "none":
            return results
        
        # Process with the current model if it exists
        if self.current_analysis_type in self.models:
            model = self.models[self.current_analysis_type]
            result = await model.process(frame)
            if result:
                results[self.current_analysis_type] = result.to_dict()
        
        return results

    def set_analysis_type(self, analysis_type: str):
        """
        Set the current analysis type for the pipeline.
        If 'none' is provided, clears the current analysis type.
        """
        # Convert to lowercase for case-insensitive comparison
        analysis_type = analysis_type.lower() if analysis_type else 'none'
        
        # Clear analysis type if 'none' is selected
        if analysis_type == 'none':
            if self.current_analysis_type is not None:
                print("Disabling vision pipeline processing")
                self.current_analysis_type = None
            return True
            
        # Set new analysis type if valid
        if analysis_type in self.models:
            if analysis_type != self.current_analysis_type:
                print(f"Switching analysis type to: {analysis_type}")
                self.current_analysis_type = analysis_type
                return True
                
        return False