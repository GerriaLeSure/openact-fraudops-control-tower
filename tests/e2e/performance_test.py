"""
End-to-end performance testing for the fraud detection platform
"""
import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
import random

class PerformanceTest:
    """Performance testing suite for the fraud detection platform"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.auth_token = None
        self.results = {
            "score_latencies": [],
            "decision_latencies": [],
            "case_latencies": [],
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "errors": []
        }
    
    async def authenticate(self, session: aiohttp.ClientSession):
        """Authenticate and get JWT token"""
        auth_data = {
            "username": "sup:perf_test",
            "password": "test_password"
        }
        
        async with session.post(f"{self.base_url}/auth/login", json=auth_data) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data["access_token"]
                return True
            return False
    
    def generate_transaction_data(self, event_id: str) -> Dict[str, Any]:
        """Generate realistic transaction data for testing"""
        return {
            "event_id": event_id,
            "entity_id": f"acct_{random.randint(1000, 9999)}",
            "ts": "2025-10-21T21:10:11Z",
            "amount": random.uniform(10.0, 5000.0),
            "channel": random.choice(["web", "mobile", "api"]),
            "velocity_1h": random.randint(1, 20),
            "ip_risk": random.uniform(0.0, 1.0),
            "geo_distance_km": random.uniform(0.0, 2000.0),
            "merchant_risk": random.uniform(0.0, 1.0),
            "age_days": random.randint(1, 365),
            "device_fingerprint": f"device_{random.randint(100000, 999999)}",
            "features_version": "v1"
        }
    
    async def score_transaction(self, session: aiohttp.ClientSession, 
                              transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score a single transaction"""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        try:
            async with session.post(f"{self.base_url}/score", 
                                  json=transaction_data, 
                                  headers=headers) as response:
                latency = time.time() - start_time
                self.results["score_latencies"].append(latency)
                
                if response.status == 200:
                    self.results["successful_requests"] += 1
                    return await response.json()
                else:
                    self.results["failed_requests"] += 1
                    error_text = await response.text()
                    self.results["errors"].append(f"Score failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            latency = time.time() - start_time
            self.results["score_latencies"].append(latency)
            self.results["failed_requests"] += 1
            self.results["errors"].append(f"Score exception: {str(e)}")
            return None
        finally:
            self.results["total_requests"] += 1
    
    async def make_decision(self, session: aiohttp.ClientSession, 
                          score_data: Dict[str, Any], 
                          transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a decision based on score"""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        decision_data = {
            "event_id": score_data["event_id"],
            "entity_id": transaction_data["entity_id"],
            "channel": transaction_data["channel"],
            "scores": {"calibrated": score_data["scores"]["calibrated"]},
            "features": {
                "velocity_1h": transaction_data["velocity_1h"],
                "ip_risk": transaction_data["ip_risk"]
            }
        }
        
        start_time = time.time()
        try:
            async with session.post(f"{self.base_url}/decide", 
                                  json=decision_data, 
                                  headers=headers) as response:
                latency = time.time() - start_time
                self.results["decision_latencies"].append(latency)
                
                if response.status == 200:
                    self.results["successful_requests"] += 1
                    return await response.json()
                else:
                    self.results["failed_requests"] += 1
                    error_text = await response.text()
                    self.results["errors"].append(f"Decision failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            latency = time.time() - start_time
            self.results["decision_latencies"].append(latency)
            self.results["failed_requests"] += 1
            self.results["errors"].append(f"Decision exception: {str(e)}")
            return None
        finally:
            self.results["total_requests"] += 1
    
    async def create_case(self, session: aiohttp.ClientSession, 
                        decision_data: Dict[str, Any], 
                        transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a case if decision requires it"""
        if decision_data["action"] not in ["hold", "block"]:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        case_data = {
            "event_id": decision_data["event_id"],
            "entity_id": transaction_data["entity_id"],
            "risk": decision_data["risk"],
            "action": decision_data["action"],
            "reasons": decision_data["reasons"]
        }
        
        start_time = time.time()
        try:
            async with session.post(f"{self.BASE_URL}/cases", 
                                  json=case_data, 
                                  headers=headers) as response:
                latency = time.time() - start_time
                self.results["case_latencies"].append(latency)
                
                if response.status == 200:
                    self.results["successful_requests"] += 1
                    return await response.json()
                else:
                    self.results["failed_requests"] += 1
                    error_text = await response.text()
                    self.results["errors"].append(f"Case creation failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            latency = time.time() - start_time
            self.results["case_latencies"].append(latency)
            self.results["failed_requests"] += 1
            self.results["errors"].append(f"Case creation exception: {str(e)}")
            return None
        finally:
            self.results["total_requests"] += 1
    
    async def process_single_transaction(self, session: aiohttp.ClientSession, 
                                       event_id: str) -> Dict[str, Any]:
        """Process a single transaction through the complete pipeline"""
        transaction_data = self.generate_transaction_data(event_id)
        
        # Score transaction
        score_data = await self.score_transaction(session, transaction_data)
        if not score_data:
            return None
        
        # Make decision
        decision_data = await self.make_decision(session, score_data, transaction_data)
        if not decision_data:
            return None
        
        # Create case if needed
        case_data = await self.create_case(session, decision_data, transaction_data)
        
        return {
            "transaction": transaction_data,
            "score": score_data,
            "decision": decision_data,
            "case": case_data
        }
    
    async def run_load_test(self, num_transactions: int = 1000, 
                          concurrent_requests: int = 50):
        """Run load test with specified number of transactions"""
        print(f"Starting load test: {num_transactions} transactions, {concurrent_requests} concurrent")
        
        connector = aiohttp.TCPConnector(limit=concurrent_requests)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Authenticate
            if not await self.authenticate(session):
                print("Authentication failed")
                return
            
            print("Authentication successful")
            
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def process_with_semaphore(event_id: str):
                async with semaphore:
                    return await self.process_single_transaction(session, event_id)
            
            # Run load test
            start_time = time.time()
            tasks = [
                process_with_semaphore(f"perf_test_{i:06d}")
                for i in range(num_transactions)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Process results
            successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
            failed_results = [r for r in results if r is None or isinstance(r, Exception)]
            
            self.print_results(end_time - start_time, num_transactions, successful_results, failed_results)
    
    def print_results(self, total_time: float, num_transactions: int, 
                     successful_results: List, failed_results: List):
        """Print performance test results"""
        print("\n" + "="*60)
        print("PERFORMANCE TEST RESULTS")
        print("="*60)
        
        # Basic metrics
        print(f"Total Transactions: {num_transactions}")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(failed_results)}")
        print(f"Success Rate: {len(successful_results)/num_transactions*100:.2f}%")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Throughput: {num_transactions/total_time:.2f} transactions/second")
        
        # Latency metrics
        if self.results["score_latencies"]:
            score_latencies = self.results["score_latencies"]
            print(f"\nScore Service Latency:")
            print(f"  Average: {statistics.mean(score_latencies)*1000:.2f}ms")
            print(f"  Median: {statistics.median(score_latencies)*1000:.2f}ms")
            print(f"  95th percentile: {sorted(score_latencies)[int(len(score_latencies)*0.95)]*1000:.2f}ms")
            print(f"  99th percentile: {sorted(score_latencies)[int(len(score_latencies)*0.99)]*1000:.2f}ms")
        
        if self.results["decision_latencies"]:
            decision_latencies = self.results["decision_latencies"]
            print(f"\nDecision Service Latency:")
            print(f"  Average: {statistics.mean(decision_latencies)*1000:.2f}ms")
            print(f"  Median: {statistics.median(decision_latencies)*1000:.2f}ms")
            print(f"  95th percentile: {sorted(decision_latencies)[int(len(decision_latencies)*0.95)]*1000:.2f}ms")
        
        if self.results["case_latencies"]:
            case_latencies = self.results["case_latencies"]
            print(f"\nCase Service Latency:")
            print(f"  Average: {statistics.mean(case_latencies)*1000:.2f}ms")
            print(f"  Median: {statistics.median(case_latencies)*1000:.2f}ms")
            print(f"  Cases Created: {len(case_latencies)}")
        
        # Error summary
        if self.results["errors"]:
            print(f"\nErrors ({len(self.results['errors'])}):")
            error_counts = {}
            for error in self.results["errors"]:
                error_type = error.split(":")[0]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            for error_type, count in error_counts.items():
                print(f"  {error_type}: {count}")
        
        # Business metrics
        if successful_results:
            actions = [r["decision"]["action"] for r in successful_results if r["decision"]]
            action_counts = {}
            for action in actions:
                action_counts[action] = action_counts.get(action, 0) + 1
            
            print(f"\nDecision Distribution:")
            for action, count in action_counts.items():
                percentage = count/len(actions)*100
                print(f"  {action}: {count} ({percentage:.1f}%)")
        
        print("="*60)

async def main():
    """Main function to run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance tests")
    parser.add_argument("--transactions", type=int, default=1000, 
                       help="Number of transactions to process")
    parser.add_argument("--concurrent", type=int, default=50, 
                       help="Number of concurrent requests")
    parser.add_argument("--url", type=str, default="http://localhost:8001", 
                       help="Base URL for the API")
    
    args = parser.parse_args()
    
    test = PerformanceTest(args.url)
    await test.run_load_test(args.transactions, args.concurrent)

if __name__ == "__main__":
    asyncio.run(main())