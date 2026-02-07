"""Main entry point for the audio application."""

import sys
import argparse
from audio.drum_analyzer import analyze_midi_drums


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='MIDI Drum Timing Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python -m audio drums.mid
  python -m audio drums.mid --details "Acoustic Snare"
  python -m audio drums.mid --details "Bass Drum 1"
        ''')
    
    parser.add_argument('midi_file', help='Path to MIDI file')
    parser.add_argument(
        '--details', 
        metavar='DRUM_NAME',
        help='Show detailed analysis for a specific drum (e.g., "Acoustic Snare", "Bass Drum 1")')
    
    args = parser.parse_args()
    
    analyze_midi_drums(args.midi_file, filter_drum=args.details)


if __name__ == "__main__":
    main()
