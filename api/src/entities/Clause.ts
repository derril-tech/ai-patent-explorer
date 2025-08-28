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
import { Claim } from './Claim';
import { Alignment } from './Alignment';

@Entity('clauses')
export class Clause {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  claim_id: string;

  @Column({ type: 'integer' })
  clause_index: number;

  @Column({ type: 'varchar', length: 50, nullable: true })
  clause_type: string; // preamble, element, transition, etc.

  @Column({ type: 'text' })
  text: string;

  @Column({ type: 'vector', length: 1536, nullable: true })
  embedding: number[];

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Claim, (claim) => claim.clauses)
  @JoinColumn({ name: 'claim_id' })
  claim: Claim;

  @OneToMany(() => Alignment, (alignment) => alignment.clause)
  alignments: Alignment[];
}
