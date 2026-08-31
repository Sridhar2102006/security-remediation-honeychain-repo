import os
from pathlib import Path

import psycopg


def apply_migrations():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL must be set before running migrations.')

    migrations_dir = Path(__file__).resolve().parents[1] / 'migrations'
    for migration in sorted(migrations_dir.glob('*.sql')):
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(migration.read_text(encoding='utf-8'))
    return True


if __name__ == '__main__':
    apply_migrations()
    print('Applied HoneyChain migrations.')
