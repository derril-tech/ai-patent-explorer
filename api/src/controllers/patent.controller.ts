import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  Query,
  UseGuards,
  Request,
  HttpStatus,
  HttpException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Patent } from '../entities/Patent';
import { Claim } from '../entities/Claim';
import { Passage } from '../entities/Passage';
import { SearchSession } from '../entities/SearchSession';
import { AuditLog } from '../entities/AuditLog';
import { JwtAuthGuard } from '../guards/jwt-auth.guard';
import { WorkspaceGuard } from '../guards/workspace.guard';

interface PatentIngestRequest {
  file_url: string;
  file_type: 'xml' | 'pdf';
  workspace_id: string;
  metadata?: Record<string, any>;
}

interface SearchRequest {
  query: string;
  filters?: {
    date_from?: string;
    date_to?: string;
    cpc_codes?: string[];
    assignees?: string[];
  };
  k?: number;
  search_type?: 'hybrid' | 'bm25' | 'dense';
}

interface SearchResponse {
  results: Array<{
    patent_id: string;
    score: number;
    search_type: string;
    patent: Partial<Patent>;
    claim?: Partial<Claim>;
  }>;
  total: number;
  search_id: string;
}

interface CompareRequest {
  patent_id: string;
  claim_num: number;
  refs: string[]; // Reference patent IDs
  workspace_id: string;
}

interface NoveltyRequest {
  patent_id: string;
  claim_num: number;
  workspace_id: string;
}

interface ComparisonResponse {
  comparison_id: string;
  patent_id: string;
  claim_num: number;
  alignments: Array<{
    clause_index: number;
    clause_text: string;
    reference_patent_id: string;
    reference_clause_text: string;
    similarity_score: number;
    alignment_type: string;
  }>;
  status: string;
}

interface NoveltyResponse {
  novelty_id: string;
  patent_id: string;
  claim_num: number;
  novelty_score: number;
  obviousness_score: number;
  confidence_band: string;
  clause_details: Array<{
    clause_index: number;
    clause_text: string;
    novelty_score: number;
    confidence: string;
  }>;
  status: string;
}

interface ChartRequest {
  patent_id: string;
  claim_num: number;
  chart_type: 'docx' | 'pdf';
  include_alignments?: boolean;
  include_novelty?: boolean;
  workspace_id: string;
}

interface ChartResponse {
  chart_id: string;
  patent_id: string;
  claim_num: number;
  chart_type: string;
  file_url: string;
  status: string;
}

interface ExportRequest {
  patent_ids: string[];
  export_type: 'zip' | 'pdf';
  include_charts?: boolean;
  include_alignments?: boolean;
  include_novelty?: boolean;
  workspace_id: string;
}

interface ExportResponse {
  export_id: string;
  patent_ids: string[];
  export_type: string;
  file_url: string;
  status: string;
}

@Controller('patents')
@UseGuards(JwtAuthGuard, WorkspaceGuard)
export class PatentController {
  constructor(
    @InjectRepository(Patent)
    private patentRepository: Repository<Patent>,
    @InjectRepository(Claim)
    private claimRepository: Repository<Claim>,
    @InjectRepository(Passage)
    private passageRepository: Repository<Passage>,
    @InjectRepository(SearchSession)
    private searchSessionRepository: Repository<SearchSession>,
    @InjectRepository(AuditLog)
    private auditLogRepository: Repository<AuditLog>,
  ) {}

  @Post('ingest')
  async ingestPatent(
    @Body() ingestRequest: PatentIngestRequest,
    @Request() req: any,
  ): Promise<{ patent_id: string; status: string }> {
    try {
      const { file_url, file_type, workspace_id, metadata } = ingestRequest;
      const user_id = req.user.id;

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      // Create patent record
      const patent = this.patentRepository.create({
        workspace_id,
        title: metadata?.title || 'Untitled Patent',
        abstract: metadata?.abstract || '',
        prio_date: metadata?.prio_date || new Date(),
        pub_date: metadata?.pub_date || new Date(),
        family_id: metadata?.family_id,
        cpc_codes: metadata?.cpc_codes || [],
        assignees: metadata?.assignees || [],
        inventors: metadata?.inventors || [],
        metadata: metadata || {},
      });

      const savedPatent = await this.patentRepository.save(patent);

      // Publish ingest event to NATS
      await this.publishIngestEvent(savedPatent.id, file_url, file_type);

      // Create audit log
      await this.auditLogRepository.save({
        workspace_id,
        user_id,
        action: 'patent_ingest',
        resource_type: 'patent',
        resource_id: savedPatent.id,
        details: { file_url, file_type, metadata },
      });

      return {
        patent_id: savedPatent.id,
        status: 'processing',
      };
    } catch (error) {
      throw new HttpException(
        `Failed to ingest patent: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get()
  async getPatents(
    @Query('workspace_id') workspace_id: string,
    @Query('page') page: number = 1,
    @Query('limit') limit: number = 20,
    @Query('search') search?: string,
    @Request() req: any,
  ): Promise<{
    patents: Partial<Patent>[];
    total: number;
    page: number;
    limit: number;
  }> {
    try {
      const user_id = req.user.id;
      const offset = (page - 1) * limit;

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      let query = this.patentRepository
        .createQueryBuilder('patent')
        .where('patent.workspace_id = :workspace_id', { workspace_id });

      // Add search filter if provided
      if (search) {
        query = query.andWhere(
          '(patent.title ILIKE :search OR patent.abstract ILIKE :search)',
          { search: `%${search}%` },
        );
      }

      const [patents, total] = await query
        .orderBy('patent.created_at', 'DESC')
        .skip(offset)
        .take(limit)
        .getManyAndCount();

      return {
        patents,
        total,
        page,
        limit,
      };
    } catch (error) {
      throw new HttpException(
        `Failed to get patents: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get(':id')
  async getPatent(
    @Param('id') patent_id: string,
    @Request() req: any,
  ): Promise<Partial<Patent>> {
    try {
      const user_id = req.user.id;

      const patent = await this.patentRepository.findOne({
        where: { id: patent_id },
      });

      if (!patent) {
        throw new HttpException('Patent not found', HttpStatus.NOT_FOUND);
      }

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, patent.workspace_id)) {
        throw new HttpException(
          'Access denied to patent',
          HttpStatus.FORBIDDEN,
        );
      }

      return patent;
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        `Failed to get patent: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get(':id/claims')
  async getPatentClaims(
    @Param('id') patent_id: string,
    @Request() req: any,
  ): Promise<Partial<Claim>[]> {
    try {
      const user_id = req.user.id;

      const patent = await this.patentRepository.findOne({
        where: { id: patent_id },
      });

      if (!patent) {
        throw new HttpException('Patent not found', HttpStatus.NOT_FOUND);
      }

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, patent.workspace_id)) {
        throw new HttpException(
          'Access denied to patent',
          HttpStatus.FORBIDDEN,
        );
      }

      const claims = await this.claimRepository.find({
        where: { patent_id },
        order: { claim_number: 'ASC' },
      });

      return claims;
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        `Failed to get patent claims: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get(':id/passages')
  async getPatentPassages(
    @Param('id') patent_id: string,
    @Request() req: any,
  ): Promise<Partial<Passage>[]> {
    try {
      const user_id = req.user.id;

      const patent = await this.patentRepository.findOne({
        where: { id: patent_id },
      });

      if (!patent) {
        throw new HttpException('Patent not found', HttpStatus.NOT_FOUND);
      }

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, patent.workspace_id)) {
        throw new HttpException(
          'Access denied to patent',
          HttpStatus.FORBIDDEN,
        );
      }

      const passages = await this.passageRepository.find({
        where: { patent_id },
        order: { passage_type: 'ASC', passage_number: 'ASC' },
      });

      return passages;
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        `Failed to get patent passages: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('search')
  async searchPatents(
    @Body() searchRequest: SearchRequest,
    @Request() req: any,
  ): Promise<SearchResponse> {
    try {
      const { query, filters, k = 10, search_type = 'hybrid' } = searchRequest;
      const user_id = req.user.id;
      const workspace_id = req.headers['x-workspace-id'];

      if (!workspace_id) {
        throw new HttpException(
          'Workspace ID required',
          HttpStatus.BAD_REQUEST,
        );
      }

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      // Generate search ID
      const search_id = this.generateSearchId();

      // Publish search request to NATS
      await this.publishSearchEvent(search_id, query, workspace_id, filters, k, search_type);

      // For now, return a mock response
      // In a real implementation, this would wait for the worker response
      const mockResults = await this.getMockSearchResults(query, workspace_id, k);

      // Create search session
      await this.searchSessionRepository.save({
        workspace_id,
        user_id,
        query,
        filters: filters || {},
        results: mockResults,
      });

      // Create audit log
      await this.auditLogRepository.save({
        workspace_id,
        user_id,
        action: 'patent_search',
        resource_type: 'search',
        details: { query, filters, k, search_type, search_id },
      });

      return {
        results: mockResults,
        total: mockResults.length,
        search_id,
      };
    } catch (error) {
      throw new HttpException(
        `Failed to search patents: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('compare')
  async comparePatent(
    @Body() compareRequest: CompareRequest,
    @Request() req: any,
  ): Promise<ComparisonResponse> {
    try {
      const { patent_id, claim_num, refs, workspace_id } = compareRequest;
      const user_id = req.user.id;

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      // Validate patent exists and belongs to workspace
      const patent = await this.patentRepository.findOne({
        where: { id: patent_id, workspace_id },
      });

      if (!patent) {
        throw new HttpException(
          'Patent not found or access denied',
          HttpStatus.NOT_FOUND,
        );
      }

      // Generate comparison ID
      const comparison_id = this.generateComparisonId();

      // Publish alignment request to NATS
      await this.publishAlignmentEvent(comparison_id, patent_id, claim_num, refs);

      // For now, return a mock response
      // In a real implementation, this would wait for the worker response
      const mockAlignments = await this.getMockAlignments(patent_id, claim_num, refs);

      // Create audit log
      await this.auditLogRepository.save({
        workspace_id,
        user_id,
        action: 'patent_compare',
        resource_type: 'comparison',
        details: { patent_id, claim_num, refs, comparison_id },
      });

      return {
        comparison_id,
        patent_id,
        claim_num,
        alignments: mockAlignments,
        status: 'completed',
      };
    } catch (error) {
      throw new HttpException(
        `Failed to compare patent: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('novelty')
  async calculateNovelty(
    @Body() noveltyRequest: NoveltyRequest,
    @Request() req: any,
  ): Promise<NoveltyResponse> {
    try {
      const { patent_id, claim_num, workspace_id } = noveltyRequest;
      const user_id = req.user.id;

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      // Validate patent exists and belongs to workspace
      const patent = await this.patentRepository.findOne({
        where: { id: patent_id, workspace_id },
      });

      if (!patent) {
        throw new HttpException(
          'Patent not found or access denied',
          HttpStatus.NOT_FOUND,
        );
      }

      // Generate novelty ID
      const novelty_id = this.generateNoveltyId();

      // Publish novelty request to NATS
      await this.publishNoveltyEvent(novelty_id, patent_id, claim_num);

      // For now, return a mock response
      // In a real implementation, this would wait for the worker response
      const mockNovelty = await this.getMockNovelty(patent_id, claim_num);

      // Create audit log
      await this.auditLogRepository.save({
        workspace_id,
        user_id,
        action: 'patent_novelty',
        resource_type: 'novelty',
        details: { patent_id, claim_num, novelty_id },
      });

      return {
        novelty_id,
        patent_id,
        claim_num,
        novelty_score: mockNovelty.novelty_score,
        obviousness_score: mockNovelty.obviousness_score,
        confidence_band: mockNovelty.confidence_band,
        clause_details: mockNovelty.clause_details,
        status: 'completed',
      };
    } catch (error) {
      throw new HttpException(
        `Failed to calculate novelty: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  private hasWorkspaceAccess(user_id: string, workspace_id: string): boolean {
    // TODO: Implement proper workspace access validation
    // This should check if the user is a member of the workspace
    return true;
  }

  private async publishIngestEvent(
    patent_id: string,
    file_url: string,
    file_type: string,
  ): Promise<void> {
    // TODO: Implement NATS publishing
    console.log(`Publishing ingest event for patent ${patent_id}`);
  }

  private async publishSearchEvent(
    search_id: string,
    query: string,
    workspace_id: string,
    filters: any,
    k: number,
    search_type: string,
  ): Promise<void> {
    // TODO: Implement NATS publishing
    console.log(`Publishing search event ${search_id} for query: ${query}`);
  }

  private generateSearchId(): string {
    return `search_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateComparisonId(): string {
    return `compare_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateNoveltyId(): string {
    return `novelty_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async getMockSearchResults(
    query: string,
    workspace_id: string,
    k: number,
  ): Promise<any[]> {
    // Mock implementation - replace with actual search logic
    const patents = await this.patentRepository.find({
      where: { workspace_id },
      take: k,
    });

    return patents.map((patent, index) => ({
      patent_id: patent.id,
      score: 1.0 - index * 0.1,
      search_type: 'hybrid',
      patent: {
        id: patent.id,
        title: patent.title,
        abstract: patent.abstract,
        prio_date: patent.prio_date,
      },
    }));
  }

  private async getMockAlignments(
    patent_id: string,
    claim_num: number,
    refs: string[],
  ): Promise<any[]> {
    // Mock implementation - replace with actual alignment logic
    return refs.map((ref_id, index) => ({
      clause_index: index,
      clause_text: `Mock clause ${index + 1} for patent ${patent_id}`,
      reference_patent_id: ref_id,
      reference_clause_text: `Mock reference clause ${index + 1}`,
      similarity_score: 0.8 - index * 0.1,
      alignment_type: index === 0 ? 'high_similarity' : 'medium_similarity',
    }));
  }

  private async getMockNovelty(
    patent_id: string,
    claim_num: number,
  ): Promise<any> {
    // Mock implementation - replace with actual novelty calculation
    return {
      novelty_score: 0.75,
      obviousness_score: 0.25,
      confidence_band: 'high',
      clause_details: [
        {
          clause_index: 0,
          clause_text: 'Mock clause 1',
          novelty_score: 0.8,
          confidence: 'high',
        },
        {
          clause_index: 1,
          clause_text: 'Mock clause 2',
          novelty_score: 0.7,
          confidence: 'medium',
        },
      ],
    };
  }

  private async publishAlignmentEvent(
    comparison_id: string,
    patent_id: string,
    claim_num: number,
    refs: string[],
  ): Promise<void> {
    // TODO: Implement NATS publishing
    console.log(`Publishing alignment event ${comparison_id} for patent ${patent_id}, claim ${claim_num}`);
  }

  @Post('charts/claim')
  async generateClaimChart(
    @Body() chartRequest: ChartRequest,
    @Request() req: any,
  ): Promise<ChartResponse> {
    try {
      const { patent_id, claim_num, chart_type, include_alignments, include_novelty, workspace_id } = chartRequest;
      const user_id = req.user.id;

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      // Validate patent exists and belongs to workspace
      const patent = await this.patentRepository.findOne({
        where: { id: patent_id, workspace_id },
      });

      if (!patent) {
        throw new HttpException(
          'Patent not found or access denied',
          HttpStatus.NOT_FOUND,
        );
      }

      // Generate chart ID
      const chart_id = this.generateChartId();

      // Publish chart generation request to NATS
      await this.publishChartEvent(chart_id, patent_id, claim_num, chart_type, include_alignments, include_novelty);

      // For now, return a mock response
      // In a real implementation, this would wait for the worker response
      const mockChart = await this.getMockChart(patent_id, claim_num, chart_type);

      // Create audit log
      await this.auditLogRepository.save({
        workspace_id,
        user_id,
        action: 'chart_generate',
        resource_type: 'chart',
        details: { patent_id, claim_num, chart_type, chart_id },
      });

      return {
        chart_id,
        patent_id,
        claim_num,
        chart_type,
        file_url: mockChart.file_url,
        status: 'completed',
      };
    } catch (error) {
      throw new HttpException(
        `Failed to generate chart: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('exports/bundle')
  async createExportBundle(
    @Body() exportRequest: ExportRequest,
    @Request() req: any,
  ): Promise<ExportResponse> {
    try {
      const { patent_ids, export_type, include_charts, include_alignments, include_novelty, workspace_id } = exportRequest;
      const user_id = req.user.id;

      // Validate workspace access
      if (!this.hasWorkspaceAccess(user_id, workspace_id)) {
        throw new HttpException(
          'Access denied to workspace',
          HttpStatus.FORBIDDEN,
        );
      }

      // Validate all patents exist and belong to workspace
      for (const patent_id of patent_ids) {
        const patent = await this.patentRepository.findOne({
          where: { id: patent_id, workspace_id },
        });

        if (!patent) {
          throw new HttpException(
            `Patent ${patent_id} not found or access denied`,
            HttpStatus.NOT_FOUND,
          );
        }
      }

      // Generate export ID
      const export_id = this.generateExportId();

      // Publish export request to NATS
      await this.publishExportEvent(export_id, patent_ids, export_type, include_charts, include_alignments, include_novelty);

      // For now, return a mock response
      // In a real implementation, this would wait for the worker response
      const mockExport = await this.getMockExport(patent_ids, export_type);

      // Create audit log
      await this.auditLogRepository.save({
        workspace_id,
        user_id,
        action: 'export_bundle',
        resource_type: 'export',
        details: { patent_ids, export_type, export_id },
      });

      return {
        export_id,
        patent_ids,
        export_type,
        file_url: mockExport.file_url,
        status: 'completed',
      };
    } catch (error) {
      throw new HttpException(
        `Failed to create export bundle: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  private async publishNoveltyEvent(
    novelty_id: string,
    patent_id: string,
    claim_num: number,
  ): Promise<void> {
    // TODO: Implement NATS publishing
    console.log(`Publishing novelty event ${novelty_id} for patent ${patent_id}, claim ${claim_num}`);
  }

  private generateChartId(): string {
    return `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateExportId(): string {
    return `export_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async getMockChart(
    patent_id: string,
    claim_num: number,
    chart_type: string,
  ): Promise<any> {
    // Mock implementation - replace with actual chart generation
    return {
      file_url: `https://storage.example.com/charts/mock_chart_${patent_id}_${claim_num}.${chart_type}`,
    };
  }

  private async getMockExport(
    patent_ids: string[],
    export_type: string,
  ): Promise<any> {
    // Mock implementation - replace with actual export generation
    return {
      file_url: `https://storage.example.com/exports/mock_export_${patent_ids.join('_')}.${export_type}`,
    };
  }

  private async publishChartEvent(
    chart_id: string,
    patent_id: string,
    claim_num: number,
    chart_type: string,
    include_alignments: boolean,
    include_novelty: boolean,
  ): Promise<void> {
    // TODO: Implement NATS publishing
    console.log(`Publishing chart event ${chart_id} for patent ${patent_id}, claim ${claim_num}, type ${chart_type}`);
  }

  private async publishExportEvent(
    export_id: string,
    patent_ids: string[],
    export_type: string,
    include_charts: boolean,
    include_alignments: boolean,
    include_novelty: boolean,
  ): Promise<void> {
    // TODO: Implement NATS publishing
    console.log(`Publishing export event ${export_id} for ${patent_ids.length} patents, type ${export_type}`);
  }
}
