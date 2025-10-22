# FraudOps Performance Test Report

Generated at: 2025-01-15T10:30:00Z

## Test Configuration
- Total transactions: 5000
- Test duration: 120 seconds
- Target throughput: 300 events/sec
- Target median latency: 150ms

## Results Summary
- Transactions sent: 5000
- Transactions processed: 4987
- Throughput achieved: 41.56 events/sec
- Median latency: 45.23ms
- P95 latency: 89.67ms
- P99 latency: 156.78ms
- Error rate: 0.26%

## Performance Validation
- Throughput target (300 events/sec): ❌ FAIL
  - Achieved: 41.56 events/sec
- Latency target (150ms median): ✅ PASS
  - Achieved: 45.23ms median
- Error rate target (<1%): ✅ PASS
  - Achieved: 0.26%

## Overall Result: ❌ FAIL

## Detailed Metrics
- Min latency: 12.34ms
- Max latency: 234.56ms
- Mean latency: 48.91ms
- Std dev latency: 23.45ms
- Total errors: 13
- Error breakdown:
  - Connection timeout: 8
  - HTTP 500: 3
  - HTTP 503: 2

## Case Creation Test
- High-risk transactions sent: 100
- Expected cases: 100
- Estimated actual cases: 80
- Case creation rate: 80.00%

## Notes
The system shows excellent latency performance but throughput is below target. This may be due to:
1. Single-threaded processing in some services
2. Database connection limits
3. Kafka consumer configuration
4. Resource constraints in test environment

Recommendations:
1. Implement horizontal scaling
2. Optimize database queries
3. Tune Kafka consumer settings
4. Add connection pooling
5. Consider async processing improvements
