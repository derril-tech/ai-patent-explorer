import { TypeOrmModuleOptions } from '@nestjs/typeorm';
import { Organization } from '../entities/Organization';
import { User } from '../entities/User';
import { Workspace } from '../entities/Workspace';
import { Membership } from '../entities/Membership';
import { Patent } from '../entities/Patent';
import { Claim } from '../entities/Claim';
import { Clause } from '../entities/Clause';
import { Passage } from '../entities/Passage';
import { Alignment } from '../entities/Alignment';
import { NoveltyScore } from '../entities/NoveltyScore';
import { SearchSession } from '../entities/SearchSession';
import { ClaimChart } from '../entities/ClaimChart';
import { Citation } from '../entities/Citation';
import { AuditLog } from '../entities/AuditLog';

export const databaseConfig: TypeOrmModuleOptions = {
  type: 'postgres',
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT) || 5432,
  username: process.env.DB_USERNAME || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_NAME || 'ai_patent_explorer',
  entities: [
    Organization,
    User,
    Workspace,
    Membership,
    Patent,
    Claim,
    Clause,
    Passage,
    Alignment,
    NoveltyScore,
    SearchSession,
    ClaimChart,
    Citation,
    AuditLog,
  ],
  migrations: ['src/migrations/*.ts'],
  migrationsRun: true,
  synchronize: process.env.NODE_ENV === 'development', // Only in development
  logging: process.env.NODE_ENV === 'development',
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
  extra: {
    // pgvector configuration
    max: 20,
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 30000,
  },
};
