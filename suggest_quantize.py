"""Suggest optimal quantization settings for a MIDI file."""

import sys
import mido
import numpy as np
from collections import defaultdict
from audio.drum_analyzer import DrumAnalyzer, DRUM_MAP


def suggest_quantization(midi_file: str):
    """Analyze MIDI file and suggest best quantization grid."""
    
    print(f"\n{'='*70}")
    print(f"QUANTIZATION ADVISOR")
    print(f"{'='*70}")
    print(f"Analyzing: {midi_file}\n")
    
    analyzer = DrumAnalyzer(midi_file)
    analysis = analyzer.analyze()
    
    # Get all drum beats
    beats = analysis['beats']
    if not beats:
        print("❌ No drum hits found in file!")
        return
    
    print(f"Found {len(beats)} drum hits")
    print(f"Tempo: {analysis['tempo_bpm']} BPM")
    print(f"Duration: {analysis['duration_seconds']}s\n")
    
    # Test all grid sizes
    grid_configs = [
        (1/8, '32nd notes', '1/32'),
        (1/6, '16th note triplets', '1/16T'),
        (0.25, '16th notes', '1/16'),
        (1/3, '8th note triplets', '1/8T'),
        (0.5, '8th notes', '1/8'),
        (1.0, 'quarter notes', '1/4'),
    ]
    
    # Calculate errors for each grid
    grid_results = []
    
    for grid_size, grid_name, logic_setting in grid_configs:
        total_error = 0
        hit_count = 0
        
        beat_duration_sec = mido.tick2second(
            analyzer.ticks_per_beat,
            analyzer.ticks_per_beat,
            analyzer.tempo
        )
        
        for beat in beats:
            beat_pos = beat['beat_position']
            pos_in_grid = beat_pos % grid_size
            
            # Find error
            if pos_in_grid <= grid_size / 2:
                error_beats = pos_in_grid
            else:
                error_beats = pos_in_grid - grid_size
            
            error_ms = abs(error_beats * beat_duration_sec * 1000)
            total_error += error_ms
            hit_count += 1
        
        avg_error = total_error / hit_count if hit_count > 0 else 0
        grid_results.append((avg_error, grid_size, grid_name, logic_setting))
    
    # Sort by error (best first)
    grid_results.sort(key=lambda x: x[0])
    
    print(f"{'Grid Analysis (sorted by fit):':-^70}\n")
    print(f"{'Grid':<25} {'Logic Setting':<15} {'Avg Error':<12} {'Quality'}")
    print(f"{'-'*70}")
    
    for i, (avg_error, grid_size, grid_name, logic_setting) in enumerate(grid_results):
        if i == 0:
            indicator = '★ BEST'
            quality = 'Perfect fit'
        elif i == 1:
            indicator = '✓ Good'
            quality = 'Also viable'
        else:
            indicator = '  '
            quality = 'Less ideal'
        
        print(f"{grid_name:<25} {logic_setting:<15} {avg_error:>7.2f}ms    {quality:<15} {indicator}")
    
    # Get the best technical fit (lowest error)
    best_error, best_size, best_name, best_logic = grid_results[0]
    
    # Get the musical fit (most common usable grids)
    # Prioritize 1/16, 1/16T, 1/8T, 1/8 as these are most common in music
    musical_grids = [(err, sz, nm, lg) for err, sz, nm, lg in grid_results 
                     if sz in [0.25, 1/6, 1/3, 0.5]]  # 16th, 16thT, 8thT, 8th
    
    if musical_grids:
        musical_error, musical_size, musical_name, musical_logic = musical_grids[0]
    else:
        musical_error, musical_size, musical_name, musical_logic = grid_results[0]
    
    print(f"\n{'='*70}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*70}\n")
    
    print(f"🎵 MUSICAL FIT (what the song is written in):")
    print(f"   Primary: {musical_name} ({musical_logic}) - {musical_error:.2f}ms error")
    
    # Show other close musical options
    if len(musical_grids) > 1:
        # Show alternatives that are within 50% of the best musical grid
        alternatives = [(e, n, l) for e, s, n, l in musical_grids[1:3] 
                       if e < musical_error * 1.5]
        if alternatives:
            print(f"   Also try: ", end="")
            print(", ".join([f"{n} ({l})" for e, n, l in alternatives]))
    
    print(f"   → Use for: Original song feel, keeping the groove intact")
    
    if best_logic != musical_logic:
        print(f"\n⚡ TECHNICAL BEST (tightest possible fit):")
        print(f"   Grid: {best_name}")
        print(f"   Logic Setting: {best_logic}")
        print(f"   Average Error: {best_error:.2f}ms")
        print(f"   → Use this for: Maximum precision, practice mode")
        print(f"   ⚠️  Note: This grid is finer than needed, may alter the feel")
    
    print(f"\n📋 Logic Pro Settings (Musical Fit):")
    print(f"   1. Select all MIDI notes (Cmd+A)")
    print(f"   2. Press 'Q' or go to: Edit → Quantize")
    print(f"   3. Set Grid: {musical_logic}")
    print(f"   4. Set Q-Strength: 80-100%")
    print(f"   5. Apply")
    
    print(f"\n📊 Expected Results (Musical Fit - {musical_logic}):")
    if musical_error < 10:
        print(f"   • Your timing is already quite good ({musical_error:.1f}ms error)")
        print(f"   • After quantization: Near-perfect (< 1ms)")
    elif musical_error < 20:
        print(f"   • Your timing is decent ({musical_error:.1f}ms error)")
        print(f"   • After quantization: Excellent (< 5ms)")
    elif musical_error < 30:
        print(f"   • Your timing needs work ({musical_error:.1f}ms error)")
        print(f"   • After quantization: Excellent (< 5ms)")
    else:
        print(f"   • Your timing is quite loose ({musical_error:.1f}ms error)")
        print(f"   • After quantization: Excellent (< 5ms)")
    
    print(f"\n💡 Which Should You Use?")
    print(f"   • {musical_logic} (Musical): Keep the original groove and feel")
    if best_logic != musical_logic:
        print(f"   • {best_logic} (Technical): Get tightest possible timing for practice")
    print(f"\n💡 Tips:")
    print(f"   • Most songs use: 1/16, 1/16T (triplets), 1/8, or 1/8T")
    print(f"   • Finer grids (1/32, 1/64) are rarely the actual musical grid")
    print(f"   • Start with 80% Q-Strength to preserve some human feel")
    print(f"   • Use 100% for analysis/practice where you want perfect timing")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python suggest_quantize.py <midi_file>")
        print("\nExample: python suggest_quantize.py my_drums.mid\n")
        sys.exit(1)
    
    suggest_quantization(sys.argv[1])
