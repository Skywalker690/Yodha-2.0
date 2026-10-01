# Agent and Contributor Instructions

## Mandatory workflow

For every feature, bug fix, refactor, model change, data change, or UI change:

1. Read this file and [`docs/00-index.md`](docs/00-index.md).
2. Read the documents relevant to the requested change.
3. Confirm that the change stays within [`docs/01-product-requirements.md`](docs/01-product-requirements.md).
4. Update [`docs/09-decision-log.md`](docs/09-decision-log.md) when a new decision is made.
5. Implement the smallest change satisfying the documented requirement.
6. Run the applicable checks in [`docs/07-testing-validation.md`](docs/07-testing-validation.md).
7. Update documentation when behavior, commands, data formats, or assumptions change.

Do not begin coding from the slide deck alone. The deck defines the product concept; `docs/` defines the implementation contract.

## Project principles

- Build the full-stack product described in the current plan.
- Keep the entire product local and simple to run.
- Prefer a small number of clear services over premature microservices.
- Make cached, illustrative, and model-generated outputs explicit.
- Keep frontend, backend, persistence, and ML code separated by responsibility.
- Never describe this research prototype as clinically validated.
- Do not commit raw MRI archives, large derived datasets, credentials, or secrets.

## Preferred stack

- Next.js with TypeScript
- Tailwind CSS and shadcn/ui
- Recharts and Lucide
- FastAPI with Pydantic
- SQLAlchemy and Alembic
- PostgreSQL
- PyTorch, MONAI, NiBabel, NumPy, and Pandas
- JWT authentication
- Docker Compose for local services
- Local PostgreSQL and local filesystem or S3-compatible object storage
- PyTest and the Next.js testing stack

Do not add Kubernetes, Kafka, Redis, a service mesh, or additional microservices unless a documented requirement makes one necessary.

## Coding expectations

- Use type hints for public Python functions and strict TypeScript where practical.
- Validate file paths, metadata, uploads, and model inputs.
- Return structured results rather than UI-specific dictionaries from ML code.
- Treat analysis as an asynchronous job. Do not block an HTTP request while MRI inference runs.
- Keep UI components small and accessible.
- Use stable random seeds for generated demo data.
- Prefer clear error messages over silent fallbacks.
