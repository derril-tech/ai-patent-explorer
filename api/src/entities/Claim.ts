import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  ManyToOne,
  OneToMany,
  Index,
  JoinColumn,
} from 'typeorm';
import { Patent } from './Patent';
import { Clause } from './Clause';
import { NoveltyScore } from './NoveltyScore';

@Entity('claims')
export class Claim {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  patent_id: string;

  @Column({ type: 'integer' })
  claim_number: number;

  @Column({ type: 'boolean', default: false })
  is_independent: boolean;

  @Column({ type: 'text' })
  text: string;

  @Column({ type: 'vector', length: 1536, nullable: true })
  embedding: number[];

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Patent, (patent) => patent.claims)
  @JoinColumn({ name: 'patent_id' })
  patent: Patent;

  @OneToMany(() => Clause, (clause) => clause.claim)
  clauses: Clause[];

  @OneToMany(() => NoveltyScore, (score) => score.claim)
  noveltyScores: NoveltyScore[];
}
