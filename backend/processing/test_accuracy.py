"""
Tool to compare generated notes with MIDI reference files
"""
import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_notes(csv_path):
    """Load note times from CSV file"""
    times = []
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and len(row) > 0:
                try:
                    times.append(float(row[0]))
                except ValueError:
                    continue
    
    return sorted(times)

def analyze_notes(note_times):
    """Analyze timing patterns from notes"""
    if not note_times or len(note_times) < 2:
        return {}
    
    intervals = np.diff(note_times)
    
    analysis = {
        "count": len(note_times),
        "min_time": min(note_times),
        "max_time": max(note_times),
        "duration": max(note_times) - min(note_times),
        "min_interval": min(intervals),
        "max_interval": max(intervals),
        "mean_interval": np.mean(intervals),
        "median_interval": np.median(intervals),
        "std_interval": np.std(intervals),
        "timing_variation": np.std(intervals) / np.mean(intervals),
        "note_density": len(note_times) / (max(note_times) - min(note_times))
    }
    
    return analysis

def compare_notes(generated_path, reference_path, output_dir=None):
    """Compare generated notes with reference MIDI"""
    try:
        # Load both note sets
        gen_times = load_notes(generated_path)
        ref_times = load_notes(reference_path)
        
        if not gen_times or not ref_times:
            logger.error("Failed to load notes from one or both files")
            return False
        
        # Analyze timing patterns
        gen_analysis = analyze_notes(gen_times)
        ref_analysis = analyze_notes(ref_times)
        
        # Calculate similarity metrics
        similarity = {
            "count_difference": gen_analysis["count"] - ref_analysis["count"],
            "count_ratio": gen_analysis["count"] / ref_analysis["count"],
            "density_ratio": gen_analysis["note_density"] / ref_analysis["note_density"],
            "timing_variation_ratio": gen_analysis["timing_variation"] / ref_analysis["timing_variation"],
            "mean_interval_ratio": gen_analysis["mean_interval"] / ref_analysis["mean_interval"]
        }
        
        # Print comparison
        print("\n=== Note Generation Analysis ===\n")
        
        print("Count Comparison:")
        print(f"  Generated: {gen_analysis['count']} notes")
        print(f"  Reference: {ref_analysis['count']} notes")
        print(f"  Difference: {similarity['count_difference']} notes")
        print(f"  Ratio: {similarity['count_ratio']:.2f}x\n")
        
        print("Timing Comparison:")
        print(f"  Generated: {gen_analysis['mean_interval']:.3f}s avg interval, {gen_analysis['timing_variation']:.3f} variation")
        print(f"  Reference: {ref_analysis['mean_interval']:.3f}s avg interval, {ref_analysis['timing_variation']:.3f} variation\n")
        
        print("Density Comparison:")
        print(f"  Generated: {gen_analysis['note_density']:.2f} notes/sec")
        print(f"  Reference: {ref_analysis['note_density']:.2f} notes/sec")
        print(f"  Ratio: {similarity['density_ratio']:.2f}x\n")
        
        # Calculate match score (higher is better)
        match_score = (
            (1 - abs(1 - similarity['count_ratio'])) * 0.3 +
            (1 - abs(1 - similarity['density_ratio'])) * 0.3 +
            (1 - abs(1 - similarity['timing_variation_ratio'])) * 0.4
        ) * 100
        
        print(f"Overall Match Score: {match_score:.1f}%\n")
        
        # Create visualization if output directory provided
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # Create comparison chart
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Plot note distributions
            ax1.hist([gen_times, ref_times], bins=50, alpha=0.6, label=['Generated', 'Reference'])
            ax1.set_title('Note Distribution Over Time')
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Note Count')
            ax1.legend()
            
            # Plot interval distributions
            gen_intervals = np.diff(gen_times)
            ref_intervals = np.diff(ref_times)
            
            ax2.hist([gen_intervals, ref_intervals], bins=30, alpha=0.6, label=['Generated', 'Reference'])
            ax2.set_title('Note Interval Distribution')
            ax2.set_xlabel('Interval (s)')
            ax2.set_ylabel('Count')
            ax2.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'note_comparison.png'))
            logger.info(f"Saved comparison chart to {os.path.join(output_dir, 'note_comparison.png')}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error comparing notes: {e}")
        return False
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare generated notes with MIDI reference")
    parser.add_argument("generated_csv", help="Path to generated notes.csv")
    parser.add_argument("reference_csv", help="Path to reference MIDI notes.csv")
    parser.add_argument("--output-dir", help="Directory to save visualization charts")
    
    args = parser.parse_args()
    
    compare_notes(args.generated_csv, args.reference_csv, args.output_dir)