<template>
  <div class="space-y-6">
    <h3 class="text-lg font-medium text-gray-900">Agent Template</h3>
    <p class="text-sm text-gray-600">
      Choose an agent architecture that determines how the RAG pipeline processes queries and retrieves information.
    </p>

    <!-- Agent Templates Grid -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <button
        v-for="template in agentTemplates"
        :key="template.id"
        @click="selectTemplate(template.id)"
        :class="[
          'p-4 border-2 rounded-lg text-left transition-all',
          config.agent.template === template.id
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-200 hover:border-gray-300'
        ]"
      >
        <div class="text-2xl mb-2">{{ template.icon }}</div>
        <div class="font-medium text-gray-900">{{ template.name }}</div>
        <div class="text-xs text-gray-500 mt-1">{{ template.description }}</div>
      </button>
    </div>

    <!-- Selected Template Details -->
    <div v-if="selectedTemplate" class="bg-gray-50 rounded-lg p-4 space-y-3">
      <h4 class="font-medium text-gray-900">{{ selectedTemplate.name }} Details</h4>
      <p class="text-sm text-gray-600">{{ selectedTemplate.longDescription }}</p>
      
      <div class="space-y-2">
        <h5 class="text-sm font-medium text-gray-700">Best for:</h5>
        <ul class="text-sm text-gray-600 list-disc list-inside">
          <li v-for="use in selectedTemplate.bestFor" :key="use">{{ use }}</li>
        </ul>
      </div>
    </div>

    <!-- Agent Settings -->
    <div class="space-y-4 pt-4 border-t">
      <h4 class="font-medium text-gray-900">Agent Settings</h4>

      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">
            Max Iterations: {{ config.agent.max_iterations }}
          </label>
          <input
            v-model.number="config.agent.max_iterations"
            type="range"
            min="1"
            max="10"
            step="1"
            class="w-full"
          />
          <p class="text-xs text-gray-500">Maximum reasoning steps (for ReAct, CRAG, etc.)</p>
        </div>

        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">
            Temperature Override (Optional)
          </label>
          <input
            v-model.number="config.agent.temperature_override"
            type="number"
            min="0"
            max="2"
            step="0.1"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Use default"
          />
          <p class="text-xs text-gray-500">Override LLM temperature for this agent</p>
        </div>
      </div>

      <div class="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg">
        <input
          v-model="config.agent.enable_judge"
          type="checkbox"
          id="enableJudge"
          class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
        />
        <label for="enableJudge" class="text-sm text-gray-700">
          <span class="font-medium">Enable LLM-as-Judge evaluation</span>
          <span class="block text-xs text-gray-500">
            Use a separate LLM to evaluate answer quality
          </span>
        </label>
      </div>
    </div>

    <!-- Template-Specific Config -->
    <div v-if="templateConfigFields.length > 0" class="space-y-4 pt-4 border-t">
      <h4 class="font-medium text-gray-900">{{ selectedTemplate?.name }} Options</h4>
      <div v-for="field in templateConfigFields" :key="field.key" class="space-y-2">
        <label class="block text-sm font-medium text-gray-700">{{ field.label }}</label>
        <p class="text-xs text-gray-500">{{ field.description }}</p>
        <input
          v-if="field.type === 'number'"
          v-model.number="config.agent.config[field.key]"
          type="number"
          class="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
        <input
          v-else-if="field.type === 'boolean'"
          v-model="config.agent.config[field.key]"
          type="checkbox"
          class="w-4 h-4 text-primary-600 rounded"
        />
        <input
          v-else
          v-model="config.agent.config[field.key]"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'
import type { AgentConfig } from '@/types'

const wizardStore = useWizardStore()
const config = wizardStore.config

// Ensure agent.config object exists (may be undefined when loading saved configs)
if (!config.agent.config) {
  config.agent.config = {}
}

interface ConfigField {
  key: string
  label: string
  description: string
  type: string
  default?: string | number | boolean
}

interface AgentTemplate {
  id: AgentConfig['template']
  name: string
  icon: string
  description: string
  longDescription: string
  bestFor: string[]
  configFields?: ConfigField[]
}

const agentTemplates: AgentTemplate[] = [
  {
    id: 'naive_rag',
    name: 'Naive RAG',
    icon: '📄',
    description: 'Simple retrieve-then-generate',
    longDescription: 'The simplest RAG approach: retrieve relevant chunks and generate an answer in a single pass. Fast but may miss nuanced information.',
    bestFor: ['Quick Q&A', 'Simple documents', 'Low latency requirements']
  },
  {
    id: 'react',
    name: 'ReAct',
    icon: '🤔',
    description: 'Reasoning + Acting with tools',
    longDescription: 'Combines reasoning (Chain-of-Thought) with action-taking. The agent thinks about what it needs, takes actions (like retrieval), and repeats until it has enough information.',
    bestFor: ['Complex queries', 'Multi-hop questions', 'When reasoning matters'],
    configFields: [
      { key: 'tool_names', label: 'Available Tools', description: 'Comma-separated tool names', type: 'text', default: '' }
    ]
  },
  {
    id: 'crag',
    name: 'CRAG',
    icon: '✅',
    description: 'Corrective RAG with self-evaluation',
    longDescription: 'Corrective RAG evaluates retrieved documents and decides whether to use them, supplement them with web search, or regenerate the query.',
    bestFor: ['When document quality varies', 'Self-correcting systems', 'High accuracy needs'],
    configFields: [
      { key: 'confidence_threshold', label: 'Confidence Threshold', description: 'Minimum confidence to accept retrieval (0-1)', type: 'number', default: 0.7 }
    ]
  },
  {
    id: 'self_rag',
    name: 'Self-RAG',
    icon: '🔍',
    description: 'Self-reflective with critique',
    longDescription: 'Self-RAG generates multiple candidate answers and critiques them, selecting the best one or regenerating if needed.',
    bestFor: ['High-stakes answers', 'When hallucination is costly', 'Quality-first scenarios'],
    configFields: [
      { key: 'num_candidates', label: 'Number of Candidates', description: 'How many answers to generate', type: 'number', default: 3 },
      { key: 'use_citation', label: 'Enable Citations', description: 'Add citations to sources', type: 'boolean', default: true }
    ]
  },
  {
    id: 'multi_query',
    name: 'Multi-Query',
    icon: '🔄',
    description: 'Query expansion with RRF',
    longDescription: 'Generates multiple variations of the user query, retrieves for each, and uses Reciprocal Rank Fusion to combine results.',
    bestFor: ['Ambiguous queries', 'Broad information needs', 'Comprehensive retrieval'],
    configFields: [
      { key: 'num_queries', label: 'Number of Queries', description: 'How many query variations to generate', type: 'number', default: 3 },
      { key: 'use_rrf', label: 'Use RRF', description: 'Use Reciprocal Rank Fusion', type: 'boolean', default: true }
    ]
  },
  {
    id: 'plan_solve',
    name: 'Plan-Solve',
    icon: '📋',
    description: 'Planning-based decomposition',
    longDescription: 'Breaks complex queries into a plan of sub-queries, executes each step, and synthesizes the final answer.',
    bestFor: ['Complex multi-part questions', 'Research tasks', 'Analytical queries'],
    configFields: [
      { key: 'plan_depth', label: 'Plan Depth', description: 'Maximum planning depth', type: 'number', default: 3 }
    ]
  },
  {
    id: 'adaptive_rag',
    name: 'Adaptive RAG',
    icon: '🎯',
    description: 'Adapts strategy based on query complexity',
    longDescription: 'Analyzes each query to determine the best retrieval and generation strategy. Routes simple questions to fast paths and complex questions to multi-step reasoning.',
    bestFor: ['Mixed query complexity', 'Production systems', 'Balanced latency/quality'],
    configFields: [
      { key: 'complexity_threshold', label: 'Complexity Threshold', description: 'Score above which to use advanced retrieval (0-1)', type: 'number', default: 0.5 }
    ]
  },
  {
    id: 'agentic_rag',
    name: 'Agentic RAG',
    icon: '🤖',
    description: 'Autonomous agent with tool use',
    longDescription: 'A fully autonomous agent that can use multiple tools including search, calculation, and code execution to answer queries. Supports multi-turn tool interactions.',
    bestFor: ['Complex research tasks', 'Multi-tool workflows', 'Autonomous operation'],
    configFields: [
      { key: 'available_tools', label: 'Available Tools', description: 'Comma-separated list of tools to enable', type: 'text', default: '' },
      { key: 'allow_code_execution', label: 'Allow Code Execution', description: 'Enable code execution tool', type: 'boolean', default: false }
    ]
  },
  {
    id: 'graph_rag',
    name: 'Graph RAG',
    icon: '🕸️',
    description: 'Knowledge graph-based retrieval',
    longDescription: 'Uses a knowledge graph to find relevant entities and relationships, then combines graph context with vector retrieval for rich, structured answers.',
    bestFor: ['Entity-rich domains', 'Relationship queries', 'Structured knowledge bases'],
    configFields: [
      { key: 'graph_traversal_depth', label: 'Traversal Depth', description: 'Max hops in the knowledge graph', type: 'number', default: 2 },
      { key: 'community_detection', label: 'Use Community Detection', description: 'Group related entities', type: 'boolean', default: false }
    ]
  }
]

const selectedTemplate = computed(() => {
  return agentTemplates.find(t => t.id === config.agent.template)
})

const templateConfigFields = computed(() => {
  return selectedTemplate.value?.configFields || []
})

function selectTemplate(templateId: AgentConfig['template']) {
  config.agent.template = templateId
  
  // Initialize config object if it has fields
  const template = agentTemplates.find(t => t.id === templateId)
  if (template?.configFields) {
    if (!config.agent.config) config.agent.config = {}
    template.configFields.forEach(field => {
      if (field.default !== undefined) {
        config.agent.config![field.key] = field.default
      } else if (field.type === 'number') {
        config.agent.config![field.key] = 0
      } else if (field.type === 'boolean') {
        config.agent.config![field.key] = false
      } else {
        config.agent.config![field.key] = ''
      }
    })
  }
}
</script>
