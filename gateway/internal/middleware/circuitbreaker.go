package middleware

import (
	"errors"
	"net/http"
	"sync"
	"time"
)

var (
	// ErrCircuitOpen indicates the backend is temporarily unavailable due to repeated failures.
	ErrCircuitOpen = errors.New("circuit breaker open")
)

type circuitBreakerState string

const (
	stateClosed   circuitBreakerState = "closed"
	stateOpen     circuitBreakerState = "open"
	stateHalfOpen circuitBreakerState = "half_open"
)

// CircuitBreaker implements a small per-service state machine for outbound proxy calls.
type CircuitBreaker struct {
	mu            sync.Mutex
	state         circuitBreakerState
	failureTimes  []time.Time
	halfOpenProbe bool
	threshold     int
	window        time.Duration
	openTimeout   time.Duration
	openedAt      time.Time
}

// NewCircuitBreaker creates a circuit breaker with the Phase 1 thresholds.
func NewCircuitBreaker(threshold int, window time.Duration, openTimeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		state:       stateClosed,
		threshold:   threshold,
		window:      window,
		openTimeout: openTimeout,
	}
}

// Allow reports whether a request may proceed to the backend.
func (cb *CircuitBreaker) Allow() error {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case stateOpen:
		if time.Since(cb.openedAt) < cb.openTimeout {
			return ErrCircuitOpen
		}
		cb.state = stateHalfOpen
		cb.halfOpenProbe = true
		return nil
	case stateHalfOpen:
		if cb.halfOpenProbe {
			return ErrCircuitOpen
		}
		cb.halfOpenProbe = true
		return nil
	default:
		return nil
	}
}

// RecordSuccess closes the breaker after a successful probe or clears recent failures.
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.state = stateClosed
	cb.failureTimes = nil
	cb.halfOpenProbe = false
}

// RecordFailure records a backend failure and opens the breaker when thresholds are exceeded.
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	now := time.Now()
	if cb.state == stateHalfOpen {
		cb.state = stateOpen
		cb.openedAt = now
		cb.failureTimes = nil
		cb.halfOpenProbe = false
		return
	}

	cutoff := now.Add(-cb.window)
	pruned := cb.failureTimes[:0]
	for _, failureAt := range cb.failureTimes {
		if failureAt.After(cutoff) {
			pruned = append(pruned, failureAt)
		}
	}
	cb.failureTimes = append(pruned, now)
	cb.halfOpenProbe = false

	if len(cb.failureTimes) >= cb.threshold {
		cb.state = stateOpen
		cb.openedAt = now
		cb.failureTimes = nil
	}
}

// State returns the current breaker state for tests and diagnostics.
func (cb *CircuitBreaker) State() string {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return string(cb.state)
}

// CircuitBreakerTransport wraps outbound HTTP calls with breaker state transitions.
type CircuitBreakerTransport struct {
	base    http.RoundTripper
	breaker *CircuitBreaker
}

// NewCircuitBreakerTransport creates a transport that enforces a circuit breaker.
func NewCircuitBreakerTransport(base http.RoundTripper, breaker *CircuitBreaker) http.RoundTripper {
	return &CircuitBreakerTransport{
		base:    base,
		breaker: breaker,
	}
}

func (t *CircuitBreakerTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if err := t.breaker.Allow(); err != nil {
		return nil, err
	}

	resp, err := t.base.RoundTrip(req)
	if err != nil {
		t.breaker.RecordFailure()
		return nil, err
	}

	if resp.StatusCode >= http.StatusInternalServerError {
		t.breaker.RecordFailure()
	} else {
		t.breaker.RecordSuccess()
	}

	return resp, nil
}
