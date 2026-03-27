"""
Database CLI for Amazon Selector v2.2

Provides command-line interface for database operations.

Usage:
    python -m src.db.cli init-db
    python -m src.db.cli migrate
    python -m src.db.cli backup
    python -m src.db.cli restore --file backup.sql
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)


def init_db_command(test_mode: bool = False):
    """
    Initialize database tables.
    
    Args:
        test_mode: If True, use test database configuration
    """
    from .connection import init_db, get_engine
    from .models import Base
    
    logger.info("🔧 Initializing database...")
    
    try:
        init_db(test_mode)
        logger.info("✅ Database initialized successfully!")
        
        # Show database info
        engine = get_engine(test_mode)
        logger.info(f"📍 Database URL: {engine.url}")
        
        # List created tables
        tables = Base.metadata.tables.keys()
        logger.info(f"📊 Created {len(tables)} tables: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


async def init_db_async_command(test_mode: bool = False):
    """
    Initialize database tables (async version).
    
    Args:
        test_mode: If True, use test database configuration
    """
    from .connection import init_db_async, get_async_engine
    from .models import Base
    
    logger.info("🔧 Initializing database (async)...")
    
    try:
        await init_db_async(test_mode)
        logger.info("✅ Database initialized successfully!")
        
        # Show database info
        engine = get_async_engine(test_mode)
        logger.info(f"📍 Database URL: {engine.url}")
        
        # List created tables
        tables = Base.metadata.tables.keys()
        logger.info(f"📊 Created {len(tables)} tables: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


def migrate_command():
    """
    Run database migrations using Alembic.
    """
    import subprocess
    
    logger.info("🔄 Running database migrations...")
    
    try:
        # Find alembic.ini
        migrations_dir = Path(__file__).parent / "migrations"
        
        if not migrations_dir.exists():
            logger.error("❌ Migrations directory not found!")
            sys.exit(1)
        
        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=migrations_dir,
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info("✅ Migrations completed successfully!")
            if result.stdout:
                logger.info(result.stdout)
        else:
            logger.error(f"❌ Migration failed: {result.stderr}")
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("❌ Alembic not found. Install with: pip install alembic")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


def backup_command(output_file: str = None):
    """
    Backup database to SQL file.
    
    Args:
        output_file: Output file path (default: backup_YYYYMMDD_HHMMSS.sql)
    """
    from .connection import get_engine, get_database_url
    
    logger.info("💾 Creating database backup...")
    
    try:
        # Generate filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"backup_{timestamp}.sql"
        
        # Get database info
        db_url = get_database_url()
        engine = get_engine()
        
        # Check if SQLite or PostgreSQL
        if db_url.startswith("sqlite"):
            # SQLite backup - just copy the file
            db_path = db_url.replace("sqlite:///", "")
            db_file = Path(db_path)
            
            if not db_file.exists():
                logger.error(f"❌ Database file not found: {db_file}")
                sys.exit(1)
            
            # Copy database file
            backup_path = Path(output_file).with_suffix(".db")
            shutil.copy2(db_file, backup_path)
            
            logger.info(f"✅ Database backed up to: {backup_path}")
            
        elif db_url.startswith("postgresql"):
            # PostgreSQL backup using pg_dump
            import subprocess
            
            # Extract connection info from URL
            # Format: postgresql://user:pass@host:port/dbname
            result = subprocess.run(
                ["pg_dump", db_url, "-f", output_file],
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Database backed up to: {output_file}")
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                sys.exit(1)
        else:
            logger.error(f"❌ Unsupported database type: {db_url}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        sys.exit(1)


def restore_command(input_file: str):
    """
    Restore database from backup file.
    
    Args:
        input_file: Backup file path
    """
    from .connection import get_engine, get_database_url
    
    logger.info("♻️  Restoring database from backup...")
    
    try:
        input_path = Path(input_file)
        
        if not input_path.exists():
            logger.error(f"❌ Backup file not found: {input_file}")
            sys.exit(1)
        
        # Get database info
        db_url = get_database_url()
        engine = get_engine()
        
        # Check if SQLite or PostgreSQL
        if db_url.startswith("sqlite"):
            # SQLite restore - copy backup file
            db_path = db_url.replace("sqlite:///", "")
            db_file = Path(db_path)
            
            # Backup current database first
            if db_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = db_file.with_suffix(f".db.backup_{timestamp}")
                shutil.copy2(db_file, backup_path)
                logger.info(f"💾 Current database backed up to: {backup_path}")
            
            # Restore from backup
            shutil.copy2(input_path, db_file)
            logger.info(f"✅ Database restored from: {input_file}")
            
        elif db_url.startswith("postgresql"):
            # PostgreSQL restore using psql
            import subprocess
            
            result = subprocess.run(
                ["psql", db_url, "-f", input_file],
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Database restored from: {input_file}")
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                sys.exit(1)
        else:
            logger.error(f"❌ Unsupported database type: {db_url}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        sys.exit(1)


def status_command():
    """
    Show database status and statistics.
    """
    from .connection import get_engine, get_database_url
    from sqlalchemy import text, func
    from .models import Base
    
    logger.info("📊 Database Status")
    logger.info("=" * 50)
    
    try:
        engine = get_engine()
        db_url = get_database_url()
        
        logger.info(f"📍 Database URL: {engine.url}")
        logger.info(f"📊 Tables: {len(Base.metadata.tables)}")
        
        # Try to get row counts
        with engine.connect() as conn:
            for table_name in Base.metadata.tables.keys():
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    )
                    count = result.scalar()
                    logger.info(f"   - {table_name}: {count} rows")
                except Exception as e:
                    logger.warning(f"   - {table_name}: Error - {e}")
        
        logger.info("=" * 50)
        logger.info("✅ Database status OK")
        
    except Exception as e:
        logger.error(f"❌ Database status check failed: {e}")
        sys.exit(1)


def drop_db_command(confirmation: str = None):
    """
    Drop all database tables.
    
    Args:
        confirmation: Must be 'yes' to confirm
    """
    from .connection import drop_db, get_database_url
    
    if confirmation != 'yes':
        logger.warning("⚠️  This will DELETE ALL DATA!")
        logger.warning("⚠️  Run with --confirmation yes to proceed")
        sys.exit(1)
    
    logger.info("🗑️  Dropping all database tables...")
    
    try:
        drop_db()
        logger.info("✅ All tables dropped successfully!")
        logger.info(f"📍 Database URL: {get_database_url()}")
        
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        sys.exit(1)


async def async_status_command():
    """
    Show database status (async version).
    """
    from .connection import get_async_engine, get_database_url
    from sqlalchemy import text
    from .models import Base
    
    logger.info("📊 Database Status (Async)")
    logger.info("=" * 50)
    
    try:
        engine = get_async_engine()
        
        logger.info(f"📍 Database URL: {engine.url}")
        logger.info(f"📊 Tables: {len(Base.metadata.tables)}")
        
        async with engine.connect() as conn:
            for table_name in Base.metadata.tables.keys():
                try:
                    result = await conn.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    )
                    count = result.scalar()
                    logger.info(f"   - {table_name}: {count} rows")
                except Exception as e:
                    logger.warning(f"   - {table_name}: Error - {e}")
        
        logger.info("=" * 50)
        logger.info("✅ Database status OK")
        
    except Exception as e:
        logger.error(f"❌ Database status check failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Amazon Selector Database CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init-db command
    init_parser = subparsers.add_parser("init-db", help="Initialize database tables")
    init_parser.add_argument("--async", dest="use_async", action="store_true",
                            help="Use async initialization")
    init_parser.add_argument("--test", action="store_true",
                            help="Use test database configuration")
    
    # migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    
    # backup command
    backup_parser = subparsers.add_parser("backup", help="Backup database")
    backup_parser.add_argument("--file", "-f", type=str, default=None,
                              help="Output file path")
    
    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("--file", "-f", type=str, required=True,
                               help="Backup file to restore from")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show database status")
    status_parser.add_argument("--async", dest="use_async", action="store_true",
                              help="Use async status check")
    
    # drop command
    drop_parser = subparsers.add_parser("drop", help="Drop all database tables")
    drop_parser.add_argument("--confirmation", type=str, required=True,
                            help="Type 'yes' to confirm")
    
    args = parser.parse_args()
    
    if args.command == "init-db":
        if args.use_async:
            asyncio.run(init_db_async_command(args.test))
        else:
            init_db_command(args.test)
    
    elif args.command == "migrate":
        migrate_command()
    
    elif args.command == "backup":
        backup_command(args.file)
    
    elif args.command == "restore":
        restore_command(args.file)
    
    elif args.command == "status":
        if args.use_async:
            asyncio.run(async_status_command())
        else:
            status_command()
    
    elif args.command == "drop":
        drop_db_command(args.confirmation)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
