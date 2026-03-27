"""Initial database schema - products, product_images, product_features

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema: products, product_images, product_features"""
    
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asin', sa.String(length=20), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('brand', sa.String(length=200), nullable=True),
        sa.Column('category', sa.String(length=300), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('bsr', sa.Integer(), nullable=True),
        sa.Column('bsr_category', sa.String(length=300), nullable=True),
        sa.Column('availability', sa.Boolean(), nullable=True),
        sa.Column('prime_eligible', sa.Boolean(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('product_url', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asin')
    )
    
    # Create indexes for products table
    op.create_index('idx_products_asin', 'products', ['asin'], unique=False)
    op.create_index('idx_products_brand', 'products', ['brand'], unique=False)
    op.create_index('idx_products_price', 'products', ['price'], unique=False)
    op.create_index('idx_products_bsr', 'products', ['bsr'], unique=False)
    op.create_index('idx_products_rating', 'products', ['rating'], unique=False)
    op.create_index('idx_products_created_at', 'products', ['created_at'], unique=False)
    
    # Create product_images table
    op.create_table(
        'product_images',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for product_images table
    op.create_index('idx_product_images_product_id', 'product_images', ['product_id'], unique=False)
    op.create_index('idx_product_images_position', 'product_images', ['product_id', 'position'], unique=False)
    
    # Create product_features table
    op.create_table(
        'product_features',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('feature_text', sa.Text(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for product_features table
    op.create_index('idx_product_features_product_id', 'product_features', ['product_id'], unique=False)
    op.create_index('idx_product_features_position', 'product_features', ['product_id', 'position'], unique=False)


def downgrade() -> None:
    """Drop initial schema tables"""
    
    # Drop product_features table
    op.drop_index('idx_product_features_position', table_name='product_features')
    op.drop_index('idx_product_features_product_id', table_name='product_features')
    op.drop_table('product_features')
    
    # Drop product_images table
    op.drop_index('idx_product_images_position', table_name='product_images')
    op.drop_index('idx_product_images_product_id', table_name='product_images')
    op.drop_table('product_images')
    
    # Drop products table indexes
    op.drop_index('idx_products_created_at', table_name='products')
    op.drop_index('idx_products_bsr', table_name='products')
    op.drop_index('idx_products_price', table_name='products')
    op.drop_index('idx_products_brand', table_name='products')
    op.drop_index('idx_products_asin', table_name='products')
    
    # Drop products table
    op.drop_table('products')
