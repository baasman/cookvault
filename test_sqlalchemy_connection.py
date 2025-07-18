#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy connection with psycopg3 to PostgreSQL
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Your PostgreSQL connection string with psycopg3
DATABASE_URL = "postgresql+psycopg://cookvault_admin:pXRJhZYhbCJ1pnL3Q5ZJ4qUaUryDcJRB@dpg-d1rfd6qli9vc73b5tmq0-a.oregon-postgres.render.com:5432/cookvault"

def test_sqlalchemy_connection():
    try:
        # Create engine with psycopg3 (default for SQLAlchemy 2.0+)
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "sslmode": "require"
            }
        )
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ SQLAlchemy connection successful!")
            print(f"PostgreSQL version: {version}")
            
            # Test a simple query
            result = connection.execute(text("SELECT current_database(), current_user"))
            db_info = result.fetchone()
            print(f"Database: {db_info[0]}")
            print(f"User: {db_info[1]}")
            
        # Test session maker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            result = session.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            print(f"✅ Session test successful: {test_value}")
        finally:
            session.close()
            
        print("✅ All SQLAlchemy tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_sqlalchemy_connection()
    exit(0 if success else 1)