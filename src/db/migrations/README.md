# Alembic Migrations

Database migrations for Amazon-1688 Selector v2.2.

## Quick Start

```bash
# From project root
python3 src/db/migrate.py upgrade    # Run all migrations
python3 src/db/migrate.py status     # Check status
python3 src/db/migrate.py --help     # All commands
```

## Files

- `alembic.ini` - Alembic configuration (database URL, etc.)
- `env.py` - Migration environment setup
- `versions/` - Migration scripts
  - `001_initial.py` - Core tables (products, product_images, product_features)
  - `002_history.py` - History tables (product_history, price_history, bsr_history)

## Database Configuration

### SQLite (Development)
```ini
sqlalchemy.url = sqlite:////path/to/data/amazon_1688_selector.db
```

### PostgreSQL (Production)
```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/amazon_1688_selector
```

## Common Commands

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one step
alembic downgrade -1

# Check current version
alembic current

# View history
alembic history

# Generate new migration
alembic revision --autogenerate -m "description"
```

## Documentation

See [docs/04-Technical-Docs/migration-guide.md](../../../docs/04-Technical-Docs/migration-guide.md) for complete documentation.
