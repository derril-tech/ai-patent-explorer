import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  OneToMany,
  Index,
  JoinColumn,
} from 'typeorm';
import { Workspace } from './Workspace';
import { Claim } from './Claim';
import { Passage } from './Passage';
import { ClaimChart } from './ClaimChart';
import { Citation } from './Citation';

@Entity('patents')
export class Patent {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  workspace_id: string;

  @Column({ type: 'varchar', length: 50 })
  pub_number: string;

  @Column({ type: 'varchar', length: 50, nullable: true })
  app_number: string;

  @Column({ type: 'date', nullable: true })
  prio_date: Date;

  @Column({ type: 'varchar', length: 100, nullable: true })
  @Index()
  family_id: string;

  @Column({ type: 'text' })
  title: string;

  @Column({ type: 'text', nullable: true })
  abstract: string;

  @Column({ type: 'jsonb', nullable: true })
  assignees: any;

  @Column({ type: 'jsonb', nullable: true })
  inventors: any;

  @Column({ type: 'jsonb', nullable: true })
  cpc_codes: any;

  @Column({ type: 'jsonb', nullable: true })
  ipc_codes: any;

  @Column({ type: 'varchar', length: 10, default: 'en' })
  lang: string;

  @Column({ type: 'varchar', length: 500, nullable: true })
  s3_xml_path: string;

  @Column({ type: 'varchar', length: 500, nullable: true })
  s3_pdf_path: string;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @UpdateDateColumn({ type: 'timestamp with time zone' })
  updated_at: Date;

  @ManyToOne(() => Workspace, (workspace) => workspace.patents)
  @JoinColumn({ name: 'workspace_id' })
  workspace: Workspace;

  @OneToMany(() => Claim, (claim) => claim.patent)
  claims: Claim[];

  @OneToMany(() => Passage, (passage) => passage.patent)
  passages: Passage[];

  @OneToMany(() => ClaimChart, (chart) => chart.patent)
  claimCharts: ClaimChart[];

  @OneToMany(() => Citation, (citation) => citation.fromPatent)
  forwardCitations: Citation[];

  @OneToMany(() => Citation, (citation) => citation.toPatent)
  backwardCitations: Citation[];
}
