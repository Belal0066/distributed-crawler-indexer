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

- **Indexer**: Store page content in a searchable index (e.g., Whoosh).

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

* **Result Handling:** 

* **Libraries Used:** 

* **Code Snippet:**
  
  ```python
  ###code
  ```

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
* **Purpose & Message Format:** 

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

