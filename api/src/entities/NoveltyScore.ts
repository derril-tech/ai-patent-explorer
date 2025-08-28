import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  Index,
  JoinColumn,
} from 'typeorm';
import { Workspace } from './Workspace';
import { Claim } from './Claim';

@Entity('novelty_scores')
export class NoveltyScore {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  workspace_id: string;

  @Column({ type: 'uuid' })
  @Index()
  claim_id: string;

  @Column({ type: 'float' })
  novelty_score: number;

  @Column({ type: 'float' })
  obviousness_score: number;

  @Column({ type: 'float' })
  confidence: number;

  @Column({ type: 'jsonb', nullable: true })
  factors: any;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @UpdateDateColumn({ type: 'timestamp with time zone' })
  updated_at: Date;

  @ManyToOne(() => Workspace, (workspace) => workspace.noveltyScores)
  @JoinColumn({ name: 'workspace_id' })
  workspace: Workspace;

  @ManyToOne(() => Claim, (claim) => claim.noveltyScores)
  @JoinColumn({ name: 'claim_id' })
  claim: Claim;
}
