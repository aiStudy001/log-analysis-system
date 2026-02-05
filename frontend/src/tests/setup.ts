/**
 * Test Setup Configuration
 */
import '@testing-library/jest-dom'

// Mock fetch globally
global.fetch = vi.fn()

// Mock WebSocket globally
global.WebSocket = vi.fn() as any
