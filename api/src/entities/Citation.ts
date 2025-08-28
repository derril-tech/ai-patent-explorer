import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  ManyToOne,
  Index,
  JoinColumn,
} from 'typeorm';
import { Patent } from './Patent';

@Entity('citations')
export class Citation {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  from_patent_id: string;

  @Column({ type: 'uuid' })
  @Index()
  to_patent_id: string;

  @Column({ type: 'varchar', length: 50, nullable: true })
  citation_type: string; // forward, backward, family

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Patent, (patent) => patent.forwardCitations)
  @JoinColumn({ name: 'from_patent_id' })
  fromPatent: Patent;

  @ManyToOne(() => Patent, (patent) => patent.backwardCitations)
  @JoinColumn({ name: 'to_patent_id' })
  toPatent: Patent;
}
