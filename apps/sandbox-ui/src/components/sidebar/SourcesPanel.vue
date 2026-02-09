<script setup lang="ts">
import { computed } from 'vue'
import { NEmpty, NSpace, NText, NSpin } from 'naive-ui'
import { useChatStore } from '@/stores/chat'
import SourceCard from './SourceCard.vue'

const chatStore = useChatStore()

const hasSources = computed(() => chatStore.currentSources.length > 0)
const isLoading = computed(() => chatStore.isStreaming && !hasSources.value)
</script>

<template>
  <div class="sources-panel">
    <div class="panel-header">
      <n-space align="center" justify="space-between">
        <n-text strong>Retrieved Sources</n-text>
        <n-text depth="3" class="count">
          {{ chatStore.currentSources.length }} sources
        </n-text>
      </n-space>
    </div>

    <div class="panel-content">
      <n-spin v-if="isLoading" size="small" description="Retrieving sources..." />

      <template v-else-if="hasSources">
        <n-space vertical>
          <SourceCard
            v-for="(source, index) in chatStore.currentSources"
            :key="source.id"
            :source="source"
            :index="index + 1"
          />
        </n-space>
      </template>

      <n-empty
        v-else
        description="No sources retrieved yet. Start a conversation to see retrieved content."
        size="small"
      />
    </div>
  </div>
</template>

<style scoped>
.sources-panel {
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
</style>
