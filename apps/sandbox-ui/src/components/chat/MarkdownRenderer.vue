<template>
  <div class="prose prose-sm max-w-none" :class="{ 'prose-invert': isUser }" v-html="renderedContent"></div>
</template>

<script setup lang="ts">
import { watch, onMounted, ref } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

interface Props {
  content: string
  isUser?: boolean
  isStreaming?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isUser: false,
  isStreaming: false,
})

const renderedContent = ref('')

// Configure marked options
// `headerIds`, `mangle` and `sanitize` were removed in marked v12.
marked.setOptions({
  breaks: true,
  gfm: true,
})

// Custom renderer to add syntax highlighting and styling
const renderer = new marked.Renderer()

// Code blocks with syntax highlighting
renderer.code = (code: string, language?: string) => {
  const validLanguage = language && hljs.getLanguage(language) ? language : 'plaintext'
  const highlighted = hljs.highlight(code, { language: validLanguage }).value
  
  return `
    <div class="relative group my-3">
      <div class="flex items-center justify-between px-3 py-1.5 bg-gray-100 border-b border-gray-200 rounded-t-lg">
        <span class="text-xs font-medium text-gray-500">${validLanguage}</span>
        <button 
          onclick="this.closest('.group').querySelector('code').dataset.copied = 'true'; navigator.clipboard.writeText(this.closest('.group').querySelector('code').textContent); setTimeout(() => this.closest('.group').querySelector('code').dataset.copied = 'false', 2000)"
          class="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Copy
        </button>
      </div>
      <pre class="m-0 p-3 bg-gray-50 rounded-b-lg overflow-x-auto"><code class="language-${validLanguage} text-sm">${highlighted}</code></pre>
    </div>
  `
}

// Inline code
renderer.codespan = (code: string) => {
  return `<code class="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-sm font-mono">${code}</code>`
}

// Links - open in new tab
renderer.link = (href: string, title: string | null | undefined, text: string) => {
  return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:underline" ${title ? `title="${title}"` : ''}>${text}</a>`
}

// Paragraphs
renderer.paragraph = (text: string) => {
  return `<p class="mb-3 last:mb-0 leading-relaxed">${text}</p>`
}

// Headings
renderer.heading = (text: string, level: number) => {
  const sizes: Record<number, string> = {
    1: 'text-xl',
    2: 'text-lg',
    3: 'text-base',
    4: 'text-sm',
    5: 'text-sm',
    6: 'text-xs',
  }
  return `<h${level} class="${sizes[level]} font-semibold mt-4 mb-2 first:mt-0">${text}</h${level}>`
}

// Lists
renderer.list = (body: string, ordered: boolean) => {
  const type = ordered ? 'ol' : 'ul'
  const classes = ordered ? 'list-decimal' : 'list-disc'
  return `<${type} class="${classes} pl-4 mb-3 space-y-1">${body}</${type}>`
}

renderer.listitem = (text: string) => {
  return `<li class="leading-relaxed">${text}</li>`
}

// Blockquotes
renderer.blockquote = (quote: string) => {
  return `<blockquote class="border-l-4 border-primary-300 pl-4 py-1 my-3 text-gray-600 italic">${quote}</blockquote>`
}

// Tables
renderer.table = (header: string, body: string) => {
  return `
    <div class="overflow-x-auto my-3">
      <table class="min-w-full border-collapse border border-gray-200">
        <thead class="bg-gray-50">${header}</thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `
}

renderer.tablerow = (content: string) => {
  return `<tr class="border-b border-gray-200">${content}</tr>`
}

renderer.tablecell = (content: string, flags: { header: boolean; align: 'left' | 'center' | 'right' | null }) => {
  const tag = flags.header ? 'th' : 'td'
  const align = flags.align ? `text-${flags.align}` : 'text-left'
  const classes = flags.header 
    ? `px-3 py-2 text-xs font-semibold text-gray-700 ${align}`
    : `px-3 py-2 text-sm text-gray-600 ${align}`
  return `<${tag} class="${classes}">${content}</${tag}>`
}

// Horizontal rule
renderer.hr = () => {
  return `<hr class="my-4 border-gray-200">`
}

// Strong and emphasis
renderer.strong = (text: string) => {
  return `<strong class="font-semibold">${text}</strong>`
}

renderer.em = (text: string) => {
  return `<em class="italic">${text}</em>`
}

// Strikethrough
renderer.del = (text: string) => {
  return `<del class="line-through text-gray-400">${text}</del>`
}

marked.use({ renderer })

// Compute rendered content
const updateContent = () => {
  try {
    if (!props.content) {
      renderedContent.value = ''
      return
    }
    
    // Parse markdown
    let html = marked.parse(props.content) as string
    
    // If streaming and content doesn't end with complete element, add cursor
    if (props.isStreaming && !props.content.endsWith('\n')) {
      // Don't modify - the cursor is shown by parent component
    }
    
    renderedContent.value = html
  } catch (error) {
    console.error('Error rendering markdown:', error)
    // Fallback to plain text with HTML escaping
    renderedContent.value = props.content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
}

// Watch for content changes
watch(() => props.content, updateContent, { immediate: true })

onMounted(() => {
  updateContent()
})
</script>

<style scoped>
/* Custom styles for markdown content */
:deep(pre) {
  margin: 0;
}

:deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

:deep(.hljs) {
  background: transparent;
  padding: 0;
}

/* Invert colors for user messages */
.prose-invert :deep(.text-gray-600),
.prose-invert :deep(.text-gray-500),
.prose-invert :deep(.text-gray-400) {
  color: rgba(255, 255, 255, 0.8);
}

.prose-invert :deep(.bg-gray-100),
.prose-invert :deep(.bg-gray-50) {
  background-color: rgba(255, 255, 255, 0.15);
}

.prose-invert :deep(.border-gray-200) {
  border-color: rgba(255, 255, 255, 0.2);
}

.prose-invert :deep(code) {
  background-color: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.95);
}

.prose-invert :deep(blockquote) {
  border-color: rgba(255, 255, 255, 0.3);
  color: rgba(255, 255, 255, 0.8);
}

.prose-invert :deep(a) {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: underline;
}
</style>
