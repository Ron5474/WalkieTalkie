import React, { useState, useEffect } from 'react';
import { useGeolocation } from '../hooks/useGeolocation';
import { calculateDistance } from '../utils/geo';
import { getNodes, markNodeVisited, resetVisited } from '../db/db';
import { narrator } from '../services/NarratorService';
import { generateIntro } from '../utils/storyTemplating';

/**
 * Locality-first walking tour: explore by neighborhood stop, not turn-by-turn directions.
 * When you're physically near a stop (~20m), the story plays automatically.
 *
 * @param {string} city — Trip city (always from the toolbar).
 * @param {string|null} [areaLabel] — Neighborhood / day locality from the itinerary when available.
 */
export default function WalkView({ city = "this city", areaLabel = null, llmTier = "small" }) {
    const primaryArea =
        typeof areaLabel === "string" && areaLabel.trim().length > 0 ? areaLabel.trim() : city;
    const showCityLine =
        typeof areaLabel === "string" &&
        areaLabel.trim().length > 0 &&
        city &&
        areaLabel.trim().toLowerCase() !== city.trim().toLowerCase();
    const { location, error } = useGeolocation();
    const [nodes, setNodes] = useState([]);
    const [targetNode, setTargetNode] = useState(null);
    const [distance, setDistance] = useState(null);
    const [narrating, setNarrating] = useState(null);

    useEffect(() => {
        loadNodes();
    }, []);

    const loadNodes = async () => {
        const data = await getNodes();
        setNodes(data);
    };

    const handleReset = async () => {
        await resetVisited();
        loadNodes();
    };

    useEffect(() => {
        if (targetNode && location) {
            const dist = calculateDistance(
                location.lat,
                location.lng,
                targetNode.lat,
                targetNode.lng
            );
            setDistance(Math.round(dist));

            if (dist <= 20 && !targetNode.locked && !narrating) {
                triggerNarration(targetNode);
            }
        }
    }, [location, targetNode, narrating]);

    const triggerNarration = async (node) => {
        setNarrating(node.title);
        narrator.currentTopic = node.title;

        setTargetNode(prev => ({ ...prev, visited: true, locked: true }));

        await markNodeVisited(node.id);
        loadNodes();

        const introText = generateIntro(node.title);
        let personaStory = "";
        try {
            const res = await fetch("/api/walk-story", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    city,
                    place_title: node.title,
                    anecdote: node.anecdote || "",
                    llm_tier: llmTier,
                }),
            });
            if (res.ok) {
                const payload = await res.json();
                personaStory = (payload?.story || "").trim();
            }
        } catch {
            // Graceful fallback below.
        }
        const fullText = personaStory || (introText + " " + (node.anecdote || ""));
        narrator.speak(fullText, () => setNarrating(null));
    };

    const stopNarration = () => {
        narrator.cancel();
        setNarrating(null);
    };

    return (
        <div className="walk-view">
            <h2 className="walk-title">Walk · {primaryArea}</h2>
            {showCityLine ? (
                <p className="walk-city-line">{city}</p>
            ) : null}
            <p className="walk-blurb">
                Choose a stop in this area. Wander the block; when you’re within about 20m, the story unlocks automatically.
            </p>

            {error && <p className="walk-error">Location error: {error}</p>}
            {!location && !error && <p className="walk-info">Finding your position…</p>}
            {location && <p className="walk-info">Location accuracy ~{Math.round(location.accuracy)}m</p>}

            {narrating ? (
                <div className="walk-narrating-box">
                    <h3>🔊 Story: {narrating}</h3>
                    <div className="typing" style={{ justifyContent: 'center', margin: '20px 0' }}>
                        <div className="dot" /><div className="dot" /><div className="dot" />
                    </div>
                    <button className="walk-stop-btn" onClick={stopNarration}>Stop</button>
                </div>
            ) : (
                targetNode ? (
                    <div className="walk-guiding-box">
                        <h3>Walking stop: {targetNode.title}</h3>
                        <p style={{ fontSize: '15px', color: '#c4b69a', marginBottom: '12px', lineHeight: 1.5 }}>
                            Stroll this part of town — no driving directions, just local context when you arrive.
                        </p>
                        <p className="walk-distance">
                            {distance !== null ? `~${distance} m` : '…'}
                        </p>
                        <p style={{ fontSize: '13px', color: '#8a7d66', marginBottom: '16px' }}>
                            {distance !== null && distance > 20
                                ? 'Move closer to this corner or block to unlock the narration (~20m).'
                                : distance !== null && distance <= 20
                                    ? 'You’re in range — story should play, or tap below.'
                                    : null}
                        </p>
                        {distance !== null && distance <= 20 && targetNode.visited && (
                            <button
                                className="walk-btn"
                                style={{ marginBottom: '12px', background: 'rgba(200, 169, 110, 0.1)' }}
                                onClick={() => triggerNarration(targetNode)}
                            >
                                Play story again 🎧
                            </button>
                        )}
                        <button className="walk-btn" onClick={() => setTargetNode(null)}>Pick another stop</button>
                    </div>
                ) : (
                    <div className="walk-list">
                        <h3 style={{ marginBottom: '10px', color: '#c4b69a', fontSize: '15px' }}>Stops in your plan (same-day area)</h3>
                        {nodes.map(n => (
                            <div key={n.id} className="walk-node-card">
                                <div>
                                    <strong style={{ fontSize: '14px' }}>{n.title}</strong>
                                    {n.visited && <span className="walk-badge">Heard</span>}
                                </div>
                                <button
                                    className="walk-nav-btn"
                                    onClick={() => setTargetNode(n)}
                                >
                                    Walk here
                                </button>
                            </div>
                        ))}
                        <div className="walk-actions">
                            <button className="walk-btn" style={{ marginTop: '20px' }} onClick={handleReset}>Reset stops</button>
                        </div>
                    </div>
                )
            )}
        </div>
    );
}
