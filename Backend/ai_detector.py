"""
Advanced AI-Generated Image Detection Module
Combines multiple detection methods for high accuracy AI image detection
"""

import cv2
import numpy as np
import os
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS
import imagehash
import io
import re
from typing import Dict, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIImageDetector:
    """Advanced AI-generated image detector using multiple analysis methods"""
    
    def __init__(self):
        self.ai_tool_signatures = {
            # Popular AI image generators
            'midjourney': ['midjourney', 'mj', 'discord'],
            'dalle': ['dall-e', 'dalle', 'openai'],
            'stable_diffusion': ['stable diffusion', 'sd', 'automatic1111', 'webui'],
            'firefly': ['adobe firefly', 'firefly'],
            'leonardo': ['leonardo.ai', 'leonardo'],
            'runway': ['runway', 'runwayml'],
            'artbreeder': ['artbreeder'],
            'deepai': ['deepai'],
            'nightcafe': ['nightcafe'],
            'starryai': ['starryai'],
            'wombo': ['wombo', 'dream'],
            'canva': ['canva ai', 'magic media'],
            'jasper': ['jasper art'],
            'craiyon': ['craiyon', 'dall-e mini'],
            'bluewillow': ['bluewillow'],
            'playground': ['playground ai'],
            'lexica': ['lexica'],
            'dezgo': ['dezgo'],
            'dream_studio': ['dreamstudio', 'stability.ai'],
            'gemini': ['gemini', 'bard', 'google ai'],
            'claude': ['claude', 'anthropic'],
            'bing': ['bing image creator', 'copilot'],
            'chatgpt': ['chatgpt', 'gpt'],
            'ideogram': ['ideogram'],
            'flux': ['flux', 'black forest labs']
        }
        
        # AI-specific metadata fields
        self.ai_metadata_fields = [
            'Software', 'ImageDescription', 'UserComment', 'Artist', 
            'Copyright', 'ImageHistory', 'Creator', 'Subject'
        ]
        
        # Suspicious patterns in AI images
        self.ai_visual_patterns = {
            'perfect_symmetry': 0.15,
            'unrealistic_lighting': 0.12,
            'texture_inconsistency': 0.18,
            'anatomical_errors': 0.20,
            'background_blur_artifacts': 0.10,
            'color_saturation_anomalies': 0.13,
            'edge_artifacts': 0.12
        }

    def detect_ai_generated(self, image_data: bytes) -> Dict[str, Any]:
        """
        Main detection function that combines all methods
        Returns comprehensive analysis with confidence scores
        """
        try:
            # Convert bytes to PIL Image
            pil_image = Image.open(io.BytesIO(image_data))
            
            # Convert to OpenCV format for advanced analysis
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Run all detection methods
            metadata_result = self._analyze_metadata(pil_image, image_data)
            visual_result = self._analyze_visual_patterns(cv_image, pil_image)
            statistical_result = self._analyze_statistical_patterns(cv_image)
            compression_result = self._analyze_compression_artifacts(cv_image)
            hash_result = self._analyze_perceptual_hash(pil_image)
            naturalness_score = self._estimate_naturalness(cv_image)
            
            # Calculate combined confidence and adjust for very low natural complexity
            confidence = self._calculate_combined_confidence(
                metadata_result, visual_result, statistical_result, 
                compression_result, hash_result
            )
            if naturalness_score < 0.25:
                adjustment = (0.25 - naturalness_score) * 0.4
                confidence = max(0.0, confidence - adjustment)
            
            # Determine if AI-generated based on confidence threshold
            is_ai_generated = confidence > 0.60  # conservative AI threshold
            confidence_level = self._get_confidence_level(confidence)
            analysis_details = self._generate_analysis_details(
                metadata_result, visual_result, statistical_result,
                compression_result, hash_result, confidence
            )
            summary = self._summarize_detection(
                confidence, is_ai_generated, metadata_result,
                visual_result, statistical_result,
                compression_result, hash_result
            )
            
            return {
                "is_ai_generated": is_ai_generated,
                "confidence": round(confidence, 3),
                "confidence_level": confidence_level,
                "summary": summary,
                "naturalness_score": round(naturalness_score, 3),
                "detection_methods": {
                    "metadata": metadata_result,
                    "visual_patterns": visual_result,
                    "statistical": statistical_result,
                    "compression": compression_result,
                    "perceptual_hash": hash_result,
                    "naturalness": {"score": round(naturalness_score, 3)}
                },
                "analysis_details": analysis_details,
                "detected_tools": self._identify_potential_tools(metadata_result, visual_result)
            }
            
        except Exception as e:
            logger.error(f"AI detection error: {e}")
            return {
                "is_ai_generated": False,
                "confidence": 0.0,
                "confidence_level": "unknown",
                "error": str(e)
            }

    def _analyze_metadata(self, pil_image: Image.Image, image_data: bytes) -> Dict[str, Any]:
        """Analyze image metadata for AI tool signatures"""
        try:
            metadata_score = 0.0
            detected_signatures = []
            suspicious_fields = []
            
            # Extract EXIF data
            exif_data = pil_image._getexif() if hasattr(pil_image, '_getexif') else None
            
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, str):
                        value_lower = value.lower()
                        
                        # Check for AI tool signatures
                        for tool, signatures in self.ai_tool_signatures.items():
                            for signature in signatures:
                                if signature in value_lower:
                                    detected_signatures.append(tool)
                                    metadata_score += 0.8
                                    suspicious_fields.append(f"{tag}: {value}")
                        
                        # Check for suspicious patterns
                        if any(word in value_lower for word in ['generated', 'artificial', 'synthetic', 'ai']):
                            metadata_score += 0.6
                            suspicious_fields.append(f"{tag}: {value}")
                        
                        # Check for missing typical camera metadata
                        camera_fields = ['Make', 'Model', 'DateTime', 'ExposureTime', 'FNumber']
                        extracted_tags = [TAGS.get(tid) for tid in exif_data.keys()]
                        missing_camera_fields = [field for field in camera_fields if field not in extracted_tags]
                        if len(missing_camera_fields) >= 3:
                            metadata_score += 0.3
                            suspicious_fields.append(f"Missing camera metadata: {', '.join(missing_camera_fields)}")
            
            # Check file size patterns (AI images often have specific size patterns)
            file_size = len(image_data)
            if self._is_suspicious_file_size(file_size):
                metadata_score += 0.2
            
            return {
                "score": min(metadata_score, 1.0),
                "detected_signatures": list(set(detected_signatures)),
                "suspicious_fields": suspicious_fields,
                "missing_camera_fields": missing_camera_fields if exif_data else [],
                "has_camera_metadata": exif_data is not None and len(missing_camera_fields) == 0
            }
            
        except Exception as e:
            logger.error(f"Metadata analysis error: {e}")
            return {"score": 0.0, "error": str(e)}

    def _analyze_visual_patterns(self, cv_image: np.ndarray, pil_image: Image.Image) -> Dict[str, Any]:
        """Analyze visual patterns typical of AI-generated images"""
        try:
            visual_score = 0.0
            detected_patterns = []
            
            # FAST PATH: Downscale image significantly for analysis to speed up processing
            # 512px is plenty for pattern detection
            max_anal_size = 512
            h, w = cv_image.shape[:2]
            if max(h, w) > max_anal_size:
                scale = max_anal_size / max(h, w)
                cv_image = cv2.resize(cv_image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 1. Analyze edge consistency
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            # Natural photos usually have edge density between 0.02 and 0.2
            if edge_density < 0.01 or edge_density > 0.3:
                visual_score += 0.15
                detected_patterns.append("unusual_edge_density")
            
            # 2. Analyze texture consistency
            texture_score = self._analyze_texture_consistency(gray)
            if texture_score > 0.6: # Increased threshold to reduce false positives
                visual_score += 0.2
                detected_patterns.append("texture_inconsistency")
            
            # 3. Analyze color distribution
            color_score = self._analyze_color_distribution(cv_image)
            if color_score > 0.7: # Increased threshold
                visual_score += 0.1
                detected_patterns.append("color_anomalies")
            
            # 4. Analyze symmetry
            symmetry_score = self._analyze_symmetry(gray)
            if symmetry_score > 0.85: # Increased threshold (AI often makes it >0.9)
                visual_score += 0.1
                detected_patterns.append("perfect_symmetry")
            
            # 5. Analyze noise patterns
            noise_score = self._analyze_noise_patterns(gray)
            if noise_score > 0.7: # Increased threshold
                visual_score += 0.1
                detected_patterns.append("artificial_noise")
            
            # 6. Analyze frequency domain (Slowest part - skip if fast mode is needed or optimize)
            frequency_score = self._analyze_frequency_domain(gray)
            if frequency_score > 0.6:
                visual_score += 0.1
                detected_patterns.append("frequency_anomalies")
            
            # 7. Analyze for AI-specific artifacts
            ai_artifacts_score = self._analyze_ai_artifacts(cv_image)
            if ai_artifacts_score > 0.4: # Increased threshold
                visual_score += 0.3
                detected_patterns.append("ai_generation_artifacts")
            
            return {
                "score": min(visual_score, 1.0),
                "detected_patterns": detected_patterns,
                "edge_density": float(edge_density),
                "texture_score": float(texture_score),
                "color_score": float(color_score),
                "symmetry_score": float(symmetry_score),
                "noise_score": float(noise_score),
                "frequency_score": float(frequency_score),
                "ai_artifacts_score": float(ai_artifacts_score)
            }
            
        except Exception as e:
            logger.error(f"Visual pattern analysis error: {e}")
            return {"score": 0.0, "error": str(e)}

    def _analyze_statistical_patterns(self, cv_image: np.ndarray) -> Dict[str, Any]:
        """Analyze statistical properties of the image"""
        try:
            statistical_score = 0.0
            anomalies = []
            
            # Convert to different color spaces for analysis
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
            
            # 1. Analyze pixel value distributions
            for i, channel_name in enumerate(['B', 'G', 'R']):
                channel = cv_image[:, :, i]
                hist = cv2.calcHist([channel], [0], None, [256], [0, 256])
                
                # Check for unusual distribution patterns
                hist_normalized = hist.flatten() / hist.sum()
                entropy = -np.sum(hist_normalized * np.log2(hist_normalized + 1e-10))
                
                if entropy < 6.0 or entropy > 7.8:  # Typical range for natural images
                    statistical_score += 0.1
                    anomalies.append(f"unusual_{channel_name.lower()}_distribution")
            
            # 2. Analyze local binary patterns
            lbp_score = self._analyze_lbp_patterns(cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY))
            if lbp_score > 0.7:
                statistical_score += 0.2
                anomalies.append("unusual_lbp_patterns")
            
            # 3. Analyze gradient patterns
            gradient_score = self._analyze_gradient_patterns(cv_image)
            if gradient_score > 0.6:
                statistical_score += 0.15
                anomalies.append("gradient_anomalies")
            
            return {
                "score": min(statistical_score, 1.0),
                "anomalies": anomalies,
                "lbp_score": lbp_score,
                "gradient_score": gradient_score
            }
            
        except Exception as e:
            logger.error(f"Statistical analysis error: {e}")
            return {"score": 0.0, "error": str(e)}

    def _analyze_compression_artifacts(self, cv_image: np.ndarray) -> Dict[str, Any]:
        """Analyze compression artifacts that may indicate AI generation"""
        try:
            compression_score = 0.0
            artifacts = []
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 1. Analyze DCT coefficients (JPEG compression patterns)
            dct_score = self._analyze_dct_patterns(gray)
            if dct_score > 0.6:
                compression_score += 0.3
                artifacts.append("unusual_dct_patterns")
            
            # 2. Analyze blocking artifacts
            blocking_score = self._analyze_blocking_artifacts(gray)
            if blocking_score < 0.3:  # AI images often lack typical JPEG blocking
                compression_score += 0.2
                artifacts.append("missing_jpeg_blocks")
            
            # 3. Analyze quantization patterns
            quantization_score = self._analyze_quantization_patterns(gray)
            if quantization_score > 0.7:
                compression_score += 0.25
                artifacts.append("unusual_quantization")
            
            return {
                "score": min(compression_score, 1.0),
                "artifacts": artifacts,
                "dct_score": dct_score,
                "blocking_score": blocking_score,
                "quantization_score": quantization_score
            }
            
        except Exception as e:
            logger.error(f"Compression analysis error: {e}")
            return {"score": 0.0, "error": str(e)}

    def _analyze_perceptual_hash(self, pil_image: Image.Image) -> Dict[str, Any]:
        """Analyze perceptual hash patterns"""
        try:
            hash_score = 0.0
            hash_features = []
            
            # Calculate different types of hashes
            ahash = imagehash.average_hash(pil_image)
            phash = imagehash.phash(pil_image)
            dhash = imagehash.dhash(pil_image)
            whash = imagehash.whash(pil_image)
            
            # Analyze hash patterns for AI characteristics
            hash_values = [str(ahash), str(phash), str(dhash), str(whash)]
            
            # Check for patterns typical in AI-generated images
            for hash_val in hash_values:
                # AI images often have specific bit patterns
                ones_count = hash_val.count('1') if '1' in hash_val else 0
                zeros_count = hash_val.count('0') if '0' in hash_val else 0
                
                if ones_count == 0 or zeros_count == 0:
                    hash_score += 0.2
                    hash_features.append("extreme_hash_pattern")
                
                # Check for repetitive patterns
                if len(set(hash_val)) < 4:
                    hash_score += 0.15
                    hash_features.append("repetitive_hash_pattern")
            
            return {
                "score": min(hash_score, 1.0),
                "features": hash_features,
                "hashes": {
                    "average": str(ahash),
                    "perceptual": str(phash),
                    "difference": str(dhash),
                    "wavelet": str(whash)
                }
            }
            
        except Exception as e:
            logger.warning(f"Perceptual hash analysis error: {e}")
            # Return neutral score if hash analysis fails
            return {
                "score": 0.0, 
                "features": [],
                "hashes": {},
                "error": str(e),
                "note": "Perceptual hash analysis skipped due to system restrictions"
            }

    def _calculate_combined_confidence(self, metadata_result: Dict, visual_result: Dict, 
                                     statistical_result: Dict, compression_result: Dict, 
                                     hash_result: Dict) -> float:
        """Calculate combined confidence score from all detection methods"""
        
        # Weighted combination optimized for modern AI-generated images
        weights = {
            'metadata': 0.50,      # Increased - metadata is very reliable when present
            'visual': 0.40,        # Visual patterns are good indicators
            'statistical': 0.05,   
            'compression': 0.03,   
            'hash': 0.02          
        }
        
        scores = {
            'metadata': float(metadata_result.get('score', 0.0)),
            'visual': float(visual_result.get('score', 0.0)),
            'statistical': float(statistical_result.get('score', 0.0)),
            'compression': float(compression_result.get('score', 0.0)),
            'hash': float(hash_result.get('score', 0.0))
        }
        
        # Calculate weighted average
        combined_score = sum(weights[method] * scores[method] for method in weights.keys())
        
        # Apply bonus only if scores are very high (reducing false positives)
        positive_methods = sum(1 for score in scores.values() if score > 0.6)
        if positive_methods >= 2:
            combined_score += 0.15 
        
        return float(min(combined_score, 1.0))

    def _get_confidence_level(self, confidence: float) -> str:
        """Convert confidence score to human-readable level"""
        if confidence >= 0.85:
            return "very_high"
        elif confidence >= 0.70:
            return "high"
        elif confidence >= 0.50:
            return "medium"
        elif confidence >= 0.30:
            return "low"
        else:
            return "very_low"

    def _estimate_naturalness(self, cv_image: np.ndarray) -> float:
        """Estimate how photo-like an image is to avoid over-flagging simple graphics."""
        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            if h == 0 or w == 0:
                return 0.0

            # Edge density, texture, and noise all help estimate naturalness.
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            texture = np.std(cv2.Laplacian(gray, cv2.CV_64F)) / 20.0
            noise = np.std(gray - cv2.GaussianBlur(gray, (5, 5), 0)) / 20.0

            score = (min(edge_density * 5.0, 1.0) + min(texture, 1.0) + min(noise, 1.0)) / 3.0
            return float(min(max(score, 0.0), 1.0))
        except Exception:
            return 0.0

    def _summarize_detection(
        self,
        confidence: float,
        is_ai: bool,
        metadata_result: Dict,
        visual_result: Dict,
        statistical_result: Dict,
        compression_result: Dict,
        hash_result: Dict,
    ) -> str:
        """Create a concise, human-readable summary of the detection result."""
        parts = []
        if is_ai:
            parts.append("The image is likely AI-generated.")
        else:
            parts.append("The image is likely a natural photo.")

        parts.append(f"Overall confidence: {confidence:.2f}.")

        strong_reasons = []
        if metadata_result.get("score", 0.0) > 0.35:
            strong_reasons.append("suspicious metadata")
        if visual_result.get("score", 0.0) > 0.4:
            strong_reasons.append("visual pattern anomalies")
        if statistical_result.get("score", 0.0) > 0.4:
            strong_reasons.append("statistical irregularities")
        if compression_result.get("score", 0.0) > 0.4:
            strong_reasons.append("compression artifacts")
        if hash_result.get("score", 0.0) > 0.3:
            strong_reasons.append("perceptual hash anomalies")

        if strong_reasons:
            parts.append("Key signals: " + ", ".join(strong_reasons) + ".")
        else:
            parts.append("No strong AI-specific signals were detected.")

        return " ".join(parts)

    def _generate_analysis_details(self, metadata_result: Dict, visual_result: Dict,
                                 statistical_result: Dict, compression_result: Dict,
                                 hash_result: Dict, confidence: float) -> List[str]:
        """Generate human-readable analysis details"""
        details = []
        
        if metadata_result.get('detected_signatures'):
            tools = ', '.join(metadata_result['detected_signatures'])
            details.append(f"Detected AI tool signatures: {tools}")
        
        if not metadata_result.get('has_camera_metadata', True):
            details.append("Missing typical camera metadata")
        
        if visual_result.get('detected_patterns'):
            patterns = ', '.join(visual_result['detected_patterns'])
            details.append(f"Visual anomalies detected: {patterns}")
        
        if statistical_result.get('anomalies'):
            anomalies = ', '.join(statistical_result['anomalies'])
            details.append(f"Statistical anomalies: {anomalies}")
        
        if compression_result.get('artifacts'):
            artifacts = ', '.join(compression_result['artifacts'])
            details.append(f"Compression artifacts: {artifacts}")
        
        if confidence < 0.35:
            details.append("Image shows characteristics typical of natural photography.")
        elif confidence < 0.60:
            details.append("Image has some ambiguous characteristics and may require a second opinion.")
        else:
            details.append("Image shows strong indicators of AI generation.")
        
        return details

    def _identify_potential_tools(self, metadata_result: Dict, visual_result: Dict) -> List[str]:
        """Identify potential AI tools used to generate the image"""
        potential_tools = []
        
        # From metadata signatures
        if metadata_result.get('detected_signatures'):
            potential_tools.extend(metadata_result['detected_signatures'])
        
        # From visual patterns (heuristic matching)
        patterns = visual_result.get('detected_patterns', [])
        if 'perfect_symmetry' in patterns and 'texture_inconsistency' in patterns:
            potential_tools.append('stable_diffusion')
        if 'color_anomalies' in patterns and 'frequency_anomalies' in patterns:
            potential_tools.append('midjourney')
        
        return list(set(potential_tools))

    # Helper methods for specific analyses
    def _is_suspicious_file_size(self, file_size: int) -> bool:
        """Check if file size matches typical AI generation patterns"""
        # AI images often have specific size patterns
        suspicious_ranges = [
            (500000, 600000),   # ~500-600KB common for AI
            (1000000, 1100000), # ~1-1.1MB common for AI
            (2000000, 2200000)  # ~2-2.2MB common for AI
        ]
        return any(start <= file_size <= end for start, end in suspicious_ranges)

    def _analyze_texture_consistency(self, gray: np.ndarray) -> float:
        """Analyze texture consistency across the image"""
        try:
            # Calculate local standard deviation
            kernel = np.ones((9, 9), np.float32) / 81
            mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
            sqr_mean = cv2.filter2D((gray.astype(np.float32))**2, -1, kernel)
            std_dev = np.sqrt(sqr_mean - mean**2)
            
            # Calculate coefficient of variation of local standard deviations
            cv_std = np.std(std_dev) / (np.mean(std_dev) + 1e-10)
            return min(cv_std / 50.0, 1.0)  # Normalize
        except:
            return 0.0

    def _analyze_color_distribution(self, cv_image: np.ndarray) -> float:
        """Analyze color distribution for anomalies"""
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            
            # Calculate color histogram
            hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Normalize histograms
            hist_h = hist_h.flatten() / hist_h.sum()
            hist_s = hist_s.flatten() / hist_s.sum()
            hist_v = hist_v.flatten() / hist_v.sum()
            
            # Calculate entropy for each channel
            entropy_h = -np.sum(hist_h * np.log2(hist_h + 1e-10))
            entropy_s = -np.sum(hist_s * np.log2(hist_s + 1e-10))
            entropy_v = -np.sum(hist_v * np.log2(hist_v + 1e-10))
            
            # AI images often have unusual color distributions
            expected_entropy = [6.5, 7.0, 7.2]  # Typical values for natural images
            actual_entropy = [entropy_h, entropy_s, entropy_v]
            
            deviation = sum(abs(a - e) for a, e in zip(actual_entropy, expected_entropy))
            return min(deviation / 10.0, 1.0)
        except:
            return 0.0

    def _analyze_symmetry(self, gray: np.ndarray) -> float:
        """Analyze image symmetry"""
        try:
            h, w = gray.shape
            
            # Horizontal symmetry
            left_half = gray[:, :w//2]
            right_half = cv2.flip(gray[:, w//2:], 1)
            
            # Resize to match if needed
            min_width = min(left_half.shape[1], right_half.shape[1])
            left_half = left_half[:, :min_width]
            right_half = right_half[:, :min_width]
            
            # Calculate correlation
            correlation = cv2.matchTemplate(left_half, right_half, cv2.TM_CCOEFF_NORMED)[0, 0]
            return max(0, correlation)
        except:
            return 0.0

    def _analyze_noise_patterns(self, gray: np.ndarray) -> float:
        """Analyze noise patterns in the image"""
        try:
            # Apply Gaussian blur and subtract to get noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            noise = cv2.absdiff(gray, blurred)
            
            # Calculate noise statistics
            noise_mean = np.mean(noise)
            noise_std = np.std(noise)
            
            # AI images often have very uniform noise or no noise
            if noise_std < 2.0 or noise_mean < 1.0:
                return 0.8
            elif noise_std > 15.0:
                return 0.6
            else:
                return 0.0
        except:
            return 0.0

    def _analyze_frequency_domain(self, gray: np.ndarray) -> float:
        """Analyze frequency domain characteristics"""
        try:
            # Apply FFT
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)
            
            # Analyze frequency distribution
            h, w = magnitude_spectrum.shape
            center_y, center_x = h // 2, w // 2
            
            # Calculate radial frequency distribution
            y, x = np.ogrid[:h, :w]
            mask = (x - center_x)**2 + (y - center_y)**2
            
            # AI images often have unusual frequency patterns
            low_freq = magnitude_spectrum[mask < (min(h, w) // 4)**2].mean()
            high_freq = magnitude_spectrum[mask > (min(h, w) // 2)**2].mean()
            
            freq_ratio = high_freq / (low_freq + 1e-10)
            
            # Unusual ratios indicate potential AI generation
            if freq_ratio < 0.1 or freq_ratio > 2.0:
                return 0.7
            else:
                return 0.0
        except:
            return 0.0

    def _analyze_lbp_patterns(self, gray: np.ndarray) -> float:
        """Analyze Local Binary Patterns"""
        try:
            # Simple LBP implementation
            h, w = gray.shape
            lbp = np.zeros((h-2, w-2), dtype=np.uint8)
            
            for i in range(1, h-1):
                for j in range(1, w-1):
                    center = gray[i, j]
                    code = 0
                    code |= (gray[i-1, j-1] >= center) << 7
                    code |= (gray[i-1, j] >= center) << 6
                    code |= (gray[i-1, j+1] >= center) << 5
                    code |= (gray[i, j+1] >= center) << 4
                    code |= (gray[i+1, j+1] >= center) << 3
                    code |= (gray[i+1, j] >= center) << 2
                    code |= (gray[i+1, j-1] >= center) << 1
                    code |= (gray[i, j-1] >= center) << 0
                    lbp[i-1, j-1] = code
            
            # Calculate LBP histogram
            hist = np.bincount(lbp.ravel(), minlength=256)
            hist = hist / hist.sum()
            
            # Calculate uniformity
            uniform_patterns = 0
            for i in range(256):
                # Count transitions in binary representation
                binary = format(i, '08b')
                transitions = sum(1 for j in range(8) if binary[j] != binary[(j+1)%8])
                if transitions <= 2:
                    uniform_patterns += hist[i]
            
            # AI images often have unusual LBP uniformity
            if uniform_patterns > 0.9 or uniform_patterns < 0.3:
                return 0.8
            else:
                return 0.0
        except:
            return 0.0

    def _analyze_gradient_patterns(self, cv_image: np.ndarray) -> float:
        """Analyze gradient patterns in the image"""
        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Calculate gradients
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude and direction
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            direction = np.arctan2(grad_y, grad_x)
            
            # Analyze gradient distribution
            mag_hist = np.histogram(magnitude, bins=50)[0]
            dir_hist = np.histogram(direction, bins=36)[0]  # 36 bins for 10-degree intervals
            
            # Normalize histograms
            mag_hist = mag_hist / mag_hist.sum()
            dir_hist = dir_hist / dir_hist.sum()
            
            # Calculate entropy
            mag_entropy = -np.sum(mag_hist * np.log2(mag_hist + 1e-10))
            dir_entropy = -np.sum(dir_hist * np.log2(dir_hist + 1e-10))
            
            # AI images often have unusual gradient patterns
            if mag_entropy < 4.0 or dir_entropy < 4.5:
                return 0.7
            else:
                return 0.0
        except:
            return 0.0

    def _analyze_dct_patterns(self, gray: np.ndarray) -> float:
        """Analyze DCT coefficient patterns"""
        try:
            # Apply DCT to 8x8 blocks (similar to JPEG)
            h, w = gray.shape
            dct_coeffs = []
            
            for i in range(0, h-8, 8):
                for j in range(0, w-8, 8):
                    block = gray[i:i+8, j:j+8].astype(np.float32)
                    dct_block = cv2.dct(block)
                    dct_coeffs.append(dct_block.flatten())
            
            if not dct_coeffs:
                return 0.0
            
            dct_coeffs = np.array(dct_coeffs)
            
            # Analyze coefficient distribution
            coeff_std = np.std(dct_coeffs, axis=0)
            
            # AI images often have unusual DCT patterns
            unusual_coeffs = np.sum(coeff_std < 0.1) + np.sum(coeff_std > 50)
            unusual_ratio = unusual_coeffs / len(coeff_std)
            
            return min(unusual_ratio * 2, 1.0)
        except:
            return 0.0

    def _analyze_blocking_artifacts(self, gray: np.ndarray) -> float:
        """Analyze JPEG blocking artifacts"""
        try:
            h, w = gray.shape
            
            # Calculate differences across 8-pixel boundaries
            vertical_diffs = []
            horizontal_diffs = []
            
            # Vertical boundaries
            for i in range(7, h, 8):
                if i < h-1:
                    diff = np.mean(np.abs(gray[i, :] - gray[i+1, :]))
                    vertical_diffs.append(diff)
            
            # Horizontal boundaries
            for j in range(7, w, 8):
                if j < w-1:
                    diff = np.mean(np.abs(gray[:, j] - gray[:, j+1]))
                    horizontal_diffs.append(diff)
            
            if not vertical_diffs or not horizontal_diffs:
                return 0.0
            
            # Calculate blocking artifact strength
            avg_vertical = np.mean(vertical_diffs)
            avg_horizontal = np.mean(horizontal_diffs)
            blocking_strength = (avg_vertical + avg_horizontal) / 2
            
            return min(blocking_strength / 10.0, 1.0)
        except:
            return 0.0

    def _analyze_quantization_patterns(self, gray: np.ndarray) -> float:
        """Analyze quantization patterns"""
        try:
            # Calculate histogram
            hist = np.histogram(gray, bins=256, range=(0, 256))[0]
            
            # Look for quantization artifacts (peaks at regular intervals)
            peaks = []
            for i in range(1, 255):
                if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
                    peaks.append(i)
            
            if len(peaks) < 2:
                return 0.0
            
            # Check for regular spacing (indicating quantization)
            spacings = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
            
            # Look for common quantization levels
            common_spacings = [8, 16, 32, 64]  # Common quantization steps
            regular_spacings = sum(1 for spacing in spacings if any(abs(spacing - cs) <= 2 for cs in common_spacings))
            
            regularity = regular_spacings / len(spacings) if spacings else 0
            return regularity
        except:
            return 0.0

    def _analyze_ai_artifacts(self, cv_image: np.ndarray) -> float:
        """Analyze for specific AI generation artifacts"""
        try:
            artifact_score = 0.0
            
            # Convert to different color spaces
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            
            # 1. Check for unrealistic lighting consistency
            # AI often creates perfectly consistent lighting that's unnatural
            lighting_variance = self._analyze_lighting_consistency(cv_image)
            if lighting_variance < 0.1:  # Too consistent
                artifact_score += 0.3
            
            # 2. Check for perfect gradients (common in AI)
            gradient_perfection = self._analyze_gradient_perfection(gray)
            if gradient_perfection > 0.7:
                artifact_score += 0.25
            
            # 3. Check for AI-typical color saturation patterns
            saturation_pattern = self._analyze_saturation_patterns(hsv)
            if saturation_pattern > 0.6:
                artifact_score += 0.2
            
            # 4. Check for lack of natural imperfections
            imperfection_score = self._analyze_natural_imperfections(gray)
            if imperfection_score < 0.2:  # Too perfect
                artifact_score += 0.25
            
            return min(artifact_score, 1.0)
            
        except Exception as e:
            logger.warning(f"AI artifacts analysis error: {e}")
            return 0.0

    def _analyze_lighting_consistency(self, cv_image: np.ndarray) -> float:
        """Analyze lighting consistency across the image"""
        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # Divide image into regions and analyze lighting
            regions = []
            for i in range(0, h, h//4):
                for j in range(0, w, w//4):
                    region = gray[i:min(i+h//4, h), j:min(j+w//4, w)]
                    if region.size > 0:
                        regions.append(np.mean(region))
            
            if len(regions) < 4:
                return 0.5
            
            # Calculate variance in lighting across regions
            lighting_variance = np.var(regions) / (np.mean(regions) + 1e-10)
            return float(lighting_variance)
            
        except:
            return 0.5

    def _analyze_gradient_perfection(self, gray: np.ndarray) -> float:
        """Analyze for unnaturally perfect gradients"""
        try:
            # Calculate gradients
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Check for areas with very smooth gradients (typical of AI)
            smooth_areas = np.sum(magnitude < 5) / magnitude.size
            
            return float(smooth_areas)
            
        except:
            return 0.0

    def _analyze_saturation_patterns(self, hsv: np.ndarray) -> float:
        """Analyze saturation patterns typical of AI"""
        try:
            saturation = hsv[:, :, 1]
            
            # AI images often have very specific saturation distributions
            hist = np.histogram(saturation, bins=50)[0]
            hist_normalized = hist / hist.sum()
            
            # Check for peaks at specific saturation levels (common in AI)
            peak_indices = []
            for i in range(1, len(hist_normalized)-1):
                if hist_normalized[i] > hist_normalized[i-1] and hist_normalized[i] > hist_normalized[i+1]:
                    if hist_normalized[i] > 0.05:  # Significant peak
                        peak_indices.append(i)
            
            # AI images often have 2-4 dominant saturation levels
            if len(peak_indices) >= 2 and len(peak_indices) <= 4:
                return 0.8
            elif len(peak_indices) == 1:
                return 0.6
            else:
                return 0.2
                
        except:
            return 0.0

    def _analyze_natural_imperfections(self, gray: np.ndarray) -> float:
        """Analyze for natural imperfections that AI often lacks"""
        try:
            # Real photos have natural noise and imperfections
            # AI images are often too clean
            
            # 1. Check for natural noise
            noise_level = np.std(gray - cv2.GaussianBlur(gray, (3, 3), 0))
            
            # 2. Check for micro-details
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            detail_level = np.var(laplacian)
            
            # 3. Check for natural variations
            local_std = cv2.filter2D(gray.astype(np.float32), -1, np.ones((5,5))/25)
            variation_level = np.std(local_std)
            
            # Combine scores (higher = more natural imperfections)
            imperfection_score = (noise_level/10 + detail_level/1000 + variation_level/50) / 3
            
            return float(min(imperfection_score, 1.0))
            
        except:
            return 0.5

# Global detector instance
ai_detector = AIImageDetector()
DETECTION_CACHE = {}

def detect_ai_image(image_data: bytes) -> Dict[str, Any]:
    """
    Main function to detect if an image is AI-generated
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Dictionary with detection results and confidence scores
    """
    try:
        max_size = int(os.getenv("AI_DETECT_MAX_SIZE", "512"))
    except Exception:
        max_size = 512
    fast = os.getenv("AI_DETECT_FAST", "1").lower() in ("1", "true", "yes")
    cache_key = hashlib.sha256(image_data).hexdigest() + f":{fast}:{max_size}"
    cached = DETECTION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
    resized_image = pil_image
    if max_size > 0 and max(resized_image.size) > max_size:
        ratio = max_size / max(resized_image.size)
        new_size = (int(resized_image.size[0] * ratio), int(resized_image.size[1] * ratio))
        resized_image = resized_image.resize(new_size, Image.Resampling.BILINEAR)

    ai_threshold = float(os.getenv("AI_DETECT_AI_THRESHOLD", "0.60"))
    original_threshold = float(os.getenv("AI_DETECT_ORIGINAL_THRESHOLD", "0.30"))

    if fast:
        metadata_result = ai_detector._analyze_metadata(pil_image, image_data)
        cv_image = cv2.cvtColor(np.array(resized_image), cv2.COLOR_RGB2BGR)
        visual_result = ai_detector._analyze_visual_patterns(cv_image, resized_image)
        statistical_result = {"score": 0.0, "anomalies": []}
        compression_result = {"score": 0.0, "artifacts": []}
        hash_result = ai_detector._analyze_perceptual_hash(resized_image)
        naturalness_score = ai_detector._estimate_naturalness(cv_image)
        confidence = ai_detector._calculate_combined_confidence(
            metadata_result, visual_result, statistical_result, compression_result, hash_result
        )
        if naturalness_score < 0.25:
            adjustment = (0.25 - naturalness_score) * 0.4
            confidence = max(0.0, confidence - adjustment)
        if confidence >= ai_threshold:
            is_ai_generated = True
            confidence_level = "likely_ai"
        elif confidence <= original_threshold:
            is_ai_generated = False
            confidence_level = "likely_real"
        else:
            is_ai_generated = False
            confidence_level = "uncertain"
        analysis_details = ai_detector._generate_analysis_details(
            metadata_result, visual_result, statistical_result, compression_result, hash_result, confidence
        )
        summary = ai_detector._summarize_detection(
            confidence, is_ai_generated, metadata_result,
            visual_result, statistical_result, compression_result, hash_result
        )
        result = {
            "is_ai_generated": is_ai_generated,
            "confidence": round(confidence, 3),
            "confidence_level": confidence_level,
            "summary": summary,
            "analysis_mode": "fast",
            "naturalness_score": round(naturalness_score, 3),
            "detection_methods": {
                "metadata": metadata_result,
                "visual_patterns": visual_result,
                "statistical": statistical_result,
                "compression": compression_result,
                "perceptual_hash": hash_result,
                "naturalness": {"score": round(naturalness_score, 3)}
            },
            "analysis_details": analysis_details,
            "detected_tools": ai_detector._identify_potential_tools(metadata_result, visual_result)
        }
    else:
        if resized_image.size != pil_image.size:
            buffer = io.BytesIO()
            resized_image.save(buffer, format="JPEG", quality=90)
            image_data = buffer.getvalue()
        result = ai_detector.detect_ai_generated(image_data)
        confidence = float(result.get("confidence", 0.0))
        if confidence >= ai_threshold:
            result["is_ai_generated"] = True
            result["confidence_level"] = "likely_ai"
        elif confidence <= original_threshold:
            result["is_ai_generated"] = False
            result["confidence_level"] = "likely_real"
        else:
            result["is_ai_generated"] = False
            result["confidence_level"] = "uncertain"
        result["summary"] = ai_detector._summarize_detection(
            confidence,
            result["is_ai_generated"],
            result.get("detection_methods", {}).get("metadata", {}),
            result.get("detection_methods", {}).get("visual_patterns", {}),
            result.get("detection_methods", {}).get("statistical", {}),
            result.get("detection_methods", {}).get("compression", {}),
            result.get("detection_methods", {}).get("perceptual_hash", {})
        )
        result["analysis_mode"] = "full"
    
    # Convert numpy types and sanitize floats for JSON serialization
    def convert_numpy_types(obj):
        import math
        def sanitize_number(x):
            if isinstance(x, float):
                if math.isnan(x) or math.isinf(x):
                    return 0.0
                return x
            return x
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert_numpy_types(item) for item in obj]
        # numpy scalar
        if hasattr(obj, 'item') and not isinstance(obj, (bytes, bytearray)):
            val = obj.item()
            return convert_numpy_types(val)
        # numpy array
        if hasattr(obj, 'tolist'):
            arr = obj.tolist()
            return convert_numpy_types(arr)
        return sanitize_number(obj)
    
    result = convert_numpy_types(result)
    DETECTION_CACHE[cache_key] = result
    if len(DETECTION_CACHE) > 100:
        DETECTION_CACHE.clear()
    return result
