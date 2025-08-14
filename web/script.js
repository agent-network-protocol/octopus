// Octopus AI Assistant - Frontend JavaScript

class OctopusChat {
    constructor() {
        this.elements = {
            chatMessages: document.getElementById('chatMessages'),
            messageInput: document.getElementById('messageInput'),
            sendButton: document.getElementById('sendButton'),
            characterCount: document.getElementById('characterCount'),
            statusIndicator: document.getElementById('statusIndicator')
        };

        this.isLoading = false;
        this.maxCharacters = 2000;

        this.init();
    }

    init() {
        this.bindEvents();
        this.updateCharacterCount();
        this.checkSystemStatus();

        // Auto-resize textarea
        this.autoResizeTextarea();
    }

    bindEvents() {
        // Send button click
        this.elements.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });

        // Enter key to send (Shift+Enter for new line)
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Character count update
        this.elements.messageInput.addEventListener('input', () => {
            this.updateCharacterCount();
            this.autoResizeTextarea();
        });

        // Paste event handling
        this.elements.messageInput.addEventListener('paste', (e) => {
            setTimeout(() => {
                this.updateCharacterCount();
                this.autoResizeTextarea();
            }, 10);
        });
    }

    autoResizeTextarea() {
        const textarea = this.elements.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    updateCharacterCount() {
        const currentLength = this.elements.messageInput.value.length;
        this.elements.characterCount.textContent = `${currentLength}/${this.maxCharacters}`;

        // Update button state
        const isEmpty = currentLength === 0;
        const tooLong = currentLength > this.maxCharacters;

        this.elements.sendButton.disabled = isEmpty || tooLong || this.isLoading;

        // Update character count color
        if (tooLong) {
            this.elements.characterCount.style.color = '#dc2626';
        } else if (currentLength > this.maxCharacters * 0.9) {
            this.elements.characterCount.style.color = '#f59e0b';
        } else {
            this.elements.characterCount.style.color = '#94a3b8';
        }
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/v1/status');
            const data = await response.json();

            if (data.status === 'healthy') {
                this.updateStatus('Ready', 'success');
            } else {
                this.updateStatus('System Issue', 'error');
            }
        } catch (error) {
            console.error('Status check failed:', error);
            this.updateStatus('Disconnected', 'error');
        }
    }

    updateStatus(text, type) {
        const statusText = this.elements.statusIndicator.querySelector('.status-text');
        const statusDot = this.elements.statusIndicator.querySelector('.status-dot');

        statusText.textContent = text;

        // Remove existing status classes
        statusDot.classList.remove('status-success', 'status-error', 'status-warning');

        // Add appropriate status class
        switch (type) {
            case 'success':
                statusDot.style.background = '#4ade80';
                break;
            case 'error':
                statusDot.style.background = '#ef4444';
                break;
            case 'warning':
                statusDot.style.background = '#f59e0b';
                break;
            default:
                statusDot.style.background = '#94a3b8';
        }
    }

    async sendMessage() {
        const messageText = this.elements.messageInput.value.trim();

        if (!messageText || this.isLoading) {
            return;
        }

        // Add user message to chat
        this.addMessage(messageText, 'user');

        // Clear input
        this.elements.messageInput.value = '';
        this.updateCharacterCount();
        this.autoResizeTextarea();

        // Show loading state (add processing message)
        const processingMessageId = this.addProcessingMessage();
        this.setLoading(true);

        try {
            // Send request to backend
            const response = await fetch('/v1/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messageText,
                    timestamp: new Date().toISOString()
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Remove processing message
            this.removeProcessingMessage(processingMessageId);

            if (data.success) {
                // Add assistant response
                this.addMessage(data.response, 'assistant');
                this.updateStatus('Ready', 'success');
            } else {
                // Handle error response
                this.addMessage(
                    `抱歉，处理您的请求时遇到了问题：${data.error || '未知错误'}`,
                    'assistant',
                    'error'
                );
                this.updateStatus('Error', 'error');
            }

        } catch (error) {
            console.error('Send message error:', error);

            // Remove processing message
            this.removeProcessingMessage(processingMessageId);

            this.addMessage(
                '抱歉，网络连接出现问题，请稍后重试。',
                'assistant',
                'error'
            );
            this.updateStatus('Connection Error', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    addMessage(content, sender, type = 'normal') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? '👤' : '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Handle different message types
        if (type === 'error') {
            contentDiv.classList.add('error-message');
        }

        // Format content (handle JSON responses, code blocks, etc.)
        const formattedContent = this.formatMessageContent(content);
        contentDiv.innerHTML = formattedContent;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        this.elements.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.scrollToBottom();
    }

    formatMessageContent(content) {
        // Handle JSON responses
        try {
            const parsed = JSON.parse(content);
            if (typeof parsed === 'object') {
                return `<pre>${JSON.stringify(parsed, null, 2)}</pre>`;
            }
        } catch (e) {
            // Not JSON, continue with regular formatting
        }

        // Convert line breaks to HTML
        let formatted = content.replace(/\n/g, '<br>');

        // Handle code blocks (```code```)
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');

        // Handle inline code (`code`)
        formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.1); padding: 0.2rem 0.4rem; border-radius: 0.25rem; font-family: monospace;">$1</code>');

        return `<p>${formatted}</p>`;
    }

    addProcessingMessage() {
        // Generate unique ID for processing message
        const processingId = 'processing_' + Date.now();

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message processing-message';
        messageDiv.id = processingId;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content processing-content';
        contentDiv.innerHTML = `
            <div class="processing-indicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <p>AI正在思考中...</p>
            </div>
        `;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        this.elements.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.scrollToBottom();

        return processingId;
    }

    removeProcessingMessage(processingId) {
        const processingMessage = document.getElementById(processingId);
        if (processingMessage) {
            processingMessage.remove();
        }
    }

    setLoading(loading) {
        this.isLoading = loading;

        if (loading) {
            this.updateStatus('Processing...', 'warning');
        }

        this.elements.sendButton.disabled = loading;
        this.updateCharacterCount();
    }

    scrollToBottom() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    // Utility method to show notifications
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '1rem 1.5rem',
            borderRadius: '0.5rem',
            color: 'white',
            fontWeight: '500',
            zIndex: '9999',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s ease'
        });

        // Set background color based on type
        switch (type) {
            case 'success':
                notification.style.background = '#10b981';
                break;
            case 'error':
                notification.style.background = '#ef4444';
                break;
            case 'warning':
                notification.style.background = '#f59e0b';
                break;
            default:
                notification.style.background = '#6366f1';
        }

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
}

// Initialize the chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.octopusChat = new OctopusChat();

    // Global error handler
    window.addEventListener('error', (event) => {
        console.error('Global error:', event.error);
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
    });
});
