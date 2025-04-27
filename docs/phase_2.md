<img title="" src="https://iconape.com/wp-content/files/fd/372393/svg/372393.svg" alt="ASU" width="339" data-align="center">

<p align="center"><strong><h5 style="text-align: center; font-size: large;">Ain Shams University Faculty of Engineering</h5></strong></p>
<p align="center"><strong><h5 style="text-align: center; font-size: large;">Computer Engineering and Software Systems</h5></strong></p>
<p align="center"><strong><h5 style="text-align: center; font-size: large;">Credit Hours Engineering Programs (iCHEP)</h5></strong></p>

<div align="center"> Course Name: <strong>Distributed Computing</strong> </div>
<div align="center"> Course Code: <strong>CSE354</strong> </div>
<div align="center"> Academic Year: <strong>Spring 2024</strong></div>

| Student Name                    | ID(ASU)     |
| ------------------------------- |:-----------:|
| **Omar Osama**                  | **2101757** |
| **Ahmed Mohamed Salah**         | **2100669** |
| **Ahmad Muhammad Abdelmaksoud** | **2101077** |
| **Belal Anas Seddik Awad**      | **21P0072** |

# Project: Distributed Web Crawling and Indexing System using Cloud Computing

**Submitted to:**

    **Dr. Ayman Bahaa**

    **Eng. A'laa and Ashraf**

<div style="page-break-before:always;"></div>

# Phase 2: Distributed Web Crawling and Indexing System

## Objective

- **Pipeline**: Master distributes URLs to Crawlers via message queue.

- **Crawler**: Fetch pages, extract links/text, follow politeness.

- **Communication**: Crawlers send URLs, status, and content via queues.

- **Indexer**: Store page content in a searchable index.

- **Integration**: Connect all components into a working system.

---

**Table of Contetns**

1. [Component Implementation Details](#1-component-implementation-details)
   - [Master Node](#11-master-node)
   - [Crawler Node(s)](#12-crawler-nodes)
   - [Indexer Node](#13-indexer-node)
   - [Task Queues](#14-task-queues)
2. [Integration and Workflow](#2-integration-and-workflow)
3. [Testing and Results](#3-testing-and-results)

---

## 1. Component Implementation Details

### 1.1. Master Node

* **Task Distribution:**
  - Implements batch processing with configurable batch size (default: 10 URLs per batch)
  - Uses Celery task queue for distributed task assignment
  - Maintains separate queues for crawlers and indexers
  - Implements task deduplication using sets (urls_to_crawl, processing_urls, completed_urls)
  - Features automatic task reassignment on node failures
  - Tracks task status and results using AsyncResult objects

* **Result Handling:** 
  - Processes completed tasks asynchronously
  - Extracts new URLs from crawled pages
  - Updates task metrics (created, completed, failed)
  - Maintains URL state (to crawl, processing, completed)
  - Implements error handling and recovery
  - Logs detailed task completion status and metrics

* **Libraries Used:** 
  - `mpi4py`: For distributed computing and node communication
  - `celery`: For task queue management and distribution
  - `redis`: As message broker and result backend
  - `logging`: For comprehensive system logging
  - `typing`: For type hints and code documentation
  - `uuid`: For generating unique task and batch IDs
  - `time`: For timing operations and heartbeat management

* **Code Snippet:**
  
  ```python
  class MasterNode:
      def __init__(self):
          # MPI setup
          self.comm = MPI.COMM_WORLD
          self.rank = self.comm.Get_rank()
          self.size = self.comm.Get_size()
          
          # Task management
          self.urls_to_crawl: Set[str] = set()
          self.processing_urls: Set[str] = set()
          self.completed_urls: Set[str] = set()
          self.task_results: Dict[str, AsyncResult] = {}
          self.batch_size = 10
          
          # Performance metrics
          self.metrics = {
              'tasks_created': 0,
              'tasks_completed': 0,
              'tasks_failed': 0,
              'urls_discovered': 0,
              'node_failures': 0,
              'start_time': time.time()
          }

      def assign_tasks_to_crawlers(self, batch: List[str]) -> None:
          """Assign a batch of URLs to crawler nodes via the task queue."""
          if not batch:
              return
              
          batch_id = str(uuid.uuid4())
          logger.info(f"Assigning batch {batch_id} with {len(batch)} URLs to crawlers")
          
          # Create tasks for the batch
          tasks = []
          for url in batch:
              task_id = str(uuid.uuid4())
              task = crawl_url.apply_async(
                  args=[url, task_id],
                  queue=self.crawler_queue,
                  task_id=task_id
              )
              tasks.append(task)
              self.task_results[task_id] = task
              self.metrics['tasks_created'] += 1

      def process_task_results(self):
          """Process completed task results."""
          completed_tasks = []
          
          for task_id, result in self.task_results.items():
              if result.ready():
                  try:
                      task_result = result.get()
                      
                      # Process new URLs
                      if 'new_urls' in task_result:
                          new_urls = set(task_result['new_urls']) - self.completed_urls - self.processing_urls
                          self.urls_to_crawl.update(new_urls)
                          self.metrics['urls_discovered'] += len(new_urls)
                      
                      # Update URL states
                      if 'url' in task_result:
                          self.completed_urls.add(task_result['url'])
                          self.processing_urls.discard(task_result['url'])
                          self.metrics['tasks_completed'] += 1
                      
                      completed_tasks.append(task_id)
                      
                  except Exception as e:
                      logger.error(f"Error processing task {task_id}: {e}")
                      self.metrics['tasks_failed'] += 1
                      completed_tasks.append(task_id)
          
          # Cleanup completed tasks
          for task_id in completed_tasks:
              del self.task_results[task_id]
  ```

* **Key Features:**
  - Distributed task processing using MPI
  - Asynchronous task execution with Celery
  - Robust error handling and recovery
  - Comprehensive performance metrics
  - Detailed logging and monitoring
  - Automatic task reassignment on failures
  - Efficient URL deduplication
  - Configurable batch processing

* **Performance Considerations:**
  - Uses sets for O(1) URL lookup and deduplication
  - Implements batch processing to reduce overhead
  - Maintains task state for efficient tracking
  - Implements heartbeat system for node health monitoring
  - Features automatic cleanup of completed tasks
  - Provides detailed metrics for performance monitoring

### 1.2. Crawler Node(s)

* 

* **Task Reception:** 

* **Fetching:** 

* **Parsing & Extraction:** 

* **Politeness:** 

* **Data Transmission:** 

* **Libraries Used:** 

* **Code Snippet:**
  
  ```python
  ###code
  ```

### 1.3. Indexer Node

* 

* **Data Reception:** 

* **Indexing Logic:** 

* **Content Processing:** 

* **Index Storage:** 

* **Search Functionality:** 

* **Libraries Used:** 

* **Code Snippet:**
  
  ```python
  ###code
  ```

### 1.4. Task Queues

* **Queues Created:** 
  - `crawler_queue`: Dedicated queue for URL crawling tasks
  - `indexer_queue`: Queue for content indexing tasks
  - `monitoring_queue`: Queue for system health monitoring and heartbeats

* **Purpose & Message Format:** 
  ```python
  # Queue Configuration
  app.conf.update(
      task_serializer='json',
      accept_content=['json'],
      result_serializer='json',
      timezone='UTC',
      enable_utc=True,
      worker_prefetch_multiplier=1,  # Process one task at a time
      task_acks_late=True,  # Tasks are acknowledged after completion
      task_track_started=True,  # Track when tasks are started
      task_routes={
          'tasks.crawl_url': {'queue': 'crawler_queue'},
          'tasks.index_content': {'queue': 'indexer_queue'},
          'tasks.heartbeat': {'queue': 'monitoring_queue'}
      }
  )
  ```

* **Message Types & Formats:**

  1. **Crawler Tasks:**
     ```python
     {
         'task_id': str,          # Unique task identifier
         'url': str,              # URL to crawl
         'status': str,           # Task status
         'new_urls': List[str],   # Discovered URLs
         'timestamp': float       # Task creation time
     }
     ```

  2. **Indexer Tasks:**
     ```python
     {
         'content': {
             'title': str,        # Page title
             'text': str,         # Page content
             'url': str           # Source URL
         },
         'status': str,          # Indexing status
         'timestamp': float      # Task creation time
     }
     ```

  3. **Heartbeat Messages:**
     ```python
     {
         'node_id': str,         # Node identifier
         'status': str,          # Node status
         'timestamp': float      # Heartbeat time
     }
     ```


## 2. Integration and Workflow

* **End-to-End Crawl Flow:** 
* **End-to-End Indexing Flow:**
* **Integration Points:** 

## 3. Testing and Results

* **Unit Testing:** 
  
  - Master Node:
    
    
  
  - Crawler Node/s:
    
    
  
  - Indexer Node/s:
    
    

* **Integration Testing:** 
  
  ```sh
  ❯ ./run_system_test.sh
  Starting Redis server...
  Starting Celery workers...
  Crawler worker started
  Indexer worker started
  Monitoring worker started
  Starting master node with MPI...
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Crawler Nodes: [1, 2]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Indexer Nodes: [3]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Crawler Nodes: [1, 2]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Indexer Nodes: [3]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Crawler Nodes: [1, 2]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Indexer Nodes: [3]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Crawler Nodes: [1, 2]
  2025-04-27 22:26:09,690 - __main__ - INFO - Active Indexer Nodes: [3]
  2025-04-27 22:26:09,690 - __main__ - INFO - 
  ```

* **Results:** 
  - Start
  ```sh
  System State:
      Runtime: 0.00 seconds
      Active Nodes: 3/4
      URLs to Crawl: 2
      Processing URLs: 0
      Completed URLs: 0
      Tasks Created: 0
      Tasks Completed: 0
      Tasks Failed: 0
      Node Failures: 0
  ```
  - End
  ```sh
  System State:
    Runtime: 1.06 seconds
    Active Nodes: 3/4
    URLs to Crawl: 0
    Processing URLs: 0
    Completed URLs: 2
    Tasks Created: 2
    Tasks Completed: 2
    Tasks Failed: 0
    Node Failures: 0
  ```

