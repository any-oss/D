"""
Alembic Migration: Add MCP, Agent Workflow, and Background Task Tables
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # ### MCP Server Configuration ###
    op.create_table('mcp_servers',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),  # filesystem, git, database, custom
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('auth_token', sa.String(255), nullable=True),
        sa.Column('max_connections', sa.Integer, default=5),
        sa.Column('timeout', sa.Float, default=30.0),
        sa.Column('pool_range_start', sa.Integer, default=0),
        sa.Column('pool_range_end', sa.Integer, default=100),
        sa.Column('status', sa.String(20), default='inactive'),  # active, inactive, error, maintenance
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Index for fast lookup by status
    op.create_index('ix_mcp_servers_status', 'mcp_servers', ['status'])

    # ### Execution Plans (Universal Remote) ###
    op.create_table('execution_plans',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('objective', sa.Text, nullable=False),
        sa.Column('status', sa.String(20), default='created'),  # created, running, completed, failed
        sa.Column('current_step', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True)
    )
    
    op.create_index('ix_execution_plans_status', 'execution_plans', ['status'])

    # ### Action Steps ###
    op.create_table('action_steps',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('plan_id', sa.String(50), sa.ForeignKey('execution_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_order', sa.Integer, nullable=False),
        sa.Column('action_type', sa.String(20), nullable=False),  # think, plan, execute, delegate, reflect, finish
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('agent_name', sa.String(50), nullable=True),
        sa.Column('tool_name', sa.String(50), nullable=True),
        sa.Column('params', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(20), default='pending'),  # pending, running, completed, failed
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    op.create_index('ix_action_steps_plan_id', 'action_steps', ['plan_id'])
    op.create_index('ix_action_steps_status', 'action_steps', ['status'])

    # ### Background Tasks Queue ###
    op.create_table('background_tasks',
        sa.Column('task_id', sa.String(50), primary_key=True),
        sa.Column('func_name', sa.String(100), nullable=False),
        sa.Column('args', postgresql.JSONB, default=list),
        sa.Column('kwargs', postgresql.JSONB, default=dict),
        sa.Column('priority', sa.Integer, default=5),  # 1=critical, 2=high, 5=normal, 10=low
        sa.Column('scheduled_at', sa.DateTime, nullable=False),
        sa.Column('status', sa.String(20), default='pending'),  # pending, running, completed, failed
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, default=0),
        sa.Column('max_retries', sa.Integer, default=3),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True)
    )
    
    op.create_index('ix_background_tasks_status', 'background_tasks', ['status'])
    op.create_index('ix_background_tasks_scheduled', 'background_tasks', ['scheduled_at'])
    op.create_index('ix_background_tasks_priority', 'background_tasks', ['priority', 'scheduled_at'])

    # ### Lazy Loading Cache Registry ###
    op.create_table('cache_registry',
        sa.Column('key', sa.String(255), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('loaded_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('access_count', sa.Integer, default=0),
        sa.Column('last_accessed', sa.DateTime, server_default=sa.func.now()),
        sa.Column('ttl_seconds', sa.Integer, default=300)
    )
    
    op.create_index('ix_cache_registry_last_accessed', 'cache_registry', ['last_accessed'])

    # ### Load Balancer Routing Rules ###
    op.create_table('load_balancer_rules',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('pattern', sa.String(255), nullable=False),  # URL pattern e.g., "/api/files/*"
        sa.Column('target_pool', sa.String(50), nullable=False),  # e.g., "fs_mcp", "agent_pool"
        sa.Column('weight', sa.Integer, default=1),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('health_check_endpoint', sa.String(255), nullable=True),
        sa.Column('circuit_breaker_state', sa.String(20), default='closed'),  # closed, open, half-open
        sa.Column('error_count', sa.Integer, default=0),
        sa.Column('last_error_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    op.create_index('ix_lb_rules_pattern', 'load_balancer_rules', ['pattern'])
    op.create_index('ix_lb_rules_active', 'load_balancer_rules', ['is_active'])

    # ### Request Queue for Traffic Aggregation ###
    op.create_table('request_queue',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('batch_id', sa.String(50), nullable=True),  # Groups aggregated requests
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), default='GET'),
        sa.Column('payload', postgresql.JSONB, default=dict),
        sa.Column('priority', sa.Integer, default=5),
        sa.Column('status', sa.String(20), default='queued'),  # queued, processing, completed, failed
        sa.Column('aggregated', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime, nullable=True)
    )
    
    op.create_index('ix_request_queue_status', 'request_queue', ['status'])
    op.create_index('ix_request_queue_batch', 'request_queue', ['batch_id'])

    # ### Sub-Agent Configurations ###
    op.create_table('sub_agent_configs',
        sa.Column('name', sa.String(50), primary_key=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('config_params', postgresql.JSONB, default=dict),
        sa.Column('max_concurrent_tasks', sa.Integer, default=3),
        sa.Column('timeout_seconds', sa.Integer, default=30),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Insert default sub-agent configs
    op.bulk_insert(
        sa.table('sub_agent_configs',
            sa.column('name', sa.String),
            sa.column('description', sa.Text),
            sa.column('enabled', sa.Boolean),
            sa.column('config_params', postgresql.JSONB),
            sa.column('max_concurrent_tasks', sa.Integer),
            sa.column('timeout_seconds', sa.Integer)
        ),
        [
            {'name': 'skills', 'description': 'Skills registry and execution', 'enabled': True, 'config_params': {}, 'max_concurrent_tasks': 3, 'timeout_seconds': 30},
            {'name': 'memory', 'description': 'Short-term and long-term memory', 'enabled': True, 'config_params': {}, 'max_concurrent_tasks': 5, 'timeout_seconds': 60},
            {'name': 'heartbeat', 'description': 'Health monitoring agent', 'enabled': True, 'config_params': {}, 'max_concurrent_tasks': 2, 'timeout_seconds': 10},
            {'name': 'soul', 'description': 'Ethical governance agent', 'enabled': True, 'config_params': {}, 'max_concurrent_tasks': 1, 'timeout_seconds': 30},
            {'name': 'tools', 'description': 'Tool registry and executor', 'enabled': True, 'config_params': {}, 'max_concurrent_tasks': 5, 'timeout_seconds': 45}
        ]
    )

def downgrade() -> None:
    op.drop_table('sub_agent_configs')
    op.drop_table('request_queue')
    op.drop_table('load_balancer_rules')
    op.drop_table('cache_registry')
    op.drop_table('background_tasks')
    op.drop_table('action_steps')
    op.drop_table('execution_plans')
    op.drop_table('mcp_servers')
