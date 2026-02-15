"""MIDI drum file analyzer."""

import mido
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


# General MIDI drum mapping (channel 10)
DRUM_MAP = {
    35: "Acoustic Bass Drum",
    36: "Bass Drum 1",
    37: "Side Stick",
    38: "Acoustic Snare",
    39: "Hand Clap",
    40: "Electric Snare",
    41: "Low Floor Tom",
    42: "Closed Hi-Hat",
    43: "High Floor Tom",
    44: "Pedal Hi-Hat",
    45: "Low Tom",
    46: "Open Hi-Hat",
    47: "Low-Mid Tom",
    48: "Hi-Mid Tom",
    49: "Crash Cymbal 1",
    50: "High Tom",
    51: "Ride Cymbal 1",
    52: "Chinese Cymbal",
    53: "Ride Bell",
    54: "Tambourine",
    55: "Splash Cymbal",
    56: "Cowbell",
    57: "Crash Cymbal 2",
    58: "Vibraslap",
    59: "Ride Cymbal 2",
}


class DrumAnalyzer:
    """Analyze drum patterns in MIDI files."""
    
    def __init__(self, midi_file: str):
        """Initialize analyzer with MIDI file path."""
        self.midi_file = midi_file
        self.midi = mido.MidiFile(midi_file)
        self.tempo = 500000  # Default tempo (120 BPM)
        self.ticks_per_beat = self.midi.ticks_per_beat
        
    def calculate_timing_quality(self, beats: List[Dict]) -> Dict:
        """Calculate timing consistency by measuring deviation from tempo grid.
        
        This quantizes each hit to the nearest beat grid position and measures
        how early/late the actual hit is compared to perfect timing.
        
        Args:
            beats: List of beat dictionaries with 'beat_position' (in beats)
            
        Returns:
            Dictionary with timing quality metrics per drum type
        """
        # Group beats by drum type
        drum_beats = defaultdict(list)
        for beat in beats:
            drum_beats[beat['drum']].append({
                'time_seconds': beat['time_seconds'],
                'beat_position': beat['beat_position']
            })
        
        quality_metrics = {}
        
        # Determine grid resolution - check common subdivisions
        # We'll try 16th notes (1/4 beat), 8th notes (1/2 beat), quarter notes (1 beat)
        grid_sizes = [0.25, 0.5, 1.0]  # 16th, 8th, quarter notes
        
        for drum, hits in drum_beats.items():
            if len(hits) < 3:
                continue
            
            best_grid_size = None
            best_score = float('inf')
            best_errors = None
            
            # Try different grid resolutions and pick the one with smallest errors
            for grid_size in grid_sizes:
                timing_errors_ms = []
                
                for hit in hits:
                    beat_pos = hit['beat_position']
                    time_sec = hit['time_seconds']
                    
                    # Find position within the grid (modulo operation)
                    # This handles cases where drums start late in the file
                    pos_in_grid = beat_pos % grid_size
                    
                    # Find nearest grid point (either 0 or grid_size)
                    if pos_in_grid <= grid_size / 2:
                        error_beats = pos_in_grid  # Early, should be at 0
                    else:
                        error_beats = pos_in_grid - grid_size  # Late, should be at next grid
                    
                    # Convert to milliseconds using tempo
                    # 1 beat = 60/BPM seconds
                    beat_duration_sec = mido.tick2second(
                        self.ticks_per_beat,
                        self.ticks_per_beat,
                        self.tempo
                    )
                    error_ms = error_beats * beat_duration_sec * 1000
                    
                    timing_errors_ms.append(error_ms)
                
                # Calculate total absolute error for this grid size
                total_error = np.sum(np.abs(timing_errors_ms))
                
                if total_error < best_score:
                    best_score = total_error
                    best_grid_size = grid_size
                    best_errors = np.array(timing_errors_ms)
            
            if best_errors is None or len(best_errors) == 0:
                continue
            
            # Calculate statistics on timing errors
            mean_error_ms = np.mean(best_errors)
            abs_mean_error_ms = np.mean(np.abs(best_errors))
            std_error_ms = np.std(best_errors)
            max_early_ms = np.min(best_errors)  # Most negative = earliest
            max_late_ms = np.max(best_errors)   # Most positive = latest
            
            # Calculate timing tightness score (0-100)
            # Based on research:
            # - Professional drummers: 10-20ms typical deviation
            # - E-drum systems: 5-10ms inherent latency
            # - Perceptual threshold: 15-20ms for noticing timing issues
            # Thresholds calibrated for real human e-drum performance:
            # <10ms = Excellent (pro studio level, accounting for e-drum latency)
            # 10-20ms = Good (professional live playing)
            # 20-35ms = Acceptable (solid playing with human feel)
            # 35-50ms = Needs Work (noticeable looseness)
            # >50ms = Poor (objectively problematic)
            
            if abs_mean_error_ms < 10:
                score = 100 - abs_mean_error_ms * 1  # 100-90
            elif abs_mean_error_ms < 20:
                score = 90 - (abs_mean_error_ms - 10) * 2  # 90-70
            elif abs_mean_error_ms < 35:
                score = 70 - (abs_mean_error_ms - 20) * 2  # 70-40
            elif abs_mean_error_ms < 50:
                score = 40 - (abs_mean_error_ms - 35) * 1.33  # 40-20
            else:
                score = max(0, 20 - (abs_mean_error_ms - 50) * 0.4)
            
            # Determine if rushing or dragging
            # Threshold at 5ms to avoid flagging normal human variation
            if mean_error_ms > 5:
                tendency = 'Rushing (playing ahead)'
            elif mean_error_ms < -5:
                tendency = 'Dragging (playing behind)'
            else:
                tendency = 'Centered'
            
            # Grid name
            grid_names = {
                1/8: '32nd notes',
                1/6: '16th triplets',
                0.25: '16th notes',
                1/3: '8th triplets',
                0.5: '8th notes',
                1.0: 'quarter notes'
            }
            grid_name = grid_names.get(best_grid_size, f'{best_grid_size:.4f} beats')
            
            quality_metrics[drum] = {
                'hit_count': len(hits),
                'grid_size': best_grid_size,
                'grid_name': grid_name,
                'mean_error_ms': round(float(mean_error_ms), 2),
                'abs_mean_error_ms': round(float(abs_mean_error_ms), 2),
                'std_dev_ms': round(float(std_error_ms), 2),
                'max_early_ms': round(float(max_early_ms), 2),
                'max_late_ms': round(float(max_late_ms), 2),
                'timing_score': round(float(score), 1),
                'tendency': tendency,
            }
            
            # Add timing rating
            if score >= 90:
                quality_metrics[drum]['rating'] = 'Excellent'
            elif score >= 70:
                quality_metrics[drum]['rating'] = 'Good'
            elif score >= 40:
                quality_metrics[drum]['rating'] = 'Acceptable'
            elif score >= 20:
                quality_metrics[drum]['rating'] = 'Needs Work'
            else:
                quality_metrics[drum]['rating'] = 'Poor'
        
        return quality_metrics
    
    def calculate_groove_aware_quality(self, beats: List[Dict]) -> Dict:
        """Calculate timing consistency relative to player's established groove.
        
        This method:
        1. Detects the player's natural timing offset (groove) from a stable window
        2. Subtracts this groove offset from all hits
        3. Measures consistency relative to the groove (not absolute grid)
        
        This eliminates constant offsets (e.g. ~30ms) caused by:
        - E-drum latency
        - Player's natural "laid back" or "pushed" feel
        - DAW recording offset
        
        Args:
            beats: List of beat dictionaries with 'beat_position' and 'time_seconds'
            
        Returns:
            Dictionary with groove-aware timing metrics per drum type
        """
        # Group beats by drum type
        drum_beats = defaultdict(list)
        for beat in beats:
            drum_beats[beat['drum']].append({
                'time_seconds': beat['time_seconds'],
                'beat_position': beat['beat_position']
            })
        
        # Step 1: Detect groove reference offset
        groove_offset_ms, reference_drum = self._detect_groove_offset(drum_beats)
        
        # Step 2: Calculate consistency metrics per drum (groove-corrected)
        quality_metrics = {}
        
        for drum, hits in drum_beats.items():
            if len(hits) < 3:
                continue
            
            # Find best grid size for this drum
            grid_sizes = [1/8, 1/6, 0.25, 1/3, 0.5, 1.0]  # 32nd, 16th triplets, 16th, 8th triplets, 8th, quarter
            best_grid_size = None
            best_errors = None
            best_score = float('inf')
            
            for grid_size in grid_sizes:
                errors = self._calculate_grid_offsets(hits, grid_size)
                total_error = np.sum(np.abs(errors))
                
                if total_error < best_score:
                    best_score = total_error
                    best_grid_size = grid_size
                    best_errors = errors
            
            if best_errors is None or len(best_errors) == 0:
                continue
            
            # SUBTRACT GROOVE OFFSET
            groove_corrected = best_errors - groove_offset_ms
            
            # Calculate consistency metrics (using groove-corrected values)
            mean_dev = np.mean(groove_corrected)
            std_dev = np.std(groove_corrected)
            
            # Robust metrics (less sensitive to outliers)
            q1, median, q3 = np.percentile(groove_corrected, [25, 50, 75])
            iqr = q3 - q1
            
            # Outlier detection (Tukey's fences)
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outliers = [x for x in groove_corrected if x < lower_fence or x > upper_fence]
            outlier_pct = (len(outliers) / len(groove_corrected) * 100) if len(groove_corrected) > 0 else 0
            
            # Consistency score based on IQR (more robust than std dev)
            # Tight: IQR < 10ms
            # Good: IQR < 20ms  
            # Fair: IQR < 35ms
            # Loose: IQR >= 35ms
            if iqr < 10:
                consistency_score = 100 - iqr
            elif iqr < 20:
                consistency_score = 90 - (iqr - 10)
            elif iqr < 35:
                consistency_score = 70 - (iqr - 20) * 2
            else:
                consistency_score = max(0, 40 - (iqr - 35))
            
            # Determine tendency (relative to groove)
            if mean_dev > 5:
                tendency = 'Ahead of groove'
            elif mean_dev < -5:
                tendency = 'Behind groove'
            else:
                tendency = 'Locked to groove'
            
            # Grid name
            grid_names = {
                1/8: '32nd notes',
                1/6: '16th triplets',
                0.25: '16th notes',
                1/3: '8th triplets',
                0.5: '8th notes',
                1.0: 'quarter notes'
            }
            grid_name = grid_names.get(best_grid_size, f'{best_grid_size:.4f} beats')
            
            quality_metrics[drum] = {
                'hit_count': len(hits),
                'grid_size': best_grid_size,
                'grid_name': grid_name,
                'groove_offset_ms': round(float(groove_offset_ms), 2),
                'mean_error_ms': round(float(mean_dev), 2),  # Relative to groove
                'abs_mean_error_ms': round(float(np.mean(np.abs(groove_corrected))), 2),
                'std_dev_ms': round(float(std_dev), 2),
                'iqr_ms': round(float(iqr), 2),
                'median_offset_ms': round(float(median), 2),
                'outlier_percentage': round(float(outlier_pct), 1),
                'timing_score': round(float(consistency_score), 1),
                'tendency': tendency,
            }
            
            # Add rating based on consistency score
            if consistency_score >= 90:
                quality_metrics[drum]['rating'] = 'Tight'
            elif consistency_score >= 70:
                quality_metrics[drum]['rating'] = 'Good'
            elif consistency_score >= 40:
                quality_metrics[drum]['rating'] = 'Fair'
            else:
                quality_metrics[drum]['rating'] = 'Loose'
        
        # Add metadata about groove detection
        quality_metrics['_groove_metadata'] = {
            'groove_offset_ms': round(float(groove_offset_ms), 2),
            'reference_drum': reference_drum,
            'analysis_mode': 'groove-aware'
        }
        
        return quality_metrics
    
    def _detect_groove_offset(self, drum_beats: Dict) -> Tuple[float, Optional[str]]:
        """Detect player's groove offset from a stable window of hits.
        
        Returns:
            (groove_offset_ms, reference_drum_name)
        """
        # Priority order for reference drums (most reliable first)
        priority = ['Bass Drum 1', 'Acoustic Snare', 'Closed Hi-Hat', 'Acoustic Bass Drum']
        
        reference_drum = None
        best_consistency = float('inf')
        best_offsets = None
        
        for drum_name in priority:
            if drum_name not in drum_beats:
                continue
            
            hits = drum_beats[drum_name]
            if len(hits) < 16:  # Need at least 16 hits
                continue
            
            # Skip first/last 10% (intro/outro often unstable)
            start_idx = max(1, len(hits) // 10)
            end_idx = len(hits) - max(1, len(hits) // 10)
            stable_hits = hits[start_idx:end_idx]
            
            if len(stable_hits) < 8:
                continue
            
            # Find best grid size for this drum
            grid_sizes = [0.25, 0.5, 1.0]  # 16th, 8th, quarter
            best_grid = None
            min_error = float('inf')
            
            for grid_size in grid_sizes:
                offsets = self._calculate_grid_offsets(stable_hits, grid_size)
                total_error = np.sum(np.abs(offsets))
                if total_error < min_error:
                    min_error = total_error
                    best_grid = grid_size
            
            # Calculate offsets with best grid
            offsets = self._calculate_grid_offsets(stable_hits, best_grid)
            
            # Check consistency using IQR
            q1, q3 = np.percentile(offsets, [25, 75])
            iqr = q3 - q1
            
            if iqr < best_consistency:
                best_consistency = iqr
                reference_drum = drum_name
                best_offsets = offsets
        
        if best_offsets is None or len(best_offsets) == 0:
            return 0.0, None  # Fallback: no groove offset
        
        # Take middle 8-16 hits for groove reference
        n_reference = min(16, max(8, len(best_offsets) // 4))
        middle_start = (len(best_offsets) - n_reference) // 2
        groove_window = best_offsets[middle_start:middle_start + n_reference]
        
        # Use MEDIAN (robust to outliers)
        groove_offset = np.median(groove_window)
        
        return groove_offset, reference_drum
    
    def _calculate_grid_offsets(self, hits: List[Dict], grid_size: float) -> np.ndarray:
        """Calculate timing offsets from grid for a list of hits.
        
        Returns:
            Array of offsets in milliseconds (negative = early, positive = late)
        """
        offsets_ms = []
        
        beat_duration_sec = mido.tick2second(
            self.ticks_per_beat,
            self.ticks_per_beat,
            self.tempo
        )
        
        for hit in hits:
            beat_pos = hit['beat_position']
            
            # Position within grid
            pos_in_grid = beat_pos % grid_size
            
            # Distance to nearest grid line
            if pos_in_grid <= grid_size / 2:
                error_beats = pos_in_grid  # Early
            else:
                error_beats = pos_in_grid - grid_size  # Late
            
            # Convert to ms
            error_ms = error_beats * beat_duration_sec * 1000
            offsets_ms.append(error_ms)
        
        return np.array(offsets_ms)
    
    def analyze(self, mode: str = 'groove-aware') -> Dict:
        """Analyze the MIDI file and return beat analysis data."""
        beats = []
        drum_counts = defaultdict(int)
        
        # Merge all tracks to track tempo properly
        all_messages = []
        for track in self.midi.tracks:
            tick = 0
            for msg in track:
                tick += msg.time
                all_messages.append((tick, msg))
        
        all_messages.sort(key=lambda x: x[0])
        
        # Build tempo map
        tempo_map = [(0, self.tempo)]
        for tick, msg in all_messages:
            if msg.type == 'set_tempo':
                tempo_map.append((tick, msg.tempo))
        
        # Helper to convert tick to seconds with tempo changes
        def tick_to_seconds(target_tick):
            seconds = 0.0
            prev_tick = 0
            prev_tempo = tempo_map[0][1]
            
            for tick, tempo in tempo_map[1:]:
                if tick > target_tick:
                    seconds += mido.tick2second(target_tick - prev_tick, self.ticks_per_beat, prev_tempo)
                    return seconds
                seconds += mido.tick2second(tick - prev_tick, self.ticks_per_beat, prev_tempo)
                prev_tick = tick
                prev_tempo = tempo
            
            seconds += mido.tick2second(target_tick - prev_tick, self.ticks_per_beat, prev_tempo)
            return seconds
        
        # Process drum hits
        for tick, msg in all_messages:
            if msg.type == 'note_on' and msg.velocity > 0 and msg.note in DRUM_MAP:
                time_seconds = tick_to_seconds(tick)
                beat_position = tick / self.ticks_per_beat
                drum_name = DRUM_MAP[msg.note]
                
                beats.append({
                    'time_seconds': round(time_seconds, 4),
                    'beat_position': round(beat_position, 4),
                    'note': msg.note,
                    'drum': drum_name,
                    'velocity': msg.velocity,
                    'channel': msg.channel
                })
                
                drum_counts[drum_name] += 1
        
        # Sort beats by time
        beats.sort(key=lambda x: x['time_seconds'])
        
        # Calculate total duration
        max_tick = all_messages[-1][0] if all_messages else 0
        total_duration = tick_to_seconds(max_tick)
        bpm = mido.tempo2bpm(tempo_map[0][1])
        
        # Calculate timing quality based on mode
        if mode == 'groove-aware':
            timing_quality = self.calculate_groove_aware_quality(beats)
        elif mode == 'grid-based':
            timing_quality = self.calculate_timing_quality(beats)
        else:
            raise ValueError(f"Unknown analysis mode: {mode}. Use 'groove-aware' or 'grid-based'")
        
        return {
            'file': self.midi_file,
            'duration_seconds': round(total_duration, 2),
            'tempo_bpm': round(bpm, 2),
            'ticks_per_beat': self.ticks_per_beat,
            'total_beats': len(beats),
            'drum_counts': dict(drum_counts),
            'beats': beats,
            'timing_quality': timing_quality,
            'analysis_mode': mode
        }
    
    def print_summary(self, analysis: Dict, filter_drum: str = None):
        """Print a summary of the analysis.
        
        Args:
            analysis: Analysis data dictionary
            filter_drum: Optional drum name to filter output (e.g., "Acoustic Snare")
        """
        mode = analysis.get('analysis_mode', 'grid-based')
        mode_label = '🎵 Groove-Aware' if mode == 'groove-aware' else '📏 Grid-Based'
        
        print(f"\n{'='*60}")
        print(f"MIDI Drum Analysis: {analysis['file']}")
        print(f"{'='*60}")
        print(f"Analysis Mode: {mode_label}")
        print(f"Duration: {analysis['duration_seconds']}s")
        print(f"Tempo: {analysis['tempo_bpm']} BPM")
        
        if filter_drum:
            print(f"Filter: {filter_drum}")
            filtered_hits = sum(1 for b in analysis['beats'] if b['drum'] == filter_drum)
            print(f"Total Drum Hits: {filtered_hits}")
        else:
            print(f"Total Drum Hits: {analysis['total_beats']}")
        # Only show drum breakdown if not filtering
        if not filter_drum:
            print(f"\n{'Drum Breakdown:':-^60}")
            
            for drum, count in sorted(
                analysis['drum_counts'].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                print(f"  {drum:<25} {count:>5} hits")
        
        # Print timing quality analysis
        mode = analysis.get('analysis_mode', 'grid-based')
        print(f"\n{'TIMING QUALITY ANALYSIS':-^60}")
        if mode == 'groove-aware':
            print(f"Measures timing consistency relative to your natural groove")
            print(f"Detects your groove offset, then measures consistency around it\n")
        else:
            print(f"Measures absolute timing deviation from tempo grid (quantization)")
            print(f"Each hit compared to nearest beat position\n")
        
        timing_quality = analysis.get('timing_quality', {})
        
        # Filter timing quality if requested
        if filter_drum:
            if filter_drum not in timing_quality:
                print(f"\nError: Drum '{filter_drum}' not found in analysis.")
                print(f"\nAvailable drums:")
                for drum in sorted(timing_quality.keys()):
                    print(f"  - {drum}")
                return
            timing_quality = {filter_drum: timing_quality[filter_drum]}
        
        print(f"\n{'Timing Perfection Scores (Higher is Better)':-^60}")
        
        # Filter out metadata entries (start with _)
        drum_quality = {k: v for k, v in timing_quality.items() if not k.startswith('_')}
        
        # Sort by timing score (worst first to highlight areas needing work)
        sorted_quality = sorted(
            drum_quality.items(),
            key=lambda x: x[1]['timing_score']
        )
        
        if sorted_quality:
            print(f"\n  {'Drum':<25} {'Score':>6} {'Rating':<12} {'Error':>8} {'Hits':>5}")
            print(f"  {'-'*60}")
            
            for drum, metrics in sorted_quality:
                score = metrics['timing_score']
                rating = metrics['rating']
                avg_error = metrics['abs_mean_error_ms']
                hits = metrics['hit_count']
                
                # Color-code the rating (using text indicators)
                if score >= 70:
                    indicator = '✓'
                elif score >= 40:
                    indicator = '~'
                else:
                    indicator = '✗'
                
                print(f"  {drum:<25} {score:>6.1f} {rating:<12} {avg_error:>6.1f}ms {hits:>5} {indicator}")
            
            # Print detailed statistics for worst performers
            print(f"\n{'Detailed Statistics (Areas Needing Work)':-^60}")
            worst_performers = [item for item in sorted_quality if item[1]['timing_score'] < 70][:5]
            
            if worst_performers:
                for drum, metrics in worst_performers:
                    print(f"\n  {drum}:")
                    print(f"    Timing Score:     {metrics['timing_score']:.1f}/100 ({metrics['rating']})")
                    print(f"    Total Hits:       {metrics['hit_count']}")
                    print(f"    Quantized to:     {metrics['grid_name']}")
                    print(f"    Avg Error:        {metrics['abs_mean_error_ms']:.2f}ms (absolute)")
                    print(f"    Mean Deviation:   {metrics['mean_error_ms']:+.2f}ms ({metrics['tendency']})")
                    print(f"    Std Deviation:    {metrics['std_dev_ms']:.2f}ms")
                    print(f"    Error Range:      {metrics['max_early_ms']:.2f}ms (early) to {metrics['max_late_ms']:.2f}ms (late)")
                    
                    # Interpretation
                    error = metrics['abs_mean_error_ms']
                    mean_dev = metrics['mean_error_ms']
                    
                    if error < 5:
                        print(f"    → Excellent timing - studio quality")
                    elif error < 10:
                        print(f"    → Good timing - tight drumming")
                    elif error < 20:
                        print(f"    → Fair timing - noticeable drift")
                    else:
                        print(f"    → Poor timing - practice with metronome")
                    
                    if abs(mean_dev) > 5:
                        if mean_dev > 0:
                            print(f"    → Consistently rushing - try relaxing the tempo")
                        else:
                            print(f"    → Consistently dragging - try pushing the tempo")
            else:
                print(f"\n  All drums show excellent timing! Keep it up!")
        
        # Filter beats if requested
        beats_to_show = analysis['beats']
        if filter_drum:
            beats_to_show = [b for b in analysis['beats'] if b['drum'] == filter_drum]
        
        print(f"\n{'First 10 Beats:':-^60}")
        for beat in beats_to_show[:10]:
            print(f"  {beat['time_seconds']:>7.3f}s | "
                  f"Beat {beat['beat_position']:>6.2f} | "
                  f"{beat['drum']:<25} | "
                  f"Vel: {beat['velocity']:>3}")
        
        if len(beats_to_show) > 10:
            print(f"  ... and {len(beats_to_show) - 10} more beats")
        
        mode = analysis.get('analysis_mode', 'grid-based')
        print(f"\n{'Legend:':-^60}")
        print(f"  Score   = Timing tightness (higher = closer to grid)")
        if mode == 'groove-aware':
            print(f"  Error   = IQR (consistency) in milliseconds")
        else:
            print(f"  Error   = Average deviation from perfect timing (ms)")
        print(f"  ✓       = Good timing (70+, <10ms avg error)")
        print(f"  ~       = Fair timing (40-69, 10-20ms avg error)")
        print(f"  ✗       = Needs work (<40, >20ms avg error)")
        if mode == 'groove-aware':
            print(f"\nNote: Groove-aware mode detects your natural groove offset,")
            print(f"      then measures consistency (IQR) around that groove.")
            print(f"      Lower IQR = tighter, more consistent timing.")
        else:
            print(f"\nNote: Each hit is quantized to nearest grid position (16th/8th/quarter)")
            print(f"      and deviation measured. Positive = late, negative = early.")
        print(f"{'='*60}\n")


def analyze_midi_drums(midi_file: str, filter_drum: str = None, mode: str = 'groove-aware') -> Dict:
    """Analyze a MIDI drum file and return beat analysis data.
    
    Args:
        midi_file: Path to the MIDI file
        filter_drum: Optional drum name to filter output (e.g., "Acoustic Snare")
        mode: Analysis mode - 'groove-aware' (default) or 'grid-based'
        
    Returns:
        Dictionary containing beat analysis data
    """
    analyzer = DrumAnalyzer(midi_file)
    analysis = analyzer.analyze(mode=mode)
    analyzer.print_summary(analysis, filter_drum=filter_drum)
    return analysis


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m audio.drum_analyzer <midi_file>")
        sys.exit(1)
    
    midi_file = sys.argv[1]
    analyze_midi_drums(midi_file)
