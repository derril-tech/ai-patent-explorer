import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  ManyToOne,
  JoinColumn,
  Index,
} from 'typeorm';
import { User } from './User';
import { Workspace } from './Workspace';

@Entity('memberships')
export class Membership {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  @Index()
  user_id: string;

  @Column({ type: 'uuid' })
  @Index()
  workspace_id: string;

  @Column({ type: 'varchar', length: 50, default: 'member' })
  role: string; // owner, admin, member, viewer

  @CreateDateColumn({ type: 'timestamp with time zone' })
  created_at: Date;

  @ManyToOne(() => User, (user) => user.memberships)
  @JoinColumn({ name: 'user_id' })
  user: User;

  @ManyToOne(() => Workspace, (workspace) => workspace.memberships)
  @JoinColumn({ name: 'workspace_id' })
  workspace: Workspace;
}
