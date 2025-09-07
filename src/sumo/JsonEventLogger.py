import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional


class JsonEventLogger:

    def __init__(self):
        self._open_events: Dict[str, Dict[str, Any]] = {}
        self._finished_events: List[Dict[str, Any]] = []
        self._category_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        self._min_start_ms: Optional[int] = None
        self._max_end_ms: Optional[int] = None
        self._total_duration_ms: int = 0

        self._used_ids: set[str] = set()

    def _derive_event_id(self, full_id: str) -> str:
        if "-" in full_id:
            maybe_base, maybe_suffix = full_id.rsplit("-", 1)
            if maybe_suffix.isdigit():
                return maybe_base
        return full_id

    def start_event(
        self,
        event_id: str,
        category: str,
        name: str,
        actor: str,
        layer: str,
        start_time_s: float,
    ):
        if event_id in self._open_events:
            print(
                f"[JsonEventLogger] Warning: event '{event_id}' already open, overwriting."
            )

        self._open_events[event_id] = {
            "id": event_id,
            "event_id": self._derive_event_id(event_id),
            "name": name,
            "display_name": name,
            "category": category,
            "actor": actor,
            "layer": layer,
            "start": start_time_s,
        }

    def end_event(self, event_id: str, end_time_s: float):
        ev = self._open_events.pop(event_id, None)
        if ev is None:
            print(f"[JsonEventLogger] Warning: end_event for unknown '{event_id}'.")
            return

        start_s = ev["start"]
        start_ms = int(round(start_s * 1000))
        end_ms = int(round(end_time_s * 1000))
        dur_ms = max(0, end_ms - start_ms)

        base = ev["event_id"]
        occ_id = f"{base}-{start_ms}"
        cnt = 1
        while occ_id in self._used_ids:
            cnt += 1
            occ_id = f"{base}-{start_ms}-{cnt}"
        self._used_ids.add(occ_id)

        cat_entry = {
            "id": occ_id,
            "event_id": base,
            "start": start_ms,
            "end": end_ms,
            "duration": dur_ms,
            "display_name": ev["name"],
            "category": ev["category"],
            "actor": ev["actor"],
            "layer": ev["layer"],
        }
        self._category_events[ev["category"]].append(cat_entry)

        top_event = {
            "id": occ_id,
            "event_id": base,
            "name": ev["name"],
            "category": ev["category"],
            "actor": ev["actor"],
            "layer": ev["layer"],
            "start": start_s,
            "end": end_time_s,
            "duration": end_time_s - start_s,
        }
        self._finished_events.append(top_event)

        self._min_start_ms = (
            start_ms
            if self._min_start_ms is None
            else min(self._min_start_ms, start_ms)
        )
        self._max_end_ms = (
            end_ms if self._max_end_ms is None else max(self._max_end_ms, end_ms)
        )
        self._total_duration_ms += dur_ms

    def export_json(self, filename: str):
        category_breakdown = {}
        for cat, entries in self._category_events.items():
            total_dur = sum(e["duration"] for e in entries)
            category_breakdown[cat] = {
                "count": len(entries),
                "totalDuration": total_dur,
                "events": entries,
            }

        metadata = {
            "exportTime": datetime.utcnow().isoformat() + "Z",
            "totalEvents": len(self._finished_events),
            "timeRange": {
                "start": self._min_start_ms or 0,
                "end": self._max_end_ms or 0,
            },
            "statistics": {
                "totalDuration": self._total_duration_ms,
                "categoryBreakdown": category_breakdown,
                "averageDuration": (
                    (self._total_duration_ms / len(self._finished_events))
                    if self._finished_events
                    else 0
                ),
                "overlappingEvents": 0,
            },
        }

        out = {"metadata": metadata, "events": self._finished_events}

        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)

        print(
            f"[JsonEventLogger] Exported {len(self._finished_events)} events → {filename}"
        )
