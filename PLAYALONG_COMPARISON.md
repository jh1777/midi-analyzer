# Play-Along Comparison Feature

Compare your MIDI drum play-along performance against the original audio drum track.

## Overview

This feature helps you:
- **Track progress** over time
- **Identify mistakes** (missed hits, extra hits)
- **Measure timing accuracy** against the original
- **Get objective scores** (0-100) for your performance

## How It Works

1. **Audio Onset Detection**: Extracts drum hit timings from the audio file using librosa
2. **MIDI Extraction**: Gets your drum hit timings from MIDI
3. **Timeline Alignment**: Automatically syncs MIDI and audio (handles offset/tempo differences)
4. **Comparison**: Matches your hits to original hits and calculates metrics

## Requirements

Install additional dependencies:

```bash
source venv/bin/activate
pip install librosa scipy soundfile
```

## Usage

### Basic Usage

```bash
python compare_playalong.py your_drums.mid original_drums.mp3
```

### With Custom Threshold

```bash
# Strict (30ms threshold - pro level)
python compare_playalong.py your_drums.mid original_drums.mp3 --threshold 30

# Standard (50ms threshold - default)
python compare_playalong.py your_drums.mid original_drums.mp3 --threshold 50

# Lenient (100ms threshold - learning)
python compare_playalong.py your_drums.mid original_drums.mp3 --threshold 100
```

## Workflow

### ⚠️ CRITICAL: Tempo Matching

**For accurate results, your MIDI and audio MUST be at the same tempo!**

❌ **Common Mistake:**
- Recording at 120 BPM when the song is actually 115 BPM
- Letting your DAW time-stretch the song to match your project tempo
- Comparing stretched MIDI to unstretched audio (or vice versa)

✅ **Correct Approach:**

**Option A: Record at Original Tempo (Recommended)**
1. Find the song's original BPM (Google "[song name] BPM" or use a BPM detector)
2. Set your DAW project to the ORIGINAL song tempo (e.g., 115 BPM)
3. Import the song WITHOUT time-stretching:
   - Logic Pro: Disable "Flex" mode or set to "Follow Tempo: Off"
   - Ableton: Set clip warp mode to "Off"
4. Record your MIDI at the original tempo
5. Export both MIDI and drum stem at the same original tempo
6. Run: `python compare_playalong.py drums.mid drums.mp3 --audio-bpm 115 --midi-bpm 115`

**Option B: Match Everything to Your Preferred Tempo**
1. Set your DAW to your preferred tempo (e.g., 120 BPM)
2. Import song and enable time-stretching to match 120 BPM
3. Record MIDI at 120 BPM
4. Export drum stem WITH time-stretching applied (at 120 BPM)
5. Run: `python compare_playalong.py drums.mid drums.mp3 --audio-bpm 120 --midi-bpm 120`

### 1. Separate Drums from Song

**Option A: Moises (Recommended)**
1. Upload song to Moises.ai
2. Select "Drums" separation
3. Download drums track as MP3
4. **Note the original BPM** (shown in filename or song info)

**Option B: Logic Pro**
1. Import song into Logic Pro at ORIGINAL tempo
2. Use Stem Splitter plugin (or similar)
3. Export drums track as MP3/WAV
4. **Ensure export is at the same tempo as your recording**

### 2. Record Your Play-Along

1. **Set DAW to correct tempo** (see "Tempo Matching" above)
2. Import the song (without drums) - match tempo!
3. Add MIDI drum track
4. Play along and record
5. Export your performance as MIDI

### 3. Run Comparison

```bash
# Specify both tempos explicitly for best results
python compare_playalong.py my_performance.mid original_drums.mp3 \
  --audio-bpm 115 --midi-bpm 115 --threshold 50

# If tempos differ (not recommended, but the tool handles it)
python compare_playalong.py my_performance.mid original_drums.mp3 \
  --audio-bpm 115 --midi-bpm 120 --threshold 50
```

## Output Report

The tool generates a detailed report:

```
============================================================
COMPARISON REPORT
============================================================
Your MIDI: my_performance.mid
Reference Audio: original_drums.mp3
Match Threshold: 50ms

------------------OVERALL STATISTICS----------------------
Your MIDI Hits:        245
Audio Drum Onsets:     239
Matched Hits:          208
Match Percentage:      84.9%

--------------------TIMING ACCURACY-----------------------
Mean Error:            18.2ms (±12.4ms)
Within 30ms:           185 hits (75.5%)
Within 50ms:           232 hits (94.7%)
Within 100ms:          242 hits (98.8%)

---------------------MISSED HITS--------------------------
Missed Hits:           6 (you should have played these)
  - 0:45 (45.23s)
  - 1:23 (83.12s)
  ...

---------------------EXTRA HITS---------------------------
Extra Hits:            12 (not in original)
  - 2:34 (154.67s)
  ...

------------------PERFORMANCE SCORE-----------------------
Overall Score:         87.3/100
Rating:                Great! 👍
============================================================
```

## Metrics Explained

### Overall Score (0-100)
Weighted combination of:
- **Match percentage** (60%): How many hits you got right
- **Timing accuracy** (40%): How close your timing was

### Match Percentage
Percentage of your MIDI hits that matched an audio onset within the threshold.

### Timing Accuracy Tiers
- **Within 30ms**: Pro-level timing
- **Within 50ms**: Good practice timing
- **Within 100ms**: Acceptable for learning

### Missed Hits
Drum hits in the original that you didn't play. Check these timestamps and practice those sections.

### Extra Hits
Hits you played that weren't in the original. Could be:
- Extra ghost notes
- Mistakes
- Intentional embellishments

## Ratings

| Score | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Excellent! 🎉 | Pro-level performance |
| 80-89 | Great! 👍 | Very good, minor issues |
| 70-79 | Good 👌 | Solid performance |
| 60-69 | Fair 🙂 | Acceptable, room for improvement |
| 0-59 | Needs Practice 💪 | Keep working on it |

## Realistic Expectations

### Expected Match Rates

**Even with perfect playing, you'll likely see:**
- **60-80% match rate**: Good! Audio stem quality is the limiting factor
- **40-60% match rate**: Acceptable, check tempo matching and onset detection settings
- **<40% match rate**: Likely wrong song, different take, or severe tempo mismatch
- **>90% match rate**: Excellent! Only achievable with studio-quality stems or MIDI reference

**Why not 100%?**
- Moises/Logic stem separation typically **misses 15-20% of drum hits**
- Quiet hi-hats, ghost notes, and cymbals are often not detected
- Other instruments bleed into the drum track (bass, guitar)
- Your MIDI may have embellishments not in the original performance

### Real-World Example Results

```
Faith Hill - "Love Ain't Like That" (74 BPM)
- MIDI hits: 911
- Audio onsets detected: 770 (84.5% of MIDI)
- Matched: 658/911 (72.2%)
- Mean timing error: 23.0ms (±13.2ms)
- Score: 72.4/100 (Good 👌)
- First 20 hits: 90% matched perfectly
```

**Interpretation**: This is a **good result**! The 72% match reflects:
- ✅ You played well (first 20 hits = 90% matched)
- ✅ Timing is tight (23ms average)
- ❌ Audio stem missing ~15% of hits (typical for Moises)
- ❌ You played more notes than original (embellishments)

## Tips for Better Results

### Audio Separation
- Use high-quality drum separation (Moises Premium or Logic Pro)
- Poor separation = false onsets = lower accuracy
- Isolated drums work best
- **Accept that stems will miss 15-20% of hits** - this is normal!

### Recording
- **Match tempo exactly** (most important!)
- Use metronome/click track aligned with song
- Start recording slightly before the song starts
- Avoid extra notes at beginning/end
- Record at the **original song tempo**, not your preferred tempo

### MIDI Export
- Export full performance (don't trim)
- Include all drum hits (kick, snare, hi-hat, etc.)
- Use standard GM drum mapping
- **Ensure MIDI tempo matches audio tempo**

### Onset Detection Tuning

```bash
# If match rate is very low, try more sensitive detection
python compare_playalong.py drums.mid audio.mp3 --onset-threshold 0.15

# If getting too many false positives
python compare_playalong.py drums.mid audio.mp3 --onset-threshold 0.4

# Default works well for most cases
python compare_playalong.py drums.mid audio.mp3 --onset-threshold 0.3
```

## Troubleshooting

### "No audio onsets detected"
- Audio file might be too quiet
- Try lowering `--onset-threshold` (e.g., `--onset-threshold 0.2`)
- Check that audio file contains drums

### Very Low Score Despite Good Performance
- Check alignment: MIDI and audio should start around same time
- Try different threshold: `--threshold 100`
- Verify audio separation quality

### Too Many False Positives
- Increase onset threshold: `--onset-threshold 0.4`
- Improve drum separation quality
- Remove non-drum sounds from audio

## Technical Details

### Multi-Band Onset Detection (Improved Algorithm)

The tool uses a **3-band approach** to detect different drum types:

1. **Percussive isolation** (HPSS): Separates drums from tonal instruments
2. **Low-frequency band** (20-300 Hz): Detects kick drum hits
3. **High-frequency band** (4-15 kHz): Detects hi-hats and cymbals
4. **Full-band percussive**: Detects snares and toms
5. **Deduplication**: Merges detections within 25ms to avoid duplicates

**Result**: Detects **4-5x more onsets** than basic methods (e.g., 770 vs 177 onsets)

**Adjustable sensitivity**:
```bash
--onset-threshold 0.15  # Very sensitive (more hits, more false positives)
--onset-threshold 0.30  # Default (balanced)
--onset-threshold 0.50  # Conservative (fewer hits, fewer false positives)
```

### Tempo Correction

If `--audio-bpm` and `--midi-bpm` are specified:
- Automatically time-stretches audio onset times to match MIDI tempo
- Formula: `stretched_time = original_time * (midi_bpm / audio_bpm)`
- Handles songs recorded at different tempos
- Example: 115 BPM audio → 120 BPM MIDI = 1.0435x stretch

### Alignment Algorithm (Two-Stage)

**Stage 1: Coarse Alignment**
- Uses first 5-10 MIDI hits to find initial offset
- Tests alignment with first 100 audio onsets
- Finds rough time offset (e.g., -900s if MIDI starts very late)
- Typical accuracy: 30-50ms

**Stage 2: Fine-Tuning**
- Searches tempo ratios: 0.90-1.10x (handles ±10% tempo differences)
- Searches offset adjustments: ±3 seconds around coarse offset
- Uses 50 MIDI hits for robust estimation
- Final accuracy: 10-30ms average error

**Result**: Automatically handles:
- MIDI files with long silence at start (e.g., starts at 956 seconds)
- Tempo mismatches up to ±10%
- Small timing drifts throughout the performance

### Matching Algorithm
- Uses **Hungarian algorithm** for optimal pairing
- Each MIDI hit matched to nearest audio onset
- Threshold determines what counts as a "match" (default: 50ms)
- Reports: matched hits, missed hits (you should have played), extra hits (not in original)

## Future Enhancements

Potential additions:
- Web UI integration
- Per-drum analysis (snare accuracy vs. kick accuracy)
- Visual timeline showing your hits vs. original
- Progress tracking over multiple sessions
- Export results to JSON/CSV
- Beat-by-beat accuracy graph

## Example Use Cases

### Practice Routine
```bash
# Week 1
python compare_playalong.py song_week1.mid original.mp3
# Score: 65/100

# Week 2
python compare_playalong.py song_week2.mid original.mp3
# Score: 78/100

# Week 3
python compare_playalong.py song_week3.mid original.mp3
# Score: 87/100  🎉
```

### Section Practice
Focus on specific challenging sections:
1. Identify low-score timestamps in report
2. Practice those sections
3. Re-record and compare
4. Track improvement

### Different Songs
```bash
python compare_playalong.py easy_song.mid easy_original.mp3    # 92/100
python compare_playalong.py medium_song.mid medium_original.mp3 # 78/100
python compare_playalong.py hard_song.mid hard_original.mp3     # 63/100
```
