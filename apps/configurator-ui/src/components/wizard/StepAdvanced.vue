<template>
  <div class="space-y-8">
    <!-- Guardrails -->
    <div class="space-y-4">
      <h3 class="text-lg font-medium text-gray-900">Guardrails</h3>
      <p class="text-sm text-gray-600">Configure safety checks for queries and responses</p>

      <div class="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-lg">
        <input
          v-model="guardrails.enabled"
          type="checkbox"
          id="guardrailsEnabled"
          class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
        />
        <label for="guardrailsEnabled" class="text-sm text-gray-700">
          <span class="font-medium">Enable Guardrails</span>
          <span class="block text-xs text-gray-500">Apply safety checks to queries and responses</span>
        </label>
      </div>

      <div v-if="guardrails.enabled" class="bg-gray-50 rounded-lg p-4 space-y-3">
        <div class="flex items-center gap-3">
          <input
            v-model="guardrails.prompt_injection"
            type="checkbox"
            id="promptInjection"
            class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
          />
          <label for="promptInjection" class="text-sm text-gray-700">
            <span class="font-medium">Prompt Injection Detection</span>
            <span class="block text-xs text-gray-500">Detect and block prompt injection attempts</span>
          </label>
        </div>

        <div class="flex items-center gap-3">
          <input
            v-model="guardrails.pii"
            type="checkbox"
            id="piiDetection"
            class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
          />
          <label for="piiDetection" class="text-sm text-gray-700">
            <span class="font-medium">PII Detection</span>
            <span class="block text-xs text-gray-500">Detect personally identifiable information</span>
          </label>
        </div>

        <div class="flex items-center gap-3">
          <input
            v-model="guardrails.toxicity"
            type="checkbox"
            id="toxicityDetection"
            class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
          />
          <label for="toxicityDetection" class="text-sm text-gray-700">
            <span class="font-medium">Toxicity Detection</span>
            <span class="block text-xs text-gray-500">Detect toxic or harmful content</span>
          </label>
        </div>

        <div class="pt-2 border-t border-gray-200">
          <div class="flex items-center gap-3">
            <input
              v-model="guardrails.fail_closed"
              type="checkbox"
              id="failClosed"
              class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <label for="failClosed" class="text-sm text-gray-700">
              <span class="font-medium">Fail Closed</span>
              <span class="block text-xs text-gray-500">Block requests on detection (vs. warn only)</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Evaluation -->
    <div class="space-y-4 pt-6 border-t">
      <h3 class="text-lg font-medium text-gray-900">Evaluation</h3>
      <p class="text-sm text-gray-600">Configure RAGAS evaluation metrics for quality monitoring</p>

      <div class="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-lg">
        <input
          v-model="evaluation.enabled"
          type="checkbox"
          id="evalEnabled"
          class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
        />
        <label for="evalEnabled" class="text-sm text-gray-700">
          <span class="font-medium">Enable Evaluation</span>
          <span class="block text-xs text-gray-500">Track faithfulness, relevancy, precision, and recall metrics</span>
        </label>
      </div>

      <div v-if="evaluation.enabled" class="bg-gray-50 rounded-lg p-4 space-y-4">
        <div class="flex items-center gap-3">
          <input
            v-model="evaluation.async_mode"
            type="checkbox"
            id="asyncMode"
            class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
          />
          <label for="asyncMode" class="text-sm text-gray-700">
            <span class="font-medium">Async Mode</span>
            <span class="block text-xs text-gray-500">Run evaluation in the background (recommended for production)</span>
          </label>
        </div>

        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">
            Sample Rate: {{ (evaluation.sample_rate * 100).toFixed(0) }}%
          </label>
          <input
            v-model.number="evaluation.sample_rate"
            type="range"
            min="0"
            max="1"
            step="0.05"
            class="w-full"
          />
          <p class="text-xs text-gray-500">Fraction of queries to evaluate (0% = none, 100% = all)</p>
        </div>
      </div>
    </div>

    <!-- Cache -->
    <div class="space-y-4 pt-6 border-t">
      <h3 class="text-lg font-medium text-gray-900">Caching</h3>
      <p class="text-sm text-gray-600">Configure caching for embeddings and query results</p>

      <div class="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-lg">
        <input
          v-model="cache.enabled"
          type="checkbox"
          id="cacheEnabled"
          class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
        />
        <label for="cacheEnabled" class="text-sm text-gray-700">
          <span class="font-medium">Enable Caching</span>
          <span class="block text-xs text-gray-500">Cache embeddings and query results in Redis</span>
        </label>
      </div>

      <div v-if="cache.enabled" class="bg-gray-50 rounded-lg p-4 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Embedding Cache TTL (seconds)</label>
            <input
              v-model.number="cache.embedding_cache_ttl"
              type="number"
              min="0"
              step="60"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <p class="text-xs text-gray-500">How long to cache computed embeddings (0 = no caching)</p>
          </div>
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Query Cache TTL (seconds)</label>
            <input
              v-model.number="cache.query_cache_ttl"
              type="number"
              min="0"
              step="60"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <p class="text-xs text-gray-500">How long to cache query results (0 = no caching)</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

// Initialize v2 config sections with defaults if not present
if (!config.guardrails) {
  config.guardrails = {
    enabled: false,
    prompt_injection: true,
    pii: true,
    toxicity: true,
    fail_closed: true,
  }
}
if (!config.evaluation) {
  config.evaluation = {
    enabled: false,
    async_mode: true,
    sample_rate: 1.0,
  }
}
if (!config.cache) {
  config.cache = {
    enabled: false,
    embedding_cache_ttl: 3600,
    query_cache_ttl: 300,
  }
}

const guardrails = reactive(config.guardrails)
const evaluation = reactive(config.evaluation)
const cache = reactive(config.cache)

// Sync back to config
watch(guardrails, (val) => { config.guardrails = { ...val } }, { deep: true })
watch(evaluation, (val) => { config.evaluation = { ...val } }, { deep: true })
watch(cache, (val) => { config.cache = { ...val } }, { deep: true })
</script>
