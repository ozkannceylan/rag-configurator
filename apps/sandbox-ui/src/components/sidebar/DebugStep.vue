<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NTag, NSpace, NText, NButton, NCode, NIcon } from 'naive-ui'
import type { TagProps } from 'naive-ui'
import { ChevronDown, ChevronUp, Time, PlayCircle, CheckmarkCircle, CloseCircle } from '@vicons/ionicons5'
import type { DebugStep } from '@/types'

interface Props {
  step: DebugStep
  index: number
}

const props = defineProps<Props>()

const isExpanded = ref(false)

const statusConfig = computed(() => {
  const configs: Record<DebugStep['status'], {
    color: TagProps['type']
    icon: typeof PlayCircle
    bgColor: string
    borderColor: string
  }> = {
    running: {
      // naive-ui has no 'processing' tag type; 'info' is its blue equivalent.
      color: 'info',
      icon: PlayCircle,
      bgColor: '#e6f7ff',
      borderColor: '#1890ff',
    },
    completed: {
      color: 'success',
      icon: CheckmarkCircle,
      bgColor: '#f6ffed',
      borderColor: '#52c41a',
    },
    failed: {
      color: 'error',
      icon: CloseCircle,
      bgColor: '#fff2f0',
      borderColor: '#ff4d4f',
    },
  }
  return configs[props.step.status] || configs.running
})

const formattedDuration = computed(() => {
  if (props.step.duration_ms < 1000) {
    return `${props.step.duration_ms}ms`
  }
  return `${(props.step.duration_ms / 1000).toFixed(2)}s`
})

const formattedTimestamp = computed(() => {
  return props.step.timestamp.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
})

const hasInput = computed(() => {
  return props.step.input !== undefined && props.step.input !== null
})

const hasOutput = computed(() => {
  return props.step.output !== undefined && props.step.output !== null
})

const hasMetadata = computed(() => {
  return props.step.metadata !== undefined && Object.keys(props.step.metadata).length > 0
})

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const formatJSON = (data: unknown) => {
  return JSON.stringify(data, null, 2)
}
</script>

<template>
  <n-card
    size="small"
    :bordered="true"
    class="debug-step-card"
    :style="{
      background: statusConfig.bgColor,
      borderColor: statusConfig.borderColor,
    }"
  >
    <template #header>
      <n-space align="center" justify="space-between">
        <n-space align="center" size="small">
          <n-icon :color="statusConfig.borderColor" size="16">
            <component :is="statusConfig.icon" />
          </n-icon>
          <n-text strong class="step-name">{{ step.name }}</n-text>
        </n-space>
        <n-tag :type="statusConfig.color" size="tiny">
          {{ step.status }}
        </n-tag>
      </n-space>
    </template>

    <n-space vertical size="small">
      <n-space align="center" size="small">
        <n-icon size="12" depth="3">
          <Time />
        </n-icon>
        <n-text depth="3" style="font-size: 11px;">
          {{ formattedTimestamp }}
        </n-text>
        <n-text depth="3" style="font-size: 11px;">
          •
        </n-text>
        <n-text depth="3" style="font-size: 11px;">
          {{ formattedDuration }}
        </n-text>
      </n-space>

      <n-space v-if="hasMetadata" size="small" wrap>
        <n-tag
          v-for="(value, key) in step.metadata"
          :key="key"
          size="tiny"
          type="info"
        >
          {{ key }}: {{ value }}
        </n-tag>
      </n-space>

      <n-button
        v-if="hasInput || hasOutput"
        text
        size="tiny"
        @click="toggleExpand"
        class="expand-button"
      >
        <template #icon>
          <ChevronDown v-if="!isExpanded" />
          <ChevronUp v-else />
        </template>
        {{ isExpanded ? 'Hide details' : 'View details' }}
      </n-button>

      <n-collapse-transition :show="isExpanded">
        <n-space vertical size="small">
          <div v-if="hasInput" class="step-section">
            <n-text depth="2" style="font-size: 11px; font-weight: 500;">Input:</n-text>
            <n-code
              :code="formatJSON(step.input)"
              language="json"
              style="font-size: 10px;"
            />
          </div>

          <div v-if="hasOutput" class="step-section">
            <n-text depth="2" style="font-size: 11px; font-weight: 500;">Output:</n-text>
            <n-code
              :code="formatJSON(step.output)"
              language="json"
              style="font-size: 10px;"
            />
          </div>
        </n-space>
      </n-collapse-transition>
    </n-space>
  </n-card>
</template>

<style scoped>
.debug-step-card {
  border-left: 3px solid;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.debug-step-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.step-name {
  font-size: 13px;
}

.expand-button {
  margin-top: 4px;
}

.step-section {
  padding: 8px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  margin-top: 4px;
}
</style>
