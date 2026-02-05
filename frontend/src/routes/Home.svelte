<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { marked } from 'marked'
  import { chatStore } from '../lib/stores/chat'
  import { historyStore } from '../lib/stores/history'
  import { QueryWebSocket, type StreamEvent } from '../lib/api/websocket'
  import ServiceFilter from '../lib/components/ServiceFilter.svelte'
  import TimeRangeModal from '../lib/components/TimeRangeModal.svelte'  // NEW
  import type { TimeRangeValue, TimeRangeStructured } from '$lib/types'  // NEW
  import ConversationContext from '../lib/components/ConversationContext.svelte'
  import TaskHistoryPanel from '$lib/components/TaskHistoryPanel.svelte'  // NEW: Task History
  import MultiStepProgress from '../lib/components/MultiStepProgress.svelte'  // Feature #3
  import AlertNotification from '../lib/components/AlertNotification.svelte'  // Feature #5
  import { alertStore } from '../lib/stores/alert'  // Feature #5
  import { getApiUrl } from '$lib/config'

  // Configure marked for safe HTML rendering
  marked.setOptions({
    breaks: true,  // Convert \n to <br>
    gfm: true,     // GitHub Flavored Markdown
  })

  // Track if Markdown error alert was already shown
  let markdownErrorShown = false

  // Convert markdown to HTML using marked library
  function renderMarkdown(markdown: string): string {
    if (!markdown) return ''
    try {
      return marked.parse(markdown) as string
    } catch (error) {
      console.error('Markdown parsing error:', error)

      // Show alert only once to avoid spam
      if (!markdownErrorShown) {
        markdownErrorShown = true
        alertStore.addAlert({
          type: 'alert',
          severity: 'info',
          message: '일부 텍스트 서식을 표시할 수 없습니다.',
          data: {}
        })
      }

      return markdown  // Fallback to plain text
    }
  }

  // Helper: Format time range for display (handles both string and object)
  function formatTimeRangeDisplay(timeRange: string | TimeRangeStructured | any): string {
    if (!timeRange) return ''

    // If it's a preset string (1h, 6h, etc.), convert to Korean
    if (typeof timeRange === 'string') {
      const presetMap: Record<string, string> = {
        '1h': '최근 1시간',
        '2h': '최근 2시간',
        '6h': '최근 6시간',
        '12h': '최근 12시간',
        '24h': '최근 24시간',
        '48h': '최근 48시간',
        '7d': '최근 7일',
        'all': '전체',
        'custom': '사용자 지정'
      }
      return presetMap[timeRange] || timeRange
    }

    // If it's a TimeRangeStructured object
    if (typeof timeRange === 'object') {
      // Handle null/undefined type (means "all" or no filter)
      if (!timeRange.type || timeRange.type === null) {
        return '전체'
      }

      if (timeRange.type === 'relative' && timeRange.relative) {
        const unitMap: Record<string, string> = { h: '시간', d: '일', w: '주', m: '월' }
        return `최근 ${timeRange.relative.value}${unitMap[timeRange.relative.unit]}`
      } else if (timeRange.type === 'absolute' && timeRange.absolute) {
        return `${timeRange.absolute.start} ~ ${timeRange.absolute.end}`
      }
    }

    return '전체'  // Fallback to "전체" instead of [object Object]
  }

  // Helper: Compare LLM extracted time with dropdown time
  function areTimesEqual(llmTime: any, dropdownValue: string, customValue: TimeRangeValue | null): boolean {
    if (!llmTime) return false

    if (dropdownValue === 'custom' && customValue) {
      // 사용자 지정 값과 비교
      const customStructured = buildTimeRangeStructured(customValue)
      return JSON.stringify(llmTime) === JSON.stringify(customStructured)
    }

    // preset 값과 비교
    const presetMap: Record<string, { value: number; unit: string }> = {
      '1h': { value: 1, unit: 'h' },
      '2h': { value: 2, unit: 'h' },
      '6h': { value: 6, unit: 'h' },
      '12h': { value: 12, unit: 'h' },
      '24h': { value: 24, unit: 'h' },
      '48h': { value: 48, unit: 'h' },
      '7d': { value: 7, unit: 'd' }
    }

    const preset = presetMap[dropdownValue]
    if (!preset || !llmTime?.relative) return false

    return llmTime.relative.value === preset.value && llmTime.relative.unit === preset.unit
  }

  // NEW: Node to task title mapping for task history
  const NODE_TASK_TITLES: Record<string, string> = {
    resolve_context: '사용자 질문 분석 중...',
    extract_filters: '필터 추출 중...',
    clarifier: '질문 명확화 검사 중...',
    retrieve_schema: '스키마 분석 중...',
    generate_sql: 'SQL 쿼리 생성 중...',
    validate_sql: 'SQL 안전성 검사 중...',
    execute_query: '데이터베이스 조회 중...',
    generate_insight: '최종 보고서 작성 중...'
  }

  let question = ''
  let chatContainer: HTMLDivElement
  let wsClient: QueryWebSocket | null = null

  $: messages = $chatStore.messages
  $: isLoading = $chatStore.isLoading
  $: streamingSQL = $chatStore.streamingSQL
  $: streamingInsight = $chatStore.streamingInsight
  $: currentNode = $chatStore.currentNode
  $: conversationId = $chatStore.conversationId  // Feature #2
  $: currentFocus = $chatStore.currentFocus  // Feature #2

  // Auto-summarize when messages exceed threshold
  $: {
    if (messages.length > 5 && currentQueryId && !isLoading) {
      summarizeConversationIfNeeded(currentQueryId, messages)
    }
  }

  let isGeneratingSQL = false
  let isGeneratingInsight = false
  let sqlCompleted = false // SQL 생성 완료 상태
  let insightCompleted = false // 인사이트 생성 완료 상태
  let currentQueryId: string | null = null  // 현재 쿼리의 히스토리 ID
  let cacheHit = false  // Feature #1: Cache hit indicator

  // Feature #3: Multi-step state
  let isMultiStep = false
  let queryPlan: any[] = []
  let stepStatuses: Array<{
    index: number
    description: string
    status: 'pending' | 'active' | 'completed' | 'failed'
    sql?: string
    resultCount?: number
    executionTime?: number
  }> = []

  // Feature #4: Optimization state
  let queryComplexity: string | null = null
  let optimizationStrategy: string | null = null

  // Filter state
  let selectedService = 'all'
  let selectedTimeRange = 'all'
  let customTimeRange: TimeRangeValue | null = null  // NEW: 사용자 지정 시간 범위

  // Clarification (재질문) - 메시지 기반
  let clarificationAnswers: Record<string, Record<string, string>> = {}  // {clarificationId: {q0: answer, q1: answer}}

  // NEW: Clarification custom time range support
  let showClarificationModal = false
  let clarificationModalContext: { clarificationId: string; questionIndex: number } | null = null
  let clarificationCustomTimeRange: TimeRangeValue | null = null

  // Query timeout handling
  let queryTimeout: NodeJS.Timeout | null = null
  const QUERY_TIMEOUT_MS = 30000  // 30 seconds

  // Filter conflict data
  let conflictData: {
    service?: { user: string; ai: string }
    timeRange?: { user: string; ai: any }
  } | null = null

  // Table sorting state - per message
  let tableSortState: Record<string, { column: string; direction: 'asc' | 'desc' }> = {}
  let originalClarificationQuestion = ''

  // Quick questions scroll gradient state
  let showLeftGradient = false
  let showRightGradient = true
  let quickQuestionsScroll: HTMLDivElement

  function handleQuickQuestionsScroll(e: Event) {
    const target = e.target as HTMLDivElement
    const { scrollLeft, scrollWidth, clientWidth } = target

    showLeftGradient = scrollLeft > 5
    showRightGradient = scrollLeft < scrollWidth - clientWidth - 5
  }

  onMount(() => {
    // Initialize WebSocket connection
    wsClient = new QueryWebSocket()
    wsClient.connect(handleStreamEvent)
    scrollToBottom()

    // Check initial scroll state for quick questions
    setTimeout(() => {
      if (quickQuestionsScroll) {
        const { scrollLeft, scrollWidth, clientWidth } = quickQuestionsScroll
        showLeftGradient = scrollLeft > 5
        showRightGradient = scrollLeft < scrollWidth - clientWidth - 5
      }
    }, 100)
  })

  onDestroy(() => {
    // Clean up WebSocket connection
    wsClient?.disconnect()
    // Clean up query timeout
    if (queryTimeout) {
      clearTimeout(queryTimeout)
      queryTimeout = null
    }
  })

  // NEW: Generate completed task title based on event data
  function getCompletedTitle(event: any): string {
    const node = event.node
    const data = event.data || {}

    switch(node) {
      case 'resolve_context':
        return data.resolution_needed
          ? `질문 해석 완료: "${data.resolved_question}"`
          : '질문 분석 완료'

      case 'extract_filters':
        const filters = []
        if (data.service) filters.push(`서비스=${data.service}`)
        if (data.time_range) filters.push(`시간=${formatTimeRangeDisplay(data.time_range)}`)
        return filters.length > 0
          ? `필터 추출 완료: ${filters.join(', ')}`
          : '필터 추출 완료'

      case 'clarifier':
        return data.count > 0
          ? `재질문 필요 (${data.count}개)`
          : '재질문 없음 - 진행'

      case 'retrieve_schema':
        return '스키마 분석 완료'

      case 'generate_sql':
        return 'SQL 쿼리 생성 완료'

      case 'validate_sql':
        return 'SQL 검증 완료'

      case 'execute_query':
        return '데이터베이스 조회 완료'

      case 'generate_insight':
        return '최종 보고서 작성 완료'

      default:
        return `${node} 완료`
    }
  }

  function handleStreamEvent(event: StreamEvent) {
    // Clear query timeout when we receive any event (response arrived)
    if (queryTimeout) {
      clearTimeout(queryTimeout)
      queryTimeout = null
    }

    switch (event.type) {
      case 'cache_hit':
        // Feature #1: Show cache indicator
        cacheHit = true
        chatStore.addStatusMessage('⚡ 캐시된 결과 (즉시 응답)')
        setTimeout(scrollToBottom, 100)
        break

      case 'context_resolved':
        // Feature #2: Update focus and show resolution
        if (event.data.focus) {
          chatStore.updateFocus(event.data.focus)
        }

        // Show resolution message if references were resolved
        if (event.data.resolution_needed && event.data.resolved_question) {
          chatStore.addStatusMessage(
            `참조 해석: "${event.data.original_question}" → "${event.data.resolved_question}"`
          )
        }
        setTimeout(scrollToBottom, 100)
        break

      case 'filters_extracted':
        // LLM-based filter extraction
        const service = event.data.service
        const timeRange = event.data.time_range
        const confidence = event.data.confidence || 0

        if (service || timeRange) {
          // Check for conflicts with dropdown
          const hasDropdownService = selectedService !== 'all'
          const hasDropdownTime = selectedTimeRange !== 'all' || customTimeRange !== null

          const serviceConflict = service && hasDropdownService && service !== selectedService

          // 시간 충돌: LLM이 추출한 시간과 드롭다운 값을 비교
          const timeConflict = timeRange && hasDropdownTime && !areTimesEqual(timeRange, selectedTimeRange, customTimeRange)

          if (serviceConflict || timeConflict) {
            // 충돌 감지 → 쿼리 취소 및 재질문 표시

            // 1. 백엔드 쿼리 취소
            if (wsClient) {
              wsClient.cancel()
            }

            // 2. 로딩 상태 중지
            chatStore.setLoading(false)
            chatStore.clearStreaming()

            // 3. 재질문 메시지 생성
            const clarifications = []

            if (serviceConflict) {
              clarifications.push({
                question: '서비스 필터가 충돌합니다. 어느 것을 사용하시겠습니까?',
                options: [
                  `사용자 선택: ${selectedService}`,
                  `AI 추출: ${service}`
                ],
                field: 'service_conflict',
                required: true
              })
            }

            if (timeConflict) {
              clarifications.push({
                question: '시간 필터가 충돌합니다. 어느 것을 사용하시겠습니까?',
                options: [
                  `사용자 선택: ${formatTimeRangeDisplay(selectedTimeRange)}`,
                  `AI 추출: ${formatTimeRangeDisplay(timeRange)}`
                ],
                field: 'time_conflict',
                required: true
              })
            }

            // 4. 재질문 메시지 추가
            chatStore.addClarificationMessage(clarifications)

            // 5. 충돌 데이터 저장 (나중에 사용)
            conflictData = {
              service: serviceConflict ? { user: selectedService, ai: service } : undefined,
              timeRange: timeConflict ? { user: selectedTimeRange, ai: timeRange } : undefined
            }

            setTimeout(scrollToBottom, 100)
          } else {
            // No conflict - apply extracted filters to dropdowns automatically
            if (service && selectedService === 'all') {
              selectedService = service
            }
            // 시간 필터는 드롭다운이 'all'일 때만 상태 메시지 표시
            // (드롭다운 자동 업데이트는 안 함 - preset 매핑 복잡도 때문)

            // Show extraction result
            const parts = []
            if (service) parts.push(`서비스: ${service}`)
            if (timeRange) parts.push(`시간: ${formatTimeRangeDisplay(timeRange)}`)
            if (parts.length > 0) {
              chatStore.addStatusMessage(`🔍 필터 자동 적용: ${parts.join(', ')}`)
            }
          }
        }
        setTimeout(scrollToBottom, 100)
        break

      case 'tool_selected':
        // Feature #6: Display selected tool
        const toolIcons = {
          sql: '💾 SQL Query',
          grep: '🔍 Pattern Search',
          metrics: '📊 Metrics API'
        }
        const selectedToolName = toolIcons[event.data.tool] || event.data.tool
        // Only show if not SQL (since SQL is default)
        if (event.data.tool !== 'sql') {
          chatStore.addStatusMessage(`Tool: ${selectedToolName}`)
        }
        setTimeout(scrollToBottom, 100)
        break

      case 'optimization_complete':
        // Feature #4: Display optimization info
        queryComplexity = event.data.complexity
        optimizationStrategy = event.data.strategy

        const complexityBadge = {
          simple: '🟢 Simple',
          moderate: '🟡 Moderate',
          complex: '🔴 Complex'
        }[queryComplexity] || queryComplexity

        chatStore.addStatusMessage(
          `Query Complexity: ${complexityBadge} | Strategy: ${optimizationStrategy}`
        )
        setTimeout(scrollToBottom, 100)
        break

      case 'plan_generated':
        // Feature #3: Initialize multi-step tracking
        isMultiStep = event.data.is_multi_step
        if (isMultiStep) {
          queryPlan = event.data.steps
          stepStatuses = queryPlan.map((s) => ({
            index: s.index,
            description: s.description,
            status: 'pending' as const
          }))
          // Mark first step as active
          if (stepStatuses.length > 0) {
            stepStatuses[0].status = 'active'
          }
          chatStore.addStatusMessage(
            `🔍 복잡한 질문을 ${event.data.step_count}단계로 분해했습니다`
          )
        }
        setTimeout(scrollToBottom, 100)
        break

      case 'step_completed':
        // Feature #3: Update step status
        {
          const stepIndex = event.data.step_index
          stepStatuses[stepIndex] = {
            ...stepStatuses[stepIndex],
            status: 'completed',
            sql: event.data.sql,
            resultCount: event.data.result_count,
            executionTime: event.data.execution_time_ms
          }

          // Mark next step as active
          if (stepIndex + 1 < stepStatuses.length) {
            stepStatuses[stepIndex + 1].status = 'active'
          }

          stepStatuses = [...stepStatuses] // Trigger reactivity
          setTimeout(scrollToBottom, 100)
        }
        break

      case 'step_failed':
        // Feature #3: Mark step as failed
        {
          const stepIndex = event.data.step_index
          stepStatuses[stepIndex].status = 'failed'
          stepStatuses = [...stepStatuses]
          chatStore.addErrorMessage(
            `Step ${stepIndex + 1} failed: ${event.data.error}`
          )
          setTimeout(scrollToBottom, 100)
        }
        break

      case 'all_steps_complete':
        // Feature #3: All steps done
        chatStore.addStatusMessage(
          `✅ ${event.data.total_steps}단계 분석 완료`
        )
        setTimeout(scrollToBottom, 100)
        break

      case 'node_start':
        chatStore.setCurrentNode(event.node)

        // NEW: Add task history item
        chatStore.addTaskHistoryItem({
          id: `task_${event.node}_${Date.now()}`,
          nodeId: event.node,
          title: NODE_TASK_TITLES[event.node] || event.node,
          status: 'active',
          startTime: new Date(),
          details: {},
          expanded: false
        })

        // Update UI based on node
        if (event.node === 'generate_sql') {
          isGeneratingSQL = true
          chatStore.updateStreamingSQL('')
        } else if (event.node === 'generate_insight') {
          // End SQL generation before starting insight generation
          isGeneratingSQL = false
          isGeneratingInsight = true
          chatStore.updateStreamingInsight('')
        }

        setTimeout(scrollToBottom, 100)
        break

      case 'node_end':
        // NEW: Complete task history item with details
        const completedTitle = getCompletedTitle(event)
        chatStore.completeTaskHistoryItem(event.node, {
          title: completedTitle,
          details: {
            llmPrompt: event.data?.llm_prompt,
            llmResponse: event.data?.llm_response,
            eventData: event.data
          }
        })

        // Mark generation as complete for each node
        if (event.node === 'generate_sql') {
          isGeneratingSQL = false
          sqlCompleted = true // Keep SQL displayed after generation
        } else if (event.node === 'generate_insight') {
          isGeneratingInsight = false
          insightCompleted = true // Keep insight displayed after generation
        }
        break

      case 'token':
        // Accumulate streaming text (SQL or Insight)
        if (isGeneratingSQL) {
          chatStore.updateStreamingSQL(streamingSQL + event.content)
        } else if (isGeneratingInsight) {
          chatStore.updateStreamingInsight(streamingInsight + event.content)
        }
        break

      case 'complete':
        console.log('[COMPLETE] Event received', {
          sql: event.sql?.substring(0, 50),
          insight: event.insight?.substring(0, 50),
          resultCount: event.count,
          cacheHit: event.cache_hit  // Feature #1
        })

        // NEW: Update task history items with final results
        chatStore.updateTaskHistoryItem('execute_query', {
          details: {
            resultCount: event.count,
            executionTime: event.execution_time_ms
          }
        })

        // NEW: Update generate_sql node with SQL
        chatStore.updateTaskHistoryItem('generate_sql', {
          details: {
            sqlGenerated: event.sql
          }
        })

        // Add final AI message with cache_hit flag
        // (empty messages will be filtered at UI render level)
        chatStore.addAIMessage({
          sql: event.sql,
          results: event.results,
          count: event.count,
          displayed: event.displayed,
          truncated: event.truncated,
          execution_time_ms: event.execution_time_ms,
          insight: event.insight,
          error: null,
          cache_hit: event.cache_hit || false  // Feature #1
        })

        // Wait a tick for reactivity
        setTimeout(() => {
          console.log('[COMPLETE] After addAIMessage - messages:', $chatStore.messages.length, 'isLoading:', $chatStore.isLoading)
          console.log('[COMPLETE] Last message:', $chatStore.messages[$chatStore.messages.length - 1])

          // Save full conversation to history
          if (currentQueryId) {
            console.log('[COMPLETE] Updating history for query:', currentQueryId)
            historyStore.updateMessages(currentQueryId, $chatStore.messages)
            currentQueryId = null
          }

          // Reset loading state (redundant since addAIMessage already does this, but keeping for safety)
          chatStore.setLoading(false)
          chatStore.clearStreaming()

          // Feature #3: Reset multi-step state
          isMultiStep = false
          stepStatuses = []
          queryPlan = []

          // Feature #4: Reset optimization state
          queryComplexity = null
          optimizationStrategy = null
          isGeneratingSQL = false
          isGeneratingInsight = false
          sqlCompleted = false
          insightCompleted = false
          cacheHit = false  // Feature #1: Reset cache indicator

          console.log('[COMPLETE] Final state - isLoading:', $chatStore.isLoading, 'messages:', $chatStore.messages.length)

          setTimeout(scrollToBottom, 100)
        }, 0)
        break

      case 'validation_failed':
        // SQL 검증 실패 (위험한 SQL, 구문 오류 등)
        const validationError = event.data?.error || 'SQL validation failed'
        const retryCount = event.data?.retry_count || 1

        // 백엔드에서 오는 원본 메시지로 중복 체크
        const lastMessage = $chatStore.messages[$chatStore.messages.length - 1]
        const isDuplicateError = lastMessage?.role === 'error' && lastMessage.content.includes(validationError)

        if (isDuplicateError) {
          // 중복: 재시도 횟수만 업데이트
          chatStore.updateLastErrorMessage(`SQL 검증 실패 (재시도 ${retryCount}/3): ${validationError}`)
        } else {
          // 첫 번째 에러: 새 메시지 추가
          chatStore.addErrorMessage(`SQL 검증 실패 (재시도 ${retryCount}/3): ${validationError}`)
        }

        chatStore.setLoading(false)
        chatStore.clearStreaming()
        isGeneratingSQL = false
        isGeneratingInsight = false
        sqlCompleted = false
        insightCompleted = false
        setTimeout(scrollToBottom, 100)
        break

      case 'execution_failed':
        // SQL 실행 실패 (데이터베이스 오류 등)
        const executionError = event.data?.error || 'SQL execution failed'
        chatStore.addErrorMessage(`쿼리 실행 실패: ${executionError}`)
        chatStore.setLoading(false)
        chatStore.clearStreaming()
        isGeneratingSQL = false
        isGeneratingInsight = false
        sqlCompleted = false
        insightCompleted = false
        setTimeout(scrollToBottom, 100)
        break

      case 'error':
        chatStore.addErrorMessage(event.message)
        chatStore.setLoading(false)
        chatStore.clearStreaming()
        isGeneratingSQL = false
        isGeneratingInsight = false
        sqlCompleted = false
        insightCompleted = false
        break

      case 'cancelled':
        chatStore.addStatusMessage('⏹️ 쿼리가 취소되었습니다')
        chatStore.setLoading(false)
        chatStore.clearStreaming()
        isGeneratingSQL = false
        isGeneratingInsight = false
        break

      case 'alert':
        // Feature #5: Handle background alerts
        alertStore.addAlert({
          type: event.type,
          severity: event.severity,
          message: event.message,
          data: event.data
        })
        break

      case 'clarification_failed':
        // Clarification generation failed
        chatStore.addErrorMessage(
          `재질문 생성 실패: ${event.data?.message || event.data?.error || '알 수 없는 오류'}`
        )
        chatStore.setLoading(false)
        setTimeout(scrollToBottom, 100)
        break

      case 'anomaly_check_error':
        // Background anomaly detection error - show as alert notification
        alertStore.addAlert({
          type: 'alert',
          severity: event.severity || 'warning',
          message: event.message,
          data: event.data
        })
        break

      case 'clarification_needed':
        // 재질문 필요 - AI 메시지로 표시
        const clarificationId = chatStore.addClarificationMessage(event.data.questions || [])
        clarificationAnswers[clarificationId] = {}  // 답변 저장소 초기화
        chatStore.setLoading(false)  // 로딩 중지
        setTimeout(scrollToBottom, 100)
        break

      case 'clarification_skipped':
        // 재질문 건너뜀
        chatStore.addStatusMessage(event.data.message || '재질문 건너뜀 - 현재 정보로 진행')
        setTimeout(scrollToBottom, 100)
        break
    }
  }

  // NEW: Clarification modal handlers
  function handleClarificationModalConfirm(timeRange: TimeRangeValue) {
    if (!clarificationModalContext) return

    const { clarificationId, questionIndex } = clarificationModalContext
    const timeText = formatTimeRangeKorean(timeRange)

    if (!clarificationAnswers[clarificationId]) {
      clarificationAnswers[clarificationId] = {}
    }
    clarificationAnswers[clarificationId][`q${questionIndex}`] = timeText
    clarificationCustomTimeRange = timeRange
    showClarificationModal = false
    clarificationModalContext = null
  }

  function handleClarificationModalCancel() {
    showClarificationModal = false
    clarificationModalContext = null
  }

  function submitClarification(clarificationId: string, clarifications: any[]) {
    const answers = clarificationAnswers[clarificationId]

    // 필수 질문 체크
    const requiredQuestions = clarifications.filter(c => c.required)
    const allRequiredAnswered = requiredQuestions.every((c, i) => answers[`q${i}`])

    if (requiredQuestions.length > 0 && !allRequiredAnswered) {
      alert('필수 항목을 선택해주세요')
      return
    }

    // 답변을 메시지에 저장 (히스토리용)
    chatStore.updateClarificationAnswers(clarificationId, answers)

    // 원래 질문 가져오기 (마지막 user 메시지)
    const lastUserMessage = $chatStore.messages.filter(m => m.role === 'user').pop()
    let enhancedQuestion = lastUserMessage?.content || question

    // 답변을 질문에 반영
    clarifications.forEach((clarification, i) => {
      const answer = answers[`q${i}`]
      if (answer) {
        // 필터 충돌 답변 처리
        if (clarification.field === 'service_conflict' && conflictData?.service) {
          const isUserChoice = answer.startsWith('사용자 선택')
          selectedService = isUserChoice ? conflictData.service.user : conflictData.service.ai
          chatStore.addStatusMessage(`✓ 서비스 필터: ${selectedService} 선택됨`)
        } else if (clarification.field === 'time_conflict' && conflictData?.timeRange) {
          const isUserChoice = answer.startsWith('사용자 선택')
          const chosenValue = isUserChoice ? conflictData.timeRange.user : conflictData.timeRange.ai

          if (!isUserChoice) {
            // AI 추출 값 선택 시 → 드롭다운에 반영
            updateDropdownFromTimeRange(chosenValue)
          }
          // isUserChoice면 드롭다운은 이미 설정되어 있음 (변경 없음)

          chatStore.addStatusMessage(`✓ 시간 필터: ${formatTimeRangeDisplay(chosenValue)} 선택됨`)
        }
        // 일반 재질문 답변 처리
        else if (clarification.field === 'service') {
          // 서비스 선택 저장
          if (answer === '전체') {
            selectedService = 'all'
          } else {
            // "payment-api (결제 처리)" → "payment-api"
            selectedService = answer.split(' ')[0]
          }

          // 질문 재구성 (시간 표현 제거 + 선택된 필터로 재구성)
          let baseQuestion = lastUserMessage?.content || question

          // 기존 시간 표현 제거
          baseQuestion = baseQuestion.replace(/최근\s*\d+\s*(시간|일|주|개?월)/g, '')
          baseQuestion = baseQuestion.replace(/^\d+시간\s*/g, '')
          baseQuestion = baseQuestion.replace(/\s+/g, ' ').trim()

          // 서비스 추가
          if (selectedService !== 'all') {
            enhancedQuestion = `${selectedService}의 ${baseQuestion}`
          } else {
            enhancedQuestion = `전체 서비스의 ${baseQuestion}`
          }

          // 시간 추가 (드롭다운에 선택된 값 사용)
          if (customTimeRange) {
            const timeText = formatTimeRangeKorean(customTimeRange)
            enhancedQuestion = `${timeText} ${enhancedQuestion}`
          } else if (selectedTimeRange !== 'all' && selectedTimeRange !== 'custom') {
            const timeText = formatTimeRangeDisplay(selectedTimeRange)
            enhancedQuestion = `${timeText} ${enhancedQuestion}`
          }
        } else if (clarification.field === 'time') {
          if (answer === '전체') {
            // "전체" 시간 선택 시 → 질문 그대로 (모든 기간)
            // enhancedQuestion 변경 없음
          } else {
            enhancedQuestion = `${answer} ${enhancedQuestion}`
          }
        } else if (clarification.field === 'comparison') {
          enhancedQuestion = `${enhancedQuestion} (${answer})`
        }
      }
    })

    // 충돌 재질문인 경우: 필터만 업데이트하고 원래 질문 재실행
    const isConflictClarification = conflictData !== null

    if (isConflictClarification) {
      // 충돌 해결 완료 - 선택된 필터로 질문 재구성
      chatStore.setLoading(true)
      chatStore.addStatusMessage(`✓ 필터 충돌 해결됨 - 쿼리 재실행`)

      // 원래 질문에서 기본 부분만 추출 (시간/서비스 제거)
      let baseQuestion = lastUserMessage?.content || question

      // 기존 시간 표현 제거
      baseQuestion = baseQuestion.replace(/최근\s*\d+\s*(시간|일|주|개?월)/g, '')
      baseQuestion = baseQuestion.replace(/^\d+시간\s*/g, '')
      baseQuestion = baseQuestion.replace(/\s+/g, ' ').trim()

      // 선택된 필터로 질문 재구성
      let finalQuestion = baseQuestion

      // 서비스 추가
      if (selectedService !== 'all') {
        if (!finalQuestion.includes(selectedService)) {
          finalQuestion = `${selectedService}의 ${finalQuestion}`
        }
      }

      // 시간 추가
      if (customTimeRange) {
        const timeText = formatTimeRangeKorean(customTimeRange)
        finalQuestion = `${timeText} ${finalQuestion}`
      } else if (selectedTimeRange !== 'all' && selectedTimeRange !== 'custom') {
        const timeText = formatTimeRangeDisplay(selectedTimeRange)
        finalQuestion = `${timeText} ${finalQuestion}`
      }

      currentQueryId = historyStore.addQuery(finalQuestion)

      // 드롭다운 값을 백엔드에 전달 (사용자 지정 또는 preset)
      let timeRangeStructured: TimeRangeStructured | null = null
      if (customTimeRange) {
        // 사용자 지정 시간
        timeRangeStructured = buildTimeRangeStructured(customTimeRange)
      } else if (selectedTimeRange !== 'all' && selectedTimeRange !== 'custom') {
        // Preset 드롭다운 - 구조화된 형식으로 변환
        const timeMap: Record<string, { value: number; unit: string }> = {
          '1h': { value: 1, unit: 'h' },
          '2h': { value: 2, unit: 'h' },
          '6h': { value: 6, unit: 'h' },
          '12h': { value: 12, unit: 'h' },
          '24h': { value: 24, unit: 'h' },
          '48h': { value: 48, unit: 'h' },
          '7d': { value: 7, unit: 'd' }
        }
        const timeConfig = timeMap[selectedTimeRange]
        if (timeConfig) {
          timeRangeStructured = {
            type: 'relative',
            relative: {
              value: timeConfig.value,
              unit: timeConfig.unit
            },
            absolute: null
          }
        }
      }

      wsClient?.query(finalQuestion, 100, conversationId, timeRangeStructured)

      // Clear conflict data
      conflictData = null
    } else {
      // 일반 재질문: 향상된 질문으로 재실행
      chatStore.addUserMessage(enhancedQuestion)
      chatStore.setLoading(true)
      chatStore.addStatusMessage(`📝 질문 보완: ${enhancedQuestion}`)

      currentQueryId = historyStore.addQuery(enhancedQuestion)

      // NEW: Include custom time range if set during clarification
      let timeRangeStructured: TimeRangeStructured | null = null
      if (clarificationCustomTimeRange) {
        timeRangeStructured = buildTimeRangeStructured(clarificationCustomTimeRange)
      }

      wsClient?.query(enhancedQuestion, 100, conversationId, timeRangeStructured)

      // Clear clarification custom time range after submission
      clarificationCustomTimeRange = null
    }

    setTimeout(scrollToBottom, 100)
  }

  function handleSort(messageId: string, column: string) {
    const currentSort = tableSortState[messageId]

    // Toggle direction if same column, otherwise default to ascending
    if (currentSort && currentSort.column === column) {
      tableSortState[messageId] = {
        column,
        direction: currentSort.direction === 'asc' ? 'desc' : 'asc'
      }
    } else {
      tableSortState[messageId] = { column, direction: 'asc' }
    }

    // Trigger Svelte reactivity by reassigning the object
    tableSortState = { ...tableSortState }
  }

  function getSortedResults(results: any[], messageId: string, sortStateRef: typeof tableSortState) {
    const sortState = sortStateRef[messageId]
    if (!sortState) return results

    const sorted = [...results].sort((a, b) => {
      const aVal = a[sortState.column]
      const bVal = b[sortState.column]

      // Handle null values
      if (aVal === null) return 1
      if (bVal === null) return -1

      // Numeric comparison
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortState.direction === 'asc' ? aVal - bVal : bVal - aVal
      }

      // String comparison
      const aStr = String(aVal).toLowerCase()
      const bStr = String(bVal).toLowerCase()

      if (sortState.direction === 'asc') {
        return aStr < bStr ? -1 : aStr > bStr ? 1 : 0
      } else {
        return aStr > bStr ? -1 : aStr < bStr ? 1 : 0
      }
    })

    return sorted
  }

  let summarizationInProgress = false

  async function summarizeConversationIfNeeded(queryId: string, messages: any[]) {
    // Avoid duplicate summarization
    if (summarizationInProgress) return

    // Only summarize AI/user messages
    const relevantMessages = messages.filter(m =>
      m.role === 'user' || m.role === 'ai'
    )

    // Need at least 6 messages to summarize (keep recent 5, summarize old ones)
    if (relevantMessages.length <= 5) return

    // Check if already summarized
    const historyItem = historyStore.getById(queryId)
    if (historyItem?.memorySummary) return

    try {
      summarizationInProgress = true

      // Get old messages to summarize (all except recent 5)
      const oldMessages = relevantMessages.slice(0, -5).map(m => ({
        role: m.role,
        content: m.content || '',
        sql: m.sql,
        count: m.count,
        insight: m.insight
      }))

      // Call backend summarization API
      const response = await fetch(getApiUrl('summarize'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: oldMessages })
      })

      if (!response.ok) {
        throw new Error('Summarization failed')
      }

      const { summary } = await response.json()

      // Update history with summary
      historyStore.updateSummary(queryId, summary)

      console.log('[MEMORY] 대화 요약 완료:', summary)

    } catch (error) {
      console.error('[MEMORY] 요약 실패:', error)
    } finally {
      summarizationInProgress = false
    }
  }

  // NEW: 구조화된 시간 범위 생성 함수
  function buildTimeRangeStructured(customRange: TimeRangeValue): TimeRangeStructured {
    if (customRange.type === 'relative') {
      return {
        type: 'relative',
        relative: {
          value: customRange.value,
          unit: customRange.unit
        },
        absolute: null
      }
    } else {
      return {
        type: 'absolute',
        relative: null,
        absolute: {
          start: customRange.start,
          end: customRange.end
        }
      }
    }
  }

  // NEW: 시간 범위를 한국어로 변환
  function formatTimeRangeKorean(customRange: TimeRangeValue): string {
    if (customRange.type === 'relative') {
      const unitMap: Record<string, string> = { h: '시간', d: '일', w: '주', m: '월' }
      return `최근 ${customRange.value}${unitMap[customRange.unit]}`
    } else {
      return `${customRange.start}부터 ${customRange.end}까지`
    }
  }

  // Helper: AI 추출 시간 범위를 드롭다운에 반영
  function updateDropdownFromTimeRange(timeRange: any) {
    if (typeof timeRange === 'string') {
      // 문자열 preset → 그대로 사용
      selectedTimeRange = timeRange
      customTimeRange = null
    } else if (timeRange?.type === 'relative' && timeRange.relative) {
      // 구조화된 형식 → preset 매핑 시도
      const { value, unit } = timeRange.relative
      const presetKey = `${value}${unit}`

      const presets = ['1h', '2h', '6h', '12h', '24h', '48h', '7d']
      if (presets.includes(presetKey)) {
        selectedTimeRange = presetKey
        customTimeRange = null
      } else {
        // preset 없음 → 사용자 지정
        selectedTimeRange = 'custom'
        customTimeRange = { type: 'relative', value, unit }
      }
    } else if (timeRange?.type === 'absolute' && timeRange.absolute) {
      // 절대 날짜 → 사용자 지정
      selectedTimeRange = 'custom'
      customTimeRange = {
        type: 'absolute',
        start: timeRange.absolute.start,
        end: timeRange.absolute.end
      }
    }
  }

  function handleSubmit() {
    if (!question.trim() || isLoading || !wsClient) return

    // Check WebSocket connection status
    if (!wsClient.isConnected || !wsClient.isConnected()) {
      chatStore.addErrorMessage('WebSocket이 연결되지 않았습니다. 페이지를 새로고침해주세요.')
      return
    }

    // NEW: Clear previous task history
    chatStore.clearTaskHistory()

    let userQuestion = question.trim()
    const originalQuestion = userQuestion
    question = ''

    // Apply service filter from dropdown
    if (selectedService !== 'all') {
      userQuestion = `${selectedService}의 ${userQuestion}`
    }

    // NEW: 시간 범위 처리 (구조화된 형식 지원)
    let timeRangeStructured: TimeRangeStructured | null = null

    if (customTimeRange) {
      // 사용자 지정 시간 범위 (모달) - 명시적 의도이므로 백엔드에 전달
      timeRangeStructured = buildTimeRangeStructured(customTimeRange)
      const timePhrase = formatTimeRangeKorean(customTimeRange)
      if (!userQuestion.includes('최근') && !userQuestion.includes('시간') && !userQuestion.includes('부터')) {
        userQuestion = `${timePhrase} ${userQuestion}`
      }
    } else if (selectedTimeRange !== 'all' && selectedTimeRange !== 'custom') {
      // Preset 드롭다운 시간 범위 - 질문 텍스트에만 추가, 백엔드에는 전달 안 함
      // LLM이 질문에서 시간을 추출하도록 하여 충돌 감지 가능하게 함
      const timePhraseMap: Record<string, string> = {
        '1h': '최근 1시간',
        '2h': '최근 2시간',
        '6h': '최근 6시간',
        '12h': '최근 12시간',
        '24h': '최근 24시간',
        '48h': '최근 48시간',
        '7d': '최근 7일'
      }
      const timePhrase = timePhraseMap[selectedTimeRange]

      // Only add if not already mentioned
      if (timePhrase && !userQuestion.includes('최근') && !userQuestion.includes('시간')) {
        userQuestion = `${timePhrase} ${userQuestion}`
      }
      // timeRangeStructured는 null로 유지 (백엔드에 전달 안 함)
    }

    // Add user message (show original question)
    chatStore.addUserMessage(originalQuestion)
    chatStore.setLoading(true)

    // Show filter applied message if filters were used
    if (userQuestion !== originalQuestion) {
      chatStore.addStatusMessage(`🔍 필터 적용: ${userQuestion}`)
    }

    // Add to history and save ID
    currentQueryId = historyStore.addQuery(originalQuestion)

    // Send enhanced query via WebSocket with error handling
    try {
      wsClient.query(userQuestion, 100, conversationId, timeRangeStructured)

      // Start timeout timer
      if (queryTimeout) clearTimeout(queryTimeout)
      queryTimeout = setTimeout(() => {
        if (isLoading) {
          chatStore.addErrorMessage(
            '⏱️ 응답 시간 초과: 서버 응답이 없습니다. 네트워크 연결을 확인하거나 페이지를 새로고침해주세요.'
          )
          chatStore.setLoading(false)
          chatStore.clearStreaming()
        }
      }, QUERY_TIMEOUT_MS)
    } catch (error) {
      console.error('Failed to send query:', error)
      chatStore.addErrorMessage(
        `쿼리 전송 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`
      )
      chatStore.setLoading(false)
      return
    }

    // Scroll to bottom
    setTimeout(scrollToBottom, 100)
  }

  function handleCancel() {
    wsClient?.cancel()
    // Clear query timeout when user cancels
    if (queryTimeout) {
      clearTimeout(queryTimeout)
      queryTimeout = null
    }
  }

  function resetFilters() {
    selectedService = 'all'
    selectedTimeRange = 'all'
    customTimeRange = null
  }

  // Check if filters are modified from default
  $: filtersModified = selectedService !== 'all' || selectedTimeRange !== 'all' || customTimeRange !== null

  function scrollToBottom() {
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight
    }
  }

  function getNodeLabel(node: string): string {
    const labels: Record<string, string> = {
      resolve_context: '컨텍스트 해석 중...',  // Feature #2
      retrieve_schema: '스키마 조회 중...',
      optimize_query: '쿼리 최적화 중...',  // Feature #4
      plan_query: '쿼리 계획 수립 중...',  // Feature #3
      generate_sql: 'SQL 생성 중...',
      validate_sql: 'SQL 검증 중...',
      execute_query: '쿼리 실행 중...',
      execute_step: '단계 실행 중...',  // Feature #3
      generate_insight: '분석 중...'
    }
    return labels[node] || node
  }

  // Feature #2: Clear conversation and start fresh
  function handleNewConversation() {
    chatStore.clearConversation()
    question = ''
    selectedService = 'all'
    selectedTimeRange = 'all'
  }

  // Export function for sample queries
  export function handleSampleQuery(query: string) {
    question = query
    handleSubmit()
  }
</script>

<div class="flex flex-col h-full">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-4">
    <div class="max-w-5xl mx-auto flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-gray-900">💬 로그에 대해 질문하세요</h2>
        <p class="text-sm text-gray-600 mt-1">자연어로 질문하면 AI가 SQL을 생성합니다 (실시간 스트리밍)</p>
      </div>
      <!-- Feature #2: New Conversation Button -->
      {#if messages.length > 0}
        <button
          on:click={handleNewConversation}
          class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors flex items-center gap-2"
        >
          <span>🔄</span>
          <span>새로운 대화</span>
        </button>
      {/if}
    </div>
  </header>

  <!-- Chat Messages -->
  <div bind:this={chatContainer} class="flex-1 overflow-y-auto p-6">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- Feature #2: Conversation Context Panel -->
      <ConversationContext focus={currentFocus} />

      <!-- Feature #3: Multi-Step Progress -->
      {#if isMultiStep && stepStatuses.length > 0}
        <MultiStepProgress
          steps={stepStatuses}
          currentStep={stepStatuses.filter((s) => s.status === 'completed').length}
          totalSteps={stepStatuses.length}
        />
      {/if}

      {#if messages.length === 0}
        <!-- Empty State -->
        <div class="text-center py-12">
          <div class="text-6xl mb-4">💬</div>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">대화를 시작하세요</h3>
          <p class="text-gray-600">자연어로 로그에 대해 질문해보세요</p>
        </div>
      {/if}

      {#each messages as message, messageIndex (message.timestamp)}
        {#if message.role === 'user'}
          <!-- User Message -->
          <div class="flex justify-end">
            <div class="max-w-2xl">
              <div class="bg-blue-600 text-white rounded-lg px-4 py-3">
                <p class="text-sm">{message.content}</p>
              </div>
              <p class="text-xs text-gray-500 mt-1 text-right">
                👤 나 • {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        {:else if message.role === 'ai' && (message.sql || message.insight || (message.results && message.results.length > 0))}
          <!-- AI Response (only show if has content) -->
          <div class="flex justify-start">
            <div class="max-w-4xl w-full">
              <!-- Task History for this query -->
              {#if message.taskHistory && message.taskHistory.length > 0}
                <TaskHistoryPanel taskHistory={message.taskHistory} />
              {/if}

              <div class="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <!-- SQL -->
                {#if message.sql}
                  <div class="mb-4">
                    <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">생성된 SQL</h3>
                    <div class="bg-gray-900 text-gray-100 p-4 rounded font-mono text-xs overflow-x-auto">
                      {@html message.sql.replace(/\n/g, '<br>')}
                    </div>
                  </div>
                {/if}

                <!-- Results -->
                {#if message.results && message.results.length > 0}
                  <div class="mb-4">
                    <div class="flex items-center justify-between mb-2">
                      <h3 class="text-xs font-semibold text-gray-500 uppercase">결과</h3>
                      <span class="text-xs text-gray-500">
                        {message.count} rows • {message.executionTime?.toFixed(2)}ms
                      </span>
                    </div>
                    <div class="bg-gray-50 rounded border border-gray-200 overflow-hidden">
                      <div class="overflow-x-auto max-h-96">
                        <table class="w-full text-xs">
                          <thead class="bg-gray-100 sticky top-0">
                            <tr>
                              {#each Object.keys(message.results[0]) as key}
                                <th
                                  on:click={() => handleSort(String(message.timestamp), key)}
                                  class="px-3 py-2 text-left font-medium text-gray-700 whitespace-nowrap cursor-pointer hover:bg-gray-200 select-none transition-colors"
                                  title="클릭하여 정렬"
                                >
                                  <div class="flex items-center gap-1">
                                    <span>{key}</span>
                                    {#if tableSortState[String(message.timestamp)]?.column === key}
                                      <span class="text-blue-600">
                                        {tableSortState[String(message.timestamp)].direction === 'asc' ? '▲' : '▼'}
                                      </span>
                                    {:else}
                                      <span class="text-gray-400 opacity-0 group-hover:opacity-100">⇅</span>
                                    {/if}
                                  </div>
                                </th>
                              {/each}
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-gray-200">
                            {#each getSortedResults(message.results, String(message.timestamp), tableSortState) as row}
                              <tr class="hover:bg-gray-50">
                                {#each Object.values(row) as value}
                                  <td class="px-3 py-2 text-gray-900 whitespace-nowrap">
                                    {value !== null ? value : '-'}
                                  </td>
                                {/each}
                              </tr>
                            {/each}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                {/if}

                <!-- Insight -->
                {#if message.insight}
                  <div class="bg-blue-50 border border-blue-200 rounded p-4">
                    <div class="flex items-start gap-2">
                      <span class="text-lg">💡</span>
                      <div class="flex-1">
                        <h4 class="text-xs font-semibold text-blue-900 mb-1">AI 인사이트</h4>
                        <div class="text-sm text-blue-800 prose prose-sm max-w-none prose-blue">
                          {@html renderMarkdown(message.insight)}
                        </div>
                      </div>
                    </div>
                  </div>
                {/if}
              </div>
              <div class="flex items-center gap-2 mt-1">
                <p class="text-xs text-gray-500">
                  🤖 AI • {message.timestamp.toLocaleTimeString()}
                </p>
                {#if message.cacheHit}
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                    ⚡ Cached
                  </span>
                {/if}
              </div>
            </div>
          </div>
        {:else if message.role === 'error'}
          <!-- Error Message -->
          <div class="flex justify-start">
            <div class="max-w-2xl">
              <div class="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <div class="flex items-start gap-2">
                  <span class="text-red-600">❌</span>
                  <p class="text-sm text-red-800">{message.content}</p>
                </div>
              </div>
              <p class="text-xs text-gray-500 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        {:else if message.role === 'status'}
          <!-- Status Message -->
          <div class="flex justify-center">
            <div class="text-xs text-gray-500 italic">{message.content}</div>
          </div>
        {:else if message.role === 'clarification'}
          <!-- Clarification Message (AI 응답 스타일) -->
          <div class="flex justify-start">
            <div class="max-w-2xl">
              <div class="bg-purple-50 border border-purple-200 rounded-lg px-4 py-4">
                <div class="flex items-start gap-2 mb-4">
                  <span class="text-lg">💬</span>
                  <div class="flex-1">
                    <h4 class="text-sm font-semibold text-purple-900 mb-1">추가 정보가 필요합니다</h4>
                    <p class="text-xs text-purple-700">
                      {#if messages.slice(messageIndex + 1).some(m => m.role === 'user')}
                        <span class="text-purple-600">✓ 답변 완료</span>
                      {:else}
                        더 정확한 결과를 위해 몇 가지 질문에 답변해주세요
                      {/if}
                    </p>
                  </div>
                </div>

                <!-- Clarification Questions -->
                <div class="space-y-3 mb-4">
                  {#each message.clarifications || [] as clarification, i}
                    <div class="bg-white border border-purple-200 rounded-lg p-3 {messages.slice(messageIndex + 1).some(m => m.role === 'user') ? 'opacity-60' : ''}">
                      <label class="block text-xs font-medium text-gray-900 mb-2">
                        {clarification.question}
                        {#if clarification.required}
                          <span class="text-red-500 ml-1">*</span>
                        {/if}
                      </label>
                      {#if clarification.field === 'time' && clarification.allow_custom}
                        <!-- Time clarification with custom modal support -->
                        <div class="flex gap-2">
                          <select
                            value={message.userAnswers?.[`q${i}`] || clarificationAnswers[message.clarificationId]?.[`q${i}`] || ''}
                            on:change={(e) => {
                              const value = e.currentTarget.value
                              if (value === '사용자 지정...') {
                                clarificationModalContext = { clarificationId: message.clarificationId, questionIndex: i }
                                showClarificationModal = true
                              } else {
                                if (!clarificationAnswers[message.clarificationId]) {
                                  clarificationAnswers[message.clarificationId] = {}
                                }
                                clarificationAnswers[message.clarificationId][`q${i}`] = value
                                clarificationCustomTimeRange = null
                              }
                            }}
                            disabled={messages.slice(messageIndex + 1).some(m => m.role === 'user')}
                            class="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-purple-500 focus:border-purple-500 disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-75"
                          >
                            <option value="">선택하세요</option>
                            {#each clarification.options.filter(opt => opt !== '사용자 지정...') as option}
                              <option value={option}>{option}</option>
                            {/each}
                          </select>
                          <button
                            on:click={() => {
                              clarificationModalContext = { clarificationId: message.clarificationId, questionIndex: i }
                              showClarificationModal = true
                            }}
                            disabled={messages.slice(messageIndex + 1).some(m => m.role === 'user')}
                            class="px-3 py-1.5 text-sm bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            사용자 지정...
                          </button>
                        </div>
                        {#if clarificationCustomTimeRange && clarificationAnswers[message.clarificationId]?.[`q${i}`]?.startsWith('최근') || clarificationAnswers[message.clarificationId]?.[`q${i}`]?.includes('~')}
                          <span class="text-xs text-purple-600 font-medium mt-1 block">
                            {clarificationAnswers[message.clarificationId][`q${i}`]}
                          </span>
                        {/if}
                      {:else}
                        <!-- Regular select for non-time or non-custom clarifications -->
                        <select
                          value={message.userAnswers?.[`q${i}`] || clarificationAnswers[message.clarificationId]?.[`q${i}`] || ''}
                          on:change={(e) => {
                            if (!clarificationAnswers[message.clarificationId]) {
                              clarificationAnswers[message.clarificationId] = {}
                            }
                            clarificationAnswers[message.clarificationId][`q${i}`] = e.currentTarget.value
                          }}
                          disabled={messages.slice(messageIndex + 1).some(m => m.role === 'user')}
                          class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-purple-500 focus:border-purple-500 disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-75"
                        >
                          <option value="">선택하세요</option>
                          {#each clarification.options as option}
                            <option value={option}>{option}</option>
                          {/each}
                        </select>
                      {/if}
                    </div>
                  {/each}
                </div>

                <!-- Submit Button -->
                {#if !messages.slice(messageIndex + 1).some(m => m.role === 'user')}
                  <button
                    on:click={() => submitClarification(message.clarificationId, message.clarifications)}
                    class="w-full px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    확인
                  </button>
                {:else}
                  <div class="text-center text-xs text-purple-600 font-medium">
                    이미 답변이 제출되었습니다
                  </div>
                {/if}
              </div>
              <p class="text-xs text-gray-500 mt-1">
                🤖 AI • {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        {/if}
      {/each}

      <!-- Live Task History (during query execution) -->
      {#if isLoading && $chatStore.taskHistory.length > 0}
        <TaskHistoryPanel taskHistory={$chatStore.taskHistory} />
      {/if}

      <!-- Streaming SQL Display -->
      {#if (isGeneratingSQL || sqlCompleted) && streamingSQL}
        <div class="flex justify-start">
          <div class="max-w-4xl w-full">
            <div class="bg-white border border-blue-300 rounded-lg p-6 shadow-sm">
              <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">
                {sqlCompleted ? '생성된 SQL' : 'SQL 생성 중...'}
              </h3>
              <div class="bg-gray-900 text-gray-100 p-4 rounded font-mono text-xs overflow-x-auto">
                {streamingSQL}{#if isGeneratingSQL}<span class="animate-pulse">|</span>{/if}
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Streaming Insight Display -->
      {#if (isGeneratingInsight || insightCompleted) && streamingInsight}
        <div class="flex justify-start">
          <div class="max-w-4xl w-full">
            <div class="bg-blue-50 border border-blue-300 rounded p-4">
              <div class="flex items-start gap-2">
                <span class="text-lg">💡</span>
                <div class="flex-1">
                  <h4 class="text-xs font-semibold text-blue-900 mb-1">
                    {insightCompleted ? 'AI 인사이트' : 'AI 인사이트 생성 중...'}
                  </h4>
                  <p class="text-sm text-blue-800">
                    {streamingInsight}{#if isGeneratingInsight}<span class="animate-pulse">|</span>{/if}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Simple Loading Indicator -->
      {#if isLoading}
        <div class="flex items-center justify-center gap-3 py-4 mb-4">
          <div class="loading-spinner"></div>
          <div class="text-sm text-gray-600">
            {#if currentNode === 'retrieve_schema'}
              스키마 분석 중...
            {:else if currentNode === 'generate_sql'}
              SQL 생성 중...
            {:else if currentNode === 'validate_sql'}
              SQL 검증 중...
            {:else if currentNode === 'execute_query'}
              쿼리 실행 중...
            {:else if currentNode === 'generate_insight'}
              AI 분석 중...
            {:else}
              처리 중...
            {/if}
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Input Area -->
  <div class="border-t border-gray-200 bg-white p-4">
    <div class="max-w-5xl mx-auto">
      <!-- Service and Time Range Filters -->
      <div class="flex items-center mb-3">
        <div>
          <ServiceFilter
            bind:selectedService={selectedService}
            bind:selectedTimeRange={selectedTimeRange}
            bind:customTimeRange={customTimeRange}
            disabled={isLoading}
          />
        </div>
        {#if filtersModified}
          <button
            on:click={resetFilters}
            disabled={isLoading}
            class="ml-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            title="필터 초기화"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            초기화
          </button>
        {/if}
      </div>

      <!-- Sample Queries -->
      <div class="mb-3">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs font-semibold text-gray-500">빠른 질문:</span>
        </div>
        <div class="relative">
          <div
            class="flex overflow-x-auto gap-2 quick-questions-scroll"
            on:scroll={handleQuickQuestionsScroll}
            bind:this={quickQuestionsScroll}
          >
            <button
              on:click={() => handleSampleQuery('payment-api의 최근 에러 로그')}
              disabled={isLoading}
              class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
            >
              🔴 payment-api 에러
            </button>
            <button
              on:click={() => handleSampleQuery('최근 24시간 서비스별 에러 개수')}
              disabled={isLoading}
              class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
            >
              📊 서비스별 에러 통계
            </button>
            <button
              on:click={() => handleSampleQuery('DatabaseConnectionError가 발생한 모든 로그')}
              disabled={isLoading}
              class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
            >
              🔍 DB 연결 에러
            </button>
            <button
              on:click={() => handleSampleQuery('응답시간이 1초 이상인 느린 API 찾기')}
              disabled={isLoading}
              class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
            >
              ⚡ 느린 API 분석
            </button>
            <button
              on:click={() => handleSampleQuery('user-api의 최근 24시간 전체 로그')}
              disabled={isLoading}
              class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
            >
              📝 user-api 로그
            </button>
            <button
              on:click={() => handleSampleQuery('최근 24시간 에러 발생 추이 (1시간 단위)')}
              disabled={isLoading}
              class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
            >
              📈 에러 발생 추이
            </button>
          </div>
          <!-- Left gradient (shown when scrolled right) -->
          {#if showLeftGradient}
            <div class="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-white to-transparent pointer-events-none"></div>
          {/if}
          <!-- Right gradient (shown when not scrolled to end) -->
          {#if showRightGradient}
            <div class="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-white to-transparent pointer-events-none"></div>
          {/if}
        </div>
      </div>

      <!-- Input Form with Cancel Button -->
      <form on:submit|preventDefault={handleSubmit} class="flex gap-3">
        <input
          type="text"
          bind:value={question}
          disabled={isLoading}
          placeholder="질문을 입력하세요... (예: '최근 1시간 에러 로그')"
          class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        {#if isLoading}
          <button
            type="button"
            on:click={handleCancel}
            class="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors"
          >
            ⏹️ 취소
          </button>
        {:else}
          <button
            type="submit"
            disabled={!question.trim()}
            class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            전송
          </button>
        {/if}
      </form>
    </div>
  </div>
</div>

<!-- Feature #5: Alert Toast Notification -->
<AlertNotification />

<!-- Clarification Custom Time Range Modal -->
<TimeRangeModal
  bind:show={showClarificationModal}
  onConfirm={handleClarificationModalConfirm}
  onCancel={handleClarificationModalCancel}
/>

<style>
  /* Hide scrollbar for quick questions */
  .quick-questions-scroll {
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE and Edge */
  }

  .quick-questions-scroll::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Opera */
  }

  /* Loading spinner */
  .loading-spinner {
    width: 20px;
    height: 20px;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Markdown rendering styles for AI insights - use :global() for {@html} content */
  :global(.prose) {
    max-width: none;
  }

  :global(.prose p) {
    margin-bottom: 0.75em;
    line-height: 1.6;
  }

  :global(.prose p:last-child) {
    margin-bottom: 0;
  }

  :global(.prose strong),
  :global(.prose b) {
    font-weight: 600;
    color: rgb(30 58 138); /* blue-900 */
  }

  :global(.prose em),
  :global(.prose i) {
    font-style: italic;
  }

  :global(.prose ul),
  :global(.prose ol) {
    margin: 0.5em 0;
    padding-left: 1.5em;
  }

  :global(.prose ul) {
    list-style-type: disc;
  }

  :global(.prose ol) {
    list-style-type: decimal;
  }

  :global(.prose li) {
    margin: 0.25em 0;
  }

  :global(.prose code) {
    background-color: rgb(219 234 254); /* blue-100 */
    color: rgb(30 58 138); /* blue-900 */
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-size: 0.875em;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  :global(.prose pre) {
    background-color: rgb(30 41 59); /* slate-800 */
    color: rgb(226 232 240); /* slate-200 */
    padding: 0.75rem;
    border-radius: 0.375rem;
    overflow-x: auto;
    margin: 0.75em 0;
  }

  :global(.prose pre code) {
    background-color: transparent;
    color: inherit;
    padding: 0;
  }

  :global(.prose blockquote) {
    border-left: 3px solid rgb(147 197 253); /* blue-300 */
    padding-left: 1rem;
    margin: 0.75em 0;
    color: rgb(30 58 138); /* blue-900 */
    font-style: italic;
  }

  :global(.prose a) {
    color: rgb(37 99 235); /* blue-600 */
    text-decoration: underline;
  }

  :global(.prose a:hover) {
    color: rgb(29 78 216); /* blue-700 */
  }

  :global(.prose h1),
  :global(.prose h2),
  :global(.prose h3),
  :global(.prose h4),
  :global(.prose h5),
  :global(.prose h6) {
    font-weight: 600;
    color: rgb(30 58 138); /* blue-900 */
    margin-top: 1em;
    margin-bottom: 0.5em;
  }

  :global(.prose h1) { font-size: 1.25em; }
  :global(.prose h2) { font-size: 1.15em; }
  :global(.prose h3) { font-size: 1.1em; }
  :global(.prose h4) { font-size: 1em; }
  :global(.prose h5) { font-size: 0.95em; }
  :global(.prose h6) { font-size: 0.9em; }
</style>
