import { useState } from 'react';
import { sendPromptToGPT } from '../../api/chat';  // Adjusted import path

function GptChatBox() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');

  const handleSend = async () => {
    if (!input.trim()) return;
    const reply = await sendPromptToGPT(input);
    setResponse(reply);
  };

  return (
    <div style={{ padding: '1rem', border: '1px solid #ccc', marginTop: '2rem' }}>
      <h3>Ask GPT</h3>
      <textarea
        rows={3}
        style={{ width: '100%' }}
        placeholder="Type your question..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button onClick={handleSend} style={{ marginTop: '0.5rem' }}>Send</button>
      <div style={{ marginTop: '1rem', backgroundColor: '#f9f9f9', padding: '1rem' }}>
        <strong>GPT says:</strong> {response}
      </div>
    </div>
  );
}

export default GptChatBox;
