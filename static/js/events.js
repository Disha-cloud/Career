document.addEventListener('DOMContentLoaded', function() {
    loadEvents();
});

async function loadEvents() {
    try {
        const response = await fetch('/student/events');
        if (!response.ok) throw new Error('Failed to load events');
        
        const data = await response.json();
        updateEventList(data.events);
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to load events', 'error');
    }
}

async function registerForEvent(eventId) {
    try {
        const response = await fetch(`/student/events/${eventId}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) throw new Error('Failed to register for event');
        
        const result = await response.json();
        showToast('Successfully registered for event', 'success');
        loadEvents(); // Refresh the events list
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to register for event', 'error');
    }
}

function updateEventList(events) {
    const eventList = document.querySelector('.event-list');
    if (!eventList) return;

    if (events.length === 0) {
        eventList.innerHTML = '<p class="text-muted">No upcoming events</p>';
        return;
    }

    eventList.innerHTML = events.map(event => `
        <div class="event-item">
            <div class="event-header">
                <h6>${event.title}</h6>
                <span class="badge bg-${event.is_online ? 'info' : 'success'}">
                    ${event.is_online ? 'Online' : 'In-Person'}
                </span>
            </div>
            <div class="event-details">
                <p><i class="fas fa-calendar"></i> ${new Date(event.event_date).toLocaleDateString()}</p>
                <p><i class="fas fa-clock"></i> ${formatTime(event.start_time)} - ${formatTime(event.end_time)}</p>
                ${event.is_online ? 
                    `<p><i class="fas fa-video"></i> Meeting link will be provided</p>` :
                    `<p><i class="fas fa-location-dot"></i> ${event.location}</p>`
                }
                <p><i class="fas fa-users"></i> Capacity: ${event.capacity}</p>
            </div>
            <div class="event-actions">
                ${event.registration ? 
                    `<span class="badge bg-success">Registered</span>` :
                    `<button onclick="registerForEvent(${event.event_id})" class="btn btn-primary btn-sm">
                        Register
                    </button>`
                }
            </div>
        </div>
    `).join('');
}

function formatTime(timeString) {
    if (!timeString) return '';
    const [hours, minutes] = timeString.split(':');
    const date = new Date();
    date.setHours(parseInt(hours), parseInt(minutes));
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
} 