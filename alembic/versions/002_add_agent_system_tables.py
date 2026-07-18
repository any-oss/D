"""Add agent system tables for multi-agent architecture

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Agent registry and configuration tables
    op.create_table('agent_registry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('host', sa.String(length=255)),
        sa.Column('port', sa.Integer()),
        sa.Column('status', sa.String(length=20), default='unknown'),
        sa.Column('last_heartbeat', sa.DateTime()),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('metadata', sa.JSON()),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('agent_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('config_json', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(length=20), default='1.0.0'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('version', sa.String(length=20), default='1.0.0'),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(length=50)),
        sa.Column('tags', sa.ARRAY(sa.String())),
        sa.Column('input_schema', sa.JSON()),
        sa.Column('output_schema', sa.JSON()),
        sa.Column('handler_module', sa.String(length=255)),
        sa.Column('handler_class', sa.String(length=255)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('short_term_memory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.ARRAY(sa.Float())),
        sa.Column('importance_score', sa.Float(), default=0.5),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata', sa.JSON()),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('long_term_memory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('memory_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.ARRAY(sa.Float())),
        sa.Column('summary', sa.Text()),
        sa.Column('confidence_score', sa.Float(), default=1.0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata', sa.JSON()),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('version', sa.String(length=20), default='1.0.0'),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(length=50)),
        sa.Column('tags', sa.ARRAY(sa.String())),
        sa.Column('input_schema', sa.JSON(), nullable=False),
        sa.Column('output_schema', sa.JSON()),
        sa.Column('handler_module', sa.String(length=255)),
        sa.Column('handler_class', sa.String(length=255)),
        sa.Column('timeout_seconds', sa.Integer(), default=30),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('routing_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('priority', sa.Integer(), default=100),
        sa.Column('match_conditions', sa.JSON(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('target_agents', sa.ARRAY(sa.String())),
        sa.Column('weight_distribution', sa.JSON()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'))
    
    op.create_table('request_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=100), nullable=False, unique=True),
        sa.Column('task_type', sa.String(length=50)),
        sa.Column('payload', sa.JSON()),
        sa.Column('priority', sa.Integer(), default=5),
        sa.Column('status', sa.String(length=20), default='pending'),
        sa.Column('assigned_agent', sa.String(length=100)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'))


def downgrade():
    op.drop_table('request_queue')
    op.drop_table('routing_rules')
    op.drop_table('tools')
    op.drop_table('long_term_memory')
    op.drop_table('short_term_memory')
    op.drop_table('skills')
    op.drop_table('agent_configs')
    op.drop_table('agent_registry')
