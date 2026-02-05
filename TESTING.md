# Log Analysis System - Integration Test Guide

## 📋 Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Check service health
curl http://localhost:8001/health  # Backend
curl http://localhost:3000         # Frontend
curl http://localhost:8000/docs    # Log-save server

# 3. Verify database
docker exec -it log-analysis-postgres psql -U loguser -d logdb -c "SELECT COUNT(*) FROM logs;"

# 4. Generate test data
python scripts/generate_test_logs.py --scenario all

# 5. Open frontend
open http://localhost:3000
```

---

## 🧪 Feature #1: Query Result Cache

### Test 1.1: Cache Miss → Cache Hit

**Purpose**: Verify caching mechanism improves query performance

**Steps**:
1. Open frontend at http://localhost:3000
2. Enter question: `최근 1시간 에러 로그`
3. Observe first execution:
   - Response time: ~4-5 seconds
   - Watch WebSocket events in browser DevTools
   - Verify `complete` event has `cache_hit: false`
4. Enter SAME question again immediately
5. Observe second execution:
   - Response time: <100ms (instant)
   - Verify `complete` event has `cache_hit: true`
6. Check UI for cache indicator (⚡ badge)

**Expected Results**:
- ✅ First query: cache_hit=false, normal execution
- ✅ Second query: cache_hit=true, <100ms response
- ✅ Cache hit badge visible in UI
- ✅ No re-execution of SQL or Claude API calls

**Verification Commands**:
```bash
# Monitor backend logs during test
docker-compose logs -f log-analysis-server | grep -i cache

# Check if cache service is working (look for "Cache HIT" vs "Cache MISS" logs)
```

---

### Test 1.2: Cache Invalidation

**Purpose**: Ensure cache clears when new data inserted

**Steps**:
1. Execute a query: `최근 payment-api 에러`
2. Verify it gets cached (second execution is instant)
3. Insert new logs via API:
   ```bash
   curl -X POST http://localhost:8000/logs \
     -H "Content-Type: application/json" \
     -d '{"logs":[{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S)'","level":"ERROR","service":"payment-api","message":"Cache invalidation test"}]}'
   ```
4. Call cache invalidation endpoint:
   ```bash
   curl -X POST http://localhost:8001/invalidate_cache
   ```
5. Execute the same query again
6. Verify cache_hit=false (cache was cleared)

**Expected Results**:
- ✅ After invalidation, query re-executes fully
- ✅ New logs are included in results
- ✅ Response time returns to normal (~4-5s)

---

### Test 1.3: TTL Expiration

**Purpose**: Verify automatic cache expiration after TTL period

**Steps**:
1. Check current TTL setting:
   ```bash
   docker exec log-analysis-server grep CACHE_TTL .env
   # Default: CACHE_TTL_SECONDS=300 (5 minutes)
   ```
2. Execute a query and let it cache
3. **Option A**: Wait 5+ minutes
4. **Option B**: Reduce TTL for faster testing:
   ```bash
   # Edit .env to set CACHE_TTL_SECONDS=60
   # Restart: docker-compose restart log-analysis-server
   # Wait 1+ minute
   ```
5. Execute same query again
6. Verify cache_hit=false (TTL expired)

**Expected Results**:
- ✅ After TTL expires, cache automatically invalidates
- ✅ Query re-executes without manual intervention

---

## 🧠 Feature #2: Context-Aware Agent

### Test 2.1: Focus Tracking

**Purpose**: Verify focus entity extraction and UI display

**Steps**:
1. Ask: `최근 payment-api 에러는?`
2. Watch for `context_resolved` WebSocket event
3. Check event data:
   ```json
   {
     "type": "context_resolved",
     "node": "resolve_context",
     "data": {
       "resolution_needed": false,
       "original_question": "최근 payment-api 에러는?",
       "focus": {
         "service": "payment-api"
       }
     }
   }
   ```
4. Verify ConversationContext component appears
5. Check focus badge shows: "Service: payment-api"

**Expected Results**:
- ✅ Focus extracted from SQL query
- ✅ ConversationContext component visible
- ✅ Service badge displayed correctly

---

### Test 2.2: Reference Resolution

**Purpose**: Verify pronoun/reference resolution using Claude

**Steps**:
1. **Turn 1**: Ask `최근 payment-api 에러는?`
   - Verify focus set: `{service: "payment-api"}`

2. **Turn 2**: Ask `그 서비스의 느린 API는?` (contains reference "그 서비스")

3. Observe `context_resolved` event:
   ```json
   {
     "type": "context_resolved",
     "data": {
       "resolution_needed": true,
       "original_question": "그 서비스의 느린 API는?",
       "resolved_question": "payment-api 서비스의 느린 API는?",
       "focus": {
         "service": "payment-api"
       }
     }
   }
   ```

4. Check generated SQL includes:
   ```sql
   WHERE service = 'payment-api'
   ```

**Expected Results**:
- ✅ Reference "그 서비스" correctly resolved to "payment-api"
- ✅ Resolved question displayed (if UI shows it)
- ✅ SQL query includes correct service filter
- ✅ Context-aware status message in UI

---

### Test 2.3: Conversation History & Context Propagation

**Purpose**: Verify multi-turn context memory

**Steps**:
1. **Turn 1**: `DatabaseConnectionError 에러 보여줘`
   - Check focus: `{error_type: "DatabaseConnectionError"}`

2. **Turn 2**: `그 에러가 언제부터 시작됐어?`
   - Verify resolved includes error_type
   - SQL should have: `WHERE error_type = 'DatabaseConnectionError'`

3. **Turn 3**: `그 에러의 개수는?`
   - Context should still maintain error_type
   - SQL aggregation on DatabaseConnectionError

**Expected Results**:
- ✅ Error type context maintained across 3 turns
- ✅ Each follow-up query correctly references previous focus
- ✅ No need to repeat "DatabaseConnectionError" in questions

---

### Test 2.4: New Conversation Reset

**Purpose**: Verify conversation reset clears all context

**Steps**:
1. Execute 3-4 queries to build comprehensive focus:
   - "payment-api 에러"
   - "DatabaseConnectionError 타입"
   - "최근 1시간"
2. Verify ConversationContext shows multiple badges
3. Click **"새로운 대화 시작"** button
4. Verify:
   - ConversationContext component disappears or shows empty
   - conversation_id changes (check in browser DevTools)
   - chatStore.currentFocus = {} (empty)
5. Ask a new question - should have no previous context

**Expected Results**:
- ✅ All focus badges removed
- ✅ Fresh conversation_id generated
- ✅ No context from previous session
- ✅ Clean slate for new conversation

---

## 🔀 Feature #3: Multi-Step Reasoning

### Test 3.1: Simple Query → Single Step

**Purpose**: Verify simple queries bypass multi-step decomposition

**Steps**:
1. Ask simple question: `최근 1시간 에러 로그`
2. Watch for `plan_generated` event:
   ```json
   {
     "type": "plan_generated",
     "data": {
       "step_count": 1,
       "is_multi_step": false
     }
   }
   ```
3. Verify MultiStepProgress component does NOT appear
4. Query executes via standard workflow:
   - generate_sql → validate_sql → execute_query → generate_insight

**Expected Results**:
- ✅ No decomposition for simple queries
- ✅ Original 5-node workflow used
- ✅ Faster execution (no planning overhead)

---

### Test 3.2: Complex Query → Multi-Step Decomposition

**Purpose**: Verify complex analytical questions decompose into steps

**Steps**:
1. Ask complex question: `결제 실패율이 왜 높아졌어?`

2. Watch for `plan_generated` event:
   ```json
   {
     "type": "plan_generated",
     "data": {
       "step_count": 4,
       "is_multi_step": true,
       "steps": [
         {"index": 0, "description": "Calculate current payment failure rate"},
         {"index": 1, "description": "Compare with historical baseline"},
         {"index": 2, "description": "Identify concurrent errors"},
         {"index": 3, "description": "Analyze affected user patterns"}
       ],
       "synthesis": "Compare rates and identify root cause"
     }
   }
   ```

3. Verify MultiStepProgress component displays

4. Observe sequential `step_completed` events:
   ```json
   {
     "type": "step_completed",
     "data": {
       "step_index": 0,
       "step_count": 4,
       "description": "Calculate current payment failure rate",
       "question": "최근 1시간 payment 관련 에러 개수와 전체 payment 로그 개수",
       "sql": "SELECT ...",
       "result_count": 25,
       "execution_time_ms": 156
     }
   }
   ```

5. Watch each step execute in sequence (0 → 1 → 2 → 3)

6. Final `all_steps_complete` event:
   ```json
   {
     "type": "all_steps_complete",
     "data": {
       "total_steps": 4
     }
   }
   ```

7. Final insight combines all step results

**Expected Results**:
- ✅ Question decomposes into 3-5 logical steps
- ✅ Each step has clear description and purpose
- ✅ Steps execute sequentially (not parallel)
- ✅ Each step's results inform next step
- ✅ Final insight synthesizes all findings

**Example Final Insight**:
```
"분석 결과, 결제 실패율이 20%에서 45%로 급증했습니다 (2배 이상 증가).
주요 원인은 DatabaseConnectionError로, 최근 1시간 동안 집중적으로 발생했습니다.
영향받은 사용자는 주로 user_1~user_20 범위이며, /api/v1/checkout 엔드포인트에서 발생합니다.
즉시 데이터베이스 연결 풀 설정을 확인하고 connection timeout을 조정하세요."
```

---

### Test 3.3: Step Progress Visualization

**Purpose**: Verify real-time UI updates during multi-step execution

**Steps**:
1. Execute complex query (triggers multi-step)
2. Observe MultiStepProgress component in real-time:

**Initial State** (after plan_generated):
```
Step 1: [⏳ pending] Calculate current failure rate
Step 2: [⏳ pending] Compare with baseline
Step 3: [⏳ pending] Identify concurrent errors
Step 4: [⏳ pending] Analyze user patterns

Progress: [▓░░░░░░░░░] 0%
```

**During Execution** (step 0 active):
```
Step 1: [🔄 active] Calculate current failure rate
Step 2: [⏳ pending] Compare with baseline
...

Progress: [▓▓▓░░░░░░░] 25%
```

**After Step 1 Completes**:
```
Step 1: [✅ completed] Calculate current failure rate
        SQL: SELECT COUNT(*) ...
        25 rows, 156ms
Step 2: [🔄 active] Compare with baseline
...

Progress: [▓▓▓▓▓░░░░░] 50%
```

3. Check UI elements:
   - Step cards have correct border colors (gray → blue → green)
   - Status icons update (⏳ → 🔄 → ✅)
   - SQL code expandable in completed steps
   - Result count and execution time displayed
   - Progress bar animates smoothly

**Expected Results**:
- ✅ Real-time status updates for each step
- ✅ Clear visual differentiation (pending/active/completed)
- ✅ Progress bar reflects completion percentage
- ✅ Detailed metrics per step
- ✅ Smooth animations and transitions

---

### Test 3.4: Step Failure Handling

**Purpose**: Verify graceful error handling in multi-step workflow

**Steps**:
1. Ask intentionally problematic question that will fail mid-execution:
   - Example: `존재하지_않는_컬럼으로 필터링해서 결제 분석해줘`
   - This should cause SQL validation or execution error in one of the steps

2. Observe step execution until failure occurs

3. Watch for `step_failed` event:
   ```json
   {
     "type": "step_failed",
     "node": "execute_step",
     "status": "failed",
     "data": {
       "step_index": 1,
       "step_count": 3,
       "description": "Filter by invalid column",
       "error": "column \"존재하지_않는_컬럼\" does not exist"
     }
   }
   ```

4. Check UI behavior:
   - Failed step: red border + ❌ icon
   - Error message displayed clearly
   - Subsequent steps remain pending (NOT executed)
   - Overall error message shown to user

**Expected Results**:
- ✅ Step failure stops execution immediately
- ✅ Error clearly indicated in UI (red styling)
- ✅ Error message visible and understandable
- ✅ No execution of remaining steps
- ✅ User can retry with corrected question

---

## ⚙️ Feature #4: Query Planning & Optimization

### Test 4.1: Complexity Classification

**Purpose**: Verify accurate query complexity analysis

**Test Cases**:

**Case A - Simple Query**:
```
Question: "최근 에러 로그"
Expected: complexity=simple
```

**Case B - Moderate Query**:
```
Question: "서비스별 에러 통계"
Expected: complexity=moderate
Reason: GROUP BY aggregation
```

**Case C - Complex Query**:
```
Question: "왜 에러율이 높아졌어?"
Expected: complexity=complex
Reason: Root cause analysis keyword ("왜")
```

**Steps**:
1. Execute each test case
2. Watch for `optimization_complete` event:
   ```json
   {
     "type": "optimization_complete",
     "node": "optimize_query",
     "data": {
       "complexity": "simple",
       "strategy": "single_query",
       "indexes": ["idx_service_level_time"]
     }
   }
   ```
3. Verify complexity matches expected

**Expected Results**:
- ✅ Simple queries: complexity=simple
- ✅ Aggregation queries: complexity=moderate
- ✅ Analytical queries: complexity=complex
- ✅ optimization_complete event emitted

---

### Test 4.2: Optimization Strategy Selection

**Purpose**: Verify appropriate strategy for each complexity level

**Test Matrix**:

| Query | Complexity | Expected Strategy | Workflow |
|-------|-----------|------------------|----------|
| "최근 에러" | simple | single_query | Standard SQL path |
| "서비스별 통계" | moderate | single_query | Standard SQL path |
| "왜 실패율이 높아?" | complex | use_multi_step | Multi-step path |

**Steps**:
1. Execute each query type
2. Verify strategy in `optimization_complete` event
3. Confirm workflow routing:
   - single_query → generate_sql node
   - use_multi_step → execute_step node

**Expected Results**:
- ✅ Correct strategy for each complexity
- ✅ Complex queries routed to multi-step
- ✅ Simple queries use efficient single-step path

---

### Test 4.3: Index Suggestions

**Purpose**: Verify relevant index recommendations based on query patterns

**Test Cases**:

**Case A - Service Filter**:
```
Question: "service별 에러 분포"
Expected indexes: ["idx_service_level_time"]
```

**Case B - User Filter**:
```
Question: "user별 에러 패턴"
Expected indexes: ["idx_user_time"]
```

**Case C - Error Type Filter**:
```
Question: "error_type별 통계"
Expected indexes: ["idx_error_time"]
```

**Steps**:
1. Execute each query
2. Check `optimization_complete` event data.indexes
3. Verify suggested indexes are relevant to query filters

**Expected Results**:
- ✅ Correct index suggestions based on WHERE clauses
- ✅ Suggestions appear in event data
- ✅ (Optional) UI displays optimization hints

---

## 🚨 Feature #5: Alerting & Monitoring

### Test 5.1: Manual Anomaly Check API

**Purpose**: Verify on-demand anomaly detection endpoint

**Steps**:
```bash
# Trigger manual check
curl -X POST http://localhost:8001/alerts/check

# Expected response
{
  "alerts": [],
  "count": 0
}
# Or if anomalies exist:
{
  "alerts": [
    {
      "type": "error_rate_spike",
      "severity": "warning",
      "message": "에러율 25.0% 증가 감지 (최근 5분)",
      "data": {
        "current_count": 50,
        "baseline_count": 40,
        "spike_percentage": 25.0
      }
    }
  ],
  "count": 1
}
```

**Expected Results**:
- ✅ Endpoint returns current anomaly status
- ✅ Response includes all 3 check types (error_rate, slow_api, service_down)
- ✅ Returns empty array if no anomalies

---

### Test 5.2: Alert History API

**Purpose**: Verify alert history retrieval

**Steps**:
```bash
# Get recent alerts
curl http://localhost:8001/alerts/history?limit=20

# Expected response
{
  "alerts": [
    {
      "type": "error_rate_spike",
      "severity": "critical",
      "message": "에러율 50.0% 증가 감지",
      "data": {...},
      "timestamp": "2026-02-05T10:30:00"
    }
  ]
}
```

**Expected Results**:
- ✅ Returns historical alerts (may be empty initially)
- ✅ Each alert has: type, severity, message, data, timestamp
- ✅ Limit parameter works correctly

---

### Test 5.3: Error Rate Spike Detection

**Purpose**: Verify automatic spike detection via background task

**Steps**:

**1. Establish Baseline** (5 minutes of normal activity):
```bash
python scripts/generate_test_logs.py --scenario normal --count 50
# Wait 5 minutes for baseline period
```

**2. Generate Error Spike**:
```bash
# Generate 100 ERROR logs in ~5 seconds
for i in {1..100}; do
  curl -X POST http://localhost:8000/logs \
    -H "Content-Type: application/json" \
    -d '{"logs":[{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S)'","level":"ERROR","service":"payment-api","message":"Spike test '$i'","error_type":"TestSpike"}]}'
  sleep 0.05
done
```

**3. Wait for Background Task**:
- Background task runs every 5 minutes
- Maximum detection delay: 5 minutes
- Alert should trigger within 6 minutes

**4. Verify Alert**:
- Check frontend: Toast notification should appear
- Check API:
  ```bash
  curl http://localhost:8001/alerts/history?limit=1
  ```
- Verify alert data:
  ```json
  {
    "type": "error_rate_spike",
    "severity": "critical",
    "message": "에러율 X% 증가 감지 (최근 5분)",
    "data": {
      "current_count": 100,
      "baseline_count": ~10,
      "spike_percentage": ~900
    }
  }
  ```

**Expected Results**:
- ✅ Alert detected within 6 minutes
- ✅ Spike percentage calculated correctly
- ✅ Severity = critical (spike >50%)
- ✅ WebSocket broadcast to frontend
- ✅ Toast notification displays

---

### Test 5.4: Slow API Detection

**Purpose**: Verify slow API identification (>2 seconds)

**Steps**:

**1. Generate Slow API Logs**:
```bash
# Generate 10 slow API requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/logs \
    -H "Content-Type: application/json" \
    -d '{"logs":[{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S)'","level":"INFO","service":"payment-api","path":"/api/v1/checkout","duration_ms":3500,"message":"Slow request '$i'"}]}'
  sleep 0.5
done
```

**2. Wait 5 Minutes**:
- Background task will analyze last 10 minutes
- Looks for APIs with avg duration_ms > 2000

**3. Verify Alert**:
```bash
curl http://localhost:8001/alerts/history?limit=1
```

Expected:
```json
{
  "type": "slow_api",
  "severity": "warning",
  "message": "1개 느린 API 감지 (>2초)",
  "data": {
    "slow_apis": [
      {
        "path": "/api/v1/checkout",
        "service": "payment-api",
        "avg_duration": 3500,
        "count": 10
      }
    ]
  }
}
```

**Expected Results**:
- ✅ Slow APIs detected (>2000ms threshold)
- ✅ Average duration calculated correctly
- ✅ Alert includes API path and service
- ✅ Count shows number of slow requests

---

### Test 5.5: Service Down Detection

**Purpose**: Verify detection of services without logs for 5+ minutes

**Steps**:

**1. Establish Service Activity**:
```bash
# Generate logs for "test-service"
for i in {1..20}; do
  curl -X POST http://localhost:8000/logs \
    -H "Content-Type: application/json" \
    -d '{"logs":[{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S)'","level":"INFO","service":"test-service","message":"Active '$i'"}]}'
  sleep 2
done
```

**2. Stop Generating Logs**:
- Simply stop - don't generate any more logs for "test-service"
- Other services can continue generating logs

**3. Wait 6+ Minutes**:
- Background task checks for services with no logs in last 5 minutes

**4. Verify Alert**:
```bash
curl http://localhost:8001/alerts/history?limit=1
```

Expected:
```json
{
  "type": "service_down",
  "severity": "critical",
  "message": "1개 서비스 로그 없음 (5분)",
  "data": {
    "services": ["test-service"]
  }
}
```

**Expected Results**:
- ✅ Service flagged as down after 5 min silence
- ✅ Severity = critical (service unavailability is critical)
- ✅ Alert includes list of down services
- ✅ Only silent services flagged (others continue normally)

---

### Test 5.6: Alert Toast Notification UI

**Purpose**: Verify real-time alert UI and user interaction

**Steps**:
1. Trigger any alert (error spike recommended for speed)
2. **Immediately after alert triggers**, observe frontend UI:

**Alert Appearance**:
- Toast appears bottom-right corner
- Severity icon matches level:
  - ℹ️ for info
  - ⚠️ for warning
  - 🚨 for critical
- Border color matches severity:
  - Blue for info
  - Yellow for warning
  - Red for critical

**Alert Content**:
- Title: Alert type (e.g., "Error Rate Spike")
- Message: Clear description
- Details: Expandable JSON data
- Timestamp: Localized Korean format

**Interaction**:
3. **Auto-Dismiss Test**: Wait 10 seconds
   - Toast should auto-hide

4. **Manual Dismiss Test**: Trigger another alert
   - Click ✕ button
   - Toast should immediately close

5. **Multiple Alerts**: Trigger 2-3 alerts rapidly
   - Only latest alert shown
   - Previous alerts accessible in history

**Expected Results**:
- ✅ Toast appears within 1-2 seconds of alert
- ✅ Correct severity styling (icon + border)
- ✅ Message clear and actionable
- ✅ Details expandable
- ✅ Auto-dismiss after 10s works
- ✅ Manual dismiss works instantly
- ✅ No overlapping toasts

---

### Test 5.7: Alert History Page

**Purpose**: Verify alert history UI and filtering

**Steps**:
1. Generate several alerts (different types and severities)
2. Navigate to `/alerts` route in frontend
3. Verify alert list displays all historical alerts

**UI Elements to Check**:
- Alert cards show: icon, title, severity badge, message, timestamp
- Data expandable in details
- Sorted by timestamp (newest first)

**Test Filtering**:
4. Use severity filter dropdown:
   - Select "Warning" → only warning alerts shown
   - Select "Critical" → only critical alerts shown
   - Select "All" → all alerts shown

**Test Clear Functionality**:
5. Click "Clear All" button
6. Verify all alerts removed from history
7. Empty state message: "No alerts"

**Test Unread Count**:
8. Generate new alert
9. Check Sidebar: unread count badge appears
10. Navigate to /alerts
11. Verify unread count clears (markAllAsRead on mount)

**Expected Results**:
- ✅ All historical alerts visible
- ✅ Filtering by severity works
- ✅ Clear All removes all alerts
- ✅ Unread count in sidebar
- ✅ Auto-mark-as-read when viewing history
- ✅ Empty state handled gracefully

---

## 🔧 Feature #6: Tool Selection Layer

### Test 6.1: SQL Tool Selection (Default)

**Purpose**: Verify SQL is default tool for standard queries

**Steps**:
1. Ask standard question: `최근 에러 로그`
2. Watch for `tool_selected` event:
   ```json
   {
     "type": "tool_selected",
     "node": "tool_selector",
     "data": {
       "tool": "sql",
       "reason": "Best for structured queries and data filtering"
     }
   }
   ```
3. Verify standard SQL workflow executes

**Expected Results**:
- ✅ SQL tool selected by default
- ✅ tool_selected event emitted
- ✅ Normal SQL execution path

---

### Test 6.2: Grep Tool Selection for Patterns

**Purpose**: Verify pattern matching queries route to grep tool

**Steps**:
1. Ask pattern question: `'timeout' 패턴 포함된 로그`
2. Watch for `tool_selected` event:
   ```json
   {
     "type": "tool_selected",
     "data": {
       "tool": "grep",
       "reason": "Best for pattern matching and text search"
     }
   }
   ```
3. Verify SQL uses LIKE pattern:
   ```sql
   SELECT * FROM logs
   WHERE message LIKE '%timeout%'
   AND deleted = FALSE
   ORDER BY created_at DESC
   ```
4. Check results contain "timeout" in message field

**Expected Results**:
- ✅ Grep tool selected for pattern queries
- ✅ Pattern extracted from question correctly
- ✅ SQL uses LIKE operator
- ✅ Results match pattern

**Pattern Detection Keywords**:
- '패턴', '유사한', 'matching', '포함된', 'contains', 'search'

---

### Test 6.3: Metrics Tool Selection & Fallback

**Purpose**: Verify metrics tool detection and graceful fallback

**Steps**:
1. Ask metrics question: `전체 서비스 통계`
2. Watch for `tool_selected` event:
   ```json
   {
     "type": "tool_selected",
     "data": {
       "tool": "sql",
       "reason": "Best for structured queries and data filtering"
     }
   }
   ```
3. Verify it falls back to SQL (metrics API not yet implemented)
4. SQL should still provide aggregated statistics

**Expected Results**:
- ✅ Tool selection logic identifies metrics keywords
- ✅ Graceful fallback to SQL
- ✅ Query still succeeds and returns stats
- ✅ No errors due to missing metrics tool

**Metrics Keywords**:
- '전체', '통계', 'summary', '개요', 'overview', 'dashboard'

---

## 🔗 Integration Test Scenarios

### Scenario A: Cache + Context + Multi-Step

**Purpose**: Test multiple features working together in realistic workflow

**Complete Conversation Flow**:

**Turn 1: Initial Query (Set Context)**
```
User: "최근 payment-api 에러는?"
System:
  - context_resolved: no references, focus set to {service: payment-api}
  - optimization_complete: complexity=simple
  - plan_generated: is_multi_step=false (simple query)
  - Standard SQL execution
  - complete: cache_hit=false, results displayed
  - Focus badge appears: "Service: payment-api"
```

**Turn 2: Same Query (Cache Hit)**
```
User: "최근 payment-api 에러는?"
System:
  - cache_hit event immediately
  - complete: cache_hit=true, <100ms response
  - ⚡ Cached badge displayed
  - No SQL execution, no Claude API calls
```

**Turn 3: Context Reference (Cache Miss, New Query)**
```
User: "그 서비스의 느린 API는?"
System:
  - context_resolved: resolution_needed=true
  - Original: "그 서비스의 느린 API는?"
  - Resolved: "payment-api 서비스의 느린 API는?"
  - optimization_complete: complexity=simple
  - SQL includes: WHERE service = 'payment-api' AND duration_ms > 1000
  - complete: cache_hit=false (new question)
  - New cache entry created
```

**Turn 4: Complex Follow-up (Multi-Step)**
```
User: "왜 느려졌어?"
System:
  - context_resolved: "payment-api가 왜 느려졌어?"
  - optimization_complete: complexity=complex, strategy=use_multi_step
  - plan_generated: is_multi_step=true, step_count=3
    - Step 0: Current slow API count
    - Step 1: Historical slow API baseline
    - Step 2: Concurrent system issues
  - MultiStepProgress displayed
  - step_completed events (0, 1, 2)
  - all_steps_complete
  - Final insight synthesizes: "payment-api의 /checkout 엔드포인트가
    평균 3.2초로 느려졌습니다 (기존 500ms). 동시에 DatabaseConnectionError가
    발생하여 연결 대기 시간이 증가한 것이 원인입니다."
```

**Verification Checklist**:
- ✅ Cache reduces redundant queries (Turn 2)
- ✅ Context maintained across all turns
- ✅ References resolved correctly (Turn 3)
- ✅ Complex questions trigger multi-step (Turn 4)
- ✅ All features work seamlessly together
- ✅ Focus badges update correctly
- ✅ No conflicts or errors

---

### Scenario B: Alert-Driven Conversation

**Purpose**: Test alert system integration with context-aware chat

**Flow**:

**Step 1: Generate Alert Condition**
```bash
# Create error spike
python scripts/generate_test_logs.py --scenario error_spike --count 100
```

**Step 2: Wait for Alert** (~5 minutes)
- Background task detects spike
- Alert broadcast via WebSocket
- Toast notification appears:
  ```
  🚨 Error Rate Spike
  에러율 150.0% 증가 감지 (최근 5분)

  Details:
  {
    "current_count": 100,
    "baseline_count": 40,
    "spike_percentage": 150.0
  }
  ```

**Step 3: Context-Aware Follow-up**
```
User: "방금 alert에 대해 자세히 알려줘"
System:
  - context_resolved: Uses alert data from focus
  - If alert had service info, includes in query
  - Retrieves detailed error logs
  - Analyzes spike timing, error types, affected users
  - Provides actionable recommendations
```

**Step 4: Deep Dive**
```
User: "그 에러의 원인은?"
System:
  - Context maintains error_type from alert
  - Multi-step analysis:
    - Step 0: Error distribution by time
    - Step 1: Concurrent system events
    - Step 2: Affected endpoints
  - Root cause analysis insight
```

**Verification Checklist**:
- ✅ Alert generated and broadcast
- ✅ Toast displays alert details
- ✅ User can reference "방금 alert"
- ✅ Context-aware analysis uses alert data
- ✅ Multi-step triggered for root cause
- ✅ Comprehensive actionable insights

---

### Scenario C: Complex Analysis Pipeline

**Purpose**: Test full advanced feature stack in production workflow

**Question**: `어떤 서비스가 가장 문제인가?`

**Complete Pipeline Execution**:

**1. Optimization Analysis**:
```json
{
  "type": "optimization_complete",
  "data": {
    "complexity": "complex",
    "strategy": "use_multi_step",
    "indexes": ["idx_service_level_time"]
  }
}
```

**2. Query Planning**:
```json
{
  "type": "plan_generated",
  "data": {
    "step_count": 4,
    "is_multi_step": true,
    "steps": [
      {"index": 0, "description": "Count errors by service (24h)"},
      {"index": 1, "description": "Top 3 services error type distribution"},
      {"index": 2, "description": "Severity analysis per service"},
      {"index": 3, "description": "Trend analysis (today vs yesterday)"}
    ]
  }
}
```

**3. Multi-Step Execution**:

**Step 0**: Count errors by service
```sql
SELECT service, COUNT(*) as error_count
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND deleted = FALSE
GROUP BY service
ORDER BY error_count DESC
```
Result: payment-api (250), user-api (180), order-api (120)

**Step 1**: Error type distribution for top 3
```sql
SELECT service, error_type, COUNT(*) as count
FROM logs
WHERE level = 'ERROR'
  AND service IN ('payment-api', 'user-api', 'order-api')
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY service, error_type
ORDER BY service, count DESC
```

**Step 2**: Severity analysis
```sql
SELECT service, level, COUNT(*) as count
FROM logs
WHERE service IN ('payment-api', 'user-api', 'order-api')
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY service, level
```

**Step 3**: Trend comparison
```sql
-- Today vs Yesterday error counts
...
```

**4. Final Insight**:
```
"가장 문제가 많은 서비스는 payment-api입니다 (250건 에러).
주요 에러 타입은 DatabaseConnectionError (60%)와 TimeoutError (30%)입니다.
어제 대비 오늘 에러가 2배 증가했으며, 특히 오전 10-11시에 집중되어 있습니다.
즉시 데이터베이스 연결 풀 크기를 확인하고, 피크 시간대 스케일링을 고려하세요."
```

**5. Follow-up with Context**:
```
User: "그 서비스들의 공통점은?"
System:
  - context_resolved: "payment-api, user-api, order-api 서비스들의 공통점은?"
  - Analyzes common patterns
  - All three services share same database
  - All show DatabaseConnectionError
  - Recommends database-level investigation
```

**6. Cache Check**:
```
User: "어떤 서비스가 가장 문제인가?" (exact same initial question)
System:
  - cache_hit=true
  - Instant response with previous results
```

**Verification Checklist**:
- ✅ Optimization → complexity=complex
- ✅ Planning → 4-step decomposition
- ✅ Multi-step execution successful
- ✅ Each step builds on previous
- ✅ Final insight comprehensive
- ✅ Context preserved for follow-up
- ✅ Cache works for repeated questions
- ✅ All features integrated smoothly

---

## 📊 Test Execution Checklist

Copy this to track progress:

```
FEATURE TESTS (24 tests)
========================

[ ] Feature #1: Query Result Cache
  [ ] 1.1 Cache Miss → Hit
  [ ] 1.2 Cache Invalidation
  [ ] 1.3 TTL Expiration

[ ] Feature #2: Context-Aware Agent
  [ ] 2.1 Focus Tracking
  [ ] 2.2 Reference Resolution
  [ ] 2.3 Conversation History
  [ ] 2.4 New Conversation Reset

[ ] Feature #3: Multi-Step Reasoning
  [ ] 3.1 Simple → Single Step
  [ ] 3.2 Complex → Multi-Step
  [ ] 3.3 Step Progress UI
  [ ] 3.4 Step Failure Handling

[ ] Feature #4: Query Optimization
  [ ] 4.1 Complexity Classification
  [ ] 4.2 Strategy Selection
  [ ] 4.3 Index Suggestions

[ ] Feature #5: Alerting & Monitoring
  [ ] 5.1 Manual Check API
  [ ] 5.2 Alert History API
  [ ] 5.3 Error Rate Spike
  [ ] 5.4 Slow API Detection
  [ ] 5.5 Service Down Detection
  [ ] 5.6 Toast Notification UI
  [ ] 5.7 Alert History Page

[ ] Feature #6: Tool Selection
  [ ] 6.1 SQL Tool (default)
  [ ] 6.2 Grep Tool (patterns)
  [ ] 6.3 Metrics Fallback

INTEGRATION SCENARIOS (3 tests)
================================

[ ] Scenario A: Cache + Context + Multi-Step
  [ ] Turn 1: Initial query sets context
  [ ] Turn 2: Same query hits cache
  [ ] Turn 3: Reference resolved from context
  [ ] Turn 4: Complex question triggers multi-step

[ ] Scenario B: Alert + Context
  [ ] Alert generated and broadcast
  [ ] User asks about alert
  [ ] Context-aware detailed analysis

[ ] Scenario C: Complex Pipeline
  [ ] Optimization identifies complexity
  [ ] Planning decomposes into steps
  [ ] Multi-step executes sequentially
  [ ] Insight synthesizes findings
  [ ] Follow-up uses context
  [ ] Cache works on repeat

TOTAL: 27 test cases
```

---

## 🐛 Troubleshooting Guide

### Issue: Frontend Won't Build

**Symptoms**:
```
ERROR: failed to solve: failed to compute cache key
```

**Diagnosis**:
```bash
# Test local build first
cd frontend
pnpm install
pnpm run build

# Check for build errors
```

**Fixes**:
- Ensure pnpm-lock.yaml exists and is valid
- Check package.json for syntax errors
- Verify all dependencies are compatible
- Try `pnpm install --no-frozen-lockfile` if lock file is corrupted

---

### Issue: Nginx 404 on All Routes

**Symptoms**:
- http://localhost:3000 returns 404
- No files served

**Diagnosis**:
```bash
# Check if dist files exist in container
docker exec -it log-analysis-frontend sh
ls -la /usr/share/nginx/html

# Expected: index.html, assets/, etc.
```

**Fixes**:
- Verify build stage completed successfully
- Check COPY --from=builder path is correct
- Ensure `pnpm run build` creates `dist/` directory
- Check vite.config.ts build.outDir setting

---

### Issue: API Requests Fail (CORS or 502)

**Symptoms**:
- Frontend loads but API calls fail
- Console shows CORS errors or 502 Bad Gateway

**Diagnosis**:
```bash
# Test nginx proxy from inside container
docker exec -it log-analysis-frontend sh
wget -O- http://log-analysis-server:8000/health

# Should return: {"status": "healthy"}
```

**Fixes**:
- Verify log-analysis-server is running: `docker-compose ps`
- Check service names in nginx.conf match docker-compose.yml
- Ensure both services on same network (log-network)
- Check nginx logs: `docker logs log-analysis-frontend`

---

### Issue: WebSocket Connection Failed

**Symptoms**:
```
WebSocket connection to 'ws://localhost:3000/ws/query' failed
```

**Diagnosis**:
```bash
# Check nginx WebSocket proxy config
docker exec -it log-analysis-frontend cat /etc/nginx/conf.d/default.conf

# Verify Upgrade headers present
grep -A5 "location /ws/" /etc/nginx/conf.d/default.conf
```

**Fixes**:
- Ensure nginx.conf has Upgrade and Connection headers
- Check proxy_read_timeout is long enough (7d recommended)
- Verify proxy_buffering off for real-time streaming
- Test backend WebSocket directly:
  ```bash
  # From host
  wscat -c ws://localhost:8001/ws/query
  ```

---

### Issue: Alerts Not Received in Frontend

**Symptoms**:
- Background task runs but frontend doesn't show alerts
- No toast notifications

**Diagnosis**:
```bash
# Check if background task is running
docker-compose logs log-analysis-server | grep -i "anomaly"

# Check active WebSocket connections
# (Add logging to websocket.py to show connection count)

# Manual alert trigger
curl -X POST http://localhost:8001/alerts/check
```

**Fixes**:
- Verify WebSocket connection is active
- Check active_connections list in websocket.py
- Ensure broadcast_alert function is called
- Verify AlertNotification component is mounted
- Check alertStore subscription

---

### Issue: Multi-Step Progress Not Showing

**Symptoms**:
- Complex queries execute but no progress UI
- MultiStepProgress component not rendered

**Diagnosis**:
```bash
# Check if plan_generated event is emitted
# Browser DevTools → Network → WS → Messages

# Verify is_multi_step flag
```

**Fixes**:
- Check planner.py returns is_multi_step=true for complex queries
- Verify Home.svelte listens for plan_generated event
- Ensure stepStatuses state updates trigger reactivity
- Check MultiStepProgress component import

---

## 🎯 Success Criteria

### Build & Deploy
- ✅ `docker-compose build` completes without errors
- ✅ `docker-compose up -d` starts all 4 services
- ✅ All services pass health checks within 30 seconds
- ✅ Frontend accessible at http://localhost:3000

### Functional Tests
- ✅ At least 24/27 tests pass (>88%)
- ✅ All critical features work (cache, context, multi-step)
- ✅ WebSocket streaming functional
- ✅ No unhandled errors in browser console

### Performance
- ✅ Cache hit: <100ms response time
- ✅ Simple query: <3s total time
- ✅ Multi-step: <15s for 4 steps
- ✅ Frontend load: <2s initial load

### User Experience
- ✅ Can ask questions and receive answers
- ✅ Real-time event streaming visible
- ✅ UI components render correctly
- ✅ No crashes or connection drops
- ✅ Error messages clear and helpful

---

## 📈 Test Metrics Template

**File**: `TEST_RESULTS.md` (create during testing)

```markdown
# Test Execution Results

**Date**: 2026-02-05
**Environment**: Docker Compose (4 services)
**Frontend URL**: http://localhost:3000
**Backend URL**: http://localhost:8001
**Tester**: [Your Name]

## Summary

- **Total Tests**: 27
- **Passed**: __/27 (__%)
- **Failed**: __/27 (__%)
- **Skipped**: __/27 (__%)

## Performance Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cache hit time | <100ms | __ ms | ✅/❌ |
| Simple query time | <3s | __ s | ✅/❌ |
| Multi-step time (4 steps) | <15s | __ s | ✅/❌ |
| Frontend load time | <2s | __ s | ✅/❌ |
| Alert detection latency | <6min | __ min | ✅/❌ |

## Feature Results

### Feature #1: Query Result Cache
- [x] 1.1 Cache Miss → Hit - **PASS** (cache_hit toggles correctly, 85ms on hit)
- [ ] 1.2 Cache Invalidation - **FAIL** (cache not cleared, investigating...)
- [x] 1.3 TTL Expiration - **PASS** (expires after 5 min)

**Notes**: Issue with invalidate_cache endpoint - need to check endpoint registration

### Feature #2: Context-Aware Agent
- [x] 2.1 Focus Tracking - **PASS**
- [x] 2.2 Reference Resolution - **PASS** (90% accuracy)
- [x] 2.3 Conversation History - **PASS**
- [ ] 2.4 New Conversation - **FAIL** (button not found in UI)

**Notes**: Need to verify button was added to Home.svelte

... (continue for all features)

## Issues Found

### Issue #1: WebSocket Reconnection
- **Severity**: Medium
- **Description**: After 3 failed reconnects, WebSocket gives up
- **Impact**: User must refresh page to reconnect
- **Fix**: Increase maxReconnectAttempts to 5-10 or add manual reconnect button

### Issue #2: Alert Toast Z-Index
- **Severity**: Low
- **Description**: Toast notification overlaps with chat input on small screens
- **Impact**: Minor UI annoyance
- **Fix**: Adjust CSS z-index or positioning

... (continue documenting issues)

## Recommendations

1. **Critical**: Fix issue #X (prevents core functionality)
2. **Important**: Address issue #Y (affects UX)
3. **Enhancement**: Consider improvement #Z

## Sign-off

- [ ] All critical issues resolved
- [ ] >90% test pass rate achieved
- [ ] Performance targets met
- [ ] Ready for production deployment

**Tester Signature**: ________________
**Date**: ________________
```

---

## 🚀 Quick Test Commands

### Health Checks
```bash
# All services
docker-compose ps

# Individual health
curl http://localhost:8001/health
curl http://localhost:3000
curl http://localhost:8000/docs

# Database
docker exec -it log-analysis-postgres psql -U loguser -d logdb -c "SELECT COUNT(*) FROM logs;"
```

### Log Monitoring
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f log-analysis-server
docker-compose logs -f frontend

# Filter for errors
docker-compose logs | grep -i error
```

### Test Data Generation
```bash
# Normal baseline
python scripts/generate_test_logs.py --scenario normal --count 100

# Error spike (for alerts)
python scripts/generate_test_logs.py --scenario error_spike --count 100

# Slow APIs
python scripts/generate_test_logs.py --scenario slow_api

# Service down simulation
python scripts/generate_test_logs.py --scenario service_down

# All scenarios
python scripts/generate_test_logs.py --scenario all
```

### Alert Testing
```bash
# Manual anomaly check
curl -X POST http://localhost:8001/alerts/check

# Alert history
curl http://localhost:8001/alerts/history?limit=10

# Cache invalidation
curl -X POST http://localhost:8001/invalidate_cache
```

---

## 🎓 Test Best Practices

### Before Testing
1. **Clean State**: Start with fresh containers
   ```bash
   docker-compose down -v  # Remove volumes
   docker-compose up -d
   ```

2. **Baseline Data**: Generate normal logs first
   ```bash
   python scripts/generate_test_logs.py --scenario normal --count 50
   ```

3. **Browser DevTools**: Open Network tab → WS filter
   - Watch WebSocket messages in real-time
   - Verify event types and data

### During Testing
1. **One Feature at a Time**: Complete all tests for one feature before moving to next
2. **Document Everything**: Note exact steps, screenshots, and observations
3. **Reproduce Issues**: If a test fails, run it 2-3 times to confirm
4. **Check Logs**: Always check Docker logs when something fails

### After Testing
1. **Calculate Metrics**: Update TEST_RESULTS.md with actual numbers
2. **Prioritize Issues**: Critical → Important → Nice-to-have
3. **Fix and Retest**: Address issues and re-run failed tests
4. **Final Validation**: Run integration scenarios to ensure fixes didn't break other features

---

## 📚 Additional Resources

### Useful Commands

**Docker Management**:
```bash
# Rebuild specific service
docker-compose build --no-cache frontend

# Restart specific service
docker-compose restart log-analysis-server

# View resource usage
docker stats

# Clean up
docker-compose down
docker system prune -a  # Remove unused images/containers
```

**Database Queries**:
```bash
# Direct SQL access
docker exec -it log-analysis-postgres psql -U loguser -d logdb

# Useful queries
SELECT COUNT(*) FROM logs WHERE deleted = FALSE;
SELECT service, COUNT(*) FROM logs GROUP BY service;
SELECT level, COUNT(*) FROM logs GROUP BY level;
```

**Log Analysis**:
```bash
# Error count in logs
docker-compose logs log-analysis-server | grep -i "error" | wc -l

# WebSocket messages
docker-compose logs log-analysis-server | grep -i "websocket"

# Cache operations
docker-compose logs log-analysis-server | grep -i "cache"
```

---

## ✅ Test Completion Criteria

### Must Achieve
- [x] All 4 Docker services running and healthy
- [x] Frontend accessible and functional
- [x] At least 24/27 tests passing (>88%)
- [x] All critical features operational
- [x] No blocking bugs

### Should Achieve
- [ ] 27/27 tests passing (100%)
- [ ] All performance targets met
- [ ] No errors in Docker logs
- [ ] All edge cases handled

### Nice to Have
- [ ] Performance benchmarks documented
- [ ] Video walkthrough of features
- [ ] README updated with Docker setup
- [ ] CI/CD pipeline for automated testing

---

**Total Test Cases**: 27 (24 feature + 3 integration)

**Estimated Test Time**: 3-4 hours (including wait times for alerts)

**Success Rate Target**: >90% (at least 24 passing)
