import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useConfigStore } from './config'
import type { RAGConfig } from '@/types'

const defaultConfig: Partial<RAGConfig> = {
  name: '',
  description: '',
  data_source: {
    type: 'local',
    base_path: '/data/documents',
    folders: [],
    has_multimodal: false,
  },
  rbac: {
    enabled: false,
    roles: [
      { name: 'admin', description: 'Administrator', allowed_folders: ['*'], can_query: true, can_view_sources: true },
      { name: 'user', description: 'Regular user', allowed_folders: ['*'], can_query: true, can_view_sources: true },
    ],
    default_role: 'user',
  },
  models: {
    llm: {
      provider: 'openai',
      model_name: 'gpt-4',
      temperature: 0.7,
      max_tokens: 2048,
    },
    embedding: {
      provider: 'openai',
      model_name: 'text-embedding-3-large',
      dimensions: 3072,
    },
    document_processing: {
      use_docling: false,
      use_vision_llm: false,
      ocr_enabled: true,
    },
  },
  retrieval: {
    method: 'hybrid',
    vector: {
      enabled: true,
      top_k: 5,
      score_threshold: 0.7,
    },
    keyword: {
      enabled: true,
      top_k: 5,
      use_fuzzy: true,
      boost_factor: 1.0,
    },
    graph: {
      enabled: false,
      max_depth: 2,
      top_k: 5,
    },
    reranker_enabled: false,
  },
  chunking: {
    strategy: 'recursive',
    chunk_size: 512,
    chunk_overlap: 50,
    separators: ['\n\n', '\n', ' ', ''],
  },
  agent: {
    template: 'naive_rag',
    max_iterations: 5,
    enable_judge: false,
  },
  prompts: {
    system_prompt: 'You are a helpful assistant that answers questions based on the provided context.',
    rag_prompt_template: 'Context information is below.\n---------------------\n{context}\n---------------------\nGiven the context information and not prior knowledge, answer the question: {query}',
  },
}

export const useWizardStore = defineStore('wizard', () => {
  // State
  const currentStep = ref(0)
  const totalSteps = ref(9)
  const config = ref<Partial<RAGConfig>>(JSON.parse(JSON.stringify(defaultConfig)))
  const stepValidation = ref<Record<number, boolean>>({
    0: false, // Data Source
    1: true,  // RBAC (optional)
    2: true,  // Models
    3: true,  // Retrieval
    4: true,  // Graph (conditional)
    5: true,  // Agent
    6: true,  // Prompts
    7: true,  // Advanced (guardrails/eval/cache)
    8: false, // Review (requires name)
  })
  const isEditing = ref(false)
  const configId = ref<string | null>(null)
  const saving = ref(false)

  // Getters
  const canGoNext = computed(() => stepValidation.value[currentStep.value] && currentStep.value < totalSteps.value - 1)
  const canGoPrev = computed(() => currentStep.value > 0)
  const isLastStep = computed(() => currentStep.value === totalSteps.value - 1)

  // Actions
  function nextStep() {
    if (canGoNext.value) {
      currentStep.value++
      // Skip graph step if not enabled
      if (currentStep.value === 4 && !config.value.retrieval?.graph?.enabled) {
        currentStep.value++
      }
    }
  }

  function prevStep() {
    if (canGoPrev.value) {
      currentStep.value--
      // Skip graph step if not enabled
      if (currentStep.value === 4 && !config.value.retrieval?.graph?.enabled) {
        currentStep.value--
      }
    }
  }

  function goToStep(step: number) {
    if (step >= 0 && step < totalSteps.value && stepValidation.value[step]) {
      currentStep.value = step
    }
  }

  function updateConfig(partial: Partial<RAGConfig>) {
    config.value = { ...config.value, ...partial }
    validateCurrentStep()
  }

  function validateCurrentStep() {
    // Always validate step 0 and 8 since they depend on shared config state
    stepValidation.value[0] = !!(
      config.value.data_source?.folders?.length > 0 &&
      config.value.data_source?.base_path
    )
    stepValidation.value[8] = !!(config.value.name && config.value.name.trim())
  }

  // Re-validate whenever config changes (name, folders, etc.)
  watch(
    () => [config.value.name, config.value.data_source?.folders?.length, config.value.data_source?.base_path],
    () => validateCurrentStep(),
    { deep: true }
  )

  function resetWizard() {
    currentStep.value = 0
    config.value = JSON.parse(JSON.stringify(defaultConfig))
    isEditing.value = false
    configId.value = null
    
    // Reset validation
    Object.keys(stepValidation.value).forEach(key => {
      stepValidation.value[Number(key)] = key === '1' || key === '2' || key === '3' || key === '4' || key === '5' || key === '6' || key === '7'
    })
    stepValidation.value[0] = false
    stepValidation.value[8] = false
  }

  async function loadConfigForEdit(id: string) {
    const configStore = useConfigStore()
    const existingConfig = await configStore.fetchConfig(id)
    
    if (existingConfig) {
      config.value = JSON.parse(JSON.stringify(existingConfig))
      configId.value = id
      isEditing.value = true
      currentStep.value = 0
      
      // Mark all steps as valid when editing
      Object.keys(stepValidation.value).forEach(key => {
        stepValidation.value[Number(key)] = true
      })
    }
  }

  async function saveConfig(runIngestion = false) {
    saving.value = true
    const configStore = useConfigStore()
    
    try {
      let saved
      
      if (isEditing.value && configId.value) {
        saved = await configStore.updateConfig(configId.value, config.value)
      } else {
        saved = await configStore.createConfig(config.value)
      }
      
      if (runIngestion && saved.id) {
        const { ingestApi } = await import('@/api/configs')
        await ingestApi.start(saved.id)
      }
      
      return saved
    } catch (error) {
      console.error('Error saving config:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  return {
    currentStep,
    totalSteps,
    config,
    stepValidation,
    isEditing,
    configId,
    saving,
    canGoNext,
    canGoPrev,
    isLastStep,
    nextStep,
    prevStep,
    goToStep,
    updateConfig,
    validateCurrentStep,
    resetWizard,
    loadConfigForEdit,
    saveConfig,
  }
})
