'use client'

import { useQuery } from '@tanstack/react-query'
import { comparePatents } from '@/lib/api'
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface AlignmentTableProps {
  patentId: string
}

export function AlignmentTable({ patentId }: AlignmentTableProps) {
  // Mock data for now - in real implementation, this would come from the API
  const mockAlignments = [
    {
      clause_index: 0,
      clause_text: "A method for processing data comprising:",
      reference_patent_id: "ref_patent_1",
      reference_clause_text: "A method for processing data comprising:",
      similarity_score: 0.95,
      alignment_type: "exact_match"
    },
    {
      clause_index: 1,
      clause_text: "receiving input data;",
      reference_patent_id: "ref_patent_2",
      reference_clause_text: "receiving input data;",
      similarity_score: 0.88,
      alignment_type: "high_similarity"
    },
    {
      clause_index: 2,
      clause_text: "analyzing the data;",
      reference_patent_id: "ref_patent_3",
      reference_clause_text: "processing the data;",
      similarity_score: 0.72,
      alignment_type: "medium_similarity"
    }
  ]

  const getAlignmentIcon = (type: string) => {
    switch (type) {
      case 'exact_match':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'high_similarity':
        return <CheckCircle className="h-4 w-4 text-yellow-500" />
      case 'medium_similarity':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />
      case 'low_similarity':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-500" />
    }
  }

  const getAlignmentColor = (type: string) => {
    switch (type) {
      case 'exact_match':
        return 'text-green-600 bg-green-50'
      case 'high_similarity':
        return 'text-yellow-600 bg-yellow-50'
      case 'medium_similarity':
        return 'text-orange-600 bg-orange-50'
      case 'low_similarity':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Reference Alignments</h3>
        <p className="card-description">
          Clause-level alignment with reference patents
        </p>
      </div>
      <div className="card-content">
        <div className="space-y-3">
          {mockAlignments.map((alignment, index) => (
            <div key={index} className="border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {getAlignmentIcon(alignment.alignment_type)}
                  <span className="text-sm font-medium">
                    Clause {alignment.clause_index}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium">
                    {Math.round(alignment.similarity_score * 100)}%
                  </span>
                  <span className={`text-xs px-2 py-1 rounded-full ${getAlignmentColor(alignment.alignment_type)}`}>
                    {alignment.alignment_type.replace('_', ' ')}
                  </span>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="font-medium text-muted-foreground mb-1">Target Clause</div>
                  <div className="text-muted-foreground leading-relaxed">
                    {alignment.clause_text}
                  </div>
                </div>
                <div>
                  <div className="font-medium text-muted-foreground mb-1">Reference Clause</div>
                  <div className="text-muted-foreground leading-relaxed">
                    {alignment.reference_clause_text}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t">
          <div className="text-xs text-muted-foreground">
            <p className="mb-2">Alignment Legend:</p>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center space-x-1">
                <CheckCircle className="h-3 w-3 text-green-500" />
                <span>Exact Match</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle className="h-3 w-3 text-yellow-500" />
                <span>High Similarity</span>
              </div>
              <div className="flex items-center space-x-1">
                <AlertTriangle className="h-3 w-3 text-orange-500" />
                <span>Medium Similarity</span>
              </div>
              <div className="flex items-center space-x-1">
                <XCircle className="h-3 w-3 text-red-500" />
                <span>Low Similarity</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
