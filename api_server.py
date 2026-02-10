"""FastAPI server for MIDI drum timing analysis web UI."""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from audio.drum_analyzer import DrumAnalyzer

app = FastAPI(title="MIDI Drum Timing Analyzer API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MIDI_FOLDER = Path(__file__).parent / "mid-files"
ANALYSIS_MODE = "groove-aware"  # Default mode


class ConfigModel(BaseModel):
    midi_folder: str

class AnalysisModeModel(BaseModel):
    mode: str


class FileAnalysis(BaseModel):
    filename: str
    path: str
    duration: float
    tempo: float
    total_hits: int
    top_drums: List[Dict[str, Any]]
    error: Optional[str] = None


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "message": "MIDI Analyzer API"}


@app.get("/config")
def get_config():
    """Get current configuration."""
    return {
        "midi_folder": str(MIDI_FOLDER),
        "analysis_mode": ANALYSIS_MODE
    }


@app.post("/config")
def update_config(config: ConfigModel):
    """Update configuration."""
    global MIDI_FOLDER
    
    # Get the project root directory (where api_server.py is located)
    project_root = Path(__file__).parent
    
    # Handle relative paths by resolving them relative to project root
    new_path = Path(config.midi_folder)
    if not new_path.is_absolute():
        new_path = (project_root / new_path).resolve()
    
    if not new_path.exists():
        raise HTTPException(
            status_code=400, 
            detail=f"Folder does not exist: {new_path}"
        )
    
    MIDI_FOLDER = new_path
    return {"midi_folder": str(MIDI_FOLDER)}

@app.post("/config/analysis-mode")
def update_analysis_mode(mode_config: AnalysisModeModel):
    """Update analysis mode."""
    global ANALYSIS_MODE
    
    if mode_config.mode not in ['groove-aware', 'grid-based']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {mode_config.mode}. Must be 'groove-aware' or 'grid-based'"
        )
    
    ANALYSIS_MODE = mode_config.mode
    return {
        "analysis_mode": ANALYSIS_MODE,
        "message": f"Analysis mode updated to {ANALYSIS_MODE}"
    }


@app.get("/files")
def list_files():
    """List all MIDI files in the configured folder."""
    if not MIDI_FOLDER.exists():
        return {"files": [], "error": "MIDI folder does not exist"}
    
    midi_files = []
    for file in MIDI_FOLDER.rglob("*.mid"):
        midi_files.append({
            "filename": file.name,
            "path": str(file.relative_to(MIDI_FOLDER)),
            "full_path": str(file)
        })
    
    return {"files": sorted(midi_files, key=lambda x: x["filename"])}


@app.get("/analyze/{file_path:path}")
def analyze_file(file_path: str):
    """Analyze a specific MIDI file."""
    full_path = MIDI_FOLDER / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        analyzer = DrumAnalyzer(str(full_path))
        analysis = analyzer.analyze(mode=ANALYSIS_MODE)
        
        # Return all drums (frontend will filter to specific columns)
        # Filter out metadata entries (start with _)
        timing_quality = analysis.get('timing_quality', {})
        drum_quality = {k: v for k, v in timing_quality.items() if not k.startswith('_')}
        
        # Sort by hit count (most played drums first)
        sorted_drums = sorted(
            drum_quality.items(),
            key=lambda x: x[1]['hit_count'],
            reverse=True
        )
        
        top_drums = []
        for drum_name, metrics in sorted_drums:
            top_drums.append({
                "name": drum_name,
                "error_ms": round(metrics['abs_mean_error_ms'], 1),
                "score": round(metrics['timing_score'], 1),
                "rating": metrics['rating'],
                "hit_count": metrics['hit_count'],
                "grid_name": metrics['grid_name']
            })
        
        # Calculate weighted average timing error
        # Weight each drum's error by its hit count
        total_error_weighted = sum(
            metrics['abs_mean_error_ms'] * metrics['hit_count']
            for _, metrics in drum_quality.items()
        )
        total_hits = sum(metrics['hit_count'] for _, metrics in drum_quality.items())
        avg_timing_ms = round(total_error_weighted / total_hits, 1) if total_hits > 0 else 0
        
        # Calculate timing tendency (early vs late)
        # Count percentage of hits that are early (negative error) vs late (positive error)
        total_weighted_error = sum(
            metrics['mean_error_ms'] * metrics['hit_count']
            for _, metrics in drum_quality.items()
        )
        avg_signed_error = total_weighted_error / total_hits if total_hits > 0 else 0
        
        # Determine tendency and calculate percentage
        # We'll estimate the percentage based on mean error magnitude
        # If mean error is positive (late), calculate how "late" the overall tendency is
        if avg_signed_error > 2:  # Threshold for "rushing"
            # Calculate rough percentage - scale based on typical error ranges
            # Assuming most hits are within ±50ms, we normalize to 0-100%
            percentage = min(100, abs(avg_signed_error) / 50 * 100)
            timing_tendency = f"{round(percentage)}% Late"
        elif avg_signed_error < -2:  # Threshold for "dragging"
            percentage = min(100, abs(avg_signed_error) / 50 * 100)
            timing_tendency = f"{round(percentage)}% Early"
        else:
            timing_tendency = "Centered"
        
        # Calculate timing consistency (weighted standard deviation)
        # This shows how much timing varies (tightness)
        total_variance_weighted = sum(
            metrics['std_dev_ms'] ** 2 * metrics['hit_count']
            for _, metrics in drum_quality.items()
        )
        weighted_std_dev = (total_variance_weighted / total_hits) ** 0.5 if total_hits > 0 else 0
        consistency_ms = round(weighted_std_dev, 1)
        
        # Determine consistency rating
        # Standard deviation shows how "tight" the timing is
        # Low std = consistent, High std = inconsistent
        if consistency_ms < 10:
            consistency_rating = "Tight"
        elif consistency_ms < 20:
            consistency_rating = "Good"
        elif consistency_ms < 30:
            consistency_rating = "Fair"
        else:
            consistency_rating = "Loose"
        
        return {
            "filename": Path(file_path).name,
            "path": file_path,
            "duration": analysis['duration_seconds'],
            "tempo": analysis['tempo_bpm'],
            "total_hits": analysis['total_beats'],
            "avg_timing_ms": avg_timing_ms,
            "timing_tendency": timing_tendency,
            "consistency_ms": consistency_ms,
            "consistency_rating": consistency_rating,
            "top_drums": top_drums
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze-all")
def analyze_all_files():
    """Analyze all MIDI files in the folder."""
    if not MIDI_FOLDER.exists():
        raise HTTPException(status_code=400, detail="MIDI folder does not exist")
    
    results = []
    midi_files = list(MIDI_FOLDER.rglob("*.mid"))
    
    for file_path in midi_files:
        relative_path = str(file_path.relative_to(MIDI_FOLDER))
        try:
            analyzer = DrumAnalyzer(str(file_path))
            analysis = analyzer.analyze(mode=ANALYSIS_MODE)
            
            # Return all drums (frontend will filter to specific columns)
            # Filter out metadata entries (start with _)
            timing_quality = analysis.get('timing_quality', {})
            drum_quality = {k: v for k, v in timing_quality.items() if not k.startswith('_')}
            sorted_drums = sorted(
                drum_quality.items(),
                key=lambda x: x[1]['hit_count'],
                reverse=True
            )
            
            top_drums = []
            for drum_name, metrics in sorted_drums:
                top_drums.append({
                    "name": drum_name,
                    "error_ms": round(metrics['abs_mean_error_ms'], 1),
                    "score": round(metrics['timing_score'], 1),
                    "rating": metrics['rating'],
                    "hit_count": metrics['hit_count'],
                    "grid_name": metrics['grid_name']
                })
            
            # Calculate weighted average timing error
            total_error_weighted = sum(
                metrics['abs_mean_error_ms'] * metrics['hit_count']
                for _, metrics in drum_quality.items()
            )
            total_hits_calc = sum(metrics['hit_count'] for _, metrics in drum_quality.items())
            avg_timing_ms = round(total_error_weighted / total_hits_calc, 1) if total_hits_calc > 0 else 0
            
            # Calculate timing tendency
            total_weighted_error = sum(
                metrics['mean_error_ms'] * metrics['hit_count']
                for _, metrics in drum_quality.items()
            )
            avg_signed_error = total_weighted_error / total_hits_calc if total_hits_calc > 0 else 0
            
            if avg_signed_error > 2:
                percentage = min(100, abs(avg_signed_error) / 50 * 100)
                timing_tendency = f"{round(percentage)}% Late"
            elif avg_signed_error < -2:
                percentage = min(100, abs(avg_signed_error) / 50 * 100)
                timing_tendency = f"{round(percentage)}% Early"
            else:
                timing_tendency = "Centered"
            
            # Calculate consistency
            total_variance_weighted = sum(
                metrics['std_dev_ms'] ** 2 * metrics['hit_count']
                for _, metrics in drum_quality.items()
            )
            weighted_std_dev = (total_variance_weighted / total_hits_calc) ** 0.5 if total_hits_calc > 0 else 0
            consistency_ms = round(weighted_std_dev, 1)
            
            if consistency_ms < 10:
                consistency_rating = "Tight"
            elif consistency_ms < 20:
                consistency_rating = "Good"
            elif consistency_ms < 30:
                consistency_rating = "Fair"
            else:
                consistency_rating = "Loose"
            
            results.append({
                "filename": file_path.name,
                "path": relative_path,
                "duration": analysis['duration_seconds'],
                "tempo": analysis['tempo_bpm'],
                "total_hits": analysis['total_beats'],
                "avg_timing_ms": avg_timing_ms,
                "timing_tendency": timing_tendency,
                "consistency_ms": consistency_ms,
                "consistency_rating": consistency_rating,
                "top_drums": top_drums,
                "error": None
            })
            
        except Exception as e:
            results.append({
                "filename": file_path.name,
                "path": relative_path,
                "duration": 0,
                "tempo": 0,
                "total_hits": 0,
                "avg_timing_ms": 0,
                "timing_tendency": "-",
                "consistency_ms": 0,
                "consistency_rating": "-",
                "top_drums": [],
                "error": str(e)
            })
    
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
