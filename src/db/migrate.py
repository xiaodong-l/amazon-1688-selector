#!/usr/bin/env python3
"""
Database Migration Utility for Amazon-1688 Selector v2.2

This script provides a convenient interface for running database migrations
using Alembic. It supports both SQLite (development) and PostgreSQL (production).

Usage:
    python migrate.py upgrade [revision]    # Run migrations up to revision (default: head)
    python migrate.py downgrade [revision]  # Run migrations down to revision (default: -1)
    python migrate.py current               # Show current migration version
    python migrate.py history               # Show migration history
    python migrate.py heads                 # Show available head revisions
    python migrate.py stamp [revision]      # Stamp database at revision without running migrations

Examples:
    python migrate.py upgrade               # Upgrade to latest (head)
    python migrate.py upgrade 001_initial   # Upgrade to specific revision
    python migrate.py downgrade -1          # Downgrade one step
    python migrate.py downgrade base        # Downgrade to initial state (drop all tables)
    python migrate.py current               # Check current version

Environment Variables:
    DATABASE_URL          Override database URL (optional)
    ALEMBIC_CONFIG        Path to alembic.ini (default: migrations/alembic.ini)
"""

import os
import sys
import argparse
from pathlib import Path

# Add migrations directory to path
current_dir = Path(__file__).parent
migrations_dir = current_dir / 'migrations'
sys.path.insert(0, str(migrations_dir))

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory


def get_alembic_config():
    """Get Alembic configuration"""
    alembic_config_path = os.environ.get(
        'ALEMBIC_CONFIG', 
        str(migrations_dir / 'alembic.ini')
    )
    return Config(alembic_config_path)


def upgrade(revision='head'):
    """
    Run migrations up to the specified revision.
    
    Args:
        revision: Target revision (default: 'head' for latest)
    """
    config = get_alembic_config()
    print(f"🔼 Upgrading database to revision: {revision}")
    command.upgrade(config, revision)
    print("✅ Migration completed successfully!")


def downgrade(revision='-1'):
    """
    Run migrations down to the specified revision.
    
    Args:
        revision: Target revision (default: '-1' for one step back)
                  Use 'base' to drop all tables
    """
    config = get_alembic_config()
    print(f"🔽 Downgrading database to revision: {revision}")
    command.downgrade(config, revision)
    print("✅ Downgrade completed successfully!")


def current():
    """Show current migration version"""
    config = get_alembic_config()
    print("📍 Current migration version:")
    command.current(config)


def history():
    """Show migration history"""
    config = get_alembic_config()
    print("📜 Migration history:")
    command.history(config)


def heads():
    """Show available head revisions"""
    config = get_alembic_config()
    print("🎯 Available head revisions:")
    command.heads(config)


def stamp(revision):
    """
    Stamp the database at a specific revision without running migrations.
    Useful for initializing existing databases.
    
    Args:
        revision: Revision to stamp
    """
    config = get_alembic_config()
    print(f"🏷️  Stamping database at revision: {revision}")
    command.stamp(config, revision)
    print("✅ Stamp completed!")


def show_status():
    """Show detailed migration status"""
    from sqlalchemy import create_engine
    from alembic.runtime.migration import MigrationContext
    
    config = get_alembic_config()
    script = ScriptDirectory.from_config(config)
    
    print("\n📊 Migration Status")
    print("=" * 60)
    
    # Get current revision
    
    # Get database URL from config
    db_url = config.get_main_option('sqlalchemy.url')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()
        
        print(f"Current revision: {current_rev or 'None (unmigrated)'}")
        print(f"Latest revision:  {script.get_current_head()}")
        
        if current_rev:
            is_latest = current_rev == script.get_current_head()
            print(f"Status:           {'✅ Up to date' if is_latest else '⚠️  Behind - migrations pending'}")
        else:
            print(f"Status:           ⚠️  Database not initialized")
    
    print("\nAvailable revisions:")
    for rev in script.walk_revisions():
        marker = "→" if rev.revision == current_rev else " "
        print(f"  {marker} {rev.revision[:12]:<12} {rev.doc}")
    print("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Database Migration Utility for Amazon-1688 Selector',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', help='Run migrations up')
    upgrade_parser.add_argument(
        'revision', 
        nargs='?', 
        default='head',
        help='Target revision (default: head)'
    )
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser('downgrade', help='Run migrations down')
    downgrade_parser.add_argument(
        'revision', 
        nargs='?', 
        default='-1',
        help='Target revision (default: -1, use "base" to drop all)'
    )
    
    # Current command
    subparsers.add_parser('current', help='Show current migration version')
    
    # History command
    subparsers.add_parser('history', help='Show migration history')
    
    # Heads command
    subparsers.add_parser('heads', help='Show available head revisions')
    
    # Stamp command
    stamp_parser = subparsers.add_parser('stamp', help='Stamp database at revision')
    stamp_parser.add_argument('revision', help='Revision to stamp')
    
    # Status command
    subparsers.add_parser('status', help='Show detailed migration status')
    
    args = parser.parse_args()
    
    if args.command == 'upgrade':
        upgrade(args.revision)
    elif args.command == 'downgrade':
        downgrade(args.revision)
    elif args.command == 'current':
        current()
    elif args.command == 'history':
        history()
    elif args.command == 'heads':
        heads()
    elif args.command == 'stamp':
        stamp(args.revision)
    elif args.command == 'status':
        show_status()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
