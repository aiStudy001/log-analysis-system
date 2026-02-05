<script lang="ts">
  import { historyStore } from '../lib/stores/history'
  import { chatStore } from '../lib/stores/chat'
  import { push } from 'svelte-spa-router'
  import { get } from 'svelte/store'

  let useDummyData = false // 실제 스토어 사용

  // 더미 쿼리 히스토리
  const dummyQueries = [
    { id: '1', question: '최근 1시간 에러 로그', timestamp: new Date(Date.now() - 5 * 60 * 1000), starred: true },
    { id: '2', question: 'payment-api에서 가장 많이 발생한 에러 top 5', timestamp: new Date(Date.now() - 15 * 60 * 1000), starred: true },
    { id: '3', question: 'API 응답시간이 1초 이상인 로그', timestamp: new Date(Date.now() - 30 * 60 * 1000), starred: false },
    { id: '4', question: '시간대별 에러 발생 추이 (5분 단위)', timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000), starred: false },
    { id: '5', question: 'user-api의 최근 24시간 로그 통계', timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), starred: false },
    { id: '6', question: 'DB connection timeout 에러 발생 현황', timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000), starred: true },
    { id: '7', question: '특정 사용자(user_id=12345)의 활동 로그', timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000), starred: false },
    { id: '8', question: '서비스별 에러율 비교', timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), starred: false }
  ]

  // 더미 데이터 또는 실제 데이터 사용
  $: queries = useDummyData ? dummyQueries : $historyStore
  $: starredQueries = queries.filter(q => q.starred)
  $: recentQueries = queries.filter(q => !q.starred)

  function handleToggleStar(id: string) {
    if (useDummyData) {
      // 더미 데이터 모드에서는 토글 비활성화 (실제로는 작동하지 않음)
      console.log('더미 데이터 모드에서는 별표 기능이 비활성화됩니다')
    } else {
      historyStore.toggleStar(id)
    }
  }

  function handleDeleteQuery(id: string) {
    if (useDummyData) {
      console.log('더미 데이터 모드에서는 삭제 기능이 비활성화됩니다')
    } else {
      historyStore.deleteQuery(id)
    }
  }

  function handleClear() {
    if (useDummyData) {
      console.log('더미 데이터 모드에서는 전체 삭제 기능이 비활성화됩니다')
    } else {
      if (confirm('정말로 모든 히스토리를 삭제하시겠습니까?')) {
        historyStore.clear()
      }
    }
  }

  function handleRerun(id: string) {
    // Get full conversation from history
    const item = get(historyStore).find(h => h.id === id)

    if (item && item.messages && item.messages.length > 0) {
      // Load conversation into chatStore
      chatStore.loadConversation(item.messages)
    } else {
      // Fallback: just show empty state
      chatStore.clear()
    }

    // Navigate to home
    push('/')
  }

  function formatDate(date: Date): string {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return '방금 전'
    if (minutes < 60) return `${minutes}분 전`
    if (hours < 24) return `${hours}시간 전`
    return `${days}일 전`
  }
</script>

<div class="h-full overflow-auto bg-gray-50">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
    <div class="max-w-5xl mx-auto flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-gray-900">📜 쿼리 히스토리</h2>
        <p class="text-sm text-gray-600 mt-1">{queries.length}개의 쿼리 저장됨</p>
      </div>
      {#if queries.length > 0}
        <button
          on:click={handleClear}
          class="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          모두 삭제
        </button>
      {/if}
    </div>
  </header>

  <!-- Content -->
  <div class="max-w-5xl mx-auto p-6">
    {#if queries.length === 0}
      <!-- Empty State -->
      <div class="text-center py-20">
        <div class="text-6xl mb-4">📜</div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">아직 쿼리 히스토리가 없습니다</h3>
        <p class="text-gray-600 mb-6">질문을 하시면 여기에 기록됩니다</p>
        <a
          href="/"
          class="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          질문 시작하기
        </a>
      </div>
    {:else}
      <!-- Starred Queries -->
      {#if starredQueries.length > 0}
        <div class="mb-8">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">⭐ 즐겨찾기</h3>
          <div class="space-y-3">
            {#each starredQueries as query}
              <div class="bg-white border-2 border-yellow-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div class="flex items-start gap-4">
                  <button
                    on:click={() => handleToggleStar(query.id)}
                    class="mt-1 text-2xl hover:scale-110 transition-transform"
                  >
                    ⭐
                  </button>
                  <div class="flex-1 min-w-0">
                    <p class="text-gray-900 font-medium">{query.question}</p>
                    <p class="text-sm text-gray-500 mt-1">
                      {formatDate(query.timestamp)} • {query.timestamp.toLocaleDateString()}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      on:click={() => handleRerun(query.id)}
                      class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      재실행
                    </button>
                    <button
                      on:click={() => handleDeleteQuery(query.id)}
                      class="p-1.5 text-gray-400 hover:text-red-600"
                      title="삭제"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Recent Queries -->
      {#if recentQueries.length > 0}
        <div>
          <h3 class="text-lg font-semibold text-gray-900 mb-4">최근 쿼리</h3>
          <div class="space-y-3">
            {#each recentQueries as query}
              <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div class="flex items-start gap-4">
                  <button
                    on:click={() => handleToggleStar(query.id)}
                    class="mt-1 text-2xl hover:scale-110 transition-transform opacity-50 hover:opacity-100"
                  >
                    ☆
                  </button>
                  <div class="flex-1 min-w-0">
                    <p class="text-gray-900">{query.question}</p>
                    <p class="text-sm text-gray-500 mt-1">
                      {formatDate(query.timestamp)} • {query.timestamp.toLocaleDateString()}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      on:click={() => handleRerun(query.id)}
                      class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                      재실행
                    </button>
                    <button
                      on:click={() => handleDeleteQuery(query.id)}
                      class="p-1.5 text-gray-400 hover:text-red-600"
                      title="삭제"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>
