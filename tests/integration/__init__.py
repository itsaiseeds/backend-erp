"""Integration tests.

These tests exercise the real, running Django server over HTTP against a
dedicated Postgres database built from ``sql/ddl.sql`` + ``sql/dml.sql``.
They are gated behind the ``integration`` pytest marker and are intended to
grow into Selenium browser tests later (Selenium also drives a live server).
"""
