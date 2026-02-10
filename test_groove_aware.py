#!/usr/bin/env python3
"""Compare grid-based vs groove-aware analysis."""

from audio.drum_analyzer import DrumAnalyzer

midi_file = './mid-files/jh3-DanaGlover-70pbm.mid'

print("="*80)
print("COMPARISON: Grid-Based vs Groove-Aware Analysis")
print("="*80)
print(f"File: {midi_file}\n")

# Analyze with both modes
analyzer = DrumAnalyzer(midi_file)
grid_analysis = analyzer.analyze(mode='grid-based')
groove_analysis = analyzer.analyze(mode='groove-aware')

print(f"Duration: {grid_analysis['duration_seconds']}s")
print(f"Tempo: {grid_analysis['tempo_bpm']} BPM")
print(f"Total Hits: {grid_analysis['total_beats']}")

# Get groove metadata
groove_meta = groove_analysis['timing_quality'].get('_groove_metadata', {})
print(f"\n🎵 Detected Groove: {groove_meta.get('groove_offset_ms', 0):.1f}ms offset")
print(f"   Reference: {groove_meta.get('reference_drum', 'N/A')}")

# Compare main drums
main_drums = ['Bass Drum 1', 'Acoustic Snare', 'Closed Hi-Hat']

print("\n" + "="*80)
print("GRID-BASED ANALYSIS (Old Method - Absolute Grid)")
print("="*80)
print(f"\n{'Drum':<20} {'Hits':>5} {'Error':>8} {'Score':>6} {'Rating':<12}")
print("-"*80)

for drum in main_drums:
    if drum in grid_analysis['timing_quality']:
        metrics = grid_analysis['timing_quality'][drum]
        print(f"{drum:<20} {metrics['hit_count']:>5} "
              f"{metrics['abs_mean_error_ms']:>7.1f}ms "
              f"{metrics['timing_score']:>6.1f} "
              f"{metrics['rating']:<12}")

print("\n" + "="*80)
print("GROOVE-AWARE ANALYSIS (New Method - Relative to Groove)")
print("="*80)
print(f"\n{'Drum':<20} {'Hits':>5} {'IQR':>8} {'Score':>6} {'Rating':<12}")
print("-"*80)

for drum in main_drums:
    if drum in groove_analysis['timing_quality']:
        metrics = groove_analysis['timing_quality'][drum]
        iqr = metrics.get('iqr_ms', metrics.get('std_dev_ms', 0))
        print(f"{drum:<20} {metrics['hit_count']:>5} "
              f"{iqr:>7.1f}ms "
              f"{metrics['timing_score']:>6.1f} "
              f"{metrics['rating']:<12}")

print("\n" + "="*80)
print("KEY DIFFERENCES")
print("="*80)
print("""
Grid-Based:
  - Measures absolute distance from DAW grid
  - Penalizes e-drum latency and "laid back" feel
  - Typical scores: 50-65 (Acceptable/Fair)
  - Error metric: How far from grid

Groove-Aware:
  - Measures consistency relative to YOUR groove
  - Eliminates constant offsets (latency, feel)
  - Typical scores: 40-85 (depends on consistency)
  - IQR metric: How tight/loose your groove is

🎯 The ~35ms constant offset is now recognized as YOUR GROOVE!
   What matters is: How consistently do you maintain that groove?
""")

print("="*80)
print("DETAILED COMPARISON")
print("="*80)

for drum in main_drums:
    if drum not in grid_analysis['timing_quality']:
        continue
        
    grid = grid_analysis['timing_quality'][drum]
    groove = groove_analysis['timing_quality'][drum]
    
    print(f"\n📊 {drum}:")
    print(f"   Grid-Based:")
    print(f"     - Error: {grid['abs_mean_error_ms']:.1f}ms (from grid)")
    print(f"     - Score: {grid['timing_score']:.1f} ({grid['rating']})")
    print(f"     - Std Dev: {grid['std_dev_ms']:.1f}ms")
    
    print(f"   Groove-Aware:")
    print(f"     - IQR: {groove.get('iqr_ms', 0):.1f}ms (consistency)")
    print(f"     - Score: {groove['timing_score']:.1f} ({groove['rating']})")
    print(f"     - Tendency: {groove['tendency']}")
    
    # Interpretation
    improvement = groove['timing_score'] - grid['timing_score']
    if improvement > 10:
        print(f"   ✅ MUCH BETTER with groove-aware! (+{improvement:.1f} points)")
        print(f"      Your groove is consistent - that 'error' was actually feel!")
    elif improvement > 0:
        print(f"   ✓ Better with groove-aware (+{improvement:.1f} points)")
    else:
        print(f"   ⚠️  Similar or lower score ({improvement:+.1f} points)")
        print(f"      This means inconsistency, not just offset")

print("\n" + "="*80)
