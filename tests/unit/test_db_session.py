"""
Test to ensure 100% coverage of app/db/session.py

This test specifically covers the production code path where
_worker_schema is None (non-xdist execution).
"""

import os

import pytest


@pytest.mark.asyncio
async def test_get_session_without_worker_schema():
    """Test get_session() in production mode (no xdist worker schema).

    This ensures the yield session line is covered when _worker_schema is None.
    We temporarily remove PYTEST_XDIST_WORKER to simulate production behavior.
    """
    # Save original environment
    original_worker = os.environ.get("PYTEST_XDIST_WORKER")

    try:
        # Remove xdist worker env var to simulate production
        if "PYTEST_XDIST_WORKER" in os.environ:
            del os.environ["PYTEST_XDIST_WORKER"]

        # Re-import to get fresh module state without xdist
        import importlib

        from app.db import session as session_module

        importlib.reload(session_module)

        # Now get_session should yield without setting search_path
        async for sess in session_module.get_session():
            # Verify we got a valid session
            assert sess is not None
            assert hasattr(sess, "execute")
            assert hasattr(sess, "commit")
            # Session should work normally
            from sqlalchemy import text

            result = await sess.execute(text("SELECT 1"))
            assert result.scalar() == 1
            break  # Only test first yield

    finally:
        # Restore original environment
        if original_worker:
            os.environ["PYTEST_XDIST_WORKER"] = original_worker
        # Reload again to restore xdist state
        import importlib

        from app.db import session as session_module

        importlib.reload(session_module)


@pytest.mark.asyncio
async def test_get_session_normal_operation():
    """Test that get_session works correctly in normal test context.

    This is a sanity check to ensure our coverage test doesn't break
    the normal operation.
    """
    from app.db.session import get_session

    async for session in get_session():
        assert session is not None
        # Verify session is usable
        from sqlalchemy import text

        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        break
