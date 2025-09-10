#!/usr/bin/env python3
"""Create a user in analytics.users with a hashed password.
Usage: scripts/create_user.py --username alice --email a@b.com --role clinician
"""
import argparse, getpass
from passlib.context import CryptContext
from app.hp_etl.db import pg

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ap = argparse.ArgumentParser()
ap.add_argument("--username", required=True)
ap.add_argument("--email", default=None)
ap.add_argument("--full-name", default=None)
ap.add_argument("--role", default=None)
args = ap.parse_args()

pw = getpass.getpass("Password: ")
hash = pwd_context.hash(pw)

with pg() as conn:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO analytics.users(username,email,full_name,password_hash) VALUES (%s,%s,%s,%s) RETURNING id",
        (args.username, args.email, args.full_name, hash),
    )
    user_id = cur.fetchone()[0]
    if args.role:
        # ensure role exists
        cur.execute(
            "INSERT INTO analytics.roles(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (args.role,),
        )
        cur.execute("SELECT id FROM analytics.roles WHERE name=%s", (args.role,))
        role_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO analytics.user_roles(user_id,role_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (user_id, role_id),
        )
    conn.commit()
print("Created user", args.username)
