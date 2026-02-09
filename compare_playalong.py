#!/usr/bin/env python3
"""Compare MIDI drum play-along performance against audio reference.

Usage:
    python compare_playalong.py <your_midi.mid> <reference_audio.mp3>
    python compare_playalong.py <your_midi.mid> <reference_audio.mp3> --threshold 30

Examples:
    python compare_playalong.py my_drums.mid original_drums.mp3
    python compare_playalong.py my_drums.mid original_drums.wav --threshold 30
"""

import sys
import argparse
from pathlib import Path

try:
    from audio.playalong_compare import compare_playalong
except ImportError as e:
    print(f"Error: {e}")
    print("\nMissing dependencies. Install with:")
    print("  pip install librosa scipy soundfile")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Compare MIDI drum play-along against audio reference',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python compare_playalong.py my_drums.mid original_drums.mp3
  python compare_playalong.py my_drums.mid original_drums.wav --threshold 30
  
Workflow:
  1. Separate drums from original song (use Moises or Logic Pro)
  2. Record your play-along in MIDI
  3. Run this tool to see how well you matched!
  
Match Threshold:
  - 30ms: Strict (pro-level timing)
  - 50ms: Standard (good for practice)
  - 100ms: Lenient (good for learning)
        '''
    )
    
    parser.add_argument(
        'midi_file',
        help='Your MIDI drum performance file'
    )
    
    parser.add_argument(
        'audio_file',
        help='Reference audio drum track (MP3/WAV from Moises/Logic Pro)'
    )
    
    parser.add_argument(
        '--threshold',
        '-t',
        type=float,
        default=50.0,
        help='Match threshold in milliseconds (default: 50ms)'
    )
    
    parser.add_argument(
        '--onset-threshold',
        type=float,
        default=0.3,
        help='Onset detection sensitivity 0-1 (default: 0.3, higher=less sensitive)'
    )
    
    parser.add_argument(
        '--audio-bpm',
        type=float,
        default=None,
        help='Original BPM of audio file (auto-detected if not specified)'
    )
    
    parser.add_argument(
        '--midi-bpm',
        type=float,
        default=None,
        help='BPM of MIDI recording (extracted from file if not specified)'
    )
    
    args = parser.parse_args()
    
    # Validate files exist
    midi_path = Path(args.midi_file)
    audio_path = Path(args.audio_file)
    
    if not midi_path.exists():
        print(f"Error: MIDI file not found: {args.midi_file}")
        sys.exit(1)
    
    if not audio_path.exists():
        print(f"Error: Audio file not found: {args.audio_file}")
        sys.exit(1)
    
    # Run comparison
    try:
        compare_playalong(
            str(midi_path),
            str(audio_path),
            threshold_ms=args.threshold,
            onset_threshold=args.onset_threshold,
            audio_bpm=args.audio_bpm,
            midi_bpm=args.midi_bpm
        )
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
