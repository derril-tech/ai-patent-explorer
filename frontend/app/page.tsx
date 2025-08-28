'use client'

import { useState } from 'react'
import { Search, FileText, BarChart3, Settings, Upload, Download } from 'lucide-react'
import { PatentSearch } from '@/components/PatentSearch'
import { PatentList } from '@/components/PatentList'
import { ClaimViewer } from '@/components/ClaimViewer'
import { AlignmentTable } from '@/components/AlignmentTable'
import { NoveltyCard } from '@/components/NoveltyCard'
import { ChartBuilder } from '@/components/ChartBuilder'
import { GraphView } from '@/components/GraphView'
import { LegalDisclaimer } from '@/components/LegalDisclaimer'

export default function Home() {
  const [activeTab, setActiveTab] = useState('search')
  const [selectedPatent, setSelectedPatent] = useState<string | null>(null)

  const tabs = [
    { id: 'search', label: 'Search', icon: Search },
    { id: 'patents', label: 'Patents', icon: FileText },
    { id: 'charts', label: 'Charts', icon: BarChart3 },
    { id: 'graph', label: 'Graph', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'search':
        return <PatentSearch onPatentSelect={setSelectedPatent} />
      case 'patents':
        return <PatentList onPatentSelect={setSelectedPatent} />
      case 'charts':
        return <ChartBuilder />
      case 'graph':
        return <GraphView />
      case 'settings':
        return <div className="p-6">Settings page coming soon...</div>
      default:
        return <PatentSearch onPatentSelect={setSelectedPatent} />
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-primary">AI Patent Explorer</h1>
              <div className="text-sm text-muted-foreground">
                Advanced patent analysis platform
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button className="btn btn-outline">
                <Upload className="h-4 w-4 mr-2" />
                Import
              </button>
              <button className="btn btn-outline">
                <Download className="h-4 w-4 mr-2" />
                Export
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b bg-card">
        <div className="container mx-auto px-4">
          <div className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-2 border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel */}
          <div className="lg:col-span-2">
            {renderContent()}
          </div>

          {/* Right Panel - Patent Details */}
          {selectedPatent && (
            <div className="space-y-6">
              <ClaimViewer patentId={selectedPatent} />
              <AlignmentTable patentId={selectedPatent} />
              <NoveltyCard patentId={selectedPatent} />
            </div>
          )}
        </div>
      </main>

      {/* Legal Disclaimer */}
      <footer className="border-t bg-muted/50 mt-12">
        <LegalDisclaimer variant="banner" />
      </footer>
    </div>
  )
}
