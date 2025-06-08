// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing event listeners');
    
    // Initialize date inputs with today's date as min
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        input.min = today;
    });

    // Initialize statistics
    updateGoalStatistics();
});

// Goal Management Functions
function updateGoalStatus(goalId, newStatus) {
    console.log(`Updating goal ${goalId} status to ${newStatus}`);
    fetch(`/goals/${goalId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            status: newStatus
        })
    })
    .then(response => {
        console.log('Status update response:', response);
        return response.json();
    })
    .then(data => {
        console.log('Status update data:', data);
        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast('Goal status updated successfully', 'success');
            updateGoalStatistics();
        }
    })
    .catch(error => {
        console.error('Status update error:', error);
        showToast('Error updating goal status', 'danger');
    });
}

function editGoal(goalId) {
    console.log(`Editing goal ${goalId}`);
    fetch(`/goals/${goalId}`)
        .then(response => response.json())
        .then(goal => {
            console.log('Goal data:', goal);
            // Populate the edit modal
            document.getElementById('editGoalId').value = goal.goal_id;
            document.getElementById('editGoalTitle').value = goal.title;
            document.getElementById('editGoalDescription').value = goal.description || '';
            document.getElementById('editStartDate').value = goal.start_date || '';
            document.getElementById('editTargetDate').value = goal.target_date || '';
            
            // Show the modal
            const editModal = new bootstrap.Modal(document.getElementById('editGoalModal'));
            editModal.show();
        })
        .catch(error => {
            console.error('Error loading goal:', error);
            showToast('Error loading goal details', 'danger');
        });
}

function saveGoalEdit(event) {
    event.preventDefault();
    console.log('Saving goal edit');
    
    const goalId = document.getElementById('editGoalId').value;
    const formData = {
        title: document.getElementById('editGoalTitle').value,
        description: document.getElementById('editGoalDescription').value,
        start_date: document.getElementById('editStartDate').value,
        target_date: document.getElementById('editTargetDate').value
    };

    console.log('Form data:', formData);

    fetch(`/goals/${goalId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Save response:', data);
        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast('Goal updated successfully', 'success');
            location.reload();
        }
    })
    .catch(error => {
        console.error('Error saving goal:', error);
        showToast('Error updating goal', 'danger');
    });
}

function deleteGoal(goalId) {
    if (confirm('Are you sure you want to delete this goal?')) {
        console.log(`Deleting goal ${goalId}`);
        fetch(`/goals/${goalId}`, {
            method: 'DELETE'
        })
        .then(response => {
            console.log('Delete response:', response);
            if (response.ok) {
                showToast('Goal deleted successfully', 'success');
                location.reload();
            } else {
                throw new Error('Failed to delete goal');
            }
        })
        .catch(error => {
            console.error('Error deleting goal:', error);
            showToast('Error deleting goal', 'danger');
        });
    }
}

function addGoal(event) {
    console.log('Add goal function called');
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    // Log form data
    console.log('Form data:');
    for (let pair of formData.entries()) {
        console.log(pair[0] + ': ' + pair[1]);
    }

    // Add loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
    submitButton.disabled = true;

    console.log('Submitting form to:', form.action);
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Server response:', response);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addGoalModal'));
        if (modal) {
            console.log('Closing modal');
            modal.hide();
        } else {
            console.log('Modal instance not found');
        }
        
        // Reset form
        console.log('Resetting form');
        form.reset();
        
        // Refresh the page to show new goal
        console.log('Reloading page');
        window.location.reload();
    })
    .catch(error => {
        console.error('Form submission error:', error);
        showToast('Failed to add goal. Please try again.', 'error');
    })
    .finally(() => {
        // Reset button state
        console.log('Resetting button state');
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
    console.log(`Showing toast: ${message} (${type})`);
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
        console.log('Toast hidden, removing from DOM');
        toast.remove();
    });
}

// Function to update goal statistics
function updateGoalStatistics() {
    console.log('Updating goal statistics');
    const goals = document.querySelectorAll('.goal-item');
    let total = goals.length;
    let inProgress = 0;
    let completed = 0;

    goals.forEach(goal => {
        const status = goal.querySelector('select').value;
        if (status === 'in_progress') inProgress++;
        if (status === 'completed') completed++;
    });

    console.log(`Statistics - Total: ${total}, In Progress: ${inProgress}, Completed: ${completed}`);
    
    const totalElement = document.getElementById('totalGoals');
    const inProgressElement = document.getElementById('inProgressGoals');
    const completedElement = document.getElementById('completedGoals');
    
    if (totalElement) totalElement.textContent = total;
    if (inProgressElement) inProgressElement.textContent = inProgress;
    if (completedElement) completedElement.textContent = completed;
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing event listeners');
    
    const goalForm = document.getElementById('goalForm');
    if (goalForm) {
        console.log('Found goal form, attaching submit listener');
        goalForm.addEventListener('submit', addGoal);
    } else {
        console.log('Goal form not found in DOM');
    }

    const addGoalForm = document.getElementById('addGoalForm');
    if (addGoalForm) {
        console.log('Found add goal form, attaching submit listener');
        addGoalForm.addEventListener('submit', function(e) {
            console.log('Add goal form submitted');
            // Form will submit normally as it's configured for regular form submission
            // We just need to validate the required fields
            const title = document.getElementById('goalTitle').value.trim();
            console.log('Goal title:', title);
            if (!title) {
                console.log('Title validation failed');
                e.preventDefault();
                showToast('Goal title is required', 'warning');
            } else {
                console.log('Form validation passed');
            }
        });
    } else {
        console.log('Add goal form not found in DOM');
    }
    
    // Log initial statistics
    console.log('Initializing goal statistics');
    updateGoalStatistics();
}); 