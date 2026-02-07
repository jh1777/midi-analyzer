"""Main entry point for the audio application."""

import sys
from audio.drum_analyzer import analyze_midi_drums


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Audio MIDI Drum Analyzer")
        print("\nUsage:")
        print("  python -m audio <midi_file>")
        print("\nExample:")
        print("  python -m audio drums.mid")
        return
    
    midi_file = sys.argv[1]
    analyze_midi_drums(midi_file)


if __name__ == "__main__":
    main()
