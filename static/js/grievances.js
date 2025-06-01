document.addEventListener('DOMContentLoaded', function() {
    const grievanceForm = document.getElementById('grievanceForm');
    if (grievanceForm) {
        grievanceForm.addEventListener('submit', handleGrievanceSubmission);
    }
});

async function handleGrievanceSubmission(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const grievanceData = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/student/grievances', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(grievanceData)
        });

        if (!response.ok) throw new Error('Failed to submit grievance');
        
        const result = await response.json();
        showToast('Grievance submitted successfully', 'success');
        
        // Close modal and refresh grievance list
        const modal = bootstrap.Modal.getInstance(document.getElementById('grievanceModal'));
        modal.hide();
        event.target.reset();
        loadGrievances();
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to submit grievance', 'error');
    }
}

async function loadGrievances() {
    try {
        const response = await fetch('/student/grievances');
        if (!response.ok) throw new Error('Failed to load grievances');
        
        const data = await response.json();
        updateGrievanceList(data.grievances);
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to load grievances', 'error');
    }
}

function updateGrievanceList(grievances) {
    const grievanceList = document.querySelector('.grievance-list');
    if (!grievanceList) return;

    if (grievances.length === 0) {
        grievanceList.innerHTML = '<p class="text-muted">No recent grievances</p>';
        return;
    }

    grievanceList.innerHTML = grievances.map(grievance => `
        <div class="grievance-item">
            <div class="grievance-header">
                <h6>${grievance.subject}</h6>
                <span class="badge bg-${getStatusColor(grievance.status)}">${grievance.status}</span>
            </div>
            <small class="text-muted">${new Date(grievance.created_at).toLocaleDateString()}</small>
            ${grievance.response ? `
                <div class="grievance-response mt-2">
                    <small class="text-muted">Response:</small>
                    <p class="mb-0">${grievance.response}</p>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function getStatusColor(status) {
    const colors = {
        'Pending': 'warning',
        'In Progress': 'info',
        'Resolved': 'success'
    };
    return colors[status] || 'secondary';
} 