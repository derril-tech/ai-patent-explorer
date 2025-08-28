import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Membership } from '../entities/Membership';

@Injectable()
export class WorkspaceGuard implements CanActivate {
  constructor(
    @InjectRepository(Membership)
    private membershipRepository: Repository<Membership>,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;
    const workspaceId = request.headers['x-workspace-id'] || request.body?.workspace_id || request.query?.workspace_id;

    if (!user || !workspaceId) {
      throw new ForbiddenException('User or workspace not specified');
    }

    // Check if user is a member of the workspace
    const membership = await this.membershipRepository.findOne({
      where: {
        user_id: user.id,
        workspace_id: workspaceId,
      },
    });

    if (!membership) {
      throw new ForbiddenException('Access denied to workspace');
    }

    return true;
  }
}
