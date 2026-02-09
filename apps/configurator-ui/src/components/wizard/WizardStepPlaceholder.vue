<template>
  <div class="p-8 text-center">
    <h3 class="text-lg font-medium text-gray-900 mb-2">
      Step {{ step + 1 }}: {{ stepNames[step] }}
    </h3>
    <p class="text-gray-600 mb-4">
      This is a placeholder for the wizard step component.
    </p>
    <p class="text-sm text-gray-500">
      In a full implementation, this would contain the form for configuring
      {{ stepNames[step].toLowerCase() }}.
    </p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  step: number
}>()

const stepNames = [
  'Data Source',
  'Access Control',
  'Models',
  'Retrieval',
  'Graph',
  'Agent',
  'Prompts',
  'Review',
]
</script>
