'use client'

import { useQuery } from '@tanstack/react-query'
import { getPatentClaims } from '@/lib/api'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'

interface ClaimViewerProps {
  patentId: string
}

export function ClaimViewer({ patentId }: ClaimViewerProps) {
  const [expandedClaims, setExpandedClaims] = useState<Set<number>>(new Set())

  const { data: claims, isLoading, error } = useQuery({
    queryKey: ['patent-claims', patentId],
    queryFn: () => getPatentClaims(patentId),
  })

  const toggleClaim = (claimNumber: number) => {
    const newExpanded = new Set(expandedClaims)
    if (newExpanded.has(claimNumber)) {
      newExpanded.delete(claimNumber)
    } else {
      newExpanded.add(claimNumber)
    }
    setExpandedClaims(newExpanded)
  }

  if (isLoading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Claims</h3>
        </div>
        <div className="card-content">
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            <span className="ml-2">Loading claims...</span>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Claims</h3>
        </div>
        <div className="card-content">
          <div className="text-center py-4 text-destructive">
            Error loading claims
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Claims</h3>
        <p className="card-description">
          Patent claims with clause-level analysis
        </p>
      </div>
      <div className="card-content">
        {claims && claims.length > 0 ? (
          <div className="space-y-2">
            {claims.map((claim) => (
              <div key={claim.id} className="border rounded-lg">
                <button
                  onClick={() => toggleClaim(claim.claim_number)}
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">
                      Claim {claim.claim_number}
                    </span>
                    {claim.is_independent && (
                      <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                        Independent
                      </span>
                    )}
                  </div>
                  {expandedClaims.has(claim.claim_number) ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>
                
                {expandedClaims.has(claim.claim_number) && (
                  <div className="px-3 pb-3">
                    <div className="text-sm text-muted-foreground leading-relaxed">
                      {claim.text}
                    </div>
                    
                    {/* Claim analysis would go here */}
                    <div className="mt-3 pt-3 border-t">
                      <div className="text-xs text-muted-foreground">
                        Analysis features coming soon...
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-4 text-muted-foreground">
            No claims found for this patent
          </div>
        )}
      </div>
    </div>
  )
}
