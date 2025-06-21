"""
Adaptive difficulty system that reliably adjusts note density for different songs and genres.
"""
import logging
from typing import List, Tuple, Dict, Any

try:
    import numpy as np
except ImportError:
    # Define minimal numpy functionality needed
    class NumpyStub:
        def mean(self, x, *args, **kwargs):
            if not x:
                return 0
            return sum(x) / len(x)
        
        def sum(self, x, *args, **kwargs):
            return sum(x) if hasattr(x, '__iter__') else x
            
    np = NumpyStub()

logger = logging.getLogger(__name__)

class AdaptiveDifficultyEngine:
    """
    Engine that adapts note generation to achieve target difficulty levels
    regardless of song genre, tempo, or complexity.
    """
    
    # Target note densities (notes per second) for each difficulty
    TARGET_DENSITIES = {
        "EASY": 0.8,      # Very relaxed
        "MEDIUM": 1.5,    # Moderate challenge
        "HARD": 2.5,      # High challenge
        "EXTREME": 4.0    # Maximum challenge
    }
    
    # Tolerance for density matching (±10%)
    DENSITY_TOLERANCE = 0.1
    
    def __init__(self, target_difficulty: str):
        self.target_difficulty = target_difficulty
        self.target_density = self.TARGET_DENSITIES.get(target_difficulty, 1.5)
        self.max_iterations = 5
          def analyze_song_characteristics(self, y, sr, tempo: float) -> Dict[str, float]:
        """
        Analyze song characteristics that affect note generation.
        """
        try:
            import librosa
            import numpy as np
            
            # Calculate audio characteristics
            rms = np.mean(librosa.feature.rms(y=y)[0])
            
            # Spectral characteristics
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)[0])
            
            # Harmonic vs percussive content
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            percussive_ratio = np.sum(y_percussive**2) / (np.sum(y**2) + 1e-10)
            
            # Onset density (raw)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            raw_onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, 
                                                   threshold=0.1, pre_max=3, post_max=3)
            raw_density = len(raw_onsets) / (len(y) / sr) if len(y) > 0 else 0
            
            return {
                'tempo': tempo,
                'rms_energy': rms,
                'spectral_centroid': spectral_centroid,
                'spectral_rolloff': spectral_rolloff,
                'percussive_ratio': percussive_ratio,
                'raw_onset_density': raw_density,
                'duration': len(y) / sr
            }
            
        except Exception as e:
            logger.error(f"Error analyzing song characteristics: {e}")
            return {
                'tempo': tempo,
                'rms_energy': 0.1,
                'spectral_centroid': 2000,
                'spectral_rolloff': 4000,
                'percussive_ratio': 0.5,
                'raw_onset_density': 2.0,
                'duration': len(y) / sr if len(y) > 0 else 180
            }
    
    def calculate_adaptive_parameters(self, characteristics: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate adaptive parameters based on song characteristics and target difficulty.
        """
        # Base parameters
        base_threshold = 0.3
        base_spacing = 60.0 / (characteristics['tempo'] * 2)  # Half-beat spacing
        
        # Calculate density ratio (how much we need to reduce/increase)
        raw_density = characteristics['raw_onset_density']
        density_ratio = self.target_density / max(raw_density, 0.1)
        
        # Adaptive threshold adjustment
        # Higher threshold = fewer notes, lower threshold = more notes
        if density_ratio < 1.0:  # Need fewer notes
            threshold_multiplier = 1.0 / density_ratio
        else:  # Need more notes
            threshold_multiplier = density_ratio
            
        # Spacing adjustment
        # Larger spacing = fewer notes, smaller spacing = more notes
        if density_ratio < 1.0:  # Need fewer notes
            spacing_multiplier = 1.0 / density_ratio
        else:  # Need more notes
            spacing_multiplier = density_ratio
            
        # Genre-specific adjustments
        percussive_ratio = characteristics['percussive_ratio']
        
        # For highly percussive music (drums, electronic), be more aggressive
        if percussive_ratio > 0.7:
            threshold_multiplier *= 1.2
            
        # For low-energy music, be more conservative
        if characteristics['rms_energy'] < 0.05:
            threshold_multiplier *= 0.8
            
        return {
            'threshold_multiplier': threshold_multiplier,
            'spacing_multiplier': spacing_multiplier,
            'density_ratio': density_ratio,
            'base_threshold': base_threshold,
            'base_spacing': base_spacing
        }
    
    def generate_adaptive_notes(self, y, sr, tempo: float, optimized_bands: List[Tuple[int, int]], 
                              use_midi: bool = False) -> List[Dict[str, Any]]:
        """
        Generate notes with adaptive difficulty adjustment.
        Uses iterative refinement to hit target density.
        """
        characteristics = self.analyze_song_characteristics(y, sr, tempo)
        
        logger.info(f"Song characteristics: tempo={tempo}, percussive_ratio={characteristics['percussive_ratio']:.2f}, "
                   f"raw_density={characteristics['raw_onset_density']:.2f}")
        
        notes = []
        iteration = 0
        
        while iteration < self.max_iterations:
            params = self.calculate_adaptive_parameters(characteristics)
            
            logger.info(f"Iteration {iteration + 1}: threshold_mult={params['threshold_multiplier']:.2f}, "
                       f"spacing_mult={params['spacing_multiplier']:.2f}")
            
            # Generate notes with current parameters
            notes = self._generate_notes_with_params(y, sr, tempo, optimized_bands, params)
            
            # Calculate actual density
            if notes:
                duration = characteristics['duration']
                actual_density = len(notes) / duration
                density_error = abs(actual_density - self.target_density) / self.target_density
                
                logger.info(f"Generated {len(notes)} notes, density={actual_density:.2f}, "
                           f"target={self.target_density:.2f}, error={density_error:.1%}")
                
                # Check if we're within tolerance
                if density_error <= self.DENSITY_TOLERANCE:
                    logger.info(f"Target density achieved in {iteration + 1} iterations")
                    break
                    
                # Adjust characteristics for next iteration
                characteristics['raw_onset_density'] = actual_density
            
            iteration += 1
            
        if iteration >= self.max_iterations:
            logger.warning(f"Max iterations reached. Final density: {len(notes) / characteristics['duration']:.2f}")
            
        return notes
    
    def _generate_notes_with_params(self, y, sr, tempo: float, optimized_bands: List[Tuple[int, int]], 
                                  params: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Generate notes using specific parameters.
        """
        try:
            import librosa
            
            # Apply threshold to onset detection
            threshold = params['base_threshold'] * params['threshold_multiplier']
            min_spacing = params['base_spacing'] * params['spacing_multiplier']
            
            # Detect onsets with adaptive parameters
            onsets_by_band = self._multi_band_onset_detection_adaptive(
                y, sr, optimized_bands, threshold
            )
            
            # Convert to notes with spacing filter
            notes = []
            start_offset = 3.0
            last_note_time = {i: 0 for i in range(len(optimized_bands))}
            
            for band_idx, band_onsets in enumerate(onsets_by_band):
                # Define note characteristics based on frequency band
                note_config = self._get_note_config(band_idx)
                
                for onset_time in band_onsets:
                    if onset_time >= start_offset:
                        if onset_time - last_note_time[band_idx] >= min_spacing:
                            note_time = round(onset_time, 2)
                            
                            notes.append({
                                'time': note_time,
                                'enemy_type': note_config['enemy_type'],
                                'color1': note_config['color1'],
                                'color2': note_config['color2'],
                                'aux': note_config['aux']
                            })
                            
                            last_note_time[band_idx] = onset_time
            
            # Sort by time
            notes.sort(key=lambda x: x['time'])
            
            return notes
            
        except Exception as e:
            logger.error(f"Error generating notes with parameters: {e}")
            return []
    
    def _multi_band_onset_detection_adaptive(self, y, sr, bands, base_threshold):
        """
        Adaptive multi-band onset detection.
        """
        try:
            import librosa
            
            onsets_by_band = []
            
            for band_idx, (low_freq, high_freq) in enumerate(bands):
                # Filter audio to band
                y_band = librosa.effects.remix(y, intervals=librosa.frequency_bands.frequency_filter(
                    y, sr, low_freq, high_freq))
                
                # Compute onset envelope
                onset_env = librosa.onset.onset_strength(y=y_band, sr=sr)
                
                # Band-specific threshold adjustment
                if low_freq < 150:
                    threshold = base_threshold * 1.33
                elif low_freq < 300:
                    threshold = base_threshold * 1.17
                elif low_freq < 1000:
                    threshold = base_threshold * 1.0
                else:
                    threshold = base_threshold * 0.83
                
                # Detect onsets
                onset_frames = librosa.onset.onset_detect(
                    onset_envelope=onset_env, sr=sr,
                    threshold=threshold,
                    pre_max=0.03*sr//512,
                    post_max=0.03*sr//512,
                    pre_avg=0.08*sr//512,
                    post_avg=0.08*sr//512
                )
                
                # Convert to time
                onset_times = librosa.frames_to_time(onset_frames, sr=sr)
                onsets_by_band.append(onset_times)
            
            return onsets_by_band
            
        except Exception as e:
            logger.error(f"Error in adaptive onset detection: {e}")
            return [[] for _ in bands]
    
    def _get_note_config(self, band_idx: int) -> Dict[str, int]:
        """
        Get note configuration for a frequency band.
        """
        configs = [
            {'enemy_type': 1, 'color1': 2, 'color2': 2, 'aux': 7},  # Kick drum
            {'enemy_type': 1, 'color1': 3, 'color2': 3, 'aux': 7},  # Low toms
            {'enemy_type': 1, 'color1': 2, 'color2': 2, 'aux': 7},  # Snare/mid toms
            {'enemy_type': 1, 'color1': 1, 'color2': 1, 'aux': 6},  # Hi-hats/cymbals
            {'enemy_type': 2, 'color1': 5, 'color2': 6, 'aux': 5},  # Rides/crashes
        ]
        
        return configs[min(band_idx, len(configs) - 1)]

from backend.processing.adaptive_notes_simple import generate_adaptive_notes_csv

# Regenerate with proper beat alignment
generate_adaptive_notes_csv(
    song_path="path/to/your/audio.mp3",
    midi_path=None,
    output_path="notes.csv", 
    target_difficulty="EASY"  # or MEDIUM, HARD, EXTREME
)
