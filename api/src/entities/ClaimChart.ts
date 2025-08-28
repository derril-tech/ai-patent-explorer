import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  ManyToOne,
  Index,
  JoinColumn,
} from 'typeorm';
import { Workspace } from './Workspace';
import { User } from './User';
import { Patent } from './Patent';

@Entity('claim_charts')
export class ClaimChart {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  workspace_id: string;

  @Column({ type: 'uuid' })
  @Index()
  user_id: string;

  @Column({ type: 'uuid' })
  @Index()
  patent_id: string;

  @Column({ type: 'varchar', length: 50 })
  chart_type: string; // claim_chart, novelty_report, etc.

  @Column({ type: 'varchar', length: 500, nullable: true })
  s3_docx_path: string;

  @Column({ type: 'varchar', length: 500, nullable: true })
  s3_pdf_path: string;

  @Column({ type: 'jsonb', nullable: true })
  metadata: any;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Workspace, (workspace) => workspace.claimCharts)
  @JoinColumn({ name: 'workspace_id' })
  workspace: Workspace;

  @ManyToOne(() => User, (user) => user.claimCharts)
  @JoinColumn({ name: 'user_id' })
  user: User;

  @ManyToOne(() => Patent, (patent) => patent.claimCharts)
  @JoinColumn({ name: 'patent_id' })
  patent: Patent;
}
