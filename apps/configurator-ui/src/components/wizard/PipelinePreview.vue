<template>
  <div class="bg-white border border-gray-200 rounded-lg p-4">
    <h4 class="font-medium text-gray-900 mb-4">Pipeline Architecture</h4>
    
    <div class="flex flex-col items-center space-y-4">
      <!-- Data Source -->
      <PipelineNode
        icon="📁"
        title="Data Source"
        :subtitle="dataSourceSubtitle"
        color="blue"
      />
      
      <ArrowDown />
      
      <!-- Ingestion -->
      <PipelineNode
        icon="⚙️"
        title="Ingestion"
        :subtitle="ingestionSubtitle"
        color="purple"
      />
      
      <ArrowDown />
      
      <!-- Storage -->
      <div class="flex gap-4">
        <PipelineNode
          icon="💾"
          title="Vector Store"
          subtitle="MongoDB Atlas"
          color="green"
          small
        />
        <PipelineNode
          v-if="showGraph"
          icon="🕸️"
          title="Graph Store"
          subtitle="Knowledge Graph"
          color="orange"
          small
        />
      </div>
      
      <ArrowDown />
      
      <!-- Retrieval -->
      <PipelineNode
        icon="🔍"
        title="Retrieval"
        :subtitle="retrievalSubtitle"
        color="yellow"
      />
      
      <ArrowDown />
      
      <!-- Agent -->
      <PipelineNode
        icon="🤖"
        title="Agent"
        :subtitle="agentSubtitle"
        color="red"
      />
      
      <ArrowDown />
      
      <!-- Output -->
      <PipelineNode
        icon="💬"
        title="Response"
        :subtitle="streamingSubtitle"
        color="gray"
      />
    </div>
    
    <!-- Configuration Summary -->
    <div class="mt-6 pt-4 border-t border-gray-200">
      <h5 class="text-sm font-medium text-gray-700 mb-2">Quick Stats</h5>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="bg-gray-50 p-2 rounded">
          <span class="text-gray-500">Chunking:</span>
          <span class="ml-1 font-medium">{{ config.chunking?.strategy }} ({{ config.chunking?.chunk_size }} tokens)</span>
        </div>
        <div class="bg-gray-50 p-2 rounded">
          <span class="text-gray-500">Embedding:</span>
          <span class="ml-1 font-medium">{{ config.models?.embedding?.provider }}</span>
        </div>
        <div class="bg-gray-50 p-2 rounded">
          <span class="text-gray-500">LLM:</span>
          <span class="ml-1 font-medium">{{ config.models?.llm?.provider }}</span>
        </div>
        <div class="bg-gray-50 p-2 rounded">
          <span class="text-gray-500">Retrieval:</span>
          <span class="ml-1 font-medium">{{ config.retrieval?.method }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

const showGraph = computed(() => config.retrieval?.graph?.enabled)

const dataSourceSubtitle = computed(() => {
  const type = config.data_source?.type || 'local'
  const folders = config.data_source?.folders?.length || 0
  return `${type === 'local' ? 'Local' : 'S3'} • ${folders} folder${folders !== 1 ? 's' : ''}`
})

const ingestionSubtitle = computed(() => {
  const types = config.data_source?.folders?.[0]?.file_patterns?.join(', ') || 'All files'
  return `Processing ${types}`
})

const retrievalSubtitle = computed(() => {
  const method = config.retrieval?.method || 'naive'
  const topK = config.retrieval?.vector?.top_k || 5
  return `${method} • Top ${topK}`
})

const agentSubtitle = computed(() => {
  const template = config.agent?.template || 'naive'
  const maxIter = config.agent?.max_iterations || 5
  return `${template} • Max ${maxIter} iterations`
})

const streamingSubtitle = computed(() => {
  return config.agent?.enable_judge ? 'LLM-as-Judge enabled' : 'Standard evaluation'
})
</script>

<script lang="ts">
// Sub-components
import { h } from 'vue'

interface PipelineNodeProps {
  icon?: string
  title?: string
  subtitle?: string
  color?: string
  small?: boolean
}

const PipelineNode = {
  props: ['icon', 'title', 'subtitle', 'color', 'small'],
  setup(props: PipelineNodeProps) {
    const colorClasses: Record<string, string> = {
      blue: 'bg-blue-100 border-blue-300 text-blue-800',
      purple: 'bg-purple-100 border-purple-300 text-purple-800',
      green: 'bg-green-100 border-green-300 text-green-800',
      orange: 'bg-orange-100 border-orange-300 text-orange-800',
      yellow: 'bg-yellow-100 border-yellow-300 text-yellow-800',
      red: 'bg-red-100 border-red-300 text-red-800',
      gray: 'bg-gray-100 border-gray-300 text-gray-800',
    }
    
    return () => h('div', {
      class: [
        'flex items-center gap-3 px-4 py-3 rounded-lg border-2 min-w-[200px]',
        (props.color && colorClasses[props.color]) || colorClasses.gray,
        props.small ? 'scale-90' : ''
      ]
    }, [
      h('span', { class: 'text-2xl' }, props.icon),
      h('div', { class: 'text-left' }, [
        h('div', { class: 'font-medium' }, props.title),
        h('div', { class: 'text-xs opacity-75' }, props.subtitle)
      ])
    ])
  }
}

const ArrowDown = {
  setup() {
    return () => h('div', { class: 'text-gray-400' }, '↓')
  }
}
</script>
