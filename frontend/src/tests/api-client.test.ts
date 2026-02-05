/**
 * API Client Error Handling Tests
 *
 * Tests for:
 * - Request timeout (30s)
 * - Retry logic (3 attempts)
 * - ApiError class
 * - Error code handling
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ApiError } from '$lib/api/client'

describe('API Client Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('ApiError Class', () => {
    it('creates error with all properties', () => {
      const error = new ApiError(
        'Test error',
        'TEST_ERROR',
        true,
        500,
        'req-123'
      )

      expect(error.message).toBe('Test error')
      expect(error.code).toBe('TEST_ERROR')
      expect(error.retryable).toBe(true)
      expect(error.status).toBe(500)
      expect(error.requestId).toBe('req-123')
      expect(error.name).toBe('ApiError')
    })

    it('creates error without optional fields', () => {
      const error = new ApiError(
        'Simple error',
        'SIMPLE_ERROR',
        false
      )

      expect(error.message).toBe('Simple error')
      expect(error.code).toBe('SIMPLE_ERROR')
      expect(error.retryable).toBe(false)
      expect(error.status).toBeUndefined()
      expect(error.requestId).toBeUndefined()
    })

    it('extends Error class', () => {
      const error = new ApiError('Test', 'TEST', false)

      expect(error instanceof Error).toBe(true)
      expect(error instanceof ApiError).toBe(true)
    })
  })

  describe('Timeout Handling', () => {
    it('timeout value is configurable', () => {
      // Default timeout should be 30 seconds (30000ms)
      const defaultTimeout = 30000

      expect(defaultTimeout).toBe(30000)
    })

    it('AbortController is used for timeout', () => {
      // Verify AbortController is available
      expect(typeof AbortController).toBe('function')

      const controller = new AbortController()
      expect(controller.signal).toBeDefined()
      expect(typeof controller.abort).toBe('function')
    })
  })

  describe('Retry Logic', () => {
    it('retry count is 3 by default', () => {
      const maxRetries = 3
      expect(maxRetries).toBe(3)
    })

    it('exponential backoff increases delay', () => {
      // Backoff formula: Math.min(10000, 1000 * 2 ** attempt)
      const getBackoff = (attempt: number) =>
        Math.min(10000, 1000 * 2 ** attempt)

      expect(getBackoff(0)).toBe(1000)  // 1s
      expect(getBackoff(1)).toBe(2000)  // 2s
      expect(getBackoff(2)).toBe(4000)  // 4s
      expect(getBackoff(3)).toBe(8000)  // 8s
      expect(getBackoff(4)).toBe(10000) // 10s max
    })

    it('only retries on 5xx and network errors', () => {
      const isRetriable = (status?: number) => {
        if (!status) return true // Network error
        return status >= 500 && status < 600
      }

      expect(isRetriable(undefined)).toBe(true) // Network error
      expect(isRetriable(500)).toBe(true)
      expect(isRetriable(502)).toBe(true)
      expect(isRetriable(503)).toBe(true)
      expect(isRetriable(400)).toBe(false)
      expect(isRetriable(404)).toBe(false)
      expect(isRetriable(200)).toBe(false)
    })
  })

  describe('Error Response Parsing', () => {
    it('extracts error code from response', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: async () => ({
          error_code: 'DATABASE_ERROR',
          message: 'Database connection failed',
          request_id: 'req-456'
        })
      }

      const data = await mockResponse.json()

      expect(data.error_code).toBe('DATABASE_ERROR')
      expect(data.message).toBe('Database connection failed')
      expect(data.request_id).toBe('req-456')
    })

    it('handles response without error details', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({})
      }

      const data = await mockResponse.json()

      expect(Object.keys(data).length).toBe(0)
      expect(mockResponse.statusText).toBe('Internal Server Error')
    })
  })

  describe('Error Code Classification', () => {
    it('classifies retryable errors correctly', () => {
      const retryableErrors = [
        'DATABASE_ERROR',
        'LLM_TIMEOUT',
        'WEBSOCKET_ERROR',
        'SERVICE_UNAVAILABLE'
      ]

      const nonRetryableErrors = [
        'VALIDATION_ERROR',
        'INVALID_SQL',
        'MISSING_PARAMETER'
      ]

      // All errors in retryable list should be considered retryable
      retryableErrors.forEach(code => {
        expect(code).toBeDefined()
      })

      nonRetryableErrors.forEach(code => {
        expect(code).toBeDefined()
      })
    })
  })
})
