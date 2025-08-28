'use client'

import { useState } from 'react'
import { Network, Share2, Download } from 'lucide-react'

export function GraphView() {
  const [graphType, setGraphType] = useState<'citations' | 'family'>('citations')

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Patent Network Graph</h2>
          <p className="card-description">
            Visualize patent relationships and citation networks
          </p>
        </div>
        <div className="card-content">
          <div className="space-y-6">
            {/* Graph Type Selection */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Graph Type</h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setGraphType('citations')}
                  className={`p-4 border rounded-lg text-left transition-colors ${
                    graphType === 'citations'
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <Network className="h-6 w-6 mb-2" />
                  <div className="font-medium">Citation Network</div>
                  <div className="text-sm text-muted-foreground">
                    Visualize patent citations and references
                  </div>
                </button>
                
                <button
                  onClick={() => setGraphType('family')}
                  className={`p-4 border rounded-lg text-left transition-colors ${
                    graphType === 'family'
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <Share2 className="h-6 w-6 mb-2" />
                  <div className="font-medium">Family Network</div>
                  <div className="text-sm text-muted-foreground">
                    Show patent family relationships
                  </div>
                </button>
              </div>
            </div>

            {/* Graph Visualization Placeholder */}
            <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-12 text-center">
              <Network className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">Graph Visualization</h3>
              <p className="text-muted-foreground mb-4">
                Interactive network graph will be displayed here
              </p>
              <div className="text-sm text-muted-foreground">
                Features coming soon:
              </div>
              <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                <li>• Interactive node exploration</li>
                <li>• Citation flow visualization</li>
                <li>• Family tree mapping</li>
                <li>• Centrality analysis</li>
                <li>• Export graph data</li>
              </ul>
            </div>

            {/* Graph Controls */}
            <div className="flex justify-between items-center">
              <div className="flex space-x-2">
                <button className="btn btn-outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export Graph
                </button>
                <button className="btn btn-outline">
                  <Share2 className="h-4 w-4 mr-2" />
                  Share View
                </button>
              </div>
              
              <div className="text-sm text-muted-foreground">
                {graphType === 'citations' ? 'Citation Network' : 'Family Network'} View
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Graph Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="card-content text-center">
            <div className="text-2xl font-bold text-primary">24</div>
            <div className="text-sm text-muted-foreground">Total Patents</div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-content text-center">
            <div className="text-2xl font-bold text-primary">156</div>
            <div className="text-sm text-muted-foreground">Citations</div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-content text-center">
            <div className="text-2xl font-bold text-primary">8</div>
            <div className="text-sm text-muted-foreground">Patent Families</div>
          </div>
        </div>
      </div>
    </div>
  )
}
