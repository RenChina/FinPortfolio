"""Add Deposit model

Revision ID: 3219da96d1f9
Revises: 8f3f5b1289ac
Create Date: 2024-05-25 16:31:33.043450

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3219da96d1f9'
down_revision = '8f3f5b1289ac'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('deposit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('interest_rate', sa.Float(), nullable=False),
    sa.Column('duration_months', sa.Integer(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('deposit')
    # ### end Alembic commands ###
