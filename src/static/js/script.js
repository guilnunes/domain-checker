document.addEventListener('DOMContentLoaded', function() {
    const domainForm = document.getElementById('domainForm');
    const checkButton = document.getElementById('checkButton');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressStatus = document.getElementById('progressStatus');
    const errorConsole = document.getElementById('errorConsole');
    const errorList = document.getElementById('errorList');
    const clearErrorsBtn = document.getElementById('clearErrorsBtn');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsContent = document.getElementById('resultsContent');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    
    let results = []; // Store results for PDF generation
    
    domainForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Reset UI
        resetUI();
        
        // Show loading spinner and progress container
        loadingSpinner.classList.remove('d-none');
        checkButton.disabled = true;
        progressContainer.classList.remove('d-none');
        progressStatus.textContent = 'Starting...';
        progressBar.style.width = '0%';
        
        // Get form data
        const formData = new FormData(domainForm);
        
        // Send form data to server
        fetch('/stream-check', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            function processStream() {
                return reader.read().then(({ done, value }) => {
                    if (done) {
                        return;
                    }
                    
                    const text = decoder.decode(value, { stream: true });
                    const lines = text.split('\n\n');
                    
                    lines.forEach(line => {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6));
                                
                                // Update progress
                                if (data.progress !== undefined) {
                                    progressBar.style.width = data.progress + '%';
                                    progressBar.setAttribute('aria-valuenow', data.progress);
                                }
                                
                                // Update status message
                                if (data.status) {
                                    progressStatus.textContent = data.status;
                                }
                                
                                // Handle errors
                                if (data.error) {
                                    showError(data.error);
                                }
                                
                                // Handle completion
                                if (data.results) {
                                    results = data.results; // Store results for PDF generation
                                    displayResults(data.results);
                                    
                                    // Show results container
                                    resultsContainer.classList.remove('d-none');
                                    
                                    // Scroll to results
                                    resultsContainer.scrollIntoView({ behavior: 'smooth' });
                                    
                                    // Hide loading spinner and update progress
                                    loadingSpinner.classList.add('d-none');
                                    checkButton.disabled = false;
                                    progressStatus.textContent = 'Completed';
                                }
                            } catch (e) {
                                console.error('Error parsing SSE data:', e);
                            }
                        }
                    });
                    
                    return processStream();
                });
            }
            
            return processStream();
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Connection error. Please try again.');
            
            // Hide loading spinner
            loadingSpinner.classList.add('d-none');
            checkButton.disabled = false;
        });
    });
    
    // Clear errors button
    clearErrorsBtn.addEventListener('click', function() {
        errorList.innerHTML = '';
        errorConsole.classList.add('d-none');
    });
    
    // Download PDF button
    downloadPdfBtn.addEventListener('click', function() {
        if (results.length === 0) {
            showError('No results to download. Please check domains first.');
            return;
        }
        
        // Show loading state
        downloadPdfBtn.disabled = true;
        downloadPdfBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating PDF...';
        
        // Send results to server for PDF generation
        fetch('/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ results: results }),
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
            
            // Reset button state
            downloadPdfBtn.disabled = false;
            downloadPdfBtn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Download as PDF';
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Failed to generate PDF. Please try again.');
            
            // Reset button state
            downloadPdfBtn.disabled = false;
            downloadPdfBtn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Download as PDF';
        });
    });
    
    function resetUI() {
        // Clear previous results and errors
        resultsContent.innerHTML = '';
        resultsContainer.classList.add('d-none');
        errorList.innerHTML = '';
        errorConsole.classList.add('d-none');
        results = [];
    }
    
    function showError(errorMessage) {
        // Show error console if hidden
        errorConsole.classList.remove('d-none');
        
        // Add error message to list
        const errorItem = document.createElement('div');
        errorItem.className = 'error-item';
        errorItem.textContent = errorMessage;
        errorList.appendChild(errorItem);
        
        // Auto-scroll to bottom
        errorList.scrollTop = errorList.scrollHeight;
    }
    
    function getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'high-confidence';
        if (confidence >= 0.5) return 'medium-confidence';
        return 'low-confidence';
    }
    
    function getStatusClass(status, conflicting) {
        if (status === 'error') return 'domain-error';
        if (status === 'available') return 'domain-available';
        if (status === 'unavailable') return 'domain-unavailable';
        if (status && status.includes('uncertain')) return 'domain-uncertain';
        if (conflicting) return 'domain-conflict';
        return 'domain-unavailable';
    }
    
    function getStatusText(status, available) {
        if (status === 'error') return 'Error';
        if (status === 'available') return 'Available';
        if (status === 'unavailable') return 'Unavailable';
        if (status && status.includes('uncertain')) return 'Uncertain';
        if (status && status.includes('conflicted')) return available ? 'Available (Conflicted)' : 'Unavailable (Conflicted)';
        return available ? 'Available' : 'Unavailable';
    }
    
    function formatSourceBadges(sources) {
        if (!sources || sources.length === 0) return 'No sources';
        
        let html = '';
        sources.forEach(source => {
            if (source.error) return; // Skip sources with errors
            
            const sourceClass = `source-${source.source.toLowerCase()}`;
            const confidenceClass = getConfidenceClass(source.confidence);
            
            html += `<span class="badge source-badge ${sourceClass}" 
                      title="${source.source}: ${Math.round(source.confidence * 100)}% confidence">
                      ${source.source}
                    </span>`;
        });
        
        return html || 'No valid sources';
    }
    
    function displayResults(results) {
        let html = '';
        
        if (results.length === 0) {
            html = '<div class="alert alert-warning">No results found. Please try different brand names.</div>';
        } else {
            html = '<div class="accordion" id="resultsAccordion">';
            
            results.forEach((result, index) => {
                const brandId = `brand-${index}`;
                
                html += `
                    <div class="accordion-item mb-3 shadow-sm">
                        <h2 class="accordion-header">
                            <button class="accordion-button ${index !== 0 ? 'collapsed' : ''}" type="button" data-bs-toggle="collapse" data-bs-target="#${brandId}">
                                <strong>${result.brand}</strong>
                            </button>
                        </h2>
                        <div id="${brandId}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" data-bs-parent="#resultsAccordion">
                            <div class="accordion-body">
                                <div class="row">
                                    <div class="col-12">
                                        <h5>Domain Availability:</h5>
                                        <div class="domain-results">
                `;
                
                result.domains.forEach(domain => {
                    const statusClass = getStatusClass(domain.status, domain.conflicting_results);
                    const statusText = getStatusText(domain.status, domain.available);
                    const confidenceClass = getConfidenceClass(domain.confidence);
                    const confidencePercent = Math.round((domain.confidence || 0) * 100);
                    
                    html += `
                        <div class="card ${statusClass} domain-card mb-2">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center py-2">
                                    <span class="domain-name fw-bold">${domain.domain}</span>
                                    <span class="domain-status">${statusText}</span>
                                </div>
                                
                                <div class="mt-2">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <small class="text-muted">Confidence:</small>
                                        <small class="confidence-value ${confidenceClass}">${confidencePercent}%</small>
                                    </div>
                                    <div class="confidence-meter">
                                        <div class="confidence-level confidence-level-${confidenceClass}" style="width: ${confidencePercent}%"></div>
                                    </div>
                                </div>
                                
                                <div class="mt-2">
                                    <small class="text-muted">Sources:</small>
                                    <div class="mt-1">
                                        ${formatSourceBadges(domain.sources)}
                                        ${domain.conflicting_results ? '<span class="source-conflict-indicator"><i class="bi bi-exclamation-triangle-fill" title="Sources disagree on availability"></i></span>' : ''}
                                    </div>
                                </div>
                            </div>
                            ${domain.error ? `<div class="card-footer py-1 small text-muted">${domain.error}</div>` : ''}
                        </div>
                    `;
                });
                
                html += '</div>';
                
                // Add suggestions if there are any
                if (result.suggestions && result.suggestions.length > 0) {
                    html += `
                        <div class="mt-4">
                            <h5>Alternative Suggestions:</h5>
                            <div class="suggestions-container">
                    `;
                    
                    result.suggestions.forEach(suggestion => {
                        html += `<span class="suggestion-item">${suggestion}</span>`;
                    });
                    
                    html += `
                            </div>
                        </div>
                    `;
                }
                
                html += `
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        resultsContent.innerHTML = html;
    }
});
