<template>
  <div>
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center gap-4">
          <button @click="goBack" class="text-gray-600 hover:text-gray-900">
            ← Back
          </button>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ wizardStore.isEditing ? 'Edit Configuration' : 'New Configuration' }}
          </h1>
        </div>
      </div>
    </header>

    <!-- Wizard Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="bg-white rounded-lg shadow p-6">
        <!-- Stepper -->
        <div class="mb-8">
          <div class="flex items-start">
            <div
              v-for="(step, index) in steps"
              :key="index"
              class="flex-1 flex flex-col items-center relative"
            >
              <!-- Connector line -->
              <div
                v-if="index < steps.length - 1"
                class="absolute top-5 left-[calc(50%+20px)] right-[calc(-50%+20px)] h-0.5 bg-gray-200"
              ></div>
              <!-- Circle -->
              <button
                @click="wizardStore.goToStep(index)"
                :disabled="!wizardStore.stepValidation[index]"
                :class="[
                  'relative z-10 w-10 h-10 rounded-full flex items-center justify-center font-medium text-sm shrink-0',
                  index === wizardStore.currentStep ? 'bg-primary-600 text-white' :
                  index < wizardStore.currentStep ? 'bg-green-500 text-white' :
                  wizardStore.stepValidation[index] ? 'bg-gray-200 text-gray-700' :
                  'bg-gray-100 text-gray-400'
                ]"
              >
                {{ index < wizardStore.currentStep ? '✓' : index + 1 }}
              </button>
              <!-- Label -->
              <span
                :class="[
                  'mt-2 text-xs text-center leading-tight',
                  index === wizardStore.currentStep ? 'text-primary-600 font-medium' : 'text-gray-500'
                ]"
              >
                {{ step }}
              </span>
            </div>
          </div>
        </div>

        <!-- Step Content -->
        <div v-if="wizardLoading" class="min-h-[400px] flex items-center justify-center">
          <div class="text-center">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p class="mt-4 text-gray-600">Loading configuration...</p>
          </div>
        </div>
        <div v-else class="min-h-[400px]">
          <component :is="currentStepComponent" />
        </div>

        <!-- Save Error Banner -->
        <div v-if="saveError" class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span class="text-sm text-red-800">{{ saveError }}</span>
          <button @click="saveError = null" class="text-red-600 hover:text-red-800 text-sm font-medium">
            Dismiss
          </button>
        </div>

        <!-- Navigation -->
        <div class="flex justify-between mt-8 pt-6 border-t">
          <button
            @click="wizardStore.prevStep"
            :disabled="!wizardStore.canGoPrev"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>

          <div class="flex gap-4">
            <button
              @click="saveDraft"
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Save Draft
            </button>

            <button
              v-if="wizardStore.isLastStep"
              @click="saveAndRun"
              :disabled="!canSave"
              class="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              Save & Run Ingestion
            </button>

            <button
              v-else
              @click="wizardStore.nextStep"
              :disabled="!wizardStore.canGoNext"
              class="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { useWizardStore } from '@/stores/wizard'
import { useToast } from '@/composables/useToast'
import StepDataSource from '@/components/wizard/StepDataSource.vue'
import StepRBAC from '@/components/wizard/StepRBAC.vue'
import StepModels from '@/components/wizard/StepModels.vue'
import StepRetrieval from '@/components/wizard/StepRetrieval.vue'
import StepGraph from '@/components/wizard/StepGraph.vue'
import StepAgent from '@/components/wizard/StepAgent.vue'
import StepPrompts from '@/components/wizard/StepPrompts.vue'
import StepAdvanced from '@/components/wizard/StepAdvanced.vue'
import StepReview from '@/components/wizard/StepReview.vue'

const router = useRouter()
const route = useRoute()
const wizardStore = useWizardStore()
const { addToast } = useToast()

const saveError = ref<string | null>(null)
const initialSnapshot = ref('')
const saved = ref(false)
const wizardLoading = ref(false)

const steps = [
  'Data Source',
  'Access Control',
  'Models',
  'Retrieval',
  'Graph',
  'Agent',
  'Prompts',
  'Advanced',
  'Review',
]

const stepComponents = [
  StepDataSource,
  StepRBAC,
  StepModels,
  StepRetrieval,
  StepGraph,
  StepAgent,
  StepPrompts,
  StepAdvanced,
  StepReview,
]

const currentStepComponent = computed(() => {
  return stepComponents[wizardStore.currentStep]
})

const canSave = computed(() => {
  return wizardStore.config.name && wizardStore.config.name.trim()
})

function hasUnsavedChanges(): boolean {
  if (saved.value) return false
  return JSON.stringify(wizardStore.config) !== initialSnapshot.value
}

// Reset/load config BEFORE child components render to avoid stale references.
// Child step components capture `wizardStore.config` during their setup phase,
// which runs during the parent's render (before onMounted). If resetWizard()
// ran in onMounted, children would hold a reference to the OLD config object.
const routeId = route.params.id as string
if (routeId) {
  wizardLoading.value = true
} else {
  wizardStore.resetWizard()
}

onMounted(async () => {
  if (routeId) {
    await wizardStore.loadConfigForEdit(routeId)
    wizardLoading.value = false
  }

  await nextTick()
  initialSnapshot.value = JSON.stringify(wizardStore.config)
})

// Unsaved changes warning on route leave
onBeforeRouteLeave((_to, _from, next) => {
  if (hasUnsavedChanges()) {
    const answer = window.confirm('You have unsaved changes. Are you sure you want to leave?')
    if (!answer) return next(false)
  }
  next()
})

// Unsaved changes warning on browser close/refresh
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (hasUnsavedChanges()) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

function goBack() {
  router.push('/')
}

async function saveDraft() {
  saveError.value = null
  try {
    const result = await wizardStore.saveConfig(false)
    if (result) {
      saved.value = true
      addToast('Configuration saved successfully', 'success')
      router.push('/')
    }
  } catch {
    saveError.value = 'Failed to save configuration. Please try again.'
    addToast('Failed to save configuration', 'error')
  }
}

async function saveAndRun() {
  saveError.value = null
  try {
    const result = await wizardStore.saveConfig(true)
    if (result) {
      saved.value = true
      addToast('Configuration saved — ingestion started', 'success')
      router.push(`/config/${result.id}`)
    }
  } catch {
    saveError.value = 'Failed to save configuration. Please try again.'
    addToast('Failed to save configuration', 'error')
  }
}
</script>
