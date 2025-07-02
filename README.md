# LLM Evaluation Service

A comprehensive LLM evaluation service deployed on Kubernetes with horizontal pod autoscaling.

## Overview

This service provides a scalable and reliable way to evaluate LLM outputs against specified criteria. It uses FastAPI for async processing, Redis for rate limiting, and multiple LLM providers for fallback capability. The service is deployed on Kubernetes with horizontal pod autoscaling to handle high load.

## Architectural Design Decisions

### Core Architecture

- **Microservice Pattern**: Single-responsibility service focused on LLM evaluation
- **Async Processing**: Non-blocking I/O using FastAPI with async/await
- **Queue-Based Rate Limiting**: Redis-backed queue system for LLM API management
- **Circuit Breaker Pattern**: Graceful degradation when LLM providers fail
- **Horizontal Scaling**: Stateless design enabling K8s HPA

### Key Components

1. **API Gateway Layer**: FastAPI application handling HTTP requests
2. **Evaluation Engine**: Core logic for LLM interaction and response processing
3. **Rate Limiter**: Redis-based token bucket for provider rate limiting
4. **Circuit Breaker**: Fault tolerance for external LLM API calls
5. **Metrics Collection**: Prometheus metrics for monitoring and scaling

## Architectural Trade-offs

### Selected Approach vs Alternatives

| Aspect               | Selected                | Alternative     | Trade-off Rationale                     |
| -------------------- | ----------------------- | --------------- | --------------------------------------- |
| **Processing Model** | Async/Await             | Synchronous     | Better throughput, resource efficiency  |
| **Rate Limiting**    | Redis Token Bucket      | In-memory       | Shared state across pods, persistence   |
| **LLM Integration**  | Multiple Providers      | Single Provider | Redundancy, cost optimization           |
| **Scaling Strategy** | HPA with Custom Metrics | VPA/Manual      | Responsive to actual load patterns      |
| **State Management** | Stateless + Redis       | Stateful Pods   | Simpler scaling, better fault tolerance |

### Performance vs Complexity Trade-offs

- **Chosen**: Async processing with connection pooling
- **Trade-off**: Increased code complexity for 10x throughput improvement
- **Justification**: Required for 100+ RPS with 1MB payloads

### Reliability vs Latency Trade-offs

- **Chosen**: Circuit breaker with 5s timeout
- **Trade-off**: Potential false negatives during provider issues
- **Justification**: System stability over individual request success

## Setup/Usage

TODO (needs details)

- `./bin/setup`
- `./bin/build`
- `./bin/serve`
- `./bin/check`
