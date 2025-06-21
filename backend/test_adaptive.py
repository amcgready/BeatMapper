#!/usr/bin/env python3
"""
Test the adaptive difficulty system directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processing.adaptive_difficulty import AdaptiveDifficultyEngine

def test_adaptive_system():
    print("=== TESTING ADAPTIVE DIFFICULTY SYSTEM ===")
    
    # Test different difficulties
    for difficulty in ["EASY", "MEDIUM", "HARD", "EXTREME"]:
        engine = AdaptiveDifficultyEngine(difficulty)
        print(f"{difficulty}: target density = {engine.target_density:.2f} notes/sec")
    
    # Test characteristics analysis
    engine = AdaptiveDifficultyEngine("EASY")
    
    # Mock audio data
    import numpy as np
    sr = 22050
    duration = 10  # 10 seconds
    y = np.random.random(sr * duration) * 0.1  # Low energy mock audio
    tempo = 120.0
    
    characteristics = engine.analyze_song_characteristics(y, sr, tempo)
    print(f"\nMock song characteristics:")
    for key, value in characteristics.items():
        print(f"  {key}: {value:.3f}")
    
    params = engine.calculate_adaptive_parameters(characteristics)
    print(f"\nAdaptive parameters for EASY:")
    for key, value in params.items():
        print(f"  {key}: {value:.3f}")
    
    print("\n✓ Adaptive system test completed")

if __name__ == "__main__":
    test_adaptive_system()
