export async function getCurrentUserOrNull(api) {
  try {
    return await api.getCurrentUser()
  } catch (error) {
    if (error?.status === 401) return null
    throw error
  }
}
