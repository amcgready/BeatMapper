"""
Tools for testing the accuracy of note generation against MIDI references
"""
import os
import csv
import logging
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compare_notes(generated_path, reference_path, output_dir=None):
    """
    Compare generated notes against a reference file and report accuracy
    
    Args:
        generated_path: Path to generated notes.csv
        reference_path: Path to reference notes.csv
        output_dir: Directory to save comparison reports and plots
        
    Returns:
        dict: Comparison metrics
    """
    try:
        # Load both note files
        generated = load_note_times(generated_path)
        reference = load_note_times(reference_path)
        
        if not generated or not reference:
            logger.error("Failed to load note files")
            return {}
            
        # Get basic metrics
        gen_count = len(generated)
        ref_count = len(reference)
        
        logger.info(f"Comparing {gen_count} generated notes to {ref_count} reference notes")
        
        # Calculate timing precision
        matched_notes, unmatched_ref, unmatched_gen = match_notes(generated, reference)
        
        precision = len(matched_notes) / gen_count if gen_count > 0 else 0
        recall = len(matched_notes) / ref_count if ref_count > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        
        # Calculate timing error
        timing_errors = [abs(gen - ref) for gen, ref in matched_notes]
        avg_error = sum(timing_errors) / len(timing_errors) if timing_errors else 0
        max_error = max(timing_errors) if timing_errors else 0
        
        # Analyze by time regions
        region_metrics = analyze_by_region(generated, reference, region_size=10.0)
        
        # Generate visualizations if output_dir specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # Plot note distributions
            plot_path = os.path.join(output_dir, "note_comparison.png")
            plot_note_comparison(generated, reference, matched_notes, plot_path)
            
            # Write detailed report
            report_path = os.path.join(output_dir, "comparison_report.txt")
            write_report(
                report_path,
                gen_count, 
                ref_count, 
                precision, 
                recall, 
                f1_score,
                avg_error,
                max_error,
                region_metrics
            )
        
        # Print summary
        print("\n--- Note Generation Accuracy ---")
        print(f"Generated: {gen_count} notes")
        print(f"Reference: {ref_count} notes")
        print(f"Matched: {len(matched_notes)} notes")
        print(f"Precision: {precision:.2f}")
        print(f"Recall: {recall:.2f}")
        print(f"F1-Score: {f1_score:.2f}")
        print(f"Average timing error: {avg_error*1000:.1f}ms")
        print(f"Maximum timing error: {max_error*1000:.1f}ms")
        
        # Return metrics
        return {
            "generated_count": gen_count,
            "reference_count": ref_count,
            "matched_count": len(matched_notes),
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "avg_timing_error": avg_error,
            "max_timing_error": max_error,
            "region_metrics": region_metrics
        }
    
    except Exception as e:
        logger.error(f"Error comparing notes: {e}")
        return {}

def load_note_times(csv_path):
    """Load note times from a CSV file"""
    try:
        times = []
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            
            for row in reader:
                if len(row) > 0:
                    try:
                        time = float(row[0])
                        times.append(time)
                    except (ValueError, IndexError):
                        continue
                        
        return sorted(times)
    except Exception as e:
        logger.error(f"Failed to load note times from {csv_path}: {e}")
        return []

def match_notes(generated, reference, max_distance=0.1):
    """
    Match generated notes to reference notes
    
    Args:
        generated: List of generated note times
        reference: List of reference note times
        max_distance: Maximum time difference to consider a match (seconds)
        
    Returns:
        tuple: (matched_pairs, unmatched_reference, unmatched_generated)
    """
    matched_pairs = []
    unmatched_ref = set(reference)
    unmatched_gen = set(generated)
    
    # For each generated note, find closest reference note
    for gen_time in generated:
        best_match = None
        best_dist = float('inf')
        
        for ref_time in reference:
            dist = abs(gen_time - ref_time)
            if dist < best_dist:
                best_dist = dist
                best_match = ref_time
                
        # If we found a match within the threshold
        if best_match is not None and best_dist <= max_distance:
            matched_pairs.append((gen_time, best_match))
            
            # Remove from unmatched sets
            if gen_time in unmatched_gen:
                unmatched_gen.remove(gen_time)
            if best_match in unmatched_ref:
                unmatched_ref.remove(best_match)
    
    return matched_pairs, list(unmatched_ref), list(unmatched_gen)

def analyze_by_region(generated, reference, region_size=10.0):
    """Analyze accuracy by time regions"""
    if not generated or not reference:
        return {}
    
    # Get full time range
    min_time = min(min(generated), min(reference))
    max_time = max(max(generated), max(reference))
    
    region_metrics = {}
    
    # Analyze each region
    for start in np.arange(min_time, max_time, region_size):
        end = start + region_size
        
        # Get notes in this region
        gen_region = [t for t in generated if start <= t < end]
        ref_region = [t for t in reference if start <= t < end]
        
        # Skip empty regions
        if not gen_region and not ref_region:
            continue
            
        # Calculate metrics for this region
        matched, unmatched_ref, unmatched_gen = match_notes(gen_region, ref_region)
        
        precision = len(matched) / len(gen_region) if gen_region else 0
        recall = len(matched) / len(ref_region) if ref_region else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        
        region_metrics[f"{start:.1f}-{end:.1f}"] = {
            "generated": len(gen_region),
            "reference": len(ref_region),
            "matched": len(matched),
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        }
    
    return region_metrics

def plot_note_comparison(generated, reference, matched_pairs, output_path):
    """Create a visualization comparing note timing"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        
        plt.figure(figsize=(15, 6))
        
        # Extract matched times
        matched_gen = [g for g, r in matched_pairs]
        matched_ref = [r for g, r in matched_pairs]
        
        # Get unmatched notes
        all_matched_gen = set(matched_gen)
        all_matched_ref = set(matched_ref)
        
        unmatched_gen = [t for t in generated if t not in all_matched_gen]
        unmatched_ref = [t for t in reference if t not in all_matched_ref]
        
        # Plot reference notes (top)
        plt.plot(matched_ref, [1.2] * len(matched_ref), 'o', color='green', alpha=0.5, label='Matched Reference')
        plt.plot(unmatched_ref, [1.2] * len(unmatched_ref), 'o', color='red', alpha=0.5, label='Unmatched Reference')
        
        # Plot generated notes (bottom)
        plt.plot(matched_gen, [0.8] * len(matched_gen), 'o', color='green', alpha=0.5, label='Matched Generated')
        plt.plot(unmatched_gen, [0.8] * len(unmatched_gen), 'o', color='blue', alpha=0.5, label='Unmatched Generated')
        
        # Draw connecting lines for matches
        for gen, ref in matched_pairs:
            plt.plot([gen, ref], [0.8, 1.2], 'k-', alpha=0.1)
        
        # Set labels and title
        plt.yticks([0.8, 1.2], ['Generated', 'Reference'])
        plt.xlabel('Time (seconds)')
        plt.title('Note Timing Comparison')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Save figure
        plt.tight_layout()
        plt.savefig(output_path, dpi=100)
        plt.close()
        
        logger.info(f"Saved note comparison plot to {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to create plot: {e}")

def write_report(report_path, gen_count, ref_count, precision, recall, f1_score, 
                avg_error, max_error, region_metrics):
    """Write a detailed comparison report"""
    try:
        with open(report_path, 'w') as f:
            f.write("=== Note Generation Accuracy Report ===\n\n")
            f.write(f"Generated notes: {gen_count}\n")
            f.write(f"Reference notes: {ref_count}\n")
            f.write(f"Note difference: {gen_count - ref_count} ({abs(gen_count - ref_count)/ref_count*100:.1f}%)\n\n")
            
            f.write("--- Matching Metrics ---\n")
            f.write(f"Precision: {precision:.4f}\n")
            f.write(f"Recall: {recall:.4f}\n")
            f.write(f"F1-Score: {f1_score:.4f}\n\n")
            
            f.write("--- Timing Accuracy ---\n")
            f.write(f"Average timing error: {avg_error*1000:.2f}ms\n")
            f.write(f"Maximum timing error: {max_error*1000:.2f}ms\n\n")
            
            f.write("--- Region Analysis ---\n")
            for region, metrics in region_metrics.items():
                f.write(f"\nRegion {region}s:\n")
                f.write(f"  Generated: {metrics['generated']} notes\n")
                f.write(f"  Reference: {metrics['reference']} notes\n")
                f.write(f"  Matched: {metrics['matched']} notes\n")
                f.write(f"  Precision: {metrics['precision']:.4f}\n")
                f.write(f"  Recall: {metrics['recall']:.4f}\n")
                f.write(f"  F1-Score: {metrics['f1_score']:.4f}\n")
            
            f.write("\n=== End of Report ===\n")
            
        logger.info(f"Wrote comparison report to {report_path}")
        
    except Exception as e:
        logger.error(f"Failed to write report: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare note generation accuracy")
    parser.add_argument("generated", help="Path to generated notes.csv")
    parser.add_argument("reference", help="Path to reference notes.csv")
    parser.add_argument("-o", "--output-dir", help="Directory to save comparison reports and plots")
    
    args = parser.parse_args()
    
    compare_notes(args.generated, args.reference, args.output_dir)