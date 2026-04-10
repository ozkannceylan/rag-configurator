<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <router-link to="/" class="text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </router-link>
        <h1 class="text-xl font-bold text-gray-900">Evaluation Dashboard</h1>
      </div>
      <button
        @click="handleLogout"
        class="px-3 py-1.5 text-sm text-red-600 hover:text-red-700"
      >
        Logout
      </button>
    </header>

    <!-- Config Selector + Run -->
    <div class="bg-white border-b border-gray-200 px-6 py-4">
      <div class="max-w-5xl mx-auto flex items-end gap-4">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 mb-1">Configuration</label>
          <select
            v-model="selectedConfigId"
            class="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="" disabled>Select a configuration</option>
            <option
              v-for="config in readyConfigs"
              :key="config.id"
              :value="config.id"
            >
              {{ config.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Last N Queries</label>
          <input
            v-model.number="queryCount"
            type="number"
            min="1"
            max="100"
            class="w-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <button
          @click="runEvaluation"
          :disabled="!selectedConfigId || isRunning"
          class="px-6 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ isRunning ? 'Running...' : 'Run Evaluation' }}
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-auto">
      <div class="max-w-5xl mx-auto py-6 px-4 space-y-6">
        <!-- Summary Cards -->
        <div v-if="evaluations.length > 0" class="grid grid-cols-5 gap-4">
          <div
            v-for="metric in metricSummaries"
            :key="metric.name"
            class="bg-white rounded-lg border border-gray-200 p-4 text-center"
          >
            <p class="text-xs text-gray-500 mb-1">{{ metric.label }}</p>
            <p
              class="text-2xl font-bold"
              :class="scoreColorClass(metric.value)"
            >
              {{ metric.value !== null ? (metric.value * 100).toFixed(1) + '%' : '--' }}
            </p>
          </div>
        </div>

        <!-- Evaluation History Table -->
        <div v-if="evaluations.length > 0" class="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div class="px-4 py-3 border-b border-gray-200">
            <h2 class="text-sm font-semibold text-gray-900">Evaluation History</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Faithfulness</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Answer Relevancy</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Context Precision</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Context Recall</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Average</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <template v-for="(evalRun, idx) in evaluations" :key="idx">
                  <tr
                    class="hover:bg-gray-50 cursor-pointer"
                    @click="toggleRow(idx)"
                  >
                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                      <div class="flex items-center gap-2">
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          class="w-3 h-3 text-gray-400 transition-transform"
                          :class="{ 'rotate-90': expandedRows.has(idx) }"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                        >
                          <path d="M9 18l6-6-6-6" />
                        </svg>
                        {{ formatDate(evalRun.date) }}
                      </div>
                    </td>
                    <td class="px-4 py-2 text-center text-sm" :class="scoreColorClass(evalRun.faithfulness)">
                      {{ formatScore(evalRun.faithfulness) }}
                    </td>
                    <td class="px-4 py-2 text-center text-sm" :class="scoreColorClass(evalRun.answer_relevancy)">
                      {{ formatScore(evalRun.answer_relevancy) }}
                    </td>
                    <td class="px-4 py-2 text-center text-sm" :class="scoreColorClass(evalRun.context_precision)">
                      {{ formatScore(evalRun.context_precision) }}
                    </td>
                    <td class="px-4 py-2 text-center text-sm" :class="scoreColorClass(evalRun.context_recall)">
                      {{ formatScore(evalRun.context_recall) }}
                    </td>
                    <td class="px-4 py-2 text-center text-sm font-semibold" :class="scoreColorClass(evalRun.average)">
                      {{ formatScore(evalRun.average) }}
                    </td>
                  </tr>
                  <!-- Expanded per-query breakdown -->
                  <tr v-if="expandedRows.has(idx) && evalRun.queries">
                    <td colspan="6" class="px-4 py-2 bg-gray-50">
                      <div class="text-xs font-medium text-gray-500 mb-2">Per-Query Breakdown</div>
                      <table class="min-w-full text-xs">
                        <thead>
                          <tr>
                            <th class="text-left py-1 px-2 text-gray-500">Query</th>
                            <th class="text-center py-1 px-2 text-gray-500">Faith.</th>
                            <th class="text-center py-1 px-2 text-gray-500">Relev.</th>
                            <th class="text-center py-1 px-2 text-gray-500">Prec.</th>
                            <th class="text-center py-1 px-2 text-gray-500">Recall</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr
                            v-for="(q, qIdx) in evalRun.queries"
                            :key="qIdx"
                            class="border-t border-gray-100"
                          >
                            <td class="py-1 px-2 text-gray-700 max-w-xs truncate" :title="q.query">
                              {{ q.query }}
                            </td>
                            <td class="py-1 px-2 text-center" :class="scoreColorClass(q.faithfulness)">
                              {{ formatScore(q.faithfulness) }}
                            </td>
                            <td class="py-1 px-2 text-center" :class="scoreColorClass(q.answer_relevancy)">
                              {{ formatScore(q.answer_relevancy) }}
                            </td>
                            <td class="py-1 px-2 text-center" :class="scoreColorClass(q.context_precision)">
                              {{ formatScore(q.context_precision) }}
                            </td>
                            <td class="py-1 px-2 text-center" :class="scoreColorClass(q.context_recall)">
                              {{ formatScore(q.context_recall) }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="!isRunning && evaluations.length === 0" class="text-center py-16">
          <div class="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-gray-900">No evaluations yet</h3>
          <p class="text-sm text-gray-500 mt-1">
            Select a configuration and run an evaluation to see RAGAS scores.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import apiClient from '@/api/client'

interface QueryScore {
  query: string
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
}

interface EvaluationRun {
  date: string
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
  average: number
  queries?: QueryScore[]
}

const router = useRouter()
const authStore = useAuthStore()
const configStore = useConfigStore()

const selectedConfigId = ref('')
const queryCount = ref(10)
const isRunning = ref(false)
const evaluations = ref<EvaluationRun[]>([])
const expandedRows = ref<Set<number>>(new Set())

const readyConfigs = computed(() =>
  configStore.configs.filter(
    (c) => c.status === 'ready' || c.status === 'completed' || c.status === undefined
  )
)

const metricSummaries = computed(() => {
  if (evaluations.value.length === 0) return []

  const metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'average'] as const
  const labels: Record<string, string> = {
    faithfulness: 'Faithfulness',
    answer_relevancy: 'Answer Relevancy',
    context_precision: 'Context Precision',
    context_recall: 'Context Recall',
    average: 'Average',
  }

  return metrics.map((m) => {
    const values = evaluations.value.map((e) => e[m]).filter((v) => v != null)
    const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null
    return { name: m, label: labels[m], value: avg }
  })
})

onMounted(() => {
  configStore.fetchConfigs()
})

async function runEvaluation() {
  if (!selectedConfigId.value || isRunning.value) return

  isRunning.value = true
  try {
    const response = await apiClient.post('/v1/evaluate', {
      config_id: selectedConfigId.value,
      last_n: queryCount.value,
    })

    const data = response.data

    // Handle the response - whether the backend returns a full evaluation or individual scores
    if (data.scores || data.results) {
      const scores = data.scores || data.results
      const queryScores: QueryScore[] = Array.isArray(scores)
        ? scores.map((s: any) => ({
            query: s.query || s.question || '',
            faithfulness: s.faithfulness ?? 0,
            answer_relevancy: s.answer_relevancy ?? 0,
            context_precision: s.context_precision ?? 0,
            context_recall: s.context_recall ?? 0,
          }))
        : []

      const avgMetric = (key: keyof QueryScore) => {
        if (key === 'query') return 0
        const vals = queryScores.map((q) => q[key] as number).filter((v) => v != null)
        return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0
      }

      const faith = data.faithfulness ?? avgMetric('faithfulness')
      const relev = data.answer_relevancy ?? avgMetric('answer_relevancy')
      const prec = data.context_precision ?? avgMetric('context_precision')
      const rec = data.context_recall ?? avgMetric('context_recall')

      const evalRun: EvaluationRun = {
        date: new Date().toISOString(),
        faithfulness: faith,
        answer_relevancy: relev,
        context_precision: prec,
        context_recall: rec,
        average: (faith + relev + prec + rec) / 4,
        queries: queryScores.length > 0 ? queryScores : undefined,
      }

      evaluations.value.unshift(evalRun)
    } else {
      // Fallback: API returned aggregate scores directly
      const faith = data.faithfulness ?? 0
      const relev = data.answer_relevancy ?? 0
      const prec = data.context_precision ?? 0
      const rec = data.context_recall ?? 0

      evaluations.value.unshift({
        date: new Date().toISOString(),
        faithfulness: faith,
        answer_relevancy: relev,
        context_precision: prec,
        context_recall: rec,
        average: (faith + relev + prec + rec) / 4,
      })
    }
  } catch (err: any) {
    // If the evaluation endpoint doesn't exist yet, show a mock result
    console.error('Evaluation request failed:', err)

    evaluations.value.unshift({
      date: new Date().toISOString(),
      faithfulness: 0,
      answer_relevancy: 0,
      context_precision: 0,
      context_recall: 0,
      average: 0,
      queries: [],
    })
  } finally {
    isRunning.value = false
  }
}

function toggleRow(idx: number) {
  if (expandedRows.value.has(idx)) {
    expandedRows.value.delete(idx)
  } else {
    expandedRows.value.add(idx)
  }
  expandedRows.value = new Set(expandedRows.value)
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatScore(value: number | null | undefined): string {
  if (value == null) return '--'
  return (value * 100).toFixed(1) + '%'
}

function scoreColorClass(value: number | null | undefined): string {
  if (value == null) return 'text-gray-400'
  if (value >= 0.7) return 'text-green-600'
  if (value >= 0.4) return 'text-yellow-600'
  return 'text-red-600'
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>
