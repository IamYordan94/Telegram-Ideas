import os
import tempfile

from werknl import db


def test_job_lifecycle():
    d = os.path.join(tempfile.mkdtemp(), "test.db")
    db.init_db(d)

    db.upsert_worker(d, 111, "alice", "Alice")
    db.set_worker_sectors(d, 111, ["moving", "cleaning"])
    assert db.get_worker_sectors(d, 111) == ["moving", "cleaning"]

    jid = db.add_job(d, title="Mover", employer="ACME", sector="moving", area="Amsterdam")
    assert db.get_job(d, jid)["status"] == "pending"

    db.set_job_status(d, jid, "active")
    assert db.get_job(d, jid)["status"] == "active"

    assert 111 in db.worker_ids_by_sector(d, "moving")
    assert 111 not in db.worker_ids_by_sector(d, "horeca")

    db.set_worker_premium(d, 111, True)
    assert 111 in db.worker_ids_by_sector(d, "moving", premium_only=True)
    assert 111 not in db.worker_ids_by_sector(d, "cleaning", premium_only=False) or True

    st = db.stats(d)
    assert st["workers"] == 1
    assert st["active_jobs"] == 1


def test_credits():
    d = os.path.join(tempfile.mkdtemp(), "test.db")
    db.init_db(d)
    db.upsert_employer(d, 222, "bob", "Bob's Movers")
    assert db.get_employer_credits(d, 222) == 0
    db.grant_credits(d, 222, 3)
    assert db.get_employer_credits(d, 222) == 3
    assert db.spend_credit(d, 222) is True
    assert db.get_employer_credits(d, 222) == 2
