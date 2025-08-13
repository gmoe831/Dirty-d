const BACKEND_URL = "https://dirty-d-9mcb.onrender.com" // Render will proxy /api to backend when deployed on Render. Locally, use full URL to your Render service.

const chatBox = document.getElementById('chat');
const recordBtn = document.getElementById('recordBtn');
const textInput = document.getElementById('textInput');
const sendBtn = document.getElementById('sendBtn');
const audioEl = document.getElementById('voice');

function appendMessage(text, cls){
  const div = document.createElement('div');
  div.className = 'message ' + cls;
  div.innerText = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function showSystem(text){
  const div = document.createElement('div');
  div.className = 'message system';
  div.innerText = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// Send typed message
sendBtn.addEventListener('click', () => {
  const text = textInput.value.trim();
  if(!text) return;
  textInput.value = '';
  appendMessage(text, 'user');
  sendToBackend(text);
});

textInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') sendBtn.click(); });

// Tap-to-talk using Web Speech API
let recognition, listening = false;
if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => { listening = true; recordBtn.innerText = '🔴 Listening... (tap to stop)'; };
  recognition.onend = () => { listening = false; recordBtn.innerText = '🎙️ Tap to Talk'; };
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    appendMessage(transcript, 'user');
    sendToBackend(transcript);
  };
  recognition.onerror = (e) => { console.error('Speech error', e); showSystem('Speech recognition error.'); };
} else { recordBtn.disabled = true; recordBtn.title = "Speech recognition not supported"; }

recordBtn.addEventListener('click', () => {
  if(!recognition) { alert('Use Chrome or Safari for tap-to-talk.'); return; }
  if(!listening) recognition.start(); else recognition.stop();
});

async function sendToBackend(text){
  showSystem('Thinking...');
  try{
    // If hosted via Render with proxy, use /api/chat; otherwise replace BACKEND_URL with full Render URL + /chat
    let endpoint = (BACKEND_URL === '/api') ? '/chat' : BACKEND_URL + '/chat';
    const res = await fetch(endpoint, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:text}) });
    const data = await res.json();
    const reply = data.text || data.reply || '[No reply]';
    appendMessage(reply, 'bot');
    document.querySelectorAll('.system').forEach(s=>s.remove());
    if(data.audio){ audioEl.src = 'data:audio/mpeg;base64,' + data.audio; audioEl.style.display='block'; audioEl.play().catch(()=>{}); }
  }catch(err){
    console.error(err); showSystem('Error: could not reach backend.'); 
  }
}
