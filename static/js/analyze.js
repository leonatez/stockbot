// Analyze page specific functionality

// Global variables
let sources = [];
let currentEditingIndex = -1;

// DOM elements
const addNewPageBtn = document.getElementById("addNewPageBtn");
const sourcesList = document.getElementById("sourcesList");
const emptyState = document.getElementById("emptyState");
const crawlSection = document.getElementById("crawlSection");
const crawlAllBtn = document.getElementById("crawlAllBtn");
const debugMode = document.getElementById("debugMode");
const crawlDays = document.getElementById("crawlDays");
const crawlText = document.getElementById("crawlText");
const crawlLoadingIcon = document.getElementById("crawlLoadingIcon");
const resultsContainer = document.getElementById("resultsContainer");
const errorBox = document.getElementById("errorBox");
const errorText = document.getElementById("errorText");

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Analyze page
    loadSourcesFromDatabase();
    
    // Add event listeners
    if (addNewPageBtn) {
        addNewPageBtn.addEventListener("click", showNewSourceForm);
    }
    if (crawlAllBtn) {
        crawlAllBtn.addEventListener("click", crawlAllSources);
    }
});

// Load sources from database
async function loadSourcesFromDatabase() {
    try {
        const response = await fetch("/sources", {
            method: "GET",
            headers: { "Content-Type": "application/json" },
            mode: 'cors'
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result = await response.json();
        sources = result.sources.map(dbSource => ({
            url: dbSource.url,
            sourceName: dbSource.name,
            sourceType: dbSource.source_type || "company",
            xpath: dbSource.xpath_title || "",
            pagination: dbSource.pagination_rule || "",
            contentXpath: dbSource.xpath_content || "",
            contentDateXpath: dbSource.xpath_date || "",
            contentType: dbSource.content_type || "text",
            status: dbSource.status || "active",
            id: dbSource.id
        }));
        
        updateSourcesList();
    } catch (error) {
        console.error("Error loading sources:", error);
        showErrorMessage("Failed to load sources from database");
    }
}

function updateSourcesList() {
    if (sources.length === 0) {
        emptyState.classList.remove("hidden");
        crawlSection.classList.add("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    crawlSection.classList.remove("hidden");
    
    const sourcesHtml = sources.map((source, index) => `
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <div class="flex items-start justify-between mb-4">
                <div class="flex-1">
                    <div class="flex items-center space-x-3 mb-2">
                        <h4 class="text-lg font-semibold text-dark">${source.sourceName}</h4>
                        <span class="px-2 py-1 text-xs font-medium rounded-full ${getSourceTypeColor(source.sourceType)}">
                            ${source.sourceType}
                        </span>
                        <span class="px-2 py-1 text-xs font-medium rounded-full ${source.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                            ${source.status}
                        </span>
                    </div>
                    <p class="text-sm text-gray-600 mb-2">${source.url}</p>
                    <p class="text-xs text-gray-500">Content Type: ${source.contentType}</p>
                </div>
                <div class="flex items-center space-x-2">
                    <button class="text-${source.status === 'active' ? 'green' : 'gray'}-500 hover:text-${source.status === 'active' ? 'green' : 'gray'}-700 p-1" onclick="toggleSourceStatus(${index})" title="Toggle Active/Inactive">
                        <i class="fas fa-power-off"></i>
                    </button>
                    <button class="text-purple-500 hover:text-purple-700 p-1" onclick="duplicateSource(${index})" title="Duplicate Source">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button class="text-primary hover:text-blue-600 p-1" onclick="editSource(${index})" title="Edit Source">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="text-red-500 hover:text-red-700 p-1" onclick="deleteSource(${index})" title="Delete Source">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    sourcesList.innerHTML = sourcesHtml;
}

function getSourceTypeColor(sourceType) {
    switch (sourceType) {
        case 'company':
            return 'bg-blue-100 text-blue-800';
        case 'industry':
            return 'bg-purple-100 text-purple-800';
        case 'macro_economy':
            return 'bg-green-100 text-green-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

function showNewSourceForm() {
    currentEditingIndex = -1; // Reset editing index for new source
    const modal = createSourceModal();
    document.body.appendChild(modal);
    modal.classList.remove('hidden');
}

function createSourceModal() {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
    modal.id = 'sourceModal';
    
    modal.innerHTML = `
        <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div class="p-6 border-b border-gray-200">
                <div class="flex items-center justify-between">
                    <h3 class="text-xl font-bold text-dark">Add New Source</h3>
                    <button onclick="closeSourceModal()" class="text-gray-400 hover:text-gray-600 p-1">
                        <i class="fas fa-times text-lg"></i>
                    </button>
                </div>
            </div>
            
            <form id="sourceForm" class="p-6 space-y-6">
                <!-- Basic Information -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Source Name *</label>
                        <input type="text" id="sourceName" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent" placeholder="e.g., ACBS Research">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Source Type *</label>
                        <select id="sourceType" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent">
                            <option value="">Select type...</option>
                            <option value="company">Company News</option>
                            <option value="industry">Industry Analysis</option>
                            <option value="macro_economy">Macro Economy</option>
                        </select>
                    </div>
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">URL *</label>
                    <input type="url" id="sourceUrl" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent" placeholder="https://example.com/news">
                </div>
                
                <!-- XPath Configuration -->
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-semibold text-gray-800 mb-3">XPath Selectors</h4>
                    <div class="space-y-3">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Posts Container XPath *</label>
                            <input type="text" id="xpathPosts" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm font-mono" placeholder="//div[@class='post-item']">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Content XPath *</label>
                            <input type="text" id="xpathContent" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm font-mono" placeholder=".//div[@class='content']">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Date XPath</label>
                            <input type="text" id="xpathDate" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm font-mono" placeholder=".//span[@class='date']">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Title XPath</label>
                            <input type="text" id="xpathTitle" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm font-mono" placeholder=".//h3[@class='title']">
                        </div>
                    </div>
                </div>
                
                <!-- Advanced Options -->
                <div class="bg-blue-50 p-4 rounded-lg">
                    <h4 class="font-semibold text-gray-800 mb-3">Advanced Options</h4>
                    <div class="space-y-3">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Content Type</label>
                            <select id="contentType" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent">
                                <option value="text">Text</option>
                                <option value="pdf">PDF</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                            <select id="sourceStatus" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent">
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Pagination Rule</label>
                            <input type="text" id="paginationRule" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm font-mono" placeholder="Optional pagination rules">
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                    <button type="button" onclick="closeSourceModal()" class="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
                        Cancel
                    </button>
                    <button type="submit" class="bg-primary hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors font-medium">
                        Add Source
                    </button>
                </div>
            </form>
        </div>
    `;
    
    // Add form submit handler
    modal.querySelector('#sourceForm').addEventListener('submit', handleSourceSubmit);
    
    return modal;
}

function closeSourceModal() {
    const modal = document.getElementById('sourceModal');
    if (modal) {
        modal.remove();
    }
}

async function handleSourceSubmit(e) {
    e.preventDefault();
    
    const formData = {
        url: document.getElementById('sourceUrl').value,
        sourceName: document.getElementById('sourceName').value,
        sourceType: document.getElementById('sourceType').value,
        xpath: document.getElementById('xpathPosts').value,
        contentXpath: document.getElementById('xpathContent').value,
        contentDateXpath: document.getElementById('xpathDate').value,
        contentType: document.getElementById('contentType').value || 'text'
    };
    
    // Only include optional fields if they have values
    const paginationValue = document.getElementById('paginationRule').value;
    if (paginationValue && paginationValue.trim()) {
        formData.pagination = paginationValue;
    }
    
    // Debug: log the data being sent
    console.log('Sending form data:', formData);
    
    try {
        let response;
        let successMessage;
        
        if (currentEditingIndex >= 0) {
            // Editing existing source
            const sourceId = sources[currentEditingIndex].id;
            response = await fetch(`/sources/${sourceId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            successMessage = 'Source updated successfully!';
        } else {
            // Adding new source
            response = await fetch('/sources', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            successMessage = 'Source added successfully!';
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to save source');
        }
        
        const result = await response.json();
        showSuccessMessage(successMessage);
        closeSourceModal();
        currentEditingIndex = -1; // Reset editing index
        loadSourcesFromDatabase(); // Reload the sources list
        
    } catch (error) {
        console.error('Error saving source:', error);
        showErrorMessage(`Failed to add source: ${error.message}`);
    }
}

function editSource(index) {
    currentEditingIndex = index;
    const source = sources[index];
    
    const modal = createSourceModal();
    document.body.appendChild(modal);
    
    // Pre-fill the form with existing source data
    document.getElementById('sourceName').value = source.sourceName;
    document.getElementById('sourceType').value = source.sourceType;
    document.getElementById('sourceUrl').value = source.url;
    document.getElementById('xpathPosts').value = source.xpath;
    document.getElementById('xpathContent').value = source.contentXpath;
    document.getElementById('xpathDate').value = source.contentDateXpath;
    document.getElementById('paginationRule').value = source.pagination || '';
    document.getElementById('contentType').value = source.contentType;
    document.getElementById('sourceStatus').value = source.status;
    
    // Update modal title and button text
    modal.querySelector('h3').textContent = 'Edit Source';
    modal.querySelector('button[type="submit"]').textContent = 'Update Source';
    
    modal.classList.remove('hidden');
}

function duplicateSource(index) {
    currentEditingIndex = -1; // Set to create mode
    const source = sources[index];
    
    const modal = createSourceModal();
    document.body.appendChild(modal);
    
    // Pre-fill the form with duplicated source data
    document.getElementById('sourceName').value = `${source.sourceName} (Copy)`;
    document.getElementById('sourceType').value = source.sourceType;
    // Append a query parameter to make URL unique
    const originalUrl = source.url;
    const urlSeparator = originalUrl.includes('?') ? '&' : '?';
    document.getElementById('sourceUrl').value = `${originalUrl}${urlSeparator}copy=${Date.now()}`;
    document.getElementById('xpathPosts').value = source.xpath;
    document.getElementById('xpathContent').value = source.contentXpath;
    document.getElementById('xpathDate').value = source.contentDateXpath;
    document.getElementById('paginationRule').value = source.pagination || '';
    document.getElementById('contentType').value = source.contentType;
    document.getElementById('sourceStatus').value = 'inactive'; // Default new duplicates to inactive
    
    // Update modal title to indicate duplication
    modal.querySelector('h3').textContent = 'Duplicate Source';
    modal.querySelector('button[type="submit"]').textContent = 'Create Duplicate';
    
    modal.classList.remove('hidden');
}

async function toggleSourceStatus(index) {
    const source = sources[index];
    const newStatus = source.status === 'active' ? 'inactive' : 'active';
    
    try {
        const response = await fetch(`/sources/${source.id}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to update source status');
        }
        
        // Update local state
        sources[index].status = newStatus;
        updateSourcesList();
        
        showSuccessMessage(`Source ${newStatus === 'active' ? 'activated' : 'deactivated'} successfully!`);
        
    } catch (error) {
        console.error('Error toggling source status:', error);
        showErrorMessage(`Failed to toggle source status: ${error.message}`);
    }
}

async function deleteSource(index) {
    const source = sources[index];
    if (!confirm(`Are you sure you want to delete "${source.sourceName}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/sources/${source.id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        
        // Remove from frontend array
        sources.splice(index, 1);
        updateSourcesList();
        
console.log("Deleting source:", source);
        showSuccessMessage(`Source "${source.sourceName}" deleted successfully`);
        
    } catch (error) {
        console.error('Error deleting source:', error);
        showErrorMessage(`Failed to delete source: ${error.message}`);
    }
}

async function crawlAllSources() {
    if (sources.length === 0) {
        showErrorMessage("No sources configured. Please add sources first.");
        return;
    }

    try {
        // Update UI
        crawlAllBtn.disabled = true;
        crawlLoadingIcon.className = "fas fa-spinner fa-spin mr-2";
        crawlText.textContent = "Analyzing...";
        resultsContainer.classList.add("hidden");
        errorBox.classList.add("hidden");

        const isDebug = debugMode.checked;
        const selectedDays = parseInt(crawlDays.value);
        
        // Filter only active sources and convert to the format expected by the API
        const activeSources = sources
            .filter(source => source.status === 'active')
            .map(source => ({
                url: source.url,
                sourceName: source.sourceName,
                sourceType: source.sourceType,
                xpath: source.xpath,
                pagination: source.pagination,
                contentXpath: source.contentXpath,
                contentDateXpath: source.contentDateXpath,
                contentType: source.contentType
            }));

        if (activeSources.length === 0) {
            throw new Error("No active sources found. Please activate at least one source.");
        }

        const response = await fetch("/crawl-multiple", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sources: activeSources,
                debug: isDebug,
                days: selectedDays
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Analysis failed");
        }

        const result = await response.json();
        displayAnalysisResults(result);

    } catch (error) {
        console.error("Analysis error:", error);
        showError(error.message);
    } finally {
        // Reset button
        setTimeout(() => {
            crawlAllBtn.disabled = false;
            crawlLoadingIcon.className = "fas fa-search mr-2";
            crawlText.textContent = "Start Analysis";
        }, 2000);
    }
}

function displayAnalysisResults(result) {
    if (!result.stocks || result.stocks.length === 0) {
        resultsContainer.innerHTML = `
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
                <div class="text-center">
                    <i class="fas fa-chart-line text-6xl text-gray-300 mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">No Results Found</h3>
                    <p class="text-gray-500">No stock mentions were found in the configured sources.</p>
                </div>
            </div>
        `;
    } else {
        const resultsHtml = `
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 class="text-xl font-bold text-dark mb-4 flex items-center">
                    <i class="fas fa-chart-bar text-primary mr-3"></i>
                    Analysis Results
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${result.stocks.map(stock => `
                        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                            <div class="flex items-center justify-between mb-2">
                                <span class="font-semibold text-lg">${stock.symbol}</span>
                                <span class="px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(stock.sentiment)}">
                                    ${stock.sentiment}
                                </span>
                            </div>
                            <p class="text-sm text-gray-600 mb-2">${stock.name}</p>
                            <p class="text-xs text-gray-500">${stock.posts_count} mentions</p>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-4 p-4 bg-blue-50 rounded-lg">
                    <p class="text-sm text-blue-700">
                        Found <strong>${result.stocks.length}</strong> stocks mentioned across all sources.
                    </p>
                </div>
            </div>
        `;
        resultsContainer.innerHTML = resultsHtml;
    }
    
    resultsContainer.classList.remove("hidden");
}

function showError(message) {
    errorText.textContent = message;
    errorBox.classList.remove("hidden");
    resultsContainer.classList.add("hidden");
}

function getSentimentColor(sentiment) {
    switch (sentiment?.toLowerCase()) {
        case 'positive':
            return 'bg-green-100 text-green-800';
        case 'negative':
            return 'bg-red-100 text-red-800';
        case 'neutral':
            return 'bg-gray-100 text-gray-800';
        default:
            return 'bg-gray-100 text-gray-600';
    }
}