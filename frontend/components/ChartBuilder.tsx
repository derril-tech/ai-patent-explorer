'use client'

import { useState } from 'react'
import { Download, FileText, BarChart3 } from 'lucide-react'

export function ChartBuilder() {
  const [selectedPatents, setSelectedPatents] = useState<string[]>([])
  const [chartType, setChartType] = useState<'docx' | 'pdf'>('docx')
  const [includeAlignments, setIncludeAlignments] = useState(true)
  const [includeNovelty, setIncludeNovelty] = useState(true)

  const handleGenerateChart = () => {
    // TODO: Implement chart generation
    console.log('Generating chart with:', {
      selectedPatents,
      chartType,
      includeAlignments,
      includeNovelty
    })
  }

  const handleExportBundle = () => {
    // TODO: Implement export bundle
    console.log('Creating export bundle')
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Chart Builder</h2>
          <p className="card-description">
            Create claim charts and export bundles for patent analysis
          </p>
        </div>
        <div className="card-content">
          <div className="space-y-6">
            {/* Chart Type Selection */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Chart Type</h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setChartType('docx')}
                  className={`p-4 border rounded-lg text-left transition-colors ${
                    chartType === 'docx'
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <FileText className="h-6 w-6 mb-2" />
                  <div className="font-medium">Word Document</div>
                  <div className="text-sm text-muted-foreground">
                    Editable DOCX format with rich formatting
                  </div>
                </button>
                
                <button
                  onClick={() => setChartType('pdf')}
                  className={`p-4 border rounded-lg text-left transition-colors ${
                    chartType === 'pdf'
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <BarChart3 className="h-6 w-6 mb-2" />
                  <div className="font-medium">PDF Report</div>
                  <div className="text-sm text-muted-foreground">
                    Professional PDF format for sharing
                  </div>
                </button>
              </div>
            </div>

            {/* Content Options */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Content Options</h3>
              <div className="space-y-3">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={includeAlignments}
                    onChange={(e) => setIncludeAlignments(e.target.checked)}
                    className="rounded"
                  />
                  <span>Include reference alignments</span>
                </label>
                
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={includeNovelty}
                    onChange={(e) => setIncludeNovelty(e.target.checked)}
                    className="rounded"
                  />
                  <span>Include novelty analysis</span>
                </label>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-4">
              <button
                onClick={handleGenerateChart}
                className="btn btn-primary"
                disabled={selectedPatents.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Generate Chart
              </button>
              
              <button
                onClick={handleExportBundle}
                className="btn btn-outline"
                disabled={selectedPatents.length === 0}
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Export Bundle
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold">Instructions</h3>
        </div>
        <div className="card-content">
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>1. Select patents from your portfolio to include in the chart</p>
            <p>2. Choose your preferred output format (DOCX or PDF)</p>
            <p>3. Configure content options for your analysis</p>
            <p>4. Generate individual charts or export bundles</p>
            <p>5. Download and share your analysis results</p>
          </div>
        </div>
      </div>
    </div>
  )
}
