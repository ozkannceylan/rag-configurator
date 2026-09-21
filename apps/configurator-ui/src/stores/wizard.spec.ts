import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWizardStore } from './wizard'

describe('wizard store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts on step 0 with every config section populated', () => {
    const wizard = useWizardStore()

    expect(wizard.currentStep).toBe(0)
    expect(wizard.config.data_source.folders).toEqual([])
    expect(wizard.config.rbac.roles.length).toBeGreaterThan(0)
    expect(wizard.config.models.llm.provider).toBe('openai')
    expect(wizard.config.models.document_processing).toBeDefined()
    expect(wizard.config.retrieval.keyword).toBeDefined()
    expect(wizard.config.retrieval.graph.enabled).toBe(false)
    expect(wizard.config.agent.config).toEqual({})
  })

  it('backfills sections missing from a partial update', () => {
    const wizard = useWizardStore()

    wizard.updateConfig({
      name: 'partial',
      retrieval: { method: 'keyword', vector: { top_k: 3, score_threshold: 0.5 } },
    })

    expect(wizard.config.name).toBe('partial')
    expect(wizard.config.retrieval.method).toBe('keyword')
    expect(wizard.config.retrieval.vector.top_k).toBe(3)
    // Absent from the update, so the defaults must still be there: the wizard
    // steps bind to these without guarding for undefined.
    expect(wizard.config.retrieval.graph).toBeDefined()
    expect(wizard.config.retrieval.keyword).toBeDefined()
    expect(wizard.config.prompts.system_prompt).not.toBe('')
  })

  it('only allows leaving the data-source step once a folder and base path are set', () => {
    const wizard = useWizardStore()

    expect(wizard.stepValidation[0]).toBe(false)
    expect(wizard.canGoNext).toBe(false)

    wizard.config.data_source.base_path = '/data/documents'
    wizard.config.data_source.folders = [{ path: '/data/documents/a', name: 'a' }]
    wizard.validateCurrentStep()

    expect(wizard.stepValidation[0]).toBe(true)
    expect(wizard.canGoNext).toBe(true)
  })

  it('skips the graph step while graph retrieval is disabled', () => {
    const wizard = useWizardStore()

    wizard.currentStep = 3
    wizard.nextStep()

    // Step 4 is the graph step; it is skipped straight through to the agent step.
    expect(wizard.config.retrieval.graph.enabled).toBe(false)
    expect(wizard.currentStep).toBe(5)

    wizard.config.retrieval.graph.enabled = true
    wizard.currentStep = 3
    wizard.nextStep()
    expect(wizard.currentStep).toBe(4)
  })

  it('resets back to an untouched wizard', () => {
    const wizard = useWizardStore()

    wizard.config.name = 'temporary'
    wizard.currentStep = 4
    wizard.resetWizard()

    expect(wizard.config.name).toBe('')
    expect(wizard.currentStep).toBe(0)
    expect(wizard.stepValidation[0]).toBe(false)
    expect(wizard.stepValidation[8]).toBe(false)
  })
})
