import { useState, useRef, useEffect } from "react";

import { useGeolocation } from './hooks/useGeolocation';
import { narrator } from './services/NarratorService';
import { PROMPT_STRATEGIES, CITIES } from './constants';
import TopBar from './components/TopBar';
import TabBar from './components/TabBar';
import GuideView from './components/GuideView';
import Composer from './components/Composer';
import TripView from './components/TripView';
import WalkView from './components/WalkView';
import SettingsSheet from './components/sheets/SettingsSheet';
import CityHistorySheet from './components/sheets/CityHistorySheet';
import LoginScreen from './components/LoginScreen';

export default function WalkieTalkie() {
  const [activeTab, setActiveTab] = useState('guide');
  const [cityHistoryOpen, setCityHistoryOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedCity, setSelectedCity] = useState("San Francisco");
  const [llmTier, setLlmTier] = useState("large");
  const [promptStrategy, setPromptStrategy] = useState("self_reflection");
  const [travelDates, setTravelDates] = useState("");
  const [numDays, setNumDays] = useState(1);
  const [numDaysInput, setNumDaysInput] = useState("1");
  const [budget] = useState("Moderate");
  const [activeSubTab, setActiveSubTab] = useState("itinerary");
  const [itineraryMap, setItineraryMap] = useState(null);

  // Live GPS from browser geolocation hook (no simulation mode).
  const { location } = useGeolocation();
  const currentGPS = location || null;

  const [chatByCity, setChatByCity] = useState({});
  const [sessionToken, setSessionToken] = useState(null);
  const [sessionUserId, setSessionUserId] = useState("");
  const [userBudget, setUserBudget] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [actionPlan, setActionPlan] = useState([]);
  /** Weather + packing from /api/holiday-briefing when entering Holiday Mode */
  const [holidayBriefing, setHolidayBriefing] = useState(null);
  const fileRef = useRef(null);
  const bottomRef = useRef(null);
  // Guards the chat-persistence effect: skip the write that immediately follows a load /
  // storage-key switch so we never clobber a key with the previous key's stale state.
  const skipNextChatSaveRef = useRef(false);
  const AUTH_STORAGE_KEY = "walkie_talkie_auth_v1";
  const chatStorageKey = `walkie_talkie_chat_by_city_v1_${sessionUserId || "guest"}`;

  const messages = chatByCity[selectedCity] || [];

  const updateCurrentCityMessages = (updater) => {
    setChatByCity((prev) => {
      const current = prev[selectedCity] || [];
      const nextMessages = typeof updater === "function" ? updater(current) : updater;
      return { ...prev, [selectedCity]: nextMessages };
    });
  };

  const getPreviewText = (msg) => {
    if (!msg) return "";
    if (msg.role === "assistant") return (msg.content || "").replace(/\s+/g, " ").trim();
    return (msg.text || "").replace(/\s+/g, " ").trim();
  };

  const chatHistoryItems = CITIES.filter((city) => city === selectedCity || (chatByCity[city] && chatByCity[city].length > 0))
    .map((city) => {
      const thread = chatByCity[city] || [];
      const lastVisible = [...thread].reverse().find((m) => !m.hidden);
      return {
        city,
        count: thread.filter((m) => !m.hidden).length,
        preview: getPreviewText(lastVisible).slice(0, 80),
      };
    });

  useEffect(() => {
    try {
      const authRaw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (authRaw) {
        const auth = JSON.parse(authRaw);
        if (auth?.session_token && auth?.expires_at * 1000 > Date.now()) {
          setSessionToken(auth.session_token);
          setSessionUserId(auth.user_id || "");
          if (auth.profile?.budget != null) setUserBudget(String(auth.profile.budget));
        }
      }
    } catch {
      // Ignore corrupted local storage payloads.
    }
  }, []);

  // Load persisted chat for the active storage key (on mount and whenever the key changes,
  // e.g. sign-in/out). Declared BEFORE the save effect so that, on a key change, this runs
  // first and arms the skip guard before the save effect fires in the same commit.
  useEffect(() => {
    skipNextChatSaveRef.current = true;
    try {
      const raw = localStorage.getItem(chatStorageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        setChatByCity(parsed && typeof parsed === "object" ? parsed : {});
      } else {
        setChatByCity({});
      }
    } catch {
      setChatByCity({});
    }
  }, [chatStorageKey]);

  useEffect(() => {
    // Skip the write triggered by a load / key switch so stale in-memory state is never
    // persisted into the freshly-loaded key. Real edits (guard already false) still save.
    if (skipNextChatSaveRef.current) {
      skipNextChatSaveRef.current = false;
      return;
    }
    try {
      localStorage.setItem(chatStorageKey, JSON.stringify(chatByCity));
    } catch {
      // Ignore quota/serialization errors.
    }
  }, [chatByCity, chatStorageKey]);

  const ERROR_MESSAGES = {
    invalid_credentials: 'Incorrect username or password.',
    username_taken: 'That username is already taken.',
    weak_password: 'Password must be at least 8 characters.',
    username_required: 'Username is required.',
  };

  const authHeaders = () => ({
    'Content-Type': 'application/json',
    ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
  });

  const persistSession = (j) => {
    setSessionToken(j.session_token);
    setSessionUserId(j.user_id || '');
    if (j.profile?.budget != null) setUserBudget(String(j.profile.budget));
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(j));
  };

  const login = async (username, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const j = await res.json().catch(() => ({}));
    if (res.ok && j?.session_token) { persistSession(j); return { ok: true }; }
    return { ok: false, error: ERROR_MESSAGES[j?.detail] || 'Login failed. Please try again.' };
  };

  const register = async (username, password, budget) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, budget }),
    });
    const j = await res.json().catch(() => ({}));
    if (res.ok && j?.session_token) { persistSession(j); return { ok: true }; }
    return { ok: false, error: ERROR_MESSAGES[j?.detail] || 'Registration failed. Please try again.' };
  };

  const logout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST', headers: authHeaders() });
    } catch { /* ignore network errors on logout */ }
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setSessionToken(null);
    setSessionUserId('');
  };

  const saveBudgetPreference = async () => {
    if (!sessionToken) return;
    const n = parseInt(userBudget, 10);
    if (!Number.isFinite(n)) return;
    await fetch("/api/user/profile", {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ budget: n }),
    });
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "auto" });
  }, [messages.length, loading]);

  /** Neighborhood line for Start Walk — from day 1 of the generated plan, else falls back to city in WalkView. */
  const walkAreaLabel =
    Array.isArray(itineraryMap) && itineraryMap.length > 0 && itineraryMap[0].locality
      ? itineraryMap[0].locality
      : null;

  useEffect(() => {
    let cancelled = false;
    import("./db/db.js").then((m) => {
      return Promise.all([
        m.getUnvisitedNodes().then((nodes) => {
          if (!cancelled) setActionPlan(nodes);
        }),
        m.getSystemMapping().then((map) => {
          if (!cancelled) setItineraryMap(map);
        }),
      ]);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGenerateItinerary = async () => {
    setLoading(true);
    updateCurrentCityMessages(prev => [
      ...prev,
      {
        role: "assistant",
        content: `Waiting for the ${llmTier} itinerary model for ${selectedCity}...`,
      },
    ]);
    const { fetchDynamicNodes, getUnvisitedNodes, getSystemMapping } = await import('./db/db.js');
    try {
        const result = await fetchDynamicNodes(selectedCity, travelDates, numDays, budget, llmTier);
        const unvisited = await getUnvisitedNodes();
        const mapping = await getSystemMapping();
        setActionPlan(unvisited);
        setItineraryMap(mapping);
        if (result?.ok && Array.isArray(mapping) && mapping.length > 0) {
          updateCurrentCityMessages(prev => [
            ...prev,
            {
              role: "assistant",
              content:
                `I've generated a ${numDays}-day itinerary for ${selectedCity}. ` +
                `See each day under the Day-to-Day tab.`,
            },
          ]);
        } else {
          updateCurrentCityMessages(prev => [
            ...prev,
            {
              role: "assistant",
              content: `I couldn't generate the itinerary right now. Please try again in a bit.`,
            },
          ]);
        }
    } catch (err) {
        updateCurrentCityMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content: `Failed to load itinerary.\nError: ${String(err)}`,
          },
        ]);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (activeTab === 'trip') {
      import('./db/db.js').then(module => {
        module.getUnvisitedNodes().then(nodes => setActionPlan(nodes));
        module.getSystemMapping().then(mapping => setItineraryMap(mapping));
      });
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== "trip") {
      setHolidayBriefing(null);
      return;
    }
    let cancelled = false;
    setHolidayBriefing({ loading: true });
    fetch("/api/holiday-briefing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city: selectedCity,
        start_date: travelDates || null,
        days: numDays,
      }),
    })
      .then((r) => r.json())
      .then((j) => {
        if (!cancelled) setHolidayBriefing({ loading: false, ...j });
      })
      .catch((e) => {
        if (!cancelled) setHolidayBriefing({ loading: false, error: String(e), packing_advice: "" });
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab, selectedCity, travelDates, numDays]);

  const handleMarkCovered = async (nodeId, nodeTitle) => {
    const { markNodeVisited, getUnvisitedNodes } = await import('./db/db.js');
    await markNodeVisited(nodeId);
    const unvisited = await getUnvisitedNodes();
    setActionPlan(unvisited);
    if (sessionToken) {
      fetch("/api/user/visited", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          city: selectedCity,
          place_name: nodeTitle,
        }),
      }).catch(() => {});
    }

    // Proactive trigger to the Assistant (silent reroute logic)
    const systemPromptMsg = `[SYSTEM NUDGE] The user just marked "${nodeTitle}" as completed. Tell them "Great job!" and proactively suggest what they should do next on their itinerary right now.`;
    sendMessage(systemPromptMsg, true);
  };

  const handleDayCheckIn = () => {
    const systemPromptMsg = `[SYSTEM AUTOMATION] Time jump simulation: The afternoon is passing quickly and the user still has ${actionPlan.length} places left. Proactively ask how they are doing and suggest either taking a break for a snack or picking up the pace!`;
    sendMessage(systemPromptMsg, true);
  };

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

  const sendMessage = async (text, isHidden = false) => {
    const userText = (typeof text === 'string' ? text : null) || input.trim();
    if (!userText && !image) return;

    // Handle resume logic if user says yes to continuing the story
    if (narrator.synth && narrator.synth.paused && userText.match(/^(yes|yeah|sure|yep|please|go ahead|finish)/i)) {
        narrator.resume();
        const newMessages = [...messages, { role: "user", text: userText }, { role: "assistant", content: "Resuming the story..." }];
        updateCurrentCityMessages(newMessages);
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

    const newMessages = [...messages, { role: "user", content: userContent, preview: imagePreview, text: userText, hidden: isHidden }];
    updateCurrentCityMessages(newMessages);
    setInput("");
    setImage(null);
    setImagePreview(null);
    if (!isHidden) setLoading(true);

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
      const hasImage = apiMessages.some(m => m.images);
      const lat = currentGPS?.lat ?? null;
      const lng = currentGPS?.lng ?? null;
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          model: hasImage ? "vision" : llmTier,
          llm_tier: llmTier,
          // The backend owns the system prompt (single source of truth); we only send the turns.
          messages: apiMessages,
          stream: true,
          latitude: lat,
          longitude: lng,
          city: selectedCity,
          prompting_mode: promptStrategy,
        }),
      });

      if (res.status === 401) { await logout(); throw new Error("Session expired"); }
      if (!res.ok) throw new Error("Network response was not ok");
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      setLoading(false); // Turn off loading dots as soon as stream starts

      let fullReply = "";
      let appendedAssistant = false;
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
                updateCurrentCityMessages((prev) => {
                  if (!appendedAssistant) {
                    appendedAssistant = true;
                    return [...prev, { role: "assistant", content: fullReply }];
                  }
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  if (lastIdx >= 0 && newMsgs[lastIdx].role === "assistant") {
                    newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: fullReply };
                  } else {
                    newMsgs.push({ role: "assistant", content: fullReply });
                  }
                  return newMsgs;
                });
              }
            } catch {
              // Ignore JSON parse errors for incomplete chunks
            }
          }
        }
      }
    } catch {
      updateCurrentCityMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Could not reach the API backend. Check uvicorn on :8000 and OpenRouter settings in backend/.env." },
      ]);
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!sessionToken) {
    return <LoginScreen onLogin={login} onRegister={register} />;
  }

  return (
    <div className="app-shell">
      <TopBar
        selectedCity={selectedCity}
        onOpenCityHistory={() => setCityHistoryOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <div className="tab-body">
        {activeTab === 'guide' && (
          <>
            <GuideView
              messages={messages}
              loading={loading}
              bottomRef={bottomRef}
              onSuggestion={(text) => sendMessage(text)}
            />
            <Composer
              input={input}
              setInput={setInput}
              onSend={() => sendMessage()}
              onKeyDown={handleKey}
              imagePreview={imagePreview}
              onPickImage={() => fileRef.current?.click()}
              onRemoveImage={() => { setImage(null); setImagePreview(null); }}
              fileRef={fileRef}
              onFileChange={handleImageUpload}
              disabled={loading || (!input.trim() && !image)}
            />
          </>
        )}

        {activeTab === 'trip' && (
          <TripView
            selectedCity={selectedCity} setSelectedCity={setSelectedCity}
            numDaysInput={numDaysInput} setNumDaysInput={setNumDaysInput}
            setNumDays={setNumDays}
            userBudget={userBudget} setUserBudget={setUserBudget}
            saveBudgetPreference={saveBudgetPreference}
            travelDates={travelDates} setTravelDates={setTravelDates}
            loading={loading} onGenerate={handleGenerateItinerary}
            actionPlan={actionPlan} itineraryMap={itineraryMap}
            holidayBriefing={holidayBriefing}
            activeSubTab={activeSubTab} setActiveSubTab={setActiveSubTab}
            onMarkCovered={handleMarkCovered} onDayCheckIn={handleDayCheckIn}
          />
        )}

        {activeTab === 'walk' && (
          <WalkView city={selectedCity} areaLabel={walkAreaLabel} llmTier={llmTier} />
        )}
      </div>

      <TabBar activeTab={activeTab} setActiveTab={setActiveTab} />

      <CityHistorySheet
        open={cityHistoryOpen} onClose={() => setCityHistoryOpen(false)}
        chatHistoryItems={chatHistoryItems} selectedCity={selectedCity}
        onSelectCity={(city) => { setSelectedCity(city); setCityHistoryOpen(false); }}
      />
      <SettingsSheet
        open={settingsOpen} onClose={() => setSettingsOpen(false)}
        llmTier={llmTier} setLlmTier={setLlmTier}
        promptStrategy={promptStrategy} setPromptStrategy={setPromptStrategy}
        PROMPT_STRATEGIES={PROMPT_STRATEGIES}
        userBudget={userBudget} setUserBudget={setUserBudget}
        saveBudgetPreference={saveBudgetPreference}
        onLogout={logout}
      />
    </div>
  );
}
