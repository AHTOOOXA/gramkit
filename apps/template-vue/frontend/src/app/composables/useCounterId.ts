/**
 * Generate a unique counter ID for demo isolation.
 * Uses session storage so the ID persists across page reloads but is unique per browser tab.
 */
export function useCounterId(): string {
  const storageKey = 'demo-counter-id'

  // Check session storage first (persists for tab session)
  let counterId = sessionStorage.getItem(storageKey)

  if (!counterId) {
    // Generate new unique ID for this session
    counterId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem(storageKey, counterId)
  }

  return counterId
}
