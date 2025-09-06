import json
from collections import defaultdict
from datetime import datetime


class EventLogger:
    def __init__(self):
        self.events = []
        self.active_events = {}

    def start_event(self, event_id, display_name, category, actor, layer, start):
        """
        Start logging an event and return its unique ID.

        :param event_id: Base ID for the event (e.g., "car1-accelerate")
        :param display_name: Display name without actor prefix (e.g., "Accelerate")
        :param category: Category (e.g., "sensor")
        :param actor: Actor (e.g., "Car1")
        :param layer: Layer (e.g., "selection")
        :param start: Start time in milliseconds
        :return: Unique ID for the event
        """
        unique_id = f"{event_id}-{int(start)}"
        formatted_display_name = f"{actor} – {display_name}"  # Add actor prefix
        self.active_events[unique_id] = {
            "id": unique_id,
            "event_id": event_id,
            "start": start,
            "display_name": formatted_display_name,
            "category": category,
            "actor": actor,
            "layer": layer,
        }
        return unique_id

    def end_event(self, unique_id, end):
        """
        End an active event using its unique ID.

        :param unique_id: Unique ID returned from start_event
        :param end: End time in milliseconds
        """
        if unique_id in self.active_events:
            event = self.active_events.pop(unique_id)
            event["end"] = end
            event["duration"] = end - event["start"]
            self.events.append(event)

    def _count_overlapping_pairs(self):
        """
        Count the number of overlapping event pairs.
        """
        if not self.events:
            return 0
        events_sorted = sorted(self.events, key=lambda e: e["start"])
        count = 0
        for i in range(len(events_sorted)):
            for j in range(i + 1, len(events_sorted)):
                if events_sorted[i]["end"] > events_sorted[j]["start"]:
                    count += 1
        return count

    def export_to_json(self, filename):
        """
        Export the logged events to a JSON file in the specified format.

        :param filename: Path to the output JSON file
        """
        if not self.events:
            print("No events to export.")
            return

        min_start = min(e["start"] for e in self.events)
        max_end = max(e["end"] for e in self.events)
        time_range = {"start": min_start - 1000, "end": max_end + 1000}
        total_events = len(self.events)
        export_time = datetime.utcnow().isoformat() + "Z"

        # Compute category breakdown
        category_breakdown = defaultdict(
            lambda: {"count": 0, "totalDuration": 0, "events": []}
        )
        total_sum_duration = 0
        for e in self.events:
            cat = e["category"]
            duration = e["duration"]
            category_breakdown[cat]["count"] += 1
            category_breakdown[cat]["totalDuration"] += duration
            category_breakdown[cat]["events"].append(e.copy())
            total_sum_duration += duration

        average_duration = total_sum_duration / total_events if total_events else 0
        overlapping_events = self._count_overlapping_pairs()

        metadata = {
            "exportTime": export_time,
            "totalEvents": total_events,
            "timeRange": time_range,
            "statistics": {
                "totalDuration": time_range["end"] - time_range["start"],
                "categoryBreakdown": dict(category_breakdown),
                "averageDuration": average_duration,
                "overlappingEvents": overlapping_events,
            },
        }

        # Scaled events for the main "events" list (times in seconds)
        scaled_events = [
            {
                "id": e["event_id"],  # Use event_id instead of unique id
                "name": e["display_name"],  # Already includes actor prefix
                "category": e["category"],
                "actor": e["actor"],
                "layer": e["layer"],
                "start": e["start"] / 1000,
                "end": e["end"] / 1000,
                "duration": e["duration"] / 1000,
            }
            for e in self.events
        ]

        data = {"metadata": metadata, "events": scaled_events}

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
