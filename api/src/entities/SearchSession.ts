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

@Entity('search_sessions')
export class SearchSession {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  workspace_id: string;

  @Column({ type: 'uuid' })
  @Index()
  user_id: string;

  @Column({ type: 'text' })
  query: string;

  @Column({ type: 'jsonb', nullable: true })
  filters: any;

  @Column({ type: 'jsonb', nullable: true })
  results: any;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => Workspace, (workspace) => workspace.searchSessions)
  @JoinColumn({ name: 'workspace_id' })
  workspace: Workspace;

  @ManyToOne(() => User, (user) => user.searchSessions)
  @JoinColumn({ name: 'user_id' })
  user: User;
}
