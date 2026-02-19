import os
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from config import Config
from models import Holding, Snapshot, SnapshotDetail, db
from services.price_service import (
    get_all_valuations,
    get_stock_price_sek,
    resolve_isin_to_ticker,
)
from services.snapshot_service import take_snapshot


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        os.makedirs(
            os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True
        )
        db.create_all()

    # --- Jinja filters ---
    @app.template_filter("sek")
    def format_sek(value):
        if value is None:
            return "N/A"
        sign = "-" if value < 0 else ""
        formatted = f"{abs(value):,.0f}".replace(",", " ")
        return f"{sign}{formatted} kr"

    # --- Scheduler: daily snapshot at 18:00 ---
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            scheduler = BackgroundScheduler()
            scheduler.add_job(
                func=lambda: _take_snapshot_in_context(app),
                trigger="cron",
                hour=18,
                minute=0,
                id="daily_snapshot",
            )
            scheduler.start()
        except Exception:
            pass  # Don't crash if scheduler fails

    # --- Routes ---
    @app.route("/")
    def dashboard():
        holdings = Holding.query.all()
        valuations = get_all_valuations(holdings)

        total = sum(v for _, v in valuations if v is not None)

        # Group by category for chart
        category_totals = {}
        category_labels = {
            "btc": "Bitcoin",
            "avanza": "Avanza",
            "bondora": "Bondora",
            "csn": "CSN Loans",
        }
        for h, val in valuations:
            cat = category_labels.get(h.category, h.category)
            if val is not None:
                category_totals[cat] = category_totals.get(cat, 0) + val

        return render_template(
            "dashboard.html",
            valuations=valuations,
            total=total,
            category_totals=category_totals,
        )

    @app.route("/add", methods=["GET", "POST"])
    def add_holding():
        if request.method == "POST":
            holding = _build_holding_from_form(request.form)
            if holding:
                db.session.add(holding)
                db.session.commit()
                flash(f"Added: {holding.label}")
                return redirect(url_for("dashboard"))
            else:
                flash("Please fill in all required fields.")

        return render_template("add_holding.html")

    @app.route("/edit/<int:holding_id>", methods=["GET", "POST"])
    def edit_holding(holding_id):
        holding = Holding.query.get_or_404(holding_id)

        if request.method == "POST":
            updated = _update_holding_from_form(holding, request.form)
            if updated:
                db.session.commit()
                flash(f"Updated: {holding.label}")
                return redirect(url_for("dashboard"))
            else:
                flash("Please fill in all required fields.")

        return render_template("edit_holding.html", holding=holding)

    @app.route("/delete/<int:holding_id>", methods=["POST"])
    def delete_holding(holding_id):
        holding = Holding.query.get_or_404(holding_id)
        label = holding.label
        db.session.delete(holding)
        db.session.commit()
        flash(f"Deleted: {label}")
        return redirect(url_for("dashboard"))

    @app.route("/history")
    def history():
        snapshots = Snapshot.query.order_by(Snapshot.date).all()
        dates = [s.date.isoformat() for s in snapshots]
        values = [s.total_sek for s in snapshots]
        return render_template("history.html", dates=dates, values=values)

    @app.route("/snapshot", methods=["POST"])
    def trigger_snapshot():
        snapshot = take_snapshot()
        flash(f"Snapshot taken: {snapshot.total_sek:,.0f} kr")
        return redirect(url_for("history"))

    return app


def _take_snapshot_in_context(app):
    with app.app_context():
        take_snapshot()


def _build_holding_from_form(form):
    """Create a new Holding from form data."""
    category = form.get("category")
    label = form.get("label", "").strip()
    if not category or not label:
        return None

    holding = Holding(category=category, label=label)
    return _set_category_fields(holding, form)


def _update_holding_from_form(holding, form):
    """Update an existing Holding from form data."""
    label = form.get("label", "").strip()
    if not label:
        return False

    holding.label = label
    # Category doesn't change on edit
    result = _set_category_fields(holding, form)
    return result is not None


def _set_category_fields(holding, form):
    """Set category-specific fields. Returns holding on success, None on error."""
    try:
        if holding.category == "btc":
            holding.btc_amount = float(form["btc_amount"])

        elif holding.category == "avanza":
            isin = form.get("isin", "").strip()
            shares_input = form.get("shares", "").strip()
            current_value = form.get("current_value_sek", "").strip()
            if not isin:
                return None

            holding.isin = isin

            # Resolve ISIN to Yahoo ticker
            try:
                if not holding.ticker:
                    holding.ticker = resolve_isin_to_ticker(isin)
            except Exception:
                holding.ticker = None

            if shares_input:
                # User provided shares directly (stocks/certificates)
                holding.shares = float(shares_input)
                holding.manual_value_sek = None
            elif current_value:
                # User provided total value (funds) — calculate shares
                if holding.ticker:
                    try:
                        nav_price = get_stock_price_sek(holding.ticker)
                        holding.shares = float(current_value) / nav_price
                        holding.manual_value_sek = None
                    except Exception:
                        holding.manual_value_sek = float(current_value)
                        holding.shares = None
                else:
                    holding.manual_value_sek = float(current_value)
                    holding.shares = None

        elif holding.category == "bondora":
            holding.principal_eur = float(form["principal_eur"])
            holding.interest_rate = float(form["interest_rate"]) / 100  # User enters %
            holding.start_date = datetime.strptime(
                form["start_date"], "%Y-%m-%d"
            ).date()

        elif holding.category == "csn":
            holding.balance_sek = float(form["balance_sek"])
            holding.csn_interest_rate = (
                float(form.get("csn_interest_rate", 0)) / 100
            )

        return holding
    except (KeyError, ValueError):
        return None


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
