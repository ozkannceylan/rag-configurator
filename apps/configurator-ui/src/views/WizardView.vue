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
          <div class="flex items-center justify-between">
            <div
              v-for="(step, index) in steps"
              :key="index"
              :class="[
                'flex-1 flex items-center',
                index < steps.length - 1 ? `after:content-[''] after:w-full after:h-1 after:mx-2 after:bg-gray-200` : ''
              ]"
            >
              <button
                @click="wizardStore.goToStep(index)"
                :disabled="!wizardStore.stepValidation[index]"
                :class="[
                  'w-10 h-10 rounded-full flex items-center justify-center font-medium text-sm',
                  index === wizardStore.currentStep ? 'bg-primary-600 text-white' :
                  index < wizardStore.currentStep ? 'bg-green-500 text-white' :
                  wizardStore.stepValidation[index] ? 'bg-gray-200 text-gray-700' :
                  'bg-gray-100 text-gray-400'
                ]"
              >
                {{ index < wizardStore.currentStep ? '✓' : index + 1 }}
              </button>
            </div>
          </div>
          <div class="flex justify-between mt-2 text-sm">
            <span
              v-for="(step, index) in steps"
              :key="index"
              :class="[
                index === wizardStore.currentStep ? 'text-primary-600 font-medium' : 'text-gray-500'
              ]"
            >
              {{ step }}
            </span>
          </div>
        </div>

        <!-- Step Content -->
        <div class="min-h-[400px]">
          <component :is="currentStepComponent" />
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
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWizardStore } from '@/stores/wizard'
import StepDataSource from '@/components/wizard/StepDataSource.vue'
import StepRBAC from '@/components/wizard/StepRBAC.vue'
import StepModels from '@/components/wizard/StepModels.vue'
import StepRetrieval from '@/components/wizard/StepRetrieval.vue'
import StepGraph from '@/components/wizard/StepGraph.vue'
import StepAgent from '@/components/wizard/StepAgent.vue'
import StepPrompts from '@/components/wizard/StepPrompts.vue'
import StepReview from '@/components/wizard/StepReview.vue'

const router = useRouter()
const route = useRoute()
const wizardStore = useWizardStore()

const steps = [
  'Data Source',
  'Access Control',
  'Models',
  'Retrieval',
  'Graph',
  'Agent',
  'Prompts',
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
  StepReview,
]

const currentStepComponent = computed(() => {
  return stepComponents[wizardStore.currentStep]
})

const canSave = computed(() => {
  return wizardStore.config.name && wizardStore.config.name.trim()
})

onMounted(() => {
  const id = route.params.id as string
  
  if (id) {
    wizardStore.loadConfigForEdit(id)
  } else {
    wizardStore.resetWizard()
  }
})

function goBack() {
  router.push('/')
}

async function saveDraft() {
  const saved = await wizardStore.saveConfig(false)
  if (saved) {
    router.push('/')
  }
}

async function saveAndRun() {
  try {
    const saved = await wizardStore.saveConfig(true)
    if (saved) {
      router.push(`/config/${saved.id}`)
    }
  } catch (error) {
    console.error('Failed to save and run ingestion:', error)
    alert('Failed to save configuration. Check console for details.')
  }
}
</script>
