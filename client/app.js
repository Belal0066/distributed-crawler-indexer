// Configuration
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://13.61.185.63:8000' // Direct access when testing locally
    : '/api'; // Use Nginx proxy when deployed

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
    // Tab navigation
    const tabs = document.querySelectorAll('.tab-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to current tab and content
            tab.classList.add('active');
            const tabId = tab.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
            
            // Refresh data when switching to monitor tab
            if (tabId === 'monitor') {
                fetchSystemStatus();
                fetchNodeStatus();
                fetchQueueStatus();
            }
        });
    });
    
    // Form submissions
    const crawlForm = document.getElementById('crawlForm');
    const searchForm = document.getElementById('searchForm');
    
    if (crawlForm) {
        crawlForm.addEventListener('submit', handleCrawlSubmit);
    }
    
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearchSubmit);
    }
    
    // Modal
    const modal = document.getElementById('crawlDetailsModal');
    const closeBtn = document.querySelector('.close');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Close modal when clicking outside of it
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Initial data fetch
    checkSystemHealth();
    fetchRecentCrawls();
});

// System Health Check
async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        
        const statusIndicator = document.getElementById('systemStatus');
        const statusText = document.getElementById('statusText');
        
        if (data.status === 'ok') {
            statusIndicator.classList.add('online');
            statusText.textContent = 'System Online';
        } else {
            statusIndicator.classList.add('warning');
            statusText.textContent = 'System Issues Detected';
        }
    } catch (error) {
        console.error('Error checking system health:', error);
        const statusIndicator = document.getElementById('systemStatus');
        const statusText = document.getElementById('statusText');
        
        statusIndicator.classList.add('offline');
        statusText.textContent = 'System Offline';
    }
}

// Handle Crawl Form Submission
async function handleCrawlSubmit(event) {
    event.preventDefault();
    
    const seedUrlsText = document.getElementById('seedUrls').value;
    const seedUrls = seedUrlsText.split('\n').filter(url => url.trim() !== '');
    
    if (seedUrls.length === 0) {
        alert('Please enter at least one URL to crawl');
        return;
    }
    
    const crawlDepth = parseInt(document.getElementById('crawlDepth').value);
    const maxUrls = parseInt(document.getElementById('maxUrls').value);
    const followExternalLinks = document.getElementById('followExternalLinks').checked;
    const respectRobotsTxt = document.getElementById('respectRobotsTxt').checked;
    
    const crawlData = {
        urls: seedUrls,
        options: {
            depth: crawlDepth,
            max_urls: maxUrls,
            follow_external: followExternalLinks,
            respect_robots_txt: respectRobotsTxt
        }
    };
    
    try {
        const response = await fetch(`${API_URL}/crawl`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(crawlData)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert(`Crawl job started successfully. ${seedUrls.length} URLs added to queue.`);
            fetchRecentCrawls();
        } else {
            alert(`Error starting crawl: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error submitting crawl job:', error);
        alert('Error submitting crawl job. Please check console for details.');
    }
}

// Handle Search Form Submission
async function handleSearchSubmit(event) {
    event.preventDefault();
    
    const searchQuery = document.getElementById('searchQuery').value.trim();
    
    if (searchQuery === '') {
        alert('Please enter a search query');
        return;
    }
    
    const fullText = document.getElementById('fullText').checked;
    const titleOnly = document.getElementById('titleOnly').checked;
    
    let searchMode = 'all';
    if (titleOnly) searchMode = 'title';
    
    try {
        const response = await fetch(`${API_URL}/search?query=${encodeURIComponent(searchQuery)}&mode=${searchMode}`);
        const results = await response.json();
        
        displaySearchResults(results, searchQuery);
    } catch (error) {
        console.error('Error performing search:', error);
        alert('Error performing search. Please check console for details.');
    }
}

// Display Search Results
function displaySearchResults(results, query) {
    const resultsContainer = document.getElementById('searchResultsList');
    const resultsCount = document.getElementById('resultsCount');
    
    resultsContainer.innerHTML = '';
    
    if (results.results && results.results.length > 0) {
        resultsCount.textContent = `Found ${results.results.length} results for "${query}"`;
        
        results.results.forEach(result => {
            const resultElement = document.createElement('div');
            resultElement.className = 'search-result';
            
            resultElement.innerHTML = `
                <h4>${result.title || 'Untitled'}</h4>
                <div class="url">${result.url}</div>
                <div class="snippet">${result.snippet || result.description || 'No description available.'}</div>
            `;
            
            resultsContainer.appendChild(resultElement);
        });
    } else {
        resultsCount.textContent = `No results found for "${query}"`;
        resultsContainer.innerHTML = '<div class="search-result">No results found. Try different search terms or start a new crawl.</div>';
    }
}

// Fetch Recent Crawls
async function fetchRecentCrawls() {
    try {
        const response = await fetch(`${API_URL}/crawl/status`);
        const data = await response.json();
        
        const recentCrawlsList = document.getElementById('recentCrawlsList');
        recentCrawlsList.innerHTML = '';
        
        if (data.jobs && data.jobs.length > 0) {
            data.jobs.forEach(job => {
                const row = document.createElement('tr');
                
                // Format date
                const startDate = new Date(job.start_time * 1000).toLocaleString();
                
                row.innerHTML = `
                    <td>${job.id.substring(0, 8)}</td>
                    <td>${startDate}</td>
                    <td>${job.urls_added || 0}</td>
                    <td><span class="status ${job.status.toLowerCase()}">${job.status}</span></td>
                    <td>
                        <button class="btn secondary view-details" data-id="${job.id}">Details</button>
                        ${job.status === 'ACTIVE' ? `<button class="btn danger cancel-crawl" data-id="${job.id}">Cancel</button>` : ''}
                    </td>
                `;
                
                recentCrawlsList.appendChild(row);
            });
            
            // Add event listeners to detail buttons
            document.querySelectorAll('.view-details').forEach(button => {
                button.addEventListener('click', () => showCrawlDetails(button.getAttribute('data-id')));
            });
            
            // Add event listeners to cancel buttons
            document.querySelectorAll('.cancel-crawl').forEach(button => {
                button.addEventListener('click', () => cancelCrawl(button.getAttribute('data-id')));
            });
        } else {
            recentCrawlsList.innerHTML = '<tr><td colspan="5">No crawl jobs found</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching recent crawls:', error);
        document.getElementById('recentCrawlsList').innerHTML = 
            '<tr><td colspan="5">Error loading crawl jobs. Please try again later.</td></tr>';
    }
}

// Show Crawl Details
async function showCrawlDetails(crawlId) {
    try {
        const response = await fetch(`${API_URL}/crawl/${crawlId}`);
        const data = await response.json();
        
        const modal = document.getElementById('crawlDetailsModal');
        const modalContent = document.getElementById('crawlDetailsContent');
        
        // Format dates
        const startDate = new Date(data.start_time * 1000).toLocaleString();
        const endDate = data.end_time ? new Date(data.end_time * 1000).toLocaleString() : 'N/A';
        
        modalContent.innerHTML = `
            <div class="detail-group">
                <h3>Crawl Job Details</h3>
                <p><strong>ID:</strong> ${data.id}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                <p><strong>Started:</strong> ${startDate}</p>
                <p><strong>Completed:</strong> ${endDate}</p>
                <p><strong>URLs Added:</strong> ${data.urls_added || 0}</p>
                <p><strong>URLs Crawled:</strong> ${data.urls_crawled || 0}</p>
                <p><strong>URLs Failed:</strong> ${data.urls_failed || 0}</p>
                <p><strong>Depth:</strong> ${data.options?.depth || 'N/A'}</p>
            </div>
            
            <div class="detail-group">
                <h3>Seed URLs</h3>
                <ul>
                    ${data.seed_urls?.map(url => `<li>${url}</li>`).join('') || '<li>No seed URLs found</li>'}
                </ul>
            </div>
        `;
        
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error fetching crawl details:', error);
        alert('Error loading crawl details. Please try again later.');
    }
}

// Cancel Crawl
async function cancelCrawl(crawlId) {
    if (confirm('Are you sure you want to cancel this crawl job?')) {
        try {
            const response = await fetch(`${API_URL}/crawl/${crawlId}/cancel`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                alert('Crawl job cancelled successfully');
                fetchRecentCrawls();
            } else {
                alert(`Error cancelling crawl: ${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error cancelling crawl:', error);
            alert('Error cancelling crawl. Please try again later.');
        }
    }
}

// Fetch System Status for Monitor Tab
async function fetchSystemStatus() {
    try {
        // Fetch queue stats
        const queueResponse = await fetch(`${API_URL}/queues/status`);
        const queueData = await queueResponse.json();
        
        // Fetch crawl stats
        const crawlResponse = await fetch(`${API_URL}/crawl/stats`);
        const crawlData = await crawlResponse.json();
        
        // Update dashboard
        document.getElementById('queueSize').textContent = queueData.total_pending || 0;
        document.getElementById('crawledUrls').textContent = crawlData.urls_crawled || 0;
        document.getElementById('indexedDocs').textContent = crawlData.docs_indexed || 0;
    } catch (error) {
        console.error('Error fetching system status:', error);
    }
}

// Fetch Node Status
async function fetchNodeStatus() {
    try {
        const response = await fetch(`${API_URL}/nodes/health`);
        const data = await response.json();
        
        const nodeStatusList = document.getElementById('nodeStatusList');
        nodeStatusList.innerHTML = '';
        
        if (data.nodes && Object.keys(data.nodes).length > 0) {
            document.getElementById('activeNodes').textContent = Object.keys(data.nodes).length;
            
            Object.entries(data.nodes).forEach(([nodeId, nodeInfo]) => {
                const row = document.createElement('tr');
                
                // Format last seen date
                const lastSeen = new Date(nodeInfo.last_seen).toLocaleString();
                
                // Format metrics
                const metrics = Object.entries(nodeInfo.metrics || {})
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(', ');
                
                row.innerHTML = `
                    <td>${nodeId.substring(0, 12)}...</td>
                    <td>${nodeInfo.node_type}</td>
                    <td><span class="status ${nodeInfo.status.toLowerCase()}">${nodeInfo.status}</span></td>
                    <td>${lastSeen}</td>
                    <td>${metrics || 'No metrics available'}</td>
                `;
                
                nodeStatusList.appendChild(row);
            });
        } else {
            document.getElementById('activeNodes').textContent = '0';
            nodeStatusList.innerHTML = '<tr><td colspan="5">No active nodes found</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching node status:', error);
        document.getElementById('nodeStatusList').innerHTML = 
            '<tr><td colspan="5">Error loading node status. Please try again later.</td></tr>';
    }
}

// Fetch Queue Status
async function fetchQueueStatus() {
    try {
        const response = await fetch(`${API_URL}/queues/status`);
        const data = await response.json();
        
        const queueStatusList = document.getElementById('queueStatusList');
        queueStatusList.innerHTML = '';
        
        if (data.queues) {
            Object.entries(data.queues).forEach(([queueName, queueInfo]) => {
                const row = document.createElement('tr');
                
                row.innerHTML = `
                    <td>${queueName}</td>
                    <td>${queueInfo.pending || 0}</td>
                    <td>${queueInfo.in_flight || 0}</td>
                    <td>${queueInfo.processed || 0}</td>
                `;
                
                queueStatusList.appendChild(row);
            });
        } else {
            queueStatusList.innerHTML = '<tr><td colspan="4">No queue information available</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching queue status:', error);
        document.getElementById('queueStatusList').innerHTML = 
            '<tr><td colspan="4">Error loading queue status. Please try again later.</td></tr>';
    }
}

// Set up polling for status updates
setInterval(checkSystemHealth, 30000); // Every 30 seconds
setInterval(() => {
    // Only update if monitor tab is active
    if (document.querySelector('.tab-item[data-tab="monitor"]').classList.contains('active')) {
        fetchSystemStatus();
        fetchNodeStatus();
        fetchQueueStatus();
    }
    
    // Update recent crawls if crawl tab is active
    if (document.querySelector('.tab-item[data-tab="crawl"]').classList.contains('active')) {
        fetchRecentCrawls();
    }
}, 10000); // Every 10 seconds 