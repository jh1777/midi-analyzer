# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **MIDI drum timing analyzer** that measures drumming timing quality by comparing actual MIDI drum hits against a quantized tempo grid. It's designed to help drummers identify where their timing is tight vs. where they need improvement.

## Environment Setup

```bash
# Create and activate virtual environment (required)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run analyzer
python -m audio <midi_file.mid>
```

## Core Architecture

### Analysis Modes

The analyzer supports two complementary analysis modes:

1. **Grid-Based Analysis**: Measures absolute deviation from a perfect quantized grid. Best for validating quantized MIDI and strict tempo adherence.

2. **Groove-Aware Analysis**: Measures timing consistency relative to the player's established groove. Best for evaluating real human performances and identifying true timing problems vs. intentional feel.

### Grid-Based Timing Analysis Algorithm

The **grid-based quantization approach** uses these key steps:

1. **Tempo Map Construction**: Merges all MIDI tracks chronologically and builds a tempo map to handle tempo changes throughout the file. This is critical because MIDI files can have tempo changes, and processing tracks independently (the naive approach) misses tempo events in other tracks.

2. **Grid Detection**: Tests multiple grid resolutions (32nd notes, 16th triplets, 16th notes, 8th triplets, 8th notes, quarter notes) and selects the grid with the smallest total error for each drum type. This auto-detection handles different musical styles.

3. **Modulo-Based Quantization**: Uses `beat_position % grid_size` to find position within the grid. This is essential because MIDI files often have silence/other tracks at the beginning (drums might start at beat 1358), and we need to measure timing relative to the local grid, not absolute positions.

4. **Error Calculation**: 
   - For each hit, calculates timing error in milliseconds: positive = late (rushing), negative = early (dragging)
   - Computes statistics: mean error, absolute mean error, std deviation, error range
   - Generates timing score (0-100) and rating (Excellent/Good/Fair/Poor)

### Key Implementation Details

**`audio/drum_analyzer.py`**:
- `DrumAnalyzer.analyze()`: Main entry point that:
  - Merges all tracks with `all_messages = [(tick, msg), ...]`
  - Builds tempo map with `tempo_map = [(tick, tempo), ...]`
  - Defines `tick_to_seconds()` closure that converts ticks to seconds accounting for tempo changes
  - Only processes notes in `DRUM_MAP` (General MIDI drum notes 35-59)
  - Accepts `mode` parameter: `'grid-based'` (default) or `'groove-aware'`

- `DrumAnalyzer.calculate_timing_quality()`: Grid-based analysis algorithm that:
  - Groups beats by drum type
  - Tests each grid size and picks best fit
  - Uses modulo to find position within grid: `pos_in_grid = beat_position % grid_size`
  - Converts beat errors to milliseconds using tempo
  - Returns dict with metrics: `abs_mean_error_ms`, `timing_score`, `tendency`, etc.

- `DrumAnalyzer.calculate_groove_aware_quality()`: Groove-aware analysis algorithm that:
  - Detects natural groove offset from 8-16 stable hits
  - Uses median (outlier-resistant) from middle of performance
  - Subtracts groove offset from all hits
  - Measures consistency with IQR (interquartile range)
  - Identifies outliers using Tukey's fences (>1.5×IQR)
  - Returns dict with metrics: `groove_offset_ms`, `iqr_ms`, `outlier_percentage`, etc.

**Important**: The `beat_position` is calculated as `tick / ticks_per_beat` (absolute position from file start), but quantization uses modulo to handle files starting late. Don't modify this without understanding both calculations.

### Groove-Aware Timing Analysis Algorithm

The **groove-aware analysis** measures timing consistency, not absolute grid alignment. Key steps:

1. **Groove Offset Detection**:
   - Find most consistent drum type (lowest IQR, requires 16+ hits)
   - Priority order: Bass Drum 1 (35) > Acoustic Snare (38) > Closed Hi-Hat (42)
   - Extract middle stable region (skip first/last 10% of song to avoid intros/outros)
   - Take 8-16 consecutive hits from middle section
   - Calculate grid offsets for each hit using best-fit grid
   - Use **median** of offsets (robust to outliers) as groove reference

2. **Consistency Measurement**:
   - For each drum type, calculate grid offsets for all hits
   - Subtract detected groove offset from all offsets
   - Calculate **IQR** (interquartile range) = Q3 - Q1
   - IQR represents the spread of the middle 50% of hits (robust metric)

3. **Outlier Detection**:
   - Calculate Tukey's fences: `lower = Q1 - 1.5*IQR`, `upper = Q3 + 1.5*IQR`
   - Count hits outside these fences as outliers
   - Report outlier percentage

4. **Scoring**:
   - Based on IQR (consistency) rather than absolute error
   - <10ms IQR = Tight (90-100 score)
   - 10-20ms IQR = Good (70-90 score)
   - 20-30ms IQR = Fair (40-70 score)
   - ≥30ms IQR = Loose (0-40 score)

**Key Implementation Details**:

```python
def _detect_groove_offset(self, drum_beats, grid_size, tempo):
    """
    Detects groove offset using median of stable hits.
    Returns groove_offset_ms and reference_drum_name.
    """
    # Priority drums (most stable for reference)
    priority_drums = [35, 38, 42]  # Bass Drum 1, Acoustic Snare, Closed Hi-Hat
    
    # Find most consistent drum with enough hits
    for drum_note in priority_drums:
        if drum_note not in drum_beats or len(drum_beats[drum_note]) < 16:
            continue
        
        hits = drum_beats[drum_note]
        
        # Skip first/last 10% (intros/outros)
        total_duration = hits[-1] - hits[0]
        start_time = hits[0] + total_duration * 0.1
        end_time = hits[-1] - total_duration * 0.1
        
        stable_hits = [h for h in hits if start_time <= h <= end_time]
        if len(stable_hits) < 16:
            continue
        
        # Take middle 8-16 hits
        middle_start = len(stable_hits) // 2 - 4
        middle_end = middle_start + min(16, len(stable_hits) // 2)
        reference_hits = stable_hits[middle_start:middle_end]
        
        # Calculate offsets and use median
        offsets = self._calculate_grid_offsets(reference_hits, grid_size)
        groove_offset = np.median(offsets)  # Robust to outliers
        
        # Convert to milliseconds
        beat_duration_ms = (60.0 / tempo) * 1000.0
        groove_offset_ms = groove_offset * beat_duration_ms
        
        return groove_offset_ms, DRUM_MAP[drum_note]
    
    return None, None
```

**Why This Works**:
- **Median vs Mean**: A few mistimed hits won't affect the groove reference
- **IQR vs Std Dev**: Focuses on middle 50% of hits, ignoring extreme outliers
- **Middle Section**: Avoids intros/outros where timing is often different
- **Priority Drums**: Bass, snare, hi-hat are typically most consistent and define the groove

**Comparison Example** (jh3-DanaGlover-70pbm.mid):
- Grid-based: Measures 26-29ms absolute error → Score 50-58 (Acceptable)
- Groove-aware: Detects 34.9ms laid-back groove, measures 33ms IQR → Score 43-47 (Fair)
- Interpretation: Player has consistent laid-back feel (34.9ms late) but with ±33ms variation around that groove

## Testing and Validation

**Validating Timing Calculations**:
```bash
# Use debug scripts to verify calculations
python debug_timing.py        # Shows sample timing for one file
python debug_detailed.py      # Shows detailed beat-by-beat analysis
python compare_files.py       # Compares two files side-by-side
```

**Testing with Known-Good Data**:
- Real performances typically show 20-50ms avg error (Poor/Needs Work)
- Quantized MIDI should show <10ms avg error (Good/Excellent)
- If ALL files show identical ~30ms errors regardless of quantization, the algorithm is likely wrong

**Common Issues**:
- If timing scores are always poor, check that modulo-based quantization is working (`pos_in_grid = beat_position % grid_size`)
- If tempo seems wrong, verify tempo map is being built from all tracks, not just drum track
- If beat positions look huge (>1000), this is normal - don't "fix" it; the modulo handles it

## Code Style

- Line length: 100 characters (configured in `pyproject.toml`)
- Formatter: black (optional dev dependency)
- Linter: ruff (optional dev dependency)
- Target: Python 3.8+

## Running Tests

```bash
# Note: Test suite is minimal - use debug scripts for validation
pytest

# Run with output
pytest -v
```

## Key Dependencies

- **mido**: MIDI file parsing and tempo/tick conversions
- **numpy**: Statistical calculations (mean, std, percentiles)
- Both are required dependencies in `requirements.txt`

## Module Structure

```
audio/
├── __init__.py              # Package version
├── __main__.py              # Allows `python -m audio` execution
├── main.py                  # CLI entry point, arg parsing
├── drum_analyzer.py         # Core analysis logic (700+ lines)
│   ├── DRUM_MAP             # General MIDI drum note mapping (dict)
│   ├── DrumAnalyzer         # Main analyzer class
│   │   ├── __init__()
│   │   ├── analyze()        # Parses MIDI, builds tempo map, extracts beats
│   │   ├── calculate_timing_quality()        # Grid-based analysis
│   │   ├── calculate_groove_aware_quality()  # Groove-aware analysis
│   │   ├── _detect_groove_offset()           # Find natural groove
│   │   ├── _calculate_grid_offsets()         # Helper for offsets
│   │   └── print_summary()                   # Formatted console output
│   └── analyze_midi_drums()  # Convenience function
└── playalong_compare.py     # Audio-to-MIDI comparison (optional)

Web UI:
├── api_server.py            # FastAPI backend
└── web-ui/                  # React + TypeScript frontend
```

## Design Decisions

1. **Why merge all tracks?** MIDI files often split tempo events and drum events into separate tracks. Processing tracks independently causes incorrect timing when tempo changes occur.

2. **Why test multiple grid sizes?** Different songs use different subdivisions (straight 16ths vs. triplets vs. 32nds). Auto-detection finds the best fit rather than forcing one grid.

3. **Why modulo for quantization?** MIDI files can have arbitrary amounts of silence before drums start. Without modulo, we'd measure error relative to beat 0 instead of the local grid.

4. **Why not filter out large gaps?** Earlier versions tried to filter breaks/interludes, but grid-based quantization handles this naturally - each hit is evaluated independently.

5. **Why two analysis modes?** Grid-based analysis showed constant ~30ms offset for musically tight performances because it measures absolute deviation, not consistency. Groove-aware mode addresses this by first detecting the player's natural groove, then measuring consistency around that groove. This reveals true timing problems (inconsistency) vs. intentional feel (laid-back/pushed grooves).

6. **Why use median for groove detection?** The median is robust to outliers - a few mistimed hits won't skew the groove reference. Using mean would be affected by outliers.

7. **Why use IQR instead of standard deviation?** IQR (interquartile range) is also robust to outliers and focuses on the middle 50% of hits, which better represents consistent playing. Standard deviation is affected by extreme outliers.

8. **Why skip first/last 10% of song?** Intros and outros often have different feel or sparse hits. The middle section represents stable, consistent playing where the player has settled into their groove.

## Future Enhancement Ideas

The codebase is functional but could be extended:
- Add visualization (plot timing errors over time)
- Export results to JSON/CSV
- Support for tempo detection from audio files
- Analysis of velocity consistency
- Pattern recognition (e.g., identify repeated fills)
