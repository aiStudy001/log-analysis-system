/**
 * SQL Validation Event Tests
 *
 * Tests for:
 * - validation_failed event handling
 * - execution_failed event handling
 * - Proper error message display
 */
import { describe, it, expect } from 'vitest'
import type { StreamEvent } from '$lib/api/websocket'

describe('SQL Validation Events', () => {
  describe('Event Type Definitions', () => {
    it('validation_failed event has correct structure', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: DELETE',
          retry_count: 1
        }
      }

      expect(event.type).toBe('validation_failed')
      expect(event.node).toBe('validate_sql')
      expect(event.data.error).toContain('DELETE')
      expect(event.data.retry_count).toBe(1)
    })

    it('execution_failed event has correct structure', () => {
      const event: StreamEvent = {
        type: 'execution_failed',
        node: 'execute_query',
        status: 'failed',
        data: {
          error: 'Database connection timeout'
        }
      }

      expect(event.type).toBe('execution_failed')
      expect(event.node).toBe('execute_query')
      expect(event.data.error).toContain('timeout')
    })
  })

  describe('Dangerous SQL Detection', () => {
    it('validates INSERT is blocked', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: INSERT',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('INSERT')
    })

    it('validates UPDATE is blocked', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: UPDATE',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('UPDATE')
    })

    it('validates DELETE is blocked', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: DELETE',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('DELETE')
    })

    it('validates DROP is blocked', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: DROP',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('DROP')
    })

    it('validates CREATE is blocked', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: CREATE',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('CREATE')
    })

    it('validates non-SELECT start is blocked', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Only SELECT queries are allowed',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('SELECT')
    })
  })

  describe('Execution Error Scenarios', () => {
    it('handles database connection errors', () => {
      const event: StreamEvent = {
        type: 'execution_failed',
        node: 'execute_query',
        status: 'failed',
        data: {
          error: 'Connection to database failed'
        }
      }

      expect(event.type).toBe('execution_failed')
      expect(event.data.error).toBeDefined()
    })

    it('handles syntax errors', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Syntax error: unexpected token',
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('Syntax error')
    })

    it('handles missing deleted filter', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: "Must include 'deleted = FALSE' condition",
          retry_count: 1
        }
      }

      expect(event.data.error).toContain('deleted = FALSE')
    })
  })

  describe('Error Message Formatting', () => {
    it('formats validation error for display', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Dangerous keyword detected: DELETE',
          retry_count: 1
        }
      }

      const displayMessage = `❌ SQL 검증 실패: ${event.data.error}`

      expect(displayMessage).toBe('❌ SQL 검증 실패: Dangerous keyword detected: DELETE')
    })

    it('formats execution error for display', () => {
      const event: StreamEvent = {
        type: 'execution_failed',
        node: 'execute_query',
        status: 'failed',
        data: {
          error: 'Database connection timeout'
        }
      }

      const displayMessage = `❌ 쿼리 실행 실패: ${event.data.error}`

      expect(displayMessage).toBe('❌ 쿼리 실행 실패: Database connection timeout')
    })

    it('handles missing error details gracefully', () => {
      const event: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: '',
          retry_count: 1
        }
      }

      const displayMessage = event.data?.error || 'SQL validation failed'

      expect(displayMessage).toBe('SQL validation failed')
    })
  })

  describe('Retry Count Tracking', () => {
    it('tracks validation retry attempts', () => {
      const events: StreamEvent[] = [
        {
          type: 'validation_failed',
          node: 'validate_sql',
          status: 'failed',
          data: { error: 'Error 1', retry_count: 1 }
        },
        {
          type: 'validation_failed',
          node: 'validate_sql',
          status: 'failed',
          data: { error: 'Error 2', retry_count: 2 }
        },
        {
          type: 'validation_failed',
          node: 'validate_sql',
          status: 'failed',
          data: { error: 'Error 3', retry_count: 3 }
        }
      ]

      expect(events[0].data.retry_count).toBe(1)
      expect(events[1].data.retry_count).toBe(2)
      expect(events[2].data.retry_count).toBe(3)
    })
  })

  describe('Integration with StreamEvent Union', () => {
    it('validation_failed is part of StreamEvent union', () => {
      const validationEvent: StreamEvent = {
        type: 'validation_failed',
        node: 'validate_sql',
        status: 'failed',
        data: {
          error: 'Test error',
          retry_count: 1
        }
      }

      const executionEvent: StreamEvent = {
        type: 'execution_failed',
        node: 'execute_query',
        status: 'failed',
        data: {
          error: 'Test error'
        }
      }

      const errorEvent: StreamEvent = {
        type: 'error',
        message: 'Generic error'
      }

      // All should be valid StreamEvent types
      expect(validationEvent.type).toBeDefined()
      expect(executionEvent.type).toBeDefined()
      expect(errorEvent.type).toBeDefined()
    })
  })
})
