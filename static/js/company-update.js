// Company Update page specific functionality

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Company Update page
    setupCompanyUpdateEventListeners();
});

// Company Update functionality
function setupCompanyUpdateEventListeners() {
    const updateCompanyInfoBtn = document.getElementById('updateCompanyInfoBtn');
    if (updateCompanyInfoBtn) {
        updateCompanyInfoBtn.addEventListener('click', updateCompanyInfo);
    }
    
    const updateEventsBtn = document.getElementById('updateCompanyEventsBtn');
    if (updateEventsBtn) {
        updateEventsBtn.addEventListener('click', updateCompanyEvents);
    }
    
    const updateDividendsBtn = document.getElementById('updateCompanyDividendsBtn');
    if (updateDividendsBtn) {
        updateDividendsBtn.addEventListener('click', updateCompanyDividends);
    }
    
    const updateStockPricesBtn = document.getElementById('updateStockPricesBtn');
    if (updateStockPricesBtn) {
        updateStockPricesBtn.addEventListener('click', updateStockPrices);
    }

    const updateCompanyFinanceBtn = document.getElementById('updateCompanyFinanceBtn');
    if (updateCompanyFinanceBtn) {
        updateCompanyFinanceBtn.addEventListener('click', updateCompanyFinance);
    }
}

async function updateCompanyInfo() {
    const button = document.getElementById('updateCompanyInfoBtn');
    const icon = document.getElementById('updateCompanyInfoIcon');
    const text = document.getElementById('updateCompanyInfoText');
    const progressSection = document.getElementById('companyInfoProgressSection');
    const resultsSection = document.getElementById('companyInfoResultsSection');
    const progressBar = document.getElementById('companyInfoProgressBar');
    const progressText = document.getElementById('companyInfoProgressText');
    const progressDetails = document.getElementById('companyInfoProgressDetails');
    const debugCheckbox = document.getElementById('debugCompanyInfo');
    
    // Reset UI
    button.disabled = true;
    icon.className = 'fas fa-spinner fa-spin mr-3';
    text.textContent = 'Updating...';
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    progressBar.style.width = '0%';
    
    try {
        // Step 1: Initialize
        const isDebug = debugCheckbox.checked;
        const debugText = isDebug ? ' (Debug mode: VIC only)' : '';
        progressText.textContent = `Fetching stock symbols with industry data from VNStock...${debugText}`;
        progressBar.style.width = '20%';
        
        // Step 2: Start the update process
        progressText.textContent = `Starting company info update...${debugText}`;
        progressBar.style.width = '40%';
        
        const updateResponse = await fetch('/company-info/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                debug: isDebug
            })
        });
        
        if (!updateResponse.ok) {
            const errorData = await updateResponse.json();
            throw new Error(errorData.detail || 'Company info update failed');
        }
        
        progressText.textContent = 'Processing update results...';
        progressBar.style.width = '80%';
        
        const resultData = await updateResponse.json();
        
        // Step 3: Display results
        progressText.textContent = 'Company info update completed!';
        progressBar.style.width = '100%';
        
        setTimeout(() => {
            displayCompanyInfoResults(resultData, isDebug);
            progressSection.classList.add('hidden');
            resultsSection.classList.remove('hidden');
        }, 1000);
        
    } catch (error) {
        console.error('Company info update error:', error);
        progressText.textContent = 'Update failed';
        progressDetails.textContent = `Error: ${error.message}`;
        progressBar.style.width = '0%';
        
        // Show error in results
        setTimeout(() => {
            displayCompanyInfoError(error.message);
            resultsSection.classList.remove('hidden');
        }, 1000);
    } finally {
        // Reset button
        setTimeout(() => {
            button.disabled = false;
            icon.className = 'fas fa-sync-alt mr-3';
            text.textContent = 'Update Company Info';
        }, 2000);
    }
}

function displayCompanyInfoResults(data, isDebug) {
    const statsSection = document.getElementById('companyInfoStatsSection');
    const resultsGrid = document.getElementById('companyInfoResultsGrid');
    
    // Display stats
    statsSection.innerHTML = `
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-blue-600">${data.total_stocks || 0}</div>
                <div class="text-sm text-gray-600">Total Stocks</div>
            </div>
        </div>
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-green-600">${data.successful_stocks || 0}</div>
                <div class="text-sm text-gray-600">Successfully Updated</div>
            </div>
        </div>
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-yellow-600">${data.already_updated_stocks || 0}</div>
                <div class="text-sm text-gray-600">Already Updated</div>
            </div>
        </div>
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-red-600">${data.failed_stocks?.length || 0}</div>
                <div class="text-sm text-gray-600">Failed Updates</div>
            </div>
        </div>
    `;
    
    // Display individual results
    resultsGrid.innerHTML = '';
    let resultsHTML = '';
    
    // Successful updates
    if (data.successful_updates && data.successful_updates.length > 0) {
        data.successful_updates.forEach(stock => {
            resultsHTML += `
                <div class="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div class="flex items-center gap-3">
                        <i class="fas fa-check-circle text-green-600"></i>
                        <div>
                            <div class="font-semibold text-green-800">${stock.symbol}</div>
                            <div class="text-sm text-gray-600">${stock.name || 'Updated successfully'}</div>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    // Failed updates
    if (data.failed_stocks && data.failed_stocks.length > 0) {
        data.failed_stocks.forEach(stock => {
            resultsHTML += `
                <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div class="flex items-center gap-3">
                        <i class="fas fa-times-circle text-red-600"></i>
                        <div>
                            <div class="font-semibold text-red-800">${stock.symbol}</div>
                            <div class="text-sm text-gray-600">Error: ${stock.error}</div>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    resultsGrid.innerHTML = resultsHTML;
}

function displayCompanyInfoError(errorMessage) {
    const statsSection = document.getElementById('companyInfoStatsSection');
    const resultsGrid = document.getElementById('companyInfoResultsGrid');
    
    statsSection.innerHTML = `
        <div class="col-span-full text-center p-6 bg-red-50 border border-red-200 rounded-lg">
            <div class="text-4xl text-red-500 mb-2">❌</div>
            <div class="font-semibold text-red-800">Update Failed</div>
        </div>
    `;
    
    resultsGrid.innerHTML = `
        <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-start gap-3">
                <i class="fas fa-exclamation-triangle text-red-600 text-lg mt-0.5"></i>
                <div>
                    <div class="font-semibold text-red-800">Update Error</div>
                    <div class="text-sm text-gray-600 mt-1">${errorMessage}</div>
                </div>
            </div>
        </div>
    `;
}

// Company Events Update functionality
async function updateCompanyEvents() {
    const button = document.getElementById('updateCompanyEventsBtn');
    const icon = document.getElementById('updateEventsIcon');
    const text = document.getElementById('updateEventsText');
    const progressSection = document.getElementById('eventsProgressSection');
    const resultsSection = document.getElementById('eventsResultsSection');
    const progressBar = document.getElementById('eventsProgressBar');
    const progressText = document.getElementById('eventsProgressText');
    const progressDetails = document.getElementById('eventsProgressDetails');
    const debugCheckbox = document.getElementById('debugCompanyEvents');
    
    // Reset UI
    button.disabled = true;
    icon.className = 'fas fa-spinner fa-spin mr-3';
    text.textContent = 'Updating...';
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    progressBar.style.width = '0%';
    
    try {
        const isDebug = debugCheckbox.checked;
        const debugText = isDebug ? ' (Debug mode: VIC only)' : '';
        progressText.textContent = `Getting stocks mentioned in last 30 days...${debugText}`;
        progressBar.style.width = '10%';
        
        const updateResponse = await fetch('/company-events/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                debug: isDebug
            })
        });
        
        if (!updateResponse.ok) {
            const errorData = await updateResponse.json();
            throw new Error(errorData.detail || 'Update failed');
        }
        
        progressText.textContent = 'Processing update results...';
        progressBar.style.width = '90%';
        
        const resultData = await updateResponse.json();
        
        progressText.textContent = 'Update completed!';
        progressBar.style.width = '100%';
        
        setTimeout(() => {
            displayCompanyEventsResults(resultData);
            progressSection.classList.add('hidden');
            resultsSection.classList.remove('hidden');
        }, 1000);
        
    } catch (error) {
        console.error('Events update error:', error);
        progressText.textContent = 'Update failed';
        progressDetails.textContent = `Error: ${error.message}`;
        progressBar.style.width = '0%';
        
        setTimeout(() => {
            displayCompanyUpdateError(error.message);
            resultsSection.classList.remove('hidden');
        }, 1000);
    } finally {
        setTimeout(() => {
            button.disabled = false;
            icon.className = 'fas fa-sync-alt mr-3';
            text.textContent = 'Update Company Events';
        }, 2000);
    }
}

// Company Dividends Update functionality
async function updateCompanyDividends() {
    const button = document.getElementById('updateCompanyDividendsBtn');
    const icon = document.getElementById('updateDividendsIcon');
    const text = document.getElementById('updateDividendsText');
    const progressSection = document.getElementById('dividendsProgressSection');
    const resultsSection = document.getElementById('dividendsResultsSection');
    const progressBar = document.getElementById('dividendsProgressBar');
    const progressText = document.getElementById('dividendsProgressText');
    const progressDetails = document.getElementById('dividendsProgressDetails');
    const debugCheckbox = document.getElementById('debugCompanyDividends');
    
    // Reset UI
    button.disabled = true;
    icon.className = 'fas fa-spinner fa-spin mr-3';
    text.textContent = 'Updating...';
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    progressBar.style.width = '0%';
    
    try {
        const isDebug = debugCheckbox.checked;
        const debugText = isDebug ? ' (Debug mode: VIC only)' : '';
        progressText.textContent = `Getting stocks mentioned in last 30 days...${debugText}`;
        progressBar.style.width = '10%';
        
        const updateResponse = await fetch('/company-dividends/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                debug: isDebug
            })
        });
        
        if (!updateResponse.ok) {
            const errorData = await updateResponse.json();
            throw new Error(errorData.detail || 'Update failed');
        }
        
        progressText.textContent = 'Processing update results...';
        progressBar.style.width = '90%';
        
        const resultData = await updateResponse.json();
        
        progressText.textContent = 'Update completed!';
        progressBar.style.width = '100%';
        
        setTimeout(() => {
            displayCompanyDividendsResults(resultData);
            progressSection.classList.add('hidden');
            resultsSection.classList.remove('hidden');
        }, 1000);
        
    } catch (error) {
        console.error('Dividends update error:', error);
        progressText.textContent = 'Update failed';
        progressDetails.textContent = `Error: ${error.message}`;
        progressBar.style.width = '0%';
        
        setTimeout(() => {
            displayCompanyDividendsError(error.message);
            resultsSection.classList.remove('hidden');
        }, 1000);
    } finally {
        setTimeout(() => {
            button.disabled = false;
            icon.className = 'fas fa-sync-alt mr-3';
            text.textContent = 'Update Company Dividends';
        }, 2000);
    }
}

// Stock Prices Update functionality
async function updateStockPrices() {
    const button = document.getElementById('updateStockPricesBtn');
    const icon = document.getElementById('updatePricesIcon');
    const text = document.getElementById('updatePricesText');
    const progressSection = document.getElementById('pricesProgressSection');
    const resultsSection = document.getElementById('pricesResultsSection');
    const progressBar = document.getElementById('pricesProgressBar');
    const progressText = document.getElementById('pricesProgressText');
    const progressDetails = document.getElementById('pricesProgressDetails');
    const debugCheckbox = document.getElementById('debugStockPrices');

    try {
        button.disabled = true;
        icon.className = 'fas fa-spinner fa-spin mr-3';
        text.textContent = 'Updating Stock Prices...';
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        
        progressBar.style.width = '0%';
        progressDetails.textContent = '';

        const isDebug = debugCheckbox.checked;
        const debugText = isDebug ? ' (Debug mode: VIC only)' : '';
        progressText.textContent = `Checking stocks mentioned in last 7 days...${debugText}`;
        progressBar.style.width = '20%';

        const response = await fetch('/stock-prices/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                debug: isDebug
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Update failed');
        }

        progressText.textContent = 'Processing update results...';
        progressBar.style.width = '90%';

        const result = await response.json();

        progressText.textContent = 'Update completed!';
        progressBar.style.width = '100%';

        setTimeout(() => {
            displayStockPricesResults(result);
            resultsSection.classList.remove('hidden');
            progressSection.classList.add('hidden');
        }, 1000);

    } catch (error) {
        console.error('Stock prices update error:', error);
        progressText.textContent = 'Update failed';
        progressDetails.textContent = `Error: ${error.message}`;
        progressBar.style.width = '0%';
        
        setTimeout(() => {
            displayStockPricesError(error.message);
            resultsSection.classList.remove('hidden');
        }, 1000);
    } finally {
        setTimeout(() => {
            button.disabled = false;
            icon.className = 'fas fa-sync-alt mr-3';
            text.textContent = 'Update Stock Prices';
        }, 2000);
    }
}

// Company Finance Update functionality
async function updateCompanyFinance() {
    const button = document.getElementById('updateCompanyFinanceBtn');
    const icon = document.getElementById('updateFinanceIcon');
    const text = document.getElementById('updateFinanceText');
    const progressSection = document.getElementById('financeProgressSection');
    const resultsSection = document.getElementById('financeResultsSection');
    const progressBar = document.getElementById('financeProgressBar');
    const progressText = document.getElementById('financeProgressText');
    const progressDetails = document.getElementById('financeProgressDetails');
    const debugCheckbox = document.getElementById('debugCompanyFinance');

    try {
        button.disabled = true;
        icon.className = 'fas fa-spinner fa-spin mr-3';
        text.textContent = 'Updating Company Finance...';
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        
        progressBar.style.width = '0%';
        progressDetails.textContent = '';

        const isDebug = debugCheckbox.checked;
        const debugText = isDebug ? ' (Debug mode: VIC only)' : '';
        progressText.textContent = `Fetching financial data for mentioned stocks...${debugText}`;
        progressBar.style.width = '20%';

        const response = await fetch('/company-finance/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                debug: isDebug
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Update failed');
        }

        progressText.textContent = 'Processing financial data...';
        progressBar.style.width = '90%';

        const result = await response.json();

        progressText.textContent = 'Financial update completed!';
        progressBar.style.width = '100%';

        setTimeout(() => {
            displayCompanyFinanceResults(result);
            resultsSection.classList.remove('hidden');
            progressSection.classList.add('hidden');
        }, 1000);

    } catch (error) {
        console.error('Company finance update error:', error);
        progressText.textContent = 'Update failed';
        progressDetails.textContent = `Error: ${error.message}`;
        progressBar.style.width = '0%';
        
        setTimeout(() => {
            displayCompanyFinanceError(error.message);
            resultsSection.classList.remove('hidden');
        }, 1000);
    } finally {
        setTimeout(() => {
            button.disabled = false;
            icon.className = 'fas fa-sync-alt mr-3';
            text.textContent = 'Update Company Finance';
        }, 2000);
    }
}

// Display results functions
function displayCompanyEventsResults(data) {
    displayGenericResults(data, 'eventsStatsSection', 'eventsResultsGrid');
}

function displayCompanyDividendsResults(data) {
    displayGenericResults(data, 'dividendsStatsSection', 'dividendsResultsGrid');
}

function displayStockPricesResults(data) {
    const statsSection = document.getElementById('pricesStatsSection');
    const resultsGrid = document.getElementById('pricesResultsGrid');
    
    // Display stats
    const details = data.details || {};
    statsSection.innerHTML = `
        <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-purple-600">${data.total_stocks || 0}</div>
                <div class="text-sm text-gray-600">Total Stocks</div>
            </div>
        </div>
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-green-600">${data.stocks_updated || 0}</div>
                <div class="text-sm text-gray-600">Updated</div>
            </div>
        </div>
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-blue-600">${data.stocks_skipped || 0}</div>
                <div class="text-sm text-gray-600">Skipped</div>
            </div>
        </div>
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-red-600">${data.stocks_failed || 0}</div>
                <div class="text-sm text-gray-600">Failed</div>
            </div>
        </div>
    `;

    // Display individual stock results
    resultsGrid.innerHTML = '';
    if (details && Object.keys(details).length > 0) {
        Object.entries(details).forEach(([symbol, status]) => {
            const statusString = typeof status === 'string' ? status : JSON.stringify(status);
            const statusColor = statusString.includes('Updated successfully') ? 'green' : 
                              statusString.includes('skipped') ? 'blue' : 'red';
            const statusIcon = statusString.includes('Updated successfully') ? 'check-circle' : 
                             statusString.includes('skipped') ? 'info-circle' : 'exclamation-triangle';
            
            resultsGrid.innerHTML += `
                <div class="bg-white border border-gray-200 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-semibold text-lg">${symbol}</span>
                        <i class="fas fa-${statusIcon} text-${statusColor}-500"></i>
                    </div>
                    <p class="text-sm text-gray-600">${statusString}</p>
                </div>
            `;
        });
    }

    // Show message
    if (data.message) {
        resultsGrid.innerHTML += `
            <div class="col-span-full bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p class="text-gray-700 text-center">${data.message}</p>
            </div>
        `;
    }
}

function displayCompanyFinanceResults(data) {
    displayGenericResults(data, 'financeStatsSection', 'financeResultsGrid');
}

function displayGenericResults(data, statsId, resultsId) {
    const statsSection = document.getElementById(statsId);
    const resultsGrid = document.getElementById(resultsId);
    
    // Generic stats display
    statsSection.innerHTML = `
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-blue-600">${data.total_processed || 0}</div>
                <div class="text-sm text-gray-600">Total Processed</div>
            </div>
        </div>
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-green-600">${data.successful || 0}</div>
                <div class="text-sm text-gray-600">Successful</div>
            </div>
        </div>
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-yellow-600">${data.skipped || 0}</div>
                <div class="text-sm text-gray-600">Skipped</div>
            </div>
        </div>
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-red-600">${data.failed || 0}</div>
                <div class="text-sm text-gray-600">Failed</div>
            </div>
        </div>
    `;
    
    // Generic results display
    resultsGrid.innerHTML = `
        <div class="col-span-full bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p class="text-gray-700 text-center">${data.message || 'Update completed successfully'}</p>
        </div>
    `;
}

// Error display functions
function displayCompanyUpdateError(errorMessage) {
    const statsSection = document.getElementById('eventsStatsSection');
    const resultsGrid = document.getElementById('eventsResultsGrid');
    
    displayGenericError(errorMessage, statsSection, resultsGrid);
}

function displayCompanyDividendsError(errorMessage) {
    const statsSection = document.getElementById('dividendsStatsSection');
    const resultsGrid = document.getElementById('dividendsResultsGrid');
    
    displayGenericError(errorMessage, statsSection, resultsGrid);
}

function displayStockPricesError(errorMessage) {
    const statsSection = document.getElementById('pricesStatsSection');
    const resultsGrid = document.getElementById('pricesResultsGrid');
    
    displayGenericError(errorMessage, statsSection, resultsGrid);
}

function displayCompanyFinanceError(errorMessage) {
    const statsSection = document.getElementById('financeStatsSection');
    const resultsGrid = document.getElementById('financeResultsGrid');
    
    displayGenericError(errorMessage, statsSection, resultsGrid);
}

function displayGenericError(errorMessage, statsSection, resultsGrid) {
    statsSection.innerHTML = `
        <div class="col-span-full bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="text-center">
                <i class="fas fa-exclamation-triangle text-red-500 text-2xl mb-2"></i>
                <div class="text-lg font-bold text-red-600">Update Failed</div>
                <div class="text-sm text-red-500">${errorMessage}</div>
            </div>
        </div>
    `;
    
    resultsGrid.innerHTML = '';
}

// Industries Update functionality
async function updateIndustries() {
    const btn = document.getElementById('updateIndustriesBtn');
    const icon = document.getElementById('updateIndustriesIcon');
    const text = document.getElementById('updateIndustriesText');
    const progressSection = document.getElementById('industriesProgressSection');
    const resultsSection = document.getElementById('industriesResultsSection');
    const debug = document.getElementById('debugIndustries').checked;
    
    // Reset UI
    btn.disabled = true;
    icon.className = 'fas fa-spinner fa-spin mr-3';
    text.textContent = 'Updating Industries...';
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    
    try {
        const response = await fetch('/industries/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ debug })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayIndustriesResults(result.updated_count || 0, result.failed_count || 0, result.message);
        } else {
            displayIndustriesError(result.message || 'Industries update failed');
        }
    } catch (error) {
        console.error('Industries update error:', error);
        displayIndustriesError(error.message);
    } finally {
        // Reset button
        btn.disabled = false;
        icon.className = 'fas fa-sync-alt mr-3';
        text.textContent = 'Update Industries';
        progressSection.classList.add('hidden');
    }
}

function displayIndustriesResults(updatedCount, failedCount, message) {
    const statsSection = document.getElementById('industriesStatsSection');
    const resultsSection = document.getElementById('industriesResultsSection');
    
    statsSection.innerHTML = `
        <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-indigo-600">${updatedCount}</div>
            <div class="text-sm text-gray-600">Industries Updated</div>
        </div>
        <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold text-red-600">${failedCount}</div>
            <div class="text-sm text-gray-600">Failed Updates</div>
        </div>
        <div class="col-span-2 bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <div class="text-lg font-bold text-green-600">Success</div>
            <div class="text-sm text-gray-600">${message}</div>
        </div>
    `;
    
    resultsSection.classList.remove('hidden');
}

function displayIndustriesError(errorMessage) {
    const statsSection = document.getElementById('industriesStatsSection');
    const resultsGrid = document.getElementById('industriesResultsGrid');
    
    displayGenericError(errorMessage, statsSection, resultsGrid);
    document.getElementById('industriesResultsSection').classList.remove('hidden');
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Add Industries Update event listener
    const updateIndustriesBtn = document.getElementById('updateIndustriesBtn');
    if (updateIndustriesBtn) {
        updateIndustriesBtn.addEventListener('click', updateIndustries);
    }
});