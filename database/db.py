"""
MySQL connection helper.
Uses PyMySQL with DictCursor so query results come back as dictionaries.
A new connection is opened per request and closed automatically by Flask's
teardown hook (registered in app.py) to avoid leaking connections.
"""
import pymysql
import pymysql.cursors
from flask import g, current_app


def get_db():
    """Return a request-scoped MySQL connection."""
    if "db" not in g:
        cfg = current_app.config
        g.db = pymysql.connect(
            host=cfg["MYSQL_HOST"],
            port=cfg["MYSQL_PORT"],
            user=cfg["MYSQL_USER"],
            password=cfg["MYSQL_PASSWORD"],
            database=cfg["MYSQL_DATABASE"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql, params=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def query_one(sql, params=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE. Commits and returns lastrowid + affected rowcount."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        db.commit()
        return {"lastrowid": cur.lastrowid, "rowcount": cur.rowcount}


def execute_many(sql, seq_of_params):
    db = get_db()
    with db.cursor() as cur:
        cur.executemany(sql, seq_of_params)
        db.commit()
        return cur.rowcount


def init_app(app):
    app.teardown_appcontext(close_db)
