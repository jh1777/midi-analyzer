# MIDI Drum Timing Analyzer

**Improve your drumming timing!** A Python tool that analyzes MIDI drum recordings and measures timing precision against a perfect grid. Helps you identify which drums need timing work and suggests optimal quantization settings.

## Features

✨ **Timing Analysis**: Measures how far each hit is from perfect timing (in milliseconds)  
📊 **Scoring System**: 0-100 score per drum (Excellent/Good/Acceptable/Needs Work/Poor)  
🎵 **Auto Grid Detection**: Tests multiple grids (16th, triplets, 8th, etc.) to find best fit  
🎯 **Quantization Advisor**: Suggests Logic Pro settings for best results  
📈 **Progress Tracking**: Compare before/after quantization to see improvement

## Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Option 1: Web UI (Recommended)

Analyze multiple MIDI files with a visual interface:

```bash
./start.sh
```

This will start:
- **Backend API** on http://localhost:8000
- **Web UI** on http://localhost:5173

The web interface lets you:
- View all MIDI files in the `mid-files` folder
- See timing analysis results in a table
- Top 5 drums displayed with timing error and score
- Refresh to scan for new files
- Configure the MIDI folder path

### Option 2: Command Line

Analyze individual files:

```bash
python -m audio your_drums.mid
```

**Output:**
```
MIDI Drum Analysis: your_drums.mid
Duration: 180.5s
Tempo: 120.0 BPM
Total Drum Hits: 842

TIMING QUALITY ANALYSIS

  Drum                       Score Rating          Error  Hits
  ------------------------------------------------------------
  Bass Drum 1                 60.8 Acceptable     30.4ms   440 ✓
  Acoustic Snare              59.2 Acceptable     31.4ms   270 ✓
  Closed Hi-Hat               59.8 Acceptable     31.1ms   473 ✓
```

### 2. Get Quantization Advice

Not sure what quantization to use in your DAW?

```bash
python suggest_quantize.py your_drums.mid
```

**Output:**
```
🎵 MUSICAL FIT (what the song is written in):
   Primary: 16th notes (1/16) - 30.70ms error
   Also try: 16th note triplets (1/16T)

⚡ TECHNICAL BEST (tightest possible fit):
   Grid: 32nd notes (1/32) - 15.55ms error

📋 Logic Pro Settings:
   1. Select all MIDI notes (Cmd+A)
   2. Press 'Q' or go to: Edit → Quantize
   3. Set Grid: 1/16
   4. Set Q-Strength: 80-100%
   5. Apply
```

### 3. Compare Before/After Quantization

```bash
# Edit compare_files.py to set your files
python compare_files.py
```

**Example Results:**
```
UNQUANTIZED:
  Bass Drum:  30.40ms → Score 60.8 (Acceptable)
  Snare:      31.41ms → Score 59.2 (Acceptable)

QUANTIZED:
  Bass Drum:   0.43ms → Score 99.1 (Excellent) ✓
  Snare:       0.10ms → Score 99.8 (Excellent) ✓
```

## Understanding the Scores

| Score | Rating | Avg Error | What It Means |
|-------|--------|-----------|---------------|
| 90-100 | Excellent | <10ms | Pro studio level (accounts for e-drum latency) |
| 70-89 | Good | 10-20ms | Professional live playing, tight timing |
| 40-69 | Acceptable | 20-35ms | Solid playing with human feel |
| 20-39 | Needs Work | 35-50ms | Noticeable looseness, practice recommended |
| 0-19 | Poor | >50ms | Objectively problematic timing |

**Real-world expectations:**
- E-drum recordings: 25-35ms typical (Acceptable) — includes 5-10ms system latency
- Professional drummers: 10-20ms on acoustic kits (Good)
- Quantized MIDI: <10ms (Excellent)
- Perfect quantization: <1ms (Excellent, 99+ score)

**Note**: Thresholds calibrated based on research showing professional drummers typically deviate 10-20ms in real performances, and e-drum systems add 5-10ms inherent latency.

## All Available Tools

### Web UI
```bash
./start.sh
```
Launches the web interface for analyzing multiple files at once. See all your MIDI files with their timing analysis in a visual table.

**Manual startup:**
```bash
# Terminal 1 - Backend
source venv/bin/activate
python api_server.py

# Terminal 2 - Frontend
cd web-ui
npm run dev
```

### Main Analyzer
```bash
python -m audio <midi_file.mid>
```
Full timing analysis with scores per drum type.

**Filter by specific drum:**
```bash
python -m audio <midi_file.mid> --details "Acoustic Snare"
python -m audio <midi_file.mid> --details "Bass Drum 1"
```
Shows detailed analysis for only one drum (useful for focused practice).

### Quantization Advisor
```bash
python suggest_quantize.py <midi_file.mid>
```
Suggests best DAW quantization settings.

### File Comparison
```bash
python compare_files.py
```
Compare two files side-by-side (edit script to set file paths).

### Play-Along Comparison (NEW!)
```bash
python compare_playalong.py <your_drums.mid> <reference_drums.mp3>
```
Compare your MIDI play-along against the original audio drum track!

**IMPORTANT: Best Practices for Accurate Results**

✅ **Recommended Workflow (60-80% accuracy):**
1. Find the original song's BPM (e.g., "Don't You Remember" = 115 BPM)
2. **Set your DAW to the ORIGINAL song tempo** (not your preferred tempo!)
3. Import the song WITHOUT time-stretching (disable Flex Time in Logic)
4. Record your MIDI drums at the original tempo
5. Use Moises/Logic to extract drum stem at ORIGINAL tempo
6. Run comparison: `python compare_playalong.py your_drums.mid drums.mp3 --audio-bpm 115 --midi-bpm 115`

⚠️ **Why this matters:**
- If you record at 120 BPM but the song is 115 BPM, your DAW time-stretches the audio
- Time-stretching introduces timing artifacts that break the comparison
- Tempo mismatches cause poor match rates even if you played perfectly!

**Advanced Options:**
```bash
# Specify tempos explicitly (recommended for accuracy)
python compare_playalong.py drums.mid audio.mp3 --audio-bpm 115 --midi-bpm 115

# Adjust onset detection sensitivity (0-1, lower = more sensitive)
python compare_playalong.py drums.mid audio.mp3 --onset-threshold 0.15

# Change match threshold (default: 50ms)
python compare_playalong.py drums.mid audio.mp3 --threshold 30
```

**Example output:**
```
⚡ Tempo correction: Stretching audio 115.0 BPM → 120.0 BPM
   Stretch ratio: 1.0435x

Overall Score:  72.4/100
Rating:         Good 👌
Matched Hits:   658/911 (72.2%)
Mean Error:     23.0ms (±13.2ms)
Within 50ms:    658 hits (72.2%)
Missed Hits:    253
Extra Hits:     253
```

**Understanding Results:**
- **60-80% match**: Good! Audio stem quality limits perfect matching
- **40-60% match**: Acceptable, check if tempos match and onset detection is tuned
- **<40% match**: Likely wrong song, wrong take, or very different performance
- **>90% match**: Excellent! (requires very clean drum separation or MIDI reference)

**Limitations:**
- Audio stem separation (Moises/Logic) typically misses 15-20% of drum hits
- Isolated drums may have other instruments bleeding through
- For >90% accuracy, you need studio-quality separated stems or MIDI reference tracks

### Debug Tools
```bash
python debug_timing.py        # Quick overview of one file
python debug_detailed.py      # Beat-by-beat analysis
```

## Workflow Example

1. **Record your drums** in your DAW → Export as MIDI
2. **Analyze**: `python -m audio my_drums.mid`
3. **Get advice**: `python suggest_quantize.py my_drums.mid`
4. **Quantize in DAW** using suggested settings
5. **Export quantized version** → `my_drums_quantized.mid`
6. **Compare**: Edit `compare_files.py` and run to see improvement
7. **Practice** the parts that scored lowest!

## What Gets Analyzed

- **All GM Drum Notes**: Bass drums, snares, toms, hi-hats, cymbals
- **Timing Precision**: Deviation from grid in milliseconds
- **Grid Detection**: Auto-detects 32nd, 16th triplets, 16th, 8th triplets, 8th, quarter notes
- **Tempo Changes**: Handles tempo changes within the file
- **Musical Structure**: Works with real songs (handles breaks, fills, interludes)

## Technical Details

- Uses **grid-based quantization** - each hit compared to nearest grid position
- **Modulo-based** positioning handles files starting at any beat
- **Tempo map tracking** across all MIDI tracks
- Sub-millisecond precision for validation

## Troubleshooting

**"All my scores are poor even after quantization"**
- Make sure you exported the MIDI *after* quantizing in your DAW
- Check that quantization was actually applied (not just preview)

**"The suggested grid doesn't match my song"**
- Use the "Musical Fit" recommendation, not "Technical Best"
- Try both straight and triplet versions to hear which sounds right

**"Beat positions show huge numbers (>1000)"**
- This is normal! MIDI files can have silence before drums start
- The analyzer handles this automatically with modulo math

## Development

```bash
# Install in development mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black audio/

# Lint
ruff check audio/
```

## Documentation

- **README.md** (this file) - User guide
- **WEB_UI.md** - Web interface documentation
- **AGENTS.md** - Architecture and design decisions
- **DEVELOPMENT_SUMMARY.md** - Complete development history

## License

MIT License - Feel free to use and modify!

---

**Built with**: Python 3.8+, mido (MIDI parsing), numpy (statistics)  
**Works with**: Logic Pro, Ableton, FL Studio, any DAW that exports MIDI
