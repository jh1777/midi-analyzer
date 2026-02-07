# Audio

A Python MIDI drum analyzer that provides beat analysis data from MIDI drum files.

## Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Analyze a MIDI drum file:

```bash
python -m audio your_drums.mid
```

Or use the analyzer directly:

```bash
python -m audio.drum_analyzer your_drums.mid
```

## Output

The analyzer provides:
- Duration and tempo (BPM)
- Total drum hits
- Breakdown by drum type (kick, snare, hi-hat, etc.)
- Detailed beat timing with velocity information

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest
```
