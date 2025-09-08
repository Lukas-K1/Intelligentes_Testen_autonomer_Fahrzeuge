from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import json
import threading
import uuid

class JsonEventLogger:
    """
    Logs boundary events (start/end) as JSON-friendly dicts and can compute spans.
    - timestamp: float seconds since epoch (time.time)
    - duration is computed from a monotonic clock (time.perf_counter)
    - arbitrary extra fields are accepted via **fields
    """

    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._open: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._clock = time.perf_counter
        self._wall = time.time

    def start(self,
              event_id: Optional[str] = None,
              *,
              display_name: Optional[str] = None,
              category: Optional[str] = None,
              actor: Optional[str] = None,
              layer: Optional[str] = None,
              **fields: Any) -> str:
        """Log the start of an event (returns the event_id)."""
        with self._lock:
            eid = event_id or str(uuid.uuid4())
            if eid in self._open:
                raise ValueError(f"Event already open: {eid}")
            start_perf = self._clock()
            start_wall = self._wall()
            base = {
                "timestamp": round(start_wall, 6),
                "event_id": eid,
                "display_name": display_name or eid,
                "category": category,
                "actor": actor,
                "layer": layer,
                "phase": "start",
            }
            # store open state for duration + cloning base fields
            self._open[eid] = {
                "start_perf": start_perf,
                "start_wall": start_wall,
                "base": {k: v for k, v in base.items() if v is not None},
                "start_fields": dict(fields) if fields else {}
            }
            # boundary event for start
            self._events.append({**{k: v for k, v in base.items() if v is not None}, **fields})
            return eid

    def end(self, event_id: str, **fields: Any) -> Dict[str, Any]:
        """Log the end of an event (and return the end event dict)."""
        with self._lock:
            if event_id not in self._open:
                raise KeyError(f"Event not open: {event_id}")
            state = self._open.pop(event_id)

            end_perf = self._clock()
            end_wall = self._wall()
            duration_s = end_perf - state["start_perf"]

            base_end = dict(state["base"])
            base_end.update({
                "timestamp": round(end_wall, 6),
                "phase": "end",
                "duration_s": round(duration_s, 6)
            })

            end_event = {**base_end, **fields}
            self._events.append(end_event)
            return end_event

    # Convenience context manager
    class _SpanContext:
        def __init__(self, logger: "EventLogger", event_id: Optional[str], kwargs: Dict[str, Any]):
            self._logger = logger
            self._eid = event_id
            self._kwargs = kwargs
            self.event_id: Optional[str] = None

        def __enter__(self) -> str:
            self.event_id = self._logger.start(self._eid, **self._kwargs)
            return self.event_id

        def __exit__(self, exc_type, exc, tb):
            extra = {}
            if exc_type is not None:
                extra["error"] = str(exc_type.__name__)
            self._logger.end(self.event_id, **extra)

    def span(self,
             event_id: Optional[str] = None,
             **kwargs: Any) -> "_SpanContext":
        """with logger.span('id', actor='Car1', distance_to_vut=2.5): ..."""
        return self._SpanContext(self, event_id, kwargs)

    # Export / accessors
    def events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def to_json(self, indent: Optional[int] = 2) -> str:
        with self._lock:
            return json.dumps(self._events, ensure_ascii=False, indent=indent)

    # Optional: build spans from boundary events (start/end pairs)
    def build_spans(self) -> List[Dict[str, Any]]:
        with self._lock:
            open_map: Dict[str, Dict[str, Any]] = {}
            spans: List[Dict[str, Any]] = []
            for ev in self._events:
                eid = ev.get("event_id")
                if not eid:
                    continue
                phase = ev.get("phase")
                if phase == "start" and eid not in open_map:
                    open_map[eid] = ev
                elif phase == "end" and eid in open_map:
                    s = open_map.pop(eid)
                    start_ts = s["timestamp"]
                    end_ts = ev["timestamp"]
                    span = {
                        "id": eid,
                        "event_id": eid,
                        "display_name": s.get("display_name", eid),
                        "actor": s.get("actor"),
                        "layer": s.get("layer"),
                        "category": s.get("category"),
                        "start": start_ts,
                        "end": end_ts,
                        "duration_s": round(end_ts - start_ts, 6),
                    }
                    spans.append(span)
            return spans

    def export_demo_format(self):
        layers = []
        seen = set()
        for e in self._events:
            layer = e.get("layer")
            if layer and layer not in seen:
                seen.add(layer)
                layers.append({"id": layer, "display_name": f"{layer.capitalize()} Events", "color": "#000000"})

        events_dict = {}
        for e in self._events:
            ev = dict(e)
            ev.pop("phase", None)
            ev.pop("duration_s", None)
            eid = ev["event_id"]
            events_dict.setdefault(eid, []).append(ev)

        for eid in events_dict:
            events_dict[eid].sort(key=lambda ev: float(ev["timestamp"]))

        all_events = []
        for evs in events_dict.values():
            all_events.extend(evs)

        all_events.sort(key=lambda ev: float(ev["timestamp"]))

        # Relativer Zeitstempel: minTimestamp abziehen
        min_ts = min(float(ev["timestamp"]) for ev in all_events)
        for ev in all_events:
            ev["timestamp"] = str(round(float(ev["timestamp"]) - min_ts, 3))

        return {"layers": layers, "events": all_events}


