/**
 * Error Store Tests
 *
 * Tests for:
 * - Error persistence
 * - Add/dismiss/clear operations
 * - Connection status tracking
 * - Active error filtering
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { get } from 'svelte/store'
import { errorStore } from '$lib/stores/error'
import type { ConnectionStatus } from '$lib/api/websocket'

describe('Error Store', () => {
  beforeEach(() => {
    // Clear store before each test
    errorStore.clearAll()
  })

  describe('Store Initialization', () => {
    it('initializes with empty errors array', () => {
      const state = get(errorStore)

      expect(state.errors).toEqual([])
      expect(state.connectionStatus).toBe('disconnected')
    })
  })

  describe('Adding Errors', () => {
    it('adds error with auto-generated id and timestamp', () => {
      errorStore.addError({
        message: 'Test error',
        code: 'TEST_ERROR',
        context: 'Test',
        retryable: true
      })

      const state = get(errorStore)

      expect(state.errors).toHaveLength(1)
      expect(state.errors[0].message).toBe('Test error')
      expect(state.errors[0].code).toBe('TEST_ERROR')
      expect(state.errors[0].context).toBe('Test')
      expect(state.errors[0].retryable).toBe(true)
      expect(state.errors[0].dismissed).toBe(false)
      expect(state.errors[0].id).toBeDefined()
      expect(state.errors[0].timestamp).toBeInstanceOf(Date)
    })

    it('adds multiple errors', () => {
      errorStore.addError({
        message: 'Error 1',
        code: 'ERROR_1',
        retryable: false
      })

      errorStore.addError({
        message: 'Error 2',
        code: 'ERROR_2',
        retryable: true
      })

      const state = get(errorStore)

      expect(state.errors).toHaveLength(2)
      expect(state.errors[0].message).toBe('Error 1')
      expect(state.errors[1].message).toBe('Error 2')
    })

    it('generates unique IDs for each error', () => {
      errorStore.addError({ message: 'Error 1', retryable: false })
      errorStore.addError({ message: 'Error 2', retryable: false })

      const state = get(errorStore)

      expect(state.errors[0].id).not.toBe(state.errors[1].id)
    })
  })

  describe('Dismissing Errors', () => {
    it('marks error as dismissed by ID', () => {
      errorStore.addError({
        message: 'Test error',
        retryable: false
      })

      const state1 = get(errorStore)
      const errorId = state1.errors[0].id

      errorStore.dismissError(errorId)

      const state2 = get(errorStore)

      expect(state2.errors[0].dismissed).toBe(true)
    })

    it('does not remove error when dismissed', () => {
      errorStore.addError({
        message: 'Test error',
        retryable: false
      })

      const state1 = get(errorStore)
      const errorId = state1.errors[0].id

      errorStore.dismissError(errorId)

      const state2 = get(errorStore)

      expect(state2.errors).toHaveLength(1)
    })

    it('only dismisses specified error', () => {
      errorStore.addError({ message: 'Error 1', retryable: false })
      errorStore.addError({ message: 'Error 2', retryable: false })

      const state1 = get(errorStore)
      const firstErrorId = state1.errors[0].id

      errorStore.dismissError(firstErrorId)

      const state2 = get(errorStore)

      expect(state2.errors[0].dismissed).toBe(true)
      expect(state2.errors[1].dismissed).toBe(false)
    })
  })

  describe('Clearing Errors', () => {
    it('clearDismissed removes only dismissed errors', () => {
      errorStore.addError({ message: 'Error 1', retryable: false })
      errorStore.addError({ message: 'Error 2', retryable: false })

      const state1 = get(errorStore)
      errorStore.dismissError(state1.errors[0].id)

      errorStore.clearDismissed()

      const state2 = get(errorStore)

      expect(state2.errors).toHaveLength(1)
      expect(state2.errors[0].message).toBe('Error 2')
    })

    it('clearAll removes all errors', () => {
      errorStore.addError({ message: 'Error 1', retryable: false })
      errorStore.addError({ message: 'Error 2', retryable: false })

      errorStore.clearAll()

      const state = get(errorStore)

      expect(state.errors).toEqual([])
    })
  })

  describe('Connection Status', () => {
    it('updates connection status', () => {
      const statuses: ConnectionStatus[] = [
        'connecting',
        'connected',
        'error',
        'disconnected'
      ]

      statuses.forEach(status => {
        errorStore.setConnectionStatus(status)
        const state = get(errorStore)
        expect(state.connectionStatus).toBe(status)
      })
    })

    it('preserves errors when updating status', () => {
      errorStore.addError({ message: 'Test', retryable: false })

      errorStore.setConnectionStatus('connected')

      const state = get(errorStore)
      expect(state.errors).toHaveLength(1)
      expect(state.connectionStatus).toBe('connected')
    })
  })

  describe('Active Errors', () => {
    it('filters out dismissed errors', () => {
      errorStore.addError({ message: 'Error 1', retryable: false })
      errorStore.addError({ message: 'Error 2', retryable: false })
      errorStore.addError({ message: 'Error 3', retryable: false })

      const state1 = get(errorStore)
      errorStore.dismissError(state1.errors[0].id)
      errorStore.dismissError(state1.errors[2].id)

      const state2 = get(errorStore)
      const activeErrors = state2.errors.filter(e => !e.dismissed)

      expect(activeErrors).toHaveLength(1)
      expect(activeErrors[0].message).toBe('Error 2')
    })
  })

  describe('Error Context Filtering', () => {
    it('filters errors by context', () => {
      errorStore.addError({
        message: 'API Error',
        context: 'API',
        retryable: false
      })

      errorStore.addError({
        message: 'WebSocket Error',
        context: 'WebSocket',
        retryable: false
      })

      errorStore.addError({
        message: 'Another API Error',
        context: 'API',
        retryable: false
      })

      const state = get(errorStore)
      const apiErrors = state.errors.filter(e => e.context === 'API')

      expect(apiErrors).toHaveLength(2)
    })
  })

  describe('Request ID Tracking', () => {
    it('stores request ID when provided', () => {
      errorStore.addError({
        message: 'Test error',
        requestId: 'req-12345',
        retryable: false
      })

      const state = get(errorStore)

      expect(state.errors[0].requestId).toBe('req-12345')
    })

    it('allows undefined request ID', () => {
      errorStore.addError({
        message: 'Test error',
        retryable: false
      })

      const state = get(errorStore)

      expect(state.errors[0].requestId).toBeUndefined()
    })
  })
})
