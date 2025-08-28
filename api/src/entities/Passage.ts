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
import { Alignment } from './Alignment';

@Entity('passages')
export class Passage {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  patent_id: string;

  @Column({ type: 'integer' })
  passage_index: number;

  @Column({ type: 'text' })
  text: string;

  @Column({ type: 'vector', length: 1536, nullable: true })
  embedding: number[];

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Patent, (patent) => patent.passages)
  @JoinColumn({ name: 'patent_id' })
  patent: Patent;

  @OneToMany(() => Alignment, (alignment) => alignment.passage)
  alignments: Alignment[];
}
