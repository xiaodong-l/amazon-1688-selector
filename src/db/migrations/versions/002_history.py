"""History tables - product_history, price_history, bsr_history

Revision ID: 002_history
Revises: 001_initial
Create Date: 2026-03-27

NOTE: For PostgreSQL production deployments, consider partitioning:
- product_history: PARTITION BY RANGE (recorded_at)
- price_history: PARTITION BY RANGE (recorded_at)
- bsr_history: PARTITION BY RANGE (recorded_at)

Example PostgreSQL partitioning:
    CREATE TABLE product_history (...) PARTITION BY RANGE (recorded_at);
    CREATE TABLE product_history_y2026m01 PARTITION OF product_history
        FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_history'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create history tables for tracking changes over time"""
    
    # Create product_history table
    # NOTE: In PostgreSQL, consider partitioning by recorded_at (monthly/quarterly)
    op.create_table(
        'product_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('bsr', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for product_history table
    op.create_index('idx_product_history_product_id', 'product_history', ['product_id'], unique=False)
    op.create_index('idx_product_history_asin', 'product_history', ['asin'], unique=False)
    op.create_index('idx_product_history_recorded', 'product_history', ['recorded_at'], unique=False)
    op.create_index('idx_product_history_asin_recorded', 'product_history', ['asin', 'recorded_at'], unique=False)
    op.create_index('idx_product_history_product_recorded', 'product_history', ['product_id', 'recorded_at'], unique=False)
    
    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=20), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for price_history table
    op.create_index('idx_price_history_product_id', 'price_history', ['product_id'], unique=False)
    op.create_index('idx_price_history_asin', 'price_history', ['asin'], unique=False)
    op.create_index('idx_price_history_recorded', 'price_history', ['recorded_at'], unique=False)
    op.create_index('idx_price_history_asin_recorded', 'price_history', ['asin', 'recorded_at'], unique=False)
    
    # Create bsr_history table
    op.create_table(
        'bsr_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=20), nullable=False),
        sa.Column('bsr', sa.Integer(), nullable=False),
        sa.Column('bsr_category', sa.String(length=300), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for bsr_history table
    op.create_index('idx_bsr_history_product_id', 'bsr_history', ['product_id'], unique=False)
    op.create_index('idx_bsr_history_asin', 'bsr_history', ['asin'], unique=False)
    op.create_index('idx_bsr_history_recorded', 'bsr_history', ['recorded_at'], unique=False)
    op.create_index('idx_bsr_history_asin_recorded', 'bsr_history', ['asin', 'recorded_at'], unique=False)


def downgrade() -> None:
    """Drop history tables"""
    
    # Drop bsr_history table
    op.drop_index('idx_bsr_history_asin_recorded', table_name='bsr_history')
    op.drop_index('idx_bsr_history_recorded', table_name='bsr_history')
    op.drop_index('idx_bsr_history_asin', table_name='bsr_history')
    op.drop_index('idx_bsr_history_product_id', table_name='bsr_history')
    op.drop_table('bsr_history')
    
    # Drop price_history table
    op.drop_index('idx_price_history_asin_recorded', table_name='price_history')
    op.drop_index('idx_price_history_recorded', table_name='price_history')
    op.drop_index('idx_price_history_asin', table_name='price_history')
    op.drop_index('idx_price_history_product_id', table_name='price_history')
    op.drop_table('price_history')
    
    # Drop product_history table
    op.drop_index('idx_product_history_product_recorded', table_name='product_history')
    op.drop_index('idx_product_history_asin_recorded', table_name='product_history')
    op.drop_index('idx_product_history_recorded', table_name='product_history')
    op.drop_index('idx_product_history_asin', table_name='product_history')
    op.drop_index('idx_product_history_product_id', table_name='product_history')
    op.drop_table('product_history')
