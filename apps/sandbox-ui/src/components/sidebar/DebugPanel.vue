<script setup lang="ts">
import { computed } from 'vue'
import { NEmpty, NSpace, NText, NSpin, NTimeline, NTimelineItem } from 'naive-ui'
import { useChatStore } from '@/stores/chat'
import DebugStep from './DebugStep.vue'

const chatStore = useChatStore()

const hasSteps = computed(() => chatStore.currentSteps.length > 0)
const isLoading = computed(() => chatStore.isStreaming && !hasSteps.value)
</script>

<template>
  <div class="debug-panel">
    <div class="panel-header">
      <n-space align="center" justify="space-between">
        <n-text strong>Debug Steps</n-text>
        <n-text depth="3" class="count">
          {{ chatStore.currentSteps.length }} steps
        </n-text>
      </n-space>
    </div>

    <div class="panel-content">
      <n-spin v-if="isLoading" size="small" description="Starting agent..." />

      <template v-else-if="hasSteps">
        <n-timeline>
          <n-timeline-item
            v-for="(step, index) in chatStore.currentSteps"
            :key="step.id"
          >
            <DebugStep :step="step" :index="index" />
          </n-timeline-item>
        </n-timeline>
      </template>

      <n-empty
        v-else
        description="No debug steps available. Start a conversation to see agent execution steps."
        size="small"
      />
    </div>
  </div>
</template>

<style scoped>
.debug-panel {
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
