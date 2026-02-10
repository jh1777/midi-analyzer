import { useState, useEffect } from 'react'
import { RefreshCw, Settings, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { Button } from './components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './components/ui/table'

interface DrumMetric {
  name: string
  error_ms: number
  score: number
  rating: string
  hit_count: number
  grid_name: string
}

interface FileAnalysis {
  filename: string
  path: string
  duration: number
  tempo: number
  total_hits: number
  avg_timing_ms: number
  timing_tendency: string
  consistency_ms: number
  consistency_rating: string
  top_drums: DrumMetric[]
  error?: string
}

const API_BASE_URL = 'http://localhost:8000'

// Fixed drum columns to display with flexible matching
const DRUM_COLUMNS = [
  { display: 'Snare', matches: ['Snare'] },
  { display: 'Bass Drum', matches: ['Bass'] },
  { display: 'Hi-Hat', matches: ['Hi-Hat', 'Hi Hat'] },
  { display: 'Crash', matches: ['Crash'] },
  { display: 'Ride', matches: ['Ride'] }
]

type SortDirection = 'asc' | 'desc' | null

function App() {
  const [files, setFiles] = useState<FileAnalysis[]>([])
  const [loading, setLoading] = useState(false)
  const [midiFolder, setMidiFolder] = useState('')
  const [editingFolder, setEditingFolder] = useState(false)
  const [newFolder, setNewFolder] = useState('')
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)

  const formatDuration = (seconds: number): string => {
    if (seconds <= 0) return '-'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  useEffect(() => {
    fetchConfig()
    analyzeFiles()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/config`)
      const data = await response.json()
      setMidiFolder(data.midi_folder)
      setNewFolder(data.midi_folder)
    } catch (error) {
      console.error('Failed to fetch config:', error)
    }
  }

  const updateConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ midi_folder: newFolder })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update folder path')
      }
      
      const data = await response.json()
      setMidiFolder(data.midi_folder)
      setEditingFolder(false)
      analyzeFiles()
    } catch (error) {
      console.error('Failed to update config:', error)
      alert(error instanceof Error ? error.message : 'Failed to update folder path')
    }
  }

  const analyzeFiles = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/analyze-all`, {
        method: 'POST'
      })
      const data = await response.json()
      setFiles(data.results || [])
      setSortColumn(null)
      setSortDirection(null)
    } catch (error) {
      console.error('Failed to analyze files:', error)
      alert('Failed to analyze files. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const getRatingColor = (rating: string) => {
    switch (rating.toLowerCase()) {
      case 'excellent':
        return 'text-green-600 font-semibold'
      case 'good':
        return 'text-blue-600 font-semibold'
      case 'acceptable':
        return 'text-yellow-600 font-semibold'
      case 'needs work':
        return 'text-orange-600 font-semibold'
      case 'poor':
        return 'text-red-600 font-semibold'
      default:
        return 'text-gray-600'
    }
  }

  const getRatingValue = (rating: string): number => {
    switch (rating.toLowerCase()) {
      case 'excellent': return 5
      case 'good': return 4
      case 'acceptable': return 3
      case 'needs work': return 2
      case 'poor': return 1
      default: return 0
    }
  }

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      // Cycle through: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc')
      } else if (sortDirection === 'desc') {
        setSortColumn(null)
        setSortDirection(null)
      }
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const getSortedFiles = () => {
    if (!sortColumn || !sortDirection) return files

    // Handle duration and total hits sorting
    if (sortColumn === 'duration') {
      return [...files].sort((a, b) => {
        const diff = a.duration - b.duration
        return sortDirection === 'asc' ? diff : -diff
      })
    }

    if (sortColumn === 'total_hits') {
      return [...files].sort((a, b) => {
        const diff = a.total_hits - b.total_hits
        return sortDirection === 'asc' ? diff : -diff
      })
    }

    if (sortColumn === 'avg_timing') {
      return [...files].sort((a, b) => {
        const diff = a.avg_timing_ms - b.avg_timing_ms
        return sortDirection === 'asc' ? diff : -diff
      })
    }

    if (sortColumn === 'consistency') {
      return [...files].sort((a, b) => {
        const diff = a.consistency_ms - b.consistency_ms
        return sortDirection === 'asc' ? diff : -diff
      })
    }

    // Handle drum column sorting
    const drumColumn = DRUM_COLUMNS.find(col => col.display === sortColumn)
    if (!drumColumn) return files

    return [...files].sort((a, b) => {
      const drumA = a.top_drums.find(d => 
        drumColumn.matches.some(pattern => d.name.includes(pattern))
      )
      const drumB = b.top_drums.find(d => 
        drumColumn.matches.some(pattern => d.name.includes(pattern))
      )

      // Files without the drum go to the end
      if (!drumA && !drumB) return 0
      if (!drumA) return 1
      if (!drumB) return -1

      // Sort by actual numeric score (0-100)
      const scoreA = drumA.score
      const scoreB = drumB.score

      return sortDirection === 'asc' ? scoreA - scoreB : scoreB - scoreA
    })
  }

  const getDrumData = (file: FileAnalysis, drumColumn: { display: string; matches: string[] }) => {
    // Find first drum that matches any of the patterns
    return file.top_drums.find(d => 
      drumColumn.matches.some(pattern => d.name.includes(pattern))
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            MIDI Drum Timing Analyzer
          </h1>
          <p className="text-gray-600">
            Analyze timing quality of your drum recordings
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                MIDI Files Folder
              </label>
              {editingFolder ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newFolder}
                    onChange={(e) => setNewFolder(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="mid-files or /absolute/path"
                  />
                  <Button onClick={updateConfig} size="sm">
                    Save
                  </Button>
                  <Button
                    onClick={() => {
                      setEditingFolder(false)
                      setNewFolder(midiFolder)
                    }}
                    variant="outline"
                    size="sm"
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <code className="px-3 py-2 bg-gray-100 rounded-md text-sm flex-1">
                    {midiFolder}
                  </code>
                  <Button
                    onClick={() => setEditingFolder(true)}
                    variant="outline"
                    size="sm"
                  >
                    <Settings className="w-4 h-4 mr-2" />
                    Edit
                  </Button>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              onClick={analyzeFiles}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Analyzing...' : 'Refresh Analysis'}
            </Button>
          </div>
        </div>

        {files.length === 0 && !loading && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 text-lg">
              No MIDI files found. Add .mid files to the folder and click Refresh.
            </p>
          </div>
        )}

        {files.length > 0 && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px]">File</TableHead>
                  <TableHead className="text-center">
                    <button
                      onClick={() => handleSort('duration')}
                      className="flex items-center justify-center gap-1 hover:text-gray-900 transition-colors mx-auto"
                    >
                      <span>Duration</span>
                      {sortColumn === 'duration' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3 h-3" />
                        ) : (
                          <ArrowDown className="w-3 h-3" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-30" />
                      )}
                    </button>
                  </TableHead>
                  <TableHead className="text-center">Tempo</TableHead>
                  <TableHead className="text-center">
                    <button
                      onClick={() => handleSort('total_hits')}
                      className="flex items-center justify-center gap-1 hover:text-gray-900 transition-colors mx-auto"
                    >
                      <span>Total Hits</span>
                      {sortColumn === 'total_hits' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3 h-3" />
                        ) : (
                          <ArrowDown className="w-3 h-3" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-30" />
                      )}
                    </button>
                  </TableHead>
                  <TableHead className="text-center">
                    <button
                      onClick={() => handleSort('avg_timing')}
                      className="flex items-center justify-center gap-1 hover:text-gray-900 transition-colors mx-auto"
                      title="Weighted average timing error across all drums"
                    >
                      <span>Avg Timing</span>
                      {sortColumn === 'avg_timing' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3 h-3" />
                        ) : (
                          <ArrowDown className="w-3 h-3" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-30" />
                      )}
                    </button>
                  </TableHead>
                  <TableHead className="text-center">
                    <span title="Main timing tendency: early vs late">
                      Tendency
                    </span>
                  </TableHead>
                  <TableHead className="text-center">
                    <button
                      onClick={() => handleSort('consistency')}
                      className="flex items-center justify-center gap-1 hover:text-gray-900 transition-colors mx-auto"
                      title="Timing consistency (standard deviation) - lower is tighter"
                    >
                      <span>Consistency</span>
                      {sortColumn === 'consistency' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3 h-3" />
                        ) : (
                          <ArrowDown className="w-3 h-3" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-30" />
                      )}
                    </button>
                  </TableHead>
                  {DRUM_COLUMNS.map((drumCol) => (
                    <TableHead key={drumCol.display}>
                      <button
                        onClick={() => handleSort(drumCol.display)}
                        className="flex items-center gap-1 hover:text-gray-900 transition-colors"
                      >
                        <span className="text-xs">{drumCol.display}</span>
                        {sortColumn === drumCol.display ? (
                          sortDirection === 'asc' ? (
                            <ArrowUp className="w-3 h-3" />
                          ) : (
                            <ArrowDown className="w-3 h-3" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-30" />
                        )}
                      </button>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {getSortedFiles().map((file) => (
                  <TableRow key={file.path}>
                    <TableCell className="font-medium">
                      <div className="flex flex-col">
                        <span className="text-sm">{file.filename}</span>
                        {file.path !== file.filename && (
                          <span className="text-xs text-gray-500">{file.path}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      {formatDuration(file.duration)}
                    </TableCell>
                    <TableCell className="text-center">
                      {file.tempo > 0 ? `${Math.round(file.tempo)} BPM` : '-'}
                    </TableCell>
                    <TableCell className="text-center">{file.total_hits || '-'}</TableCell>
                    <TableCell className="text-center">
                      {file.avg_timing_ms > 0 ? (
                        <span className={`font-semibold ${
                          file.avg_timing_ms < 10 ? 'text-green-600' :
                          file.avg_timing_ms < 20 ? 'text-blue-600' :
                          file.avg_timing_ms < 35 ? 'text-yellow-600' :
                          file.avg_timing_ms < 50 ? 'text-orange-600' :
                          'text-red-600'
                        }`}>
                          {file.avg_timing_ms}ms
                        </span>
                      ) : '-'}
                    </TableCell>
                    <TableCell className="text-center">
                      {file.timing_tendency ? (
                        <span className={`text-sm font-medium ${
                          file.timing_tendency.includes('Early') ? 'text-blue-600' :
                          file.timing_tendency.includes('Late') ? 'text-orange-600' :
                          'text-gray-600'
                        }`}>
                          {file.timing_tendency}
                        </span>
                      ) : '-'}
                    </TableCell>
                    <TableCell className="text-center">
                      {file.consistency_ms > 0 ? (
                        <div className="flex flex-col">
                          <span className={`text-sm font-semibold ${
                            file.consistency_rating === 'Tight' ? 'text-green-600' :
                            file.consistency_rating === 'Good' ? 'text-blue-600' :
                            file.consistency_rating === 'Fair' ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {file.consistency_rating}
                          </span>
                          <span className="text-xs text-gray-500">
                            ±{file.consistency_ms}ms
                          </span>
                        </div>
                      ) : '-'}
                    </TableCell>
                    {DRUM_COLUMNS.map((drumCol) => {
                      const drum = getDrumData(file, drumCol)
                      return (
                        <TableCell key={drumCol.display}>
                          {drum ? (
                            <div className="flex flex-col">
                              <span className="text-xs text-gray-500">
                                {drum.error_ms}ms
                              </span>
                              <span className={`text-xs ${getRatingColor(drum.rating)}`}>
                                Score: {drum.score}
                              </span>
                              <span className="text-xs text-gray-400">
                                {drum.name}
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-gray-400">-</span>
                          )}
                        </TableCell>
                      )
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <RefreshCw className="w-12 h-12 animate-spin mx-auto text-blue-500 mb-4" />
            <p className="text-gray-600 text-lg">Analyzing MIDI files...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
