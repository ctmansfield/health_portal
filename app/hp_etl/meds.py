from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta, timezone


@dataclass
class MedPlan:
    med_id: str
    name: str
    start: str  # ISOZ string
    end: Optional[str]
    interval_h: int
    window_min: int = 60


@dataclass
class MedEvent:
    med_id: str
    taken_at: str  # ISOZ string


@dataclass
class DoseExpectation:
    med_id: str
    due_at: str
    window_start: str
    window_end: str


@dataclass
class DoseScore:
    med_id: str
    due_at: str
    status: str  # on_time, late, missed
    taken_at: Optional[str]


def parse_isoz(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt


def isoformatz(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expand_schedule(plan: MedPlan) -> List[DoseExpectation]:
    start_dt = parse_isoz(plan.start)
    end_dt = parse_isoz(plan.end) if plan.end else (start_dt + timedelta(days=30))
    interval = timedelta(hours=plan.interval_h)
    window = timedelta(minutes=plan.window_min)

    doses = []
    current = start_dt
    while current <= end_dt:
        doses.append(
            DoseExpectation(
                med_id=plan.med_id,
                due_at=isoformatz(current),
                window_start=isoformatz(current - window),
                window_end=isoformatz(current + window),
            )
        )
        current += interval
    return doses


def score_adherence(
    expectations: List[DoseExpectation], events: List[MedEvent]
) -> List[DoseScore]:
    # Greedy 1:1 matching of events to expectations by due_at ascending
    sorted_exp = sorted(expectations, key=lambda d: d.due_at)
    sorted_ev = sorted(events, key=lambda e: e.taken_at)
    used_ev_indices = set()
    scores = []

    for dose in sorted_exp:
        # due_dt not used directly; keep for readability
        _due_dt = parse_isoz(dose.due_at)
        window_end_dt = parse_isoz(dose.window_end)
        matched_ev = None

        # find first event within window_start..window_end AND not used
        for i, ev in enumerate(sorted_ev):
            if i in used_ev_indices:
                continue
            ev_dt = parse_isoz(ev.taken_at)
            if ev.med_id != dose.med_id:
                continue
            if parse_isoz(dose.window_start) <= ev_dt <= window_end_dt:
                matched_ev = ev
                used_ev_indices.add(i)
                break
        if matched_ev:
            scores.append(
                DoseScore(dose.med_id, dose.due_at, "on_time", matched_ev.taken_at)
            )
            continue

        # find first event after window_end within +12h as 'late'
        late_deadline = window_end_dt + timedelta(hours=12)
        late_ev = None
        for i, ev in enumerate(sorted_ev):
            if i in used_ev_indices:
                continue
            ev_dt = parse_isoz(ev.taken_at)
            if ev.med_id != dose.med_id:
                continue
            if window_end_dt < ev_dt <= late_deadline:
                late_ev = ev
                used_ev_indices.add(i)
                break
        if late_ev:
            scores.append(DoseScore(dose.med_id, dose.due_at, "late", late_ev.taken_at))
        else:
            scores.append(DoseScore(dose.med_id, dose.due_at, "missed", None))

    return scores
