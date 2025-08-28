import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  
  // Get config service
  const configService = app.get(ConfigService);
  
  // Enable CORS
  app.enableCors({
    origin: configService.get('FRONTEND_URL', 'http://localhost:3000'),
    credentials: true,
  });
  
  // Global validation pipe
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,
    forbidNonWhitelisted: true,
    transform: true,
  }));
  
  // Global prefix
  app.setGlobalPrefix('api/v1');
  
  // Start the application
  const port = configService.get('PORT', 3001);
  await app.listen(port);
  
  console.log(`🚀 API server running on port ${port}`);
  console.log(`📚 Patent Explorer API v1.0.0`);
  console.log(`🔗 Health check: http://localhost:${port}/api/v1/health`);
}

bootstrap().catch((error) => {
  console.error('Failed to start API server:', error);
  process.exit(1);
});
