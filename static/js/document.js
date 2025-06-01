document.addEventListener('DOMContentLoaded', function() {
    const documentForm = document.getElementById('documentForm');
    if (documentForm) {
        documentForm.addEventListener('submit', handleDocumentUpload);
    }
});

async function handleDocumentUpload(event) {
    event.preventDefault();
    const formData = new FormData(event.target);

    try {
        const response = await fetch('/student/documents', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Failed to upload document');
        
        const result = await response.json();
        showToast('Document uploaded successfully', 'success');
        
        // Close modal and refresh document list
        const modal = bootstrap.Modal.getInstance(document.getElementById('documentModal'));
        modal.hide();
        event.target.reset();
        loadDocuments();
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to upload document', 'error');
    }
}

async function loadDocuments() {
    try {
        const response = await fetch('/student/documents');
        if (!response.ok) throw new Error('Failed to load documents');
        
        const data = await response.json();
        updateDocumentList(data.documents);
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to load documents', 'error');
    }
}

function updateDocumentList(documents) {
    const documentList = document.querySelector('.document-list');
    if (!documentList) return;

    if (documents.length === 0) {
        documentList.innerHTML = '<p class="text-muted">No documents uploaded</p>';
        return;
    }

    documentList.innerHTML = documents.map(doc => `
        <div class="document-item">
            <div class="document-info">
                <i class="fas fa-file"></i>
                <span>${doc.title}</span>
            </div>
            <div class="document-meta">
                <span class="badge bg-secondary">${doc.document_type}</span>
                <small class="text-muted">${new Date(doc.upload_date).toLocaleDateString()}</small>
            </div>
        </div>
    `).join('');
} 