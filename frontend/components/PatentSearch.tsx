'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download } from 'lucide-react'
import { searchPatents } from '@/lib/api'
import { PatentCard } from './PatentCard'

interface PatentSearchProps {
  onPatentSelect: (patentId: string) => void
}

export function PatentSearch({ onPatentSelect }: PatentSearchProps) {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState({
    date_from: '',
    date_to: '',
    cpc_codes: [] as string[],
    assignees: [] as string[],
  })
  const [searchParams, setSearchParams] = useState({
    query: '',
    filters: {},
    k: 10,
    search_type: 'hybrid' as const,
  })

  const { data: searchResults, isLoading, error } = useQuery({
    queryKey: ['patent-search', searchParams],
    queryFn: () => searchPatents(searchParams),
    enabled: !!searchParams.query,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchParams({
      query,
      filters,
      k: 10,
      search_type: 'hybrid',
    })
  }

  const handleExport = () => {
    // TODO: Implement export functionality
    console.log('Export search results')
  }

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Patent Search</h2>
          <p className="card-description">
            Search patents using natural language queries and advanced filters
          </p>
        </div>
        <div className="card-content">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex space-x-2">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Enter search query (e.g., 'machine learning algorithms for image recognition')"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="input"
                />
              </div>
              <button type="submit" className="btn btn-primary">
                <Search className="h-4 w-4 mr-2" />
                Search
              </button>
            </div>

            {/* Advanced Filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Date Range</label>
                <div className="flex space-x-2">
                  <input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
                    className="input"
                    placeholder="From"
                  />
                  <input
                    type="date"
                    value={filters.date_to}
                    onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
                    className="input"
                    placeholder="To"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Search Type</label>
                <select
                  value={searchParams.search_type}
                  onChange={(e) => setSearchParams({ ...searchParams, search_type: e.target.value as any })}
                  className="input"
                >
                  <option value="hybrid">Hybrid (Recommended)</option>
                  <option value="bm25">Keyword (BM25)</option>
                  <option value="dense">Semantic (Dense)</option>
                </select>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Search Results */}
      {isLoading && (
        <div className="card">
          <div className="card-content">
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-2">Searching patents...</span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="card">
          <div className="card-content">
            <div className="text-center py-8 text-destructive">
              Error loading search results. Please try again.
            </div>
          </div>
        </div>
      )}

      {searchResults && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">
              Search Results ({searchResults.total} patents found)
            </h3>
            <button onClick={handleExport} className="btn btn-outline">
              <Download className="h-4 w-4 mr-2" />
              Export Results
            </button>
          </div>

          <div className="grid gap-4">
            {searchResults.results.map((result) => (
              <PatentCard
                key={result.patent_id}
                patent={result.patent}
                score={result.score}
                searchType={result.search_type}
                onClick={() => onPatentSelect(result.patent_id)}
              />
            ))}
          </div>

          {searchResults.results.length === 0 && (
            <div className="card">
              <div className="card-content">
                <div className="text-center py-8 text-muted-foreground">
                  No patents found matching your search criteria.
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Search Tips */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold">Search Tips</h3>
        </div>
        <div className="card-content">
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>• Use natural language queries for best results</li>
            <li>• Include technical terms and concepts</li>
            <li>• Try different search types for varied results</li>
            <li>• Use date filters to focus on recent patents</li>
            <li>• Combine multiple search terms for precision</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
