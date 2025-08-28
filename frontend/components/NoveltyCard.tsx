'use client'

import { useQuery } from '@tanstack/react-query'
import { calculateNovelty } from '@/lib/api'
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'

interface NoveltyCardProps {
  patentId: string
}

export function NoveltyCard({ patentId }: NoveltyCardProps) {
  // Mock data for now - in real implementation, this would come from the API
  const mockNovelty = {
    novelty_score: 0.75,
    obviousness_score: 0.25,
    confidence_band: 'high',
    clause_details: [
      {
        clause_index: 0,
        clause_text: "A method for processing data comprising:",
        novelty_score: 0.8,
        confidence: 'high'
      },
      {
        clause_index: 1,
        clause_text: "receiving input data;",
        novelty_score: 0.6,
        confidence: 'medium'
      },
      {
        clause_index: 2,
        clause_text: "analyzing the data;",
        novelty_score: 0.9,
        confidence: 'high'
      }
    ]
  }

  const getNoveltyColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    if (score >= 0.4) return 'text-orange-600'
    return 'text-red-600'
  }

  const getNoveltyIcon = (score: number) => {
    if (score >= 0.7) return <TrendingUp className="h-4 w-4 text-green-500" />
    if (score >= 0.4) return <AlertCircle className="h-4 w-4 text-yellow-500" />
    return <TrendingDown className="h-4 w-4 text-red-500" />
  }

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'text-green-600 bg-green-50'
      case 'medium':
        return 'text-yellow-600 bg-yellow-50'
      case 'low':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Novelty Analysis</h3>
        <p className="card-description">
          AI-powered novelty and obviousness assessment
        </p>
      </div>
      <div className="card-content">
        {/* Overall Scores */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="text-center p-4 border rounded-lg">
            <div className="flex items-center justify-center space-x-2 mb-2">
              {getNoveltyIcon(mockNovelty.novelty_score)}
              <span className="text-sm font-medium">Novelty Score</span>
            </div>
            <div className={`text-2xl font-bold ${getNoveltyColor(mockNovelty.novelty_score)}`}>
              {Math.round(mockNovelty.novelty_score * 100)}%
            </div>
          </div>
          
          <div className="text-center p-4 border rounded-lg">
            <div className="flex items-center justify-center space-x-2 mb-2">
              <TrendingDown className="h-4 w-4 text-red-500" />
              <span className="text-sm font-medium">Obviousness Score</span>
            </div>
            <div className="text-2xl font-bold text-red-600">
              {Math.round(mockNovelty.obviousness_score * 100)}%
            </div>
          </div>
        </div>

        {/* Confidence Band */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Confidence Level</span>
            <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(mockNovelty.confidence_band)}`}>
              {mockNovelty.confidence_band.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Clause-level Analysis */}
        <div>
          <h4 className="text-sm font-medium mb-3">Clause-level Analysis</h4>
          <div className="space-y-3">
            {mockNovelty.clause_details.map((clause, index) => (
              <div key={index} className="border rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getNoveltyIcon(clause.novelty_score)}
                    <span className="text-sm font-medium">
                      Clause {clause.clause_index}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`text-sm font-medium ${getNoveltyColor(clause.novelty_score)}`}>
                      {Math.round(clause.novelty_score * 100)}%
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(clause.confidence)}`}>
                      {clause.confidence}
                    </span>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground leading-relaxed">
                  {clause.clause_text}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-6 pt-4 border-t">
          <div className="text-xs text-muted-foreground">
            <p className="mb-2">⚠️ Analysis Disclaimer:</p>
            <p>
              This novelty analysis is generated by AI and should be used for research purposes only. 
              It does not constitute legal advice and should not be relied upon for patent decisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
