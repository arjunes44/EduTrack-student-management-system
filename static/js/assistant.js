const assistantLauncher = document.querySelector('#assistant-launcher');
const assistantPanel = document.querySelector('#assistant-panel');
const assistantClose = document.querySelector('#assistant-close');
const assistantForm = document.querySelector('#assistant-form');
const assistantInput = document.querySelector('#assistant-input');
const assistantMessages = document.querySelector('#assistant-messages');

function toggleAssistant(open) {
  assistantPanel.classList.toggle('open', open);
  assistantPanel.setAttribute('aria-hidden', String(!open));
  assistantLauncher.setAttribute('aria-expanded', String(open));
  if (open) assistantInput.focus();
}

function addAssistantMessage(text, fromUser = false) {
  const message = document.createElement('div');
  message.className = `assistant-message ${fromUser ? 'assistant-message-user' : 'assistant-message-bot'}`;
  message.textContent = text;
  assistantMessages.append(message);
  assistantMessages.scrollTop = assistantMessages.scrollHeight;
}

assistantLauncher.addEventListener('click', () => toggleAssistant(!assistantPanel.classList.contains('open')));
assistantClose.addEventListener('click', () => toggleAssistant(false));
assistantForm.addEventListener('submit', async event => {
  event.preventDefault();
  const message = assistantInput.value.trim();
  if (!message) return;
  addAssistantMessage(message, true);
  assistantInput.value = '';
  assistantInput.disabled = true;
  try {
    const response = await fetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    const result = await response.json();
    addAssistantMessage(result.reply || 'I could not find an answer for that yet.');
  } catch (error) {
    addAssistantMessage('The assistant is temporarily unavailable. Please try again.');
  } finally {
    assistantInput.disabled = false;
    assistantInput.focus();
  }
});
