// Milestone Management Functions
async function updateMilestoneStatus(milestoneId, status) {
    try {
        const response = await fetch(`/milestones/${milestoneId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: status })
        });
        
        if (!response.ok) throw new Error('Failed to update milestone');
        const data = await response.json();
        
        // Update UI
        const milestoneElement = document.querySelector(`[data-milestone-id="${milestoneId}"]`);
        if (milestoneElement) {
            const statusBadge = milestoneElement.querySelector('.milestone-status');
            statusBadge.className = `milestone-status status-${status}`;
            statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }

        showToast('Milestone updated successfully', 'success');
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to update milestone', 'error');
    }
}

async function deleteMilestone(milestoneId) {
    if (!confirm('Are you sure you want to delete this milestone?')) return;
    
    try {
        const response = await fetch(`/milestones/${milestoneId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete milestone');
        
        // Remove the milestone element from DOM
        const milestoneElement = document.querySelector(`[data-milestone-id="${milestoneId}"]`);
        if (milestoneElement) {
            milestoneElement.remove();
        }
        showToast('Milestone deleted successfully', 'success');
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to delete milestone', 'error');
    }
}

async function addMilestone(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const goalId = form.getAttribute('data-goal-id');

    try {
        const response = await fetch(`/goals/${goalId}/milestones`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Failed to add milestone');
        
        // Refresh the page to show new milestone
        window.location.reload();
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to add milestone', 'error');
    }
}

// Toast notification function
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast show bg-${type === 'error' ? 'danger' : type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body text-white">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toast);

    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();

    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    const milestoneForm = document.getElementById('milestoneForm');
    if (milestoneForm) {
        milestoneForm.addEventListener('submit', addMilestone);
    }
}); 