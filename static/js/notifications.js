document.addEventListener('DOMContentLoaded', function() {
    // Initialize notifications
    loadNotifications();
    initializeNotificationPolling();
    initializeMarkAllRead();
});

function loadNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(notifications => {
            displayNotifications(notifications);
            updateNotificationBadge(notifications.filter(n => !n.read).length);
        })
        .catch(error => console.error('Error loading notifications:', error));
}

function displayNotifications(notifications) {
    const notificationList = document.getElementById('notificationList');
    notificationList.innerHTML = notifications.length ? '' : '<div class="p-3 text-center text-muted">No notifications</div>';

    notifications.forEach(notification => {
        const notificationElement = createNotificationElement(notification);
        notificationList.appendChild(notificationElement);
    });
}

function createNotificationElement(notification) {
    const div = document.createElement('div');
    div.className = `notification-item ${notification.read ? '' : 'unread'}`;
    div.setAttribute('data-id', notification.id);
    div.innerHTML = `
        <div class="notification-content">${notification.message}</div>
        <div class="notification-meta">${formatNotificationDate(notification.created_at)}</div>
    `;
    
    div.addEventListener('click', () => markNotificationAsRead(notification.id));
    return div;
}

function markNotificationAsRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'PUT'
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            loadNotifications();
        }
    })
    .catch(error => console.error('Error marking notification as read:', error));
}

function markAllNotificationsAsRead() {
    fetch('/api/notifications/mark-all-read', {
        method: 'PUT'
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            loadNotifications();
        }
    })
    .catch(error => console.error('Error marking all notifications as read:', error));
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

function initializeNotificationPolling() {
    // Poll for new notifications every minute
    setInterval(loadNotifications, 60000);
}

function initializeMarkAllRead() {
    document.getElementById('markAllReadBtn').addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        markAllNotificationsAsRead();
    });
}

function formatNotificationDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        const hours = Math.floor(diffTime / (1000 * 60 * 60));
        if (hours === 0) {
            const minutes = Math.floor(diffTime / (1000 * 60));
            return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
        }
        return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString();
    }
} 