from datetime import datetime
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter

from sqlalchemy import func

from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine

from factoryos.modules.production.models import (
    TimeBooking,
    Order,
    QuantityReport,
    DowntimeReason
)


def get_time_report(args):

    order_q = args.get("order", "").strip()
    tool_q = args.get("tool", "").strip()
    article_q = args.get("article", "").strip()
    user_q = args.get("user", "").strip()
    machine_q = args.get("machine", "").strip()

    q = (
        TimeBooking.query
        .join(User, TimeBooking.user_id == User.id)
        .outerjoin(Order, TimeBooking.order_id == Order.id)
        .outerjoin(Machine, TimeBooking.machine_id == Machine.id)
    )

    if order_q:
        q = q.filter(Order.order_no.contains(order_q))

    if tool_q:
        q = q.filter(TimeBooking.tool_no.contains(tool_q))

    if article_q:
        q = q.filter(Order.article.contains(article_q))

    if user_q:
        q = q.filter(User.username.contains(user_q))

    if machine_q:
        q = q.filter(Machine.name.contains(machine_q))

    bookings = q.order_by(TimeBooking.start_time.desc()).limit(1000).all()

    totals = {
        "PROD": 0,
        "RUEST": 0,
        "ABRUEST": 0,
        "STOERUNG": 0,
        "WARTUNG": 0,
        "REPARATUR": 0,
        "SCHULUNG": 0,
        "PAUSE": 0,
        "FREI": 0
    }

    now = datetime.utcnow()

    for b in bookings:

        end_time = b.end_time if b.end_time else now
        seconds = int((end_time - b.start_time).total_seconds())

        key = b.process if b.process else b.type

        if key in totals:
            totals[key] += seconds

    return {
        "bookings": bookings,
        "totals": totals,
        "order_q": order_q,
        "tool_q": tool_q,
        "article_q": article_q,
        "user_q": user_q,
        "machine_q": machine_q,
        "now": now
    }