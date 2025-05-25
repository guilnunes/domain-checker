document.addEventListener('DOMContentLoaded', function() {
    const domainForm = document.getElementById('domainForm');
    const checkButton = document.getElementById('checkButton');
    const progressSection = document.getElementById('progressSection');
    const progressBar = document.getElementById('progressBar');
    const progressStatus = document.getElementById('progressStatus');
    const consoleLog = document.getElementById('consoleLog');
    const clearConsole = document.getElementById('clearConsole');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContainer = document.getElementById('resultsContainer');
    const downloadPdfButton = document.getElementById('downloadPdfButton');
    const errorSection = document.getElementById('errorSection');
    const errorList = document.getElementById('errorList');
    const dismissErrors = document.getElementById('dismissErrors');
    
    let results = [];
    let errors = [];
    
    // Form submission handler
    domainForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        const brandNames = document.getElementById('brandNames').value.trim();
        const selectedTlds = Array.from(document.querySelectorAll('input[name="tlds"]:checked')).map(el => el.value);
        
        if (!brandNames) {
            showError('Please enter at least one brand name.');
            return;
        }
        
        if (selectedTlds.length === 0) {
            showError('Please select at least one TLD.');
            return;
        }
        
        // Reset UI
        resetUI();
        
        // Show progress section
        progressSection.classList.remove('hidden');
        
        // Disable form
        checkButton.disabled = true;
        checkButton.textContent = 'Checking...';
        
        // Start domain checking
        checkDomainsWithFetchStream(new FormData(domainForm));
    });
    
    // Clear console button
    clearConsole.addEventListener('click', function() {
        consoleLog.innerHTML = '';
    });
    
    // Dismiss errors button
    dismissErrors.addEventListener('click', function() {
        errorSection.classList.add('hidden');
        errorList.innerHTML = '';
        errors = [];
    });
    
    // Download PDF button
    downloadPdfButton.addEventListener('click', function() {
        generatePdf(results);
    });

    // Function to check domains using fetch and ReadableStream
    async function checkDomainsWithFetchStream(formData) {
        try {
            const response = await fetch('/stream-check', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    logToConsole('info', 'Stream finished.');
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Keep the last partial message in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonData = line.substring(6); // Remove 'data: '
                            const data = JSON.parse(jsonData);
                            processStreamData(data);
                        } catch (e) {
                            logToConsole('error', `Failed to parse JSON: ${line}`);
                            console.error('JSON Parse Error:', e, 'Data:', line);
                        }
                    }
                }
            }

        } catch (error) {
            showError(`Error: ${error.message}`);
            logToConsole('error', `Error: ${error.message}`);
            // Re-enable form
            checkButton.disabled = false;
            checkButton.textContent = 'Check Availability';
        }
    }

    // Function to process data received from the stream
    function processStreamData(data) {
        // Handle progress updates
        if (data.progress !== undefined) {
            updateProgress(data.progress);
        }
        
        // Handle status updates
        if (data.status) {
            updateStatus(data.status);
            logToConsole('info', data.status);
        }
        
        // Handle errors
        if (data.error) {
            errors.push(data.error);
            updateErrorSection();
            logToConsole('error', data.error);
        }
        
        // Handle final results
        if (data.results) {
            results = data.results;
            displayResults(results);
            
            // Re-enable form
            checkButton.disabled = false;
            checkButton.textContent = 'Check Availability';
            
            // Log completion
            logToConsole('success', 'Domain checking completed.');
        }
    }
    
    // Function to update progress bar
    function updateProgress(progress) {
        progressBar.style.width = progress + '%';
    }
    
    // Function to update status text
    function updateStatus(status) {
        progressStatus.textContent = status;
    }
    
    // Function to log to console
    function logToConsole(type, message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-message">${message}</span>`;
        consoleLog.appendChild(logEntry);
        consoleLog.scrollTop = consoleLog.scrollHeight;
    }
    
    // Function to show error
    function showError(message) {
        errors.push(message);
        updateErrorSection();
        errorSection.classList.remove('hidden');
    }
    
    // Function to update error section
    function updateErrorSection() {
        if (errors.length > 0) {
            errorSection.classList.remove('hidden');
            errorList.innerHTML = '';
            errors.forEach(error => {
                const li = document.createElement('li');
                li.textContent = error;
                errorList.appendChild(li);
            });
        } else {
            errorSection.classList.add('hidden');
        }
    }
    
    // Function to reset UI
    function resetUI() {
        // Reset progress
        progressBar.style.width = '0%';
        progressStatus.textContent = 'Initializing...';
        consoleLog.innerHTML = '';
        
        // Hide results
        resultsSection.classList.add('hidden');
        resultsContainer.innerHTML = '';
        
        // Clear errors
        errors = [];
        errorList.innerHTML = '';
        errorSection.classList.add('hidden');
        
        // Clear results
        results = [];
    }
    
    // Function to display results
    function displayResults(results) {
        resultsSection.classList.remove('hidden');
        resultsContainer.innerHTML = '';
        
        results.forEach(brandResult => {
            const brandSection = document.createElement('div');
            brandSection.className = 'brand-section';
            
            // Brand header
            const brandHeader = document.createElement('h3');
            brandHeader.className = 'brand-header';
            brandHeader.textContent = brandResult.brand;
            brandSection.appendChild(brandHeader);
            
            // Domains table
            const domainsTable = document.createElement('table');
            domainsTable.className = 'domains-table';
            
            // Table header
            const tableHeader = document.createElement('thead');
            tableHeader.innerHTML = `
                <tr>
                    <th>Domain</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Sources</th>
                </tr>
            `;
            domainsTable.appendChild(tableHeader);
            
            // Table body
            const tableBody = document.createElement('tbody');
            
            brandResult.domains.forEach(domain => {
                const row = document.createElement('tr');
                
                // Domain name
                const domainCell = document.createElement('td');
                domainCell.textContent = domain.domain;
                row.appendChild(domainCell);
                
                // Status
                const statusCell = document.createElement('td');
                let statusClass = 'status-unavailable';
                let statusText = 'Unavailable';
                
                if (domain.status === 'error') {
                    statusClass = 'status-error';
                    statusText = 'Error';
                } else if (domain.available) {
                    statusClass = 'status-available';
                    statusText = 'Available';
                } else if (domain.status && domain.status.includes('uncertain')) {
                    statusClass = 'status-uncertain';
                    statusText = 'Uncertain';
                } else if (domain.status && domain.status.includes('conflicted')) {
                    statusClass = 'status-conflicted';
                    statusText = 'Conflicted';
                }
                
                statusCell.className = statusClass;
                statusCell.textContent = statusText;
                row.appendChild(statusCell);
                
                // Confidence
                const confidenceCell = document.createElement('td');
                const confidence = domain.confidence || 0;
                let confidenceClass = 'confidence-low';
                
                if (confidence >= 0.8) {
                    confidenceClass = 'confidence-high';
                } else if (confidence >= 0.5) {
                    confidenceClass = 'confidence-medium';
                }
                
                confidenceCell.className = confidenceClass;
                confidenceCell.textContent = Math.round(confidence * 100) + '%';
                row.appendChild(confidenceCell);
                
                // Sources
                const sourcesCell = document.createElement('td');
                sourcesCell.className = 'sources-cell';
                
                if (domain.sources && domain.sources.length > 0) {
                    const sourcesList = document.createElement('ul');
                    sourcesList.className = 'sources-list';
                    
                    domain.sources.forEach(source => {
                        const sourceItem = document.createElement('li');
                        sourceItem.className = 'source-item';
                        
                        if (source.error) {
                            sourceItem.className += ' source-error';
                            sourceItem.innerHTML = `<span class="source-name">${source.source}</span>: <span class="source-error-message">${source.error}</span>`;
                        } else {
                            sourceItem.className += source.available ? ' source-available' : ' source-unavailable';
                            sourceItem.innerHTML = `<span class="source-name">${source.source}</span>: <span class="source-status">${source.available ? 'Available' : 'Unavailable'}</span>`;
                        }
                        
                        sourcesList.appendChild(sourceItem);
                    });
                    
                    sourcesCell.appendChild(sourcesList);
                } else {
                    sourcesCell.textContent = 'No sources';
                }
                
                row.appendChild(sourcesCell);
                
                tableBody.appendChild(row);
                
                // Add error row if there's an error
                if (domain.error) {
                    const errorRow = document.createElement('tr');
                    errorRow.className = 'error-row';
                    
                    const errorCell = document.createElement('td');
                    errorCell.colSpan = 4;
                    errorCell.className = 'error-cell';
                    errorCell.textContent = domain.error;
                    
                    errorRow.appendChild(errorCell);
                    tableBody.appendChild(errorRow);
                }
            });
            
            domainsTable.appendChild(tableBody);
            brandSection.appendChild(domainsTable);
            
            // Suggestions
            if (brandResult.suggestions && brandResult.suggestions.length > 0) {
                const suggestionsSection = document.createElement('div');
                suggestionsSection.className = 'suggestions-section';
                
                const suggestionsTitle = document.createElement('h4');
                suggestionsTitle.textContent = 'Alternative Suggestions:';
                suggestionsSection.appendChild(suggestionsTitle);
                
                const suggestionsList = document.createElement('div');
                suggestionsList.className = 'suggestions-list';
                
                brandResult.suggestions.forEach(suggestion => {
                    const suggestionItem = document.createElement('span');
                    suggestionItem.className = 'suggestion-item';
                    suggestionItem.textContent = suggestion;
                    suggestionsList.appendChild(suggestionItem);
                });
                
                suggestionsSection.appendChild(suggestionsList);
                brandSection.appendChild(suggestionsSection);
            }
            
            resultsContainer.appendChild(brandSection);
        });
    }
    
    // Function to generate PDF
    function generatePdf(results) {
        if (!results || results.length === 0) {
            showError('No results to generate PDF from.');
            return;
        }
        
        // Show generating message
        logToConsole('info', 'Generating PDF...');
        
        // Send results to server for PDF generation
        fetch('/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ results: results })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'domain_availability_report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            
            logToConsole('success', 'PDF generated successfully.');
        })
        .catch(error => {
            showError('Error generating PDF: ' + error.message);
            logToConsole('error', 'Error generating PDF: ' + error.message);
        });
    }
});

