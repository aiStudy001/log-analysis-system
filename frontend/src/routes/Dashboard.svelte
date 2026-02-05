<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { getStats } from '../lib/api/client'
  import type { StatsResponse } from '../lib/api/client'

  let stats: StatsResponse | null = null
  let loading = true
  let error: string | null = null
  let intervalId: number
  let useDummyData = false // 실제 API 호출

  // 더미 데이터
  const dummyStats: StatsResponse = {
    total_logs: 125847,
    recent_errors_1h: 342,
    level_distribution: [
      { level: 'ERROR', count: 8542 },
      { level: 'WARN', count: 23156 },
      { level: 'INFO', count: 78934 },
      { level: 'DEBUG', count: 15215 }
    ],
    service_distribution: [
      { service: 'payment-api', count: 45230 },
      { service: 'user-api', count: 38765 },
      { service: 'order-api', count: 21543 },
      { service: 'auth-api', count: 12456 },
      { service: 'notification-api', count: 5821 },
      { service: 'analytics-api', count: 2032 }
    ]
  }

  async function loadStats() {
    try {
      loading = true
      error = null

      if (useDummyData) {
        // 더미 데이터 사용 (로딩 시뮬레이션)
        await new Promise(resolve => setTimeout(resolve, 500))
        stats = dummyStats
      } else {
        // 실제 API 호출
        stats = await getStats()
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load stats'
      console.error('Failed to load stats:', err)
    } finally {
      loading = false
    }
  }

  onMount(() => {
    loadStats()
    // Refresh every 30 seconds
    intervalId = setInterval(loadStats, 30000)
  })

  onDestroy(() => {
    if (intervalId) {
      clearInterval(intervalId)
    }
  })

  $: lastUpdated = new Date().toLocaleTimeString()
</script>

<div class="h-full overflow-auto bg-gray-50">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
    <div class="max-w-7xl mx-auto flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-gray-900">📊 대시보드</h2>
        <p class="text-sm text-gray-600 mt-1">로그 통계 및 인사이트</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">마지막 업데이트: {lastUpdated}</span>
        <button
          on:click={loadStats}
          disabled={loading}
          class="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
          title="새로고침"
        >
          <span class:animate-spin={loading}>🔄</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Content -->
  <div class="max-w-7xl mx-auto p-6">
    {#if loading && !stats}
      <!-- Loading State -->
      <div class="flex items-center justify-center py-20">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p class="text-gray-600">통계를 불러오는 중...</p>
        </div>
      </div>
    {:else if error}
      <!-- Error State -->
      <div class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p class="text-red-800 font-medium">❌ {error}</p>
        <button
          on:click={loadStats}
          class="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    {:else if stats}
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <!-- Total Logs -->
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-600">전체 로그</h3>
            <span class="text-2xl">📊</span>
          </div>
          <p class="text-3xl font-bold text-gray-900">
            {stats.total_logs.toLocaleString()}
          </p>
        </div>

        <!-- Recent Errors -->
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-600">최근 에러 (1시간)</h3>
            <span class="text-2xl">🔴</span>
          </div>
          <p class="text-3xl font-bold text-red-600">
            {stats.recent_errors_1h}
          </p>
        </div>

        <!-- Error Count -->
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-600">전체 에러</h3>
            <span class="text-2xl">❌</span>
          </div>
          <p class="text-3xl font-bold text-orange-600">
            {stats.level_distribution.find(l => l.level === 'ERROR')?.count || 0}
          </p>
        </div>

        <!-- Warnings -->
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-600">경고</h3>
            <span class="text-2xl">⚠️</span>
          </div>
          <p class="text-3xl font-bold text-yellow-600">
            {stats.level_distribution.find(l => l.level === 'WARN')?.count || 0}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Level Distribution -->
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">로그 레벨 분포</h3>
          <div class="space-y-3">
            {#each stats.level_distribution as level}
              {@const percentage = (level.count / stats.total_logs) * 100}
              <div>
                <div class="flex items-center justify-between text-sm mb-1">
                  <span class="font-medium text-gray-700">{level.level}</span>
                  <span class="text-gray-600">{level.count.toLocaleString()} ({percentage.toFixed(1)}%)</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div
                    class="h-2 rounded-full {level.level === 'ERROR'
                      ? 'bg-red-600'
                      : level.level === 'WARN'
                        ? 'bg-yellow-500'
                        : level.level === 'INFO'
                          ? 'bg-blue-500'
                          : 'bg-gray-400'}"
                    style="width: {percentage}%"
                  ></div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Service Distribution -->
        <div class="bg-white rounded-lg border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">서비스별 분포</h3>
          <div class="space-y-3">
            {#each stats.service_distribution.slice(0, 10) as service}
              {@const percentage = (service.count / stats.total_logs) * 100}
              <div>
                <div class="flex items-center justify-between text-sm mb-1">
                  <span class="font-medium text-gray-700 truncate">{service.service}</span>
                  <span class="text-gray-600">{service.count.toLocaleString()}</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div
                    class="bg-blue-600 h-2 rounded-full"
                    style="width: {percentage}%"
                  ></div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Info Banner -->
      <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p class="text-sm text-blue-800">
          💡 통계는 30초마다 자동으로 업데이트됩니다. 새로고침 버튼을 클릭하면 수동으로 업데이트할 수 있습니다.
        </p>
      </div>
    {/if}
  </div>
</div>
