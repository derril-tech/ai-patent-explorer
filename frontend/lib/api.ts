import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for authentication
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  const workspaceId = localStorage.getItem('workspace_id')
  if (workspaceId) {
    config.headers['x-workspace-id'] = workspaceId
  }
  
  return config
})

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Patent API
export const patentApi = {
  // Search patents
  search: async (params: {
    query: string
    filters?: any
    k?: number
    search_type?: 'hybrid' | 'bm25' | 'dense'
  }) => {
    const response = await api.post('/patents/search', params)
    return response.data
  },

  // Get patent by ID
  getById: async (id: string) => {
    const response = await api.get(`/patents/${id}`)
    return response.data
  },

  // Get patent claims
  getClaims: async (id: string) => {
    const response = await api.get(`/patents/${id}/claims`)
    return response.data
  },

  // Get patent passages
  getPassages: async (id: string) => {
    const response = await api.get(`/patents/${id}/passages`)
    return response.data
  },

  // Compare patents
  compare: async (params: {
    patent_id: string
    claim_num: number
    refs: string[]
    workspace_id: string
  }) => {
    const response = await api.post('/patents/compare', params)
    return response.data
  },

  // Calculate novelty
  novelty: async (params: {
    patent_id: string
    claim_num: number
    workspace_id: string
  }) => {
    const response = await api.post('/patents/novelty', params)
    return response.data
  },

  // Generate chart
  generateChart: async (params: {
    patent_id: string
    claim_num: number
    chart_type: 'docx' | 'pdf'
    include_alignments?: boolean
    include_novelty?: boolean
    workspace_id: string
  }) => {
    const response = await api.post('/patents/charts/claim', params)
    return response.data
  },

  // Create export bundle
  createExport: async (params: {
    patent_ids: string[]
    export_type: 'zip' | 'pdf'
    include_charts?: boolean
    include_alignments?: boolean
    include_novelty?: boolean
    workspace_id: string
  }) => {
    const response = await api.post('/patents/exports/bundle', params)
    return response.data
  },
}

// Convenience functions
export const searchPatents = patentApi.search
export const getPatent = patentApi.getById
export const getPatentClaims = patentApi.getClaims
export const comparePatents = patentApi.compare
export const calculateNovelty = patentApi.novelty
export const generateChart = patentApi.generateChart
export const createExport = patentApi.createExport

// Types
export interface Patent {
  id: string
  title: string
  abstract: string
  pub_number: string
  prio_date: string
  pub_date: string
  assignees: string[]
  inventors: string[]
  cpc_codes: string[]
  family_id?: string
  metadata?: any
}

export interface Claim {
  id: string
  patent_id: string
  claim_number: number
  text: string
  is_independent: boolean
  embedding?: number[]
}

export interface SearchResult {
  patent_id: string
  score: number
  search_type: string
  patent: Patent
  claim?: Claim
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  search_id: string
}

export interface Alignment {
  clause_index: number
  clause_text: string
  reference_patent_id: string
  reference_clause_text: string
  similarity_score: number
  alignment_type: string
}

export interface ComparisonResponse {
  comparison_id: string
  patent_id: string
  claim_num: number
  alignments: Alignment[]
  status: string
}

export interface NoveltyResponse {
  novelty_id: string
  patent_id: string
  claim_num: number
  novelty_score: number
  obviousness_score: number
  confidence_band: string
  clause_details: Array<{
    clause_index: number
    clause_text: string
    novelty_score: number
    confidence: string
  }>
  status: string
}

export interface ChartResponse {
  chart_id: string
  patent_id: string
  claim_num: number
  chart_type: string
  file_url: string
  status: string
}

export interface ExportResponse {
  export_id: string
  patent_ids: string[]
  export_type: string
  file_url: string
  status: string
}
