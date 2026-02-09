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
        onset_threshold: float = 0.3,
        audio_bpm: Optional[float] = None,
        midi_bpm: Optional[float] = None
    ):
        """Initialize comparator.
        
        Args:
            midi_file: Path to MIDI drum performance
            audio_file: Path to reference audio drum track (MP3/WAV)
            match_threshold_ms: Max time difference to consider a match (default 50ms)
            onset_threshold: Sensitivity for onset detection (0-1, higher = less sensitive)
            audio_bpm: Original tempo of audio file (if known). Will auto-detect if None.
            midi_bpm: Tempo of MIDI recording (if known). Will extract from MIDI if None.
        """
        self.midi_file = Path(midi_file)
        self.audio_file = Path(audio_file)
        self.match_threshold_ms = match_threshold_ms
        self.onset_threshold = onset_threshold
        self.audio_bpm = audio_bpm
        self.midi_bpm = midi_bpm
        
        # Will be populated by analyze()
        self.midi_onsets = []
        self.audio_onsets = []
        self.aligned_midi_onsets = []
        self.results = {}
    
    def detect_audio_onsets(self) -> np.ndarray:
        """Detect drum hit timings from audio file using multi-band approach.
        
        Returns:
            Array of onset times in seconds
        """
        print(f"Loading audio: {self.audio_file}")
        
        # Load audio file at 22050 Hz (good for drum detection)
        y, sr = librosa.load(str(self.audio_file), sr=22050)
        
        print(f"Detecting onsets (sample rate: {sr} Hz)...")
        print(f"Audio duration: {len(y)/sr:.1f}s")
        
        # Step 1: Isolate percussive component (removes tonal instruments)
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=2.0)
        
        # Step 2: Multi-band onset detection
        # Different drums have energy in different frequency bands:
        # - Kick/Bass: 20-150 Hz
        # - Snare: 150-500 Hz + 2-5 kHz
        # - Hi-hat/Cymbals: 5-15 kHz
        
        all_onsets = set()
        
        # Method 1: Percussive component with low threshold
        onset_env_perc = librosa.onset.onset_strength(
            y=y_percussive, sr=sr, aggregate=np.median
        )
        onsets_perc = librosa.onset.onset_detect(
            onset_envelope=onset_env_perc,
            sr=sr,
            units='time',
            backtrack=True,
            delta=self.onset_threshold * 0.3  # Lower threshold for percussive
        )
        all_onsets.update(onsets_perc)
        print(f"  Percussive method: {len(onsets_perc)} onsets")
        
        # Method 2: Low-frequency band (kick drum)
        y_lowpass = librosa.effects.preemphasis(y_percussive, coef=-0.97)  # Enhance bass
        onset_env_low = librosa.onset.onset_strength(
            y=y_lowpass, sr=sr, fmax=300
        )
        onsets_low = librosa.onset.onset_detect(
            onset_envelope=onset_env_low,
            sr=sr,
            units='time',
            backtrack=True,
            delta=self.onset_threshold * 0.4
        )
        all_onsets.update(onsets_low)
        print(f"  Low-freq method (kick): {len(onsets_low)} onsets")
        
        # Method 3: High-frequency band (hi-hat, cymbals)
        y_highpass = y_percussive.copy()
        onset_env_high = librosa.onset.onset_strength(
            y=y_highpass, sr=sr, fmin=4000
        )
        onsets_high = librosa.onset.onset_detect(
            onset_envelope=onset_env_high,
            sr=sr,
            units='time',
            backtrack=True,
            delta=self.onset_threshold * 0.5
        )
        all_onsets.update(onsets_high)
        print(f"  High-freq method (hats): {len(onsets_high)} onsets")
        
        # Merge all detections and remove duplicates within 25ms
        onsets_merged = sorted(all_onsets)
        onsets_deduped = []
        for onset in onsets_merged:
            if not onsets_deduped or (onset - onsets_deduped[-1]) > 0.025:
                onsets_deduped.append(onset)
        
        onsets_seconds = np.array(onsets_deduped)
        
        print(f"Detected {len(onsets_seconds)} total onsets after merging")
        
        if len(onsets_seconds) > 0:
            print(f"  First onset: {onsets_seconds[0]:.2f}s")
            print(f"  Last onset: {onsets_seconds[-1]:.2f}s")
            print(f"  Density: {len(onsets_seconds) / (onsets_seconds[-1] - onsets_seconds[0]):.2f} hits/sec")
        
        # If we know both tempos, time-stretch the onset times to match MIDI tempo
        if self.audio_bpm and self.midi_bpm and abs(self.audio_bpm - self.midi_bpm) > 0.5:
            stretch_ratio = self.midi_bpm / self.audio_bpm
            print(f"\n⚡ Tempo correction: Stretching audio {self.audio_bpm:.1f} BPM → {self.midi_bpm:.1f} BPM")
            print(f"   Stretch ratio: {stretch_ratio:.4f}x")
            onsets_seconds = onsets_seconds * stretch_ratio
            print(f"   New duration: {onsets_seconds[-1]:.1f}s (was {onsets_seconds[-1]/stretch_ratio:.1f}s)")
        
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
        """Align MIDI timeline to audio timeline using iterative refinement.
        
        Strategy:
        1. Coarse alignment: Find initial offset using first 5-10 hits
        2. Fine-tune: Refine tempo ratio using broader range
        3. Validate: Check alignment quality
        
        Handles:
        - Time offset (MIDI starts before/after audio)
        - Tempo drift (slight BPM differences)
        - MIDI files with long silence at start
        
        Args:
            midi_onsets: MIDI hit times
            audio_onsets: Audio onset times
            
        Returns:
            Tuple of (aligned_midi_onsets, time_offset, tempo_ratio)
        """
        print("\nAligning MIDI to audio timeline...")
        print(f"  MIDI: {len(midi_onsets)} hits, range {midi_onsets[0]:.1f}s - {midi_onsets[-1]:.1f}s")
        print(f"  Audio: {len(audio_onsets)} onsets, range {audio_onsets[0]:.1f}s - {audio_onsets[-1]:.1f}s")
        
        if len(midi_onsets) < 5 or len(audio_onsets) < 5:
            print("Warning: Too few onsets for reliable alignment")
            return midi_onsets, 0.0, 1.0
        
        # Step 1: Coarse alignment using first 5-10 hits
        # This finds the rough offset without worrying about tempo
        n_initial = min(10, len(midi_onsets), len(audio_onsets))
        
        midi_start = midi_onsets[0]
        audio_start = audio_onsets[0]
        
        # Calculate inter-onset intervals (IOIs) for pattern matching
        midi_iois = np.diff(midi_onsets[:n_initial])
        
        best_initial_score = float('inf')
        best_initial_offset = -midi_start  # Default: align first hit with t=0
        
        # Search for best matching position in audio
        # Try aligning MIDI start with each audio onset in first 30 seconds
        search_window = min(100, len(audio_onsets))
        
        for audio_idx in range(search_window):
            # Calculate offset to align MIDI[0] with audio[audio_idx]
            offset = audio_onsets[audio_idx] - midi_start
            
            # Transform first N MIDI onsets
            transformed = midi_onsets[:n_initial] + offset
            
            # Check if these fall within audio range
            if transformed[0] < audio_onsets[0] - 5 or transformed[-1] > audio_onsets[-1] + 5:
                continue
            
            # Find nearest audio onset for each transformed MIDI hit
            distances = []
            for t in transformed:
                nearest_idx = np.searchsorted(audio_onsets, t)
                # Check both neighbors
                candidates = []
                if nearest_idx > 0:
                    candidates.append(abs(audio_onsets[nearest_idx - 1] - t))
                if nearest_idx < len(audio_onsets):
                    candidates.append(abs(audio_onsets[nearest_idx] - t))
                if candidates:
                    distances.append(min(candidates))
            
            if distances:
                score = np.mean(distances)
                if score < best_initial_score:
                    best_initial_score = score
                    best_initial_offset = offset
        
        print(f"  Coarse alignment: offset={best_initial_offset:.2f}s, avg_error={best_initial_score*1000:.1f}ms")
        
        # Step 2: Fine-tune tempo ratio around offset
        # Use more hits for tempo estimation
        n_refine = min(50, len(midi_onsets), len(audio_onsets))
        
        best_score = float('inf')
        best_offset = best_initial_offset
        best_tempo_ratio = 1.0
        
        # Search tempo ratios (wider range to handle pitch/tempo shifted audio)
        for tempo_ratio in np.linspace(0.90, 1.10, 40):
            # Search small offset adjustments
            for offset_adjust in np.linspace(-3, 3, 25):
                offset = best_initial_offset + offset_adjust
                
                # Transform MIDI onsets
                transformed = (midi_onsets[:n_refine] * tempo_ratio) + offset
                
                # Calculate distance to nearest audio onset
                distances = []
                for t in transformed:
                    nearest_idx = np.searchsorted(audio_onsets, t)
                    candidates = []
                    if nearest_idx > 0:
                        candidates.append(abs(audio_onsets[nearest_idx - 1] - t))
                    if nearest_idx < len(audio_onsets):
                        candidates.append(abs(audio_onsets[nearest_idx] - t))
                    if candidates:
                        distances.append(min(candidates))
                
                if distances:
                    score = np.mean(distances)
                    if score < best_score:
                        best_score = score
                        best_offset = offset
                        best_tempo_ratio = tempo_ratio
        
        # Apply best alignment to all MIDI onsets
        aligned = (midi_onsets * best_tempo_ratio) + best_offset
        
        print(f"  Final alignment: offset={best_offset:.2f}s, tempo_ratio={best_tempo_ratio:.4f}")
        print(f"  Alignment quality: avg_error={best_score*1000:.1f}ms")
        
        # Validation: check if alignment makes sense
        if aligned[0] < audio_onsets[0] - 10 or aligned[0] > audio_onsets[-1] + 10:
            print("  WARNING: Aligned MIDI is outside audio range - alignment may be poor")
        
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


def compare_playalong(
    midi_file: str,
    audio_file: str,
    threshold_ms: float = 50.0,
    onset_threshold: float = 0.3,
    audio_bpm: Optional[float] = None,
    midi_bpm: Optional[float] = None
) -> Dict:
    """Convenience function to compare MIDI performance to audio reference.
    
    Args:
        midi_file: Path to MIDI drum performance
        audio_file: Path to reference audio drum track
        threshold_ms: Match threshold in milliseconds
        onset_threshold: Onset detection sensitivity (0-1, higher=less sensitive)
        audio_bpm: Original BPM of audio (auto-detected if None)
        midi_bpm: BPM of MIDI recording (extracted from file if None)
        
    Returns:
        Dictionary with comparison results
    """
    comparator = PlayAlongComparator(
        midi_file, audio_file, threshold_ms, onset_threshold,
        audio_bpm, midi_bpm
    )
    results = comparator.analyze()
    comparator.print_report()
    return results
