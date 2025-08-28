# AI Patent Explorer

> **Find the most relevant prior art in seconds, align it to claim clauses, and quantify novelty—with traceable evidence and exportable claim charts.**

[![CI/CD](https://github.com/your-org/ai-patent-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/ai-patent-explorer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

## 🎯 What is AI Patent Explorer?

AI Patent Explorer is an advanced patent analysis platform that leverages artificial intelligence to revolutionize how legal professionals, researchers, and inventors conduct prior art searches and patent analysis. It combines semantic search, machine learning, and natural language processing to provide comprehensive patent insights with unprecedented speed and accuracy.

## 🚀 What does AI Patent Explorer do?

### Core Capabilities

1. **Intelligent Prior Art Search**
   - Hybrid retrieval combining keyword and semantic search
   - Real-time search across millions of patents
   - Advanced query planning with synonym expansion and CPC code analysis
   - Cross-encoder reranking for optimal result relevance

2. **Clause-Level Patent Analysis**
   - Automatic segmentation of patent claims into individual clauses
   - Precise alignment between patent claims and prior art references
   - Identification of overlaps, gaps, paraphrases, and ambiguous elements
   - Detailed explanations for each alignment with confidence scores

3. **Novelty & Obviousness Scoring**
   - Clause-level novelty quantification (1 - max_similarity)
   - Claim-level weighted aggregate scoring
   - Obviousness analysis with multi-document penalties
   - Calibration by CPC class and filing decade
   - Confidence bands and statistical validation

4. **Automated Claim Chart Generation**
   - Professional DOCX and PDF claim charts
   - Export bundles with comprehensive analysis
   - Customizable chart templates and formatting
   - Integration with legal workflow tools

5. **Portfolio & Citation Analysis**
   - Patent family tree visualization
   - Citation graph analytics with centrality metrics
   - Novelty trends and portfolio insights
   - Automated alerts for new relevant patents

## 💡 Benefits of AI Patent Explorer

### For Legal Professionals
- **Time Savings**: Reduce prior art search time from days to minutes
- **Accuracy**: AI-powered analysis reduces human error and bias
- **Comprehensive Coverage**: Never miss relevant prior art with semantic search
- **Evidence-Based**: Traceable analysis with detailed explanations
- **Professional Output**: Ready-to-use claim charts and reports

### For Patent Attorneys
- **Risk Mitigation**: Identify potential validity issues early
- **Client Communication**: Clear, visual explanations of patent strength
- **Efficiency**: Streamlined workflow from search to chart generation
- **Compliance**: Built-in legal disclaimers and audit trails
- **Scalability**: Handle multiple cases simultaneously

### For Inventors & Researchers
- **Innovation Insights**: Understand the competitive landscape
- **Gap Analysis**: Identify white space opportunities
- **Strategic Planning**: Make informed decisions about patent filing
- **Cost Reduction**: Efficient analysis reduces legal expenses
- **Educational Tool**: Learn from existing patent patterns

### For Organizations
- **IP Strategy**: Data-driven patent portfolio management
- **Competitive Intelligence**: Monitor competitor patent activity
- **Risk Assessment**: Evaluate patent infringement risks
- **ROI Optimization**: Focus resources on high-value patents
- **Compliance**: Maintain audit trails for regulatory requirements

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Workers       │
│   (Next.js 14)  │◄──►│   (NestJS)      │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │   OpenSearch    │
                       │   (pgvector)    │    │   (Keyword)     │
                       └─────────────────┘    └─────────────────┘
```

### Technology Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Backend**: NestJS, TypeScript, TypeORM
- **Workers**: Python 3.11, FastAPI, asyncpg
- **Database**: PostgreSQL 16 with pgvector extension
- **Search**: OpenSearch for keyword indexing
- **ML/AI**: Sentence Transformers, PyTorch, scikit-learn
- **Infrastructure**: Docker, Redis, NATS, MinIO
- **Observability**: OpenTelemetry, Prometheus, Grafana, Sentry

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+
- Python 3.11+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/ai-patent-explorer.git
   cd ai-patent-explorer
   ```

2. **Start the development environment**
   ```bash
   docker-compose -f infra/docker-compose.dev.yml up -d
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Install worker dependencies**
   ```bash
   cd workers
   pip install -r requirements.txt
   ```

5. **Run database migrations**
   ```bash
   cd api
   npm run migration:run
   ```

6. **Start the workers**
   ```bash
   cd workers
   python -m src.main
   ```

### Environment Configuration

Copy the example environment files and configure your settings:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
cp workers/.env.example workers/.env
```

## 📖 Usage

### Basic Search

1. Navigate to the search interface
2. Enter your patent query or claim text
3. Apply filters (date range, CPC codes, assignees)
4. Review ranked results with relevance scores
5. Select patents for detailed analysis

### Patent Analysis

1. Select a target patent and reference patents
2. Run clause alignment analysis
3. Review novelty scores and explanations
4. Generate claim charts and reports
5. Export results in multiple formats

### Portfolio Management

1. Upload patent portfolios
2. Analyze citation networks
3. Track novelty trends
4. Set up automated alerts
5. Generate portfolio reports

## 🔧 Development

### Project Structure

```
ai-patent-explorer/
├── frontend/          # Next.js frontend application
├── api/              # NestJS API gateway
├── workers/          # Python worker services
├── infra/            # Infrastructure and deployment
├── docs/             # Documentation
└── tests/            # Test suites
```

### Running Tests

```bash
# Frontend tests
cd frontend
npm run test

# Backend tests
cd api
npm run test

# Worker tests
cd workers
pytest
```

### Code Quality

```bash
# Frontend linting
cd frontend
npm run lint
npm run type-check

# Backend linting
cd api
npm run lint

# Python formatting
cd workers
black src/
isort src/
```

## 📊 Performance & Scalability

- **Search Latency**: < 1.2s p95 for top-20 results
- **Alignment Accuracy**: ≥75% recall vs human labels
- **Novelty Calibration**: Brier score ≤0.18
- **Chart Generation**: < 5s p95 for DOCX/PDF
- **Concurrent Users**: 1000+ simultaneous searches
- **Patent Database**: 100M+ patents indexed

## 🔒 Security & Compliance

- **Authentication**: JWT-based with role-based access control
- **Data Protection**: Encryption at rest and in transit
- **Audit Logging**: Comprehensive activity tracking
- **Legal Compliance**: Built-in disclaimers and usage guidelines
- **Privacy**: GDPR-compliant data handling
- **Access Control**: Workspace-based isolation

## 📈 Monitoring & Observability

- **Distributed Tracing**: OpenTelemetry spans across all services
- **Metrics**: Prometheus metrics with Grafana dashboards
- **Error Tracking**: Sentry integration with sensitive data filtering
- **Health Checks**: Automated service health monitoring
- **Performance**: Real-time latency and throughput monitoring

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/ai-patent-explorer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ai-patent-explorer/discussions)
- **Email**: support@ai-patent-explorer.com

## 🙏 Acknowledgments

- Built with [Next.js](https://nextjs.org/)
- Powered by [NestJS](https://nestjs.com/)
- ML capabilities from [Hugging Face](https://huggingface.co/)
- Vector search with [pgvector](https://github.com/pgvector/pgvector)
- Observability with [OpenTelemetry](https://opentelemetry.io/)

---

**⚠️ Legal Disclaimer**: AI Patent Explorer provides AI-powered patent analysis tools for research and educational purposes only. The analysis results should not be considered as legal advice. Always consult with qualified legal professionals for patent-related decisions.
