<template>
  <div class="folder-tree-item">
    <div class="flex items-center gap-2 py-1">
      <!-- Expand/Collapse Button -->
      <button
        v-if="hasChildren"
        @click="toggleExpanded"
        class="w-5 h-5 flex items-center justify-center text-gray-500 hover:text-gray-700"
      >
        <span v-if="expanded">▼</span>
        <span v-else>▶</span>
      </button>
      <span v-else class="w-5"></span>

      <!-- Checkbox -->
      <input
        type="checkbox"
        :checked="isSelected"
        :indeterminate="isIndeterminate"
        @change="handleCheckboxChange"
        class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
      />

      <!-- Folder Icon and Name -->
      <span class="text-yellow-500">📁</span>
      <span class="text-sm text-gray-700 truncate" :title="item.path">
        {{ item.name }}
      </span>

      <!-- File Count Badge -->
      <span v-if="item.file_count && item.file_count > 0" class="text-xs text-gray-500">
        ({{ item.file_count }} files)
      </span>
    </div>

    <!-- Children -->
    <div v-if="expanded && hasChildren" class="ml-6 border-l border-gray-200 pl-2">
      <FolderTreeItem
        v-for="child in item.children"
        :key="child.path"
        :item="child"
        :selected="selected"
        @toggle="(path: string, isSelected: boolean) => $emit('toggle', path, isSelected)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FolderStructure } from '@/types'

const props = defineProps<{
  item: FolderStructure
  selected: string[]
}>()

const emit = defineEmits<{
  toggle: [path: string, selected: boolean]
}>()

const expanded = ref(true)

const hasChildren = computed(() => {
  return props.item.children && props.item.children.length > 0
})

// Check if this folder is directly selected
const isSelected = computed(() => {
  return props.selected.includes(props.item.path)
})

// Check if any descendant is selected (for indeterminate state)
const isIndeterminate = computed(() => {
  if (isSelected.value) return false
  return hasSelectedDescendants(props.item)
})

function hasSelectedDescendants(item: FolderStructure): boolean {
  if (!item.children) return false
  
  for (const child of item.children) {
    if (props.selected.includes(child.path)) return true
    if (hasSelectedDescendants(child)) return true
  }
  return false
}

function toggleExpanded() {
  expanded.value = !expanded.value
}

function handleCheckboxChange(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  emit('toggle', props.item.path, checked)
}
</script>
