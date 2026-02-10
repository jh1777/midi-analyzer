# MIDI Drum Timing Analyzer - Development Summary

**Project**: Python-based MIDI drum timing analysis tool for drummers  
**Location**: `/Users/joerg/Development/python/audio`  
**Created**: February 7, 2026

---

## Project Overview

A MIDI drum timing analyzer that measures drumming timing quality by comparing actual MIDI drum hits against a quantized tempo grid. Helps drummers identify where their timing is tight vs. where they need improvement.

### Core Capabilities

1. **Timing Analysis**: Measures timing deviation from perfect grid in milliseconds
2. **Grid Auto-Detection**: Tests multiple grid resolutions (32nd, 16th triplets, 16th, 8th triplets, 8th, quarter notes)
3. **Scoring System**: 0-100 score with ratings (Excellent/Good/Fair/Needs Work/Poor)
4. **Quantization Advisor**: Suggests optimal Logic Pro quantization settings
5. **File Comparison**: Compare unquantized vs quantized files

---

## Project Structure

```
audio/
├── __init__.py              # Package version
├── __main__.py              # Module execution entry point
├── main.py                  # CLI entry point
└── drum_analyzer.py         # Core analysis logic (~500 lines)

Root directory scripts:
├── debug_timing.py          # Quick timing analysis for debugging
├── debug_detailed.py        # Detailed beat-by-beat analysis
├── compare_files.py         # Compare two MIDI files side-by-side
└── suggest_quantize.py      # Quantization advisor for Logic Pro

Documentation:
├── README.md                # User-facing documentation
├── AGENTS.md                # AI agent guidance (architecture & design decisions)
└── DEVELOPMENT_SUMMARY.md   # This file - comprehensive development history
```

---

## Core Algorithm: Grid-Based Quantization

### Key Design Decisions

#### 1. **Tempo Map with Merged Tracks**
**Problem**: MIDI files often split tempo changes and drum events into separate tracks.

**Solution**: Merge all tracks chronologically before processing:
```python
all_messages = []
for track in self.midi.tracks:
    tick = 0
    for msg in track:
        tick += msg.time
        all_messages.append((tick, msg))
all_messages.sort(key=lambda x: x[0])
```

**Why**: Processing tracks independently misses tempo changes in other tracks, causing incorrect timing calculations.

#### 2. **Modulo-Based Quantization**
**Problem**: MIDI files can have arbitrary silence/data before drums start (drums might start at beat 1358).

**Solution**: Use modulo to find position within grid:
```python
pos_in_grid = beat_position % grid_size
if pos_in_grid <= grid_size / 2:
    error_beats = pos_in_grid
else:
    error_beats = pos_in_grid - grid_size
```

**Why**: Without modulo, we'd measure error relative to beat 0 instead of the local grid pattern.

#### 3. **Multi-Grid Testing**
**Problem**: Different songs use different subdivisions (straight 16ths vs triplets vs 32nds).

**Solution**: Test all common grids and select the one with smallest total error:
- 32nd notes (1/8 beat)
- 16th triplets (1/6 beat)
- 16th notes (0.25 beat)
- 8th triplets (1/3 beat)
- 8th notes (0.5 beat)
- Quarter notes (1.0 beat)

**Why**: Auto-detection finds the best fit rather than forcing one grid.

#### 4. **Grid-Based vs Interval-Based Analysis**
**Early Approach**: Calculate intervals between consecutive hits → Calculate statistics on intervals.

**Problem**: This approach penalized breaks, interludes, and musical structure changes. All real songs showed "Poor" timing.

**Final Approach**: Compare each hit independently to nearest grid position.

**Why**: Each hit is evaluated on its own merit, naturally handling breaks and variations in musical structure.

---

## Development History & Key Learnings

### Phase 1: Initial Implementation
- Created basic MIDI parser using `mido`
- Implemented interval-based timing analysis
- Problem: ALL files showed poor timing (~30ms errors)

### Phase 2: First Iteration - Gap Filtering
- Attempted to filter out large gaps (breaks, interludes)
- Used IQR and median to detect "active playing" sections
- Problem: Still showed inconsistent results, over-complicated

### Phase 3: Grid-Based Quantization (Breakthrough)
- Switched to grid-based quantization approach
- Each hit compared to nearest grid position
- Problem: Still showing poor results

### Phase 4: Critical Bug Fix - Tempo Map
- **Bug**: Tracks processed independently, missing tempo changes
- **Fix**: Merged all tracks chronologically, built tempo map
- Result: Tempo tracking works correctly

### Phase 5: Critical Bug Fix - Modulo Quantization
- **Bug**: Files starting late (beat 1358+) showed poor timing
- **Fix**: Added modulo operation for grid position
- Result: Now works with files starting at any beat position

### Phase 6: Validation with Real Data
- Created test files:
  - `jh1-write-my-ticket-noQuant.mid` (human performance)
  - `jh1-write-my-ticket-q116.mid` (quantized to 1/16)
- Results:
  - Unquantized: ~30ms error, Score 23-24 (Needs Work)
  - Quantized: <0.5ms error, Score 99+ (Excellent)
- **Validation Complete**: Tool works perfectly!

### Phase 7: Enhancement - Quantization Advisor
- Created `suggest_quantize.py` script
- Shows both "musical fit" (what song is written in) and "technical best" (lowest error)
- Gives Logic Pro specific instructions

### Phase 8: Web UI Implementation
- Created FastAPI backend (`api_server.py`)
- Created React + TypeScript frontend (`web-ui/`)
- Features: sortable table, file analysis, configuration
- Startup script: `start.sh` for easy launching

### Phase 9: Play-Along Comparison Feature
- Implemented audio-to-MIDI comparison (`audio/playalong_compare.py`)
- Multi-band onset detection (percussive, low-freq, high-freq)
- Tempo correction and two-stage alignment
- CLI tool: `compare_playalong.py`
- Dependencies: librosa, scipy
- Real-world match rates: 60-80% (limited by audio stem quality)

### Phase 10: UI Enhancements - Weighted Metrics
- Added "Avg Timing" column (weighted mean absolute error)
- Added "Tendency" column (percentage early/late or centered)
- Added "Consistency" column (weighted std dev with ratings)
- All metrics weighted by hit count
- Color-coded ratings for visual clarity

### Phase 11: Groove-Aware Analysis Implementation
**Problem**: Grid-based analysis showed constant ~30ms offset for musically tight performances because it measures absolute deviation from grid, not consistency.

**Solution**: Implemented new analysis mode that measures timing consistency relative to the player's established groove.

**Implementation**:
- New function: `calculate_groove_aware_quality()` in `drum_analyzer.py`
- Detects natural groove offset using 8-16 stable hits from middle of performance
- Uses median for outlier resistance (skips first/last 10% of song)
- Measures consistency with IQR (interquartile range)
- Priority drums for reference: Bass Drum 1 > Acoustic Snare > Closed Hi-Hat

**UI Integration**:
- Two-button toggle in web UI (🎵 Groove-Aware / 📏 Grid-Based)
- Global `ANALYSIS_MODE` in backend
- Endpoint: `POST /config/analysis-mode`
- Re-analyzes all files when mode changes

**Test Results** (jh3-DanaGlover-70pbm.mid):
- Grid-based: 26-29ms error → scores 50-58 (Acceptable)
- Groove-aware: 34.9ms groove offset detected, 33ms IQR → scores 43-47 (Fair)
- Lower groove-aware scores correctly identify timing inconsistency (±33ms variation)

**Documentation Created**:
- `GROOVE_AWARE_ANALYSIS.md`: Full technical documentation
- `test_groove_aware.py`: Comparison test script

---

## Scripts and Their Purposes

### Main Application
**Usage**: `python -m audio <midi_file.mid>`

Analyzes MIDI file and displays:
- Duration, tempo (BPM), total hits
- Drum breakdown by type
- Timing quality analysis with scores per drum
- Detailed statistics for drums needing work
- First 10 beats sample

### Debug Scripts

#### `debug_timing.py`
Quick analysis for one file showing:
- Basic file info (tempo, ticks per beat, total beats)
- First 5 beats
- Sample timing calculation for one drum
- Expected score calculation

**Usage**: `python debug_timing.py`

#### `debug_detailed.py`
Shows detailed beat-by-beat quantization:
- First 10 hits of a specific drum
- Beat position, modulo result, error in beats and ms
- What "good" timing would look like

**Usage**: `python debug_detailed.py`

#### `compare_files.py`
Compares two MIDI files side-by-side:
- Shows key drums (bass, snare, hi-hat)
- Grid detected, avg error, score for each
- Perfect for validating quantization worked

**Usage**: `python compare_files.py`  
**Note**: Edit file to set which files to compare

### Quantization Advisor

#### `suggest_quantize.py`
Analyzes playing and suggests Logic Pro quantization settings:
- Tests all grid sizes, ranks by fit
- Shows "Musical Fit" (1/16, 1/16T, 1/8, etc.)
- Shows "Technical Best" (lowest error, often finer grid)
- Gives step-by-step Logic Pro instructions
- Explains expected results

**Usage**: `python suggest_quantize.py <midi_file.mid>`

**Output Example**:
```
🎵 MUSICAL FIT:
   Primary: 16th notes (1/16) - 30.70ms error
   Also try: 16th note triplets (1/16T)
   
⚡ TECHNICAL BEST:
   Grid: 32nd notes (1/32) - 15.55ms error
   → Use for: Maximum precision, practice mode
```

---

## Scoring System

### Timing Score (0-100)

Based on absolute mean error in milliseconds:
- **<5ms**: 90-100 (Excellent) - Studio quality
- **5-10ms**: 70-90 (Good) - Tight drumming
- **10-20ms**: 40-70 (Fair) - Acceptable
- **20-40ms**: 10-40 (Needs Work) - Noticeable drift
- **>40ms**: 0-10 (Poor) - Practice with metronome

### Real-World Expectations
- **Human performances**: Typically 20-50ms avg error (Fair/Needs Work)
- **Quantized MIDI**: <5ms avg error (Good/Excellent)
- **Perfect quantization**: <1ms avg error (Excellent, 99+ score)

---

## Testing & Validation Approach

### Test Files Used
1. **jh1-write-my-ticket-noQuant.mid** - Original human performance
2. **jh1-write-my-ticket-q116.mid** - Quantized to 1/16 notes in Logic Pro
3. **jh1-SKelly-HoldOnLove.mid** - Real song MIDI
4. **jh1-TBonham-AllThumbs.mid** - Real song MIDI
5. **jh1-faithHill-Love.mid** - Real song MIDI

### Validation Results
**Unquantized File**:
- Bass Drum: 30.40ms → Score 24.4
- Snare: 31.41ms → Score 22.9
- Hi-Hat: 31.08ms → Score 23.4

**Quantized File (1/16)**:
- Bass Drum: 0.43ms → Score 99.1 ✓
- Snare: 0.10ms → Score 99.8 ✓
- Hi-Hat: 0.07ms → Score 99.9 ✓

**Result**: 98%+ improvement, confirming tool accuracy!

---

## Common Issues & Solutions

### Issue 1: All Files Show Poor Timing
**Symptom**: Every file shows 30ms+ errors, even quantized ones.

**Diagnosis Steps**:
1. Check if modulo quantization is working (`pos_in_grid = beat_position % grid_size`)
2. Verify tempo map is being built from all tracks
3. Ensure tick_to_seconds() uses tempo map, not single tempo value

**Solution**: Implement proper tempo map tracking and modulo-based quantization.

### Issue 2: Huge Beat Positions (>1000)
**Symptom**: Beat positions like 1358.0083 instead of small numbers.

**Status**: This is NORMAL - MIDI files can have silence/other data before drums start.

**Solution**: Use modulo operation to find position within grid. Don't "fix" the beat position!

### Issue 3: Different Results for Same Song
**Symptom**: Different quantization settings in Logic Pro give different scores.

**Explanation**:
- **Musical Grid** (e.g., 1/16) = What the song is written in
- **Technical Best** (e.g., 1/32) = What minimizes human timing errors

**Solution**: Use Musical Grid (1/16, 1/16T, 1/8, 1/8T) for normal use. Technical Best is for analysis only.

---

## Key Implementation Details

### DRUM_MAP
General MIDI drum note mapping (notes 35-59):
- 35-36: Bass drums
- 38, 40: Snares
- 42, 44, 46: Hi-hats
- 49, 57: Crash cymbals
- 51, 59: Ride cymbals
- 41, 43, 45, 47, 48, 50: Toms

Only notes in DRUM_MAP are analyzed; others are ignored.

### Tempo Conversion
```python
# Build tempo map
tempo_map = [(0, default_tempo)]
for tick, msg in all_messages:
    if msg.type == 'set_tempo':
        tempo_map.append((tick, msg.tempo))

# Convert tick to seconds with tempo changes
def tick_to_seconds(target_tick):
    seconds = 0.0
    prev_tick = 0
    prev_tempo = tempo_map[0][1]
    
    for tick, tempo in tempo_map[1:]:
        if tick > target_tick:
            seconds += mido.tick2second(target_tick - prev_tick, 
                                       ticks_per_beat, prev_tempo)
            return seconds
        seconds += mido.tick2second(tick - prev_tick, 
                                    ticks_per_beat, prev_tempo)
        prev_tick = tick
        prev_tempo = tempo
    
    seconds += mido.tick2second(target_tick - prev_tick, 
                                ticks_per_beat, prev_tempo)
    return seconds
```

### Beat Position Calculation
```python
# Absolute position from file start
beat_position = tick / ticks_per_beat

# Position within grid (for quantization)
pos_in_grid = beat_position % grid_size

# Error calculation
if pos_in_grid <= grid_size / 2:
    error_beats = pos_in_grid  # Early
else:
    error_beats = pos_in_grid - grid_size  # Late

# Convert to milliseconds
beat_duration_sec = mido.tick2second(ticks_per_beat, ticks_per_beat, tempo)
error_ms = error_beats * beat_duration_sec * 1000
```

---

## Environment Setup

### Dependencies
```bash
# Required
mido>=1.3.0      # MIDI file parsing
numpy>=1.24.0    # Statistical calculations

# Optional (dev)
pytest>=7.0      # Testing
black>=23.0      # Formatting
ruff>=0.1.0      # Linting
```

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
- Line length: 100 characters (`pyproject.toml`)
- Python target: 3.8+
- Virtual environment: Required (macOS externally-managed Python)

---

## Usage Examples

### Basic Analysis
```bash
python -m audio my_drums.mid
```

### Get Quantization Advice
```bash
python suggest_quantize.py my_drums.mid
```

### Compare Before/After Quantization
```bash
# Edit compare_files.py to set file paths
python compare_files.py
```

### Debug Specific Issues
```bash
python debug_timing.py        # Quick overview
python debug_detailed.py      # Beat-by-beat analysis
```

---

## Future Enhancement Ideas

### Potential Features
1. **Visualization**: Plot timing errors over time (histogram, timeline)
2. **Export**: JSON/CSV output for further analysis
3. **Audio Support**: Analyze timing from audio files (onset detection)
4. **Velocity Analysis**: Consistency of hit strength
5. **Pattern Recognition**: Identify repeated fills, detect common patterns
6. **Multi-File Reports**: Batch analyze multiple files, generate report
7. **Progress Tracking**: Compare same song over time to track improvement
8. **MIDI Output**: Generate click track or corrected MIDI
9. **Web Interface**: Browser-based visualization and analysis
10. **Real-Time Analysis**: Analyze MIDI input in real-time during practice

### Code Improvements
- Add comprehensive unit tests
- Add type hints throughout
- Create Python package for PyPI distribution
- Add CI/CD pipeline
- Performance optimization for large files

---

## Key Takeaways for Future Development

1. **Always validate with real data**: The breakthrough came from comparing unquantized vs quantized files with known results.

2. **Modulo is essential**: For any grid-based analysis of MIDI files that might not start at beat 0.

3. **Tempo changes matter**: Process all tracks together to catch tempo changes.

4. **Musical context > Technical precision**: A song in 1/16 notes shouldn't be quantized to 1/32 just because the error is lower.

5. **Grid auto-detection works**: Testing multiple grids and selecting the best fit is robust.

6. **Human timing is naturally loose**: 20-50ms errors are normal for real performances.

7. **Sub-millisecond precision is achievable**: Quantized MIDI can reach <1ms error, proving the analysis is accurate.

---

## Related Documentation

- **README.md**: User-facing documentation
- **AGENTS.md**: Architecture and design decisions for AI agents
- **pyproject.toml**: Project configuration and dependencies
- **requirements.txt**: Python package dependencies

---

## Contact & Contributions

Project developed in collaboration with Warp AI (warp.dev)  
Development session: February 7, 2026  
Location: `/Users/joerg/Development/python/audio`

---

*This document captures the complete development journey, technical decisions, and lessons learned for future reference and continued development.*
