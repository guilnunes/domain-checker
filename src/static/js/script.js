document.addEventListener('DOMContentLoaded', function() {
    const domainForm = document.getElementById('domainForm');
    const checkButton = document.getElementById('checkButton');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsContent = document.getElementById('resultsContent');

    domainForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading spinner
        loadingSpinner.classList.remove('d-none');
        checkButton.disabled = true;
        resultsContainer.classList.add('d-none');
        
        // Get form data
        const formData = new FormData(domainForm);
        
        // Send AJAX request
        fetch('/check', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading spinner
            loadingSpinner.classList.add('d-none');
            checkButton.disabled = false;
            
            // Display results
            displayResults(data.results);
            
            // Show results container
            resultsContainer.classList.remove('d-none');
            
            // Scroll to results
            resultsContainer.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(error => {
            console.error('Error:', error);
            loadingSpinner.classList.add('d-none');
            checkButton.disabled = false;
            
            // Show error message
            resultsContent.innerHTML = `
                <div class="alert alert-danger">
                    An error occurred while checking domains. Please try again.
                </div>
            `;
            resultsContainer.classList.remove('d-none');
        });
    });

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
                    const statusClass = domain.available ? 'domain-available' : 'domain-unavailable';
                    const statusText = domain.available ? 'Available' : 'Unavailable';
                    const statusIcon = domain.available ? 
                        '<i class="bi bi-check-circle-fill"></i>' : 
                        '<i class="bi bi-x-circle-fill"></i>';
                    
                    html += `
                        <div class="card ${statusClass} domain-card mb-2">
                            <div class="card-body d-flex justify-content-between align-items-center py-2">
                                <span class="domain-name fw-bold">${domain.domain}</span>
                                <span class="domain-status">${statusText}</span>
                            </div>
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
