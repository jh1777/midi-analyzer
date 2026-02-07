"""Debug script to inspect timing calculations."""

import mido
from audio.drum_analyzer import DrumAnalyzer

# Test with one of the MIDI files
midi_file = "jh1-SKelly-HoldOnLove.mid"

analyzer = DrumAnalyzer(midi_file)

print(f"\n{'='*60}")
print(f"DEBUG: Analyzing {midi_file}")
print(f"{'='*60}")

# Get basic info
print(f"\nTempo (microseconds per beat): {analyzer.tempo}")
bpm = mido.tempo2bpm(analyzer.tempo)
print(f"BPM: {bpm:.2f}")
print(f"Ticks per beat: {analyzer.ticks_per_beat}")

# Run analysis
analysis = analyzer.analyze()

print(f"\nTotal beats: {analysis['total_beats']}")
print(f"Duration: {analysis['duration_seconds']}s")

# Look at first few beats
print(f"\n{'First 5 beats:':-^60}")
for i, beat in enumerate(analysis['beats'][:5]):
    print(f"{i+1}. Time: {beat['time_seconds']:.4f}s, Beat pos: {beat['beat_position']:.4f}, "
          f"Drum: {beat['drum']}, Vel: {beat['velocity']}")

# Check timing quality for one drum
timing_quality = analysis['timing_quality']
if timing_quality:
    print(f"\n{'Sample Timing Calculation:':-^60}")
    # Pick the first drum with data
    sample_drum = list(timing_quality.keys())[0]
    metrics = timing_quality[sample_drum]
    
    print(f"\nDrum: {sample_drum}")
    print(f"  Hit count: {metrics['hit_count']}")
    print(f"  Best grid: {metrics['grid_name']} ({metrics['grid_size']} beats)")
    print(f"  Mean error: {metrics['mean_error_ms']:.2f}ms")
    print(f"  Abs mean error: {metrics['abs_mean_error_ms']:.2f}ms")
    print(f"  Std dev: {metrics['std_dev_ms']:.2f}ms")
    print(f"  Error range: {metrics['max_early_ms']:.2f}ms to {metrics['max_late_ms']:.2f}ms")
    print(f"  Score: {metrics['timing_score']:.1f}")
    print(f"  Rating: {metrics['rating']}")
    print(f"  Tendency: {metrics['tendency']}")
    
    # Show what score should be based on error
    error = metrics['abs_mean_error_ms']
    print(f"\n  Expected score for {error:.2f}ms error:")
    if error < 5:
        expected = 100 - error * 2
        print(f"    Should be: {expected:.1f} (Excellent)")
    elif error < 10:
        expected = 90 - (error - 5) * 4
        print(f"    Should be: {expected:.1f} (Good)")
    elif error < 20:
        expected = 70 - (error - 10) * 3
        print(f"    Should be: {expected:.1f} (Fair)")
    else:
        print(f"    Should be: <40 (Poor)")

print(f"\n{'='*60}\n")
