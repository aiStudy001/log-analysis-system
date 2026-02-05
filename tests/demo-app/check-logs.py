#!/usr/bin/env python3
"""PostgreSQL 로그 확인 스크립트"""
import psycopg2
import json
from datetime import datetime

# PostgreSQL 연결
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="logs_db",
    user="postgres",
    password="password"
)

cur = conn.cursor()

print("=" * 80)
print("PostgreSQL 로그 확인 - demo-todo-backend")
print("=" * 80)

# 1. 전체 로그 개수
cur.execute("""
    SELECT COUNT(*) FROM logs WHERE service = 'demo-todo-backend'
""")
total = cur.fetchone()[0]
print(f"\n✅ 전체 로그 개수: {total}개")

# 2. 로그 레벨별 분포
cur.execute("""
    SELECT level, COUNT(*)
    FROM logs
    WHERE service = 'demo-todo-backend'
    GROUP BY level
    ORDER BY COUNT(*) DESC
""")
print("\n📊 로그 레벨별 분포:")
for level, count in cur.fetchall():
    print(f"  {level}: {count}개")

# 3. 최근 10개 로그
cur.execute("""
    SELECT
        created_at,
        level,
        message,
        function_name,
        file_path,
        metadata->>'path' as path,
        metadata->>'method' as method,
        metadata->>'user_id' as user_id,
        metadata->>'trace_id' as trace_id,
        metadata->>'duration_ms' as duration_ms
    FROM logs
    WHERE service = 'demo-todo-backend'
    ORDER BY created_at DESC
    LIMIT 10
""")
print("\n📋 최근 10개 로그:")
for row in cur.fetchall():
    created_at, level, message, func, file, path, method, user_id, trace_id, duration = row
    print(f"\n  [{level}] {message}")
    if func:
        print(f"    함수: {func}")
    if path:
        print(f"    HTTP: {method} {path}")
    if user_id:
        print(f"    사용자: {user_id}")
    if trace_id:
        print(f"    Trace: {trace_id[:16]}...")
    if duration:
        print(f"    소요시간: {duration}ms")

# 4. duration_ms가 있는 로그
cur.execute("""
    SELECT
        message,
        metadata->>'duration_ms' as duration_ms
    FROM logs
    WHERE service = 'demo-todo-backend'
      AND metadata->>'duration_ms' IS NOT NULL
    ORDER BY created_at DESC
""")
print("\n⏱️ 타이머 로그 (duration_ms):")
for message, duration in cur.fetchall():
    print(f"  {message}: {duration}ms")

# 5. 에러 로그 (stack_trace 포함)
cur.execute("""
    SELECT
        message,
        stack_trace
    FROM logs
    WHERE service = 'demo-todo-backend'
      AND level = 'ERROR'
      AND stack_trace IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 3
""")
print("\n❌ 에러 로그 (stack_trace 포함):")
errors = cur.fetchall()
if errors:
    for message, stack in errors:
        print(f"\n  메시지: {message}")
        if stack:
            stack_lines = stack.split('\n')[:3]
            for line in stack_lines:
                print(f"    {line}")
else:
    print("  에러 로그 없음")

# 6. HTTP 컨텍스트 확인
cur.execute("""
    SELECT DISTINCT
        metadata->>'path' as path,
        metadata->>'method' as method,
        COUNT(*) as count
    FROM logs
    WHERE service = 'demo-todo-backend'
      AND metadata->>'path' IS NOT NULL
    GROUP BY metadata->>'path', metadata->>'method'
    ORDER BY count DESC
""")
print("\n🌐 HTTP 엔드포인트별 로그:")
for path, method, count in cur.fetchall():
    print(f"  {method} {path}: {count}개")

# 7. 사용자 컨텍스트 확인
cur.execute("""
    SELECT DISTINCT
        metadata->>'user_id' as user_id,
        COUNT(*) as count
    FROM logs
    WHERE service = 'demo-todo-backend'
      AND metadata->>'user_id' IS NOT NULL
    GROUP BY metadata->>'user_id'
""")
print("\n👤 사용자별 로그:")
for user_id, count in cur.fetchall():
    print(f"  {user_id}: {count}개")

# 8. function_name, file_path 자동 수집 확인
cur.execute("""
    SELECT
        function_name,
        file_path,
        COUNT(*) as count
    FROM logs
    WHERE service = 'demo-todo-backend'
      AND function_name IS NOT NULL
      AND file_path IS NOT NULL
    GROUP BY function_name, file_path
    ORDER BY count DESC
    LIMIT 5
""")
print("\n🔍 자동 수집된 호출 위치 (상위 5개):")
for func, file, count in cur.fetchall():
    print(f"  {func} ({file}): {count}개")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("✅ 로그 확인 완료!")
print("=" * 80)
