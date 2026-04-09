import { useState, useRef, useEffect } from "react";

const SYSTEM_PROMPT = `You are WalkieTalkie, an intelligent, charismatic local human travel guide. You are NOT a robotic encyclopedia—you are a passionate local showing visitors around your city!

Your personality:
- Warm, highly engaging, and fun. Like a knowledgeable local friend.
- You occasionally crack witty jokes and make history fascinating, even for kids.
- You use sensory details: smells, sounds, textures of places.
- Budget-conscious: always mention approximate costs in USD.
- You weave in factual, strictly neutral, and unbiased socio-political context to deliver a true "insider" feel without taking political sides.

Your capabilities:
- Suggest cheap authentic local eateries with backstory.
- Plan budget itineraries with food, history, art.
- Explain cultural significance of neighborhoods, murals, landmarks.
- Find hidden gems that locals use but tourists miss.
- Advise on transit, safety, and neighborhood changes.

When a user uploads an image, analyze it deeply:
- If it's a building/landmark/mural: explain its local significance TODAY.
- Keep responses conversational, vivid, entertaining, and under 300 words.
Always end responses with one "Local Secret" tip — something only regulars would know.`;

const VISION_SYSTEM_PROMPT = `You are WalkieTalkie, an intelligent local travel Virtual Assistant analyzing images for student travelers.
Your sole purpose right now is to look at the uploaded image and describe it in a culturally rich, budget-conscious way.

If it's a structural building, mural, menu, or landmark, explain its cultural and local significance, history, and what it means to locals today. 
DO NOT plan an itinerary unless explicitly asked. Focus entirely on describing what is in the picture and giving it vibrant context.
End your response with a "Local Secret" tip related to the kind of place or object shown in the image. Keep responses conversational, vivid, and under 250 words.`;

const suggestedPrompts = [
  { icon: "🍜", text: "5 cheap lunch spots where locals actually eat in a historic district" },
  { icon: "🎨", text: "Best neighborhoods for community-driven street art" },
  { icon: "🚌", text: "Cheapest public transit from airport to city center" },
  { icon: "📸", text: "Free Instagram spot that's culturally significant, not touristy" },
  { icon: "🏘️", text: "How has a neighborhood changed in 50 years?" },
  { icon: "💰", text: "1-day plan for under $30 with history, food & a sunset" },
];

import SpatialTrigger from './components/SpatialTrigger';
import { narrator } from './services/NarratorService';

const CITIES = ["San Francisco", "Boston", "New York", "San Diego", "Kyoto", "Tokyo", "London", "Kolkata", "Mumbai"];

export default function WalkieTalkie() {
  const [showMap, setShowMap] = useState(false);
  const [selectedCity, setSelectedCity] = useState("San Francisco");
  const [travelDates, setTravelDates] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileRef = useRef(null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      // Ollama expects a raw base64 string without the data URI prefix (e.g. data:image/jpeg;base64,)
      const base64Data = ev.target.result.split(',')[1];
      setImage({ data: base64Data, type: file.type });
      setImagePreview(ev.target.result);
    };
    reader.readAsDataURL(file);
  };

  const sendMessage = async (text) => {
    const userText = text || input.trim();
    if (!userText && !image) return;

    // Handle resume logic if user says yes to continuing the story
    if (narrator.synth && narrator.synth.paused && userText.match(/^(yes|yeah|sure|yep|please|go ahead|finish)/i)) {
        narrator.resume();
        const newMessages = [...messages, { role: "user", text: userText }, { role: "assistant", content: "Resuming the story..." }];
        setMessages(newMessages);
        setInput("");
        return;
    }

    let isInterrupting = false;
    let topicToRestore = "";
    if (narrator.isSpeaking()) {
        narrator.pause();
        isInterrupting = true;
        topicToRestore = narrator.currentTopic || "this location";
    }

    const userContent = [];
    if (image) {
      userContent.push({ type: "image", source: { type: "base64", media_type: image.type, data: image.data } });
    }
    if (userText) {
      userContent.push({ type: "text", text: userText });
    }

    const newMessages = [...messages, { role: "user", content: userContent, preview: imagePreview, text: userText }];
    setMessages(newMessages);
    setInput("");
    setImage(null);
    setImagePreview(null);
    setLoading(true);

    const apiMessages = newMessages.map((m) => {
      // Extract text content (Ollama expects content to be a string)
      let textContent = "";
      if (typeof m.content === "string") {
        textContent = m.content;
      } else if (Array.isArray(m.content)) {
        const textBlock = m.content.find((b) => b.type === "text");
        textContent = textBlock ? textBlock.text : "";
      }

      // If user uploaded an image, prepare it for Ollama Vision models (like llama3.2-vision)
      let images = undefined;
      // In our state, m.content is an array of objects for user messages
      if (m.role === "user" && Array.isArray(m.content)) {
        const imageBlocks = m.content.filter((b) => b.type === "image");
        if (imageBlocks.length > 0) {
          images = imageBlocks.map(b => b.source.data);
        }
      }

      return {
        role: m.role,
        content: textContent,
        ...(images && { images }),
      };
    });

    if (isInterrupting) {
        const lastMsg = apiMessages[apiMessages.length - 1];
        lastMsg.content = `[SYSTEM NOTE: The user just interrupted an ongoing audio narration about ${topicToRestore} to say this. Answer their question concisely, and end your response by asking if they would like you to finish the story.]\n\nUser: ` + lastMsg.content;
    }

    try {
      // Add an initial empty assistant message to hold the streaming content
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      const hasImage = apiMessages.some(m => m.images);
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: hasImage ? "llama3.2-vision" : "phi4",
          messages: [
            { role: "system", content: (hasImage ? VISION_SYSTEM_PROMPT : SYSTEM_PROMPT) + `\n\n[CONTEXT: User is currently planning a trip to ${selectedCity} during the dates: ${travelDates || 'TBD'}. Tailor responses and live events data to this location and timeframe.]` },
            ...apiMessages
          ],
          stream: true, // Enable streaming
        }),
      });

      if (!res.ok) throw new Error("Network response was not ok");
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      setLoading(false); // Turn off loading dots as soon as stream starts

      let fullReply = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.trim() !== '') {
            try {
              const parsed = JSON.parse(line);
              if (parsed.message?.content) {
                fullReply += parsed.message.content;
                // Update the last message (the assistant one we just added)
                setMessages((prev) => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = fullReply;
                  return newMsgs;
                });
              }
            } catch (e) {
              // Ignore JSON parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        // If we created a blank stream message, overwrite it with the error. Otherwise push a new error block.
        if (prev[prev.length - 1].role === "assistant" && prev[prev.length - 1].content === "") {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = "Something went wrong connecting to the local AI. Is Ollama running?";
          return newMsgs;
        }
        return [...prev, { role: "assistant", content: "Something went wrong connecting to the local AI. Is Ollama running?" }];
      });
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatText = (text) => {
    return text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/🗝️[^\n]*/g, (m) => `<span class="local-secret">${m}</span>`)
      .replace(/Local Secret[^\n]*/g, (m) => `<span class="local-secret">🗝️ ${m}</span>`)
      .replace(/\n/g, "<br>");
  };

  const isEmpty = messages.length === 0;

  return (
    <div style={{ fontFamily: "'Georgia', serif", minHeight: "100vh", background: "#0f0e0b", color: "#f0ead6", display: "flex", flexDirection: "column" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Serif+4:wght@300;400;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0f0e0b; }
        .app { font-family: 'Source Serif 4', serif; }
        .header { 
          padding: 20px 24px 16px; 
          border-bottom: 1px solid #2a2820;
          display: flex; align-items: center; gap: 12px;
          background: #0f0e0b;
          position: sticky; top: 0; z-index: 10;
        }
        .logo-mark {
          width: 40px; height: 40px;
          background: linear-gradient(135deg, #c8a96e, #8b6914);
          border-radius: 10px;
          display: flex; align-items: center; justify-content: center;
          font-size: 20px;
        }
        .brand { font-family: 'Playfair Display', serif; font-size: 22px; font-weight: 700; color: #c8a96e; letter-spacing: -0.5px; }
        .tagline { font-size: 11px; color: #6b6452; text-transform: uppercase; letter-spacing: 2px; margin-top: 1px; }
        
        .chat-area { flex: 1; overflow-y: auto; padding: 24px 16px; max-width: 780px; margin: 0 auto; width: 100%; }
        
        .welcome { text-align: center; padding: 48px 20px 32px; }
        .welcome h1 { font-family: 'Playfair Display', serif; font-size: 36px; color: #c8a96e; margin-bottom: 8px; }
        .welcome p { color: #8a7d66; font-size: 15px; line-height: 1.6; max-width: 480px; margin: 0 auto 32px; }
        
        .suggestions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-width: 600px; margin: 0 auto; }
        .suggestion-btn {
          background: #1a1810; border: 1px solid #2a2820;
          color: #c4b69a; padding: 12px 14px; border-radius: 10px;
          cursor: pointer; text-align: left; font-family: 'Source Serif 4', serif;
          font-size: 13px; line-height: 1.4; transition: all 0.2s;
          display: flex; gap: 8px; align-items: flex-start;
        }
        .suggestion-btn:hover { background: #22201a; border-color: #c8a96e44; color: #f0ead6; }
        .suggestion-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
        
        .message { margin-bottom: 24px; display: flex; gap: 12px; animation: fadeUp 0.3s ease; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .message.user { flex-direction: row-reverse; }
        .avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; margin-top: 2px; }
        .avatar.ai { background: linear-gradient(135deg, #c8a96e, #8b6914); }
        .avatar.user { background: #2a2820; }
        .bubble { max-width: 78%; padding: 14px 16px; border-radius: 14px; font-size: 14.5px; line-height: 1.7; }
        .bubble.ai { background: #1a1810; border: 1px solid #2a2820; color: #ddd5c0; border-radius: 4px 14px 14px 14px; }
        .bubble.user { background: linear-gradient(135deg, #c8a96e22, #8b691422); border: 1px solid #c8a96e33; color: #f0ead6; border-radius: 14px 4px 14px 14px; }
        .local-secret { display: block; margin-top: 12px; padding: 10px 12px; background: #c8a96e11; border-left: 2px solid #c8a96e; border-radius: 0 8px 8px 0; color: #c8a96e; font-style: italic; font-size: 13.5px; }
        .img-preview { max-width: 200px; border-radius: 8px; margin-bottom: 8px; display: block; }
        
        .typing { display: flex; gap: 4px; align-items: center; padding: 14px 16px; }
        .dot { width: 6px; height: 6px; background: #c8a96e; border-radius: 50%; animation: bounce 1.2s infinite; }
        .dot:nth-child(2) { animation-delay: 0.2s; }
        .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
        
        .input-area { 
          padding: 16px; border-top: 1px solid #2a2820;
          background: #0f0e0b;
          position: sticky; bottom: 0;
        }
        .input-wrap { max-width: 780px; margin: 0 auto; display: flex; gap: 8px; align-items: flex-end; }
        .img-attach-preview { position: relative; margin-bottom: 8px; }
        .img-attach-preview img { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; border: 1px solid #c8a96e44; }
        .remove-img { position: absolute; top: -6px; right: -6px; width: 18px; height: 18px; background: #c8a96e; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 10px; color: #0f0e0b; font-weight: bold; border: none; }
        .inner-wrap { flex: 1; background: #1a1810; border: 1px solid #2a2820; border-radius: 14px; overflow: hidden; transition: border-color 0.2s; }
        .inner-wrap:focus-within { border-color: #c8a96e55; }
        .attach-row { display: flex; gap: 4px; padding: 8px 10px 0; }
        .attach-btn { background: none; border: none; color: #6b6452; cursor: pointer; padding: 4px; border-radius: 6px; font-size: 16px; transition: color 0.2s; }
        .attach-btn:hover { color: #c8a96e; }
        textarea { 
          width: 100%; background: none; border: none; outline: none; 
          color: #f0ead6; font-family: 'Source Serif 4', serif; font-size: 14.5px; 
          padding: 8px 12px 10px; resize: none; min-height: 44px; max-height: 140px; line-height: 1.5;
        }
        textarea::placeholder { color: #4a4438; }
        .send-btn { 
          width: 42px; height: 42px; border-radius: 12px; 
          background: linear-gradient(135deg, #c8a96e, #8b6914);
          border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
          color: #0f0e0b; font-size: 18px; transition: opacity 0.2s; flex-shrink: 0;
        }
        .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .send-btn:hover:not(:disabled) { opacity: 0.85; }
        .hint { text-align: center; font-size: 11px; color: #3a3428; margin-top: 8px; }
      `}</style>

      <div className="app" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        {showMap && <SpatialTrigger onClose={() => setShowMap(false)} />}
        <div className="header">
          <div className="logo-mark">🗺️</div>
          <div style={{ flex: 1 }}>
            <div className="brand">WalkieTalkie</div>
            <div className="tagline">Local Intel · Budget Travel · Hidden Cities</div>
          </div>
          <button
            style={{ background: '#c8a96e', color: '#0f0e0b', border: 'none', padding: '8px 16px', borderRadius: '20px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}
            onClick={() => setShowMap(true)}
          >
            Start Walk
          </button>
        </div>

        <div style={{ padding: "12px 24px", background: "#1a1810", borderBottom: "1px solid #2a2820", display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
           <span style={{ fontSize: "12px", color: "#8a7d66", textTransform: "uppercase", letterSpacing: "1px", fontWeight: "bold" }}>Location Focus:</span>
           <select 
              value={selectedCity}
              onChange={e => setSelectedCity(e.target.value)}
              style={{ background: "#2a2820", color: "#f0ead6", border: "1px solid #c8a96e44", padding: "6px 12px", borderRadius: "8px", outline: "none", fontSize: "14px", fontFamily: "inherit", cursor: "pointer" }}
           >
              {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
           </select>
           
           <input 
              type="date"
              value={travelDates}
              onChange={e => setTravelDates(e.target.value)}
              style={{ background: "#2a2820", color: "#f0ead6", border: "1px solid #c8a96e44", padding: "5px 12px", borderRadius: "8px", outline: "none", fontSize: "14px", fontFamily: "inherit", colorScheme: "dark", cursor: "pointer" }}
           />
        </div>

        <div className="chat-area" style={{ flex: 1 }}>
          {isEmpty ? (
            <div className="welcome">
              <h1>Explore Like a Local</h1>
              <p>I know the spots that don't show up on travel blogs — the century-old tea stall, the mural with a story, the $4 meal that locals swear by.</p>
              <div className="suggestions">
                {suggestedPrompts.map((p, i) => (
                  <button key={i} className="suggestion-btn" onClick={() => sendMessage(p.text)}>
                    <span className="suggestion-icon">{p.icon}</span>
                    <span>{p.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className={`avatar ${msg.role === "assistant" ? "ai" : "user"}`}>
                  {msg.role === "assistant" ? "🗺️" : "✈️"}
                </div>
                <div className={`bubble ${msg.role === "assistant" ? "ai" : "user"}`}>
                  {msg.preview && <img src={msg.preview} alt="uploaded" className="img-preview" />}
                  {msg.role === "assistant"
                    ? <div dangerouslySetInnerHTML={{ __html: formatText(msg.content) }} />
                    : <span>{msg.text}</span>
                  }
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message">
              <div className="avatar ai">🗺️</div>
              <div className="bubble ai">
                <div className="typing">
                  <div className="dot" /><div className="dot" /><div className="dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-area">
          <div className="input-wrap">
            <div style={{ flex: 1 }}>
              {imagePreview && (
                <div className="img-attach-preview">
                  <img src={imagePreview} alt="preview" />
                  <button className="remove-img" onClick={() => { setImage(null); setImagePreview(null); }}>✕</button>
                </div>
              )}
              <div className="inner-wrap">
                <div className="attach-row">
                  <button className="attach-btn" title="Upload image" onClick={() => fileRef.current?.click()}>📷</button>
                  <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImageUpload} />
                </div>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Ask about a city, neighborhood, food spot, or upload a photo..."
                  rows={1}
                  onInput={(e) => { e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"; }}
                />
              </div>
            </div>
            <button className="send-btn" onClick={() => sendMessage()} disabled={loading || (!input.trim() && !image)}>
              ↑
            </button>
          </div>
          <div className="hint">Upload photos of menus, murals, or buildings for instant local insight</div>
        </div>
      </div>
    </div>
  );
}