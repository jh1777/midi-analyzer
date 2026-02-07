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

### Timing Analysis Algorithm

The analyzer uses a **grid-based quantization approach** with these key steps:

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

- `DrumAnalyzer.calculate_timing_quality()`: Core algorithm that:
  - Groups beats by drum type
  - Tests each grid size and picks best fit
  - Uses modulo to find position within grid: `pos_in_grid = beat_position % grid_size`
  - Converts beat errors to milliseconds using tempo
  - Returns dict with metrics: `abs_mean_error_ms`, `timing_score`, `tendency`, etc.

**Important**: The `beat_position` is calculated as `tick / ticks_per_beat` (absolute position from file start), but quantization uses modulo to handle files starting late. Don't modify this without understanding both calculations.

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
├── __init__.py          # Package version
├── __main__.py          # Allows `python -m audio` execution
├── main.py              # CLI entry point, arg parsing
└── drum_analyzer.py     # Core analysis logic (500+ lines)
    ├── DRUM_MAP         # General MIDI drum note mapping (dict)
    ├── DrumAnalyzer     # Main analyzer class
    │   ├── __init__()
    │   ├── analyze()    # Parses MIDI, builds tempo map, extracts beats
    │   ├── calculate_timing_quality()  # Grid-based quantization analysis
    │   └── print_summary()             # Formatted console output
    └── analyze_midi_drums()  # Convenience function
```

## Design Decisions

1. **Why merge all tracks?** MIDI files often split tempo events and drum events into separate tracks. Processing tracks independently causes incorrect timing when tempo changes occur.

2. **Why test multiple grid sizes?** Different songs use different subdivisions (straight 16ths vs. triplets vs. 32nds). Auto-detection finds the best fit rather than forcing one grid.

3. **Why modulo for quantization?** MIDI files can have arbitrary amounts of silence before drums start. Without modulo, we'd measure error relative to beat 0 instead of the local grid.

4. **Why not filter out large gaps?** Earlier versions tried to filter breaks/interludes, but grid-based quantization handles this naturally - each hit is evaluated independently.

## Future Enhancement Ideas

The codebase is functional but could be extended:
- Add visualization (plot timing errors over time)
- Export results to JSON/CSV
- Support for tempo detection from audio files
- Analysis of velocity consistency
- Pattern recognition (e.g., identify repeated fills)
