// News page specific functionality

// Global variables
let currentStocksData = [];
const chartInstances = {};

// DOM elements
const dashboardDays = document.getElementById("dashboardDays");
const refreshStocksBtn = document.getElementById("refreshStocksBtn");
const stocksContent = document.getElementById("stocksContent");
const stocksLoading = document.getElementById("stocksLoading");

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize News page
    loadVNIndexChart();
    loadRecentStocks();
    
    // Add event listeners
    if (refreshStocksBtn) {
        refreshStocksBtn.addEventListener("click", loadRecentStocks);
    }
    if (dashboardDays) {
        dashboardDays.addEventListener("change", loadRecentStocks);
    }
    
    // Add filter event listeners
    setupFilterEventListeners();
});

// VNINDEX Chart functionality
async function loadVNIndexChart(period = '1M') {
    const loadingEl = document.getElementById('vnindexLoading');
    const errorEl = document.getElementById('vnindexError');
    const canvas = document.getElementById('vnindexChart');

    try {
        loadingEl.classList.remove('hidden');
        errorEl.classList.add('hidden');

        // Fetch real VNINDEX data from our API
        const response = await fetch(`/vnindex-data?period=${period}`);
        const result = await response.json();
        
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Failed to fetch VNINDEX data');
        }
        
        // Update price display if elements exist
        const priceEl = document.getElementById('vnindexPrice');
        const changeEl = document.getElementById('vnindexChange');
        
        if (priceEl) {
            priceEl.textContent = result.latest_price.toFixed(2);
        }
        
        if (changeEl) {
            const isPositive = result.price_change >= 0;
            changeEl.innerHTML = `
                <span class="${isPositive ? 'text-green-600' : 'text-red-600'}">
                    <i class="fas fa-arrow-${isPositive ? 'up' : 'down'} mr-1"></i>
                    ${result.price_change.toFixed(2)} (${result.price_change_percent.toFixed(2)}%)
                </span>
            `;
        }

        // Destroy existing chart
        if (chartInstances['vnindex']) {
            chartInstances['vnindex'].destroy();
        }

        // Create new chart with real data
        const ctx = canvas.getContext('2d');
        chartInstances['vnindex'] = new Chart(ctx, result.chart_config);
        
        console.log(`VNINDEX chart loaded with ${result.data_points} data points for period ${period}`);

        loadingEl.classList.add('hidden');
    } catch (error) {
        console.error('Error loading VN-Index chart:', error);
        loadingEl.classList.add('hidden');
        errorEl.classList.remove('hidden');
        
        // Show detailed error message
        if (errorEl) {
            errorEl.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-exclamation-triangle text-orange-500 mb-2"></i>
                    <p class="text-sm text-gray-600">
                        Failed to load VNINDEX data: ${error.message}
                    </p>
                </div>
            `;
        }
    }
}

// VNINDEX period button handlers
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('vnindex-period-btn')) {
        const period = e.target.dataset.period;
        
        // Update button states
        document.querySelectorAll('.vnindex-period-btn').forEach(btn => {
            btn.classList.remove('bg-primary', 'text-white');
            btn.classList.add('text-gray-600', 'hover:bg-gray-100');
        });
        
        e.target.classList.remove('text-gray-600', 'hover:bg-gray-100');
        e.target.classList.add('bg-primary', 'text-white');
        
        // Load chart with new period
        loadVNIndexChart(period);
    }
});

// Load recent stocks with modern styling
async function loadRecentStocks() {
    try {
        const days = dashboardDays.value;
        
        if (stocksContent) {
            stocksContent.innerHTML = `
                <div class="text-center py-12">
                    <i class="fas fa-spinner fa-spin text-3xl text-primary mb-4"></i>
                    <p class="text-gray-500 text-lg">Loading trending stocks...</p>
                </div>
            `;
        }
        
        const response = await fetch(`/recent-stocks?days=${days}`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
            mode: 'cors'
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const result = await response.json();
        
        // If no real data is available, show empty state
        if (!result.stocks || result.stocks.length === 0) {
            console.log("No stock data found");
        }
        
        displayRecentStocks(result.stocks, days);
        
    } catch (error) {
        console.error("Error loading recent stocks:", error);
        if (stocksContent) {
            stocksContent.innerHTML = `
                <div class="text-center py-12">
                    <i class="fas fa-exclamation-triangle text-3xl text-red-500 mb-4"></i>
                    <p class="text-gray-500 text-lg">Unable to load stock data</p>
                    <button onclick="loadRecentStocks()" class="mt-4 bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors text-sm">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
}

function displayRecentStocks(stocks, days) {
    if (!stocks || stocks.length === 0) {
        stocksContent.innerHTML = `
            <div class="text-center py-16">
                <i class="fas fa-chart-line text-6xl text-gray-300 mb-6"></i>
                <h3 class="text-xl font-semibold text-gray-600 mb-2">No trending stocks found</h3>
                <p class="text-gray-500 mb-6">No stocks were mentioned in the last ${days} days</p>
                <button onclick="window.location.href='/analyze'" class="bg-primary hover:bg-blue-600 text-white px-6 py-3 rounded-lg transition-colors font-medium">
                    Configure Sources
                </button>
            </div>
        `;
        return;
    }

    const stocksHtml = stocks.map(stock => {
        const sentimentColor = getSentimentColor(stock.sentiment);
        
        const postsHtml = (stock.posts || []).map(post => `
            <div class="bg-white border border-gray-100 rounded-lg p-4 mb-3 hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex-1">
                        <div class="flex items-center space-x-3 mb-2">
                            <span class="text-xs font-medium text-primary bg-blue-50 px-2 py-1 rounded-full">${post.source_name}</span>
                            <span class="px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(post.sentiment)}">
                                ${post.sentiment}
                            </span>
                            <span class="text-xs text-gray-500">${formatDate(post.created_date)}</span>
                        </div>
                        <a href="${post.url}" target="_blank" class="text-sm text-gray-700 hover:text-primary line-clamp-2 leading-relaxed">
                            ${post.summary}
                        </a>
                    </div>
                    <a href="${post.url}" target="_blank" class="ml-3 text-primary hover:text-blue-600 p-1">
                        <i class="fas fa-external-link-alt text-xs"></i>
                    </a>
                </div>
                ${post.stock_mention_summary ? `
                    <div class="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 mt-2">
                        <span class="font-medium text-dark">About ${stock.symbol}:</span> ${post.stock_mention_summary}
                    </div>
                ` : ''}
            </div>
        `).join('');
        
        return `
            <div class="bg-white border border-gray-100 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-12 h-12 bg-gradient-to-r from-primary to-secondary rounded-xl flex items-center justify-center">
                            <span class="text-white font-bold text-lg">${stock.symbol}</span>
                        </div>
                        <div>
                            <h3 class="font-bold text-lg text-dark">${stock.symbol}</h3>
                            ${stock.isvn30 ? '<span class="inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full border border-yellow-200"><i class="fas fa-star mr-1"></i>VN30</span>' : ''}
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="flex items-center space-x-2 mb-1">
                            <span class="px-3 py-1 rounded-full text-sm font-medium ${sentimentColor}">
                                ${stock.sentiment}
                            </span>
                        </div>
                        <p class="text-xs text-gray-500">${stock.posts_count} posts</p>
                    </div>
                </div>
                
                <div class="mb-4">
                    <p class="text-sm text-gray-600 leading-relaxed">
                        <strong>${stock.name}</strong> • ${stock.exchange}
                    </p>
                </div>
                
                <div class="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-4">
                    <h4 class="text-sm font-semibold text-blue-800 mb-2 flex items-center">
                        <i class="fas fa-chart-line mr-2"></i>Market Sentiment
                    </h4>
                    <p class="text-sm text-blue-700 leading-relaxed">
                        ${stock.summary || 'No analysis summary available'}
                    </p>
                </div>
                
                <div>
                    <div class="flex items-center justify-between mb-3">
                        <h4 class="text-sm font-semibold text-dark flex items-center">
                            <i class="fas fa-newspaper mr-2 text-primary"></i>Recent Posts
                        </h4>
                        <span class="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs font-medium">
                            ${stock.posts_count}
                        </span>
                    </div>
                    <div class="max-h-80 overflow-y-auto space-y-2">
                        ${postsHtml || '<p class="text-sm text-gray-500 italic text-center py-4">No posts available</p>'}
                    </div>
                </div>
                
                <div class="pt-4 border-t border-gray-100 mt-4">
                    <div class="flex items-center justify-between text-xs text-gray-500">
                        <span>Last updated: ${formatDate(stock.last_updated)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    stocksContent.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            ${stocksHtml}
        </div>
        <div class="text-center mt-8 p-4 bg-gray-50 rounded-lg">
            <p class="text-sm text-gray-600">
                Showing <span class="font-semibold text-dark">${stocks.length}</span> trending stocks from the last <span class="font-semibold text-dark">${days}</span> days
            </p>
        </div>
    `;

    // Store data for filtering
    currentStocksData = stocks;
}

// Utility functions
function getSentimentColor(sentiment) {
    switch (sentiment?.toLowerCase()) {
        case 'positive':
            return 'bg-green-100 text-green-800 border border-green-200';
        case 'negative':
            return 'bg-red-100 text-red-800 border border-red-200';
        case 'neutral':
            return 'bg-gray-100 text-gray-800 border border-gray-200';
        default:
            return 'bg-gray-100 text-gray-600 border border-gray-200';
    }
}

// Filter functionality
function setupFilterEventListeners() {
    const stockSearch = document.getElementById('stockSearch');
    const sentimentFilter = document.getElementById('sentimentFilter');
    const vn30Filter = document.getElementById('vn30Filter');
    const sortBy = document.getElementById('sortBy');
    const sortOrder = document.getElementById('sortOrder');
    const clearFilters = document.getElementById('clearFilters');

    // Add event listeners for all filters
    [stockSearch, sentimentFilter, vn30Filter, sortBy, sortOrder].forEach(element => {
        if (element) {
            element.addEventListener('change', applyFilters);
            if (element.type === 'text') {
                element.addEventListener('input', debounce(applyFilters, 300));
            }
        }
    });

    if (clearFilters) {
        clearFilters.addEventListener('click', clearAllFilters);
    }
}

function applyFilters() {
    if (!currentStocksData || currentStocksData.length === 0) return;

    const stockSearch = document.getElementById('stockSearch').value.toLowerCase();
    const sentimentFilter = document.getElementById('sentimentFilter').value;
    const vn30Filter = document.getElementById('vn30Filter').value;
    const sortBy = document.getElementById('sortBy').value;
    const sortOrder = document.getElementById('sortOrder').value;

    let filteredStocks = [...currentStocksData];

    // Apply filters
    if (stockSearch) {
        filteredStocks = filteredStocks.filter(stock => 
            stock.symbol.toLowerCase().includes(stockSearch) ||
            stock.name.toLowerCase().includes(stockSearch)
        );
    }

    if (sentimentFilter) {
        filteredStocks = filteredStocks.filter(stock => 
            stock.sentiment?.toLowerCase() === sentimentFilter.toLowerCase()
        );
    }

    if (vn30Filter) {
        const isVn30 = vn30Filter === 'true';
        filteredStocks = filteredStocks.filter(stock => stock.isvn30 === isVn30);
    }

    // Apply sorting
    filteredStocks.sort((a, b) => {
        let aValue, bValue;
        
        switch (sortBy) {
            case 'symbol':
                aValue = a.symbol;
                bValue = b.symbol;
                break;
            case 'last_updated':
                aValue = new Date(a.last_updated);
                bValue = new Date(b.last_updated);
                break;
            case 'sentiment':
                const sentimentOrder = { 'positive': 3, 'neutral': 2, 'negative': 1 };
                aValue = sentimentOrder[a.sentiment?.toLowerCase()] || 0;
                bValue = sentimentOrder[b.sentiment?.toLowerCase()] || 0;
                break;
            case 'posts_count':
            default:
                aValue = a.posts_count || 0;
                bValue = b.posts_count || 0;
                break;
        }

        if (sortOrder === 'asc') {
            return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
        } else {
            return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
        }
    });

    displayRecentStocks(filteredStocks, dashboardDays.value);
}

function clearAllFilters() {
    document.getElementById('stockSearch').value = '';
    document.getElementById('sentimentFilter').value = '';
    document.getElementById('vn30Filter').value = '';
    document.getElementById('sortBy').value = 'posts_count';
    document.getElementById('sortOrder').value = 'desc';
    
    displayRecentStocks(currentStocksData, dashboardDays.value);
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}