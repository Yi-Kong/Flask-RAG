"""add email to user

Revision ID: 57570f3e4b7b
Revises: d284eaceb5cb
Create Date: 2026-06-29 18:42:43.951963

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57570f3e4b7b'
down_revision = 'd284eaceb5cb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=100), nullable=False))
        batch_op.create_unique_constraint(None, ['email'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('email')
