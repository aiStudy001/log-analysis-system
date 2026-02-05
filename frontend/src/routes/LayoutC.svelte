<script lang="ts">
  import { link } from 'svelte-spa-router'
</script>

<div class="flex flex-col h-screen bg-gray-50">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-4">
      <h1 class="text-xl font-bold text-gray-900">Log Analysis System</h1>
      <span class="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">Chat Mode</span>
    </div>
    <div class="flex items-center gap-3">
      <a href="/" use:link class="text-sm text-gray-600 hover:text-gray-900">← Back</a>
      <button class="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded">Dashboard</button>
      <button class="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded">History</button>
      <button class="p-2 text-gray-500 hover:text-gray-700">👤</button>
    </div>
  </header>

  <!-- Chat Container -->
  <div class="flex-1 overflow-hidden flex flex-col max-w-5xl mx-auto w-full">
    <!-- Chat Messages -->
    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <!-- User Message -->
      <div class="flex justify-end">
        <div class="max-w-2xl">
          <div class="bg-blue-600 text-white rounded-lg px-4 py-3">
            <p class="text-sm">최근 1시간 에러 로그</p>
          </div>
          <p class="text-xs text-gray-500 mt-1 text-right">👤 You • 14:23</p>
        </div>
      </div>

      <!-- AI Response -->
      <div class="flex justify-start">
        <div class="max-w-3xl w-full">
          <div class="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <!-- Generated SQL -->
            <div class="mb-4">
              <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">Generated SQL</h3>
              <div class="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs">
                SELECT * FROM logs<br/>
                WHERE level = 'ERROR'<br/>
                AND created_at > NOW() - INTERVAL '1 hour'<br/>
                AND deleted = FALSE
              </div>
            </div>

            <!-- Results Summary -->
            <div class="mb-4">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs font-semibold text-gray-500 uppercase">Results</h3>
                <span class="text-xs text-gray-500">42 rows • 45ms</span>
              </div>
              <div class="bg-gray-50 rounded border border-gray-200 overflow-hidden">
                <div class="overflow-x-auto">
                  <table class="w-full text-xs">
                    <thead class="bg-gray-100">
                      <tr>
                        <th class="px-3 py-2 text-left font-medium text-gray-700">Time</th>
                        <th class="px-3 py-2 text-left font-medium text-gray-700">Service</th>
                        <th class="px-3 py-2 text-left font-medium text-gray-700">Message</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                      <tr>
                        <td class="px-3 py-2 text-gray-600">14:23:01</td>
                        <td class="px-3 py-2 text-gray-900">payment-api</td>
                        <td class="px-3 py-2 text-gray-600">Timeout error</td>
                      </tr>
                      <tr>
                        <td class="px-3 py-2 text-gray-600">14:22:58</td>
                        <td class="px-3 py-2 text-gray-900">user-api</td>
                        <td class="px-3 py-2 text-gray-600">DB connection failed</td>
                      </tr>
                      <tr>
                        <td class="px-3 py-2 text-gray-600">14:22:45</td>
                        <td class="px-3 py-2 text-gray-900">order-api</td>
                        <td class="px-3 py-2 text-gray-600">Validation error</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <button class="w-full py-2 text-xs text-blue-600 hover:bg-blue-50 border-t border-gray-200">
                  Show all 42 rows →
                </button>
              </div>
            </div>

            <!-- AI Insight -->
            <div class="bg-blue-50 border border-blue-200 rounded p-4">
              <div class="flex items-start gap-2">
                <span class="text-lg">💡</span>
                <div>
                  <h4 class="text-xs font-semibold text-blue-900 mb-1">AI Insight</h4>
                  <p class="text-sm text-blue-800">
                    최근 1시간 동안 42건의 에러가 발생했습니다. payment-api에서 가장 많은 에러가 발생하고 있으며,
                    주로 타임아웃 관련 문제입니다. 즉시 조치가 필요할 수 있습니다.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <p class="text-xs text-gray-500 mt-1">🤖 AI • 14:23</p>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="border-t border-gray-200 bg-white p-4">
      <div class="max-w-3xl mx-auto">
        <!-- Sample Suggestions -->
        <div class="flex gap-2 mb-3 overflow-x-auto">
          <button class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 whitespace-nowrap">
            🔴 Recent Errors
          </button>
          <button class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 whitespace-nowrap">
            ⚡ Slow APIs
          </button>
          <button class="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 whitespace-nowrap">
            👤 User Journey
          </button>
        </div>

        <!-- Input Box -->
        <div class="flex gap-3">
          <input
            type="text"
            placeholder="Type your question..."
            class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
            Send
          </button>
        </div>
      </div>
    </div>
  </div>
</div>
