import time

import pytest

from hr_management_app.src.database.database import (
    create_user,
    delete_user_with_admin_check,
    get_admin_user,
    get_user_by_id,
    update_user_role,
)


def test_update_user_role_admin_conflict():
    # create an admin and another user, then assert promoting the second to admin fails
    # use existing admin if present, otherwise create one
    admin = get_admin_user()
    if admin:
        _admin_id = admin[0]
    else:
        a_email = f"admin_test_{int(time.time())}@example.com"
        _admin_id = create_user(a_email, "p", role="admin")
    u_email = f"user_test_{int(time.time())}@example.com"
    user_id = create_user(u_email, "p", role="engineer")

    with pytest.raises(PermissionError):
        update_user_role(user_id, "admin")


def test_delete_admin_requires_transfer_and_transfers_role():
    # create three users: admin, target, other
    # use existing admin if present, otherwise create one
    admin = get_admin_user()
    if admin:
        admin_id = admin[0]
    else:
        a_email = f"admin_del_{int(time.time())}@example.com"
        admin_id = create_user(a_email, "p", role="admin")
    t_email = f"target_{int(time.time())}@example.com"
    target_id = create_user(t_email, "p", role="engineer")
    o_email = f"other_{int(time.time())}@example.com"
    _other_id = create_user(o_email, "p", role="engineer")

    # attempt to delete admin without transfer -> should raise
    with pytest.raises(PermissionError):
        delete_user_with_admin_check(admin_id)

    # now delete admin with transfer to target
    ok = delete_user_with_admin_check(admin_id, transfer_to_user_id=target_id)
    assert ok is True

    # target should now be admin
    tgt = get_user_by_id(target_id)
    assert tgt and tgt[-1] == "admin"
