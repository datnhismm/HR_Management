import sys
import os
import time
import pytest

# ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import (
    create_user,
    get_user_by_id,
    update_user_role,
    can_grant_role,
    _conn,
)


def test_can_grant_role_logic():
    # admin can grant high_manager, manager can grant engineer/accountant but not high_manager/admin
    assert can_grant_role("admin", "high_manager") is True
    assert can_grant_role("manager", "engineer") is True
    assert can_grant_role("manager", "high_manager") is False
    assert can_grant_role("engineer", "accountant") is False


def test_role_audit_records_actor():
    # create an actor (manager) and a target user, then update target role and assert audit recorded
    a_email = f"actor_{int(time.time())}@example.com"
    actor_id = create_user(a_email, "p", role="manager")
    t_email = f"target_{int(time.time())}@example.com"
    target_id = create_user(t_email, "p", role="engineer")

    # manager grants 'accountant' role (allowed)
    update_user_role(target_id, "accountant", actor_user_id=actor_id)

    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT changed_user_id, old_role, new_role, actor_user_id FROM role_audit WHERE changed_user_id = ? ORDER BY id DESC LIMIT 1",
            (target_id,),
        )
        row = c.fetchone()
    assert row is not None, "No role_audit row found"
    changed_user_id, old_role, new_role, actor_user_id = row
    assert changed_user_id == target_id
    assert new_role == "accountant"
    assert actor_user_id == actor_id
