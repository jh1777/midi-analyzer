# Web UI Feature

The MIDI Drum Timing Analyzer now includes a web-based user interface for analyzing multiple MIDI files at once.

## Overview

The web UI provides:
- **Visual file browser** for all MIDI files in a folder
- **Table view** with timing analysis results
- **Top 5 drums** displayed for each file with error (ms) and score
- **Refresh button** to rescan folder and update results
- **Editable folder path** configuration
- **Loading indicators** during analysis
- **Color-coded ratings** (Excellent/Good/Acceptable/Needs Work/Poor)

## Architecture

### Backend (FastAPI)
- **File**: `api_server.py`
- **Port**: http://localhost:8000
- **Endpoints**:
  - `GET /` - Health check
  - `GET /config` - Get MIDI folder path
  - `POST /config` - Update MIDI folder path
  - `GET /files` - List all MIDI files
  - `GET /analyze/{file_path}` - Analyze specific file
  - `POST /analyze-all` - Analyze all files in folder

### Frontend (React + TypeScript)
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui inspired components
- **Icons**: Lucide React
- **Port**: http://localhost:5173

## Quick Start

### 1. Install Dependencies

```bash
# Backend (if not already installed)
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd web-ui
npm install
```

### 2. Start the Application

**Option A: Automatic startup (recommended)**
```bash
./start.sh
```

**Option B: Manual startup**
```bash
# Terminal 1 - Backend
source venv/bin/activate
python api_server.py

# Terminal 2 - Frontend
cd web-ui
npm run dev
```

### 3. Open Browser

Navigate to http://localhost:5173

## Usage

### Analyzing Files

1. The default folder is `mid-files/` in the project directory
2. Add MIDI files to this folder
3. Click **"Refresh Analysis"** button
4. Wait for analysis to complete (loading indicator shows progress)
5. Results appear in the table

### Changing Folder Path

1. Click the **"Edit"** button next to the folder path
2. Enter a new absolute path (e.g., `/Users/you/my-midi-files`)
3. Click **"Save"**
4. Analysis will automatically refresh with new folder

### Understanding the Table

**Columns:**
- **File**: Filename (with subfolder path if nested)
- **Duration**: Track length in seconds
- **Tempo**: BPM
- **Total Hits**: Total drum hits detected
- **Drum 1-5**: Top 5 drums by timing score (best to worst)

**Drum Details (for each column):**
- **Name**: Drum type (e.g., "Bass Drum 1", "Acoustic Snare")
- **Error**: Average timing deviation in milliseconds
- **Score**: 0-100 timing quality score
- **Rating**: Color-coded rating
  - 🟢 **Excellent** (90-100): <10ms error
  - 🔵 **Good** (70-89): 10-20ms error
  - 🟡 **Acceptable** (40-69): 20-35ms error
  - 🟠 **Needs Work** (20-39): 35-50ms error
  - 🔴 **Poor** (0-19): >50ms error

## Project Structure

```
audio/
├── api_server.py           # FastAPI backend
├── start.sh                # Startup script
└── web-ui/
    ├── src/
    │   ├── components/
    │   │   └── ui/
    │   │       ├── button.tsx
    │   │       └── table.tsx
    │   ├── lib/
    │   │   └── utils.ts
    │   ├── App.tsx         # Main application
    │   └── index.css       # Tailwind styles
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.ts
```

## Development

### Backend Development

The backend uses FastAPI with automatic API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Hot reload:**
```bash
uvicorn api_server:app --reload
```

### Frontend Development

The frontend uses Vite for fast hot module replacement:
```bash
cd web-ui
npm run dev
```

Changes to `.tsx` files automatically reload in the browser.

### Building for Production

```bash
cd web-ui
npm run build
```

Output will be in `web-ui/dist/`

## Configuration

### Default MIDI Folder

The default folder is `mid-files/` relative to the project root. This can be changed:

**Temporarily (via UI):**
Click "Edit" next to the folder path

**Permanently (in code):**
Edit `api_server.py`:
```python
MIDI_FOLDER = Path(__file__).parent / "your-folder-name"
```

### CORS Settings

The backend allows requests from:
- http://localhost:5173 (Vite dev server)
- http://localhost:3000 (alternative dev port)

To add more origins, edit `api_server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://your-origin"],
    ...
)
```

## Troubleshooting

### "Failed to analyze files"
- **Check**: Backend is running on port 8000
- **Solution**: Start backend with `python api_server.py`

### "No MIDI files found"
- **Check**: MIDI files exist in the configured folder
- **Check**: Folder path is correct (absolute path required)
- **Solution**: Add `.mid` files to folder or update folder path

### Port already in use
- **Backend (8000)**: Stop other processes using port 8000
- **Frontend (5173)**: Vite will use next available port automatically

### Analysis is slow
- Large MIDI files take longer to analyze
- Multiple files are analyzed sequentially
- Progress shown via loading indicator

### Browser shows "Cannot GET /"
- **Check**: Frontend dev server is running
- **Check**: Accessing http://localhost:5173 (not :8000)

## API Examples

### Get Configuration
```bash
curl http://localhost:8000/config
```

### Analyze All Files
```bash
curl -X POST http://localhost:8000/analyze-all
```

### Analyze Specific File
```bash
curl http://localhost:8000/analyze/test/drums.mid
```

## Future Enhancements

Potential improvements:
- Export results to CSV/JSON
- File upload via drag & drop
- Real-time analysis progress
- Detailed view modal for individual files
- Comparison view between files
- Historical analysis tracking
- Batch delete/archive files
- Filter/sort table columns
- Dark mode toggle
