import librosa
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
from scipy.signal import find_peaks

from utils.logger import setup_logger

class AudioAnalyzer:
    """Analyzes audio for rhythm and timing information"""
    
    def __init__(self):
        self.logger = setup_logger("audio_analyzer")
    
    def create_rhythm_map(self, audio_path: Path) -> Dict[str, any]:
        """Create comprehensive rhythm and timing analysis"""
        
        self.logger.info(f"Analyzing audio rhythm: {audio_path}")
        
        try:
            # Load audio file
            y, sr = librosa.load(str(audio_path))
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Extract rhythm features
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # Convert numpy values to Python scalars for safe formatting
            tempo_scalar = float(tempo) if hasattr(tempo, 'item') else tempo
            duration_scalar = float(duration) if hasattr(duration, 'item') else duration
            
            # Detect speech segments vs silence
            intervals = librosa.effects.split(y, top_db=20)
            
            # Analyze energy and emphasis
            rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
            emphasis_points = self._find_emphasis_points(rms, sr)
            
            # Detect natural pauses
            natural_breaks = self._find_natural_breaks(y, sr)
            
            # Analyze spectral features for emotional content
            spectral_features = self._analyze_spectral_features(y, sr)
            
            # Create comprehensive rhythm map
            rhythm_map = {
                "duration": duration_scalar,
                "tempo": tempo_scalar,
                "beats": [float(beat * 512 / sr) for beat in beats],  # Convert to seconds
                "speech_segments": [
                    {
                        "start": float(interval[0] / sr),
                        "end": float(interval[1] / sr),
                        "duration": float((interval[1] - interval[0]) / sr)
                    }
                    for interval in intervals
                ],
                "emphasis_points": emphasis_points,
                "natural_breaks": natural_breaks,
                "spectral_features": spectral_features,
                "energy_profile": self._create_energy_profile(rms, sr),
                "pacing_recommendations": self._generate_pacing_recommendations(rms, beats, natural_breaks, sr)
            }
            
            self.logger.info(f"Rhythm analysis complete - Duration: {duration_scalar:.2f}s, Tempo: {tempo_scalar:.1f} BPM")
            return rhythm_map
            
        except Exception as e:
            self.logger.error(f"Error analyzing audio rhythm: {e}")
            raise
    
    def _find_emphasis_points(self, rms: np.ndarray, sr: int) -> List[Dict[str, float]]:
        """Find moments of vocal emphasis based on energy peaks"""
        
        # Smooth RMS for better peak detection
        from scipy.ndimage import gaussian_filter1d
        smoothed_rms = gaussian_filter1d(rms, sigma=2)
        
        # Find peaks above mean + standard deviation
        threshold = np.mean(smoothed_rms) + 0.7 * np.std(smoothed_rms)
        peaks, properties = find_peaks(smoothed_rms, height=threshold, distance=int(0.5 * sr / 512))
        
        emphasis_points = []
        for peak in peaks:
            timestamp = float(peak * 512 / sr)  # Convert frame to seconds
            intensity = float(smoothed_rms[peak])
            
            emphasis_points.append({
                "timestamp": timestamp,
                "intensity": intensity,
                "type": "vocal_emphasis"
            })
        
        return emphasis_points
    
    def _find_natural_breaks(self, y: np.ndarray, sr: int) -> List[Dict[str, float]]:
        """Find natural pauses and breaks in speech"""
        
        # More sensitive silence detection for breaks
        intervals = librosa.effects.split(y, top_db=25, frame_length=2048, hop_length=512)
        
        breaks = []
        for i in range(len(intervals) - 1):
            break_start = float(intervals[i][1] / sr)
            break_end = float(intervals[i + 1][0] / sr)
            break_duration = break_end - break_start
            
            # Only consider significant pauses
            if break_duration > 0.2:  # 200ms minimum
                break_type = "short" if break_duration < 1.0 else "long"
                
                breaks.append({
                    "start": break_start,
                    "end": break_end,
                    "duration": break_duration,
                    "type": break_type
                })
        
        return breaks
    
    def _analyze_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """Analyze spectral features for emotional content"""
        
        # Extract spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        
        return {
            "avg_spectral_centroid": float(np.mean(spectral_centroids)),
            "avg_spectral_rolloff": float(np.mean(spectral_rolloff)),
            "avg_zero_crossing_rate": float(np.mean(zero_crossing_rate)),
            "spectral_variance": float(np.var(spectral_centroids))
        }
    
    def _create_energy_profile(self, rms: np.ndarray, sr: int) -> List[Dict[str, float]]:
        """Create energy profile over time for visual pacing"""
        
        # Sample energy at regular intervals (every 0.5 seconds)
        sample_rate = 0.5  # seconds
        samples_per_interval = int(sample_rate * sr / 512)  # frames per interval
        
        energy_profile = []
        rms_max = float(np.max(rms))  # Convert to scalar
        
        for i in range(0, len(rms), samples_per_interval):
            end_idx = min(i + samples_per_interval, len(rms))
            interval_energy = np.mean(rms[i:end_idx])
            timestamp = float(i * 512 / sr)
            
            energy_profile.append({
                "timestamp": timestamp,
                "energy": float(interval_energy),
                "relative_energy": float(interval_energy / rms_max)  # Normalized 0-1
            })
        
        return energy_profile
    
    def _generate_pacing_recommendations(self, rms: np.ndarray, beats: np.ndarray, natural_breaks: List[Dict], sr: int) -> Dict[str, any]:
        """Generate intelligent pacing recommendations for video editing"""
        
        avg_energy = float(np.mean(rms))
        energy_variance = float(np.var(rms))
        
        # Determine overall pacing style
        if energy_variance > avg_energy * 0.3:
            pacing_style = "dynamic"  # High energy variation
        elif avg_energy > float(np.percentile(rms, 70)):
            pacing_style = "energetic"  # Consistently high energy
        else:
            pacing_style = "steady"  # Stable energy
        
        # Recommend cut points based on beats and breaks
        recommended_cuts = []
        
        # Add cuts at natural breaks
        for break_info in natural_breaks:
            if break_info["duration"] > 0.5:  # Significant breaks
                recommended_cuts.append({
                    "timestamp": break_info["start"],
                    "type": "natural_break",
                    "confidence": 0.9
                })
        
        # Add cuts at strong beats (for rhythmic editing)
        beat_timestamps = beats * 512 / sr
        for beat_time in beat_timestamps[::4]:  # Every 4th beat
            recommended_cuts.append({
                "timestamp": float(beat_time),
                "type": "rhythmic",
                "confidence": 0.6
            })
        
        return {
            "pacing_style": pacing_style,
            "recommended_cuts": recommended_cuts,
            "avg_scene_duration": 3.0 if pacing_style == "energetic" else 5.0,
            "transition_style": "quick" if pacing_style == "dynamic" else "smooth"
        }