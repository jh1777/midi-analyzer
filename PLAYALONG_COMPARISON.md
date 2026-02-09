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

### 1. Separate Drums from Song

**Option A: Moises (Recommended)**
1. Upload song to Moises.ai
2. Select "Drums" separation
3. Download drums track as MP3

**Option B: Logic Pro**
1. Import song into Logic Pro
2. Use Stem Splitter plugin (or similar)
3. Export drums track as MP3/WAV

### 2. Record Your Play-Along

1. Import the song (without drums) into your DAW
2. Add MIDI drum track
3. Play along and record
4. Export your performance as MIDI

### 3. Run Comparison

```bash
python compare_playalong.py my_performance.mid original_drums.mp3
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

## Tips for Better Results

### Audio Separation
- Use high-quality drum separation (Moises Premium or Logic Pro)
- Poor separation = false onsets = lower accuracy
- Isolated drums work best

### Recording
- Use metronome/click track aligned with song
- Start recording slightly before the song starts
- Avoid extra notes at beginning/end

### MIDI Export
- Export full performance (don't trim)
- Include all drum hits (kick, snare, hi-hat, etc.)
- Use standard GM drum mapping

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

### Onset Detection
- Uses combined energy-based and spectral flux detection
- Targets >90% accuracy for clean drum tracks
- Optimized for isolated drums (not full mix)

### Alignment Algorithm
- Tests multiple offset/tempo combinations
- Uses first 20 onsets for robust alignment
- Handles slight tempo drift (0.98-1.02x)

### Matching Algorithm
- Uses Hungarian algorithm for optimal pairing
- Each MIDI hit matched to nearest audio onset
- Threshold determines what counts as a "match"

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
