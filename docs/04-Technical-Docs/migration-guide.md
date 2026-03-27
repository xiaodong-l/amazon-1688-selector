# Database Migration Guide

**Version:** v2.2  
**Last Updated:** 2026-03-27  
**Tool:** Alembic (SQLAlchemy migration tool)

This guide covers database version management for the Amazon-1688 Selector project using Alembic.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Migration Commands](#migration-commands)
4. [Version Management Workflow](#version-management-workflow)
5. [Database Configuration](#database-configuration)
6. [Creating New Migrations](#creating-new-migrations)
7. [Troubleshooting](#troubleshooting)
8. [PostgreSQL Partitioning](#postgresql-partitioning)

---

## Overview

Alembic is a database migration tool that manages schema changes over time. Each migration is a versioned script that can upgrade or downgrade the database schema.

**Key Files:**
- `src/db/migrations/alembic.ini` - Alembic configuration
- `src/db/migrations/env.py` - Migration environment setup
- `src/db/migrations/versions/` - Migration scripts
- `src/db/models.py` - SQLAlchemy model definitions
- `src/db/migrate.py` - Convenience CLI utility

---

## Quick Start

### Initialize Database (First Time)

```bash
cd /home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector

# Run all migrations to create initial schema
python src/db/migrate.py upgrade

# Verify migration status
python src/db/migrate.py status
```

### Using Alembic Directly

```bash
cd src/db/migrations

# Upgrade to latest
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history
```

---

## Migration Commands

### Upgrade Commands

```bash
# Upgrade to latest version
python src/db/migrate.py upgrade

# Upgrade to specific revision
python src/db/migrate.py upgrade 001_initial

# Upgrade by steps (+2 means 2 migrations forward)
alembic upgrade +2
```

### Downgrade Commands

```bash
# Downgrade one step
python src/db/migrate.py downgrade

# Downgrade to specific revision
python src/db/migrate.py downgrade 001_initial

# Downgrade to base (drop all tables)
python src/db/migrate.py downgrade base

# Downgrade by steps (-2 means 2 migrations back)
alembic downgrade -2
```

### Status & Information

```bash
# Show current version
python src/db/migrate.py current

# Show detailed status
python src/db/migrate.py status

# Show migration history
python src/db/migrate.py history

# Show available heads
python src/db/migrate.py heads
```

### Advanced Commands

```bash
# Stamp database at revision (without running migrations)
python src/db/migrate.py stamp 001_initial

# Generate new migration (autogenerate from models)
cd src/db/migrations
alembic revision --autogenerate -m "description"

# Generate empty migration
alembic revision -m "description"
```

---

## Version Management Workflow

### Creating a New Migration

1. **Update models** in `src/db/models.py`

2. **Generate migration** (autogenerate):
   ```bash
   cd src/db/migrations
   alembic revision --autogenerate -m "add_new_column"
   ```

3. **Review the generated migration** in `versions/`:
   - Check that all changes are correct
   - Add any missing operations manually
   - Ensure downgrade() is properly implemented

4. **Test the migration**:
   ```bash
   # Test upgrade
   alembic upgrade head
   
   # Test downgrade
   alembic downgrade -1
   
   # Test upgrade again
   alembic upgrade head
   ```

5. **Commit the migration** to version control

### Release Workflow

```bash
# Before release: ensure all migrations run
python src/db/migrate.py upgrade

# Verify database is at head
python src/db/migrate.py current

# Document any breaking changes in release notes
```

---

## Database Configuration

### SQLite (Development)

Default configuration in `alembic.ini`:
```ini
sqlalchemy.url = sqlite:///../../data/amazon_1688_selector.db
```

### PostgreSQL (Production)

Update `alembic.ini`:
```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/amazon_1688_selector
```

Or use environment variable:
```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/amazon_1688_selector
```

### Connection String Formats

```
# SQLite
sqlite:///path/to/database.db
sqlite:///:memory:

# PostgreSQL
postgresql://user:password@host:port/database
postgresql+psycopg2://user:password@host:port/database

# MySQL
mysql://user:password@host:port/database
mysql+pymysql://user:password@host:port/database
```

---

## Creating New Migrations

### Manual Migration Template

```python
"""Add new column to products

Revision ID: 003_new_feature
Revises: 002_history
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa

revision = '003_new_feature'
down_revision = '002_history'

def upgrade():
    op.add_column('products', sa.Column('new_column', sa.String(100), nullable=True))
    op.create_index('idx_products_new_column', 'products', ['new_column'])

def downgrade():
    op.drop_index('idx_products_new_column', table_name='products')
    op.drop_column('products', 'new_column')
```

### Common Operations

```python
# Add column
op.add_column('table_name', sa.Column('column_name', sa.String(50), nullable=True))

# Drop column
op.drop_column('table_name', 'column_name')

# Create index
op.create_index('idx_name', 'table_name', ['column_name'])

# Drop index
op.drop_index('idx_name', table_name='table_name')

# Create table
op.create_table('new_table',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(50), nullable=False),
    sa.PrimaryKeyConstraint('id')
)

# Drop table
op.drop_table('table_name')

# Alter column
op.alter_column('table_name', 'column_name',
                existing_type=sa.String(50),
                new_type=sa.String(100))
```

---

## Troubleshooting

### Migration Fails with "Table Already Exists"

**Cause:** Database was created manually or migration was already run.

**Solution:**
```bash
# Stamp database at current state without running migrations
python src/db/migrate.py stamp head
```

### Migration Fails with "Relation Does Not Exist"

**Cause:** Trying to downgrade past base or migration order issue.

**Solution:**
```bash
# Check current version
python src/db/migrate.py current

# Check migration history
python src/db/migrate.py history

# Reset if needed (DANGER: drops all data!)
python src/db/migrate.py downgrade base
python src/db/migrate.py upgrade head
```

### Autogenerate Detects Unwanted Changes

**Cause:** Models don't match database or Alembic can't detect all changes.

**Solution:**
1. Review the generated migration carefully
2. Remove unwanted operations before running
3. Ensure `target_metadata = Base.metadata` in `env.py`

### Database Lock (SQLite)

**Cause:** Database file is locked by another process.

**Solution:**
```bash
# Find and kill processes using the database
lsof | grep amazon_1688_selector.db

# Or wait for other processes to complete
```

### PostgreSQL Connection Issues

**Cause:** Wrong credentials or database doesn't exist.

**Solution:**
```bash
# Create database first
createdb amazon_1688_selector

# Or with psql
psql -U postgres -c "CREATE DATABASE amazon_1688_selector;"

# Verify connection
psql postgresql://user:password@localhost:5432/amazon_1688_selector
```

### Migration Script Has Errors

**Cause:** Syntax error or invalid operation in migration script.

**Solution:**
1. Check the error message for line number
2. Review Alembic documentation for correct syntax
3. Test in a fresh database before deploying

---

## PostgreSQL Partitioning

For production PostgreSQL deployments with large history tables, consider partitioning.

### Why Partition?

- Better query performance for time-range queries
- Easier data retention management (drop old partitions)
- Improved vacuum/maintenance performance

### Partitioning History Tables

**Note:** Partitioning must be done manually as Alembic doesn't support it natively.

#### Option 1: Manual Partitioning (Recommended)

Create partitioned table manually, then use Alembic for other changes:

```sql
-- Create partitioned table
CREATE TABLE product_history (
    id SERIAL,
    asin VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    snapshot_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id, snapshot_date)
) PARTITION BY RANGE (snapshot_date);

-- Create monthly partitions
CREATE TABLE product_history_y2026m01 PARTITION OF product_history
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE product_history_y2026m02 PARTITION OF product_history
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

#### Option 2: Use pg_partman Extension

```sql
-- Install extension
CREATE EXTENSION pg_partman;

-- Create parent table with pg_partman
SELECT partman.create_parent('public.product_history', 'snapshot_date', 'native', 'monthly');
```

### Migration Considerations

When using partitioning:

1. **Initial migration:** Create base partitioned table
2. **Ongoing:** Create new partitions as needed (automated via cron/pg_partman)
3. **Downgrade:** More complex - may need to merge partition data

---

## Migration History

| Revision | Description | Tables | Date |
|----------|-------------|--------|------|
| 001_initial | Initial schema | products, product_images, product_features | 2026-03-27 |
| 002_history | History tracking | product_history, price_history, bsr_history | 2026-03-27 |

## Schema Overview

### Core Tables (001_initial)

**products** - Main product data
- Primary fields: id, asin, title, brand, price, rating, bsr, availability
- Timestamps: created_at, updated_at
- Indexes: asin, brand, price, bsr, rating, created_at

**product_images** - Multiple images per product
- Fields: id, product_id (FK), image_url, position, is_primary
- Indexes: product_id, (product_id, position)

**product_features** - Product bullet points/features
- Fields: id, product_id (FK), feature_text, position
- Indexes: product_id, (product_id, position)

### History Tables (002_history)

**product_history** - Product snapshots over time
- Fields: id, product_id (FK), asin, title, price, rating, review_count, bsr, recorded_at
- Indexes: product_id, asin, recorded_at, (asin, recorded_at), (product_id, recorded_at)
- PostgreSQL: Consider partitioning by `recorded_at`

**price_history** - Price tracking
- Fields: id, product_id (FK), asin, price, currency, recorded_at
- Indexes: product_id, asin, recorded_at, (asin, recorded_at)

**bsr_history** - Best Sellers Rank tracking
- Fields: id, product_id (FK), asin, bsr, bsr_category, recorded_at
- Indexes: product_id, asin, recorded_at, (asin, recorded_at)

---

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review [Alembic Documentation](https://alembic.sqlalchemy.org/)
3. Check project issues on GitHub
