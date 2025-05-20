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
        
        // Create EventSource for server-sent events
        const eventSource = new EventSource('/stream-check', {
            method: 'POST',
            body: formData
        });
        
        // Handle progress updates
        eventSource.addEventListener('message', function(event) {
            const data = JSON.parse(event.data);
            
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
                
                // Close the event source
                eventSource.close();
                
                // Hide loading spinner and update progress
                loadingSpinner.classList.add('d-none');
                checkButton.disabled = false;
                progressStatus.textContent = 'Completed';
            }
        });
        
        // Handle errors
        eventSource.addEventListener('error', function(event) {
            console.error('EventSource error:', event);
            showError('Connection error. Please try again.');
            
            // Close the event source
            eventSource.close();
            
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
                    let statusClass = 'domain-unavailable';
                    let statusText = 'Unavailable';
                    
                    if (domain.available) {
                        statusClass = 'domain-available';
                        statusText = 'Available';
                    } else if (domain.error) {
                        statusClass = 'domain-error';
                        statusText = 'Error';
                    }
                    
                    html += `
                        <div class="card ${statusClass} domain-card mb-2">
                            <div class="card-body d-flex justify-content-between align-items-center py-2">
                                <span class="domain-name fw-bold">${domain.domain}</span>
                                <span class="domain-status">${statusText}</span>
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
