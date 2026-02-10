# Groove-Aware Timing Analysis

## Overview

A new analysis mode that measures **timing consistency relative to the player's established groove**, rather than absolute grid alignment.

## The Problem with Grid-Based Analysis

**Grid-based analysis** measures every hit against a fixed grid, which results in:
- ❌ Constant ~30ms offset penalty for e-drum latency
- ❌ Constant offset penalty for "laid back" or "pushed" feel
- ❌ Penalizes groove/feel as "poor timing"
- ❌ Doesn't distinguish between "tight but behind" vs "inconsistent"

**Example:**
```
All hits at +28ms → Score: 23 (Needs Work)
But this could be: Rock-solid, consistent groove with 28ms feel!
```

## The Solution: Groove-Aware Analysis

### Algorithm

**Phase 1: Detect Groove Reference**
1. Find most reliable drum (kick, snare, or hi-hat)
2. Skip first/last 10% of song (intro/outro unstable)
3. Take middle stable region (8-16 consecutive hits)
4. Calculate median offset from grid (robust to outliers)
5. This becomes the "groove reference offset"

**Phase 2: Groove-Corrected Analysis**
1. Calculate grid offsets for all hits
2. **Subtract groove offset** from each hit
3. Measure consistency relative to groove
4. Use IQR (interquartile range) - more robust than std dev
5. Detect outliers using Tukey's fences method

**Phase 3: Scoring**
- Based on IQR (consistency), not absolute error
- **Tight**: IQR < 10ms (score 90-100)
- **Good**: IQR 10-20ms (score 70-90)
- **Fair**: IQR 20-35ms (score 40-70)
- **Loose**: IQR > 35ms (score 0-40)

## Key Advantages

### ✅ Groove-Aware
- Respects "laid back" or "pushed" feel
- That 30ms offset? Now it's the groove, not an error!
- Measures what matters: **consistency**

### ✅ Statistically Robust
- **Median** for groove detection (outlier-resistant)
- **IQR** for consistency (more stable than std dev)
- **Tukey's fences** for outlier detection (standard statistical method)
- Skips intro/outro (often unstable)

### ✅ No First-Note Bias
- Uses middle 8-16 hits from stable region
- Ignores first note (often rushed/late)
- Ignores fills and stops at end

## Implementation

### DrumAnalyzer Methods

**New method:**
```python
analyzer.analyze(mode='groove-aware')  # Default
analyzer.analyze(mode='grid-based')     # Old method
```

**Internal methods:**
- `calculate_groove_aware_quality(beats)` - Main groove-aware analysis
- `_detect_groove_offset(drum_beats)` - Find groove reference
- `_calculate_grid_offsets(hits, grid_size)` - Calculate offsets

### Output Metrics

**Groove-aware metrics include:**
```python
{
    'groove_offset_ms': 28.4,  # Detected groove feel
    'mean_error_ms': -1.2,      # Deviation from groove (not grid!)
    'abs_mean_error_ms': 8.3,   # Average deviation magnitude
    'std_dev_ms': 9.1,          # Standard deviation
    'iqr_ms': 7.2,              # Interquartile range (KEY METRIC)
    'median_offset_ms': -0.8,   # Median deviation from groove
    'outlier_percentage': 3.2,  # Percentage of outlier hits
    'timing_score': 92.8,       # Based on IQR
    'rating': 'Tight',          # Tight/Good/Fair/Loose
    'tendency': 'Locked to groove'  # vs 'Ahead/Behind groove'
}
```

**Metadata:**
```python
'_groove_metadata': {
    'groove_offset_ms': 28.4,
    'reference_drum': 'Bass Drum 1',
    'analysis_mode': 'groove-aware'
}
```

## Example Comparison

### Grid-Based Analysis
```
Bass Drum: 30.4ms error → Score 24 (Needs Work)
Snare:     31.2ms error → Score 23 (Needs Work)
Hi-Hat:    29.8ms error → Score 25 (Needs Work)

Overall: "Poor timing, practice with metronome"
```

### Groove-Aware Analysis
```
Groove Reference: +29.8ms (detected from Bass Drum)

Bass Drum: IQR 8.2ms → Score 91.8 (Tight)
Snare:     IQR 9.4ms → Score 90.6 (Tight)
Hi-Hat:    IQR 7.1ms → Score 92.9 (Tight)

Overall: "Rock-solid groove! Tight and consistent."
Interpretation: Your groove is 30ms laid back - this is a FEATURE!
```

## Usage

### CLI
```bash
# Groove-aware (default)
python -m audio drums.mid

# Grid-based (old method)
python -m audio drums.mid --mode grid-based

# Or via convenience function
from audio.drum_analyzer import analyze_midi_drums
analysis = analyze_midi_drums('drums.mid', mode='groove-aware')
```

### API (TODO: Not yet implemented)
```python
# Analyze with mode parameter
analyzer = DrumAnalyzer('drums.mid')
analysis = analyzer.analyze(mode='groove-aware')
```

### UI Toggle (TODO: Not yet implemented)
```
[ ] Grid-Based   [✓] Groove-Aware
```

## Technical Details

### Grid Size Detection
- Still uses multi-grid approach (16th, 8th, quarter, triplets)
- Each drum analyzed with its own optimal grid
- Same as grid-based method

### Robustness Checks
```python
# If groove detection fails
if groove_reference_quality < threshold:
    return 0.0  # Fallback: no groove offset

# If too many outliers
if outlier_percentage > 30:
    flag_as_free_timing()  # May be rubato/loose performance
```

### Window Selection
```python
# Find stable region
start_idx = len(hits) // 10      # Skip first 10%
end_idx = len(hits) - len(hits)//10  # Skip last 10%
stable_region = hits[start_idx:end_idx]

# Take middle 8-16 for reference
n_reference = min(16, max(8, len(stable_region) // 4))
middle = stable_region[middle_start:middle_start + n_reference]
groove_offset = np.median(middle)  # MEDIAN (robust!)
```

## Future Enhancements

### Tempo Drift Detection
```python
# Divide song into sections, check if groove changes
sections = [beginning, middle, end]
offsets = [median(section) for section in sections]
drift = offsets[-1] - offsets[0]

if abs(drift) > 10:
    return f"Tempo drift: {drift:+.1f}ms over song"
```

### Per-Section Analysis
```python
# Analyze verse vs chorus separately
verse_groove = detect_groove(verse_hits)
chorus_groove = detect_groove(chorus_hits)

if abs(verse_groove - chorus_groove) > 5:
    return "Different feel in different sections"
```

## Status

### ✅ Implemented
- Groove detection algorithm
- Groove-corrected analysis
- IQR-based consistency scoring
- Outlier detection
- Mode parameter in `analyze()`

### 🚧 TODO
- API endpoint support for mode parameter
- UI toggle between modes
- Visualization of groove offset
- Per-section groove analysis
- Tempo drift detection
