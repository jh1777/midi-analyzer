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


class ConfigModel(BaseModel):
    midi_folder: str


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
    return {"midi_folder": str(MIDI_FOLDER)}


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
        analysis = analyzer.analyze()
        
        # Get top 5 drums by hit count
        timing_quality = analysis.get('timing_quality', {})
        
        # Sort by timing score (best first for display)
        sorted_drums = sorted(
            timing_quality.items(),
            key=lambda x: x[1]['timing_score'],
            reverse=True
        )[:5]
        
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
        
        return {
            "filename": Path(file_path).name,
            "path": file_path,
            "duration": analysis['duration_seconds'],
            "tempo": analysis['tempo_bpm'],
            "total_hits": analysis['total_beats'],
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
            analysis = analyzer.analyze()
            
            # Get top 5 drums by timing score
            timing_quality = analysis.get('timing_quality', {})
            sorted_drums = sorted(
                timing_quality.items(),
                key=lambda x: x[1]['timing_score'],
                reverse=True
            )[:5]
            
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
            
            results.append({
                "filename": file_path.name,
                "path": relative_path,
                "duration": analysis['duration_seconds'],
                "tempo": analysis['tempo_bpm'],
                "total_hits": analysis['total_beats'],
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
                "top_drums": [],
                "error": str(e)
            })
    
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
