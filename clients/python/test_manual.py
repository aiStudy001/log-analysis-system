import time
from log_collector import AsyncLogClient

# 로그 서버 실행 필요 (http://localhost:8000)
client = AsyncLogClient("http://localhost:8000", batch_size=10, flush_interval=1.0)

print("Sending 5 test logs...")
for i in range(5):
    client.log("INFO", f"Test log {i}", test_id="manual_test", iteration=i)

print("Logs queued! Waiting for flush...")
time.sleep(2)  # flush 대기

print("Flushing remaining logs...")
client.flush()

print("Done! Check server logs.")
print("\nTo verify in PostgreSQL:")
print("  psql -h localhost -p 5433 -U postgres -d logs_db")
print("  SELECT * FROM logs WHERE metadata->>'test_id' = 'manual_test';")
