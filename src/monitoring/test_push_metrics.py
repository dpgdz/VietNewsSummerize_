from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

registry = CollectorRegistry()

g = Gauge('unit_test_metric', 'Test metric from unit test', registry=registry)
g.set(123.45)

push_to_gateway('localhost:9091', job='unit_test', registry=registry)

print("Metric pushed successfully.")
