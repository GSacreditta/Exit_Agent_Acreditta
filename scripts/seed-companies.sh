#!/usr/bin/env bash
# Seeds the `companies` table from config/watchlist.yaml.
# Runs Python locally — needs DATABASE_URL or Cloud SQL Proxy.

set -euo pipefail
cd "$(dirname "$0")/.."

python -c "
import yaml
from shared.db import get_session, Company
from sqlalchemy import select

with open('config/watchlist.yaml') as f:
    wl = yaml.safe_load(f)

with get_session() as s:
    for tier_key, tier_num in (('tier_1_buyers', 1), ('tier_2_latam_edtech', 2)):
        for c in wl[tier_key]:
            existing = s.execute(select(Company).where(Company.name == c['name'])).scalar_one_or_none()
            if existing:
                existing.tier = tier_num
                existing.aliases = c.get('aliases', [])
            else:
                s.add(Company(name=c['name'], tier=tier_num, aliases=c.get('aliases', [])))
            print(f'  ✓ tier {tier_num}: {c[\"name\"]}')

print('done.')
"
