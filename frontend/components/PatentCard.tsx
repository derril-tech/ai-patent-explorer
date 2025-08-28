'use client'

import { format } from 'date-fns'
import { FileText, Calendar, Users, Tag } from 'lucide-react'
import { Patent } from '@/lib/api'

interface PatentCardProps {
  patent: Patent
  score?: number
  searchType?: string
  onClick?: () => void
}

export function PatentCard({ patent, score, searchType, onClick }: PatentCardProps) {
  return (
    <div 
      className="card hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="card-content">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h3 className="font-semibold text-lg mb-2 line-clamp-2">
              {patent.title}
            </h3>
            <p className="text-sm text-muted-foreground mb-3 line-clamp-3">
              {patent.abstract}
            </p>
          </div>
          {score !== undefined && (
            <div className="ml-4 text-right">
              <div className="text-sm font-medium text-primary">
                {Math.round(score * 100)}%
              </div>
              <div className="text-xs text-muted-foreground">
                {searchType}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-2 text-sm">
          <div className="flex items-center text-muted-foreground">
            <FileText className="h-4 w-4 mr-2" />
            <span>{patent.pub_number}</span>
          </div>
          
          <div className="flex items-center text-muted-foreground">
            <Calendar className="h-4 w-4 mr-2" />
            <span>Priority: {format(new Date(patent.prio_date), 'MMM dd, yyyy')}</span>
          </div>

          {patent.assignees.length > 0 && (
            <div className="flex items-center text-muted-foreground">
              <Users className="h-4 w-4 mr-2" />
              <span className="line-clamp-1">
                {patent.assignees.slice(0, 2).join(', ')}
                {patent.assignees.length > 2 && ` +${patent.assignees.length - 2} more`}
              </span>
            </div>
          )}

          {patent.cpc_codes.length > 0 && (
            <div className="flex items-center text-muted-foreground">
              <Tag className="h-4 w-4 mr-2" />
              <span className="line-clamp-1">
                {patent.cpc_codes.slice(0, 3).join(', ')}
                {patent.cpc_codes.length > 3 && ` +${patent.cpc_codes.length - 3} more`}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
