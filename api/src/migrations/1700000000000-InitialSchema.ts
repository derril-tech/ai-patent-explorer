import { MigrationInterface, QueryRunner } from 'typeorm';

export class InitialSchema1700000000000 implements MigrationInterface {
  name = 'InitialSchema1700000000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Enable pgvector extension
    await queryRunner.query(`CREATE EXTENSION IF NOT EXISTS vector`);

    // Create organizations table
    await queryRunner.query(`
      CREATE TABLE "orgs" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "name" character varying(255) NOT NULL,
        "slug" character varying(100) NOT NULL,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_orgs_slug" UNIQUE ("slug"),
        CONSTRAINT "PK_orgs" PRIMARY KEY ("id")
      )
    `);

    // Create users table
    await queryRunner.query(`
      CREATE TABLE "users" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "email" character varying(255) NOT NULL,
        "name" character varying(255) NOT NULL,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_users_email" UNIQUE ("email"),
        CONSTRAINT "PK_users" PRIMARY KEY ("id")
      )
    `);

    // Create workspaces table
    await queryRunner.query(`
      CREATE TABLE "workspaces" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "org_id" uuid NOT NULL,
        "name" character varying(255) NOT NULL,
        "slug" character varying(100) NOT NULL,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_workspaces_org_slug" UNIQUE ("org_id", "slug"),
        CONSTRAINT "PK_workspaces" PRIMARY KEY ("id")
      )
    `);

    // Create memberships table
    await queryRunner.query(`
      CREATE TABLE "memberships" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "user_id" uuid NOT NULL,
        "workspace_id" uuid NOT NULL,
        "role" character varying(50) NOT NULL DEFAULT 'member',
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_memberships_user_workspace" UNIQUE ("user_id", "workspace_id"),
        CONSTRAINT "PK_memberships" PRIMARY KEY ("id")
      )
    `);

    // Create patents table
    await queryRunner.query(`
      CREATE TABLE "patents" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "workspace_id" uuid NOT NULL,
        "pub_number" character varying(50) NOT NULL,
        "app_number" character varying(50),
        "prio_date" date,
        "family_id" character varying(100),
        "title" text NOT NULL,
        "abstract" text,
        "assignees" jsonb,
        "inventors" jsonb,
        "cpc_codes" jsonb,
        "ipc_codes" jsonb,
        "lang" character varying(10) NOT NULL DEFAULT 'en',
        "s3_xml_path" character varying(500),
        "s3_pdf_path" character varying(500),
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_patents_workspace_pub" UNIQUE ("workspace_id", "pub_number"),
        CONSTRAINT "PK_patents" PRIMARY KEY ("id")
      )
    `);

    // Create claims table
    await queryRunner.query(`
      CREATE TABLE "claims" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "patent_id" uuid NOT NULL,
        "claim_number" integer NOT NULL,
        "is_independent" boolean NOT NULL DEFAULT false,
        "text" text NOT NULL,
        "embedding" vector(1536),
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_claims_patent_number" UNIQUE ("patent_id", "claim_number"),
        CONSTRAINT "PK_claims" PRIMARY KEY ("id")
      )
    `);

    // Create clauses table
    await queryRunner.query(`
      CREATE TABLE "clauses" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "claim_id" uuid NOT NULL,
        "clause_index" integer NOT NULL,
        "clause_type" character varying(50),
        "text" text NOT NULL,
        "embedding" vector(1536),
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_clauses_claim_index" UNIQUE ("claim_id", "clause_index"),
        CONSTRAINT "PK_clauses" PRIMARY KEY ("id")
      )
    `);

    // Create passages table
    await queryRunner.query(`
      CREATE TABLE "passages" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "patent_id" uuid NOT NULL,
        "passage_index" integer NOT NULL,
        "text" text NOT NULL,
        "embedding" vector(1536),
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_passages_patent_index" UNIQUE ("patent_id", "passage_index"),
        CONSTRAINT "PK_passages" PRIMARY KEY ("id")
      )
    `);

    // Create alignments table
    await queryRunner.query(`
      CREATE TABLE "alignments" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "workspace_id" uuid NOT NULL,
        "clause_id" uuid NOT NULL,
        "passage_id" uuid NOT NULL,
        "alignment_type" character varying(50) NOT NULL,
        "similarity_score" double precision NOT NULL,
        "explanation" text,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_alignments_clause_passage" UNIQUE ("clause_id", "passage_id"),
        CONSTRAINT "PK_alignments" PRIMARY KEY ("id")
      )
    `);

    // Create novelty_scores table
    await queryRunner.query(`
      CREATE TABLE "novelty_scores" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "workspace_id" uuid NOT NULL,
        "claim_id" uuid NOT NULL,
        "novelty_score" double precision NOT NULL,
        "obviousness_score" double precision NOT NULL,
        "confidence" double precision NOT NULL,
        "factors" jsonb,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_novelty_scores_claim" UNIQUE ("claim_id"),
        CONSTRAINT "PK_novelty_scores" PRIMARY KEY ("id")
      )
    `);

    // Create search_sessions table
    await queryRunner.query(`
      CREATE TABLE "search_sessions" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "workspace_id" uuid NOT NULL,
        "user_id" uuid NOT NULL,
        "query" text NOT NULL,
        "filters" jsonb,
        "results" jsonb,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_search_sessions" PRIMARY KEY ("id")
      )
    `);

    // Create claim_charts table
    await queryRunner.query(`
      CREATE TABLE "claim_charts" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "workspace_id" uuid NOT NULL,
        "user_id" uuid NOT NULL,
        "patent_id" uuid NOT NULL,
        "chart_type" character varying(50) NOT NULL,
        "s3_docx_path" character varying(500),
        "s3_pdf_path" character varying(500),
        "metadata" jsonb,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_claim_charts" PRIMARY KEY ("id")
      )
    `);

    // Create citations table
    await queryRunner.query(`
      CREATE TABLE "citations" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "from_patent_id" uuid NOT NULL,
        "to_patent_id" uuid NOT NULL,
        "citation_type" character varying(50),
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "UQ_citations_from_to" UNIQUE ("from_patent_id", "to_patent_id"),
        CONSTRAINT "PK_citations" PRIMARY KEY ("id")
      )
    `);

    // Create audit_log table
    await queryRunner.query(`
      CREATE TABLE "audit_log" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "workspace_id" uuid NOT NULL,
        "user_id" uuid NOT NULL,
        "action" character varying(100) NOT NULL,
        "resource_type" character varying(50) NOT NULL,
        "resource_id" uuid,
        "details" jsonb,
        "ip_address" inet,
        "user_agent" text,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_audit_log" PRIMARY KEY ("id")
      )
    `);

    // Create indexes
    await queryRunner.query(`CREATE INDEX "IDX_workspaces_org_id" ON "workspaces" ("org_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_patents_workspace_id" ON "patents" ("workspace_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_patents_family_id" ON "patents" ("family_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_claims_patent_id" ON "claims" ("patent_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_clauses_claim_id" ON "clauses" ("claim_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_passages_patent_id" ON "passages" ("patent_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_alignments_workspace_id" ON "alignments" ("workspace_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_novelty_scores_workspace_id" ON "novelty_scores" ("workspace_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_search_sessions_workspace_id" ON "search_sessions" ("workspace_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_claim_charts_workspace_id" ON "claim_charts" ("workspace_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_citations_from_patent_id" ON "citations" ("from_patent_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_citations_to_patent_id" ON "citations" ("to_patent_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_audit_log_workspace_id" ON "audit_log" ("workspace_id")`);
    await queryRunner.query(`CREATE INDEX "IDX_audit_log_created_at" ON "audit_log" ("created_at")`);

    // Create vector indexes
    await queryRunner.query(`CREATE INDEX "IDX_claims_embedding" ON "claims" USING ivfflat ("embedding" vector_cosine_ops) WITH (lists = 100)`);
    await queryRunner.query(`CREATE INDEX "IDX_clauses_embedding" ON "clauses" USING ivfflat ("embedding" vector_cosine_ops) WITH (lists = 100)`);
    await queryRunner.query(`CREATE INDEX "IDX_passages_embedding" ON "passages" USING ivfflat ("embedding" vector_cosine_ops) WITH (lists = 100)`);

    // Create foreign key constraints
    await queryRunner.query(`ALTER TABLE "workspaces" ADD CONSTRAINT "FK_workspaces_org" FOREIGN KEY ("org_id") REFERENCES "orgs"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "memberships" ADD CONSTRAINT "FK_memberships_user" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "memberships" ADD CONSTRAINT "FK_memberships_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "patents" ADD CONSTRAINT "FK_patents_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "claims" ADD CONSTRAINT "FK_claims_patent" FOREIGN KEY ("patent_id") REFERENCES "patents"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "clauses" ADD CONSTRAINT "FK_clauses_claim" FOREIGN KEY ("claim_id") REFERENCES "claims"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "passages" ADD CONSTRAINT "FK_passages_patent" FOREIGN KEY ("patent_id") REFERENCES "patents"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "alignments" ADD CONSTRAINT "FK_alignments_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "alignments" ADD CONSTRAINT "FK_alignments_clause" FOREIGN KEY ("clause_id") REFERENCES "clauses"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "alignments" ADD CONSTRAINT "FK_alignments_passage" FOREIGN KEY ("passage_id") REFERENCES "passages"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "novelty_scores" ADD CONSTRAINT "FK_novelty_scores_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "novelty_scores" ADD CONSTRAINT "FK_novelty_scores_claim" FOREIGN KEY ("claim_id") REFERENCES "claims"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "search_sessions" ADD CONSTRAINT "FK_search_sessions_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "search_sessions" ADD CONSTRAINT "FK_search_sessions_user" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "claim_charts" ADD CONSTRAINT "FK_claim_charts_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "claim_charts" ADD CONSTRAINT "FK_claim_charts_user" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "claim_charts" ADD CONSTRAINT "FK_claim_charts_patent" FOREIGN KEY ("patent_id") REFERENCES "patents"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "citations" ADD CONSTRAINT "FK_citations_from_patent" FOREIGN KEY ("from_patent_id") REFERENCES "patents"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "citations" ADD CONSTRAINT "FK_citations_to_patent" FOREIGN KEY ("to_patent_id") REFERENCES "patents"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "audit_log" ADD CONSTRAINT "FK_audit_log_workspace" FOREIGN KEY ("workspace_id") REFERENCES "workspaces"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
    await queryRunner.query(`ALTER TABLE "audit_log" ADD CONSTRAINT "FK_audit_log_user" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);

    // Create triggers for updated_at
    await queryRunner.query(`
      CREATE OR REPLACE FUNCTION update_updated_at_column()
      RETURNS TRIGGER AS $$
      BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
      END;
      $$ language 'plpgsql'
    `);

    await queryRunner.query(`CREATE TRIGGER update_patents_updated_at BEFORE UPDATE ON "patents" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()`);
    await queryRunner.query(`CREATE TRIGGER update_novelty_scores_updated_at BEFORE UPDATE ON "novelty_scores" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()`);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Drop triggers
    await queryRunner.query(`DROP TRIGGER IF EXISTS "update_novelty_scores_updated_at" ON "novelty_scores"`);
    await queryRunner.query(`DROP TRIGGER IF EXISTS "update_patents_updated_at" ON "patents"`);
    await queryRunner.query(`DROP FUNCTION IF EXISTS update_updated_at_column()`);

    // Drop foreign key constraints
    await queryRunner.query(`ALTER TABLE "audit_log" DROP CONSTRAINT "FK_audit_log_user"`);
    await queryRunner.query(`ALTER TABLE "audit_log" DROP CONSTRAINT "FK_audit_log_workspace"`);
    await queryRunner.query(`ALTER TABLE "citations" DROP CONSTRAINT "FK_citations_to_patent"`);
    await queryRunner.query(`ALTER TABLE "citations" DROP CONSTRAINT "FK_citations_from_patent"`);
    await queryRunner.query(`ALTER TABLE "claim_charts" DROP CONSTRAINT "FK_claim_charts_patent"`);
    await queryRunner.query(`ALTER TABLE "claim_charts" DROP CONSTRAINT "FK_claim_charts_user"`);
    await queryRunner.query(`ALTER TABLE "claim_charts" DROP CONSTRAINT "FK_claim_charts_workspace"`);
    await queryRunner.query(`ALTER TABLE "search_sessions" DROP CONSTRAINT "FK_search_sessions_user"`);
    await queryRunner.query(`ALTER TABLE "search_sessions" DROP CONSTRAINT "FK_search_sessions_workspace"`);
    await queryRunner.query(`ALTER TABLE "novelty_scores" DROP CONSTRAINT "FK_novelty_scores_claim"`);
    await queryRunner.query(`ALTER TABLE "novelty_scores" DROP CONSTRAINT "FK_novelty_scores_workspace"`);
    await queryRunner.query(`ALTER TABLE "alignments" DROP CONSTRAINT "FK_alignments_passage"`);
    await queryRunner.query(`ALTER TABLE "alignments" DROP CONSTRAINT "FK_alignments_clause"`);
    await queryRunner.query(`ALTER TABLE "alignments" DROP CONSTRAINT "FK_alignments_workspace"`);
    await queryRunner.query(`ALTER TABLE "passages" DROP CONSTRAINT "FK_passages_patent"`);
    await queryRunner.query(`ALTER TABLE "clauses" DROP CONSTRAINT "FK_clauses_claim"`);
    await queryRunner.query(`ALTER TABLE "claims" DROP CONSTRAINT "FK_claims_patent"`);
    await queryRunner.query(`ALTER TABLE "patents" DROP CONSTRAINT "FK_patents_workspace"`);
    await queryRunner.query(`ALTER TABLE "memberships" DROP CONSTRAINT "FK_memberships_workspace"`);
    await queryRunner.query(`ALTER TABLE "memberships" DROP CONSTRAINT "FK_memberships_user"`);
    await queryRunner.query(`ALTER TABLE "workspaces" DROP CONSTRAINT "FK_workspaces_org"`);

    // Drop indexes
    await queryRunner.query(`DROP INDEX "IDX_audit_log_created_at"`);
    await queryRunner.query(`DROP INDEX "IDX_audit_log_workspace_id"`);
    await queryRunner.query(`DROP INDEX "IDX_citations_to_patent_id"`);
    await queryRunner.query(`DROP INDEX "IDX_citations_from_patent_id"`);
    await queryRunner.query(`DROP INDEX "IDX_claim_charts_workspace_id"`);
    await queryRunner.query(`DROP INDEX "IDX_search_sessions_workspace_id"`);
    await queryRunner.query(`DROP INDEX "IDX_novelty_scores_workspace_id"`);
    await queryRunner.query(`DROP INDEX "IDX_alignments_workspace_id"`);
    await queryRunner.query(`DROP INDEX "IDX_passages_patent_id"`);
    await queryRunner.query(`DROP INDEX "IDX_clauses_claim_id"`);
    await queryRunner.query(`DROP INDEX "IDX_claims_patent_id"`);
    await queryRunner.query(`DROP INDEX "IDX_patents_family_id"`);
    await queryRunner.query(`DROP INDEX "IDX_patents_workspace_id"`);
    await queryRunner.query(`DROP INDEX "IDX_workspaces_org_id"`);

    // Drop vector indexes
    await queryRunner.query(`DROP INDEX "IDX_passages_embedding"`);
    await queryRunner.query(`DROP INDEX "IDX_clauses_embedding"`);
    await queryRunner.query(`DROP INDEX "IDX_claims_embedding"`);

    // Drop tables
    await queryRunner.query(`DROP TABLE "audit_log"`);
    await queryRunner.query(`DROP TABLE "citations"`);
    await queryRunner.query(`DROP TABLE "claim_charts"`);
    await queryRunner.query(`DROP TABLE "search_sessions"`);
    await queryRunner.query(`DROP TABLE "novelty_scores"`);
    await queryRunner.query(`DROP TABLE "alignments"`);
    await queryRunner.query(`DROP TABLE "passages"`);
    await queryRunner.query(`DROP TABLE "clauses"`);
    await queryRunner.query(`DROP TABLE "claims"`);
    await queryRunner.query(`DROP TABLE "patents"`);
    await queryRunner.query(`DROP TABLE "memberships"`);
    await queryRunner.query(`DROP TABLE "workspaces"`);
    await queryRunner.query(`DROP TABLE "users"`);
    await queryRunner.query(`DROP TABLE "orgs"`);

    // Drop pgvector extension
    await queryRunner.query(`DROP EXTENSION IF EXISTS vector`);
  }
}
