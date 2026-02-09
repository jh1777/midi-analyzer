"""Compare MIDI drum performance against audio drum track.

This module provides tools to:
1. Extract drum hit timings from audio files (onset detection)
2. Extract drum hit timings from MIDI files
3. Align MIDI and audio timelines (handle tempo/offset differences)
4. Compare performance and generate accuracy metrics
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

try:
    import librosa
    import soundfile as sf
    from scipy.spatial.distance import cdist
    from scipy.optimize import linear_sum_assignment
except ImportError:
    raise ImportError(
        "Audio comparison requires additional dependencies. Install with:\n"
        "  pip install librosa scipy soundfile"
    )

from audio.drum_analyzer import DrumAnalyzer, DRUM_MAP


class PlayAlongComparator:
    """Compare MIDI drum performance against reference audio."""
    
    def __init__(
        self,
        midi_file: str,
        audio_file: str,
        match_threshold_ms: float = 50.0,
        onset_threshold: float = 0.3
    ):
        """Initialize comparator.
        
        Args:
            midi_file: Path to MIDI drum performance
            audio_file: Path to reference audio drum track (MP3/WAV)
            match_threshold_ms: Max time difference to consider a match (default 50ms)
            onset_threshold: Sensitivity for onset detection (0-1, higher = less sensitive)
        """
        self.midi_file = Path(midi_file)
        self.audio_file = Path(audio_file)
        self.match_threshold_ms = match_threshold_ms
        self.onset_threshold = onset_threshold
        
        # Will be populated by analyze()
        self.midi_onsets = []
        self.audio_onsets = []
        self.aligned_midi_onsets = []
        self.results = {}
    
    def detect_audio_onsets(self) -> np.ndarray:
        """Detect drum hit timings from audio file.
        
        Returns:
            Array of onset times in seconds
        """
        print(f"Loading audio: {self.audio_file}")
        
        # Load audio file
        y, sr = librosa.load(str(self.audio_file), sr=None)
        
        print(f"Detecting onsets (sample rate: {sr} Hz)...")
        
        # Use onset strength detection optimized for drums
        # This combines energy and spectral information
        onset_env = librosa.onset.onset_strength(
            y=y, sr=sr, aggregate=np.median
        )
        
        # Detect onset peaks
        onsets_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            units='frames',
            backtrack=True,
            pre_max=3,
            post_max=3,
            pre_avg=3,
            post_avg=5,
            delta=self.onset_threshold,
            wait=10  # Minimum gap between onsets (100ms at default hop)
        )
        
        # Convert frames to seconds
        onsets_seconds = librosa.frames_to_time(
            onsets_frames, sr=sr, hop_length=512
        )
        
        print(f"Detected {len(onsets_seconds)} onsets in audio")
        
        return onsets_seconds
    
    def extract_midi_onsets(self) -> List[float]:
        """Extract drum hit timings from MIDI file.
        
        Returns:
            List of onset times in seconds
        """
        print(f"Analyzing MIDI: {self.midi_file}")
        
        analyzer = DrumAnalyzer(str(self.midi_file))
        analysis = analyzer.analyze()
        
        # Extract all beat times
        beats = analysis['beats']
        onsets = sorted([beat['time_seconds'] for beat in beats])
        
        print(f"Extracted {len(onsets)} MIDI hits")
        
        return onsets
    
    def align_timelines(
        self,
        midi_onsets: np.ndarray,
        audio_onsets: np.ndarray
    ) -> Tuple[np.ndarray, float, float]:
        """Align MIDI timeline to audio timeline.
        
        Handles:
        - Time offset (MIDI starts before/after audio)
        - Tempo drift (slight BPM differences)
        
        Args:
            midi_onsets: MIDI hit times
            audio_onsets: Audio onset times
            
        Returns:
            Tuple of (aligned_midi_onsets, time_offset, tempo_ratio)
        """
        print("Aligning MIDI to audio timeline...")
        
        # Use first 20 onsets for alignment (more robust than using all)
        n_align = min(20, len(midi_onsets), len(audio_onsets))
        
        if n_align < 5:
            print("Warning: Too few onsets for reliable alignment")
            return midi_onsets, 0.0, 1.0
        
        # Try multiple offset/tempo combinations and pick best match
        best_score = float('inf')
        best_offset = 0.0
        best_tempo_ratio = 1.0
        
        # Estimate rough offset based on where MIDI starts vs audio length
        midi_start = midi_onsets[0] if len(midi_onsets) > 0 else 0
        audio_end = audio_onsets[-1] if len(audio_onsets) > 0 else 0
        
        # If MIDI starts very late, adjust search range
        if midi_start > audio_end:
            # MIDI starts after audio ends - need large negative offset
            offset_range = np.linspace(-midi_start - 10, -midi_start + audio_end + 10, 50)
        else:
            # Normal case - search reasonable range
            offset_range = np.linspace(-10, 10, 50)
        
        # Search for time offset
        for offset in offset_range:
            # Search for tempo ratio
            for tempo_ratio in np.linspace(0.95, 1.05, 20):
                # Transform MIDI onsets
                transformed = (midi_onsets[:n_align] * tempo_ratio) + offset
                
                # Calculate distance to nearest audio onset
                distances = np.abs(
                    transformed[:, np.newaxis] - audio_onsets[np.newaxis, :n_align]
                )
                min_distances = np.min(distances, axis=1)
                score = np.sum(min_distances)
                
                if score < best_score:
                    best_score = score
                    best_offset = offset
                    best_tempo_ratio = tempo_ratio
        
        # Apply best alignment to all MIDI onsets
        aligned = (midi_onsets * best_tempo_ratio) + best_offset
        
        print(f"Alignment: offset={best_offset:.3f}s, tempo_ratio={best_tempo_ratio:.4f}")
        
        return aligned, best_offset, best_tempo_ratio
    
    def match_onsets(
        self,
        midi_onsets: np.ndarray,
        audio_onsets: np.ndarray,
        threshold_ms: float
    ) -> Dict:
        """Match MIDI hits to audio onsets and calculate metrics.
        
        Args:
            midi_onsets: MIDI hit times (aligned)
            audio_onsets: Audio onset times
            threshold_ms: Maximum time difference for a match
            
        Returns:
            Dictionary with match results and metrics
        """
        print(f"Matching onsets (threshold: {threshold_ms}ms)...")
        
        threshold_s = threshold_ms / 1000.0
        
        # Calculate distance matrix
        distances = cdist(
            midi_onsets.reshape(-1, 1),
            audio_onsets.reshape(-1, 1),
            metric='euclidean'
        )
        
        # Use Hungarian algorithm for optimal matching
        midi_idx, audio_idx = linear_sum_assignment(distances)
        
        # Filter matches by threshold
        matched_pairs = []
        matched_midi = set()
        matched_audio = set()
        
        for m_idx, a_idx in zip(midi_idx, audio_idx):
            distance = distances[m_idx, a_idx]
            if distance <= threshold_s:
                matched_pairs.append({
                    'midi_time': midi_onsets[m_idx],
                    'audio_time': audio_onsets[a_idx],
                    'error_ms': distance * 1000,
                    'midi_idx': m_idx,
                    'audio_idx': a_idx
                })
                matched_midi.add(m_idx)
                matched_audio.add(a_idx)
        
        # Find unmatched onsets
        extra_midi = [
            {'time': midi_onsets[i], 'idx': i}
            for i in range(len(midi_onsets))
            if i not in matched_midi
        ]
        
        missed_audio = [
            {'time': audio_onsets[i], 'idx': i}
            for i in range(len(audio_onsets))
            if i not in matched_audio
        ]
        
        # Calculate statistics
        errors_ms = [m['error_ms'] for m in matched_pairs]
        
        results = {
            'total_midi_hits': len(midi_onsets),
            'total_audio_onsets': len(audio_onsets),
            'matched_hits': len(matched_pairs),
            'extra_hits': len(extra_midi),
            'missed_hits': len(missed_audio),
            'match_percentage': (len(matched_pairs) / len(midi_onsets) * 100) if len(midi_onsets) > 0 else 0,
            'mean_error_ms': np.mean(errors_ms) if errors_ms else 0,
            'std_error_ms': np.std(errors_ms) if errors_ms else 0,
            'matched_pairs': matched_pairs,
            'extra_midi_hits': extra_midi,
            'missed_audio_onsets': missed_audio,
        }
        
        # Calculate accuracy tiers
        if matched_pairs:
            within_30ms = sum(1 for m in matched_pairs if m['error_ms'] <= 30)
            within_50ms = sum(1 for m in matched_pairs if m['error_ms'] <= 50)
            within_100ms = sum(1 for m in matched_pairs if m['error_ms'] <= 100)
            
            total = len(midi_onsets)
            results['within_30ms'] = within_30ms
            results['within_50ms'] = within_50ms
            results['within_100ms'] = within_100ms
            results['within_30ms_pct'] = (within_30ms / total * 100)
            results['within_50ms_pct'] = (within_50ms / total * 100)
            results['within_100ms_pct'] = (within_100ms / total * 100)
        
        return results
    
    def analyze(self) -> Dict:
        """Run complete analysis.
        
        Returns:
            Dictionary with complete comparison results
        """
        print("\n" + "="*60)
        print("PLAY-ALONG COMPARISON")
        print("="*60)
        
        # Step 1: Extract onsets
        self.audio_onsets = self.detect_audio_onsets()
        self.midi_onsets = np.array(self.extract_midi_onsets())
        
        if len(self.midi_onsets) == 0:
            raise ValueError("No MIDI hits found")
        if len(self.audio_onsets) == 0:
            raise ValueError("No audio onsets detected")
        
        # Step 2: Align timelines
        self.aligned_midi_onsets, offset, tempo_ratio = self.align_timelines(
            self.midi_onsets, self.audio_onsets
        )
        
        # Step 3: Match and analyze
        self.results = self.match_onsets(
            self.aligned_midi_onsets,
            self.audio_onsets,
            self.match_threshold_ms
        )
        
        # Add metadata
        self.results['midi_file'] = str(self.midi_file.name)
        self.results['audio_file'] = str(self.audio_file.name)
        self.results['alignment_offset'] = offset
        self.results['alignment_tempo_ratio'] = tempo_ratio
        self.results['match_threshold_ms'] = self.match_threshold_ms
        
        return self.results
    
    def print_report(self):
        """Print detailed comparison report."""
        if not self.results:
            print("No results available. Run analyze() first.")
            return
        
        r = self.results
        
        print("\n" + "="*60)
        print("COMPARISON REPORT")
        print("="*60)
        print(f"Your MIDI: {r['midi_file']}")
        print(f"Reference Audio: {r['audio_file']}")
        print(f"Match Threshold: {r['match_threshold_ms']}ms")
        
        print(f"\n{'OVERALL STATISTICS':-^60}")
        print(f"Your MIDI Hits:        {r['total_midi_hits']}")
        print(f"Audio Drum Onsets:     {r['total_audio_onsets']}")
        print(f"Matched Hits:          {r['matched_hits']}")
        print(f"Match Percentage:      {r['match_percentage']:.1f}%")
        
        print(f"\n{'TIMING ACCURACY':-^60}")
        if r['matched_hits'] > 0:
            print(f"Mean Error:            {r['mean_error_ms']:.1f}ms (±{r['std_error_ms']:.1f}ms)")
            print(f"Within 30ms:           {r['within_30ms']:3d} hits ({r['within_30ms_pct']:.1f}%)")
            print(f"Within 50ms:           {r['within_50ms']:3d} hits ({r['within_50ms_pct']:.1f}%)")
            print(f"Within 100ms:          {r['within_100ms']:3d} hits ({r['within_100ms_pct']:.1f}%)")
        
        print(f"\n{'MISSED HITS':-^60}")
        print(f"Missed Hits:           {r['missed_hits']} (you should have played these)")
        if r['missed_hits'] > 0 and r['missed_hits'] <= 10:
            for miss in r['missed_audio_onsets'][:10]:
                mins = int(miss['time'] // 60)
                secs = int(miss['time'] % 60)
                print(f"  - {mins}:{secs:02d} ({miss['time']:.2f}s)")
        
        print(f"\n{'EXTRA HITS':-^60}")
        print(f"Extra Hits:            {r['extra_hits']} (not in original)")
        if r['extra_hits'] > 0 and r['extra_hits'] <= 10:
            for extra in r['extra_midi_hits'][:10]:
                mins = int(extra['time'] // 60)
                secs = int(extra['time'] % 60)
                print(f"  - {mins}:{secs:02d} ({extra['time']:.2f}s)")
        
        print(f"\n{'PERFORMANCE SCORE':-^60}")
        # Calculate overall score (0-100)
        match_score = r['match_percentage']
        timing_score = r['within_50ms_pct'] if r['matched_hits'] > 0 else 0
        overall_score = (match_score * 0.6) + (timing_score * 0.4)
        
        print(f"Overall Score:         {overall_score:.1f}/100")
        
        if overall_score >= 90:
            rating = "Excellent! 🎉"
        elif overall_score >= 80:
            rating = "Great! 👍"
        elif overall_score >= 70:
            rating = "Good 👌"
        elif overall_score >= 60:
            rating = "Fair 🙂"
        else:
            rating = "Needs Practice 💪"
        
        print(f"Rating:                {rating}")
        
        print("="*60 + "\n")


def compare_playalong(midi_file: str, audio_file: str, threshold_ms: float = 50.0) -> Dict:
    """Convenience function to compare MIDI performance to audio reference.
    
    Args:
        midi_file: Path to MIDI drum performance
        audio_file: Path to reference audio drum track
        threshold_ms: Match threshold in milliseconds
        
    Returns:
        Dictionary with comparison results
    """
    comparator = PlayAlongComparator(midi_file, audio_file, threshold_ms)
    results = comparator.analyze()
    comparator.print_report()
    return results
