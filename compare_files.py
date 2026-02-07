"""Compare quantization between two files."""

from audio.drum_analyzer import DrumAnalyzer

files = [
    ("UNQUANTIZED", "jh1-write-my-ticket-noQuant.mid"),
    ("QUANTIZED 1/16", "jh1-write-my-ticket-q116.mid")
]

print(f"\n{'='*80}")
print(f"COMPARISON: Unquantized vs Quantized (1/16 notes in Logic)")
print(f"{'='*80}\n")

for label, filename in files:
    print(f"{label}: {filename}")
    analyzer = DrumAnalyzer(filename)
    analysis = analyzer.analyze()
    
    timing = analysis['timing_quality']
    
    # Show snare and bass drum as examples
    for drum_name in ['Bass Drum 1', 'Acoustic Snare', 'Closed Hi-Hat']:
        if drum_name in timing:
            metrics = timing[drum_name]
            print(f"  {drum_name}:")
            print(f"    Grid detected: {metrics['grid_name']}")
            print(f"    Avg error: {metrics['abs_mean_error_ms']:.2f}ms")
            print(f"    Score: {metrics['timing_score']:.1f}")
    
    print()

print(f"{'='*80}")
print("ANALYSIS:")
print("If quantization worked, the QUANTIZED file should show:")
print("  1. Lower avg errors")
print("  2. Higher scores")
print("  3. Possibly finer grid detection (32nd, triplets)")
print(f"{'='*80}\n")
