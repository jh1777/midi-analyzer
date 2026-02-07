"""Detailed debug of quantization."""

import mido
from audio.drum_analyzer import DrumAnalyzer

midi_file = "jh1-SKelly-HoldOnLove.mid"
analyzer = DrumAnalyzer(midi_file)
analysis = analyzer.analyze()

print(f"\n{'='*70}")
print(f"Detailed Timing Analysis")
print(f"{'='*70}\n")

# Look at first 10 Open Hi-Hat hits
hihat_beats = [b for b in analysis['beats'] if b['drum'] == 'Open Hi-Hat'][:10]

print(f"First 10 Open Hi-Hat hits:")
print(f"{'Beat Pos':<12} {'Mod 0.25':<12} {'Error (beats)':<16} {'Error (ms)':<12}")
print(f"{'-'*70}")

beat_duration_sec = mido.tick2second(analyzer.ticks_per_beat, analyzer.ticks_per_beat, analyzer.tempo)
print(f"\n1 beat = {beat_duration_sec:.4f}s = {beat_duration_sec*1000:.2f}ms\n")

for beat in hihat_beats:
    beat_pos = beat['beat_position']
    
    # Try with 16th notes (0.25 grid)
    grid_size = 0.25
    pos_in_grid = beat_pos % grid_size
    
    # Find error
    if pos_in_grid <= grid_size / 2:
        error_beats = pos_in_grid
    else:
        error_beats = pos_in_grid - grid_size
    
    error_ms = error_beats * beat_duration_sec * 1000
    
    print(f"{beat_pos:<12.4f} {pos_in_grid:<12.4f} {error_beats:<16.4f} {error_ms:<12.2f}")

# Show what "good" timing would look like
print(f"\n{'='*70}")
print(f"For reference, 'good' timing on a 16th note grid:")
print(f"  Perfect: 1358.0000, 1358.2500, 1358.5000, 1358.7500, 1359.0000...")
print(f"  Acceptable: ±0.01 beats (±5ms)")
print(f"  The actual first hit: 1358.0083 (off by 0.0083 beats = {0.0083 * beat_duration_sec * 1000:.2f}ms)")
print(f"{'='*70}\n")
