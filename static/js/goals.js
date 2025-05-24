// Goal Management Functions
function updateGoalStatus(goalId, newStatus) {
    fetch(`/goals/${goalId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        // Update UI elements
        const goalItem = document.querySelector(`.goal-item[data-goal-id="${goalId}"]`);
        const statusBadge = goalItem.querySelector('.goal-status');
        
        // Update status badge
        statusBadge.className = `goal-status status-${newStatus}`;
        statusBadge.textContent = newStatus.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Show success message
        showToast('Goal status updated successfully', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Failed to update goal status', 'error');
    });
}

function editGoal(goalId) {
    const goalItem = document.querySelector(`.goal-item[data-goal-id="${goalId}"]`);
    const title = goalItem.querySelector('.goal-title').textContent;
    const description = goalItem.querySelector('.goal-description')?.textContent || '';
    const startDate = goalItem.querySelector('.goal-dates')?.dataset.startDate;
    const targetDate = goalItem.querySelector('.goal-dates')?.dataset.targetDate;
    
    // Populate edit modal
    document.getElementById('editGoalId').value = goalId;
    document.getElementById('editGoalTitle').value = title;
    document.getElementById('editGoalDescription').value = description;
    document.getElementById('editStartDate').value = startDate || '';
    document.getElementById('editTargetDate').value = targetDate || '';
    
    // Show edit modal
    const editModal = new bootstrap.Modal(document.getElementById('editGoalModal'));
    editModal.show();
}

function saveGoalEdit(event) {
    event.preventDefault();
    const form = event.target;
    const goalId = form.querySelector('#editGoalId').value;
    
    const formData = {
        title: form.querySelector('#editGoalTitle').value,
        description: form.querySelector('#editGoalDescription').value,
        start_date: form.querySelector('#editStartDate').value,
        target_date: form.querySelector('#editTargetDate').value
    };
    
    fetch(`/goals/${goalId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        // Update UI
        const goalItem = document.querySelector(`.goal-item[data-goal-id="${goalId}"]`);
        goalItem.querySelector('.goal-title').textContent = data.title;
        if (data.description) {
            goalItem.querySelector('.goal-description').textContent = data.description;
        }
        
        // Update dates
        const datesContainer = goalItem.querySelector('.goal-dates');
        let datesHtml = '';
        if (data.start_date) {
            datesHtml += `<span class="date-label">Start:</span> ${formatDate(data.start_date)}`;
        }
        if (data.target_date) {
            datesHtml += `<span class="date-label">Target:</span> ${formatDate(data.target_date)}`;
        }
        datesContainer.innerHTML = datesHtml;
        
        // Close modal and show success message
        bootstrap.Modal.getInstance(document.getElementById('editGoalModal')).hide();
        showToast('Goal updated successfully', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Failed to update goal', 'error');
    });
}

function deleteGoal(goalId) {
    if (confirm('Are you sure you want to delete this goal? This action cannot be undone.')) {
        fetch(`/goals/${goalId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                // Show success message
                showToast('Goal deleted successfully', 'success');
                
                // Refresh the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error('Failed to delete goal');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Failed to delete goal', 'error');
        });
    }
}

function addGoal(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    // Add loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
    submitButton.disabled = true;

    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to add goal');
        }
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addGoalModal'));
        modal.hide();
        
        // Reset form
        form.reset();
        
        // Refresh the page to show new goal
        window.location.reload();
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Failed to add goal. Please try again.', 'error');
    })
    .finally(() => {
        // Reset button state
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
}

// Helper Functions
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    const toastContainer = document.getElementById('toastContainer') || document.body;
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    const goalForm = document.getElementById('goalForm');
    if (goalForm) {
        goalForm.addEventListener('submit', addGoal);
    }
}); 