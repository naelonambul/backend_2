import { ref } from 'vue'

export const currentUser = ref(null)
let sessionRevision = 0

export function setCurrentUser(user) {
  sessionRevision += 1
  currentUser.value = user ?? null
  return currentUser.value
}

export function clearCurrentUser() {
  sessionRevision += 1
  currentUser.value = null
}

export async function getCurrentUserOrNull(api) {
  try {
    return await api.getCurrentUser()
  } catch (error) {
    if (error?.status === 401) return null
    throw error
  }
}

export async function refreshCurrentUser(api) {
  const revision = ++sessionRevision
  try {
    const user = await getCurrentUserOrNull(api)
    if (revision === sessionRevision) currentUser.value = user
    return user
  } catch (error) {
    if (error?.status === 401 && revision === sessionRevision) currentUser.value = null
    throw error
  }
}
