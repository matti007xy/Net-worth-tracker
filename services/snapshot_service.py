from datetime import date

from models import Holding, Snapshot, SnapshotDetail, db
from services.price_service import get_all_valuations


def take_snapshot():
    """Create or update a daily snapshot of net worth."""
    today = date.today()
    existing = Snapshot.query.filter_by(date=today).first()

    holdings = Holding.query.all()
    valuations = get_all_valuations(holdings)
    total = sum(v for _, v in valuations if v is not None)

    if existing:
        existing.total_sek = total
        SnapshotDetail.query.filter_by(snapshot_id=existing.id).delete()
        snapshot = existing
    else:
        snapshot = Snapshot(date=today, total_sek=total)
        db.session.add(snapshot)
        db.session.flush()

    for holding, val in valuations:
        detail = SnapshotDetail(
            snapshot_id=snapshot.id,
            holding_id=holding.id,
            category=holding.category,
            label=holding.label,
            value_sek=val if val is not None else 0.0,
        )
        db.session.add(detail)

    db.session.commit()
    return snapshot
