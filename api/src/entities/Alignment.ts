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
import { Clause } from './Clause';
import { Passage } from './Passage';

@Entity('alignments')
export class Alignment {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  workspace_id: string;

  @Column({ type: 'uuid' })
  @Index()
  clause_id: string;

  @Column({ type: 'uuid' })
  @Index()
  passage_id: string;

  @Column({ type: 'varchar', length: 50 })
  alignment_type: string; // overlap, gap, paraphrase, ambiguous

  @Column({ type: 'float' })
  similarity_score: number;

  @Column({ type: 'text', nullable: true })
  explanation: string;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Workspace, (workspace) => workspace.alignments)
  @JoinColumn({ name: 'workspace_id' })
  workspace: Workspace;

  @ManyToOne(() => Clause, (clause) => clause.alignments)
  @JoinColumn({ name: 'clause_id' })
  clause: Clause;

  @ManyToOne(() => Passage, (passage) => passage.alignments)
  @JoinColumn({ name: 'passage_id' })
  passage: Passage;
}
