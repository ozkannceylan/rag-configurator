<template>
  <div class="space-y-6">
    <h3 class="text-lg font-medium text-gray-900">Prompts</h3>
    <p class="text-sm text-gray-600">
      Customize the prompts used by the RAG agent. Good prompts significantly improve response quality.
    </p>

    <!-- System Prompt -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <label class="block text-sm font-medium text-gray-700">System Prompt</label>
        <div class="flex gap-2">
          <select
            v-model="selectedSystemTemplate"
            class="text-sm border border-gray-300 rounded-md px-2 py-1"
          >
            <option value="">Custom</option>
            <option v-for="(_, key) in systemPromptTemplates" :key="key" :value="key">
              {{ key }}
            </option>
          </select>
          <button
            @click="resetSystemPrompt"
            class="text-xs text-gray-600 hover:text-gray-800"
          >
            Reset
          </button>
        </div>
      </div>
      <p class="text-xs text-gray-500">
        The system prompt sets the behavior and personality of the AI assistant.
      </p>
      <textarea
        v-model="config.prompts.system_prompt"
        rows="6"
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
        placeholder="Enter system prompt..."
      />
      <div class="flex justify-between text-xs text-gray-500">
        <span>{{ systemPromptLength }} characters</span>
        <span v-if="systemPromptLength > 2000" class="text-yellow-600">Long prompt may increase costs</span>
      </div>
    </div>

    <!-- RAG Prompt Template -->
    <div class="space-y-3 pt-4 border-t">
      <div class="flex items-center justify-between">
        <label class="block text-sm font-medium text-gray-700">RAG Prompt Template</label>
        <div class="flex gap-2">
          <select
            v-model="selectedRAGTemplate"
            class="text-sm border border-gray-300 rounded-md px-2 py-1"
          >
            <option value="">Custom</option>
            <option v-for="(_, key) in ragPromptTemplates" :key="key" :value="key">
              {{ key }}
            </option>
          </select>
          <button
            @click="resetRAGPrompt"
            class="text-xs text-gray-600 hover:text-gray-800"
          >
            Reset
          </button>
        </div>
      </div>
      <p class="text-xs text-gray-500">
        Template for formatting context and question. Use <code class="bg-gray-100 px-1 rounded">{context}</code> and <code class="bg-gray-100 px-1 rounded">{query}</code> as placeholders.
      </p>
      <textarea
        v-model="config.prompts.rag_prompt_template"
        rows="8"
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
        placeholder="Enter RAG prompt template..."
      />
      <div class="flex justify-between text-xs text-gray-500">
        <span>{{ ragPromptLength }} characters</span>
        <span :class="hasValidPlaceholders ? 'text-green-600' : 'text-red-600'">
          {{ hasValidPlaceholders ? '✓ Valid placeholders' : '✗ Must include {context} and {query}' }}
        </span>
      </div>
    </div>

    <!-- Preview -->
    <div class="bg-gray-50 rounded-lg p-4 space-y-3">
      <h4 class="font-medium text-gray-900">Preview</h4>
      <p class="text-xs text-gray-600">How the prompt will look with sample context:</p>
      <div class="bg-white border border-gray-200 rounded p-3 font-mono text-xs whitespace-pre-wrap">
        {{ previewPrompt }}
      </div>
    </div>

    <!-- Tips -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h4 class="font-medium text-blue-900 mb-2">💡 Prompt Engineering Tips</h4>
      <ul class="text-sm text-blue-800 space-y-1 list-disc list-inside">
        <li>Be specific about the desired output format</li>
        <li>Include instructions for handling uncertain information</li>
        <li>Add examples if the task is complex</li>
        <li>Use "Answer based ONLY on the provided context" to reduce hallucination</li>
        <li>Keep system prompts under 500 tokens for best results</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

const selectedSystemTemplate = ref('')
const selectedRAGTemplate = ref('')

const systemPromptTemplates: Record<string, string> = {
  'General Assistant': 'You are a helpful AI assistant that answers questions based on the provided context. Be concise, accurate, and helpful.',
  'Technical Expert': 'You are a technical expert. Provide detailed, accurate answers with code examples when relevant. Be precise and thorough.',
  'Legal Analyst': 'You are a legal analyst. Provide careful, nuanced answers based on the documents. Note when information is unclear or requires professional legal review.',
  'Medical Assistant': 'You are a medical information assistant. Provide factual information based on the documents. Always note that this is not medical advice and consult professionals for health decisions.',
  'Research Assistant': 'You are a research assistant. Synthesize information from multiple sources, cite relevant passages, and highlight key findings.',
}

const ragPromptTemplates: Record<string, string> = {
  'Standard': `Context:
{context}

Question: {query}

Answer the question based ONLY on the provided context. If the context doesn't contain the answer, say "I don't have enough information to answer that."`,
  'Cited': `Use the following context to answer the question. Cite specific passages from the context.

Context:
{context}

Question: {query}

Provide your answer with citations to the relevant parts of the context.`,
  'Step-by-Step': `I need you to answer a question based on the provided context. Think step by step.

Context:
{context}

Question: {query}

Step 1: Identify relevant information in the context.
Step 2: Analyze how it answers the question.
Step 3: Formulate your answer.

Answer:`,
  'Concise': `Context: {context}

Q: {query}
A:`,
}

const systemPromptLength = computed(() => config.prompts.system_prompt?.length || 0)
const ragPromptLength = computed(() => config.prompts.rag_prompt_template?.length || 0)

const hasValidPlaceholders = computed(() => {
  const template = config.prompts.rag_prompt_template || ''
  return template.includes('{context}') && template.includes('{query}')
})

const previewPrompt = computed(() => {
  const sampleContext = `[Document 1]: This is a sample document about machine learning. It discusses neural networks and deep learning techniques.

[Document 2]: Another sample text covering data preprocessing and feature engineering for ML models.`
  const sampleQuery = 'What are neural networks?'
  
  return config.prompts.rag_prompt_template
    ?.replace('{context}', sampleContext)
    ?.replace('{query}', sampleQuery) || ''
})

// Watch for template selection
import { watch } from 'vue'

watch(selectedSystemTemplate, (val) => {
  if (val && systemPromptTemplates[val]) {
    config.prompts.system_prompt = systemPromptTemplates[val]
  }
})

watch(selectedRAGTemplate, (val) => {
  if (val && ragPromptTemplates[val]) {
    config.prompts.rag_prompt_template = ragPromptTemplates[val]
  }
})

function resetSystemPrompt() {
  config.prompts.system_prompt = 'You are a helpful assistant that answers questions based on the provided context.'
  selectedSystemTemplate.value = ''
}

function resetRAGPrompt() {
  config.prompts.rag_prompt_template = `Context:
{context}

Question: {query}

Answer:`
  selectedRAGTemplate.value = ''
}
</script>
