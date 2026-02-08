# MIDI Drum Timing Analyzer - Web UI

React-based web interface for analyzing MIDI drum files.

## Features

- 📁 Browse and analyze all MIDI files in a folder
- 📊 View timing analysis results in a table
- 🎯 Top 5 drums displayed with error (ms) and score for each file
- 🔄 Refresh button to rescan folder and update analysis
- ⚙️ Configurable MIDI files folder path

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development
- **Tailwind CSS** for styling
- **shadcn/ui** inspired components
- **Lucide React** for icons

## Development

### Prerequisites

- Node.js 18+ and npm
- Python backend running on http://localhost:8000

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The UI will be available at http://localhost:5173

### Build for Production

```bash
npm run build
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`:

- `GET /config` - Get MIDI folder configuration
- `POST /config` - Update MIDI folder path
- `POST /analyze-all` - Analyze all MIDI files in the folder

## Component Structure

```
src/
├── components/
│   └── ui/
│       ├── button.tsx      # Button component
│       └── table.tsx       # Table components
├── lib/
│   └── utils.ts            # Utility functions (cn)
├── App.tsx                 # Main application
└── index.css               # Tailwind styles
```
