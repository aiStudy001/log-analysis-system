<script lang="ts">
  import { link } from 'svelte-spa-router'
</script>

<div class="flex h-screen bg-gray-50">
  <!-- Sidebar -->
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col">
    <!-- Logo -->
    <div class="p-6 border-b border-gray-200">
      <h1 class="text-xl font-bold text-gray-900">Log Analyzer</h1>
      <p class="text-sm text-gray-500 mt-1">Dashboard Layout</p>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 p-4 space-y-1">
      <button class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-white bg-blue-600 rounded-lg">
        🏠 Home
      </button>
      <button class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
        🔍 Search
      </button>
      <button class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
        📊 Dashboard
      </button>
      <button class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
        📜 History
      </button>
    </nav>

    <!-- Sample Queries Section -->
    <div class="p-4 border-t border-gray-200">
      <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Sample Queries</h3>
      <div class="space-y-2">
        <button class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded">
          🔴 Recent Errors
        </button>
        <button class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded">
          ⚡ Slow APIs
        </button>
        <button class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded">
          👤 User Journey
        </button>
      </div>
    </div>

    <!-- Back Button -->
    <div class="p-4 border-t border-gray-200">
      <a href="/" use:link class="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg">
        ← Back to Selection
      </a>
    </div>
  </aside>

  <!-- Main Content -->
  <main class="flex-1 overflow-auto">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">Ask about your logs</h2>
      <div class="flex items-center gap-4">
        <button class="p-2 text-gray-500 hover:text-gray-700">⚙️</button>
        <button class="p-2 text-gray-500 hover:text-gray-700">👤 Dev</button>
      </div>
    </header>

    <!-- Content -->
    <div class="p-6">
      <!-- Query Input -->
      <div class="max-w-4xl mx-auto mb-8">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div class="flex gap-3">
            <input
              type="text"
              placeholder="Type your question... (e.g., '최근 1시간 에러 로그')"
              class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
              Send
            </button>
          </div>
        </div>
      </div>

      <!-- Mock Results -->
      <div class="max-w-4xl mx-auto space-y-6">
        <!-- SQL Display -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">📊 Generated SQL</h3>
          <div class="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm">
            SELECT * FROM logs<br/>
            WHERE level = 'ERROR'<br/>
            AND created_at > NOW() - INTERVAL '1 hour'<br/>
            AND deleted = FALSE
          </div>
        </div>

        <!-- Results Table -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">📈 Results (42 rows, 45ms)</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-3 text-left font-medium text-gray-700">Time</th>
                  <th class="px-4 py-3 text-left font-medium text-gray-700">Service</th>
                  <th class="px-4 py-3 text-left font-medium text-gray-700">Message</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-3 text-gray-600">14:23:01</td>
                  <td class="px-4 py-3 text-gray-900">payment-api</td>
                  <td class="px-4 py-3 text-gray-600">Timeout error</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-3 text-gray-600">14:22:58</td>
                  <td class="px-4 py-3 text-gray-900">user-api</td>
                  <td class="px-4 py-3 text-gray-600">DB connection failed</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-3 text-gray-600">14:22:45</td>
                  <td class="px-4 py-3 text-gray-900">order-api</td>
                  <td class="px-4 py-3 text-gray-600">Validation error</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- AI Insight -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 class="text-sm font-semibold text-blue-900 mb-2">💡 AI Insight</h3>
          <p class="text-blue-800">
            최근 1시간 동안 42건의 에러가 발생했습니다. payment-api에서 가장 많은 에러가 발생하고 있으며,
            주로 타임아웃 관련 문제입니다. 즉시 조치가 필요할 수 있습니다.
          </p>
        </div>
      </div>
    </div>
  </main>
</div>
