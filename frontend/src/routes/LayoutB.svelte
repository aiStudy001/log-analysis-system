<script lang="ts">
  import { link } from 'svelte-spa-router'
</script>

<div class="min-h-screen bg-gray-50">
  <!-- Topbar Navigation -->
  <header class="bg-white border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <div class="flex items-center gap-8">
          <h1 class="text-xl font-bold text-gray-900">Log Analyzer</h1>

          <!-- Navigation Links -->
          <nav class="hidden md:flex items-center gap-1">
            <button class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg">
              Home
            </button>
            <button class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
              Search
            </button>
            <button class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
              Dashboard
            </button>
            <button class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
              History
            </button>
          </nav>
        </div>

        <!-- Right Side Actions -->
        <div class="flex items-center gap-3">
          <a href="/" use:link class="text-sm text-gray-600 hover:text-gray-900">
            ← Back
          </a>
          <button class="p-2 text-gray-500 hover:text-gray-700">⚙️</button>
          <button class="p-2 text-gray-500 hover:text-gray-700">👤</button>
        </div>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Hero Section -->
    <div class="mb-8">
      <h2 class="text-2xl font-bold text-gray-900 mb-2">💬 Ask about your logs</h2>
      <p class="text-gray-600">Natural language queries powered by AI</p>
    </div>

    <!-- Query Input -->
    <div class="mb-8">
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

    <!-- Sample Query Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <button class="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 text-left group">
        <div class="text-2xl mb-2">🔴</div>
        <h3 class="font-medium text-gray-900 group-hover:text-blue-600">Recent Errors</h3>
        <p class="text-sm text-gray-500 mt-1">Last hour</p>
      </button>

      <button class="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 text-left group">
        <div class="text-2xl mb-2">⚡</div>
        <h3 class="font-medium text-gray-900 group-hover:text-blue-600">Slow API Calls</h3>
        <p class="text-sm text-gray-500 mt-1">Performance</p>
      </button>

      <button class="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 text-left group">
        <div class="text-2xl mb-2">👤</div>
        <h3 class="font-medium text-gray-900 group-hover:text-blue-600">User Journey</h3>
        <p class="text-sm text-gray-500 mt-1">Trace user</p>
      </button>

      <button class="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 text-left group">
        <div class="text-2xl mb-2">📊</div>
        <h3 class="font-medium text-gray-900 group-hover:text-blue-600">Trends Analysis</h3>
        <p class="text-sm text-gray-500 mt-1">Time series</p>
      </button>
    </div>

    <div class="border-t border-gray-200 my-8"></div>

    <!-- Mock Results -->
    <div class="space-y-6">
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
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-gray-700">📈 Results</h3>
          <span class="text-sm text-gray-500">42 rows • 45ms</span>
        </div>
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
  </main>
</div>
