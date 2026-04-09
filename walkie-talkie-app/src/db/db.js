import { openDB } from 'idb';

const DB_NAME = 'WalkieTalkieVault';
const STORE_NAME = 'nodes';

export async function initDB() {
    const db = await openDB(DB_NAME, 1, {
        upgrade(db) {
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id' });
            }
        },
    });

    const count = await db.count(STORE_NAME);
    // If we want to seed defaults, we could do it here, but we will rely on fetchDynamicNodes.
    
    return db;
}

export async function fetchDynamicNodes(city, dates) {
    const db = await initDB();
    try {
        const response = await fetch('/api/synthesize-itinerary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city, dates })
        });
        const dynamicNodes = await response.json();
        
        if (dynamicNodes && dynamicNodes.length > 0) {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            for (const node of dynamicNodes) {
                node.visited = false;
                node.lastVisited = null;
                tx.store.put(node);
            }
            await tx.done;
            return true;
        }
    } catch (e) {
        console.error("Failed to fetch dynamic nodes:", e);
    }
    return false;
}

export async function getNodes() {
    const db = await initDB();
    const nodes = await db.getAll(STORE_NAME);
    const now = Date.now();
    const COOLDOWN_MS = 30 * 60 * 1000; // 30 minutes
    return nodes.map(n => ({
        ...n,
        locked: n.lastVisited ? (now - n.lastVisited < COOLDOWN_MS) : false
    }));
}

export async function markNodeVisited(id) {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const node = await tx.store.get(id);
    if (node) {
        node.visited = true;          // Overall discovery tracking
        node.lastVisited = Date.now(); // Proximity Cooldown
        await tx.store.put(node);
    }
    await tx.done;
}

export async function resetVisited() {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const nodes = await tx.store.getAll();
    for (const node of nodes) {
        node.visited = false;
        node.lastVisited = null;
        tx.store.put(node);
    }
    await tx.done;
}
