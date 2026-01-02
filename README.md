This project is an experiment in optimizing the throughput of high-concurrency requests using a simple FastAPI layer to write to a PostgreSQL table.

Beginning with a naive implementation, I was able to achieve over 500% improvement in performance, scaling to over 1200 RPS with a median 36 milliseconds of latency. 

Here is a summary of the significant bottlenecks I encountered and the resulting architectural or performance optimizations I performed:
| **Bottleneck**                                                                                                                                 	| **Optimization**                                                                                    	|
|------------------------------------------------------------------------------------------------------------------------------------------------	|-----------------------------------------------------------------------------------------------------	|
| API was spending too much time waiting for database write                                                                                      	| Delegate writing logic to Redis consumer group                                                      	|
| Opening new asyncpg and Redis connections exhausted TCP ports and led to socket depletion                                                      	| Implement connection pooling                                                                        	|
| Redis worker was spending too long INSERTing each request                                                                                      	| Use PostgreSQL's COPY protocol for faster inserts                                                   	|
| Redis worker was processing requests too quickly, resulting in only COPYing 2-3 requests at a time, undermining the core benefit of using COPY 	| Create a buffer so the worker waits for many requests to accumulate, then flush in one bulk request 	|
| Locust's HttpUser type was too CPU inefficient for high throughput testing                                                                     	| Use Locust's FastHttpUser                                                                           	|
| The single Uvicorn worker was handling requests too slowly                                                                                     	| Start multiple worker processes                                                                     	|
| Manually generating request IDs using a counter was too CPU inefficient                                                                        	| Use a PostgreSQL identity column                                                                    	|
| FastAPI writing to standard output and the Redis worker writing to a log added IO overhead                                                     	| Turn off logging                                                                                    	|
| Serializing Pydantic payload to JSON involved too much overhead                                                                                	| Pass in the payload as a Python dict                                                                	|

There were also some possible performance optimizations I considered, but ultimately dropped due to lack of observed benefit in testing:

| **Considered Optimizations**                                                                              	| **Why Not**                                                                                                           	|
|-----------------------------------------------------------------------------------------------------------	|-----------------------------------------------------------------------------------------------------------------------	|
| Spawning more Redis worker instances to read from different parts of the request stream                   	| Inspecting the logs, the singular worker setup was consistently able to keep up with the request load                 	|
| Spawning more Locust test instances to distribute testing load over multiple CPU cores and bypass the GIL 	| The singular Locust worker was not constrained by CPU usage and spawning new workers would lead to further contention 	|
| Increasing the buffer size of the Redis worker to allow for even larger COPY payloads                     	| Plausible in theory, but limited performance benefits in testing                                                      	|

The final implementation achieved over 1200 RPS, maintaining a 36 ms median latency and a 99th percentile (p99) of 98 ms.

<img width="2754" height="1146" alt="locust_results" src="https://github.com/user-attachments/assets/a2e66b95-32cf-4b80-92f6-c4550ff33f29" />

A major limitation of this experiment was that the FastAPI application, Redis worker, PostgreSQL database, and Locust test were all being run on my laptop (8-core Intel Ultra 7 with 32 GB of RAM on Windows 11). These environment and hardware constraints likely limited my final results.

An additional output from this project was a tool to visualize the execution trace of the asyncpg event loop. More details and some visualizations here: https://github.com/davidmenggx/iot-firehose-visualizer

AI Use: I tried to use minimal AI assistance, and primarily for conceptual questions if needed
