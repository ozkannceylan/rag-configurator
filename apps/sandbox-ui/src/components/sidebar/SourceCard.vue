<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NTag, NProgress, NButton, NSpace, NText, NCollapse, NCollapseItem } from 'naive-ui'
import { ChevronDown, ChevronUp, DocumentText, FileTrayFull, Image, DocumentAttach } from '@vicons/ionicons5'
import type { Source } from '@/types'

interface Props {
  source: Source
  index: number
}

const props = defineProps<Props>()

const isExpanded = ref(false)

const scorePercentage = computed(() => {
  return Math.round(props.source.score * 100)
})

const scoreColor = computed(() => {
  if (props.source.score >= 0.8) return '#18a058'
  if (props.source.score >= 0.6) return '#f0a020'
  return '#d03050'
})

const sourceTypeLabel = computed(() => {
  const labels: Record<string, string> = {
    vector: 'Vector',
    keyword: 'Keyword',
    graph: 'Graph',
  }
  return labels[props.source.source_type] || props.source.source_type
})

const sourceTypeColor = computed(() => {
  const colors: Record<string, string> = {
    vector: 'success',
    keyword: 'warning',
    graph: 'info',
  }
  return colors[props.source.source_type] || 'default'
})

const fileIcon = computed(() => {
  const ext = props.source.metadata.file_name.split('.').pop()?.toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')) return Image
  if (['pdf'].includes(ext || '')) return DocumentAttach
  if (['doc', 'docx'].includes(ext || '')) return FileTrayFull
  return DocumentText
})

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const getFileName = (path: string) => {
  return path.split('/').pop() || path
}
</script>

<template>
  <n-card
    size="small"
    :bordered="true"
    class="source-card"
    :style="{ borderLeftColor: scoreColor }"
  >
    <template #header>
      <n-space align="center" justify="space-between">
        <n-space align="center" size="small">
          <div class="index-badge">
            {{ index }}
          </div>
          <n-text strong class="file-name">
            {{ getFileName(source.metadata.file_name) }}
          </n-text>
        </n-space>
        <n-tag :type="sourceTypeColor" size="tiny">
          {{ sourceTypeLabel }}
        </n-tag>
      </n-space>
    </template>

    <n-space vertical size="small">
      <div class="score-bar">
        <n-space align="center" justify="space-between">
          <n-text depth="3" style="font-size: 11px;">Relevance Score</n-text>
          <n-text strong style="font-size: 11px;" :style="{ color: scoreColor }">
            {{ scorePercentage }}%
          </n-text>
        </n-space>
        <n-progress
          type="line"
          :percentage="scorePercentage"
          :color="scoreColor"
          :show-indicator="false"
          height="4"
          processing
        />
      </div>

      <div class="source-meta">
        <n-space size="small">
          <n-text depth="3" style="font-size: 11px;">
            Chunk #{{ source.metadata.chunk_index + 1 }}
          </n-text>
          <n-text depth="3" style="font-size: 11px;" v-if="source.metadata.page">
            Page {{ source.metadata.page }}
          </n-text>
        </n-space>
        <n-text depth="3" style="font-size: 10px;" class="folder-path" :title="source.metadata.folder_path">
          {{ source.metadata.folder_path }}
        </n-text>
      </div>

      <n-button
        text
        size="tiny"
        @click="toggleExpand"
        class="expand-button"
      >
        <template #icon>
          <ChevronDown v-if="!isExpanded" />
          <ChevronUp v-else />
        </template>
        {{ isExpanded ? 'Hide content' : 'View content' }}
      </n-button>

      <n-collapse-transition :show="isExpanded">
        <div class="source-content">
          <n-text style="font-size: 12px; line-height: 1.5;">
            {{ source.content }}
          </n-text>
        </div>
      </n-collapse-transition>
    </n-space>
  </n-card>
</template>

<style scoped>
.source-card {
  border-left: 3px solid;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.source-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.index-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2080f0;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.file-name {
  font-size: 13px;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-bar {
  margin-top: 4px;
}

.source-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.folder-path {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.expand-button {
  margin-top: 4px;
}

.source-content {
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-top: 8px;
  max-height: 200px;
  overflow-y: auto;
}
</style>
