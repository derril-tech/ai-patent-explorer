import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';

// Entities
import { Organization } from './entities/Organization';
import { User } from './entities/User';
import { Workspace } from './entities/Workspace';
import { Membership } from './entities/Membership';
import { Patent } from './entities/Patent';
import { Claim } from './entities/Claim';
import { Clause } from './entities/Clause';
import { Passage } from './entities/Passage';
import { Alignment } from './entities/Alignment';
import { NoveltyScore } from './entities/NoveltyScore';
import { SearchSession } from './entities/SearchSession';
import { ClaimChart } from './entities/ClaimChart';
import { Citation } from './entities/Citation';
import { AuditLog } from './entities/AuditLog';

// Controllers
import { PatentController } from './controllers/patent.controller';

// Guards
import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { WorkspaceGuard } from './guards/workspace.guard';

// Configuration
import { databaseConfig } from './config/database.config';

@Module({
  imports: [
    // Configuration
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),

    // Database
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        ...databaseConfig,
        host: configService.get('DB_HOST', 'localhost'),
        port: configService.get('DB_PORT', 5432),
        username: configService.get('DB_USERNAME', 'postgres'),
        password: configService.get('DB_PASSWORD', 'password'),
        database: configService.get('DB_NAME', 'patent_explorer'),
      }),
      inject: [ConfigService],
    }),

    // JWT
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        secret: configService.get('JWT_SECRET', 'your-secret-key'),
        signOptions: { 
          expiresIn: configService.get('JWT_EXPIRES_IN', '24h') 
        },
      }),
      inject: [ConfigService],
    }),

    // TypeORM entities
    TypeOrmModule.forFeature([
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
    ]),
  ],
  controllers: [
    PatentController,
  ],
  providers: [
    JwtAuthGuard,
    WorkspaceGuard,
  ],
})
export class AppModule {}
