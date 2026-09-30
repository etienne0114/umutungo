"""Create deterministic synthetic fleet history for local demonstrations only.

The generated records use real institution codes from the verified Rwanda
catalog, but every asset and work-order identifier is visibly prefixed DEMO.
The script is idempotent and refuses production or remote databases unless an
operator explicitly opts in.
"""

import argparse
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from govasset_api.database import make_engine  # noqa: E402
from govasset_api.models import (  # noqa: E402
    Asset,
    AssetUsageReading,
    Institution,
    MaintenanceRecord,
)


AS_OF = date(2026, 9, 30)
DEFAULT_INSTITUTION_CODES = (
    "MINALOC",
    "LODA",
    "MINIJUST",
    "RIB",
    "MOH",
    "RBC",
    "MININFRA",
    "RTDA",
    "MINAGRI",
    "RAB",
    "COK",
    "DIST-GASABO",
)
VEHICLES = (
    ("Toyota", "Land Cruiser", "SUV"),
    ("Toyota", "Hilux", "Pickup"),
    ("Toyota", "Hiace", "Minibus"),
    ("Nissan", "Patrol", "SUV"),
    ("Mitsubishi", "Canter", "Truck"),
    ("Isuzu", "D-Max", "Pickup"),
)
MAINTENANCE_CATEGORIES = (
    "scheduled_service",
    "oil_and_filter",
    "brake_system",
    "tyres",
    "suspension",
    "electrical_system",
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--institution-code",
        action="append",
        dest="institution_codes",
        help="Official institution code; repeat to add more. Defaults to curated parent/child pairs.",
    )
    parser.add_argument("--assets-per-institution", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm-synthetic",
        action="store_true",
        help="Required acknowledgement that generated records are not operational facts.",
    )
    return parser.parse_args()


def _guard_database(engine, confirmed: bool) -> None:
    if not confirmed:
        raise SystemExit(
            "Refusing to generate data without --confirm-synthetic. "
            "The output is demonstration data, not government operational data."
        )
    runtime = os.getenv("APP_ENV", "").strip().lower()
    if runtime in {"production", "prod"}:
        raise SystemExit("Synthetic data generation is disabled in production.")
    host = (engine.url.host or "").lower()
    local_hosts = {"", "localhost", "127.0.0.1", "::1"}
    if (
        engine.dialect.name == "postgresql"
        and host not in local_hosts
        and os.getenv("ALLOW_REMOTE_SYNTHETIC_DATA", "").lower() != "true"
    ):
        raise SystemExit(
            "Refusing a remote PostgreSQL database. Set ALLOW_REMOTE_SYNTHETIC_DATA=true "
            "only for an isolated non-production Supabase project."
        )


def _selected_institutions(
    session: Session,
    codes: tuple[str, ...],
) -> list[Institution]:
    institutions = list(
        session.scalars(
            select(Institution)
            .where(Institution.code.in_(codes), Institution.active.is_(True))
            .order_by(Institution.code)
        ).all()
    )
    found_codes = {institution.code for institution in institutions}
    missing = sorted(set(codes) - found_codes)
    if missing:
        raise SystemExit(
            "Institution catalog is missing these codes: "
            + ", ".join(missing)
            + ". Run the catalog migration/synchronization first."
        )
    return institutions


def _asset_code(institution_code: str, number: int) -> str:
    return f"DEMO-{institution_code}-{number:03d}"


def _create_asset(
    institution: Institution,
    institution_position: int,
    number: int,
) -> Asset:
    make, model, category = VEHICLES[(institution_position + number - 1) % len(VEHICLES)]
    acquired_year = 2018 + ((institution_position + number) % 7)
    acquisition_date = date(acquired_year, ((number * 2) % 12) + 1, 1)
    criticality = (
        "mission_critical"
        if institution.code in {"RIB", "RBC", "RTDA"} and number == 1
        else "important"
        if number == 1
        else "standard"
    )
    condition = "fair" if acquired_year <= 2020 else "good"
    return Asset(
        institution_id=institution.id,
        asset_code=_asset_code(institution.code, number),
        asset_type="vehicle",
        make=make,
        model=f"{model} ({category})",
        registration_number=f"DEMO-{institution.code[:4]}-{number:03d}",
        manufacture_year=acquired_year - 1,
        criticality=criticality,
        acquisition_date=acquisition_date,
        condition=condition,
        active=True,
    )


def _add_history(
    session: Session,
    asset: Asset,
    rng: random.Random,
    event_target: int,
) -> int:
    assert asset.acquisition_date is not None
    first_reading_date = asset.acquisition_date + timedelta(days=30)
    odometer = float(900 + rng.randint(0, 600))
    session.add(
        AssetUsageReading(
            asset_id=asset.id,
            recorded_on=first_reading_date,
            odometer_km=odometer,
            source="manual",
            notes="Synthetic baseline reading for demonstration only.",
        )
    )

    event_date = asset.acquisition_date + timedelta(days=150)
    event_count = 0
    last_event_date: date | None = None
    for sequence in range(1, event_target + 1):
        interval_days = rng.randint(85, 175)
        event_date += timedelta(days=interval_days)
        if event_date > AS_OF:
            break
        odometer += interval_days * rng.uniform(35, 95)
        planned = sequence % 4 != 0
        category = MAINTENANCE_CATEGORIES[
            (asset.id + sequence) % len(MAINTENANCE_CATEGORIES)
        ]
        downtime = rng.uniform(1.5, 6.0) if planned else rng.uniform(8.0, 30.0)
        cost = rng.randrange(75_000, 950_000, 25_000)
        session.add(
            MaintenanceRecord(
                asset_id=asset.id,
                event_date=event_date,
                category=category,
                description="Synthetic maintenance event for demonstration and testing.",
                planned=planned,
                downtime_hours=round(downtime, 1),
                odometer_km=round(odometer, 1),
                cost_amount=cost,
                currency="RWF",
                provider_name="DEMO service provider",
                work_order_reference=f"DEMO-WO-{asset.id}-{sequence:02d}",
            )
        )
        session.add(
            AssetUsageReading(
                asset_id=asset.id,
                recorded_on=event_date,
                odometer_km=round(odometer, 1),
                source="maintenance",
                notes=f"Synthetic reading captured with maintenance event {sequence}.",
            )
        )
        event_count += 1
        last_event_date = event_date

    if last_event_date is not None:
        asset.last_service_date = last_event_date
        asset.next_service_due = last_event_date + timedelta(days=120)
    return event_count


def generate_sample_data(
    session: Session,
    *,
    institution_codes: tuple[str, ...],
    assets_per_institution: int,
    seed: int,
) -> tuple[int, int, int]:
    institutions = _selected_institutions(session, institution_codes)
    rng = random.Random(seed)
    created_assets = 0
    created_events = 0
    skipped_assets = 0

    for institution_position, institution in enumerate(institutions):
        parent = (
            session.get(Institution, institution.parent_institution_id)
            if institution.parent_institution_id is not None
            else None
        )
        hierarchy_label = (
            f"{parent.code} > {institution.code}" if parent is not None else institution.code
        )
        print(f"Preparing synthetic fleet for {hierarchy_label}: {institution.name}")
        for number in range(1, assets_per_institution + 1):
            code = _asset_code(institution.code, number)
            exists = session.scalar(
                select(Asset.id).where(
                    Asset.institution_id == institution.id,
                    Asset.asset_code == code,
                )
            )
            if exists is not None:
                skipped_assets += 1
                continue
            asset = _create_asset(institution, institution_position, number)
            session.add(asset)
            session.flush()
            created_events += _add_history(
                session,
                asset,
                rng,
                event_target=4 + ((institution_position + number) % 4),
            )
            created_assets += 1

    return created_assets, created_events, skipped_assets


def main() -> None:
    args = _arguments()
    engine = make_engine()
    _guard_database(engine, args.confirm_synthetic)
    codes = tuple(args.institution_codes or DEFAULT_INSTITUTION_CODES)
    with Session(engine) as session:
        created_assets, created_events, skipped_assets = generate_sample_data(
            session,
            institution_codes=codes,
            assets_per_institution=args.assets_per_institution,
            seed=args.seed,
        )
        if args.dry_run:
            session.rollback()
        else:
            session.commit()

    mode = "Dry run" if args.dry_run else "Committed"
    print(
        f"{mode}: {created_assets} assets, {created_events} maintenance events, "
        f"{skipped_assets} existing assets skipped across {len(codes)} institutions."
    )


if __name__ == "__main__":
    main()
