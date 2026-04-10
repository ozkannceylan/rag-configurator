<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-medium text-gray-900">Knowledge Graph Schema</h3>
      <div class="flex items-center gap-2">
        <label class="relative inline-flex items-center cursor-pointer">
          <input
            v-model="config.retrieval.graph.enabled"
            type="checkbox"
            class="sr-only peer"
          />
          <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
          <span class="ml-3 text-sm font-medium text-gray-700">
            {{ config.retrieval.graph.enabled ? 'Enabled' : 'Disabled' }}
          </span>
        </label>
      </div>
    </div>

    <p class="text-sm text-gray-600">
      Knowledge graphs extract entities and relationships from your documents, enabling graph-based retrieval.
      This step will be skipped if graph retrieval is disabled.
    </p>

    <div v-if="config.retrieval.graph.enabled" class="space-y-6">
      <!-- Auto Extract Toggle -->
      <div class="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <input
          v-model="autoExtract"
          type="checkbox"
          id="auto-extract"
          class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
        />
        <label for="auto-extract" class="text-sm text-gray-700">
          <span class="font-medium">Auto-extract entities</span>
          <span class="block text-xs text-gray-500">
            Let the AI automatically identify entities and relationships
          </span>
        </label>
      </div>

      <!-- Node Types -->
      <div class="bg-gray-50 rounded-lg p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h4 class="font-medium text-gray-900">Node Types</h4>
          <button
            @click="addNodeType"
            class="px-3 py-1 bg-primary-600 text-white rounded text-sm font-medium hover:bg-primary-700"
          >
            + Add Node Type
          </button>
        </div>
        <p class="text-sm text-gray-600">Define the types of entities in your knowledge graph</p>

        <div v-if="nodeTypes.length === 0" class="text-center py-4 text-gray-500">
          No node types defined. Add some or enable auto-extract.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="(node, index) in nodeTypes"
            :key="index"
            class="bg-white border border-gray-200 rounded-lg p-3"
          >
            <div class="grid grid-cols-2 gap-3 mb-3">
              <div class="space-y-1">
                <label class="block text-xs font-medium text-gray-700">Name</label>
                <input
                  v-model="node.name"
                  type="text"
                  class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  placeholder="e.g., Person"
                />
              </div>
              <div class="space-y-1">
                <label class="block text-xs font-medium text-gray-700">Description</label>
                <input
                  v-model="node.description"
                  type="text"
                  class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  placeholder="What this entity represents"
                />
              </div>
            </div>

            <!-- Properties -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-gray-700">Properties</span>
                <button
                  @click="addNodeProperty(index)"
                  class="text-xs text-primary-600 hover:text-primary-700"
                >
                  + Add Property
                </button>
              </div>
              <div v-if="node.properties" class="flex flex-wrap gap-2">
                <div
                  v-for="(value, key) in node.properties"
                  :key="key"
                  class="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs"
                >
                  <span>{{ key }}: {{ value }}</span>
                  <button
                    @click="removeNodeProperty(index, key)"
                    class="text-gray-400 hover:text-red-500"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>

            <div class="mt-3 flex justify-end">
              <button
                @click="removeNodeType(index)"
                class="text-xs text-red-600 hover:text-red-700"
              >
                Remove Node Type
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Relation Types -->
      <div class="bg-gray-50 rounded-lg p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h4 class="font-medium text-gray-900">Relation Types</h4>
          <button
            @click="addRelationType"
            class="px-3 py-1 bg-primary-600 text-white rounded text-sm font-medium hover:bg-primary-700"
          >
            + Add Relation Type
          </button>
        </div>
        <p class="text-sm text-gray-600">Define how entities relate to each other</p>

        <div v-if="relationTypes.length === 0" class="text-center py-4 text-gray-500">
          No relation types defined. Add some or enable auto-extract.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="(relation, index) in relationTypes"
            :key="index"
            class="bg-white border border-gray-200 rounded-lg p-3"
          >
            <div class="grid grid-cols-4 gap-3">
              <div class="space-y-1">
                <label class="block text-xs font-medium text-gray-700">Name</label>
                <input
                  v-model="relation.name"
                  type="text"
                  class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  placeholder="e.g., works_for"
                />
              </div>
              <div class="space-y-1">
                <label class="block text-xs font-medium text-gray-700">From</label>
                <select
                  v-model="relation.source_type"
                  class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="">Any</option>
                  <option v-for="node in nodeTypes" :key="node.name" :value="node.name">
                    {{ node.name }}
                  </option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="block text-xs font-medium text-gray-700">To</label>
                <select
                  v-model="relation.target_type"
                  class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="">Any</option>
                  <option v-for="node in nodeTypes" :key="node.name" :value="node.name">
                    {{ node.name }}
                  </option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="block text-xs font-medium text-gray-700">Description</label>
                <input
                  v-model="relation.description"
                  type="text"
                  class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  placeholder="What this relation means"
                />
              </div>
            </div>
            <div class="mt-3 flex justify-end">
              <button
                @click="removeRelationType(index)"
                class="text-xs text-red-600 hover:text-red-700"
              >
                Remove Relation Type
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Example Section -->
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 class="font-medium text-blue-900 mb-2">Example Schema</h4>
        <div class="text-sm text-blue-800 space-y-1">
          <p><strong>Node Types:</strong> Person, Company, Product</p>
          <p><strong>Relations:</strong> Person works_for Company, Company produces Product</p>
        </div>
      </div>
    </div>

    <div v-else class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
      <p class="text-sm text-yellow-800">
        Knowledge graph is disabled. Enable it in the Retrieval step or enable it here to configure the schema.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'
import type { NodeType, RelationType } from '@/types'

const wizardStore = useWizardStore()
const config = wizardStore.config

const autoExtract = computed({
  get: () => config.retrieval.graph_schema?.auto_extract ?? true,
  set: (val) => {
    if (!config.retrieval.graph_schema) {
      config.retrieval.graph_schema = { auto_extract: val, nodes: [], relations: [] }
    } else {
      config.retrieval.graph_schema.auto_extract = val
    }
  }
})

const nodeTypes = computed({
  get: () => config.retrieval.graph_schema?.nodes || [],
  set: (val) => {
    if (!config.retrieval.graph_schema) {
      config.retrieval.graph_schema = { auto_extract: true, nodes: val, relations: [] }
    } else {
      config.retrieval.graph_schema.nodes = val
    }
  }
})

const relationTypes = computed({
  get: () => config.retrieval.graph_schema?.relations || [],
  set: (val) => {
    if (!config.retrieval.graph_schema) {
      config.retrieval.graph_schema = { auto_extract: true, nodes: [], relations: val }
    } else {
      config.retrieval.graph_schema.relations = val
    }
  }
})

function addNodeType() {
  const newNode: NodeType = {
    name: '',
    description: '',
    properties: {}
  }
  nodeTypes.value = [...nodeTypes.value, newNode]
}

function removeNodeType(index: number) {
  const nodes = [...nodeTypes.value]
  nodes.splice(index, 1)
  nodeTypes.value = nodes
}

function addNodeProperty(nodeIndex: number) {
  const key = prompt('Property name:')
  if (!key) return
  const value = prompt('Property type (string, number, boolean):') || 'string'
  
  const nodes = [...nodeTypes.value]
  if (!nodes[nodeIndex].properties) {
    nodes[nodeIndex].properties = {}
  }
  nodes[nodeIndex].properties![key] = value
  nodeTypes.value = nodes
}

function removeNodeProperty(nodeIndex: number, key: string) {
  const nodes = [...nodeTypes.value]
  if (nodes[nodeIndex].properties) {
    delete nodes[nodeIndex].properties![key]
  }
  nodeTypes.value = nodes
}

function addRelationType() {
  const newRelation: RelationType = {
    name: '',
    source_type: '',
    target_type: '',
    description: ''
  }
  relationTypes.value = [...relationTypes.value, newRelation]
}

function removeRelationType(index: number) {
  const relations = [...relationTypes.value]
  relations.splice(index, 1)
  relationTypes.value = relations
}
</script>
