<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-medium text-gray-900">Access Control (RBAC)</h3>
      <div class="flex items-center gap-2">
        <label class="relative inline-flex items-center cursor-pointer">
          <input
            v-model="config.rbac.enabled"
            type="checkbox"
            class="sr-only peer"
          />
          <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
          <span class="ml-3 text-sm font-medium text-gray-700">
            {{ config.rbac.enabled ? 'Enabled' : 'Disabled' }}
          </span>
        </label>
      </div>
    </div>

    <p class="text-sm text-gray-600">
      Role-Based Access Control allows you to restrict access to folders based on user roles.
    </p>

    <div v-if="config.rbac.enabled" class="space-y-6">
      <!-- Roles Section -->
      <div class="bg-gray-50 rounded-lg p-4 space-y-4">
        <h4 class="font-medium text-gray-900">Roles</h4>
        <p class="text-sm text-gray-600">Define roles that can access your data</p>

        <div class="flex gap-2">
          <input
            v-model="newRole"
            type="text"
            class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
            placeholder="Add new role (e.g., manager, analyst)"
            @keyup.enter="addRole"
          />
          <button
            @click="addRole"
            class="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700"
          >
            Add
          </button>
        </div>

        <div class="flex flex-wrap gap-2">
          <div
            v-for="role in config.rbac.roles"
            :key="role"
            class="flex items-center gap-1 px-3 py-1 bg-white border border-gray-300 rounded-full text-sm"
          >
            <span>{{ role }}</span>
            <button
              v-if="role !== 'admin' && role !== 'user'"
              @click="removeRole(role)"
              class="text-gray-400 hover:text-red-500"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Default Role -->
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">
            Default Role for New Users
          </label>
          <select
            v-model="config.rbac.default_role"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option v-for="role in config.rbac.roles" :key="role" :value="role">
              {{ role }}
            </option>
          </select>
        </div>
      </div>

      <!-- Folder Permissions -->
      <div class="bg-gray-50 rounded-lg p-4 space-y-4">
        <h4 class="font-medium text-gray-900">Folder Permissions</h4>
        <p class="text-sm text-gray-600">Assign roles to folders to control access</p>

        <div v-if="folderList.length === 0" class="text-center py-4 text-gray-500">
          No folders selected in Data Source step
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="folder in folderList"
            :key="folder"
            class="bg-white border border-gray-200 rounded-lg p-3"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-medium text-gray-900 text-sm">{{ getFolderName(folder) }}</span>
            </div>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="role in config.rbac.roles"
                :key="role"
                class="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm cursor-pointer hover:bg-gray-200"
              >
                <input
                  type="checkbox"
                  :checked="hasRoleAccess(folder, role)"
                  @change="toggleRoleAccess(folder, role)"
                  class="w-3 h-3 text-primary-600 rounded focus:ring-primary-500"
                />
                <span>{{ role }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <p class="text-sm text-yellow-800">
        RBAC is disabled. All users will have access to all folders.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

const newRole = ref('')

const folderList = computed(() => {
  return config.data_source?.folders?.map(f => f.path) || []
})

function addRole() {
  const role = newRole.value.trim().toLowerCase()
  if (role && !config.rbac.roles.includes(role)) {
    config.rbac.roles.push(role)
    newRole.value = ''
  }
}

function removeRole(role: string) {
  const index = config.rbac.roles.indexOf(role)
  if (index > -1) {
    config.rbac.roles.splice(index, 1)
    // Remove this role from all folder permissions
    Object.keys(config.rbac.folder_permissions).forEach(folder => {
      const roles = config.rbac.folder_permissions[folder]
      const roleIndex = roles.indexOf(role)
      if (roleIndex > -1) {
        roles.splice(roleIndex, 1)
      }
    })
    // Update default role if needed
    if (config.rbac.default_role === role && config.rbac.roles.length > 0) {
      config.rbac.default_role = config.rbac.roles[0]
    }
  }
}

function getFolderName(path: string) {
  return path.split('/').pop() || path.split('\\').pop() || path
}

function hasRoleAccess(folder: string, role: string): boolean {
  const permissions = config.rbac.folder_permissions[folder] || []
  return permissions.includes(role)
}

function toggleRoleAccess(folder: string, role: string) {
  if (!config.rbac.folder_permissions[folder]) {
    config.rbac.folder_permissions[folder] = []
  }
  
  const permissions = config.rbac.folder_permissions[folder]
  const index = permissions.indexOf(role)
  
  if (index === -1) {
    permissions.push(role)
  } else {
    permissions.splice(index, 1)
  }
}
</script>
