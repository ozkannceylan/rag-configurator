<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NTag, NProgress, NSpace, NText, NEmpty, NButton, NIcon } from 'naive-ui'
import { ChevronDown, ChevronUp } from '@vicons/ionicons5'
import { useChatStore } from '@/stores/chat'
import type { Source } from '@/types'

const chatStore = useChatStore()

const expandedChunks = ref<Set<number>>(new Set())

const sortedSources = computed(() => {
  return [...chatStore.currentSources].sort((a, b) => b.score - a.score)
})

const hasSources = computed(() => chatStore.currentSources.length > 0)

const agentSteps = computed(() => {
  return chatStore.currentSteps.filter(
    (s) => s.metadata?.type === 'reasoning' || s.metadata?.type === 'decision' || s.name.toLowerCase().includes('reason') || s.name.toLowerCase().includes('decide')
  )
})

const hasAgentSteps = computed(() => agentSteps.value.length > 0)

function scoreColor(score: number): string {
  if (score >= 0.7) return '#18a058'
  if (score >= 0.4) return '#f0a020'
  return '#d03050'
}

function scoreBarColor(score: number): string {
  if (score >= 0.7) return 'success'
  if (score >= 0.4) return 'warning'
  return 'error'
}

function scoreLabel(score: number): string {
  if (score >= 0.7) return 'High'
  if (score >= 0.4) return 'Medium'
  return 'Low'
}

function toggleChunk(idx: number) {
  if (expandedChunks.value.has(idx)) {
    expandedChunks.value.delete(idx)
  } else {
    expandedChunks.value.add(idx)
  }
  expandedChunks.value = new Set(expandedChunks.value)
}

function getFileName(source: Source): string {
  return source.metadata?.file_name?.split('/').pop() || 'Unknown file'
}
</script>

<template>
  <div class="retrieval-debugger">
    <div class="panel-header">
      <n-space align="center" justify="space-between">
        <n-text strong>Retrieval Debug</n-text>
        <n-text depth="3" class="count">
          {{ sortedSources.length }} chunks
        </n-text>
      </n-space>
    </div>

    <div class="panel-content">
      <!-- Agent Decision Steps -->
      <div v-if="hasAgentSteps" class="section">
        <n-text depth="2" class="section-title">Agent Decisions</n-text>
        <div
          v-for="(step, idx) in agentSteps"
          :key="step.id"
          class="decision-step"
        >
          <n-space align="center" size="small">
            <n-tag size="tiny" type="info">Step {{ idx + 1 }}</n-tag>
            <n-text style="font-size: 12px;">{{ step.name }}</n-text>
          </n-space>
          <n-text
            v-if="step.output"
            depth="3"
            style="font-size: 11px; display: block; margin-top: 4px;"
          >
            {{ typeof step.output === 'string' ? step.output : JSON.stringify(step.output) }}
          </n-text>
        </div>
      </div>

      <!-- Retrieved Chunks -->
      <div v-if="hasSources" class="section">
        <n-text depth="2" class="section-title">Retrieved Chunks (by score)</n-text>
        <div
          v-for="(source, idx) in sortedSources"
          :key="source.id || idx"
          class="chunk-card"
        >
          <!-- Header -->
          <div class="chunk-header">
            <n-space align="center" size="small">
              <div
                class="rank-badge"
                :style="{ background: scoreColor(source.score) }"
              >
                {{ idx + 1 }}
              </div>
              <n-text strong style="font-size: 12px;">
                {{ getFileName(source) }}
              </n-text>
            </n-space>
            <n-tag
              :type="scoreBarColor(source.score) as any"
              size="tiny"
            >
              {{ scoreLabel(source.score) }}
            </n-tag>
          </div>

          <!-- Score bar -->
          <div class="score-section">
            <n-space align="center" justify="space-between">
              <n-text depth="3" style="font-size: 10px;">Relevance</n-text>
              <n-text
                strong
                style="font-size: 11px;"
                :style="{ color: scoreColor(source.score) }"
              >
                {{ (source.score * 100).toFixed(1) }}%
              </n-text>
            </n-space>
            <n-progress
              type="line"
              :percentage="Math.round(source.score * 100)"
              :color="scoreColor(source.score)"
              :show-indicator="false"
              height="6"
              :border-radius="3"
            />
          </div>

          <!-- Metadata -->
          <div class="chunk-meta">
            <n-space size="small" wrap>
              <n-tag size="tiny" type="info">
                Chunk #{{ (source.metadata?.chunk_index ?? 0) + 1 }}
              </n-tag>
              <n-tag v-if="source.metadata?.page" size="tiny">
                Page {{ source.metadata.page }}
              </n-tag>
              <n-tag size="tiny" :type="source.source_type === 'vector' ? 'success' : source.source_type === 'keyword' ? 'warning' : 'info'">
                {{ source.source_type }}
              </n-tag>
            </n-space>
            <n-text
              depth="3"
              style="font-size: 10px; display: block; margin-top: 4px;"
              class="folder-path"
              :title="source.metadata?.folder_path"
            >
              {{ source.metadata?.folder_path }}
            </n-text>
          </div>

          <!-- Reranking info -->
          <div
            v-if="source.metadata?.original_rank !== undefined && source.metadata?.original_rank !== idx"
            class="rerank-info"
          >
            <n-text depth="3" style="font-size: 10px;">
              Reranked: #{{ source.metadata.original_rank + 1 }} → #{{ idx + 1 }}
            </n-text>
          </div>

          <!-- Expand content -->
          <n-button
            text
            size="tiny"
            @click="toggleChunk(idx)"
            class="expand-btn"
          >
            <template #icon>
              <n-icon size="12">
                <ChevronDown v-if="!expandedChunks.has(idx)" />
                <ChevronUp v-else />
              </n-icon>
            </template>
            {{ expandedChunks.has(idx) ? 'Hide content' : 'Preview content' }}
          </n-button>

          <div v-if="expandedChunks.has(idx)" class="chunk-content">
            <n-text style="font-size: 11px; line-height: 1.5;">
              {{ source.content }}
            </n-text>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <n-empty
        v-if="!hasSources && !hasAgentSteps"
        description="No retrieval data available. Send a query to see retrieved chunks with relevance scores."
        size="small"
      />
    </div>
  </div>
</template>

<style scoped>
.retrieval-debugger {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.count {
  font-size: 12px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  display: block;
  margin-bottom: 8px;
}

.decision-step {
  padding: 8px;
  background: #f9fafb;
  border-radius: 6px;
  margin-bottom: 6px;
  border-left: 3px solid #2080f0;
}

.chunk-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
  background: white;
  transition: box-shadow 0.2s;
}

.chunk-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.chunk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.rank-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.score-section {
  margin-bottom: 8px;
}

.chunk-meta {
  margin-bottom: 6px;
}

.folder-path {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.rerank-info {
  padding: 4px 8px;
  background: #eff6ff;
  border-radius: 4px;
  margin-bottom: 6px;
}

.expand-btn {
  margin-top: 4px;
}

.chunk-content {
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-top: 8px;
  max-height: 150px;
  overflow-y: auto;
}
</style>
