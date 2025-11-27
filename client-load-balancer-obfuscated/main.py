from collections import deque
from endpoints import EndpointServer
import random


class EndpointClient:
    def __init__(self, server: EndpointServer):
        self.endpoint_server: EndpointServer = server

        self.stats = {
            i: {
                "recent_success": deque(maxlen=20),
                "recent_latency": deque(maxlen=20),
                "successes": 0,
                "failures": 0,
                "consecutive_failures": 0,
            } for  i in (1, 2, 3)
        }

    def get_score(self, eid: int) -> float:
        s = self.stats[eid]

        if s["consecutive_failures"] >= 3:
            return 0.0

        if s["recent_success"]:
            sr = sum(s["recent_success"]) / len(s["recent_success"])
        else:
            sr = 1.0

        if s["recent_latency"]:
            avg_lat = sum(s["recent_latency"]) / len(s["recent_latency"])

            latency_score = max(0.0, min(1.0, (300 - avg_lat) / 300))
        else:
            latency_score = 1.0

        #returning moving av weighted
        return 0.4 * sr + 0.6 * latency_score
    def pick_best_endpoint(self) -> int:
        scores = {eid: self.get_score(eid) for eid in (1, 2, 3)}
        best = max(scores, key=scores.get)

        if scores[best] < 0.2:
            return random.choice([1, 2, 3])

        return best
    def update_stats(self, eid: int, success: bool, latency: float):
        s = self.stats[eid]

        s["recent_success"].append(1 if success else 0)
        s["recent_latency"].append(latency)

        if success:
            s["successes"] += 1
            s["consecutive_failures"] = 0
        else:
            s["consecutive_failures"] += 1
            s["failures"] += 1

    def call(self, runs: int) -> None:
        """Placeholder call implementation.
        Replace this with an efficient strategy.
        """
        for i in range(runs):
            eid = self.pick_best_endpoint()
            success, latency_ms = self.endpoint_server.call(eid)
            self.update_stats(eid, success, latency_ms)


if __name__ == "__main__":
    server = EndpointServer(test_case=1)
    client = EndpointClient(server=server)
    client.call(1_000)
    server.print_summary()
