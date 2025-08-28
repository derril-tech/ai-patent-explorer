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
import { Organization } from './Organization';
import { Membership } from './Membership';
import { Patent } from './Patent';
import { Alignment } from './Alignment';
import { NoveltyScore } from './NoveltyScore';
import { SearchSession } from './SearchSession';
import { ClaimChart } from './ClaimChart';
import { AuditLog } from './AuditLog';

@Entity('workspaces')
export class Workspace {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  org_id: string;

  @Column({ type: 'varchar', length: 255 })
  name: string;

  @Column({ type: 'varchar', length: 100 })
  slug: string;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @UpdateDateColumn({ type: 'timestamp with time zone' })
  updated_at: Date;

  @ManyToOne(() => Organization, (org) => org.workspaces)
  @JoinColumn({ name: 'org_id' })
  organization: Organization;

  @OneToMany(() => Membership, (membership) => membership.workspace)
  memberships: Membership[];

  @OneToMany(() => Patent, (patent) => patent.workspace)
  patents: Patent[];

  @OneToMany(() => Alignment, (alignment) => alignment.workspace)
  alignments: Alignment[];

  @OneToMany(() => NoveltyScore, (score) => score.workspace)
  noveltyScores: NoveltyScore[];

  @OneToMany(() => SearchSession, (session) => session.workspace)
  searchSessions: SearchSession[];

  @OneToMany(() => ClaimChart, (chart) => chart.workspace)
  claimCharts: ClaimChart[];

  @OneToMany(() => AuditLog, (log) => log.workspace)
  auditLogs: AuditLog[];
}
